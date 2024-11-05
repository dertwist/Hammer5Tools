from PySide6.QtWidgets import QWidget,QHBoxLayout, QVBoxLayout
from src.soudevent_editor.property.ui_frame import Ui_Form
from src.widgets import FloatWidget

class SoundEventEditorPropertyFrame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)


class SoundEventEditorPropertyObject(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout().addWidget(FloatWidget())
