"""
Observe Proctoring desktop application entry point.

Coordinates UI screen flow, proctoring service integration, and startup/shutdown
hardening for exam sessions.
"""

import sys
import os
import threading
import traceback
import ctypes
import platform
import warnings
import time
import requests
from PyQt6.QtWidgets import (
    QApplication, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

# UI screens.
from ui.splash_screen import SplashScreen
from ui.login_screen import LoginScreen
from ui.app_closer_screen import AppCloserScreen
from ui.identity_screen import IdentityScreen
from ui.terms_screen import TermsScreen
from ui.securing_screen import SecuringScreen
from ui.components.exam import ExamScreen
from env_loader import load_env
def show_error_popup(parent, title, text):
    from ui.components.premium_popup import PremiumPopup
    PremiumPopup.show_message(
        parent=parent,
        title=title or "Error",
        message=text or "An unexpected error occurred.",
        icon=QMessageBox.Icon.Warning,
        buttons=QMessageBox.StandardButton.Ok
    )


try:
    from core.proctoring_service import ProctoringService
except Exception:
    ProctoringService = None

try:
    from core.backend_config import get_backend_url
except Exception:
    get_backend_url = None

try:
    from core.exam_api import ExamApiClient
except Exception:
    ExamApiClient = None

try:
    from core.logger import logger as _AUDIT_LOGGER
except Exception:
    _AUDIT_LOGGER = None


class _StreamAuditBridge:
    """Tee stream output to console + tamper-evident audit log."""

    def __init__(self, wrapped_stream, level: str, module: str):
        self._wrapped = wrapped_stream
        self._level = level
        self._module = module
        self._buffer = ""

    def _get_fallback_stream(self):
        if self._module == "stderr":
            return getattr(sys, "__stderr__", None)
        return getattr(sys, "__stdout__", None)

    def _safe_write(self, text: str) -> None:
        target = self._wrapped or self._get_fallback_stream()
        if target is None:
            return
        try:
            target.write(text)
        except Exception:
            # Stream forwarding should never interrupt application flow.
            pass

    def write(self, data):
        text = data if isinstance(data, str) else str(data)
        self._safe_write(text)
        self._buffer += text

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._log_line(line)
        return len(text)

    def flush(self):
        if self._buffer:
            self._log_line(self._buffer)
            self._buffer = ""
        target = self._wrapped or self._get_fallback_stream()
        if target is None:
            return
        try:
            target.flush()
        except Exception:
            pass

    def _log_line(self, line: str):
        msg = line.strip()
        if not msg or _AUDIT_LOGGER is None:
            return
        try:
            # Use direct file write path to avoid console recursion.
            _AUDIT_LOGGER._write(self._level, self._module, msg)
        except Exception:
            pass

    def __getattr__(self, item):
        target = self._wrapped or self._get_fallback_stream()
        if target is None:
            raise AttributeError(item)
        return getattr(target, item)


_ORIG_SHOWWARNING = warnings.showwarning


def _audit_showwarning(message, category, filename, lineno, file=None, line=None):
    """Mirror Python warnings into tamper-evident audit log."""
    try:
        rendered = warnings.formatwarning(message, category, filename, lineno, line)
        if _AUDIT_LOGGER is not None:
            _AUDIT_LOGGER._write("WARNING", "python_warning", rendered.strip())
    except Exception:
        pass
    _ORIG_SHOWWARNING(message, category, filename, lineno, file=file, line=line)


def _install_runtime_audit_capture() -> None:
    """Capture print/stdout/stderr/warnings to audit log while app is running."""
    if os.environ.get("OBSERVE_CAPTURE_STD_STREAMS", "1") != "1":
        return
    if _AUDIT_LOGGER is None:
        return

    sys.stdout = _StreamAuditBridge(sys.stdout, "INFO", "stdout")
    sys.stderr = _StreamAuditBridge(sys.stderr, "ERROR", "stderr")
    warnings.showwarning = _audit_showwarning


def _verify_audit_chain_on_startup() -> bool:
    """Verify audit log chain; auto-reset if broken so startup is never blocked."""
    if _AUDIT_LOGGER is None:
        return True
    try:
        ok, reason = _AUDIT_LOGGER.verify_log_integrity()
        if ok:
            print(f"[Startup] Audit log integrity OK: {reason}")
            return True

        print(f"[Startup] Audit log integrity FAILED: {reason}")
        print("[Startup] Attempting to reset corrupted audit log...")

        # Remove or truncate the broken log so a fresh chain can start.
        log_path = getattr(_AUDIT_LOGGER, "log_file", None)
        if log_path and os.path.exists(log_path):
            try:
                os.remove(log_path)
                print(f"[Startup] Removed broken log: {log_path}")
            except Exception as rm_err:
                print(f"[Startup] Could not remove log file: {rm_err}")
                try:
                    open(log_path, "w").close()
                    print(f"[Startup] Truncated broken log: {log_path}")
                except Exception as trunc_err:
                    print(f"[Startup] Could not truncate log: {trunc_err}")
                    return True

        # Reinitialize the logger with a fresh chain.
        try:
            _AUDIT_LOGGER.__init__()
            print("[Startup] Audit logger re-initialised with fresh chain.")
        except Exception:
            pass

        # Run a final verification on the new log chain.
        try:
            ok2, reason2 = _AUDIT_LOGGER.verify_log_integrity()
            if ok2:
                print(f"[Startup] Audit log reset successful: {reason2}")
        except Exception:
            print("[Startup] Audit log reset — starting with empty chain.")

        return True

    except Exception as e:
        print(f"[Startup] Audit log verification error: {e}")
        return True

class _BootstrapWorker(QThread):
    success = pyqtSignal(dict)
    http_error = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, client, exam_launch_code: str | None):
        super().__init__()
        self._client = client
        self._exam_launch_code = exam_launch_code

    def run(self):
        try:
            data = self._client.bootstrap(exam_launch_code=self._exam_launch_code)
            self.success.emit(data)
        except requests.HTTPError as exc:
            body = ""
            if exc.response is not None:
                try:
                    body = (exc.response.text or "")[:400]
                except Exception:
                    body = ""
            self.http_error.emit(body or str(exc))
        except Exception as exc:
            self.failed.emit(str(exc))


