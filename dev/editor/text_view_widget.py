from PySide6.QtWidgets import QTextEdit


class TextViewWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def set_text(self, text):
        self.setPlainText(text)