import random

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QApplication
from PySide6.QtCore import Signal
from src.soudevent_editor.property.ui_frame import Ui_Form
from src.widgets import FloatWidget
from src.property.methods import PropertyMethods


class SoundEventEditorPropertyFrame(QWidget):
    """PropertyFrame suppose to collect properties and gives dict value"""
    edited = Signal()
    def __init__(self, _data: dict = None, widget_list: QHBoxLayout = None):
        """Data variable is _data:d can receive only dict value"""
        super().__init__()

        # If dict value is empty, just skip initialization of the frame and delete item itself
        if widget_list is None:
            raise ValueError
        if _data is None:
            self.deleteLater()
        else:
            # Init UI file
            self.ui = Ui_Form()
            self.ui.setupUi(self)
            self.setAcceptDrops(True)

            # Variables
            self.value = dict()
            self.name = str(_data)
            self.widget_list = widget_list

            # Populate
            self.populate_properties(data=_data)


    def add_property(self, name: str, value:str):
        """
        Adding a property to the frame widget.
        Import properties classes form another file
        """
        from src.soudevent_editor.property.base import SoundEventEditorPropertyBase, SoundEventEditorPropertyFloat
        self.property_instance = SoundEventEditorPropertyFloat(label_text=name)
        self.layout().addWidget(self.property_instance)

    def get_property(self):
        """Getting single property from the frame widget"""
        pass

    def populate_properties(self, data: dict):
        """Adding properties from received data"""
        for name in data:
            self.add_property(name, data[name])
    def serialize_property(self):
        """Serialize property to json"""
        value = {}
        return str(value)
    def deserialize_property(self):
        """Deserialize property from json"""

    #==============================================================<  Actions  >============================================================

    def copy_action(self):
        """Copy action"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.serialize_property())

    def delete_action(self):
        """Set value to None, then send signal that updates value then delete self"""
        self.value = None
        self.edited.emit()
        self.deleteLater()

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    dropEvent = PropertyMethods.dropEvent

