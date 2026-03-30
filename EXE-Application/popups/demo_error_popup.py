import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt6.QtCore import Qt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ui.components.premium_popup import PremiumPopup

def main():
    app = QApplication(sys.argv)
    
    # Create a mock application background
    bg = QWidget()
    bg.resize(1024, 768)
    bg.setStyleSheet("background-color: #F8FAFC;")
    bg.setWindowTitle("Observe App Background")
    bg.show()

    # Show the popup over the background
    PremiumPopup.show_message(
        parent=bg,
        title="Authentication Error",
        message="Invalid credentials provided. Please check your username and password.",
        icon=QMessageBox.Icon.Critical,
        buttons=QMessageBox.StandardButton.Ok
    )
    
    sys.exit()

if __name__ == "__main__":
    main()
