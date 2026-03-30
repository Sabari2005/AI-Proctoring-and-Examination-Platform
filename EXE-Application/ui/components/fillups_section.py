from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import Qt


class FillupsSection(QWidget):
    def __init__(
        self,
        question_text: str = "In Python, the ______ keyword is used to define a function.",
    ):
        super().__init__()
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

        self.answer_input = QLineEdit()
        self.answer_input.setPlaceholderText("Type your answer here...")
        self.answer_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E2E8F0;
                border-radius: 12px;
                padding: 16px 20px;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 15px;
                font-weight: 500;
                color: #0F172A;
                background-color: #F8FAFC;
            }
            QLineEdit:focus { 
                border: 2px solid #6366F1; 
                background-color: #FFFFFF;
            }
        """)
        layout.addWidget(self.answer_input)
        layout.addStretch()

    def get_answer(self) -> str:
        return self.answer_input.text().strip()

    def set_answer(self, answer):
        if isinstance(answer, list):
            value = answer[0] if answer else ""
        elif isinstance(answer, dict):
            value = answer.get("answer", "")
        else:
            value = answer
        self.answer_input.setText(str(value) if value is not None else "")
