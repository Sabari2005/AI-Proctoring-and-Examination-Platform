import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtSvgWidgets import QSvgWidget

# Add assets path 
assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.svg"))

class SubmitFinalPopupPrototype(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        overlay = QFrame()
        overlay.setStyleSheet("background-color: rgba(11, 17, 32, 0.7);")
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.setContentsMargins(40, 40, 40, 40)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                max-width: 440px;
            }
        """)

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 1. Logo (Top Left)
        logo_layout = QHBoxLayout()
        if os.path.exists(assets_path):
            logo_svg = QSvgWidget(assets_path)
            logo_svg.setFixedSize(90, 26)
            logo_svg.setStyleSheet("background: transparent; border: none;")
            logo_layout.addWidget(logo_svg)
        else:
            logo_lbl = QLabel("OBSERVE")
            logo_lbl.setFont(QFont("Inter", 14, QFont.Weight.Black))
            logo_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
            logo_layout.addWidget(logo_lbl)
            
        logo_layout.addStretch() # Forces logo to stay locked to the left
        card_layout.addLayout(logo_layout)
        
        # Divider Line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #F8FAFC;")
        card_layout.addWidget(divider)

        # 2. Main Content (Vertical: Title + Text)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 8, 0, 8)
        text_layout.setSpacing(6)
        
        title_lbl = QLabel("Submit Final Solution?")
        title_lbl.setFont(QFont("Inter", 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        text_layout.addWidget(title_lbl)

        msg_lbl = QLabel("You are about to submit your final code. This action is irreversible and you cannot make further changes.")
        msg_lbl.setFont(QFont("Inter", 12))
        msg_lbl.setStyleSheet("color: #475569; border: none; background: transparent;")
        msg_lbl.setWordWrap(True)
        msg_lbl.setMinimumHeight(45) # Solves the Qt wordwrap height-calculation bug
        text_layout.addWidget(msg_lbl)
        
        card_layout.addLayout(text_layout)

        card_layout.addSpacing(16)

        # 3. Buttons (Right Aligned)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #475569;
                border-radius: 6px;
                padding: 8px 16px;
                border: 1px solid #E2E8F0;
            }
            QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_submit = QPushButton("Submit Final")
        btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_submit.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #0F172A;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 16px;
                border: none;
            }
            QPushButton:hover { background-color: #1E293B; }
            QPushButton:pressed { background-color: #334155; }
        """)
        btn_submit.clicked.connect(self.accept)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_submit)

        card_layout.addLayout(btn_layout)

        overlay_layout.addWidget(card)
        root_layout.addWidget(overlay)

        if self.parent() and self.parent().windowState() & Qt.WindowState.WindowFullScreen:
            self.showFullScreen()
        else:
            self.resize(self.parent().size() if self.parent() else self.sizeHint())

def main():
    app = QApplication(sys.argv)
    
    bg = QWidget()
    bg.resize(1024, 768)
    bg.setStyleSheet("background-color: #0B1120;")
    bg.setWindowTitle("Observe App Background")
    bg.show()

    dialog = SubmitFinalPopupPrototype(parent=bg)
    dialog.exec()
    
    sys.exit()

if __name__ == "__main__":
    main()
