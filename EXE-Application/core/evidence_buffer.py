"""Warning-triggered evidence capture with bounded buffering and upload.

The buffer continuously stores recent vision frames. When a warning event is
triggered, the component captures both pre-event and post-event context,
packages metadata, signs the payload, and uploads evidence to the backend.

Design goals:
- Maintain low latency in the vision loop.
- Limit memory growth under warning bursts.
- Preserve enough temporal context for audit and review.
"""

import base64
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.error
from collections import deque
from typing import Callable, Optional, Any
import cv2
import numpy as np


try:
    import mss  # type: ignore[import-not-found]
    _MSS_AVAILABLE = True
except Exception:
    mss = None
    _MSS_AVAILABLE = False

# Evidence capture configuration

BUFFER_SIZE_FRAMES = 30           # Keep last 30 frames (before + after + buffer)
FRAMES_BEFORE = 10                # Capture 10 frames before warning
FRAMES_AFTER = 10                 # Capture 10 frames after warning
JPEG_QUALITY = 38                 # JPEG compression quality
MAX_DIMENSION = 960               # Resize to fit max dimension
MAX_PENDING_WARNINGS = 20         # Bound queued warnings to avoid unbounded memory growth
MIN_WARNING_CAPTURE_INTERVAL_SEC = 0.75  # Throttle burst warning capture dispatch


def _get_shared_secret() -> bytes:
    """Return HMAC signing secret from environment configuration."""
    secret = (os.environ.get("OBSERVE_PROCTOR_SECRET") or "").strip()
    if not secret:
        print("[EvidenceBuffer] ⚠ WARNING: OBSERVE_PROCTOR_SECRET not set, signature verification will fail!")
        secret = "dev-shared-secret-change-me"  # Fallback for testing
    return secret.encode("utf-8")


def _sign(payload: bytes) -> str:
    """Return hexadecimal HMAC-SHA256 signature for payload bytes."""
    return hmac.new(_get_shared_secret(), payload, hashlib.sha256).hexdigest()


def _jpeg_compress(arr: np.ndarray, quality: int = JPEG_QUALITY,
                   max_dim: int = MAX_DIMENSION) -> Optional[bytes]:
    """Compress an RGB frame to JPEG bytes.

    The frame is resized proportionally when its largest side exceeds max_dim.
    Returns None when compression fails.
    """
    if arr is None or arr.size == 0:
        return None
    try:
        h, w = arr.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            arr = cv2.resize(arr, (int(w * scale), int(h * scale)),
                            interpolation=cv2.INTER_AREA)
        # Convert RGB → BGR for OpenCV
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes() if ok else None
    except Exception as e:
        print(f"[EvidenceBuffer] JPEG compression failed: {e}")
        return None


def _capture_display_jpeg(quality: int = 30, max_width: int = 960) -> Optional[bytes]:
    """Capture a primary-display screenshot encoded as JPEG.

    Returns None when screen capture is unavailable or fails.
    """
    try:
        if not _MSS_AVAILABLE:
            return None

        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            raw = sct.grab(monitor)

        # mss returns BGRA; drop alpha and keep BGR for OpenCV encoding.
        bgr = np.array(raw)[:, :, :3]
        if bgr.size == 0:
            return None

        h, w = bgr.shape[:2]
        if w > max_width and w > 0:
            scale = max_width / float(w)
            bgr = cv2.resize(bgr, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)

        ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
        return buf.tobytes() if ok else None
    except Exception:
        return None


