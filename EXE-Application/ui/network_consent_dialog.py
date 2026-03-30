"""Network consent dialog shown before exam startup flow."""

from __future__ import annotations
from PyQt6.QtWidgets import QDialog, QCheckBox, QMessageBox
from ui.components.premium_popup import PremiumPopup

class NetworkConsentDialog(QDialog):
    """Consent dialog that confirms temporary exam-time network isolation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._exec_in_progress = False

    def exec(self):
        """Show the consent prompt and return Accepted only after explicit opt-in."""
        if self._exec_in_progress:
            return QDialog.DialogCode.Rejected

        self._exec_in_progress = True
        try:
            while True:
                checkbox = QCheckBox("I consent to temporary network isolation for this exam session.")
                checkbox.setChecked(False)
                checkbox.setStyleSheet("color: #475569; font-size: 14px; padding: 10px; font-weight: bold;")
                res = PremiumPopup.show_message(
                    parent=self.parentWidget(),
                    title="Allow Secure Network Isolation",
                    message="During the exam, network access is restricted to approved services only. "
                            "This protects exam integrity and will be automatically restored after submission or termination.",
                    icon=QMessageBox.Icon.Warning,
                    buttons=QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                    custom_widget=checkbox
                )
                if res == QMessageBox.StandardButton.Ok:
                    if not checkbox.isChecked():
                        PremiumPopup.show_message(
                            parent=self.parentWidget(),
                            title="Consent Required",
                            message="You must check the consent box to continue.",
                            icon=QMessageBox.Icon.Critical,
                            buttons=QMessageBox.StandardButton.Ok
                        )
                        continue
                    self.accept()
                    return QDialog.DialogCode.Accepted

                self.reject()
                return QDialog.DialogCode.Rejected
        finally:
            self._exec_in_progress = False
