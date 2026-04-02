"""Login screen UI for secure candidate authentication."""

import os
import threading
import requests
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont

try:
    from PyQt6.QtSvgWidgets import QSvgWidget
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False

try:
    from core.backend_config import get_backend_url
except Exception:
    get_backend_url = None

# Color constants.
COLOR_SUCCESS = "#04E762"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER  = "#EF4444"


# Background worker threads.

class ServerConnectivityChecker(QThread):
    """Background thread to poll server health every 5 s."""
    status_changed = pyqtSignal(bool)

    def __init__(self, server_url: str):
        super().__init__()
        self.server_url = server_url
        self._stop_event = threading.Event()
        self.daemon = True

    def run(self):
        while not self._stop_event.is_set() and not self.isInterruptionRequested():
            try:
                response = requests.get(f"{self.server_url}/health", timeout=2)
                self.status_changed.emit(response.status_code == 200)
            except Exception:
                self.status_changed.emit(False)

            # Sleep in short slices so stop() can interrupt promptly.
            for _ in range(50):
                if self._stop_event.is_set() or self.isInterruptionRequested():
                    break
                self.msleep(100)

    def stop(self):
        self._stop_event.set()
        self.requestInterruption()


class LoginWorker(QThread):
    """Background thread for login authentication."""
    login_success  = pyqtSignal(str, str)   # (email, token)
    login_failed   = pyqtSignal(int, str)   # (attempts_left, error_msg)
    login_locked   = pyqtSignal(str)        # lock message
    error_occurred = pyqtSignal(str)        # error message

    def __init__(self, server_url: str, email: str, password: str,
                 failed_attempts: int, max_attempts: int):
        super().__init__()
        self.server_url      = server_url
        self.email           = email
        self.password        = password
        self.failed_attempts = failed_attempts
        self.max_attempts    = max_attempts

    def run(self):
        try:
            response = requests.post(
                f"{self.server_url}/v1/auth/login",
                json={"email": self.email, "password": self.password},
                timeout=10,
            )
            if response.status_code == 200:
                if self.isInterruptionRequested():
                    return
                data = response.json()
                self.login_success.emit(self.email, data.get("login_token"))
            elif response.status_code == 401:
                if self.isInterruptionRequested():
                    return
                self.failed_attempts += 1
                remaining = self.max_attempts - self.failed_attempts
                if remaining <= 0:
                    self.login_locked.emit("Account locked. Contact administrator.")
                else:
                    self.login_failed.emit(
                        remaining,
                        f"Invalid credentials. ({remaining} attempts remaining)"
                    )
            else:
                self.error_occurred.emit(f"Server error (Code: {response.status_code})")
        except requests.ConnectionError:
            self.error_occurred.emit("Could not reach authentication server.")
        except requests.Timeout:
            self.error_occurred.emit("Connection timed out. Please retry.")
        except Exception as e:
            self.error_occurred.emit(f"System error: {str(e)[:50]}")


# Login screen.