class _SubmitWorker(QThread):
    success = pyqtSignal(dict)
    http_error = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, client, payload: dict):
        super().__init__()
        self._client = client
        self._payload = payload

    def run(self):
        try:
            data = self._client.submit_exam(**self._payload)
            self.success.emit(data)
        except requests.HTTPError as exc:
            body = ""
            if exc.response is not None:
                try:
                    body = (exc.response.text or "")[:400]
                except Exception:
                    body = ""
            self.http_error.emit(body or str(exc))
        except Exception as exc:
            self.failed.emit(str(exc))


class ObserveProctorApp:
    def __init__(self, app: QApplication):
        self.app = app
        self.user_email = None
        self.login_token = None
        self.exam_launch_code = None
        self.backend_url = (
            get_backend_url()
            if get_backend_url
            else (os.environ.get("OBSERVE_SERVER_URL") or os.environ.get("OBSERVE_BACKEND_URL") or "")
        )
        if not self.backend_url:
            raise RuntimeError("Missing backend URL. Set OBSERVE_SERVER_URL in .env for production startup.")
        self.proctoring_service = (
            ProctoringService(backend_url=self.backend_url) if ProctoringService else None
        )
        self._exam_api_client = None
        self._active_exam_id = None
        self._active_attempt_id = None
        self._bootstrap_worker = None
        self._submit_worker = None
        self._bootstrap_in_flight = False
        self._submit_in_flight = False
        self._worker_lock = threading.RLock()
        self._last_submit_data: dict | None = None
        self._critical_alert_last_ts: dict[str, float] = {}
        self._critical_alert_cooldown_seconds = 12.0
        self._cleanup_started = False
        self._force_exam_topmost = (os.environ.get("OBSERVE_FORCE_EXAM_TOPMOST", "1").strip().lower() in ("1", "true", "yes", "on"))
        self._focus_guard_interval_ms = max(500, int(os.environ.get("OBSERVE_FOCUS_GUARD_INTERVAL_MS", "1200") or "1200"))
        self._focus_guard_timer = QTimer()
        self._focus_guard_timer.setInterval(self._focus_guard_interval_ms)
        self._focus_guard_timer.timeout.connect(self._enforce_exam_focus)

        # Create main window
        self.main_window = QStackedWidget()
        self.main_window.setWindowTitle("Observe Proctoring Environment")
        self.main_window.setMinimumSize(1024, 768)

        # Create screens.
        self.splash = SplashScreen()
        self.login_screen = LoginScreen(server_url=self.backend_url)
        self.app_closer = AppCloserScreen()
        self.identity_screen = IdentityScreen()
        self.terms_screen = TermsScreen()
        self.securing_screen = SecuringScreen()
        self.exam_screen = ExamScreen()

        # Add screens to stack.
        self.main_window.addWidget(self.splash)            # index 0
        self.main_window.addWidget(self.login_screen)       # index 1
        self.main_window.addWidget(self.app_closer)         # index 2
        self.main_window.addWidget(self.identity_screen)    # index 3
        self.main_window.addWidget(self.terms_screen)       # index 4
        self.main_window.addWidget(self.securing_screen)    # index 5
        self.main_window.addWidget(self.exam_screen)        # index 6

        # Setup signal connections.
        self._setup_connections()
        self._install_error_handlers()

        # Apply global styling.
        self._apply_theme()

    def _apply_theme(self):
        """Apply global styling."""
        self.app.setStyle("Fusion")
        self.app.setStyleSheet("""
            QWidget {
                background-color: #F8FAFC;
                color: #0F172A;
                font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
            }
            QLabel { color: #0F172A; }
            QPushButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton:disabled { background-color: #E2E8F0; color: #94A3B8; }
            QMessageBox QLabel { color: #0F172A; background: transparent; }
        """)

    def _setup_connections(self):
        """Connect screen signals."""
        # Splash screen signals.
        self.splash.finished.connect(self._go_to_login)
        self.splash.shutdown.connect(self._on_shutdown)

        # Login screen signals.
        self.login_screen.login_success.connect(self._on_login_success)
        self.login_screen.error_occurred.connect(
            lambda msg: self._show_error_popup("Login Error", msg)
        )

        # App closer signals.
        self.app_closer.proceed.connect(self._go_to_identity)
        self.app_closer.cancelled.connect(self._on_shutdown)
        self.app_closer.error_occurred.connect(
            lambda msg: self._show_error_popup("System Sandbox Error", msg)
        )

        # Identity screen signals.
        self.identity_screen.identity_confirmed.connect(self._go_to_terms)
        self.identity_screen.error_occurred.connect(
            lambda msg: self._show_error_popup("Biometric Error", msg)
        )

        # Terms screen signals.
        self.terms_screen.exam_started.connect(self._go_to_securing)

        # Securing screen signals.
        self.securing_screen.securing_complete.connect(self._go_to_exam)
        self.securing_screen.error_occurred.connect(
            lambda msg: self._show_error_popup("Security Initialization Error", msg)
        )

        # Exam screen submission wiring.
        if hasattr(self.exam_screen, "exam_submitted"):
            self.exam_screen.exam_submitted.connect(self._on_exam_submitted)
        elif hasattr(self.exam_screen, "transition_requested"):
            self.exam_screen.transition_requested.connect(self._handle_exam_transition)

        if hasattr(self.exam_screen, "exam_runtime_alert"):
            self.exam_screen.exam_runtime_alert.connect(self._on_runtime_alert)

        if self.proctoring_service is not None:
            if hasattr(self.exam_screen, "set_proctoring_service"):
                self.exam_screen.set_proctoring_service(self.proctoring_service)
            self.identity_screen.set_proctoring_service(self.proctoring_service)
            self.app_closer.set_proctoring_service(self.proctoring_service)
            self.securing_screen.set_proctoring_service(self.proctoring_service)
            if hasattr(self.proctoring_service, "set_focus_guard_callback"):
                self.proctoring_service.set_focus_guard_callback(self._enforce_exam_focus)
            if hasattr(self.proctoring_service, "set_violation_threshold_callback"):
                self.proctoring_service.set_violation_threshold_callback(self._on_violation_threshold_reached)

    def _start_focus_guard(self):
        if not self._force_exam_topmost:
            return
        if not self._focus_guard_timer.isActive():
            self._focus_guard_timer.start()

    def _stop_focus_guard(self):
        if self._focus_guard_timer.isActive():
            self._focus_guard_timer.stop()
        if self._force_exam_topmost:
            try:
                self.main_window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
                self.main_window.showFullScreen()

            except Exception:
                pass

    def _enforce_exam_focus(self):
        """Best-effort keep exam window in foreground and top-most."""
        if not self._force_exam_topmost:
            return
        try:
            if self.main_window.currentIndex() != 6:
                return
            self.main_window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self.main_window.showFullScreen()
            self.main_window.raise_()
            self.main_window.activateWindow()
        except Exception:
            pass

    def _on_violation_threshold_reached(self):
        """
        Called when violation count reaches threshold.
        Triggers exam submission and cleanup to prevent further exam progress.
        """
        print("[Security] CRITICAL: Violation threshold reached. Terminating exam session.")
        try:
            # Attempt to submit exam through exam_screen if available
            if hasattr(self.exam_screen, "_emit_submit_payload"):
                self.exam_screen._emit_submit_payload()
                return
        except Exception as e:
            print(f"[Security] Exam submission failed: {e}")
        
        # Fallback: force cleanup and show message
        try:
            self._show_error_popup(
                "Exam Terminated",
                "Critical violations detected. Your exam session has been terminated for integrity reasons."
            )
        except Exception:
            pass
        
        try:
            self._finalize_and_cleanup()
        except Exception as e:
            print(f"[Security] Cleanup error: {e}")

    def _show_error_popup(self, title: str, message: str):
        # Avoid focus contention with modal dialogs during strict lockdown.
        guard_was_active = self._focus_guard_timer.isActive()
        if guard_was_active:
            self._stop_focus_guard()
        try:
            show_error_popup(self.main_window, title, message)
        finally:
            if guard_was_active and self.main_window.currentIndex() == 6:
                self._start_focus_guard()
                self._enforce_exam_focus()

    def _handle_unhandled_exception(self, exc_type, exc_value, exc_tb):
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))[-3000:]
        print(f"[ERROR] Unhandled exception:\n{details}")
        try:
            self._finalize_and_cleanup()
        except Exception as cleanup_exc:
            print(f"[ERROR] Cleanup during unhandled exception failed: {cleanup_exc}")
        try:
            self._show_error_popup(
                "Application Error",
                f"An unexpected error occurred.\n\n{exc_value}\n\nAll protections were safely released.",
            )
        except Exception:
            pass

    def _handle_thread_exception(self, args):
        self._handle_unhandled_exception(args.exc_type, args.exc_value, args.exc_traceback)

    def _install_error_handlers(self):
        sys.excepthook = self._handle_unhandled_exception
        if hasattr(threading, 'excepthook'):
            threading.excepthook = self._handle_thread_exception

    def _on_runtime_alert(self, message: str):
        # Runtime warnings remain banner-only in ExamScreen.
        if message:
            print(f"[Alert] {message}")

    def _go_to_login(self):
        """Navigate to login screen."""
        print("[UI] → Login Screen")
        self.main_window.setCurrentIndex(1)

    def _on_login_success(self, email: str, token: str):
        """Handle successful login."""
        print(f"[UI] Login successful: {email}")
        self.user_email = email
        self.login_token = token
        self.exam_launch_code = self.login_screen.get_exam_launch_code()
        if ExamApiClient is not None:
            try:
                self._exam_api_client = ExamApiClient(self.backend_url, email, token)
            except Exception as exc:
                print(f"[Exam] Failed to initialize API client: {exc}")
                self._exam_api_client = None

        if self._exam_api_client is not None:
            self.exam_screen.set_api_client(self._exam_api_client)
        
        if self.proctoring_service is not None and hasattr(self.proctoring_service, "set_exam_context"):
            self.proctoring_service.set_exam_context(self.backend_url, token, user_email=email)
        self.exam_screen.set_server_context(self.backend_url, email, token)
        self._go_to_app_closer()

    def _go_to_app_closer(self):
        """Navigate to app closer screen."""
        print("[UI] → App Closer Screen")
        self.main_window.setCurrentIndex(2)
        self.app_closer.refresh()

    def _go_to_identity(self):
        """Navigate to identity verification screen."""
        print("[UI] → Identity Verification Screen")
        self.main_window.setCurrentIndex(3)
        self.identity_screen.start_camera_feed()

    def _go_to_terms(self):
        """Navigate to terms and conditions screen."""
        print("[UI] → Terms & Conditions Screen")
        self.identity_screen.stop_camera_feed()
        self.main_window.setCurrentIndex(4)

    def _go_to_securing(self):
        """Navigate to securing and initialization screen."""
        print("[UI] → Securing Environment Screen")
        self.main_window.setCurrentIndex(5)
        if self.proctoring_service is not None:
            self.securing_screen.set_proctoring_service(self.proctoring_service)
        self.securing_screen.start_securing()

    def _go_to_exam(self):
        """Navigate to exam screen."""
        print("[UI] → Exam Screen")
        print(f"[Exam] Starting exam for {self.user_email}")

        if self._exam_api_client is not None:
            with self._worker_lock:
                if self._bootstrap_in_flight:
                    return
                self._bootstrap_in_flight = True

            self._bootstrap_worker = _BootstrapWorker(self._exam_api_client, self.exam_launch_code)
            self._bootstrap_worker.success.connect(self._on_bootstrap_success)
            self._bootstrap_worker.http_error.connect(self._on_bootstrap_http_error)
            self._bootstrap_worker.failed.connect(self._on_bootstrap_failed)
            self._bootstrap_worker.start()
            return
        else:
            exam_data = None
            self._launch_exam_ui(exam_data)

    def _on_bootstrap_success(self, bootstrap: dict):
        with self._worker_lock:
            self._bootstrap_in_flight = False
            self._bootstrap_worker = None

        status = (bootstrap.get("status") or "").lower()
        if status == "waiting":
            sec_left = int(bootstrap.get("seconds_to_start") or 0)
            retry_seconds = min(max(sec_left, 15), 60)
            if hasattr(self.securing_screen, "_status_label"):
                self.securing_screen._status_label.setText(
                    f"Exam not started yet. Retrying in {retry_seconds} second(s)..."
                )
            QTimer.singleShot(retry_seconds * 1000, self._go_to_exam)
            return

        self._active_exam_id = bootstrap.get("exam_id")
        self._active_attempt_id = bootstrap.get("attempt_id")
        if self._active_exam_id and self._active_attempt_id:
            self.exam_screen.set_exam_session(self._active_exam_id, self._active_attempt_id)

        # Prime evidence metadata so warning captures include exam identifiers.
        if self.proctoring_service is not None and hasattr(self.proctoring_service, "set_exam_metadata"):
            sections = bootstrap.get("sections") or []
            first_section_id = ""
            if isinstance(sections, list) and sections:
                first_section_id = str((sections[0] or {}).get("id") or "")
            self.proctoring_service.set_exam_metadata(
                self.user_email or "",
                str(self._active_exam_id or ""),
                first_section_id,
            )

        exam_data = {
            "title": bootstrap.get("title", "Secure Examination"),
            "duration": int(bootstrap.get("duration", 3600)),
            "sections": bootstrap.get("sections", []),
            "generation_mode": str(bootstrap.get("generation_mode") or "").strip().lower(),
            "is_jit": bool(bootstrap.get("is_jit", False)),
        }
        print(
            "[Exam] Bootstrap mode: "
            f"generation_mode={exam_data.get('generation_mode')!r}, "
            f"is_jit={exam_data.get('is_jit')}"
        )
        self._launch_exam_ui(exam_data)

    def _on_bootstrap_http_error(self, body: str):
        with self._worker_lock:
            self._bootstrap_in_flight = False
            self._bootstrap_worker = None
        self._show_error_popup("Exam Bootstrap Error", f"Server rejected bootstrap request.\n\n{body}")

    def _on_bootstrap_failed(self, message: str):
        with self._worker_lock:
            self._bootstrap_in_flight = False
            self._bootstrap_worker = None
        self._show_error_popup("Exam Bootstrap Error", f"Unable to load exam from server.\n\n{message}")

    def _launch_exam_ui(self, exam_data: dict | None):
        self.main_window.setCurrentIndex(6)
        self._start_focus_guard()
        self._enforce_exam_focus()
        try:
            self.exam_screen.start_exam(exam_data=exam_data)
        except Exception as exc:
            self._on_shutdown(f"Security initialization failed: {exc}")

    def _on_exam_submitted(self, data: dict):
        """Handle exam submission with guaranteed cleanup."""
        print(f"[Exam] Exam submitted: {data}")
        self._last_submit_data = data

        if self._exam_api_client is not None and self._active_attempt_id:
            session_nonce = ""
            if self.proctoring_service is not None:
                session_nonce = getattr(self.proctoring_service, "_session_nonce", "") or ""

            if not session_nonce:
                # Attempt on-demand session recovery before failing submit.
                if self.proctoring_service is not None and hasattr(self.proctoring_service, "_ensure_telemetry_session"):
                    try:
                        self.proctoring_service._ensure_telemetry_session()
                        session_nonce = getattr(self.proctoring_service, "_session_nonce", "") or ""
                    except Exception as exc:
                        print(f"[Exam] On-demand nonce recovery failed: {exc}")

            if not session_nonce:
                self._upload_exam_logs_best_effort(upload_reason="submit_missing_nonce")
                self._show_error_popup(
                    "Submission Error",
                    "Missing secure session nonce. Please wait a few seconds and try submitting again.",
                )
                return

            with self._worker_lock:
                if self._submit_in_flight:
                    return
                self._submit_in_flight = True

            submit_payload = {
                "session_nonce": session_nonce,
                "attempt_id": int(self._active_attempt_id),
                "answers": data.get("answers", {}),
                "total_questions": int(data.get("total_questions", len(data.get("answers", {})))),
                "duration_seconds": int(data.get("duration", 0)),
            }
            self._submit_worker = _SubmitWorker(self._exam_api_client, submit_payload)
            self._submit_worker.success.connect(self._on_submit_success)
            self._submit_worker.http_error.connect(self._on_submit_http_error)
            self._submit_worker.failed.connect(self._on_submit_failed)
            self._submit_worker.start()
            return

        self._complete_submission_flow(data)

    def _on_submit_success(self, submit_resp: dict):
        with self._worker_lock:
            self._submit_in_flight = False
            self._submit_worker = None
        print(f"[Exam] Server submit response: {submit_resp}")
        self._complete_submission_flow(self._last_submit_data or {})

    def _on_submit_http_error(self, body: str):
        with self._worker_lock:
            self._submit_in_flight = False
            self._submit_worker = None
        self._upload_exam_logs_best_effort(upload_reason="submit_http_error")
        self._show_error_popup(
            "Submission Failed",
            f"Server rejected exam submission.\n\n{body}\n\nPlease click Submit again.",
        )

    def _on_submit_failed(self, message: str):
        with self._worker_lock:
            self._submit_in_flight = False
            self._submit_worker = None
        self._upload_exam_logs_best_effort(upload_reason="submit_transport_error")
        self._show_error_popup(
            "Submission Failed",
            f"Could not submit exam to server.\n\n{message}\n\nPlease click Submit again.",
        )

    def _complete_submission_flow(self, data: dict):
        duration = int(data.get("duration", 0))
        sections = int(data.get("sections", 0))

        # Upload local logs for post-exam diagnostics (best effort).
        self._upload_exam_logs_best_effort(upload_reason="submit_success")

        # Ensure cleanup before showing message
        self._finalize_and_cleanup()

        from ui.components.premium_popup import PremiumPopup
        PremiumPopup.show_message(
            self.main_window,
            "Exam Submitted",
            f"Your exam has been submitted successfully!\n\n"
            f"Duration: {duration} seconds\n"
            f"Sections: {sections}\n\n"
            f"Thank you. The application will now close.",
            QMessageBox.Icon.Information,
            QMessageBox.StandardButton.Ok
        )
        self.app.quit()

    def _upload_exam_logs_best_effort(self, upload_reason: str = "finalize"):
        if self._exam_api_client is None or not self._active_attempt_id:
            return
        if self.proctoring_service is None:
            return

        session_nonce = getattr(self.proctoring_service, "_session_nonce", "") or ""

        log_text = ""
        try:
            log_path = getattr(_AUDIT_LOGGER, "log_file", "") if _AUDIT_LOGGER is not None else ""
            if log_path and os.path.exists(log_path):
                # Send tail to keep payload bounded.
                # Send only the tail to keep payload bounded.
                max_bytes = 300_000
                with open(log_path, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    f.seek(max(0, size - max_bytes), os.SEEK_SET)
                    tail = f.read()
                log_text = tail.decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"[Exam] Log read for upload failed: {exc}")
            return

        process_snapshot = {}
        try:
            if hasattr(self.proctoring_service, "get_process_snapshot"):
                process_snapshot = self.proctoring_service.get_process_snapshot() or {}
        except Exception as exc:
            print(f"[Exam] Process snapshot capture failed: {exc}")

        try:
            resp = self._exam_api_client.upload_exam_logs(
                session_nonce=session_nonce,
                attempt_id=int(self._active_attempt_id),
                log_text=log_text,
                process_snapshot=process_snapshot,
                upload_reason=upload_reason,
                timeout=8.0,
            )
            print(f"[Exam] Client logs uploaded: {resp}")
        except Exception as exc:
            print(f"[Exam] Client log upload failed: {exc}")

    def _handle_exam_transition(self, target: str):
        if target == "submit":
            if hasattr(self.exam_screen, "get_all_answers"):
                ans = self.exam_screen.get_all_answers()
                self._on_exam_submitted(ans)
            else:
                self._on_exam_submitted({})
        else:
            print(f"Unknown transition target from ExamScreen: {target}")

    def _on_shutdown(self, reason: str):
        """Handle application shutdown with guaranteed cleanup."""
        print(f"[UI] Shutdown: {reason}")

        # Ensure cleanup before shutdown
        self._finalize_and_cleanup()

        from ui.components.premium_popup import PremiumPopup
        PremiumPopup.show_message(
            self.main_window,
            "Session Terminated",
            f"The exam session has been terminated.\n\n"
            f"Reason: {reason}\n\n"
            f"Please contact the administrator.",
            QMessageBox.Icon.Critical,
            QMessageBox.StandardButton.Ok
        )
        self.app.quit()
    
    def _finalize_and_cleanup(self):
        """
        Finalize application state and ensure all security features are properly disengaged.
        This is called before app shutdown to guarantee firewall restoration.
        """
        if self._cleanup_started:
            return
        self._cleanup_started = True

        with self._worker_lock:
            self._bootstrap_in_flight = False
            self._submit_in_flight = False

        print("[UI] Starting final cleanup sequence...")
        self._stop_focus_guard()

        try:
            # Step 1: Stop exam monitoring (includes proctoring cleanup).
            print("[Cleanup] Stopping exam monitoring...")
            self.exam_screen.stop_exam_monitoring()
            print("[Cleanup] ✓ Exam monitoring stopped")
        except Exception as e:
            print(f"[Cleanup] ✗ Error during exam monitoring stop: {e}")
        
        try:
            # Step 2: Direct proctoring cleanup with emergency fallback.
            if self.proctoring_service is not None:
                print("[Cleanup] Force-disengaging security lockdown...")
                self.proctoring_service._disengage_security_lockdown()
                print("[Cleanup] ✓ Security lockdown disengaged")
        except Exception as e:
            print(f"[Cleanup] ✗ Error during proctoring service cleanup: {e}")

        try:
            # Step 2b: Explicit fallback unlock if lockdown is still active.
            if self.proctoring_service is not None and getattr(self.proctoring_service, "lockdown", None) is not None:
                lockdown = self.proctoring_service.lockdown
                is_locked = False
                try:
                    is_locked = bool(lockdown.is_locked())
                except Exception:
                    is_locked = True

                if is_locked:
                    print("[Cleanup] Touchpad/keyboard still locked - forcing unlock...")
                    try:
                        lockdown.unlock_keyboard()
                    except Exception:
                        if hasattr(lockdown, "_emergency_unlock"):
                            lockdown._emergency_unlock()
                    print("[Cleanup] ✓ Touchpad/keyboard protections released")
        except Exception as e:
            print(f"[Cleanup] ✗ Error during touchpad/keyboard release: {e}")

        try:
            # Step 3: Emergency firewall restore when still isolated.
            if self.proctoring_service and self.proctoring_service.firewall:
                if self.proctoring_service.firewall.is_isolated():
                    print("[Cleanup] ⚠️  Firewall still isolated - attempting emergency restore...")
                    self.proctoring_service.firewall._emergency_force_firewall_restore()
                    print("[Cleanup] ✓ Emergency firewall restore completed")
        except Exception as e:
            print(f"[Cleanup] ✗ Error during emergency firewall restore: {e}")
        
        print("[Cleanup] ✅ Final cleanup sequence completed")

    def show(self):
        """Show the application."""
        print("[UI] Showing main window in fullscreen...")
        self.main_window.showFullScreen()

    def run(self):
        """Start the application."""
        print("\n" + "="*70)
        print("Observe Proctoring UI Application (UI-Only Version)")
        print("="*70 + "\n")
        
        self.show()
        
        # Start from splash screen.
        print("[UI] Starting splash screen with consent dialog...")
        QTimer.singleShot(500, lambda: self.splash.show_consent_page())
        
        return self.app.exec()


