from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from src.widgets import FloatWidget

class SoundEventEditorPropertyBase(QWidget):
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """Base property class. There is only a label widget and a frame. New widget can be replaced or added"""
        super().__init__(parent)
        self.init_root_layout()

        self.init_label(label_text)
        self.init_widget()
        # Value variable
        self.value = value

        self.setMaximumHeight(64)
        self.setMinimumHeight(64)

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)
    def init_label(self, label_text):
        """Adding received text to the label widget"""
        if label_text is None:
            label_text = "Label"
        label_instance = QLabel()
        label_instance.setText(label_text)
        self.root_layout.addWidget(label_instance)
    def add_property_widget(self, widget):
        """Adding property widget to the root"""
        self.root_layout.addWidget(widget)
    def init_widget(self):
        """Function to overwriting."""
    def set_maxheight(self):
        """Set maximum height"""
        self.setMaximumHeight(32)

class SoundEventEditorPropertyFloat(SoundEventEditorPropertyBase):
    def init_widget(self):
        widget = FloatWidget()
        self.add_property_widget(widget)