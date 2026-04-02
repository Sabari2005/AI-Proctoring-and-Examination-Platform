"""
Periodic evidence capture and upload pipeline.

Captures desktop screenshots and optional webcam frames, compresses them,
signs payloads using HMAC-SHA256, and uploads to the evidence API.

Includes randomized scheduling, retry buffering, and HTTP 403 backoff control
to keep uploads resilient under temporary backend-policy failures.

Requires: mss, opencv-python
"""

from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import random
import ssl
import threading
import time
import urllib.request
import urllib.error
from collections import deque
from typing import Optional

import numpy as np

try:
    import mss
    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False
    print("[Snapshot] mss not installed — screenshot capture disabled. pip install mss")

try:
    import cv2 as _cv2
    _CV2_AVAILABLE = True
except ImportError:
    _cv2 = None
    _CV2_AVAILABLE = False


# Capture and upload configuration.
INTERVAL_MIN      = 25      # seconds (randomized lower bound)
INTERVAL_MAX      = 55      # seconds (randomized upper bound)
JPEG_QUALITY      = 50      # 0-100 quality/size balance
LOCAL_BUFFER_MAX  = 20      # Max locally buffered frames if upload fails
MAX_DIMENSION     = 1280    # Resize screenshot to fit within this width/height
FORBIDDEN_BACKOFF_BASE = 8  # Seconds base for HTTP 403 exponential backoff
FORBIDDEN_BACKOFF_MAX  = 90 # Max cooldown after repeated HTTP 403 errors


def _get_shared_secret() -> bytes:
    """
    Derive shared secret for HMAC signing.
    Must match backend secret policy to avoid unsigned/invalid evidence uploads.
    """
    secret = (os.environ.get("OBSERVE_PROCTOR_SECRET") or "").strip()
    if not secret or len(secret) < 24:
        raise RuntimeError(
            "OBSERVE_PROCTOR_SECRET is not set or too short. "
            "Evidence uploads will fail. Set this in your .env file."
        )
    return secret.encode("utf-8")


def _sign(payload: bytes, shared_secret: bytes) -> str:
    """Generate HMAC-SHA256 signature for payload."""
    return hmac.new(shared_secret, payload, hashlib.sha256).hexdigest()


