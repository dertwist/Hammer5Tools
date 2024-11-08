from PySide6.QtWidgets import QWidget, QLabel
from src.widgets import FloatWidget

class SoundEventEditorPropertyBase(QWidget):
    def __init__(self, parent=None, label_text: str = None):
        """Base property class. There is only a label widget and a frame. New widget can be replaced or added"""
        super().__init__(parent)
        self.init_label(label_text)

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
    def init_label(self, label_text):
        """Adding received text to the label widget"""
        if label_text is None:
            label_text = "Label"
        label_instance = QLabel()
        label_instance.setText(label_text)
        self.layout().addWidget(label_instance)
    def add_property_widget(self, widget):
        """Adding property widget to the root"""

class SoundEventEditorPropertyFloat(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None):
        super().__init__(parent)