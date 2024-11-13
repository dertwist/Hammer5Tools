import random

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QApplication
from PySide6.QtCore import Signal
from src.soudevent_editor.property.ui_frame import Ui_Form
from src.widgets import FloatWidget
from src.property.methods import PropertyMethods
from src.common import convert_snake_case, JsonToKv3, Kv3ToJson


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
            self.name = str(next(iter(_data)))
            self.widget_list = widget_list
            self._height = 24

            # Populate
            self.populate_properties(data=_data)

            # Init
            self.init_connections()
            self.init_header()
    def init_connections(self):
        """Adding connections to the buttons"""
        self.ui.show_child.clicked.connect(self.show_child_action)
        self.ui.delete_button.clicked.connect(self.delete_action)
        self.ui.copy_button.clicked.connect(self.copy_action)
    def init_header(self):
        """Setup for header frame"""
        self.ui.property_class.setText(convert_snake_case(self.name))

    #=============================================================<  Properties  >===========================================================

    def add_property(self, name: str, value:str):
        """
        Adding a property to the frame widget.
        Import properties classes form another file
        """

        # Widgets import
        from src.soudevent_editor.property.base import SoundEventEditorPropertyBase, SoundEventEditorPropertyFloat, SoundEventEditorPropertyInt

        # Float
        if name == 'volume':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name, slider_range=[0, 0],
                                                                   only_positive=True)
        elif name == 'delay':
            self.property_instance = SoundEventEditorPropertyFloat(label_text=name)
        else:
            # self.property_instance = SoundEventEditorPropertyBase(label_text=name)
            self.property_instance = SoundEventEditorPropertyInt(label_text=name, slider_range=[0,10], only_positive=True)
        # Int
        # Bool
        # Curve
        # Combobox
        # Vector3
        # Files
        self.property_instance.edited.connect(self.on_property_updated)
        self.ui.content.layout().addWidget(self.property_instance)
    def on_property_updated(self):
        """If some of the properties were changed send signa with dict value"""
        self.value = self.serialize_properties()
        self.edited.emit()

    def populate_properties(self, data: dict):
        """Adding properties from received data"""
        for name in data:
            self.add_property(name, data[name])
    def serialize_properties(self):
        """Geather all values into dict value"""
        _data = {}
        for index in range(self.ui.content.layout().count()):
            widget_instance = self.ui.content.layout().itemAt(index).widget()
            _data.update(widget_instance.value)
        return _data

    def get_property(self, index):
        """Getting single property from the frame widget"""
        pass
    def deserialize_property(self, _data: dict = None):
        """Deserialize property from json"""

    #==============================================================<  Actions  >============================================================

    def copy_action(self):
        """Copy action"""
        clipboard = QApplication.clipboard()
        _data = self.serialize_properties()
        _data = str(_data)
        clipboard.setText(_data)

    def delete_action(self):
        """Set value to None, then send signal that updates value then delete self"""
        self.value = None
        self.edited.emit()
        self.deleteLater()


    def show_child_action(self):
        if not self.ui.show_child.isChecked():
            self.ui.content.setMaximumHeight(0)
        else:
            self.ui.content.setMaximumHeight(16666)

    #===========================================================<  Drag and drop  >=========================================================

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    dropEvent = PropertyMethods.dropEvent