def _jpeg_compress(arr: Optional[np.ndarray], quality: int = JPEG_QUALITY,
                   max_dim: int = MAX_DIMENSION) -> Optional[bytes]:
    """
    Compress image array to JPEG bytes.

    Input may be RGB (typical numpy capture) or already OpenCV-compatible.
    Returns None on failure.
    """
    if not _CV2_AVAILABLE or arr is None or arr.size == 0:
        return None
    try:
        h, w = arr.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            arr   = _cv2.resize(arr, (int(w * scale), int(h * scale)),
                                interpolation=_cv2.INTER_AREA)
        
        # Convert RGB-style arrays to BGR for OpenCV JPEG encoding.
        if len(arr.shape) == 3 and arr.shape[2] == 3:
            bgr = _cv2.cvtColor(arr, _cv2.COLOR_RGB2BGR)
        else:
            bgr = arr
            
        ok, buf = _cv2.imencode(".jpg", bgr, [_cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes() if ok else None
    except Exception as e:
        print(f"[Snapshot] JPEG compression error: {e}")
        return None


def _capture_screenshot() -> Optional[np.ndarray]:
    """Capture the primary monitor as an RGB numpy array."""
    if not _MSS_AVAILABLE:
        return None
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]   # Primary monitor.
            raw     = sct.grab(monitor)
            # mss returns BGRA; drop alpha and convert to RGB.
            arr = np.array(raw)[:, :, :3][:, :, ::-1]
            return arr
    except Exception as e:
        print(f"[Snapshot] Screenshot capture error: {e}")
        return None


def _ssl_ctx() -> ssl.SSLContext:
    """Create SSL context with secure defaults."""
    ctx = ssl.create_default_context()
    ctx.verify_mode     = ssl.CERT_REQUIRED
    ctx.check_hostname  = True
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


class SnapshotUploader:
    """
    Background worker that periodically captures and uploads evidence frames.
    
    Usage:
        uploader = SnapshotUploader(
            backend_url="https://api.example.com",
            session_nonce="unique-session-id",
            vision_proctor=vision_proctor_instance
        )
        uploader.start()
        # ... exam in progress ...
        uploader.stop()
    """

    def __init__(self,
                 backend_url: str,
                 session_nonce: str,
                 vision_proctor=None,
                 interval_min: float = INTERVAL_MIN,
                 interval_max: float = INTERVAL_MAX):
        """
        Initialize uploader runtime state and scheduling configuration.
        
        Args:
            backend_url: Base URL for backend API (e.g., "https://api.example.com")
            session_nonce: Unique session identifier
            vision_proctor: VisionProctor instance to get webcam frames from
            interval_min: Minimum seconds between captures
            interval_max: Maximum seconds between captures
        """
        self._backend_url   = backend_url.rstrip("/")
        self._nonce         = session_nonce
        self._vision        = vision_proctor
        self._shared_secret = _get_shared_secret()
        self._interval_min  = interval_min
        self._interval_max  = interval_max
        self._seq_id        = 0
        self._stop_event    = threading.Event()
        self._state_lock    = threading.RLock()
        self._buffer: deque = deque(maxlen=LOCAL_BUFFER_MAX)
        self._forbidden_backoff_until = 0.0
        self._forbidden_count = 0
        self._last_backoff_log_at = 0.0
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background uploader thread."""
        if not _MSS_AVAILABLE:
            print("[Snapshot] Cannot start: mss library not available")
            return
        if not _CV2_AVAILABLE:
            print("[Snapshot] Cannot start: opencv-python not available")
            return

        with self._state_lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run, name="SnapshotUploader", daemon=True
            )
            self._thread.start()
        print(f"[Snapshot] Uploader started (interval {self._interval_min}–{self._interval_max}s).")

    def stop(self) -> None:
        """Stop the uploader thread and flush remaining buffer."""
        self._stop_event.set()
        with self._state_lock:
            thread = self._thread

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5)

        with self._state_lock:
            if self._thread is thread and (thread is None or not thread.is_alive()):
                self._thread = None
        print("[Snapshot] Uploader stopped.")

    def _run(self) -> None:
        """Main capture/upload loop running in background thread."""
        while not self._stop_event.is_set():
            sleep = random.uniform(self._interval_min, self._interval_max)
            self._stop_event.wait(sleep)
            if self._stop_event.is_set():
                break
            self._capture_and_upload()
        
        # Best-effort flush of buffered payloads during shutdown.
        with self._state_lock:
            buffered_count = len(self._buffer)
        print(f"[Snapshot] Flushing {buffered_count} buffered frames...")
        attempts = 0
        while attempts < 3:
            with self._state_lock:
                if not self._buffer:
                    break
                payload = self._buffer.popleft()
            if not self._post_evidence(payload):
                with self._state_lock:
                    self._buffer.appendleft(payload)
                break
            attempts += 1

    def _capture_and_upload(self) -> None:
        """Capture screenshot + webcam frame and upload."""
        with self._state_lock:
            self._seq_id += 1
            seq_id = self._seq_id
        ts = time.time()
        with self._state_lock:
            in_forbidden_backoff = ts < self._forbidden_backoff_until

        # Capture evidence sources.
        screen_jpg  = _jpeg_compress(_capture_screenshot())
        
        webcam_arr  = None
        if self._vision and hasattr(self._vision, 'get_current_frame'):
            try:
                webcam_arr = self._vision.get_current_frame()
            except Exception as e:
                print(f"[Snapshot] Error getting webcam frame: {e}")
        
        webcam_jpg  = _jpeg_compress(webcam_arr) if webcam_arr is not None else None

        # Drain buffered payloads first (FIFO) when backoff is inactive.
        if not in_forbidden_backoff:
            while True:
                with self._state_lock:
                    if not self._buffer:
                        break
                    buffered = self._buffer.popleft()
                if not self._post_evidence(buffered):
                    with self._state_lock:
                        self._buffer.appendleft(buffered)
                    break   # Stop draining if server remains unavailable.

        # Build payload for current capture.
        payload = {
            "session_nonce": self._nonce,
            "sequence_id":   seq_id,
            "timestamp":     ts,
            "screen":        base64.b64encode(screen_jpg).decode() if screen_jpg else None,
            "webcam":        base64.b64encode(webcam_jpg).decode() if webcam_jpg else None,
        }

        if in_forbidden_backoff:
            with self._state_lock:
                self._buffer.append(payload)
                should_log = ts - self._last_backoff_log_at >= 10.0
                remaining = max(1, int(self._forbidden_backoff_until - ts))
                buffered = len(self._buffer)
                if should_log:
                    self._last_backoff_log_at = ts
            if should_log:
                print(
                    f"[Snapshot] Backoff active after HTTP 403 "
                    f"({remaining}s remaining) — buffering ({buffered}/{LOCAL_BUFFER_MAX})."
                )
            return

        # Upload newly captured payload.
        if not self._post_evidence(payload):
            with self._state_lock:
                self._buffer.append(payload)
                buffered = len(self._buffer)
            print(f"[Snapshot] Upload failed — buffered ({buffered}/{LOCAL_BUFFER_MAX}).")

    def _post_evidence(self, payload: dict) -> bool:
        """
        POST a single evidence payload to /v1/evidence.

        Returns True on HTTP 200/201.
        """
        try:
            body    = json.dumps(payload, default=str).encode("utf-8")
            headers = {
                "Content-Type":        "application/json",
                "User-Agent":          "ObserveProctorClient/2.0",
                "X-Observe-Signature": _sign(body, self._shared_secret),
            }
            req = urllib.request.Request(
                f"{self._backend_url}/v1/evidence",
                data=body,
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx()) as resp:
                success = resp.status in (200, 201)
                if success:
                    with self._state_lock:
                        self._forbidden_count = 0
                        self._forbidden_backoff_until = 0.0
                    print(f"[Snapshot] Uploaded seq={payload['sequence_id']} (HTTP {resp.status})")
                return success
        except urllib.error.HTTPError as e:
            if e.code == 403:
                with self._state_lock:
                    self._forbidden_count = min(self._forbidden_count + 1, 6)
                    forbidden_count = self._forbidden_count
                cooldown = min(
                    FORBIDDEN_BACKOFF_MAX,
                    FORBIDDEN_BACKOFF_BASE * (2 ** (forbidden_count - 1)),
                )
                with self._state_lock:
                    self._forbidden_backoff_until = time.time() + cooldown
                    self._last_backoff_log_at = 0.0
                print(
                    f"[Snapshot] HTTP 403 error: {e.reason} — "
                    f"pausing evidence retries for {int(cooldown)}s."
                )
            else:
                print(f"[Snapshot] HTTP {e.code} error: {e.reason}")
            return False
        except Exception as e:
            print(f"[Snapshot] POST error: {e}")
            return False

    def get_buffer_size(self) -> int:
        """Return number of buffered (failed) uploads."""
        with self._state_lock:
            return len(self._buffer)

    def is_running(self) -> bool:
        """Return True if uploader thread is running."""
        with self._state_lock:
            thread = self._thread
            return bool(thread and thread.is_alive())

