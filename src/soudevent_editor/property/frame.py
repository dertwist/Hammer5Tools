from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from src.soudevent_editor.property.ui_frame import Ui_Form
from src.widgets import FloatWidget


class SoundEventEditorPropertyFrame(QWidget):
    def __init__(self, parent=None, _data: dict = None):
        """Data variable is _data:d can receive only dict value"""
        super().__init__(parent)
        # If dict value is empty, just skip initialization of the frame and delete item itself
        if _data is None:
            self.deleteLater()
        else:
            self.ui = Ui_Form()
            self.ui.setupUi(self)
            self.init(data=_data)

    def add_property(self, name: str, value:str):
        """
        Adding a property to the frame widget.
        Import properties classes form another file
        """
        from src.soudevent_editor.property.base import SoundEventEditorPropertyBase
        self.property_instance = SoundEventEditorPropertyBase(label_text=name)
        self.layout().addWidget(self.property_instance)

    def get_property(self):
        "Getting single property from the frame widget"
        pass

    def init(self, data: dict):
        """Init the frame widget and populate properties, usually this is only one property in the widget"""
        self.populate_properties(data=data)
    def populate_properties(self, data: dict):
        """Adding properties from received data"""
        for name, value in data:
            self.add_property(name, value)
