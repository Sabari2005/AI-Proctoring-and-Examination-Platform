"""
Runtime proctoring orchestration for the UI exam flow.

Coordinates audio, vision, process, integrity, and security controls used
during identity verification and exam runtime.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import threading
import time
from typing import List, Optional

import psutil

from .logger import logger

try:
    from .audio_proctor import AudioProctor
except Exception:  # pragma: no cover - optional during setup
    AudioProctor = None

try:
    from .vision_proctor import VisionProctor
except Exception:  # pragma: no cover - optional during setup
    VisionProctor = None

try:
    from .process_monitor import ProcessMonitor
except Exception:  # pragma: no cover - optional during setup
    ProcessMonitor = None

try:
    from .process_monitor import SUSPICIOUS_PROC_KEYWORDS
except Exception:  # pragma: no cover - optional during setup
    SUSPICIOUS_PROC_KEYWORDS = [
        "obs", "bandicam", "sharex", "anydesk", "teamviewer", "x64dbg", "cheatengine",
    ]

try:
    from .hasher import (
        set_baseline,
        register_tamper_callback,
        start_continuous_monitoring,
    )
except Exception:  # pragma: no cover - optional during setup
    set_baseline = None
    register_tamper_callback = None
    start_continuous_monitoring = None

try:
    from .firewall import NetworkIsolator
except Exception:  # pragma: no cover - optional during setup
    NetworkIsolator = None

try:
    from .lockdown import KeyboardLocker
    _LOCKDOWN_IMPORT_ERROR = ""
except Exception as e_rel:  # pragma: no cover - optional during setup
    try:
        # Fallback for frozen/runtime import edge-cases where relative import may fail.
        from core.lockdown import KeyboardLocker  # type: ignore
        _LOCKDOWN_IMPORT_ERROR = f"relative import failed: {e_rel}"
    except Exception as e_abs:  # pragma: no cover - optional during setup
        KeyboardLocker = None
        _LOCKDOWN_IMPORT_ERROR = f"relative import failed: {e_rel}; absolute import failed: {e_abs}"

try:
    from .snapshot_uploader import SnapshotUploader
except Exception:  # pragma: no cover - optional during setup
    SnapshotUploader = None

try:
    from .evidence_buffer import EvidenceFrameBuffer
except Exception:  # pragma: no cover - optional during setup
    EvidenceFrameBuffer = None

try:
    from .backend_config import get_backend_url
except Exception:  # pragma: no cover - optional during setup
    get_backend_url = None

try:
    from .telemetry import TelemetryClient
except Exception:  # pragma: no cover - optional during setup
    TelemetryClient = None

try:
    from .os_checks import OSEnvChecker
except Exception:  # pragma: no cover - optional during setup
    OSEnvChecker = None

try:
    from .hw_checks import HardwareChecker
except Exception:  # pragma: no cover - optional during setup
    HardwareChecker = None

if platform.system() == "Windows":
    try:
        import win32gui  # type: ignore
        import win32process  # type: ignore
    except Exception:  # pragma: no cover - optional on non-pywin32 setups
        win32gui = None
        win32process = None
else:
    win32gui = None
    win32process = None


class ProctoringService:
    def __init__(self, backend_url: Optional[str] = None, session_nonce: Optional[str] = None):
        """
        Initialize service state and optional monitoring dependencies.
        
        Args:
            backend_url: Optional backend URL for snapshot uploads
            session_nonce: Optional session identifier for evidence collection
        """
        self.audio = AudioProctor() if AudioProctor else None
        self.vision = None  # Lazy initialized to avoid MediaPipe load during object construction.
        self._vision_initialized = False
        self.process = ProcessMonitor(scan_interval=20.0) if ProcessMonitor else None

        # Security hardening components.
        self.firewall = NetworkIsolator() if NetworkIsolator else None
        self.lockdown = KeyboardLocker() if KeyboardLocker else None
        self.snapshot_uploader = None  # Created at exam start once session identifiers are available.
        self.evidence_buffer = None  # Warning-driven frame buffer attached to vision monitor.
        self._backend_url = backend_url or (get_backend_url() if get_backend_url else None)
        self._login_token: Optional[str] = None
        self._session_nonce = session_nonce
        self._user_email: Optional[str] = None
        self._telemetry = None
        self._telemetry_session_lock = threading.Lock()
        self._telemetry_init_thread: Optional[threading.Thread] = None
        self._state_lock = threading.RLock()
        self._lifecycle_in_progress = False
        self._lifecycle_action: Optional[str] = None
        self._vision_init_lock = threading.Lock()

        self._started = False
        self._hash_monitor_started = False
        self._security_engaged = False
        self._tamper_messages: List[str] = []
        self._last_scan_result: dict = {}
        self._identity_started = False
        
        # Violation scoring state.
        self._violation_count = 0
        self._violation_threshold = 30
        self._threshold_callback = None  # Called when threshold is reached
        self._threshold_reached = False  # Flag to prevent multiple triggers
        self._alert_active_state: dict[str, dict] = {}
        self._alert_recount_interval = max(
            30.0,
            float(os.environ.get("OBSERVE_ALERT_RECOUNT_INTERVAL_SEC", "90") or "90"),
        )
        self._max_violation_increment_per_poll = max(
            1,
            int(os.environ.get("OBSERVE_MAX_VIOLATION_INCREMENT_PER_POLL", "1") or "1"),
        )
        self._exam_metadata = {
            "username": "",
            "testid": "",
            "sectionid": "",
        }
        
        # Periodic environment and hardware telemetry checks.
        self._env_checker = OSEnvChecker() if OSEnvChecker else None
        self._hw_checker = HardwareChecker() if HardwareChecker else None
        self._last_env_check_time = 0.0
        self._env_check_interval = 10.0  # Check environment every 10 seconds

        # Runtime policy toggles (production defaults).
        self._enable_firewall_isolation = (os.environ.get("OBSERVE_ENABLE_FIREWALL_ISOLATION", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._enable_keyboard_lockdown = (os.environ.get("OBSERVE_ENABLE_KEYBOARD_LOCKDOWN", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._lockdown_block_input = (os.environ.get("OBSERVE_LOCKDOWN_BLOCK_INPUT", "0").strip().lower() in ("1", "true", "yes", "on"))
        self._strict_touchpad_lockdown = (os.environ.get("OBSERVE_STRICT_TOUCHPAD_LOCKDOWN", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._strict_os_lockdown = (os.environ.get("OBSERVE_STRICT_OS_LOCKDOWN", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._require_keyboard_lockdown = (os.environ.get("OBSERVE_REQUIRE_KEYBOARD_LOCKDOWN", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._enable_runtime_auto_terminate = (os.environ.get("OBSERVE_ENABLE_RUNTIME_AUTO_TERMINATE", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._auto_terminate_cooldown_sec = max(3.0, float(os.environ.get("OBSERVE_RUNTIME_AUTO_TERMINATE_COOLDOWN_SEC", "3") or "3"))
        self._auto_terminate_max_per_scan = max(1, int(os.environ.get("OBSERVE_RUNTIME_AUTO_TERMINATE_MAX_PER_SCAN", "10") or "10"))
        self._runtime_quarantine: dict[int, float] = {}
        self._runtime_quarantine_ttl_sec = 180.0
        self._enforce_server_decision = (os.environ.get("OBSERVE_ENFORCE_SERVER_DECISION", "1").strip().lower() in ("1", "true", "yes", "on"))

        # Full-lockdown controls (process suppression + overlay control).
        self._enable_full_lockdown = (os.environ.get("OBSERVE_ENABLE_FULL_LOCKDOWN", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._full_lockdown_close_all_apps = (os.environ.get("OBSERVE_CLOSE_ALL_APPS_EXCEPT_SELF", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._full_lockdown_scan_interval = max(2.0, float(os.environ.get("OBSERVE_FULL_LOCKDOWN_SCAN_INTERVAL_SEC", "3.0") or "3.0"))
        allow_raw = (os.environ.get("OBSERVE_FULL_LOCKDOWN_ALLOWLIST", "") or "").strip().lower()
        self._full_lockdown_allowlist = {x.strip() for x in allow_raw.split(",") if x.strip()}
        own_name = (os.path.basename(sys.executable or "") or "").strip().lower()
        if own_name:
            self._full_lockdown_allowlist.add(own_name)
        self._full_lockdown_allowlist.update({
            "observeproctor.exe",
            "observeproctor",
            "conhost.exe",
            "explorer.exe",
            "dwm.exe",
            "shellexperiencehost.exe",
            "searchhost.exe",
            "taskhostw.exe",
            "runtimebroker.exe",
            "svchost.exe",
            "lsass.exe",
            "wininit.exe",
            "winlogon.exe",
            "services.exe",
            "smss.exe",
            "csrss.exe",
            "fontdrvhost.exe",
            "audiodg.exe",
            "ctfmon.exe",
            "dllhost.exe",
            "sihost.exe",
            "textinputhost.exe",
            "startmenuexperiencehost.exe",
            "applicationframehost.exe",
            "securityhealthsystray.exe",
            "securityhealthservice.exe",
            "msmpeng.exe",
            "nissrv.exe",
            "smartscreen.exe",
            "spoolsv.exe",
            "wuauclt.exe",
            "backgroundtaskhost.exe",
            "lockapp.exe",
            "widgets.exe",
        })
        self._full_lockdown_thread: Optional[threading.Thread] = None
        self._full_lockdown_stop = threading.Event()
        self._full_lockdown_baseline_pids: set[int] = set()
        self._full_lockdown_started_epoch = 0.0
        self._full_lockdown_quarantine: dict[str, float] = {}
        self._full_lockdown_kill_cooldown_sec = max(
            4.0,
            float(os.environ.get("OBSERVE_FULL_LOCKDOWN_KILL_COOLDOWN_SEC", "8") or "8"),
        )
        default_max_kills = "20" if self._full_lockdown_close_all_apps else "4"
        self._full_lockdown_max_kills_per_scan = max(
            1,
            int(os.environ.get("OBSERVE_FULL_LOCKDOWN_MAX_KILLS_PER_SCAN", default_max_kills) or default_max_kills),
        )
        self._focus_guard_callback = None

        if self._enable_keyboard_lockdown and self.lockdown is None and _LOCKDOWN_IMPORT_ERROR:
            logger.error(
                f"KeyboardLocker import unavailable: {_LOCKDOWN_IMPORT_ERROR}",
                module="proctoring_service",
            )

    def set_exam_context(
        self,
        backend_url: Optional[str],
        session_nonce: Optional[str],
        user_email: Optional[str] = None,
    ) -> None:
        """Update backend/session context for evidence uploads before exam start."""
        with self._state_lock:
            if backend_url:
                self._backend_url = backend_url
            if session_nonce:
                self._login_token = session_nonce
            if user_email:
                self._user_email = user_email.strip().lower()

    def set_focus_guard_callback(self, callback) -> None:
        """Register UI callback that forces exam window to foreground/topmost."""
        self._focus_guard_callback = callback

    def _start_telemetry_session_async(self) -> None:
        """Start telemetry auth in a daemon thread to avoid blocking the Qt main thread."""
        with self._state_lock:
            backend_url = self._backend_url
            login_token = self._login_token
            user_email = self._user_email
            has_live_telemetry = bool(self._telemetry and self._session_nonce)
            init_thread = self._telemetry_init_thread

        if not TelemetryClient or not backend_url or not login_token or not user_email:
            return
        if has_live_telemetry:
            return

        if init_thread and init_thread.is_alive():
            return

        init_thread = threading.Thread(
            target=self._ensure_telemetry_session,
            daemon=True,
            name="TelemetryInit",
        )
        with self._state_lock:
            self._telemetry_init_thread = init_thread
        init_thread.start()

    def _ensure_evidence_buffer_initialized(self) -> None:
        """Initialize warning-triggered evidence buffer once nonce + vision are ready."""
        if self.evidence_buffer is not None:
            return
        if not (EvidenceFrameBuffer and self._backend_url and self._session_nonce):
            return

        self._ensure_vision_initialized()
        if not self.vision:
            return

        try:
            self.evidence_buffer = EvidenceFrameBuffer(
                backend_url=self._backend_url,
                session_nonce=self._session_nonce,
            )
            self.evidence_buffer.set_session_metadata(
                self._exam_metadata.get("username", ""),
                self._exam_metadata.get("testid", ""),
                self._exam_metadata.get("sectionid", ""),
            )
            self.vision.set_evidence_buffer(self.evidence_buffer)
            logger.info("Evidence buffer initialized and wired to vision proctor", module="proctoring_service")
        except Exception as e:
            logger.warning(f"Failed to initialize evidence buffer: {e}", module="proctoring_service")

    def _ensure_snapshot_uploader_started(self) -> bool:
        """Start snapshot uploader once nonce is available; safe to call repeatedly."""
        if not (SnapshotUploader and self._backend_url and self._session_nonce):
            return False
        if self.snapshot_uploader and self.snapshot_uploader.is_running():
            return True

        try:
            self._ensure_vision_initialized()
            self.snapshot_uploader = SnapshotUploader(
                backend_url=self._backend_url,
                session_nonce=self._session_nonce,
                vision_proctor=self.vision,
            )
            self.snapshot_uploader.start()
            logger.info("Evidence collection started", module="proctoring_service")
            return True
        except Exception as e:
            logger.warning(f"Evidence collection error: {e}", module="proctoring_service")
            return False

    def _ensure_telemetry_session(self) -> None:
        """
        Create authenticated telemetry session and refresh server-issued nonce.

        Startup remains non-fatal in local/offline scenarios.
        """
        if not TelemetryClient or not self._backend_url or not self._login_token or not self._user_email:
            return

        if not self._telemetry_session_lock.acquire(blocking=False):
            return

        try:
            self._telemetry = TelemetryClient(
                email=self._user_email,
                login_token=self._login_token,
                backend_url=self._backend_url,
            )
            auth_ok = False
            for attempt in range(1, 4):
                if self._telemetry.authenticate_session() and self._telemetry.session_nonce:
                    auth_ok = True
                    break
                time.sleep(0.35 * attempt)

            if auth_ok and self._telemetry.session_nonce:
                # Keep login token unchanged; track server-issued nonce separately.
                self._session_nonce = self._telemetry.session_nonce
                logger.info("Telemetry session authenticated with server nonce", module="proctoring_service")

                if self.process and hasattr(self.process, "set_blacklisted_hashes"):
                    hashes = list(getattr(self._telemetry, "blacklisted_hashes", []) or [])
                    try:
                        self.process.set_blacklisted_hashes(hashes)
                        logger.info(
                            f"Process hash blacklist loaded: {len(hashes)} entries",
                            module="proctoring_service",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to apply process hash blacklist: {e}", module="proctoring_service")
                
                # Telemetry credentials are required before environment check uploads.
                if self._env_checker:
                    self._env_checker.set_credentials(self._user_email, self._login_token)
                    if hasattr(self._env_checker, "set_telemetry_client"):
                        self._env_checker.set_telemetry_client(self._telemetry)

                # Telemetry can finish after exam start, so initialize nonce-dependent services here.
                if self._started:
                    self._ensure_evidence_buffer_initialized()
                    if self._security_engaged:
                        self._ensure_snapshot_uploader_started()
            else:
                logger.warning("Telemetry auth failed; continuing in local-check mode", module="proctoring_service")
                self._telemetry = None
        except Exception as e:
            logger.warning(f"Telemetry init failed: {e}", module="proctoring_service")
            self._telemetry = None
        finally:
            self._telemetry_session_lock.release()
    
    def set_violation_threshold_callback(self, callback) -> None:
        """
        Register callback invoked when violation threshold is reached.
        
        Args:
            callback: Function to call when threshold is reached (e.g., to close exam)
        """
        with self._state_lock:
            self._threshold_callback = callback
    
    def get_violation_count(self) -> int:
        """Return current violation count."""
        with self._state_lock:
            return self._violation_count
    
    def reset_violation_count(self) -> None:
        """Reset violation counter to zero."""
        with self._state_lock:
            self._violation_count = 0
            self._threshold_reached = False
        logger.info("Violation counter reset to 0", module="proctoring_service")

    def set_exam_metadata(self, username: str, testid: str, sectionid: str) -> None:
        """
        Set exam metadata used by evidence and telemetry payloads.
        
        Args:
            username: Candidate email/username
            testid: Exam ID
            sectionid: Section ID within exam
        """
        with self._state_lock:
            self._exam_metadata = {
                "username": str(username or "").strip().lower(),
                "testid": str(testid or "").strip(),
                "sectionid": str(sectionid or "").strip(),
            }
        if self.evidence_buffer:
            with self._state_lock:
                username_value = self._exam_metadata["username"]
                testid_value = self._exam_metadata["testid"]
                sectionid_value = self._exam_metadata["sectionid"]
            self.evidence_buffer.set_session_metadata(
                username_value,
                testid_value,
                sectionid_value,
            )
        logger.info(
            f"Evidence metadata set: user={self._exam_metadata['username']}, "
            f"test={self._exam_metadata['testid']}, section={self._exam_metadata['sectionid']}",
            module="proctoring_service",
        )

    def _ensure_vision_initialized(self) -> None:
        """Initialize vision monitor once, on first use."""
        if self._vision_initialized or not VisionProctor:
            return

        with self._vision_init_lock:
            if self._vision_initialized:
                return
            try:
                self.vision = VisionProctor()
                logger.info("Vision proctor lazy-initialized", module="proctoring_service")
            except Exception as e:
                logger.warning(f"Failed to initialize vision proctor: {e}", module="proctoring_service")
                self.vision = None
            finally:
                self._vision_initialized = True

    def _on_hash_tamper(self, reason: str) -> None:
        msg = f"Integrity tamper detected: {reason}"
        with self._state_lock:
            self._tamper_messages.append(msg)
        logger.critical_security_event(msg, module="proctoring_service")
        try:
            self._disengage_security_lockdown()
            logger.warning("Emergency security cleanup completed before hard kill", module="proctoring_service")
        except Exception as e:
            logger.warning(f"Emergency cleanup during tamper callback failed: {e}", module="proctoring_service")

    def start_exam_monitoring(self, engage_security: bool = True) -> None:
        """
        Start full exam monitoring including all proctoring components.
        
        Args:
            engage_security: If True, engage firewall isolation, keyboard lockdown,
                and snapshot uploads. Some controls require Administrator privileges.
        """
        with self._state_lock:
            if self._started or self._lifecycle_in_progress:
                return
            self._lifecycle_in_progress = True
            self._lifecycle_action = "start"

        audio_started = False
        vision_started = False
        process_started = False
        hw_started = False
        full_lockdown_started = False

        try:
            if (
                engage_security
                and self._enable_keyboard_lockdown
                and self._require_keyboard_lockdown
                and self.lockdown is None
            ):
                raise RuntimeError(
                    "Keyboard lockdown is required but unavailable. "
                    f"Import detail: {_LOCKDOWN_IMPORT_ERROR or 'not provided'}"
                )

            # Start telemetry authentication off the UI thread.
            self._start_telemetry_session_async()

            if self.audio:
                self.audio.start_monitoring()
                logger.info("Audio proctor started", module="proctoring_service")
                audio_started = True

            # Initialize vision only when needed.
            self._ensure_vision_initialized()
            if self.vision:
                self._ensure_evidence_buffer_initialized()

                self.vision.start_monitoring()
                logger.info("Vision proctor started", module="proctoring_service")
                vision_started = True

            if self.process:
                self.process.start_background_scanning(on_violation=self._on_process_violation)
                logger.info("Process monitor started", module="proctoring_service")
                process_started = True

            # Prime clock-integrity baseline before network isolation.
            if self._env_checker:
                try:
                    self._env_checker.prime_clock_integrity()
                except Exception as e:
                    logger.debug(f"Clock integrity prime failed: {e}", module="proctoring_service")

            if self._hw_checker:
                try:
                    self._hw_checker.start_continuous_monitor(alert_callback=self._on_hw_alert)
                    logger.info("Hardware continuous monitor started", module="proctoring_service")
                    hw_started = True
                except Exception as e:
                    logger.warning(f"Failed to start hardware continuous monitor: {e}", module="proctoring_service")

            if set_baseline and register_tamper_callback and start_continuous_monitoring:
                if not self._hash_monitor_started:
                    set_baseline()
                    register_tamper_callback(self._on_hash_tamper)
                    start_continuous_monitoring()
                    self._hash_monitor_started = True
                    logger.info("File integrity monitor started", module="proctoring_service")

            # Engage security controls when requested.
            if engage_security and not self._security_engaged:
                try:
                    self._engage_security_lockdown()
                except Exception:
                    try:
                        self._disengage_security_lockdown()
                    except Exception:
                        pass
                    raise

                if self._enable_keyboard_lockdown and self._require_keyboard_lockdown:
                    locked = bool(self.lockdown and self.lockdown.is_locked())
                    if not locked:
                        reason = ""
                        if self.lockdown is not None and hasattr(self.lockdown, "get_last_error"):
                            try:
                                reason = str(self.lockdown.get_last_error() or "")
                            except Exception:
                                reason = ""
                        try:
                            self._disengage_security_lockdown()
                        except Exception:
                            pass
                        detail = f" Reason: {reason}" if reason else ""
                        logger.critical_security_event(
                            f"Keyboard lockdown required but did not engage.{detail}",
                            module="proctoring_service",
                        )
                        raise RuntimeError(
                            "Keyboard lockdown is required but did not engage. "
                            f"Exam start blocked by OBSERVE_REQUIRE_KEYBOARD_LOCKDOWN.{detail}"
                        )

            if engage_security and self._enable_full_lockdown:
                self._start_full_lockdown_watchdog()
                full_lockdown_started = True

            with self._state_lock:
                self._started = True
        except Exception:
            # Roll back partially started components to avoid orphan worker threads.
            try:
                if full_lockdown_started:
                    self._stop_full_lockdown_watchdog()
            except Exception:
                pass
            try:
                if self._security_engaged:
                    self._disengage_security_lockdown()
            except Exception:
                pass
            try:
                if process_started and self.process:
                    self.process.stop_background_scanning()
            except Exception:
                pass
            try:
                if vision_started and self.vision:
                    self.vision.stop_monitoring()
            except Exception:
                pass
            try:
                if audio_started and self.audio:
                    self.audio.stop_monitoring()
            except Exception:
                pass
            try:
                if hw_started and self._hw_checker:
                    self._hw_checker.stop_continuous_monitor()
            except Exception:
                pass
            raise
        finally:
            with self._state_lock:
                self._lifecycle_in_progress = False
                self._lifecycle_action = None

    def start_identity_monitoring(self) -> None:
        """Start vision-only monitoring for biometric identity flow."""
        with self._state_lock:
            if self._identity_started or self._lifecycle_in_progress:
                return
            self._identity_started = True
        # Initialize vision only when needed.
        self._ensure_vision_initialized()
        if self.vision:
            self.vision.start_monitoring()
            logger.info("Identity vision monitor started", module="proctoring_service")

    def stop_identity_monitoring(self) -> None:
        with self._state_lock:
            if self._lifecycle_in_progress:
                return
            should_stop = bool(self.vision and self._identity_started and not self._started)
            self._identity_started = False
        if should_stop:
            self.vision.stop_monitoring()
            logger.info("Identity vision monitor stopped", module="proctoring_service")

    def stop_exam_monitoring(self) -> None:
        """Stop all exam monitoring and security lockdown."""
        with self._state_lock:
            if self._lifecycle_in_progress or not self._started:
                return
            self._lifecycle_in_progress = True
            self._lifecycle_action = "stop"

        try:
            self._stop_full_lockdown_watchdog()

            # Disengage security first. Do not rely only on _security_engaged,
            # because state drift could leave lockdown/firewall active.
            should_disengage = bool(self._security_engaged)
            if not should_disengage and self.lockdown:
                try:
                    should_disengage = should_disengage or bool(self.lockdown.is_locked())
                except Exception:
                    pass
            if not should_disengage and self.firewall:
                try:
                    should_disengage = should_disengage or bool(self.firewall.is_isolated())
                except Exception:
                    pass
            if not should_disengage and self.snapshot_uploader:
                try:
                    should_disengage = should_disengage or bool(self.snapshot_uploader.is_running())
                except Exception:
                    pass

            if should_disengage:
                self._disengage_security_lockdown()

            if self.audio:
                self.audio.stop_monitoring()
            if self.vision:
                self.vision.stop_monitoring()
            if self.process:
                self.process.stop_background_scanning()
            if self._hw_checker:
                try:
                    self._hw_checker.stop_continuous_monitor()
                except Exception:
                    pass

            logger.info("Exam monitoring stopped", module="proctoring_service")
        finally:
            with self._state_lock:
                self._started = False
                self._identity_started = False
                self._lifecycle_in_progress = False
                self._lifecycle_action = None

    def _engage_security_lockdown(self) -> None:
        """
        Engage security hardening features:
        1. Network isolation.
        2. Keyboard and input lockdown.
        3. Evidence collection.
        
        Some controls require Administrator privileges for full effect.
        """
        success_count = 0
        total_count = 1 + (1 if self._enable_firewall_isolation else 0) + (1 if self._enable_keyboard_lockdown else 0)

        # 1) Network isolation.
        if self._enable_firewall_isolation:
            if self.firewall:
                try:
                    # Whitelist backend endpoints before isolation to preserve service connectivity.
                    if self._backend_url:
                        self.firewall.add_backend_whitelist(self._backend_url)
                        print(f"[Security] Backend pre-whitelisted: {self._backend_url[:50]}...")
                    else:
                        logger.warning("Backend URL not set for whitelist", module="proctoring_service")

                    # Optional extra allowlist URLs supplied via environment variable.
                    extra_urls_raw = os.environ.get("OBSERVE_ADDITIONAL_WHITELIST_URLS", "")
                    for raw in (u.strip() for u in extra_urls_raw.split(",") if u.strip()):
                        self.firewall.add_backend_whitelist(raw)
                        print(f"[Security] Extra URL pre-whitelisted: {raw[:50]}...")

                    result = self.firewall.engage_isolation()
                    if result.get("isolated"):
                        logger.info("Network isolation engaged", module="proctoring_service")
                        success_count += 1
                    else:
                        reason = "; ".join(result.get("flags", [])) or "unknown reason"
                        logger.warning(
                            f"Network isolation failed: {reason}",
                            module="proctoring_service",
                        )
                except Exception as e:
                    logger.warning(f"Network isolation error: {e}", module="proctoring_service")
            else:
                logger.warning("NetworkIsolator not available", module="proctoring_service")
        else:
            logger.info("Network isolation disabled by env", module="proctoring_service")

        # 2) Keyboard/input lockdown.
        if self._enable_keyboard_lockdown:
            if self.lockdown:
                try:
                    if self.lockdown.lock_keyboard(
                        use_block_input=self._lockdown_block_input,
                        strict_touchpad=self._strict_touchpad_lockdown,
                        strict_os=self._strict_os_lockdown,
                    ):
                        logger.info(
                            f"Keyboard lockdown engaged (block_input={self._lockdown_block_input}, strict_touchpad={self._strict_touchpad_lockdown}, strict_os={self._strict_os_lockdown})",
                            module="proctoring_service",
                        )
                        success_count += 1
                    else:
                        reason = ""
                        if hasattr(self.lockdown, "get_last_error"):
                            try:
                                reason = str(self.lockdown.get_last_error() or "")
                            except Exception:
                                reason = ""
                        detail = f": {reason}" if reason else ""
                        logger.warning(f"Keyboard lockdown not engaged{detail}", module="proctoring_service")
                except Exception as e:
                    logger.warning(f"Keyboard lockdown error: {e}", module="proctoring_service")
            else:
                logger.warning("KeyboardLocker not available", module="proctoring_service")
        else:
            logger.info("Keyboard lockdown disabled by env", module="proctoring_service")

        # 3) Evidence collection upload pipeline.
        if SnapshotUploader and self._backend_url and self._session_nonce:
            if self._ensure_snapshot_uploader_started():
                success_count += 1
        else:
            if not SnapshotUploader:
                logger.warning("SnapshotUploader not available", module="proctoring_service")
            elif not self._backend_url:
                logger.warning("Evidence collection disabled: no backend URL", module="proctoring_service")

        with self._state_lock:
            self._security_engaged = (
                (self.firewall is not None and self.firewall.is_isolated())
                or (self.lockdown is not None and self.lockdown.is_locked())
                or (self.snapshot_uploader is not None and self.snapshot_uploader.is_running())
            )
        logger.info(f"Security lockdown: {success_count}/{total_count} features engaged", 
                   module="proctoring_service")

    def _disengage_security_lockdown(self) -> None:
        """Release all security lockdown features with comprehensive cleanup and failover."""
        self._stop_full_lockdown_watchdog()
        cleanup_results = []
        
        # 1) Stop snapshot uploader first.
        if self.snapshot_uploader:
            try:
                self.snapshot_uploader.stop()
                logger.info("Evidence collection stopped", module="proctoring_service")
                cleanup_results.append(("snapshot_uploader", True, None))
            except Exception as e:
                logger.warning(f"Error stopping snapshot uploader: {e}", module="proctoring_service")
                cleanup_results.append(("snapshot_uploader", False, str(e)))
            self.snapshot_uploader = None

        # 2) Unlock keyboard/input controls.
        if self.lockdown:
            try:
                self.lockdown.unlock_keyboard()
                still_locked = False
                try:
                    still_locked = bool(self.lockdown.is_locked())
                except Exception:
                    still_locked = True

                if still_locked and hasattr(self.lockdown, "_emergency_unlock"):
                    logger.warning(
                        "Keyboard lockdown still active after unlock attempt; applying emergency unlock",
                        module="proctoring_service",
                    )
                    try:
                        self.lockdown._emergency_unlock()
                        still_locked = bool(self.lockdown.is_locked())
                    except Exception as e:
                        logger.warning(f"Emergency keyboard unlock failed: {e}", module="proctoring_service")

                if still_locked:
                    logger.warning("Keyboard lockdown release incomplete", module="proctoring_service")
                    cleanup_results.append(("lockdown", False, "Lockdown still active after unlock attempts"))
                else:
                    logger.info("Keyboard lockdown released", module="proctoring_service")
                    cleanup_results.append(("lockdown", True, None))
            except Exception as e:
                logger.warning(f"Error unlocking keyboard: {e}", module="proctoring_service")
                cleanup_results.append(("lockdown", False, str(e)))

        # 3. Release network isolation with auto-failover
        if self.firewall:
            try:
                result = self.firewall.release_isolation()
                if result.get("success"):
                    logger.info(f"Network isolation released: {result.get('message')}", module="proctoring_service")
                    cleanup_results.append(("firewall", True, result.get('message')))
                else:
                    logger.error(f"Firewall cleanup failed: {result.get('message')}", module="proctoring_service")
                    cleanup_results.append(("firewall", False, result.get('message')))
                    
                    # Attempt emergency restore if normal cleanup fails.
                    if not result.get("success") and self.firewall._is_isolated:
                        logger.warning("Attempting emergency firewall restore...", module="proctoring_service")
                        emergency_success = self.firewall._emergency_force_firewall_restore()
                        if emergency_success:
                            logger.info("Emergency firewall restore successful", module="proctoring_service")
                            cleanup_results[-1] = ("firewall_emergency", True, "Emergency restore successful")
                        
            except Exception as e:
                logger.error(f"Exception during firewall cleanup: {e}", module="proctoring_service")
                cleanup_results.append(("firewall", False, f"Exception: {str(e)}"))
                
                # Attempt emergency restore even when normal cleanup raises.
                try:
                    if self.firewall._is_isolated:
                        logger.warning("Emergency restore due to exception...", module="proctoring_service")
                        self.firewall._emergency_force_firewall_restore()
                except Exception as e2:
                    logger.error(f"Emergency restore also failed: {e2}", module="proctoring_service")

        # 4) Verify cleanup status.
        if self.firewall:
            try:
                status = self.firewall.verify_isolation_status()
                if not status.get("isolated", False):
                    logger.info(f"Firewall status verified: {status.get('status')}", module="proctoring_service")
                else:
                    logger.warning(f"Firewall still isolated after cleanup! Status: {status.get('status')}", module="proctoring_service")
            except Exception as e:
                logger.warning(f"Could not verify firewall status: {e}", module="proctoring_service")

        with self._state_lock:
            self._security_engaged = False
        
        # Log cleanup summary.
        successful = sum(1 for _, success, _ in cleanup_results if success)
        total = len(cleanup_results)
        logger.info(f"Security lockdown disengagement summary: {successful}/{total} systems cleaned up", 
                   module="proctoring_service")
        
        for component, success, detail in cleanup_results:
            status = "✓" if success else "✗"
            logger.info(f"  {status} {component}: {detail or 'OK'}", module="proctoring_service")

    def get_security_status(self) -> dict:
        """
        Get current status of security lockdown features.
        
        Returns:
            dict with firewall, lockdown, snapshot_uploader status
        """
        with self._state_lock:
            quarantine_size = len(self._runtime_quarantine)
            security_engaged = bool(self._security_engaged)

        return {
            "engaged": security_engaged,
            "firewall": {
                "available": self.firewall is not None,
                "active": security_engaged and self.firewall is not None,
            },
            "lockdown": {
                "available": self.lockdown is not None,
                "active": self.lockdown.is_locked() if self.lockdown else False,
            },
            "snapshots": {
                "available": SnapshotUploader is not None,
                "active": self.snapshot_uploader is not None and self.snapshot_uploader.is_running(),
                "buffered": self.snapshot_uploader.get_buffer_size() if self.snapshot_uploader else 0,
            },
            "runtime_policy": {
                "keyboard_lockdown_enabled": self._enable_keyboard_lockdown,
                "keyboard_lockdown_required": self._require_keyboard_lockdown,
                "lockdown_block_input": self._lockdown_block_input,
                "strict_os_lockdown": self._strict_os_lockdown,
                "firewall_isolation_enabled": self._enable_firewall_isolation,
                "auto_terminate_enabled": self._enable_runtime_auto_terminate,
                "auto_terminate_cooldown_sec": self._auto_terminate_cooldown_sec,
                "auto_terminate_max_per_scan": self._auto_terminate_max_per_scan,
                "quarantine_size": quarantine_size,
                "full_lockdown_enabled": self._enable_full_lockdown,
                "full_lockdown_scan_interval_sec": self._full_lockdown_scan_interval,
            },
        }

    def _is_system_critical_process(self, proc: psutil.Process) -> bool:
        """Best-effort guardrail to avoid killing critical OS processes."""
        try:
            info = getattr(proc, "info", {}) or {}
            name = (info.get("name") or proc.name() or "").lower()
            if name in self._full_lockdown_allowlist:
                return True
            if name in {
                "explorer.exe",
                "shellexperiencehost.exe",
                "startmenuexperiencehost.exe",
                "searchhost.exe",
                "dwm.exe",
                "textinputhost.exe",
                "lockapp.exe",
                "sihost.exe",
                "applicationframehost.exe",
                "widgets.exe",
                "taskviewhost.exe",
                "multitaskingviewframehost.exe",
            }:
                return True

            # Never terminate Windows OS binaries/system apps from lockdown watchdog.
            exe_path = ""
            try:
                exe_path = (info.get("exe") or proc.exe() or "").lower()
            except Exception:
                exe_path = ""
            if exe_path:
                windir = (os.environ.get("WINDIR") or r"C:\Windows").lower().rstrip("\\/")
                systemapps = f"{windir}\\systemapps\\"
                system32 = f"{windir}\\system32\\"
                if exe_path.startswith(systemapps) or exe_path.startswith(system32):
                    return True

            # Avoid killing processes owned by core shell parents.
            try:
                parent = proc.parent()
                parent_name = (parent.name() or "").lower() if parent else ""
                if parent_name in {
                    "explorer.exe",
                    "sihost.exe",
                    "shellexperiencehost.exe",
                    "startmenuexperiencehost.exe",
                }:
                    return True
            except Exception:
                pass

            username = (info.get("username") or "").lower()
            if not username:
                try:
                    username = (proc.username() or "").lower()
                except Exception:
                    username = ""
            if username in {
                "nt authority\\system",
                "system",
                "nt authority\\local service",
                "nt authority\\network service",
            }:
                return True

            if proc.pid <= 4:
                return True
        except Exception:
            return True
        return False

    def _start_full_lockdown_watchdog(self) -> None:
        """Start runtime guard that can suppress overlays or close all user apps."""
        with self._state_lock:
            if self._full_lockdown_thread and self._full_lockdown_thread.is_alive():
                return

        if self._full_lockdown_close_all_apps:
            self._full_lockdown_baseline_pids = set()
        else:
            self._full_lockdown_baseline_pids = set(psutil.pids())
        self._full_lockdown_started_epoch = time.time()
        self._full_lockdown_quarantine = {}
        self._full_lockdown_stop.clear()

        def _identity_key(proc: psutil.Process) -> str:
            try:
                exe = (proc.info.get("exe") or proc.exe() or "").strip().lower()  # type: ignore[attr-defined]
                if exe:
                    return f"exe:{exe}"
            except Exception:
                pass
            try:
                name = (proc.info.get("name") or proc.name() or "").strip().lower()  # type: ignore[attr-defined]
            except Exception:
                name = ""
            return f"name:{name or 'unknown'}"

        def _within_kill_cooldown(proc: psutil.Process, now_ts: float) -> bool:
            key = _identity_key(proc)
            last = self._full_lockdown_quarantine.get(key)
            if last is None:
                return False
            return (now_ts - float(last)) < self._full_lockdown_kill_cooldown_sec

        def _mark_kill(proc: psutil.Process, now_ts: float) -> None:
            key = _identity_key(proc)
            self._full_lockdown_quarantine[key] = now_ts

        def _watchdog_loop() -> None:
            while not self._full_lockdown_stop.wait(self._full_lockdown_scan_interval):
                if not self._started:
                    continue
                # Avoid invoking Qt/UI callbacks from this worker thread.
                # Foreground enforcement remains on the main-thread timer.

                try:
                    own_pid = os.getpid()
                    own_process = psutil.Process(own_pid)
                    protected_pids = {own_pid}
                    killed_this_scan = 0
                    try:
                        protected_pids.update(p.pid for p in own_process.parents())
                    except Exception:
                        pass
                    try:
                        protected_pids.update(p.pid for p in own_process.children(recursive=True))
                    except Exception:
                        pass

                    for proc in psutil.process_iter(["pid", "name", "create_time", "username"]):
                        if killed_this_scan >= self._full_lockdown_max_kills_per_scan:
                            break
                        now_ts = time.time()
                        pid = int(proc.info.get("pid") or 0)
                        if pid in protected_pids:
                            continue
                        if (not self._full_lockdown_close_all_apps) and pid in self._full_lockdown_baseline_pids:
                            continue
                        if self._is_system_critical_process(proc):
                            continue

                        created_at = float(proc.info.get("create_time") or 0.0)
                        if created_at <= 0:
                            continue
                        # Non-strict mode targets processes launched after lockdown start.
                        if (not self._full_lockdown_close_all_apps) and created_at < (self._full_lockdown_started_epoch - 1.0):
                            continue
                        if _within_kill_cooldown(proc, now_ts):
                            continue

                        ok, msg = self.kill_process(pid, kill_all_matching=True)
                        if ok:
                            _mark_kill(proc, now_ts)
                            killed_this_scan += 1
                            logger.warning(f"Full lockdown terminated newly launched process: {msg}", module="proctoring_service")
                        else:
                            logger.warning(f"Full lockdown could not terminate PID {pid}: {msg}", module="proctoring_service")

                    # Overlay suppression: terminate non-allowed foreground owner.
                    if win32gui and win32process and killed_this_scan < self._full_lockdown_max_kills_per_scan:
                        try:
                            fg = win32gui.GetForegroundWindow()
                            if fg and win32gui.IsWindowVisible(fg):
                                _, fg_pid = win32process.GetWindowThreadProcessId(fg)
                                if fg_pid and fg_pid not in protected_pids:
                                    p = psutil.Process(int(fg_pid))
                                    if (not self._full_lockdown_close_all_apps) and int(fg_pid) in self._full_lockdown_baseline_pids:
                                        continue
                                    if not self._is_system_critical_process(p):
                                        now_ts = time.time()
                                        created_at = 0.0
                                        try:
                                            created_at = float(p.create_time() or 0.0)
                                        except Exception:
                                            created_at = 0.0
                                        if (not self._full_lockdown_close_all_apps) and created_at < (self._full_lockdown_started_epoch - 1.0):
                                            continue
                                        if _within_kill_cooldown(p, now_ts):
                                            continue
                                        title = (win32gui.GetWindowText(fg) or "").strip()
                                        ok, msg = self.kill_process(int(fg_pid), kill_all_matching=True)
                                        if ok:
                                            _mark_kill(p, now_ts)
                                            killed_this_scan += 1
                                            logger.warning(
                                                f"Full lockdown removed foreground overlay process: {msg} title='{title[:64]}'",
                                                module="proctoring_service",
                                            )
                        except Exception:
                            pass

                except Exception as e:
                    logger.debug(f"Full lockdown watchdog error: {e}", module="proctoring_service")

        worker = threading.Thread(
            target=_watchdog_loop,
            daemon=True,
            name="Full-Lockdown-Watchdog",
        )
        with self._state_lock:
            self._full_lockdown_thread = worker
        worker.start()
        logger.info("Full lockdown watchdog started", module="proctoring_service")

    def _stop_full_lockdown_watchdog(self) -> None:
        with self._state_lock:
            worker = self._full_lockdown_thread
            self._full_lockdown_thread = None
        if not worker:
            return
        self._full_lockdown_stop.set()
        if worker.is_alive():
            worker.join(timeout=2.0)
        logger.info("Full lockdown watchdog stopped", module="proctoring_service")
    
    def verify_cleanup_status(self) -> dict:
        """
        Verify that all security features have been properly cleaned up.
        
        Returns:
            dict with cleanup verification status and details
        """
        cleanup_status = {
            "all_clean": True,
            "timestamp": __import__('time').time(),
            "components": {}
        }
        
        # Check firewall state.
        if self.firewall:
            firewall_isolated = self.firewall.is_isolated()
            firewall_detail = self.firewall.verify_isolation_status()
            cleanup_status["components"]["firewall"] = {
                "is_isolated_flag": firewall_isolated,
                "verification": firewall_detail,
                "clean": not firewall_isolated and not firewall_detail.get("isolated", False)
            }
            if not cleanup_status["components"]["firewall"]["clean"]:
                cleanup_status["all_clean"] = False
        
        # Check lockdown state.
        if self.lockdown:
            lockdown_locked = self.lockdown.is_locked()
            cleanup_status["components"]["lockdown"] = {
                "is_locked": lockdown_locked,
                "clean": not lockdown_locked
            }
            if not cleanup_status["components"]["lockdown"]["clean"]:
                cleanup_status["all_clean"] = False
        
        # Check snapshot uploader state.
        if self.snapshot_uploader:
            uploader_running = self.snapshot_uploader.is_running()
            cleanup_status["components"]["snapshot_uploader"] = {
                "is_running": uploader_running,
                "clean": not uploader_running
            }
            if not cleanup_status["components"]["snapshot_uploader"]["clean"]:
                cleanup_status["all_clean"] = False
        
        # Log cleanup summary.
        if cleanup_status["all_clean"]:
            logger.info("✅ All security features cleanly disengaged", module="proctoring_service")
        else:
            logger.warning(f"⚠️  Incomplete cleanup detected: {cleanup_status}", module="proctoring_service")
        
        return cleanup_status

    def collect_alerts(self) -> List[str]:
        alerts: List[str] = []

        with self._state_lock:
            if self._tamper_messages:
                alerts.extend(self._tamper_messages)
                self._tamper_messages.clear()

        if self.audio:
            t = self.audio.get_latest_telemetry()
            alerts.extend(t.get("flags", []))

        # Lazy-initialize vision if needed
        self._ensure_vision_initialized()
        if self.vision:
            t = self.vision.get_latest_telemetry()
            alerts.extend(t.get("flags", []))

        if self.process:
            result = self.process.get_latest_result()
            with self._state_lock:
                self._last_scan_result = result or {}
            alerts.extend(result.get("flags", []))
            scan_error = str((result or {}).get("scan_error") or "").strip()
            if scan_error:
                logger.debug(
                    f"Process monitor degraded (internal): {scan_error}",
                    module="proctoring_service",
                )

        seen = set()
        deduped = []
        for msg in alerts:
            text = str(msg or "").strip()
            if not text:
                continue
            if self._is_non_violation_alert(text):
                logger.debug(
                    f"Ignoring non-violation runtime alert: {text}",
                    module="proctoring_service",
                )
                continue
            if text not in seen:
                seen.add(text)
                deduped.append(text)

        # Transition-based scoring avoids repeated counting of persistent alerts.
        should_fire_threshold = False
        violation_snapshot = 0
        threshold_snapshot = self._violation_threshold

        with self._state_lock:
            threshold_reached = self._threshold_reached

        if not threshold_reached:
            now = time.time()
            current_keys = set()
            score_increment = 0

            with self._state_lock:
                for msg in deduped:
                    key = self._normalize_alert_key(msg)
                    current_keys.add(key)
                    state = self._alert_active_state.get(key)
                    if state is None:
                        self._alert_active_state[key] = {
                            "first_seen": now,
                            "last_seen": now,
                            "last_counted": now,
                        }
                        score_increment += 1
                        continue

                    state["last_seen"] = now
                    if now - float(state.get("last_counted", 0.0)) >= self._alert_recount_interval:
                        state["last_counted"] = now
                        score_increment += 1

                # Remove inactive alerts once they disappear.
                inactive_keys = [k for k in self._alert_active_state.keys() if k not in current_keys]
                for key in inactive_keys:
                    self._alert_active_state.pop(key, None)

            if score_increment > self._max_violation_increment_per_poll:
                score_increment = self._max_violation_increment_per_poll

            if score_increment > 0:
                with self._state_lock:
                    self._violation_count += score_increment
                    violation_snapshot = self._violation_count
                logger.warning(
                    f"Violation count increased by {score_increment} to {violation_snapshot}/{threshold_snapshot}",
                    module="proctoring_service"
                )
            else:
                with self._state_lock:
                    violation_snapshot = self._violation_count

            # Check whether threshold is newly reached.
            with self._state_lock:
                if self._violation_count >= self._violation_threshold and not self._threshold_reached:
                    self._threshold_reached = True
                    should_fire_threshold = True
                violation_snapshot = self._violation_count

            if should_fire_threshold:
                logger.critical_security_event(
                    f"CRITICAL: Violation threshold reached ({violation_snapshot}/{threshold_snapshot}). "
                    "Exam must be terminated.",
                    module="proctoring_service"
                )

                # Trigger threshold callback if registered.
                if self._threshold_callback:
                    try:
                        self._threshold_callback()
                    except Exception as e:
                        logger.error(f"Threshold callback error: {e}", module="proctoring_service")
        else:
            with self._state_lock:
                violation_snapshot = self._violation_count

        if deduped and self._telemetry:
            try:
                payload = self._telemetry.generate_payload(
                    {
                        "runtime_alerts": deduped,
                        "violation_count": violation_snapshot,
                        "threshold": threshold_snapshot,
                    }
                )
                server_resp = self._telemetry.send_telemetry(payload)
                decision = (server_resp or {}).get("server_decision") or {}
                action = str(decision.get("action") or "").strip().lower()
                reasons = decision.get("reasons") or []
                reason_text = ", ".join(str(x) for x in reasons) if isinstance(reasons, list) else str(reasons)

                if self._enforce_server_decision and action:
                    if action == "block":
                        logger.critical_security_event(
                            f"Server decision BLOCK received. reasons={reason_text or 'n/a'}",
                            module="proctoring_service",
                        )
                        if not self._threshold_reached:
                            self._threshold_reached = True
                            if self._threshold_callback:
                                try:
                                    self._threshold_callback()
                                except Exception as e:
                                    logger.error(f"Threshold callback error: {e}", module="proctoring_service")
                    elif action == "warn":
                        logger.warning(
                            f"Server decision WARN received. reasons={reason_text or 'n/a'}",
                            module="proctoring_service",
                        )
                        # Add synthetic alert so warn decisions participate in local violation scoring.
                        with self._state_lock:
                            self._tamper_messages.append(f"server_warn:{reason_text or 'policy_warning'}")
            except Exception:
                # Keep runtime monitoring resilient if telemetry transport fails.
                pass
        
            # Periodically publish environment-check telemetry.
        current_time = time.time()
        with self._state_lock:
            should_env_check = (
                bool(self._env_checker and self._telemetry)
                and (current_time - self._last_env_check_time >= self._env_check_interval)
            )

        if should_env_check:
            try:
                with self._state_lock:
                    self._last_env_check_time = current_time
                env_results = self._env_checker.run_all_checks()
                if env_results:
                    # run_all_checks uses credentials already installed during telemetry setup.
                    binary_hash_preview = str(env_results.get("binary_integrity_hash") or "N/A")[:16]
                    logger.debug(
                        f"Environmental checks: binary_hash={binary_hash_preview}...",
                        module="proctoring_service",
                    )
            except Exception as e:
                logger.debug(f"Environmental check error: {e}", module="proctoring_service")
        
        return deduped

    def _normalize_alert_key(self, message: str) -> str:
        """Normalize dynamic alert text into a stable key for counting/dedup."""
        text = (message or "").strip().lower()
        text = re.sub(r"pid\s*\d+", "pid", text)
        text = re.sub(r"\b\d+(?:\.\d+)?\b", "#", text)
        text = re.sub(r"'[^']*'", "''", text)
        text = re.sub(r'"[^"]*"', '""', text)
        text = re.sub(r"\s+", " ", text)
        return text[:180]

    def _is_non_violation_alert(self, message: str) -> bool:
        """Return True for internal diagnostics that should never be user-facing violations."""
        text = (message or "").strip().lower()
        if not text:
            return True

        # Internal provider glitches are diagnostic noise and not user-facing violations.
        if "process scan error" in text:
            return True

        return False

    def _on_process_violation(self, result: dict) -> None:
        """
        Callback from ProcessMonitor background scanner.

        Optionally auto-terminate flagged processes during active exam runtime.
        """
        with self._state_lock:
            self._last_scan_result = result or {}

        if not self._enable_runtime_auto_terminate or not self._started:
            return

        now = time.time()
        with self._state_lock:
            stale = [pid for pid, ts in self._runtime_quarantine.items() if now - ts > self._runtime_quarantine_ttl_sec]
        for pid in stale:
            with self._state_lock:
                self._runtime_quarantine.pop(pid, None)

        flagged_pids: List[int] = []
        for line in (result or {}).get("flags", []) or []:
            match = re.search(r"PID\s*(\d+)", str(line), re.IGNORECASE)
            if not match:
                continue
            try:
                pid = int(match.group(1))
                if pid > 0 and pid != os.getpid():
                    flagged_pids.append(pid)
            except Exception:
                continue

        if not flagged_pids:
            return

        killed = 0
        for pid in sorted(set(flagged_pids)):
            with self._state_lock:
                last = self._runtime_quarantine.get(pid)
            if last and (now - last) < self._auto_terminate_cooldown_sec:
                continue

            ok, msg = self.kill_process(pid)
            if ok or "no longer running" in (msg or "").lower():
                with self._state_lock:
                    self._runtime_quarantine[pid] = now
                killed += 1
                logger.warning(
                    f"Runtime auto-terminate action: {msg}",
                    module="proctoring_service",
                )
            else:
                logger.warning(
                    f"Runtime auto-terminate failed for PID {pid}: {msg}",
                    module="proctoring_service",
                )

            if killed >= self._auto_terminate_max_per_scan:
                break

    def _on_hw_alert(self, event_type: str, detail: dict) -> None:
        """Callback from HardwareChecker continuous watcher."""
        detail = detail or {}
        if event_type == "usb_inserted":
            message = f"Hardware alert: USB inserted mid-exam ({detail.get('new_devices', [])})"
        elif event_type == "monitor_changed":
            message = (
                f"Hardware alert: monitor count changed mid-exam "
                f"({detail.get('previous')} -> {detail.get('current')})"
            )
        else:
            message = f"Hardware alert: {event_type}"

        logger.critical_security_event(message, module="proctoring_service")
        with self._state_lock:
            self._tamper_messages.append(message)

    def get_identity_gaze_status(self) -> dict:
        """Return lightweight gaze/face telemetry for Step 4 biometric screen."""
        # Initialize vision only when needed.
        self._ensure_vision_initialized()
        if not self.vision:
            return {
                "available": False,
                "face_count": 0,
                "yaw": 0.0,
                "pitch": 0.0,
                "flags": ["Vision proctor unavailable"],
            }

        telemetry = self.vision.get_latest_telemetry()
        stats = telemetry.get("stats", {})
        return {
            "available": True,
            "face_count": int(stats.get("face_count", 0) or 0),
            "yaw": float(stats.get("yaw_deg", 0.0) or 0.0),
            "pitch": float(stats.get("pitch_deg", 0.0) or 0.0),
            "flags": telemetry.get("flags", []),
        }

    def list_malicious_processes(self) -> List[dict]:
        """
        Return suspicious process candidates with PID, name, executable, and reason.

        Combines process-keyword matching with latest process monitor findings.
        """
        results: List[dict] = []

        # Refresh scan on demand for current review page state.
        if self.process:
            try:
                self._last_scan_result = self.process.scan_environment()
            except Exception as e:
                logger.warning(f"Process scan failed: {e}", module="proctoring_service")

        pid_reasons: dict[int, str] = {}
        for line in self._last_scan_result.get("flags", []) if self._last_scan_result else []:
            m = re.search(r"PID\s*(\d+)", line)
            if m:
                pid_reasons[int(m.group(1))] = line

        own_pid = os.getpid()
        own_exe = None
        try:
            own_exe = os.path.abspath(psutil.Process(own_pid).exe()).lower()
        except Exception:
            pass
        
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pid = int(proc.info.get("pid") or 0)
                if pid == own_pid:
                    continue
                name = (proc.info.get("name") or "").lower()
                proc_exe = ""
                try:
                    proc_exe = (proc.info.get("exe") or proc.exe() or "").lower()
                except Exception:
                    proc_exe = ""
                if not name:
                    continue
                
                # Ignore own executable name.
                if name in ("observeproctor.exe", "observeproctor"):
                    continue
                
                # Also compare executable path to handle renamed binaries.
                if own_exe and proc_exe and os.path.abspath(proc_exe) == own_exe:
                    continue
                
                # Ignore direct parent/child relation with current process.
                try:
                    if proc.ppid() == own_pid or psutil.Process(own_pid).ppid() == pid:
                        continue
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                reason = pid_reasons.get(pid)
                if reason is None:
                    for kw in SUSPICIOUS_PROC_KEYWORDS:
                        if str(kw).lower() in name:
                            reason = f"Suspicious keyword '{kw}' in process name"
                            break
                if reason is None:
                    continue

                results.append(
                    {
                        "pid": pid,
                        "name": proc.info.get("name") or str(pid),
                        "exe": proc_exe,
                        "reason": reason,
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        dedup = {}
        for item in results:
            dedup[item["pid"]] = item
        return sorted(dedup.values(), key=lambda x: (x["name"].lower(), x["pid"]))

    def kill_process(
        self,
        pid: int,
        kill_all_matching: bool = False,
        force_immediate: bool = False,
    ) -> tuple[bool, str]:
        """
        Terminate a process tree by PID and return status tuple.

        Args:
            pid: Root process ID.
            kill_all_matching: When True, also terminate sibling instances that share
                the same executable path (preferred) or process name.
            force_immediate: When True, skip graceful terminate and use hard kill.
        """
        try:
            root = psutil.Process(pid)
            name = root.name()
            root_name = (name or "").strip().lower()
            root_exe = ""
            try:
                root_exe = (root.exe() or "").strip().lower()
            except Exception:
                root_exe = ""

            # Browser-style apps often spawn child trees; terminate full process tree.
            targets = []
            try:
                targets.extend(root.children(recursive=True))
            except Exception:
                pass
            targets.append(root)

            if kill_all_matching:
                try:
                    for proc in psutil.process_iter(["pid", "name"]):
                        try:
                            if int(proc.pid) <= 0:
                                continue
                            p_name = (proc.info.get("name") or "").strip().lower()
                            p_exe = ""
                            try:
                                p_exe = (proc.info.get("exe") or proc.exe() or "").strip().lower()
                            except Exception:
                                p_exe = ""

                            same_identity = False
                            if root_exe and p_exe:
                                same_identity = p_exe == root_exe
                            elif root_name and p_name:
                                same_identity = p_name == root_name

                            if same_identity:
                                targets.append(proc)
                                try:
                                    targets.extend(proc.children(recursive=True))
                                except Exception:
                                    pass
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                except Exception:
                    pass

            own_pid = os.getpid()
            dedup: dict[int, psutil.Process] = {}
            for proc in targets:
                try:
                    ppid = int(proc.pid)
                    if ppid > 0 and ppid != own_pid:
                        dedup[ppid] = proc
                except Exception:
                    continue

            procs = list(dedup.values())
            if not procs:
                return False, f"No terminable processes found for PID {pid}."

            if force_immediate:
                alive = list(procs)
            else:
                for proc in procs:
                    try:
                        proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                _, alive = psutil.wait_procs(procs, timeout=3)

            for proc in alive:
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            _, still_alive = psutil.wait_procs(alive, timeout=2)

            # Final Windows fallback for stubborn process trees.
            if still_alive and platform.system() == "Windows":
                try:
                    result = subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True,
                        text=True,
                        creationflags=0x08000000,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        still_alive = []
                except Exception:
                    pass

            if psutil.pid_exists(pid):
                alive_names = []
                for proc in still_alive:
                    try:
                        alive_names.append(f"{proc.name()}({proc.pid})")
                    except Exception:
                        pass
                suffix = f" Remaining: {', '.join(alive_names)}" if alive_names else ""
                return False, f"Failed to terminate PID {pid}.{suffix}"

            if kill_all_matching:
                remaining_same = []
                try:
                    for proc in psutil.process_iter(["pid", "name"]):
                        try:
                            ppid = int(proc.pid)
                            p_name = (proc.info.get("name") or "").strip().lower()
                            p_exe = ""
                            try:
                                p_exe = (proc.info.get("exe") or proc.exe() or "").strip().lower()
                            except Exception:
                                p_exe = ""
                            same_identity = False
                            if root_exe and p_exe:
                                same_identity = p_exe == root_exe
                            elif root_name and p_name:
                                same_identity = p_name == root_name
                            if same_identity:
                                remaining_same.append(f"{proc.info.get('name') or p_name}({ppid})")
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                except Exception:
                    pass
                if remaining_same:
                    return False, f"Process restarted or sibling instances remain: {', '.join(remaining_same[:5])}"

            mode = "hard-killed" if force_immediate else "terminated"
            msg = f"{mode.capitalize()} process tree: {name} (PID {pid})"
            logger.warning(msg, module="proctoring_service")
            return True, msg
        except psutil.NoSuchProcess:
            return False, f"Process {pid} is no longer running."
        except psutil.AccessDenied:
            return False, f"Access denied when terminating PID {pid}."
        except Exception as e:
            return False, f"Failed to terminate PID {pid}: {e}"

    def get_process_snapshot(self) -> dict:
        """Return latest process monitor result for diagnostics/upload."""
        snapshot = {}
        if self.process:
            try:
                snapshot = self.process.get_latest_result() or {}
            except Exception:
                snapshot = {}
        if not snapshot:
            snapshot = dict(self._last_scan_result or {})
        return snapshot

