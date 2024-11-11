from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from src.widgets import FloatWidget
from PySide6.QtCore import Signal

class SoundEventEditorPropertyBase(QWidget):
    edited = Signal()
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """Base property class. There is only a label widget and a frame. New widget can be replaced or added"""
        super().__init__(parent)

        # Init
        self.init_root_layout()
        self.init_label(label_text)
        self.init_widget()
        self.set_widget_size()

        # Value variable
        self.value = value

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
    def set_widget_size(self):
        """Set maximum height"""
        self.setMaximumHeight(48)
        self.setMinimumHeight(48)

class SoundEventEditorPropertyFloat(SoundEventEditorPropertyBase):
    def init_widget(self):
        """Initialize float widget instance"""


        self.range = None
        if self.range is None:
            self.float_widget_instance = FloatWidget()
        else:
            self.float_widget_instance = FloatWidget(slider_range=self.range)

        self.add_property_widget(self.float_widget_instance)
    def init_float_widget(self):
        """Specific properties for float widget instance that can be overwritten"""
        pass

class SoundEventEditorPropertyInt(SoundEventEditorPropertyFloat):
    def init_float_widget(self):
        """Adding parameter init for float widget instance"""
        self.float_widget_instance.int_output = True