class LoginScreen(QWidget):
    """Authentication screen that validates credentials against backend APIs."""
    login_success  = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)

    # Path to the white logo asset.
    _WHITE_LOGO = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "whitelogo.svg")
    )

    def __init__(self, server_url: Optional[str] = None):
        super().__init__()
        if server_url is None:
            if get_backend_url:
                server_url = get_backend_url()
            else:
                server_url = (
                    os.environ.get("OBSERVE_SERVER_URL")
                    or os.environ.get("OBSERVE_BACKEND_URL")
                    or ""
                )
        if not server_url:
            raise RuntimeError(
                "Missing backend URL. Set OBSERVE_SERVER_URL for production login."
            )

        self.server_url          = server_url
        self.login_token         = None
        self.user_email          = None
        self.failed_attempts     = 0
        self.max_attempts        = 5
        self.server_online       = False
        self._login_worker       = None
        self._login_lock         = threading.Lock()
        self._login_in_progress  = False
        self.exam_launch_code_input = None   # set in _init_ui

        self.setWindowTitle("Observe - Secure Examination Provider")
        self._init_ui()
        self._start_connectivity_checker()

    # UI construction

    def _init_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #0B1120;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self._make_left_panel())
        main_layout.addWidget(self._make_right_panel(), 1)

    def _make_left_panel(self) -> QFrame:
        """Build the left panel with branding and authentication context."""
        left_panel = QFrame()
        left_panel.setFixedWidth(500)
        left_panel.setStyleSheet("background-color: #0B1120;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 50, 40, 40)

        # Logo.
        logo_layout = QHBoxLayout()
        if _SVG_AVAILABLE and os.path.exists(self._WHITE_LOGO):
            logo_w = QSvgWidget(self._WHITE_LOGO)
            logo_w.setFixedSize(260, 120)
            logo_layout.addWidget(logo_w)
        else:
            logo_lbl = QLabel("OBSERVE")
            logo_lbl.setStyleSheet(
                "font-size: 24px; font-weight: bold; color: white;"
            )
            logo_layout.addWidget(logo_lbl)
        logo_layout.addStretch()
        left_layout.addLayout(logo_layout)

        left_layout.addStretch()

        # Floating authentication card.
        card_container = QWidget()
        card_container.setFixedSize(300, 320)

        card = QFrame(card_container)
        card.setGeometry(10, 30, 280, 260)
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
            }
        """)
        fc_layout = QVBoxLayout(card)
        fc_layout.setContentsMargins(25, 40, 25, 40)
        fc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("👤")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 56px; background: transparent; border: none;")
        fc_layout.addWidget(icon)
        fc_layout.addSpacing(15)

        fc_title = QLabel("Authentication")
        fc_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_title.setStyleSheet(
            "font-size: 22px; font-weight: 900; color: #FFFFFF;"
            " background: transparent; border: none; letter-spacing: 1px;"
        )
        fc_layout.addWidget(fc_title)

        fc_desc = QLabel(
            "Verify your credentials to load your assigned"
            " examination profile securely."
        )
        fc_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_desc.setWordWrap(True)
        fc_desc.setStyleSheet(
            "font-size: 13px; font-weight: 500; color: #94A3B8;"
            " background: transparent; border: none; margin-top: 10px;"
        )
        fc_layout.addWidget(fc_desc)

        left_layout.addWidget(card_container, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()

        # Watermark.
        wm = QHBoxLayout()
        wm_icon = QLabel("✨")
        wm_icon.setStyleSheet("font-size: 15px; color: #64748B;")
        wm_lbl = QLabel("Powering next-gen proctoring")
        wm_lbl.setStyleSheet("font-size: 14px; color: #64748B; font-weight: 500;")
        wm.addWidget(wm_icon)
        wm.addWidget(wm_lbl)
        wm.addStretch()
        left_layout.addLayout(wm)

        return left_panel

    def _make_right_panel(self) -> QFrame:
        """Build the right panel with server status and sign-in fields."""
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top-left-radius: 40px;
                border-bottom-left-radius: 40px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(80, 50, 80, 40)

        # Header.
        title = QLabel("Sign In")
        title.setStyleSheet(
            "font-size: 34px; font-weight: 900; color: #0F172A;"
            " margin-top: 40px; margin-left: -10px;"
        )
        right_layout.addWidget(title)

        subtitle = QLabel("Please enter your organizational credentials to continue.")
        subtitle.setStyleSheet("font-size: 16px; color: #64748B; margin-top: 5px;")
        right_layout.addWidget(subtitle)
        right_layout.addSpacing(25)

        # Server status bar.
        status_box = QFrame()
        status_box.setFixedHeight(48)
        status_box.setStyleSheet("""
            QFrame {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background-color: #F8FAFC;
            }
        """)
        sb_lyt = QHBoxLayout(status_box)
        sb_lyt.setContentsMargins(20, 0, 20, 0)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(
            "color: #F59E0B; font-size: 14px; background: transparent; border: none;"
        )
        self.status_indicator_label = QLabel("Connecting to secure server...")
        self.status_indicator_label.setStyleSheet(
            "color: #F59E0B; font-size: 14px; font-weight: 500;"
            " background: transparent; border: none;"
        )
        sb_lyt.addWidget(self.status_dot)
        sb_lyt.addSpacing(10)
        sb_lyt.addWidget(self.status_indicator_label)
        sb_lyt.addStretch()

        right_layout.addWidget(status_box)
        right_layout.addSpacing(25)

        # Form fields.
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)

        # Email.
        email_widget, self.email_input = self._create_input_field(
            "Email Address", "candidate@example.com"
        )
        self.email_input.returnPressed.connect(self.on_login)
        form_layout.addWidget(email_widget)

        # Password.
        password_widget, self.password_input = self._create_input_field(
            "Password", "Enter your secure token",
            is_password=True, right_label="Forgot password?"
        )
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.on_login)
        form_layout.addWidget(password_widget)

        # Exam launch code.
        code_widget, self.exam_launch_code_input = self._create_input_field(
            "Exam Launch Code", "Enter one-time code from dashboard"
        )
        self.exam_launch_code_input.returnPressed.connect(self.on_login)
        form_layout.addWidget(code_widget)

        right_layout.addLayout(form_layout)
        right_layout.addSpacing(12)

        # Status and error label.
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color: #EF4444; font-size: 13px; background: transparent;"
        )
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(20)
        right_layout.addWidget(self.status_label)

        right_layout.addStretch()

        # Authentication button.
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.login_btn = QPushButton("Authenticate Session  →")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setFixedHeight(48)
        self.login_btn.setEnabled(False)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0F172A; color: #FFFFFF;
                border-radius: 8px; font-weight: bold;
                font-size: 15px; padding: 0 40px;
            }
            QPushButton:hover { background-color: #1E293B; }
            QPushButton:disabled { background-color: #CBD5E1; color: #94A3B8; }
        """)
        self.login_btn.clicked.connect(self.on_login)
        btn_row.addWidget(self.login_btn)

        right_layout.addLayout(btn_row)
        return right_panel

    def _create_input_field(
        self,
        label_text: str,
        placeholder: str,
        is_password: bool = False,
        right_label: Optional[str] = None,
    ):
        """Create a labeled input field and return container and line edit."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lyt = QVBoxLayout(w)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(8)

        label_row = QHBoxLayout()
        label_row.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        label_row.addWidget(lbl)

        if right_label:
            rlbl = QLabel(
                f"<a href='#' style='color: #6366F1; text-decoration: none;'>"
                f"{right_label}</a>"
            )
            rlbl.setOpenExternalLinks(False)
            rlbl.setStyleSheet("font-size: 14px; font-weight: 500;")
            label_row.addStretch()
            label_row.addWidget(rlbl)

        lyt.addLayout(label_row)

        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        if is_password:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setFixedHeight(50)
        inp.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 0 15px;
                font-size: 14px;
                font-weight: 500;
                color: #0F172A;
                background-color: #F8FAFC;
            }
            QLineEdit:hover {
                border: 1px solid #6366F1;
            }
            QLineEdit:focus {
                border: 2px solid #6366F1;
                background-color: #FFFFFF;
            }
        """)
        lyt.addWidget(inp)
        return w, inp

    # Authentication logic

    def on_login(self):
        with self._login_lock:
            existing = self._login_worker
            if self._login_in_progress or (existing is not None and existing.isRunning()):
                return

        email            = self.email_input.text().strip().lower()
        password         = self.password_input.text()
        exam_launch_code = self.get_exam_launch_code()

        if not email or not password:
            self._show_status("Email and password required.", is_error=True)
            return
        if not exam_launch_code:
            self._show_status("Exam launch code is required.", is_error=True)
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Authenticating...")
        self._show_status("Verifying organizational credentials...", is_error=False)

        worker = LoginWorker(
            self.server_url, email, password,
            self.failed_attempts, self.max_attempts
        )
        worker.login_success.connect(self._on_login_success)
        worker.login_failed.connect(self._on_login_failed)
        worker.login_locked.connect(self._on_login_locked)
        worker.error_occurred.connect(self._on_login_error)
        worker.finished.connect(lambda w=worker: self._on_login_worker_finished(w))

        with self._login_lock:
            self._login_worker = worker
            self._login_in_progress = True
        worker.start()

    def _on_login_worker_finished(self, worker: QThread):
        with self._login_lock:
            if self._login_worker is worker:
                self._login_worker = None
            self._login_in_progress = False
        try:
            worker.deleteLater()
        except RuntimeError:
            pass

    @pyqtSlot(str, str)
    def _on_login_success(self, email: str, token: str):
        self.login_token = token
        self.user_email  = email
        self.login_success.emit(email, token)

    @pyqtSlot(int, str)
    def _on_login_failed(self, remaining_attempts: int, message: str):
        self.failed_attempts = self.max_attempts - remaining_attempts
        self._show_status(message, is_error=True)
        self.password_input.clear()
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Authenticate Session  →")

    @pyqtSlot(str)
    def _on_login_locked(self, message: str):
        self.failed_attempts = self.max_attempts
        self._show_status(message, is_error=True)
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Authenticate Session  →")

    @pyqtSlot(str)
    def _on_login_error(self, error_msg: str):
        self._show_status(error_msg, is_error=True)
        self.login_btn.setEnabled(self.failed_attempts < self.max_attempts)
        self.login_btn.setText("Authenticate Session  →")

    def _show_status(self, message: str, is_error: bool = False):
        self.status_label.setText(message)
        if is_error:
            self.status_label.setStyleSheet(
                "color: #EF4444; font-size: 13px; background: transparent;"
            )
            self.error_occurred.emit(message)
        else:
            self.status_label.setStyleSheet(
                "color: #64748B; font-size: 13px; background: transparent;"
            )

    # Server connectivity

    def _start_connectivity_checker(self):
        existing = getattr(self, "connectivity_checker", None)
        if existing is not None and existing.isRunning():
            existing.stop()
            existing.wait(1500)

        self.connectivity_checker = ServerConnectivityChecker(self.server_url)
        self.connectivity_checker.status_changed.connect(self._update_server_status)
        self.connectivity_checker.start()

    @pyqtSlot(bool)
    def _update_server_status(self, is_online: bool):
        self.server_online = is_online
        if is_online:
            self.status_dot.setStyleSheet(
                "color: #04E762; font-size: 14px; background: transparent; border: none;"
            )
            self.status_indicator_label.setText("Secure server online")
            self.status_indicator_label.setStyleSheet(
                "color: #04E762; font-size: 14px; font-weight: 600;"
                " background: transparent; border: none;"
            )
            if self.failed_attempts < self.max_attempts:
                self.login_btn.setEnabled(True)
        else:
            self.status_dot.setStyleSheet(
                "color: #F59E0B; font-size: 14px; background: transparent; border: none;"
            )
            self.status_indicator_label.setText("Connecting...")
            self.status_indicator_label.setStyleSheet(
                "color: #F59E0B; font-size: 14px; font-weight: 500;"
                " background: transparent; border: none;"
            )
            self.login_btn.setEnabled(False)

    # Public API

    def get_exam_launch_code(self) -> str:
        if self.exam_launch_code_input is None:
            return ""
        return self.exam_launch_code_input.text().strip().upper()

    def dev_mode_auto_login(self):
        """Return False because development auto-login is disabled."""
        return False

    def closeEvent(self, event):
        with self._login_lock:
            login_worker = self._login_worker
            self._login_worker = None
            self._login_in_progress = False
        if login_worker is not None:
            login_worker.requestInterruption()
            login_worker.wait(500)

        if hasattr(self, "connectivity_checker"):
            self.connectivity_checker.stop()
            self.connectivity_checker.wait(2000)
        super().closeEvent(event)

