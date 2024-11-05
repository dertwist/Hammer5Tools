from PySide6.QtWidgets import QWidget
from src.soudevent_editor.property.ui_frame import Ui_Form

class SoundEventEditorPropertyFrame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

