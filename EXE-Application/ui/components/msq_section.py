from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import Qt


class MSQSection(QWidget):
    def __init__(
        self,
        question_text: str = "Which of the following are valid IP addresses? (Select all that apply)",
        options: list[str] = None,
    ):
        super().__init__()
        if options is None:
            options = ["192.168.1.1", "256.256.256.256", "10.0.0.1", "127.0.0.1"]

        self.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        q_text = QLabel(question_text)
        q_text.setWordWrap(True)
        q_text.setStyleSheet(
            "font-size: 18px; color: #000000; line-height: 1.6; "
            "font-weight: 600; font-family:'Inter','Segoe UI',sans-serif;"
        )
        layout.addWidget(q_text)
        layout.addSpacing(25)

        self._checkboxes: list[QCheckBox] = []

        for opt in options:
            cb = QCheckBox(opt)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setStyleSheet(self._cb_style(False))
            cb.stateChanged.connect(
                lambda state, c=cb: c.setStyleSheet(self._cb_style(state > 0))
            )
            self._checkboxes.append(cb)
            layout.addWidget(cb)
            layout.addSpacing(10)

        layout.addStretch()

    @staticmethod
    def _cb_style(checked: bool) -> str:
        if checked:
            return """
                QCheckBox {
                    font-size: 15px; font-family: 'Inter', 'Segoe UI', sans-serif;
                    color: #4338CA; font-weight: 500;
                    padding: 16px 20px; border-radius: 12px;
                    border: 2px solid #6366F1; background-color: #EEF2FF;
                }
                QCheckBox::indicator {
                    width: 20px; height: 20px; border-radius: 12px;
                    border: 6px solid #6366F1; background-color: #FFFFFF; margin-right: 12px;
                }
            """
        return """
            QCheckBox {
                font-size: 15px; font-family: 'Inter', 'Segoe UI', sans-serif;
                color: #1E293B; font-weight: 500;
                padding: 16px 20px; border-radius: 12px;
                border: 1.5px solid #E2E8F0; background-color: #FFFFFF;
            }
            QCheckBox:hover { background-color: #F8FAFC; border-color: #CBD5E1; }
            QCheckBox::indicator {
                width: 20px; height: 20px; border-radius: 12px;
                border: 2px solid #CBD5E1; background: #FFFFFF; margin-right: 12px;
            }
        """

    # ── Answer API ────────────────────────────────────────────────────────────
    def get_answer(self) -> list[str]:
        return [cb.text() for cb in self._checkboxes if cb.isChecked()]

    def set_answer(self, answer):
        if isinstance(answer, dict):
            answer = answer.get("answer")

        if isinstance(answer, str):
            tokens = [part.strip() for part in answer.replace("\n", ",").split(",") if part.strip()]
            selected = set(tokens)
        elif isinstance(answer, list):
            selected = {str(item) for item in answer if item is not None}
        elif answer:
            selected = {str(answer)}
        else:
            selected = set()

        for cb in self._checkboxes:
            cb.setChecked(cb.text() in selected)
