"""
Vision monitoring pipeline for face presence, liveness, and gaze behavior.

This module provides:
- Verified MediaPipe model preparation with SHA-256 integrity checks.
- Physical-camera selection heuristics to avoid virtual camera endpoints.
- Multi-layer liveness checks (EAR variance, blink count, blink entropy).
- Per-user gaze calibration to reduce false positives from posture variance.
- Safe camera and detector shutdown paths for robust lifecycle handling.

The runtime favors detection integrity and graceful degradation over best-effort
operation when model integrity or camera readiness cannot be verified.
"""

import hashlib
import math
import os
import platform
import sys
import threading
import time
import atexit
from collections import deque
from typing import Optional

import numpy as np

try:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    _CV_AVAILABLE = True
except ImportError:
    cv2 = None
    mp  = None
    _CV_AVAILABLE = False

# Import helper for PyInstaller bundles
try:
    from .mediapipe_helper import get_mediapipe_model_path
except ImportError:
    get_mediapipe_model_path = None

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

# SHA-256 of the official MediaPipe face_landmarker float16/v1 .task file.
# Update this if Google releases a new version.
MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
MODEL_URL    = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

# Known real USB camera vendor IDs.
REAL_CAMERA_VIDS = {
    "046d", "045e", "0bda", "04f2", "13d3", "04ca",
    "0408", "05ac", "1532", "0fd9", "054c", "04a9",
    "04b0", "04e8", "17ef", "8086", "05ca", "1e4e",
    "1b3f", "2b3e",
}

# Liveness thresholds.
EAR_BLINK_THRESHOLD  = 0.21     # EAR below this = blink frame
MIN_BLINKS_PER_WIN   = 2        # Require ≥ 2 blinks per observation window
ENTROPY_THRESHOLD    = 1.2      # bits — below = suspiciously periodic blinks

# Gaze calibration thresholds.
CALIB_SECONDS        = 30       # Seconds of neutral-pose data to collect
YAW_THRESHOLD        = 30.0     # Degrees from calibrated neutral
PITCH_THRESHOLD      = 25.0     # Degrees from calibrated neutral (downward)

# Shutdown timeout.
STOP_TIMEOUT_S       = 4.0

# Runtime throughput tuning.
# CPU stays conservative to avoid starving other monitors.
CPU_MAX_FPS          = 15
GPU_MAX_FPS          = 24
CPU_MIN_LOOP_SLEEP_S = 0.03
GPU_MIN_LOOP_SLEEP_S = 0.02


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _shannon_entropy(values: list) -> float:
    """Shannon entropy of a list of numeric values (binned to 0.1 resolution)."""
    if len(values) < 2:
        return 99.0   # Insufficient data — do not flag
    from collections import Counter
    binned  = [round(v, 1) for v in values]
    counts  = Counter(binned)
    total   = len(binned)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    return entropy


def _wmi_camera_name_at_index(index: int) -> str:
    """Return the WMI device name for an OpenCV camera index (Windows only)."""
    if platform.system() != "Windows":
        return ""
    try:
        import wmi
        c = wmi.WMI()
        cams = (
            list(c.Win32_PnPEntity(PNPClass="Image")) +
            list(c.Win32_PnPEntity(PNPClass="Camera"))
        )
        if index < len(cams):
            return (cams[index].Name or "").lower()
    except Exception:
        pass
    return ""