def main():
    load_env(base_dir=os.path.dirname(os.path.abspath(__file__)))

    if not _verify_audit_chain_on_startup():
        print("[Startup] Aborting: tamper-evident audit chain check failed.")
        return

    if not _ensure_admin_privileges():
        return

    _install_runtime_audit_capture()

    app = QApplication(sys.argv)

    # Set application icon for taskbar and window title bar.
    try:
        # Prefer ICO for Windows taskbar display.
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        else:
            # Fallback to SVG icon during development.
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "logo.svg")
            if os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass

    # Create and run application.
    proctoring_app = ObserveProctorApp(app)

    # Register cleanup to run before process exit.
    def cleanup_on_exit():
        """Absolute final cleanup before process termination."""
        print("[Exit] Running final firewall restoration...")
        try:
            proctoring_app._finalize_and_cleanup()
        except Exception as e:
            print(f"[Exit] Cleanup error (will still exit): {e}")
    
    app.aboutToQuit.connect(cleanup_on_exit)

    exit_code = proctoring_app.run()
    
    print("\n[UI] Application closed")
    sys.exit(exit_code)


def _is_windows_admin() -> bool:
    """Return True if running with admin privileges on Windows."""
    if platform.system() != "Windows":
        return True
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except Exception:
        return False


def _ensure_admin_privileges() -> bool:
    """
    Ensure this app runs as admin on Windows.

    Behavior:
    - If already elevated, continue startup.
    - If not elevated, trigger UAC prompt and relaunch this app as admin.
    - If user cancels UAC, abort startup cleanly.
    """
    if platform.system() != "Windows":
        return True

    if _is_windows_admin():
        return True

    try:
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = ""
        else:
            exe = sys.executable
            script_path = os.path.abspath(__file__)
            extra_args = " ".join(f'"{a}"' for a in sys.argv[1:])
            params = f'"{script_path}" {extra_args}'.strip()

        rc = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            exe,
            params,
            None,
            1,
        )

        # Per ShellExecute docs, value <= 32 means failure/cancel.
        if rc <= 32:
            print("[Startup] Admin elevation was cancelled or failed.")
            return False

        print("[Startup] Relaunched with admin privileges. Exiting original process.")
        return False
    except Exception as e:
        print(f"[Startup] Failed to request admin privileges: {e}")
        return False


if __name__ == "__main__":
    main()

