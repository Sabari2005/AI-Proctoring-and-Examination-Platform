"""Audio-based proctoring using adaptive RMS and spectral heuristics.

The monitor combines three layers of analysis:
1) Session calibration to derive an environment-specific RMS threshold.
2) Spectral speech-band ratio checks for high-energy chunks.
3) Whisper-oriented centroid/flatness checks for low-amplitude activity.

If audio capture cannot start, telemetry reports a critical condition so
exam orchestration can block the session.
"""

import threading
import time
from collections import deque

import numpy as np

try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    sd = None
    _SD_AVAILABLE = False


# Detection constants
CALIB_SECONDS        = 8          # Duration of startup ambient-noise calibration.
THRESHOLD_MULTIPLIER = 3.0        # RMS alert threshold = baseline RMS * multiplier.
HARD_MIN_THRESHOLD   = 0.004      # Lower clamp to avoid over-sensitivity.
HARD_MAX_THRESHOLD   = 0.045      # Upper clamp to avoid suppressing real speech.

SPEECH_LOW_HZ        = 85         # Lower bound of speech-focused frequency band.
SPEECH_HIGH_HZ       = 3500       # Upper bound of speech-focused frequency band.
SPEECH_RATIO_THRESH  = 0.55       # Minimum in-band energy ratio to classify speech-like audio.

WHISPER_CENTROID_LOW  = 1500      # Whisper candidate centroid lower bound (Hz).
WHISPER_CENTROID_HIGH = 4500      # Whisper candidate centroid upper bound (Hz).
WHISPER_FLATNESS_MIN  = 0.12      # Whisper-like spectral flatness lower bound.
WHISPER_FLATNESS_MAX  = 0.65      # Whisper-like spectral flatness upper bound.

SUSTAINED_RATIO      = 0.5        # Minimum high-RMS fraction across the rolling window.
SAMPLERATE           = 16000
BLOCKS_PER_SEC       = 10         # 100 ms chunks
BUFFER_SECONDS       = 3.0


# Spectral helpers

def _speech_energy_ratio(chunk: np.ndarray, samplerate: int) -> float:
    """
    Return the fraction of spectral energy within the speech band.

    Higher values indicate that dominant energy is concentrated in
    human-voice frequencies rather than broad ambient noise.
    """
    n      = len(chunk)
    fft    = np.abs(np.fft.rfft(chunk, n=n))
    freqs  = np.fft.rfftfreq(n, d=1.0 / samplerate)
    total  = np.sum(fft ** 2) + 1e-12
    speech = np.sum(fft[(freqs >= SPEECH_LOW_HZ) & (freqs <= SPEECH_HIGH_HZ)] ** 2)
    return float(speech / total)


def _spectral_centroid(chunk: np.ndarray, samplerate: int) -> float:
    """
    Compute frequency-weighted spectral centroid in Hz.

    The centroid is used as one whisper heuristic: quiet ambient signals tend
    to concentrate at lower frequencies than aspirated speech-like content.
    """
    n     = len(chunk)
    fft   = np.abs(np.fft.rfft(chunk, n=n))
    freqs = np.fft.rfftfreq(n, d=1.0 / samplerate)
    denom = np.sum(fft) + 1e-12
    return float(np.sum(freqs * fft) / denom)


def _spectral_flatness(chunk: np.ndarray) -> float:
    """
    Compute spectral flatness (Wiener entropy proxy).

    Values near 0 indicate tone-like spectra; values near 1 indicate noise-like
    spectra. Intermediate ranges are used as part of whisper detection.
    """
    fft  = np.abs(np.fft.rfft(chunk)) + 1e-12
    geom = np.exp(np.mean(np.log(fft)))
    arith = np.mean(fft) + 1e-12
    return float(geom / arith)


# Main proctoring class

