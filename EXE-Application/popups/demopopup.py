import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox, QCheckBox
from PyQt6.QtCore import Qt

# Ensure the parent directory is in sys.path so we can import ui components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ui.components.premium_popup import PremiumPopup

class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Observe ")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        
        btn_error = QPushButton("1. Show Main Error Popup (main.py)")
        btn_error.clicked.connect(self.show_error)
        
        btn_submit = QPushButton("2. Show Submit Final (coding_section.py)")
        btn_submit.clicked.connect(self.show_submit)
        
        btn_network = QPushButton("3. Show Network Consent (network_consent_dialog.py)")
        btn_network.clicked.connect(self.show_network)

        btn_app_closer = QPushButton("4. Show App Closer Warning (app_closer_screen.py)")
        btn_app_closer.clicked.connect(self.show_app_closer)
        
        for btn in [btn_error, btn_submit, btn_network, btn_app_closer]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 14px; 
                    font-size: 14px;
                    font-family: 'Inter', sans-serif;
                    font-weight: 700; 
                    background-color: #0F172A; 
                    color: white; 
                    border-radius: 8px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #1E293B;
                }
            """)
            layout.addWidget(btn)

    def show_error(self):
        PremiumPopup.show_message(
            parent=self,
            title="Authentication Error",
            message="Invalid credentials provided. Please check your username and password.",
            icon=QMessageBox.Icon.Critical,
            buttons=QMessageBox.StandardButton.Ok
        )

    def show_submit(self):
        PremiumPopup.show_message(
            parent=self,
            title="Submit Final",
            message="Submit your final solution? You won't be able to change it afterward.",
            icon=QMessageBox.Icon.Question,
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No
        )

    def show_network(self):
        checkbox = QCheckBox("I consent to temporary network isolation for this exam session.")
        checkbox.setStyleSheet("color: #475569; font-size: 14px; padding: 10px; font-weight: bold;")
        
        PremiumPopup.show_message(
            parent=self,
            title="Allow Secure Network Isolation",
            message="During the exam, network access is restricted to approved services only. "
                    "This protects exam integrity and will be automatically restored after submission or termination.",
            icon=QMessageBox.Icon.Warning,
            buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            custom_widget=checkbox
        )

    def show_app_closer(self):
        PremiumPopup.show_message(
            parent=self,
            title="Cannot Proceed",
            message="Please terminate all suspicious processes before continuing.\n\n"
                    "Detected 2 suspicious process(es).\n"
                    "Use the 'Force Close All' button to verify they are closed.",
            icon=QMessageBox.Icon.Warning,
            buttons=QMessageBox.StandardButton.Ok
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())
