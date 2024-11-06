from PySide6.QtWidgets import QWidget, QLabel
from src.widgets import FloatWidget

class SoundEventEditorPropertyBase(QWidget):
    def __init__(self, parent=None, label_text: str = None):
        super().__init__(parent)
        if label_text is None:
            label_text = "Label"
        label_instance = QLabel()
        label_instance.setText(label_text)
        self.layout().addWidget(label_instance)