class AudioProctor:
    def __init__(self, samplerate: int = SAMPLERATE,
                 buffer_seconds: float = BUFFER_SECONDS):
        self.samplerate      = samplerate
        self.is_available    = _SD_AVAILABLE

        self.blocks_per_sec  = BLOCKS_PER_SEC
        max_buf              = int(buffer_seconds * self.blocks_per_sec)
        self.rms_buffer      = deque(maxlen=max_buf)
        self.max_buffer_len  = max_buf

        # Adaptive calibration state.
        self._calib_rms: list[float] = []
        self._calib_done   = False
        self._calib_start: float | None = None
        self.threshold     = 0.015   # Safe default before calibration completes.

        self._is_running   = False
        self._stream       = None
        self._lock         = threading.RLock()
        self.current_flags: list[str] = []
        self.current_stats = {"avg_rms": 0.0, "baseline_rms": 0.0, "threshold": self.threshold}

    def _reset_session_state(self) -> None:
        """Reset per-session rolling buffers and calibration before a fresh start."""
        self.rms_buffer.clear()
        self._calib_rms.clear()
        self._calib_done = False
        self._calib_start = None
        self.threshold = 0.015
        self.current_flags = []
        self.current_stats = {
            "avg_rms": 0.0,
            "baseline_rms": 0.0,
            "threshold": self.threshold,
        }

    def _append_flag_once(self, flag: str) -> None:
        if flag not in self.current_flags:
            self.current_flags.append(flag)

    # Calibration

    def _update_calibration(self, rms: float) -> bool:
        """
        Update startup calibration with a new RMS sample.

        Returns True only after calibration has completed and threshold has
        been finalized for this session.
        """
        now = time.monotonic()
        if self._calib_start is None:
            self._calib_start = now
            print("[Audio] Calibrating ambient noise baseline — stay quiet...")

        if now - self._calib_start < CALIB_SECONDS:
            self._calib_rms.append(rms)
            return False

        if not self._calib_done:
            if self._calib_rms:
                baseline = float(np.median(self._calib_rms))
            else:
                baseline = HARD_MIN_THRESHOLD
            raw_thresh = baseline * THRESHOLD_MULTIPLIER
            self.threshold = max(HARD_MIN_THRESHOLD, min(raw_thresh, HARD_MAX_THRESHOLD))
            self._calib_done = True
            self.current_stats["baseline_rms"] = baseline
            self.current_stats["threshold"]    = self.threshold
            print(
                f"[Audio] Calibration done — baseline={baseline:.5f}, "
                f"adaptive threshold={self.threshold:.5f}"
            )
        return True

    # Spectral analysis

    def _analyze_chunk_spectral(self, chunk: np.ndarray) -> list[str]:
        """
        Analyze one audio chunk for speech-like or whisper-like signatures.

        High-RMS chunks use speech-band energy ratio checks.
        Lower-RMS chunks use centroid and flatness heuristics.
        Returns a list of human-readable flags for this chunk.
        """
        flags = []
        rms   = float(np.sqrt(np.mean(np.square(chunk))))

        if not self._calib_done:
            return flags

        # High-energy path: classify speech-like vs ambient high-noise.
        if rms > self.threshold:
            speech_ratio = _speech_energy_ratio(chunk, self.samplerate)
            if speech_ratio > SPEECH_RATIO_THRESH:
                flags.append(
                    f"Speech detected (RMS={rms:.4f}, "
                    f"speech_ratio={speech_ratio:.2f} "
                    f"> threshold={SPEECH_RATIO_THRESH})"
                )
            else:
                # High amplitude without speech-band dominance is treated as ambient.
                flags.append(
                    f"Sustained ambient noise (RMS={rms:.4f}, "
                    f"speech_ratio={speech_ratio:.2f} — broadband, not speech)"
                )

        # Low-energy path: whisper-oriented spectral heuristics.
        elif rms > HARD_MIN_THRESHOLD:
            centroid  = _spectral_centroid(chunk, self.samplerate)
            flatness  = _spectral_flatness(chunk)
            in_centroid  = WHISPER_CENTROID_LOW <= centroid <= WHISPER_CENTROID_HIGH
            in_flatness  = WHISPER_FLATNESS_MIN <= flatness <= WHISPER_FLATNESS_MAX
            if in_centroid and in_flatness:
                flags.append(
                    f"Possible whisper / bone-conduction detected "
                    f"(RMS={rms:.4f} below threshold but "
                    f"centroid={centroid:.0f} Hz, flatness={flatness:.3f})"
                )

        return flags

    # Audio callback

    def _audio_callback(self, indata, frames, time_info, status):
        chunk = indata[:, 0].astype(np.float64)
        rms   = float(np.sqrt(np.mean(np.square(chunk))))

        with self._lock:
            if not self._is_running:
                return
            # Suppress event generation while baseline calibration is in progress.
            if not self._update_calibration(rms):
                self.rms_buffer.append(rms)
                return

            self.rms_buffer.append(rms)
            self._analyze_temporal_buffer(chunk)

    def _analyze_temporal_buffer(self, latest_chunk: np.ndarray):
        """
        Temporal sustained assessment + per-chunk spectral events.
        Called with self._lock held.
        """
        flags: list[str] = []

        # Per-chunk spectral analysis (FIX 2+3)
        flags.extend(self._analyze_chunk_spectral(latest_chunk))

        # Temporal RMS rule to catch continuous loud audio across the window.
        if len(self.rms_buffer) >= self.max_buffer_len:
            high = sum(1 for v in self.rms_buffer if v > self.threshold)
            ratio = high / self.max_buffer_len
            if ratio > SUSTAINED_RATIO and not any("Speech" in f or "whisper" in f for f in flags):
                flags.append(
                    f"Sustained elevated audio ({ratio*100:.0f}% of window above "
                    f"adaptive threshold={self.threshold:.4f})"
                )

        # Keep framework-level flags while replacing chunk-level detections.
        existing = [f for f in self.current_flags
                    if f.startswith("AudioProctor") or "unavailable" in f]
        self.current_flags = existing + flags if flags else []
        self.current_stats["avg_rms"] = float(np.mean(self.rms_buffer)) if self.rms_buffer else 0.0

    # Start / stop

    def start_monitoring(self):
        """Start the audio stream and begin continuous analysis."""
        if not self.is_available:
            # Unavailable audio capture is treated as a critical exam condition.
            with self._lock:
                self._append_flag_once(
                    "AudioProctor CRITICAL: sounddevice not installed — "
                    "audio monitoring DISABLED. Exam cannot proceed."
                )
            print("[Audio] sounddevice not installed — audio monitoring DISABLED.")
            return

        with self._lock:
            if self._is_running:
                return
            self._reset_session_state()
            self._is_running = True

        try:
            blocksize = int(self.samplerate / self.blocks_per_sec)
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=1,
                dtype="float32",
                blocksize=blocksize,
                callback=self._audio_callback,
            )
            self._stream.start()
            print("[Audio] Continuous temporal stream started.")
        except Exception as e:
            with self._lock:
                self._is_running = False
                self._stream = None
            # Stream startup failure is reported as a critical block condition.
            with self._lock:
                self._append_flag_once(
                    f"AudioProctor CRITICAL: stream failed to start ({e!s}) — "
                    "audio monitoring DISABLED. Exam cannot proceed."
                )
            print(f"[Audio] Failed to start stream: {e}")

    def stop_monitoring(self):
        with self._lock:
            stream = self._stream
            was_running = self._is_running
            self._stream = None
            self._is_running = False

        if stream and was_running:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    # Telemetry

    def get_latest_telemetry(self) -> dict:
        if not self.is_available:
            return {
                "detected":  True,
                "severity":  "critical",
                "flags":     [
                    "AudioProctor CRITICAL: sounddevice not installed. "
                    "Exam cannot proceed."
                ],
                "avg_rms":   0.0,
                "threshold": self.threshold,
                "calibrated": False,
            }

        with self._lock:
            flags_copy  = list(self.current_flags)
            avg_rms     = self.current_stats.get("avg_rms", 0.0)
            threshold   = self.threshold
            calibrated  = self._calib_done

        has_critical = any("CRITICAL" in f for f in flags_copy)
        return {
            "detected":   len(flags_copy) > 0,
            "severity":   "critical" if has_critical else "warn",
            "avg_rms":    avg_rms,
            "threshold":  threshold,
            "calibrated": calibrated,
            "flags":      flags_copy,
        }