class EvidenceFrameBuffer:
    """
    Maintain recent frames and orchestrate warning-triggered evidence uploads.

    Capture flow:
    1) Keep a rolling frame buffer.
    2) On warning, snapshot pre-warning frames and begin collecting post-warning frames.
    3) Build payload asynchronously and upload without blocking vision processing.
    """

    def __init__(self,
                 backend_url: str,
                 session_nonce: str,
                 max_frames: int = BUFFER_SIZE_FRAMES,
                 upload_callback: Optional[Callable[[dict], None]] = None):
        """
        Args:
            backend_url: Base API URL used for evidence POST requests.
            session_nonce: Unique identifier for the active exam session.
            max_frames: Maximum number of in-memory rolling frames.
            upload_callback: Optional callback for custom upload transport.
        """
        self._backend_url = backend_url.rstrip("/")
        self._session_nonce = session_nonce
        self._max_frames = max_frames
        self._upload_callback = upload_callback

        # Circular buffer entries are stored as (frame_rgb, timestamp).
        self._frame_buffer: deque = deque(maxlen=max_frames)
        self._lock = threading.RLock()
        self._capture_in_progress = False
        self._frames_after_warning: int = 0
        self._pending_warning_queue: deque = deque(maxlen=MAX_PENDING_WARNINGS)
        self._pending_upload: dict[str, Any] = {}
        self._upload_worker_lock = threading.Lock()
        self._upload_thread: threading.Thread | None = None
        self._queued_upload_job: dict[str, Any] | None = None
        self._last_capture_dispatch_ts = 0.0

        # Session metadata attached to each evidence payload.
        self._session_metadata = {
            "username": "",
            "testid": "",
            "sectionid": "",
        }

    def set_session_metadata(self, username: str, testid: str, sectionid: str):
        """Set session metadata fields included in future payloads."""
        with self._lock:
            self._session_metadata.update({
                "username": str(username or ""),
                "testid": str(testid or ""),
                "sectionid": str(sectionid or ""),
            })

    def add_frame(self, frame_rgb: np.ndarray, timestamp: Optional[float] = None):
        """
        Add a frame to the circular buffer.

        Args:
            frame_rgb: RGB numpy array (uint8)
            timestamp: Frame timestamp (default: current time)
        """
        if frame_rgb is None or frame_rgb.size == 0:
            return

        if timestamp is None:
            timestamp = time.time()

        pending_upload = None
        frames_snapshot = None

        with self._lock:
            self._frame_buffer.append((frame_rgb.copy(), timestamp))
            # During post-warning collection, count incoming frames until enough
            # context is available to dispatch the upload job.
            if self._capture_in_progress:
                self._frames_after_warning += 1
                if self._frames_after_warning >= FRAMES_AFTER:
                    # Snapshot mutable state while locked; process/upload outside
                    # the lock to avoid blocking producers.
                    self._capture_in_progress = False
                    pending_upload = dict(getattr(self, "_pending_upload", {}) or {})
                    frames_snapshot = list(self._frame_buffer)

        if pending_upload and frames_snapshot is not None:
            self._schedule_upload_async(pending_upload, frames_snapshot)

    def trigger_warning(self, warning_text: str, vision_stats: dict):
        """
        Begin evidence capture for a warning emitted by vision analysis.

        The current ring buffer is snapshotted as pre-warning context, then the
        next FRAMES_AFTER frames are collected before dispatching upload work.

        Args:
            warning_text: Description of the warning
            vision_stats: Current vision stats (face_count, ear, pitch, yaw)
        """
        warning_payload = {
            "frames_before": [],
            "warning_text": warning_text,
            "vision_stats": vision_stats,
            "trigger_time": time.time(),
        }

        with self._lock:
            now = time.time()
            if now - self._last_capture_dispatch_ts < MIN_WARNING_CAPTURE_INTERVAL_SEC:
                # Throttle high-frequency warning bursts to reduce repeated
                # compression and upload pressure.
                return

            warning_payload["frames_before"] = list(self._frame_buffer)

            if self._capture_in_progress:
                dropped = None
                if len(self._pending_warning_queue) >= MAX_PENDING_WARNINGS:
                    dropped = self._pending_warning_queue.popleft()
                self._pending_warning_queue.append(warning_payload)
                print(
                    f"[EvidenceBuffer] ⏳ Warning queued while capture in progress: {warning_text} "
                    f"(queue={len(self._pending_warning_queue)})"
                )
                if dropped:
                    print(
                        "[EvidenceBuffer] ⚠ Pending warning queue full; "
                        f"dropped oldest warning: {str(dropped.get('warning_text', ''))[:80]}"
                    )
                return

            self._capture_in_progress = True
            self._frames_after_warning = 0
            self._pending_upload = warning_payload
            self._last_capture_dispatch_ts = now

            print(
                f"[EvidenceBuffer] ⚠ Warning triggered: {warning_text}\n"
                f"  Buffered frames before: {len(warning_payload['frames_before'])}\n"
                f"  Waiting for {FRAMES_AFTER} frames after warning..."
            )

    def _schedule_upload_async(self, pending: dict, frames_snapshot: list):
        """
        Schedule asynchronous payload building/upload after capture completion.

        This method executes outside the frame-buffer lock to keep frame ingest
        responsive while heavier encoding/network work is offloaded.
        """
        if not pending:
            return

        frames_before = pending.get("frames_before", [])
        warning_text = pending.get("warning_text", "")
        vision_stats = pending.get("vision_stats", {})
        trigger_time = pending.get("trigger_time", time.time())

        # Keep only the configured evidence window around the trigger.
        frames_before = frames_before[-FRAMES_BEFORE:]

        # Post-warning frames are read from the captured add_frame snapshot.
        frames_after = list(frames_snapshot)[-FRAMES_AFTER:]

        # Capture additional display screenshots to complement camera frames.
        display_frames = []
        trigger_display = _capture_display_jpeg()
        if trigger_display:
            display_frames.append({
                "sequence": 0,
                "phase": "trigger",
                "timestamp": trigger_time,
                "jpeg_b64": base64.b64encode(trigger_display).decode(),
            })
        after_display = _capture_display_jpeg()
        if after_display:
            display_frames.append({
                "sequence": 1,
                "phase": "after",
                "timestamp": time.time(),
                "jpeg_b64": base64.b64encode(after_display).decode(),
            })

        print(
            f"[EvidenceBuffer] ✔ Evidence capture complete:\n"
            f"  Frames before: {len(frames_before)}\n"
            f"  Frames after: {len(frames_after)}\n"
            f"  Total frames: {len(frames_before) + len(frames_after)}"
        )

        # Queue heavy payload build/upload on a dedicated worker thread.
        self._dispatch_upload_job(
            {
                "kind": "capture",
                "frames_before": frames_before,
                "frames_after": frames_after,
                "display_frames": display_frames,
                "warning_text": warning_text,
                "vision_stats": vision_stats,
                "trigger_time": trigger_time,
            }
        )

        self._start_next_queued_capture()

    def _dispatch_upload_job(self, job: dict) -> None:
        """Dispatch upload work on a single worker thread.

        If a worker is already active, only the most recent queued job is
        retained to bound backlog growth.
        """
        with self._upload_worker_lock:
            thread = self._upload_thread
            if thread is not None and thread.is_alive():
                self._queued_upload_job = dict(job)
                return

            worker = threading.Thread(
                target=self._upload_worker_loop,
                args=(dict(job),),
                daemon=True,
                name="EvidenceUpload"
            )
            self._upload_thread = worker
        worker.start()

    def _upload_worker_loop(self, first_job: dict) -> None:
        job = dict(first_job)
        while job:
            payload = None
            if job.get("kind") == "capture":
                payload = self._build_evidence_payload(
                    job.get("frames_before", []),
                    job.get("frames_after", []),
                    job.get("display_frames", []),
                    str(job.get("warning_text") or ""),
                    dict(job.get("vision_stats") or {}),
                    float(job.get("trigger_time") or time.time()),
                )
            elif job.get("kind") == "payload":
                payload = dict(job.get("payload") or {})

            if payload:
                if self._upload_callback:
                    try:
                        self._upload_callback(payload)
                    except Exception as e:
                        print(f"[EvidenceBuffer] Upload callback failed: {e}")
                else:
                    self._post_evidence_sync(payload)

            with self._upload_worker_lock:
                next_job = self._queued_upload_job
                self._queued_upload_job = None
                if next_job is None:
                    self._upload_thread = None
                    return

            job = dict(next_job)

    def _start_next_queued_capture(self):
        """Start the next queued warning capture, if any are waiting."""
        with self._lock:
            if self._capture_in_progress:
                return
            if not self._pending_warning_queue:
                return

            next_warning = self._pending_warning_queue.popleft()
            remaining = len(self._pending_warning_queue)
            self._capture_in_progress = True
            self._frames_after_warning = 0
            self._pending_upload = next_warning

        print(
            f"[EvidenceBuffer] ▶ Starting queued warning capture: {next_warning.get('warning_text', '')} "
            f"(remaining_queue={remaining})"
        )

    def _build_evidence_payload(self, frames_before: list, frames_after: list,
                               display_frames: list,
                               warning_text: str, vision_stats: dict,
                               trigger_time: float) -> dict:
        """Convert captured frames and metadata into API payload format."""
        encoded_frames = []

        for idx, (frame_arr, ts) in enumerate(frames_before):
            jpeg_bytes = _jpeg_compress(frame_arr)
            if jpeg_bytes:
                encoded_frames.append({
                    "sequence": idx,
                    "phase": "before",
                    "timestamp": ts,
                    "jpeg_b64": base64.b64encode(jpeg_bytes).decode(),
                })

        for idx, (frame_arr, ts) in enumerate(frames_after):
            jpeg_bytes = _jpeg_compress(frame_arr)
            if jpeg_bytes:
                encoded_frames.append({
                    "sequence": len(frames_before) + idx,
                    "phase": "after",
                    "timestamp": ts,
                    "jpeg_b64": base64.b64encode(jpeg_bytes).decode(),
                })
        with self._lock:
            metadata = dict(self._session_metadata)

        return {
            "session_nonce": self._session_nonce,
            "session_id": self._session_nonce,
            "username": metadata.get("username", ""),
            "email": metadata.get("username", ""),
            "testid": metadata.get("testid", ""),
            "test_id": metadata.get("testid", ""),
            "sectionid": metadata.get("sectionid", ""),
            "section_id": metadata.get("sectionid", ""),
            "trigger_time": trigger_time,
            "warning_text": warning_text,
            "vision_stats": vision_stats,
            "frames": encoded_frames,
            "frame_count": len(encoded_frames),
            "display_frames": display_frames,
            "display_frame_count": len(display_frames),
        }

    def _build_reduced_payload(self, payload: dict) -> dict:
        """Build a reduced payload variant for HTTP 413 retry handling."""
        shrunk = dict(payload)
        frames = list(payload.get("frames") or [])

        # Downsample and cap frame count to reduce body size.
        reduced_frames = frames[::2]
        if len(reduced_frames) > 10:
            reduced_frames = reduced_frames[:10]

        shrunk["frames"] = reduced_frames
        shrunk["frame_count"] = len(reduced_frames)
        shrunk["display_frames"] = []
        shrunk["display_frame_count"] = 0
        return shrunk

    def _post_evidence_sync(self, payload: dict) -> bool:
        """POST evidence payload to the backend with one reduced-size retry.

        When the server rejects the payload as too large (HTTP 413), this
        method retries once using _build_reduced_payload.
        """
        def _send_once(data: dict) -> bool:
            body = json.dumps(data, default=str).encode("utf-8")
            signature = _sign(body)

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ObserveProctor/2.0",
                "X-Observe-Signature": signature,
            }

            url = f"{self._backend_url}/v1/evidence/save-frames"

            # Runtime diagnostics for evidence transport.
            print(f"[EvidenceBuffer] 📤 Sending {data.get('frame_count')} frames to {url}")
            print(f"[EvidenceBuffer]   Session: {self._session_nonce[:16]}...")
            print(f"[EvidenceBuffer]   Signature: {signature[:16]}...")
            print(f"[EvidenceBuffer]   Body size: {len(body)} bytes")

            import urllib.request
            import ssl

            # Configure strict TLS defaults when the endpoint is HTTPS.
            ctx = None
            if url.startswith("https://"):
                ctx = ssl.create_default_context()
                ctx.verify_mode = ssl.CERT_REQUIRED
                ctx.check_hostname = True
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2

            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                if resp.status in (200, 201):
                    print(f"[EvidenceBuffer] ✔ Evidence uploaded ({data.get('frame_count')} frames)")
                    return True
                error_resp = resp.read().decode("utf-8", errors="ignore")
                print(f"[EvidenceBuffer] ❌ Upload failed (HTTP {resp.status}): {error_resp[:200]}")
                return False

        try:
            return _send_once(payload)
        except urllib.error.HTTPError as e:
            if int(getattr(e, "code", 0)) == 413:
                print("[EvidenceBuffer] ⚠ Upload rejected (413). Retrying with reduced payload...")
                try:
                    return _send_once(self._build_reduced_payload(payload))
                except Exception as retry_exc:
                    print(f"[EvidenceBuffer] ❌ Reduced retry failed: {type(retry_exc).__name__}: {retry_exc}")
                    return False
            print(f"[EvidenceBuffer] ❌ Upload error: HTTPError: {e}")
            return False
        except Exception as e:
            import traceback
            print(f"[EvidenceBuffer] ❌ Upload error: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

