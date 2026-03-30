"""Splash and consent flow screen shown before authentication.

Provides a loading phase followed by policy consent pages for system lockdown
and network isolation before transitioning into the login stage.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QProgressBar, QGraphicsOpacityEffect, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap

try:
    from PyQt6.QtSvgWidgets import QSvgWidget
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False

# Legacy dialog symbol retained for compatibility; flow now uses stacked pages.
NetworkConsentDialog = None

# Color palette.
BG_WHITE          = "#FFFFFF"
BG_LIGHT_GREY     = "#F8F9FA"
TEXT_BLACK        = "#1A1A1A"
TEXT_GREY         = "#6C757D"
ACCENT_BLUE_VIOLET = "#5A4FCF"
ACCENT_HOVER      = "#4F44B8"
BORDER_LIGHT      = "#E9ECEF"
COLOR_BORDER      = "#E2E8F0"

FONT_FAMILY = "Segoe UI Variable, Segoe UI, Roboto, sans-serif"

# Button styles for consent pages.
STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background: {ACCENT_BLUE_VIOLET};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-family: {FONT_FAMILY};
        font-size: 14px;
        font-weight: 600;
        padding: 14px 32px;
    }}
    QPushButton:hover {{
        background: {ACCENT_HOVER};
    }}
    QPushButton:pressed {{
        background: #3D34A5;
    }}
"""

STYLE_BTN_SECONDARY = f"""
    QPushButton {{
        background: {BG_WHITE};
        color: {TEXT_GREY};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        font-family: {FONT_FAMILY};
        font-size: 14px;
        font-weight: 600;
        padding: 14px 32px;
    }}
    QPushButton:hover {{
        background: {BG_LIGHT_GREY};
        color: {TEXT_BLACK};
    }}
"""


