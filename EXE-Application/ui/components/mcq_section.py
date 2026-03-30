from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QRadioButton, QButtonGroup
from PyQt6.QtCore import Qt


class MCQSection(QWidget):
    def __init__(
        self,
        question_text: str = "What is the primary architectural difference between a monolithic kernel and a microkernel?",
        options: list[str] = None,
    ):
        super().__init__()
        if options is None:
            options = [
                "A) Monolithic kernels handle all OS services in kernel space.",
                "B) Microkernels are generally faster because they have less overhead in IPC.",
                "C) Monolithic kernels crash less frequently due to isolated driver execution.",
                "D) There is no functional difference; they are just different deployment models.",
            ]

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

        self._btn_grp = QButtonGroup(self)
        self._radio_buttons: list[QRadioButton] = []

        for opt in options:
            rb = QRadioButton(opt)
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.setStyleSheet(self._rb_style(False))
            rb.toggled.connect(lambda checked, r=rb: r.setStyleSheet(self._rb_style(checked)))
            self._btn_grp.addButton(rb)
            self._radio_buttons.append(rb)
            layout.addWidget(rb)
            layout.addSpacing(10)

        layout.addStretch()

    @staticmethod
    def _rb_style(checked: bool) -> str:
        if checked:
            return """
                QRadioButton {
                    font-size: 15px; font-family: 'Inter', 'Segoe UI', sans-serif;
                    color: #4338CA; font-weight: 500;
                    padding: 16px 20px; border-radius: 12px;
                    border: 2px solid #6366F1; background-color: #EEF2FF;
                }
                QRadioButton::indicator {
                    width: 20px; height: 20px; border-radius: 12px;
                    border: 6px solid #6366F1; background: #FFFFFF; margin-right: 12px;
                }
            """
        return """
            QRadioButton {
                font-size: 15px; font-family: 'Inter', 'Segoe UI', sans-serif;
                color: #1E293B; font-weight: 500;
                padding: 16px 20px; border-radius: 12px;
                border: 1.5px solid #E2E8F0; background-color: #FFFFFF;
            }
            QRadioButton:hover { background-color: #F8FAFC; border-color: #CBD5E1; }
            QRadioButton::indicator {
                width: 20px; height: 20px; border-radius: 12px;
                border: 2px solid #CBD5E1; background: #FFFFFF; margin-right: 12px;
            }
        """

    # ── Answer API ────────────────────────────────────────────────────────────
    def get_answer(self):
        selected = self._btn_grp.checkedButton()
        return selected.text() if selected else None

    def set_answer(self, answer):
        if isinstance(answer, list):
            value = answer[0] if answer else None
        elif isinstance(answer, dict):
            value = answer.get("answer")
        else:
            value = answer

        selected_text = None
        if isinstance(value, int) and 0 <= value < len(self._radio_buttons):
            selected_text = self._radio_buttons[value].text()
        elif isinstance(value, str):
            raw = value.strip()
            if raw:
                # Exact text match first
                for rb in self._radio_buttons:
                    if rb.text() == raw:
                        selected_text = rb.text()
                        break
                # Then case-insensitive match
                if selected_text is None:
                    lower_raw = raw.lower()
                    for rb in self._radio_buttons:
                        if rb.text().strip().lower() == lower_raw:
                            selected_text = rb.text()
                            break
                # Finally, allow option label selection like "A" or "b"
                if selected_text is None and len(raw) == 1 and raw.isalpha():
                    prefix = raw.upper() + ")"
                    for rb in self._radio_buttons:
                        if rb.text().lstrip().upper().startswith(prefix):
                            selected_text = rb.text()
                            break

        for rb in self._radio_buttons:
            rb.setChecked(rb.text() == selected_text)