def _vid_from_wmi_name(name: str) -> Optional[str]:
    """Extract USB VID from a WMI device name / hardware ID string."""
    import re
    m = re.search(r"vid[_&]([0-9a-f]{4})", name, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _is_virtual_camera_index(index: int) -> bool:
    """
    Return True when camera index appears virtual based on WMI metadata.

    Uses virtual-keyword matching and optional VID allowlist validation.
    """
    name = _wmi_camera_name_at_index(index)
    if not name:
        return False   # Can't determine — allow

    VIRTUAL_KW = [
        "obs", "virtual", "snap camera", "xsplit", "manycam",
        "splitcam", "iriun", "droidcam", "epoccam",
    ]
    if any(kw in name for kw in VIRTUAL_KW):
        return True

    # If VID is available, require it to map to known physical camera vendors.
    vid = _vid_from_wmi_name(name)
    if vid is not None and vid not in REAL_CAMERA_VIDS:
        return True   # Unknown VID → treat as suspicious

    return False


def _find_physical_camera_index() -> int:
    """
    Probe camera indices and return the first verified physical camera.

    Skips virtual-camera candidates and requires a minimal working resolution.
    Falls back to index 0 when no physical candidate can be confirmed.
    """
    if not _CV_AVAILABLE:
        return 0

    backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
    for idx in range(10):
        if _is_virtual_camera_index(idx):
            print(f"[Vision] Skipping virtual camera at index {idx}.")
            continue
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                if w >= 320 and h >= 240:   # Reject software-only stubs.
                    print(f"[Vision] Selected physical camera at index {idx} ({w}x{h}).")
                    return idx
    print("[Vision] No confirmed physical camera found — defaulting to index 0.")
    return 0


class VisionProctor:
    # Global single-flight guard so concurrent instances do not race model prep.
    _model_init_lock = threading.Lock()

    def __init__(self, blink_buffer_secs: int = 15, fps: int = 15):
        self.is_available  = _CV_AVAILABLE
        self.buffer_size   = blink_buffer_secs * fps

        # Temporal buffers.
        self.ear_buffer    = deque(maxlen=self.buffer_size)
        self._blink_times: list[float] = []   # Blink event timestamps.
        self._in_blink     = False

        # Gaze-calibration state.
        self._calib_yaws:   list[float] = []
        self._calib_pitchs: list[float] = []
        self._calib_done    = False
        self._calib_start   = None
        self._neutral_yaw   = 0.0
        self._neutral_pitch = 0.0

        # Concurrency and lifecycle.
        self._is_running  = False
        self._stop_event  = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock        = threading.Lock()
        self._camera_io_lock = threading.Lock()
        self._cap_ref: Optional[object] = None   # Shared capture reference for forced release path.
        self.latest_frame = None
        self._frame_seq = 0
        self._requested_fps = int(fps or 15)
        self._gpu_accel_enabled = False
        self._delegate_used = "cpu"
        self._detector_closed = False

        # Light backpressure to keep inference from saturating CPU.
        self._configure_runtime_limits(self._requested_fps)

        # Telemetry snapshot.
        self.current_flags: list[str] = []
        self.current_stats  = {"face_count": 0, "ear": 0.0,
                                "pitch_deg": 0.0, "yaw_deg": 0.0}

        # Evidence buffer (warning-triggered frame capture).
        self._evidence_buffer = None
        self._last_flagged_warning: set[str] = set()  # Track warnings we've triggered evidence for

        if self.is_available:
            # Serialize model preparation and detector construction across instances.
            with VisionProctor._model_init_lock:
                self._ensure_model_exists()
                model_path = self._get_model_path()
                if os.path.exists(model_path):
                    try:
                        self.detector = self._create_face_landmarker(model_path)
                    except Exception as e:
                        # MediaPipe resource loading can fail in bundled runtimes.
                        print(f"[Vision] Error loading model from {model_path}: {e}")
                        print("[Vision] This may be a PyInstaller resource loading issue.")
                        print("[Vision] Vision proctoring disabled.")
                        self.is_available = False
                else:
                    print(f"[Vision] Model path does not exist: {model_path}")
                    print("[Vision] Vision proctoring disabled.")
                    self.is_available = False

            # Ensure MediaPipe resources are released before interpreter teardown.
            atexit.register(self._safe_close_detector)

    def _configure_runtime_limits(self, requested_fps: int) -> None:
        """
        Configure processing cadence based on active delegate.
        GPU mode runs slightly faster detection while CPU stays conservative.
        """
        max_fps = GPU_MAX_FPS if self._gpu_accel_enabled else CPU_MAX_FPS
        min_sleep = GPU_MIN_LOOP_SLEEP_S if self._gpu_accel_enabled else CPU_MIN_LOOP_SLEEP_S

        target_fps = max(5, min(int(requested_fps or 0), max_fps))
        self._loop_sleep_s = max(min_sleep, 1.0 / float(target_fps))

        if self._gpu_accel_enabled:
            # GPU path can process every frame for slightly faster detection.
            self._process_every_n = 1
        else:
            # CPU path skips alternate frames at higher requested FPS.
            self._process_every_n = 2 if target_fps >= 10 else 1

    def _create_face_landmarker(self, model_path: str):
        """
        Prefer GPU delegate if supported; fall back to CPU automatically.
        """
        gpu_error = ""
        base_delegate = getattr(python.BaseOptions, "Delegate", None)
        gpu_delegate = getattr(base_delegate, "GPU", None) if base_delegate else None
        cpu_delegate = getattr(base_delegate, "CPU", None) if base_delegate else None

        # Attempt GPU first when the runtime exposes a GPU delegate.
        if gpu_delegate is not None:
            try:
                base_options = python.BaseOptions(
                    model_asset_path=model_path,
                    delegate=gpu_delegate,
                )
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=True,
                    output_facial_transformation_matrixes=True,
                    num_faces=2,
                )
                detector = vision.FaceLandmarker.create_from_options(options)
                self._gpu_accel_enabled = True
                self._delegate_used = "gpu"
                self._configure_runtime_limits(self._requested_fps)
                print("[Vision] FaceLandmarker initialized with GPU delegate.")
                return detector
            except Exception as e:
                gpu_error = str(e)

        # CPU fallback path (always attempted).
        try:
            if cpu_delegate is not None:
                base_options = python.BaseOptions(
                    model_asset_path=model_path,
                    delegate=cpu_delegate,
                )
            else:
                base_options = python.BaseOptions(model_asset_path=model_path)

            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                num_faces=2,
            )
            detector = vision.FaceLandmarker.create_from_options(options)
            self._gpu_accel_enabled = False
            self._delegate_used = "cpu"
            self._configure_runtime_limits(self._requested_fps)

            if gpu_error:
                print(f"[Vision] GPU delegate unavailable, using CPU fallback: {gpu_error}")
            else:
                print("[Vision] FaceLandmarker initialized with CPU delegate.")
            return detector
        except Exception as e:
            if gpu_error:
                raise RuntimeError(f"GPU init failed ({gpu_error}); CPU init failed ({e})") from e
            raise

    def _get_model_path(self) -> str:
        name = "face_landmarker.task"
        if getattr(sys, "frozen", False):
            p = os.path.join(sys._MEIPASS, name)
            if os.path.exists(p):
                return p
        for base in (os.getcwd(),
                     os.path.dirname(os.path.dirname(os.path.dirname(
                         os.path.abspath(__file__))))):
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
        return os.path.join(os.getcwd(), name)

    def _ensure_model_exists(self):
        """Ensure model file exists and passes SHA-256 integrity verification."""
        model_path = self._get_model_path()
        if os.path.exists(model_path):
            digest = _sha256_file(model_path)
            if MODEL_SHA256 and not _sha256_compare(digest, MODEL_SHA256):
                print(
                    f"[Vision] CRITICAL: model hash mismatch "
                    f"(expected {MODEL_SHA256[:16]}... got {digest[:16]}...). "
                    "Deleting and re-downloading."
                )
                os.remove(model_path)
            else:
                print(f"[Vision] Model hash OK ({digest[:16]}...).")
                return

        print("[Vision] Downloading MediaPipe Face Landmarker model (~2 MB)...")
        try:
            tmp_path = model_path + ".tmp"
            urllib.request.urlretrieve(MODEL_URL, tmp_path)

            digest = _sha256_file(tmp_path)
            if MODEL_SHA256 and not _sha256_compare(digest, MODEL_SHA256):
                os.remove(tmp_path)
                print(
                    f"[Vision] Downloaded model FAILED hash check "
                    f"(got {digest[:16]}...). Possible MITM. "
                    "Vision proctoring disabled."
                )
                self.is_available = False
                return

            os.replace(tmp_path, model_path)
            print(f"[Vision] Model downloaded and verified ({digest[:16]}...).")
        except Exception as e:
            print(f"[Vision] Failed to download model: {e}")
            self.is_available = False

    def _calculate_ear(self, eye_pts, w: int, h: int) -> float:
        def px(lm): return lm.x * w, lm.y * h
        p2_p6 = math.dist(px(eye_pts[1]), px(eye_pts[5]))
        p3_p5 = math.dist(px(eye_pts[2]), px(eye_pts[4]))
        p1_p4 = math.dist(px(eye_pts[0]), px(eye_pts[3]))
        return (p2_p6 + p3_p5) / (2.0 * p1_p4) if p1_p4 else 0.0

    def _get_head_pose_degrees(self, landmarks, w: int, h: int):
        model_pts = np.array([
            (0.0,    0.0,    0.0),
            (0.0,  -330.0, -65.0),
            (-225.0, 170.0, -135.0),
            (225.0, 170.0, -135.0),
            (-150.0, -150.0, -125.0),
            (150.0, -150.0, -125.0),
        ], dtype="double")
        image_pts = np.array([
            (landmarks[1].x * w,   landmarks[1].y * h),
            (landmarks[152].x * w, landmarks[152].y * h),
            (landmarks[33].x * w,  landmarks[33].y * h),
            (landmarks[263].x * w, landmarks[263].y * h),
            (landmarks[61].x * w,  landmarks[61].y * h),
            (landmarks[291].x * w, landmarks[291].y * h),
        ], dtype="double")
        cam_mat   = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]], dtype="double")
        ok, rvec, _ = cv2.solvePnP(model_pts, image_pts, cam_mat, np.zeros((4, 1)))
        if not ok:
            return 0.0, 0.0, 0.0
        rmat, _ = cv2.Rodrigues(rvec)
        angles, *_ = cv2.RQDecomp3x3(rmat)
        return float(angles[0]), float(angles[1]), float(angles[2])

    def _check_liveness(self, ear: float, now: float) -> list[str]:
        flags = []
        # Layer A: track blink events.
        if ear < EAR_BLINK_THRESHOLD:
            if not self._in_blink:
                self._in_blink = True
                self._blink_times.append(now)
        else:
            self._in_blink = False

        # Prune blink timestamps outside observation window.
        window = self.buffer_size / 15.0   # seconds
        self._blink_times = [t for t in self._blink_times if now - t <= window]

        if len(self.ear_buffer) < self.buffer_size:
            return flags   # Not enough data yet.

        # Layer B: EAR variance.
        std_dev = float(np.std(self.ear_buffer))
        if std_dev < 0.005:
            flags.append(
                f"Liveness: EAR flatline (std={std_dev:.4f}) — static photo detected."
            )
            return flags   # No value in later checks for static image signal.

        # Layer C: blink count requirement.
        blink_count = len(self._blink_times)
        if blink_count < MIN_BLINKS_PER_WIN:
            flags.append(
                f"Liveness: Only {blink_count} blink(s) in {window:.0f}s window "
                f"(require ≥ {MIN_BLINKS_PER_WIN}) — possible unblinking video loop."
            )

        # Layer D: blink interval entropy.
        if len(self._blink_times) >= 4:
            intervals = [
                self._blink_times[i + 1] - self._blink_times[i]
                for i in range(len(self._blink_times) - 1)
            ]
            ent = _shannon_entropy(intervals)
            if ent < ENTROPY_THRESHOLD:
                flags.append(
                    f"Liveness: Blink intervals suspiciously periodic "
                    f"(entropy={ent:.2f} bits < {ENTROPY_THRESHOLD}) — "
                    "possible video loop with repeated blinks."
                )

        return flags

    def _check_gaze(self, pitch: float, yaw: float, now: float) -> list[str]:
        flags = []
        if not self._calib_done:
            if self._calib_start is None:
                self._calib_start = now
                print("[Vision] Gaze calibration started (30 s neutral pose).")
            self._calib_yaws.append(yaw)
            self._calib_pitchs.append(pitch)
            if now - self._calib_start >= CALIB_SECONDS:
                self._neutral_yaw   = float(np.median(self._calib_yaws))
                self._neutral_pitch = float(np.median(self._calib_pitchs))
                self._calib_done    = True
                print(
                    f"[Vision] Calibration done — neutral yaw={self._neutral_yaw:.1f}° "
                    f"pitch={self._neutral_pitch:.1f}°"
                )
            return flags   # No alerts during calibration.

        rel_yaw   = yaw   - self._neutral_yaw
        rel_pitch = pitch - self._neutral_pitch
        if abs(rel_yaw) > YAW_THRESHOLD:
            flags.append(
                f"Gaze: Looking away horizontally "
                f"(Δyaw={rel_yaw:+.1f}°, neutral={self._neutral_yaw:.1f}°)"
            )
        if rel_pitch < -PITCH_THRESHOLD:
            flags.append(
                f"Gaze: Looking down "
                f"(Δpitch={rel_pitch:+.1f}°, neutral={self._neutral_pitch:.1f}°)"
            )
        return flags

    def _vision_loop(self):
        """Main vision loop with camera reconnect and detector inference."""
        camera_index = _find_physical_camera_index()
        backend      = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
        cap          = None

        while self._is_running and not self._stop_event.is_set():
            # Camera open/reconnect path.
            if cap is None or not cap.isOpened():
                if cap is not None:
                    with self._camera_io_lock:
                        cap.release()
                with self._camera_io_lock:
                    cap = cv2.VideoCapture(camera_index, backend)
                with self._lock:
                    self._cap_ref = cap   # Expose for emergency release path.
                if not cap.isOpened():
                    with self._lock:
                        self.current_flags = ["Camera unavailable — check webcam."]
                    self._stop_event.wait(2.0)
                    continue

            with self._camera_io_lock:
                ret, frame = cap.read()
            if not ret or frame is None:
                with self._camera_io_lock:
                    cap.release()
                cap = None
                with self._lock:
                    self._cap_ref = None
                self._stop_event.wait(0.5)
                continue

            self._frame_seq += 1
            if self._process_every_n > 1 and (self._frame_seq % self._process_every_n) != 0:
                self._stop_event.wait(self._loop_sleep_s)
                continue

            h, w = frame.shape[:2]
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            with self._lock:
                self.latest_frame = rgb.copy()

            try:
                mp_img  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result  = self.detector.detect(mp_img)
            except Exception:
                self._stop_event.wait(0.1)
                continue

            now   = time.monotonic()
            flags: list[str] = []

            with self._lock:
                if not result.face_landmarks:
                    flags.append("No face detected — user absent.")
                    self.current_stats["face_count"] = 0
                else:
                    fc = len(result.face_landmarks)
                    self.current_stats["face_count"] = fc
                    if fc > 1:
                        flags.append(f"Multiple faces detected ({fc}).")
                    else:
                        face = result.face_landmarks[0]
                        eye  = [face[i] for i in [33, 160, 158, 133, 153, 144]]
                        ear  = self._calculate_ear(eye, w, h)
                        self.ear_buffer.append(ear)
                        self.current_stats["ear"] = ear

                        # Multi-layer liveness checks.
                        flags.extend(self._check_liveness(ear, now))

                        # Calibrated gaze checks.
                        try:
                            pitch, yaw, _ = self._get_head_pose_degrees(face, w, h)
                            self.current_stats["pitch_deg"] = pitch
                            self.current_stats["yaw_deg"]   = yaw
                            flags.extend(self._check_gaze(pitch, yaw, now))
                        except Exception:
                            pass

                self.current_flags = flags

                # Feed frame to evidence buffer for warning-triggered capture.
                if self._evidence_buffer is not None:
                    # Evidence buffer performs its own defensive copy.
                    self._evidence_buffer.add_frame(rgb, time.time())

            # Trigger evidence capture for newly observed warning transitions.
            self._trigger_evidence_if_warning()

            self._stop_event.wait(self._loop_sleep_s)

        # Clean shutdown.
        if cap is not None and cap.isOpened():
            with self._camera_io_lock:
                cap.release()
        with self._lock:
            self._cap_ref = None
        print("[Vision] Camera released.")

    def start_monitoring(self):
        with self._lock:
            detector_ready = hasattr(self, "detector") and self.detector is not None
            if not self.is_available or self._is_running or not detector_ready:
                if self.is_available and not detector_ready:
                    self.current_flags = [
                        "VisionProctor unavailable: detector not initialized."
                    ]
                return
            self._is_running = True
            self._stop_event.clear()
            # Reset warning transition tracking for fresh monitoring session.
            self._last_flagged_warning = set()
            worker = threading.Thread(
                target=self._vision_loop, daemon=True, name="VisionProctor"
            )
            self._thread = worker
        worker.start()
        print("[Vision] Continuous temporal stream started.")

    def stop_monitoring(self):
        """Stop vision thread and force-release camera if shutdown hangs."""
        with self._lock:
            thread = self._thread
            self._thread = None
            self._is_running = False
            self._stop_event.set()

        if thread and thread is not threading.current_thread():
            thread.join(timeout=STOP_TIMEOUT_S)
            if thread.is_alive():
                # Thread appears hung; force-release capture object.
                with self._lock:
                    cap = self._cap_ref
                    self._cap_ref = None
                if cap is not None:
                    try:
                        with self._camera_io_lock:
                            cap.release()
                        print("[Vision] Forcibly released hung camera.")
                    except Exception:
                        pass

    def _safe_close_detector(self):
        """Best-effort explicit MediaPipe detector close for clean process shutdown."""
        with self._lock:
            if self._detector_closed:
                return
        try:
            self.stop_monitoring()
        except Exception:
            pass

        detector = None
        with self._lock:
            detector = getattr(self, "detector", None)
            self.detector = None

        if detector is not None:
            try:
                close_fn = getattr(detector, "close", None)
                if callable(close_fn):
                    close_fn()
            except Exception:
                pass

        with self._lock:
            self._detector_closed = True

    def set_evidence_buffer(self, evidence_buffer):
        """Wire evidence buffer for warning-triggered frame capture."""
        with self._lock:
            self._evidence_buffer = evidence_buffer

    def _trigger_evidence_if_warning(self):
        """Check if new warnings were detected and trigger evidence capture."""
        with self._lock:
            if not self._evidence_buffer:
                return

            current_flags_set = set(self.current_flags)
            new_warnings = current_flags_set - self._last_flagged_warning

            if new_warnings:
                for warning in new_warnings:
                    print(f"[Vision] 🎥 Triggering evidence capture for: {warning}")
                    self._evidence_buffer.trigger_warning(
                        warning_text=warning,
                        vision_stats=dict(self.current_stats)
                    )

            # Always refresh baseline so warnings can retrigger after they clear.
            self._last_flagged_warning = current_flags_set

    def get_latest_telemetry(self) -> dict:
        if not self.is_available:
            return {
                "detected": False,
                "flags":    ["VisionProctor: mediapipe/opencv not available."],
                "stats":    self.current_stats,
                "inference_delegate": self._delegate_used,
            }
        with self._lock:
            return {
                "detected": len(self.current_flags) > 0,
                "flags":    list(self.current_flags),
                "stats":    dict(self.current_stats),
                "inference_delegate": self._delegate_used,
            }

    def get_current_frame(self):
        if not self.is_available:
            return None
        with self._lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None


def _sha256_compare(a: str, b: str) -> bool:
    """Constant-time compare of two hex digests."""
    import hmac as _hmac
    return _hmac.compare_digest(a.lower(), b.lower())
