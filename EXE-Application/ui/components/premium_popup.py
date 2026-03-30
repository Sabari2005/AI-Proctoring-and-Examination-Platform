import os
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
    QMessageBox, QWidget, QSizePolicy
)
from PyQt6.QtSvgWidgets import QSvgWidget


class PremiumPopup(QDialog):
    """
    A unified, modern, premium popup dialog.
    It replaces standard QMessageBox usage across the app to provide 
    a highly branded, beautiful UI including the logo SVG.
    """

    def __init__(
        self,
        parent=None,
        title: str = "",
        message: str = "",
        icon: QMessageBox.Icon = QMessageBox.Icon.Information,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
        custom_widget: QWidget = None,
    ):
        super().__init__(parent)
        self.setModal(True)
        # FramelessWindowHint only — NO WA_TranslucentBackground (causes black box on Windows)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        # Use plain white background — no transparency
        self.setStyleSheet("QDialog { background-color: #FFFFFF; border-radius: 12px; }")

        # Output mimicking QMessageBox
        self.clicked_button = QMessageBox.StandardButton.NoButton

        self._icon_type = icon
        self._buttons_mask = buttons
        self._default_button = default_button
        
        self._title_text = title
        self._message_text = message
        self._custom_widget = custom_widget

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        # Small margins to allow the drop shadow from the QDialog to be visible
        root_layout.setContentsMargins(2, 2, 2, 2)
        root_layout.setSpacing(0)

        # Card frame directly in the dialog — no dark overlay
        self.card = QFrame(self)
        self.card.setObjectName("PremiumCard")
        self.card.setStyleSheet("""
            #PremiumCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        self.card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # 1. Logo (Top Left)
        logo_layout = QHBoxLayout()
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logo.svg"))
        if os.path.exists(logo_path):
            logo_svg = QSvgWidget(logo_path)
            logo_svg.setFixedSize(90, 26)
            logo_svg.setStyleSheet("background: transparent; border: none;")
            logo_layout.addWidget(logo_svg)
        else:
            logo_lbl = QLabel("OBSERVE")
            logo_lbl.setFont(QFont("Inter", 14, QFont.Weight.Black))
            logo_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
            logo_layout.addWidget(logo_lbl)
            
        logo_layout.addStretch()
        card_layout.addLayout(logo_layout)
        
        # Divider Line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #F1F5F9; border: none;")
        divider.setFixedHeight(1)
        card_layout.addWidget(divider)

        # 2. Main Content (Vertical: Title + Text + Custom)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 8, 0, 8)
        text_layout.setSpacing(6)
        
        title_lbl = QLabel(self._title_text)
        title_lbl.setFont(QFont("Inter", 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        text_layout.addWidget(title_lbl)

        if self._message_text:
            msg_lbl = QLabel(self._message_text)
            msg_lbl.setFont(QFont("Inter", 12))
            msg_lbl.setStyleSheet("color: #475569; border: none; background: transparent;")
            msg_lbl.setWordWrap(True)
            msg_lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            text_layout.addWidget(msg_lbl)
            
        if self._custom_widget:
            text_layout.addSpacing(10)
            text_layout.addWidget(self._custom_widget)
            
        card_layout.addLayout(text_layout)

        card_layout.addSpacing(16)

        # 3. Buttons (Right Aligned)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        # Secondary Buttons (shown on left of primary)
        self._add_button_if_requested(btn_layout, QMessageBox.StandardButton.Cancel, "Cancel", is_primary=False)
        self._add_button_if_requested(btn_layout, QMessageBox.StandardButton.No, "No", is_primary=False)
        self._add_button_if_requested(btn_layout, QMessageBox.StandardButton.Abort, "Abort", is_primary=False)
        self._add_button_if_requested(btn_layout, QMessageBox.StandardButton.Retry, "Retry", is_primary=False)
        
        # Primary Buttons
        self._add_button_if_requested(btn_layout, QMessageBox.StandardButton.Yes, "Yes", is_primary=True)
        self._add_button_if_requested(btn_layout, QMessageBox.StandardButton.Ok, "OK", is_primary=True)

        card_layout.addLayout(btn_layout)
        root_layout.addWidget(self.card)

        # Size to content, then center over parent window
        self.adjustSize()
        self._center_over_parent()

    def _center_over_parent(self):
        """Center this dialog over the parent's top-level window."""
        parent = self.parent()
        if parent:
            window = parent.window()
            geo = window.frameGeometry()
            center = geo.center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)


    def _add_button_if_requested(self, layout, btn_flag: QMessageBox.StandardButton, label: str, is_primary: bool):
        if self._buttons_mask & btn_flag:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Inter", 11, QFont.Weight.Bold))
            
            if is_primary:
                btn.setStyleSheet("""
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
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F8FAFC;
                        color: #475569;
                        border-radius: 6px;
                        padding: 8px 16px;
                        border: 1px solid #E2E8F0;
                    }
                    QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }
                """)
                
            btn.clicked.connect(lambda: self._finish(btn_flag))
            layout.addWidget(btn)

    def _finish(self, btn_flag: QMessageBox.StandardButton):
        self.clicked_button = btn_flag
        # Custom widgets may be reused by callers across repeated popup loops.
        # Detach them before closing so they are not destroyed with this dialog.
        if self._custom_widget is not None:
            try:
                parent = self._custom_widget.parentWidget()
                if parent is not None:
                    layout = parent.layout()
                    if layout is not None:
                        layout.removeWidget(self._custom_widget)
                self._custom_widget.setParent(None)
            except RuntimeError:
                pass
        if btn_flag in (QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.No, QMessageBox.StandardButton.Abort):
            self.reject()
        else:
            self.accept()

    @classmethod
    def show_message(
        cls,
        parent=None,
        title: str = "",
        message: str = "",
        icon: QMessageBox.Icon = QMessageBox.Icon.Information,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
        custom_widget: QWidget = None
    ) -> QMessageBox.StandardButton:
        """Helper to act identically to QMessageBox static methods but using PremiumPopup."""
        dialog = cls(parent, title, message, icon, buttons, default_button, custom_widget)
        dialog.exec()
        return dialog.clicked_button

