from ui.components.premium_popup import PremiumPopup
from PyQt6.QtWidgets import QMessageBox

class ErrorPopup:
    """Legacy wrapper around PremiumPopup."""
    def __init__(self, title: str, message: str, parent=None):
        self.title = title
        self.message = message
        self.parent = parent
        self.result = QMessageBox.StandardButton.Ok

    def exec(self):
        self.result = PremiumPopup.show_message(
            parent=self.parent,
            title=self.title,
            message=self.message,
            icon=QMessageBox.Icon.Critical,
            buttons=QMessageBox.StandardButton.Ok
        )
        return self.result

def show_error_popup(parent, title: str, message: str):
    dialog = ErrorPopup(title, message, parent=parent)
    return dialog.exec()
