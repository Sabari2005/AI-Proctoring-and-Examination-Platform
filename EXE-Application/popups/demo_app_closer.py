import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt6.QtCore import Qt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ui.components.premium_popup import PremiumPopup

def main():
    app = QApplication(sys.argv)
    
    bg = QWidget()
    bg.resize(1024, 768)
    bg.setStyleSheet("background-color: #0B1120;") 
    bg.setWindowTitle("Observe App Background")
    bg.show()

    PremiumPopup.show_message(
        parent=bg,
        title="Cannot Proceed",
        message="Please terminate all suspicious processes before continuing.\n\n"
                "Detected 2 suspicious process(es).\n"
                "Use the 'Force Close All' button to verify they are closed.",
        icon=QMessageBox.Icon.Warning,
        buttons=QMessageBox.StandardButton.Ok
    )
    
    sys.exit()

if __name__ == "__main__":
    main()