class SplashScreen(QWidget):
    """Loading and consent flow before exam login.

    Stack pages:
        0 - Loading animation
        1 - System lockdown consent
        2 - Network isolation consent
    """
    finished = pyqtSignal()
    shutdown = pyqtSignal(str)

    # Path to the splash logo asset.
    _LOGO_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "Blacklogo.svg")
    )

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._consent_done = False
        self._progress_value = 0
        self._consent_requested = False   # set True if show_consent_page() called early
        self._transition_emitted = False
        self._init_ui()

    def _emit_finished_once(self):
        if self._transition_emitted:
            return
        self._transition_emitted = True
        self.finished.emit()

    def _emit_shutdown_once(self, reason: str):
        if self._transition_emitted:
            return
        self._transition_emitted = True
        self.shutdown.emit(reason)

    # UI construction

    def _init_ui(self):
        self.setWindowTitle("Observe - Secure Examination Provider")
        self.setStyleSheet(f"background-color: {BG_WHITE}; border-radius: 0px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Stacked widget: loading, lockdown consent, and network consent pages.
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")
        self._stack.addWidget(self._make_loading_page())

        outer.addWidget(self._stack)

    def _make_loading_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background-color: {BG_WHITE};")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 80)

        layout.addStretch(1)

        # Center area: logo and tagline.
        middle = QVBoxLayout()
        middle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle.setSpacing(15)

        # Prefer SVG logo when available; otherwise use text fallback.
        if _SVG_AVAILABLE and os.path.exists(self._LOGO_PATH):
            self._logo = QSvgWidget(self._LOGO_PATH)
            self._logo.setFixedSize(440, 200)
            middle.addWidget(self._logo, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            self._logo = QLabel("OBSERVE")
            self._logo.setFont(QFont("Segoe UI", 42, QFont.Weight.Bold))
            self._logo.setStyleSheet(f"color: {ACCENT_BLUE_VIOLET}; letter-spacing: -1px;")
            middle.addWidget(self._logo, alignment=Qt.AlignmentFlag.AlignCenter)

        tagline = QLabel("secure exam environment")
        tagline.setStyleSheet(f"""
            color: {TEXT_GREY};
            font-size: 14px;
            letter-spacing: 2px;
            text-transform: uppercase;
        """)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle.addWidget(tagline, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(middle)
        layout.addStretch(1)

        # Bottom area: status text and progress bar.
        loader = QVBoxLayout()
        loader.setSpacing(16)
        loader.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._detail_label = QLabel("Checking system requirements...")
        self._detail_label.setStyleSheet(
            f"color: {TEXT_BLACK}; font-size: 13px; letter-spacing: 1px;"
        )
        self._detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loader.addWidget(self._detail_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(2)
        self._progress_bar.setMinimumWidth(600)
        self._progress_bar.setMaximumWidth(800)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BORDER_LIGHT};
                border: none;
                border-radius: 0px;
            }}
            QProgressBar::chunk {{
                background-color: {TEXT_BLACK};
                border-radius: 0px;
            }}
        """)
        loader.addWidget(self._progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(loader)

        # Fade-in animation.
        self._opacity_effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(self._opacity_effect)
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(1000)
        self._fade_anim.setStartValue(0)
        self._fade_anim.setEndValue(1)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._fade_anim.start()

        # Auto-progress timer.
        self._loading_timer = QTimer(self)
        self._loading_timer.timeout.connect(self._update_progress)
        self._loading_timer.start(25)

        return page

    def _update_progress(self):
        """Advance the progress bar and update status labels."""
        self._progress_value += 1
        self._progress_bar.setValue(self._progress_value)

        if self._progress_value == 30:
            self._detail_label.setText("Checking system integrity...")
        elif self._progress_value == 65:
            self._detail_label.setText("Loading biometric drivers...")
        elif self._progress_value == 90:
            self._detail_label.setText("Starting secure sandbox...")
        elif self._progress_value >= 100:
            self._loading_timer.stop()
            # Show consent once loading completes.
            self._do_show_consent()

    # Public API

    def show_consent_page(self):
        """Switch to the lockdown consent page.

        If loading is still active, switching is deferred until progress reaches
        completion.
        """
        if self._loading_timer.isActive():
            # Loading still in progress; defer switching.
            self._consent_requested = True
            return
        self._do_show_consent()

    def _do_show_consent(self):
        """Internal: actually switch the stack to the lockdown consent page."""
        if self._stack.count() == 1:
            self._stack.addWidget(self._make_consent_page())
        self._stack.setCurrentIndex(1)

    # Lockdown consent page (stack index 1)

    def _make_consent_page(self) -> QWidget:
        """Build the lockdown consent page."""
        page = QWidget()
        page.setStyleSheet("background-color: #0B1120;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left panel.
        left_panel = QFrame()
        left_panel.setFixedWidth(500)
        left_panel.setStyleSheet("background-color: #0B1120;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 50, 40, 40)

        # White logo.
        logo_layout = QHBoxLayout()
        _white_logo_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "assets", "whitelogo.svg")
        )
        if _SVG_AVAILABLE and os.path.exists(_white_logo_path):
            _logo_widget = QSvgWidget(_white_logo_path)
            _logo_widget.setFixedSize(260, 120)
            logo_layout.addWidget(_logo_widget)
        else:
            _logo_widget = QLabel("OBSERVE")
            _logo_widget.setStyleSheet(
                "font-size: 24px; font-weight: bold; color: white;"
            )
            logo_layout.addWidget(_logo_widget)
        logo_layout.addStretch()
        left_layout.addLayout(logo_layout)

        left_layout.addStretch()

        # Floating shield card.
        shield_container = QWidget()
        shield_container.setFixedSize(300, 320)

        card = QFrame(shield_container)
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

        shield_icon = QLabel("🛡️")
        shield_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shield_icon.setStyleSheet(
            "font-size: 56px; background: transparent; border: none;"
        )
        fc_layout.addWidget(shield_icon)
        fc_layout.addSpacing(20)

        fc_title = QLabel("System Lockdown")
        fc_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_title.setStyleSheet(
            "font-size: 22px; font-weight: 900; color: #FFFFFF;"
            " background: transparent; border: none; letter-spacing: 1px;"
        )
        fc_layout.addWidget(fc_title)

        fc_desc = QLabel(
            "AI-driven local enforcement active. Mapping security state"
            " to enterprise parameters."
        )
        fc_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_desc.setWordWrap(True)
        fc_desc.setStyleSheet(
            "font-size: 13px; font-weight: 500; color: #94A3B8;"
            " background: transparent; border: none; margin-top: 10px;"
        )
        fc_layout.addWidget(fc_desc)

        left_layout.addWidget(shield_container, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()

        # Bottom watermark.
        wm_lyt = QHBoxLayout()
        wm_icon = QLabel("✨")
        wm_icon.setStyleSheet("font-size: 15px; color: #64748B;")
        wm_lbl = QLabel("Powering next-gen proctoring")
        wm_lbl.setStyleSheet("font-size: 14px; color: #64748B; font-weight: 500;")
        wm_lyt.addWidget(wm_icon)
        wm_lyt.addWidget(wm_lbl)
        wm_lyt.addStretch()
        left_layout.addLayout(wm_lyt)

        main_layout.addWidget(left_panel)

        # Right panel.
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top-left-radius: 40px;
                border-bottom-left-radius: 40px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(60, 50, 60, 40)

        title = QLabel("System Restrictions")
        title.setStyleSheet(
            "font-size: 36px; font-weight: 900; color: #0F172A;"
            " margin-top: 50px; margin-left: -10px;"
        )
        right_layout.addWidget(title)

        desc = QLabel(
            "Security policy enforcements required. Please review the constraints "
            "below to proceed with your examination securely."
        )
        desc.setStyleSheet("font-size: 14px; color: #64748B; margin-top: 10px;")
        desc.setWordWrap(True)
        right_layout.addWidget(desc)
        right_layout.addSpacing(30)

        # Constraint grid.
        grid = QGridLayout()
        grid.setSpacing(25)
        grid.addWidget(self._create_info_box("BACKGROUND APPS",  "Blocks specific applications...",     "✕"), 0, 0)
        grid.addWidget(self._create_info_box("DUAL MONITOR",     "Disabled during examination",         "✕"), 0, 1)
        grid.addWidget(self._create_info_box("CLIPBOARD",        "Copy & Paste functionality blocked",  "✕"), 1, 0)
        grid.addWidget(self._create_info_box("SYSTEM RESTORE",   "Reverts automatically after exam",    "✓"), 1, 1)
        right_layout.addLayout(grid)
        right_layout.addStretch()

        # Divider.
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #F1F5F9; margin-bottom: 10px;")
        right_layout.addWidget(divider)

        # Footer actions.
        footer = QHBoxLayout()

        self.btn_cancel = QPushButton("Decline")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 14px; font-weight: bold; color: #64748B;
            }
            QPushButton:hover { color: #0F172A; }
        """)
        self.btn_cancel.clicked.connect(lambda: self._emit_shutdown_once("User cancelled"))

        self.btn_agree = QPushButton("Accept && Continue")
        self.btn_agree.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_agree.setFixedHeight(44)
        self.btn_agree.setStyleSheet("""
            QPushButton {
                background-color: #0F172A; color: #FFFFFF;
                border-radius: 6px; font-weight: bold;
                font-size: 14px; padding: 0 40px;
            }
            QPushButton:hover { background-color: #1E293B; }
        """)
        self.btn_agree.clicked.connect(self._on_agree)

        footer.addWidget(self.btn_cancel)
        footer.addStretch()
        footer.addWidget(self.btn_agree)
        right_layout.addLayout(footer)

        main_layout.addWidget(right_panel, 1)
        return page

    def _create_info_box(self, title: str, desc: str, icon_sym: str) -> QWidget:
        """Constraint info box used in the 2×2 lockdown grid."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lyt = QVBoxLayout(w)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(6)

        t = QLabel(title)
        t.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B;")
        lyt.addWidget(t)

        box = QFrame()
        box.setFixedHeight(48)
        box.setStyleSheet("""
            QFrame {
                border: 1px solid #F1F5F9;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
        """)
        box_lyt = QHBoxLayout(box)
        box_lyt.setContentsMargins(15, 0, 15, 0)

        d = QLabel(desc)
        d.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #94A3B8;"
            " border: none; background: transparent;"
        )
        icon_lbl = QLabel()
        if icon_sym == "✓":
            icon_lbl.setText("✓")
            icon_lbl.setStyleSheet(
                "font-size: 14px; font-weight: 900; color: #00EBA4;"
                " background: transparent;"
            )
        else:
            icon_lbl.setText("✕")
            icon_lbl.setStyleSheet(
                "font-size: 14px; font-weight: 900; color: #94A3B8;"
                " background: transparent;"
            )

        box_lyt.addWidget(d)
        box_lyt.addStretch()
        box_lyt.addWidget(icon_lbl)
        lyt.addWidget(box)
        return w

    def _on_agree(self):
        """Handle lockdown consent and navigate to the network page."""
        self.btn_agree.setEnabled(False)
        # Add the network page lazily on first call.
        if self._stack.count() == 2:
            self._stack.addWidget(self._make_network_page())
        self._stack.setCurrentIndex(2)

    # Network isolation page (stack index 2)

    def _make_network_page(self) -> QWidget:
        """Build the network isolation consent page."""
        page = QWidget()
        page.setStyleSheet("background-color: #0B1120;")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left panel.
        left_panel = QFrame()
        left_panel.setFixedWidth(500)
        left_panel.setStyleSheet("background-color: #0B1120;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 50, 40, 40)

        # White logo.
        logo_layout = QHBoxLayout()
        _white_logo_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "assets", "whitelogo.svg")
        )
        if _SVG_AVAILABLE and os.path.exists(_white_logo_path):
            _logo_widget = QSvgWidget(_white_logo_path)
            _logo_widget.setFixedSize(260, 120)
            logo_layout.addWidget(_logo_widget)
        else:
            _logo_widget = QLabel("OBSERVE")
            _logo_widget.setStyleSheet(
                "font-size: 24px; font-weight: bold; color: white;"
            )
            logo_layout.addWidget(_logo_widget)
        logo_layout.addStretch()
        left_layout.addLayout(logo_layout)

        left_layout.addStretch()

        # Floating antenna card.
        antenna_container = QWidget()
        antenna_container.setFixedSize(300, 320)

        net_card = QFrame(antenna_container)
        net_card.setGeometry(10, 30, 280, 260)
        net_card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
            }
        """)
        nc_layout = QVBoxLayout(net_card)
        nc_layout.setContentsMargins(25, 40, 25, 40)
        nc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        net_icon = QLabel("📡")
        net_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        net_icon.setStyleSheet(
            "font-size: 56px; background: transparent; border: none;"
        )
        nc_layout.addWidget(net_icon)
        nc_layout.addSpacing(15)

        nc_title = QLabel("Network Isolation")
        nc_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nc_title.setStyleSheet(
            "font-size: 22px; font-weight: 900; color: #FFFFFF;"
            " background: transparent; border: none; letter-spacing: 1px;"
        )
        nc_layout.addWidget(nc_title)

        nc_desc = QLabel(
            "Restricting external traffic to ensure exclusive connection"
            " to the secure exam servers."
        )
        nc_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nc_desc.setWordWrap(True)
        nc_desc.setStyleSheet(
            "font-size: 13px; font-weight: 500; color: #94A3B8;"
            " background: transparent; border: none; margin-top: 10px;"
        )
        nc_layout.addWidget(nc_desc)

        left_layout.addWidget(antenna_container, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()

        # Bottom watermark.
        wm_lyt = QHBoxLayout()
        wm_icon = QLabel("✨")
        wm_icon.setStyleSheet("font-size: 15px; color: #64748B;")
        wm_lbl = QLabel("Powering next-gen proctoring")
        wm_lbl.setStyleSheet("font-size: 14px; color: #64748B; font-weight: 500;")
        wm_lyt.addWidget(wm_icon)
        wm_lyt.addWidget(wm_lbl)
        wm_lyt.addStretch()
        left_layout.addLayout(wm_lyt)

        main_layout.addWidget(left_panel)

        # Right panel.
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top-left-radius: 40px;
                border-bottom-left-radius: 40px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(60, 50, 60, 40)

        title = QLabel("Network Isolation")
        title.setStyleSheet(
            "font-size: 36px; font-weight: 900; color: #0F172A;"
            " margin-top: 50px; margin-left: -10px;"
        )
        right_layout.addWidget(title)

        desc = QLabel(
            "Internet access will be strictly restricted to the examination servers. "
            "All other traffic will be blocked via system firewall."
        )
        desc.setStyleSheet("font-size: 14px; color: #64748B; margin-top: 10px;")
        desc.setWordWrap(True)
        right_layout.addWidget(desc)
        right_layout.addSpacing(30)

        # Network constraint grid.
        grid = QGridLayout()
        grid.setSpacing(25)
        grid.addWidget(self._create_network_info_box("EXAM SERVERS",       "Connection maintained securely",     "✓"), 0, 0)
        grid.addWidget(self._create_network_info_box("EXTERNAL BROWSING",  "All outside internet blocked",       "✕"), 0, 1)
        grid.addWidget(self._create_network_info_box("MESSAGING PORTS",    "Discord, Slack, etc. disconnected",  "✕"), 1, 0)
        grid.addWidget(self._create_network_info_box("SYSTEM FIREWALL",    "Reverts automatically after exam",   "✓"), 1, 1)
        right_layout.addLayout(grid)
        right_layout.addStretch()

        # Divider.
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #F1F5F9; margin-bottom: 10px;")
        right_layout.addWidget(divider)

        # Footer actions.
        footer = QHBoxLayout()

        btn_decline = QPushButton("Decline")
        btn_decline.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_decline.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 14px; font-weight: bold; color: #64748B;
            }
            QPushButton:hover { color: #0F172A; }
        """)
        # Decline and emit shutdown.
        btn_decline.clicked.connect(
            lambda: self._emit_shutdown_once("Network isolation consent not granted")
        )

        btn_isolate = QPushButton("Accept && Isolate")
        btn_isolate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_isolate.setFixedHeight(44)
        btn_isolate.setStyleSheet("""
            QPushButton {
                background-color: #0F172A; color: #FFFFFF;
                border-radius: 6px; font-weight: bold;
                font-size: 14px; padding: 0 40px;
            }
            QPushButton:hover { background-color: #1E293B; }
        """)
        # Accept and continue to the next stage.
        btn_isolate.clicked.connect(self._on_network_accepted)

        footer.addWidget(btn_decline)
        footer.addStretch()
        footer.addWidget(btn_isolate)
        right_layout.addLayout(footer)

        main_layout.addWidget(right_panel, 1)
        return page

    def _on_network_accepted(self):
        """Handle accepted network isolation consent and continue flow."""
        self._consent_done = True
        self._emit_finished_once()

    def _create_network_info_box(self, title: str, desc: str, icon_sym: str) -> QWidget:
        """Info box for the network isolation constraint grid."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lyt = QVBoxLayout(w)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(6)

        t = QLabel(title)
        t.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B;")
        lyt.addWidget(t)

        box = QFrame()
        box.setFixedHeight(48)
        box.setStyleSheet("""
            QFrame {
                border: 1px solid #F1F5F9;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
        """)
        box_lyt = QHBoxLayout(box)
        box_lyt.setContentsMargins(15, 0, 15, 0)

        d = QLabel(desc)
        d.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #94A3B8;"
            " border: none; background: transparent;"
        )
        icon_lbl = QLabel()
        if icon_sym == "✓":
            icon_lbl.setText("✓")
            icon_lbl.setStyleSheet(
                "font-size: 14px; font-weight: 900; color: #00EBA4;"
                " background: transparent;"
            )
        else:
            icon_lbl.setText("✕")
            icon_lbl.setStyleSheet(
                "font-size: 14px; font-weight: 900; color: #94A3B8;"
                " background: transparent;"
            )

        box_lyt.addWidget(d)
        box_lyt.addStretch()
        box_lyt.addWidget(icon_lbl)
        lyt.addWidget(box)
        return w
