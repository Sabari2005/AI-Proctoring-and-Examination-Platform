"""Terms and conditions screen for pre-exam compliance acceptance."""

import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QCursor

try:
    from PyQt6.QtSvgWidgets import QSvgWidget
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False


class FloatingCardContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 320)

        self.wrapper = QWidget(self)
        self.wrapper.setGeometry(10, 30, 280, 260)

        self.card = QFrame(self.wrapper)
        self.card.setGeometry(0, 0, 280, 260)
        self.card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
            }
        """)

        fc_layout = QVBoxLayout(self.card)
        fc_layout.setContentsMargins(25, 40, 25, 40)
        fc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📜")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 56px; background: transparent; border: none;")
        fc_layout.addWidget(icon)

        fc_layout.addSpacing(15)

        fc_title = QLabel("Exam Compliances")
        fc_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_title.setStyleSheet("font-size: 22px; font-weight: 900; color: #FFFFFF; background: transparent; border: none; letter-spacing: 1px;")
        fc_layout.addWidget(fc_title)

        fc_desc = QLabel("Review and agree to the organizational terms of service before starting the exam session.")
        fc_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_desc.setWordWrap(True)
        fc_desc.setStyleSheet("font-size: 13px; font-weight: 500; color: #94A3B8; background: transparent; border: none; margin-top: 10px;")
        fc_layout.addWidget(fc_desc)


class TermsScreen(QWidget):
    exam_started = pyqtSignal()
    cancelled = pyqtSignal(str)

    _WHITE_LOGO = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "whitelogo.svg")
    )

    def __init__(self):
        super().__init__()
        self._start_emitted = False
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Observe - Compliance Consent")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #0B1120;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left panel.
        left_panel = QFrame()
        left_panel.setFixedWidth(500)
        left_panel.setStyleSheet("background-color: #0B1120;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 50, 40, 40)
        
        # Logo.
        logo_layout = QHBoxLayout()
        if _SVG_AVAILABLE and os.path.exists(self._WHITE_LOGO):
            self.logo = QSvgWidget(self._WHITE_LOGO)
            self.logo.setFixedSize(260, 120)
            logo_layout.addWidget(self.logo)
        else:
            self.logo = QLabel("OBSERVE")
            self.logo.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
            logo_layout.addWidget(self.logo)
            
        logo_layout.addStretch()
        left_layout.addLayout(logo_layout)
        left_layout.addStretch()
        
        self.floating_container = FloatingCardContainer()
        left_layout.addWidget(self.floating_container, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()
        
        # Bottom-left watermark.
        watermark_lyt = QHBoxLayout()
        icon_wm = QLabel("✨")
        icon_wm.setStyleSheet("font-size: 15px; color: #64748B;")
        lbl_wm = QLabel("Powering next-gen proctoring")
        lbl_wm.setStyleSheet("font-size: 14px; color: #64748B; font-weight: 500;")
        watermark_lyt.addWidget(icon_wm)
        watermark_lyt.addWidget(lbl_wm)
        watermark_lyt.addStretch()
        left_layout.addLayout(watermark_lyt)
        
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
        right_layout.setContentsMargins(80, 50, 80, 40)
        
        # Title and subtitle.
        title = QLabel("Examination Rules & Consent")
        title.setStyleSheet("font-size: 34px; font-weight: 900; color: #0F172A; margin-top: 40px; margin-left:-10px;")
        right_layout.addWidget(title)
        
        desc = QLabel("Please read and acknowledge the following compliance requirements before proceeding.")
        desc.setStyleSheet("font-size: 15px; color: #64748B; margin-top: 5px;")
        desc.setWordWrap(True)
        right_layout.addWidget(desc)
        
        right_layout.addSpacing(25)
        
        # Rules layout inside a scroll area.
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { background-color: transparent; border: 1px solid #E2E8F0; border-radius: 8px; }
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #F8FAFC; border-radius: 8px;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(30, 30, 30, 30)
        scroll_layout.setSpacing(25)
        
        rules = [
            (
                "Continuous Audio-Visual Monitoring",
                "Your webcam and microphone will remain active for the entire duration of the examination. Video and audio streams are securely recorded and analyzed in real time. The camera must remain unobstructed, and your face must be clearly visible at all times."
            ),
            (
                "AI-Driven Behavioral Analysis",
                "Advanced AI systems continuously evaluate gaze direction, facial orientation, background activity, and audio signals to detect anomalies or suspicious patterns. Any deviation from expected behavior may be flagged for review."
            ),
            (
                "Strict Environment Compliance",
                "You must remain alone in a controlled and distraction-free environment. The use of secondary devices, external assistance, printed materials, or communication with others is strictly prohibited throughout the session."
            ),
            (
                "Secure Network Enforcement",
                "All non-essential network activity is automatically restricted through enforced firewall and isolation policies. Any attempt to bypass, manipulate, or interfere with these controls will result in immediate termination of the examination."
            ),
            (
                "System Integrity Lockdown",
                "The application enforces a secure execution environment by restricting system-level actions such as screen sharing, virtual machines, unauthorized applications, and background processes. Violations will be logged and acted upon."
            ),
            (
                "Violation Tracking and Reporting",
                "All activities, including potential violations, are logged with timestamps and contextual evidence. Repeated or severe violations may lead to automatic submission, disqualification, or further disciplinary action."
            )
        ]
        
        for rule_title, rule_desc in rules:
            item_layout = QVBoxLayout()
            item_layout.setSpacing(5)
            
            lbl_title = QLabel(rule_title)
            lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #1E293B; background: transparent;")
            item_layout.addWidget(lbl_title)
            
            lbl_desc = QLabel(rule_desc)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("font-size: 14px; font-weight: 500; color: #64748B; background: transparent; line-height: 1.4;")
            item_layout.addWidget(lbl_desc)
            
            scroll_layout.addLayout(item_layout)
            
        scroll_layout.addStretch()
        self.scroll.setWidget(scroll_content)
        
        right_layout.addWidget(self.scroll)
        right_layout.addSpacing(20)
        
        # Consent checkbox.
        checkbox_lyt = QHBoxLayout()
        self.cb_consent = QCheckBox(" I acknowledge and agree to abide by the Examination Terms and Conditions")
        self.cb_consent.setEnabled(False)
        # Resolve check icon path for both packaged and source execution.
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.join(os.path.dirname(__file__), "..")
            
        check_icon_path = os.path.normpath(os.path.join(base_path, "assets", "tick.svg"))
        if not os.path.exists(check_icon_path):
            check_icon_path = ""
        else:
            # Normalize path for stylesheet url(...).
            check_icon_path = check_icon_path.replace('\\', '/')
            
        checkbox_css = f"""
            QCheckBox {{
                background: transparent;
                color: #0F172A;
                font-size: 14px;
                font-weight: 700;
                margin-left: 5px;
                spacing: 10px;
            }}
            QCheckBox:disabled {{
                color: #94A3B8;
            }}
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: 2px solid #CBD5E1;
                background: #FFFFFF;
            }}
            QCheckBox::indicator:disabled {{
                background: #F1F5F9;
                border: 2px solid #E2E8F0;
            }}
            QCheckBox::indicator:hover:!disabled {{
                border-color: #6366F1;
            }}
            QCheckBox::indicator:checked {{
                background-color: #FFFFFF;
                border: 2px solid #e8e8e8;
            }}
        """
        
        if check_icon_path:
             checkbox_css += f"""
             QCheckBox::indicator:checked {{
                 image: url('{check_icon_path}');
             }}
             """
             
        self.cb_consent.setStyleSheet(checkbox_css)

        # Enable consent once the user reaches the end of the rules.
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.scroll.verticalScrollBar().rangeChanged.connect(self.on_scroll_range_changed)

        checkbox_lyt.addWidget(self.cb_consent)
        checkbox_lyt.addStretch()
        right_layout.addLayout(checkbox_lyt)
        
        right_layout.addSpacing(30)
        
        # Footer actions.
        btn_row = QHBoxLayout()
        
        self.btn_decline = QPushButton("Decline && Exit")
        self.btn_decline.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_decline.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; font-weight: bold; color: #EF4444; }
            QPushButton:hover { color: #DC2626; }
        """)
        btn_row.addWidget(self.btn_decline)
        btn_row.addStretch()
        
        self.btn_proceed = QPushButton("Accept && Continue  →")
        self.btn_proceed.setCursor(Qt.CursorShape.ForbiddenCursor)
        self.btn_proceed.setFixedHeight(48)
        self.btn_proceed.setEnabled(False)
        self.btn_proceed.setStyleSheet("""
            QPushButton {
                background-color: #0F172A; color: #FFFFFF; border-radius: 8px; font-weight: bold; font-size: 15px; padding: 0 40px;
            }
            QPushButton:hover:!disabled { background-color: #1E293B; }
            QPushButton:disabled { background-color: #CBD5E1; color: #F1F5F9; }
        """)
        btn_row.addWidget(self.btn_proceed)
        right_layout.addLayout(btn_row)
        
        main_layout.addWidget(right_panel, 1)
        
        self.btn_decline.clicked.connect(self._on_decline)
        self.btn_proceed.clicked.connect(self._on_start)
        self.cb_consent.toggled.connect(self.on_consent_toggled)

    def on_scroll(self, value):
        scrollbar = self.scroll.verticalScrollBar()
        if value >= scrollbar.maximum() - 10:
            self.cb_consent.setEnabled(True)

    def on_scroll_range_changed(self, min_val, max_val):
        if max_val <= 0:
            self.cb_consent.setEnabled(True)

    def on_consent_toggled(self, checked):
        self.btn_proceed.setEnabled(checked)

        if checked:
            self.btn_proceed.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_proceed.setStyleSheet("""
                QPushButton {
                    background-color: #0F172A;
                    color: #FFFFFF;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 15px;
                    padding: 0 40px;
                }
                QPushButton:hover {
                    background-color: #1E293B;
                }
            """)
        else:
            self.btn_proceed.setCursor(Qt.CursorShape.ForbiddenCursor)
            self.btn_proceed.setStyleSheet("""
                QPushButton {
                    background-color: #CBD5E1;
                    color: #F1F5F9;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 15px;
                    padding: 0 40px;
                }
            """)

    def _on_decline(self):
        self.cancelled.emit("User declined terms & conditions.")
        app = QApplication.instance()
        if app:
            app.quit()
        else:
            sys.exit(0)

    def _on_start(self):
        if self._start_emitted:
            return
        self._start_emitted = True
        self.btn_proceed.setText("Booting secure environment...")
        self.btn_proceed.setEnabled(False)
        self.btn_decline.setEnabled(False)
        self.exam_started.emit()
