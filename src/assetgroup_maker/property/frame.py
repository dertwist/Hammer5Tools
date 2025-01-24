import ast
import os.path
import random

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QApplication, QTreeWidget
from PySide6.QtCore import Signal

from src.assetgroup_maker.property.common import PropertyReplacement
from src.assetgroup_maker.property.ui_frame import Ui_Form
from src.widgets import FloatWidget
from src.property.methods import PropertyMethods
from src.common import convert_snake_case, JsonToKv3, Kv3ToJson
from src.preferences import debug, get_addon_dir


class PropertyFrame(QWidget):
    """PropertyFrame suppose to collect properties and gives dict value"""
    edited = Signal()
    def __init__(self, _data: dict = None, widget_list: QHBoxLayout = None, tree:QTreeWidget = None):
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
            self.tree = tree
            self.value = dict()
            self.name = str(next(iter(_data)))
            self.widget_list = widget_list
            self._height = 24

            self.setMinimumHeight(72)
            self.setMaximumHeight(72)

            # Populate
            self.populate_properties(data=_data)

            # Init
            self.init_connections()
            self.init_header()

            # Update data
            self.on_property_updated()

            # TODO add support of copy and paste functions
            self.ui.copy_button.hide()

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
        # Convert value str to dict
        if isinstance(value, str):
            try:
                value = ast.literal_eval(value)
            except Exception as error:
                debug(error)

        if name == 'volume':
            pass
        # Legacy
        else:
            self.property_instance = PropertyReplacement(label_text=name,value=value)
        self.property_instance.edited.connect(self.on_property_updated)
        self.ui.content.layout().addWidget(self.property_instance)
    def on_property_updated(self):
        """If some of the properties were changed send signa with dict value"""
        self.value = self.serialize_properties()
        self.edited.emit()

    def populate_properties(self, data: dict):
        """Adding properties from received data"""
        for name, value in data.items():
            self.add_property(name, value)
    def serialize_properties(self):
        """Geather all values into dict value"""
        _data = {}
        for index in range(self.ui.content.layout().count()):
            widget_instance = self.ui.content.layout().itemAt(index).widget()
            value_dict = widget_instance.value
            _data.update(value_dict)
        debug(f"serialize_properties frame Data: \n {_data}")
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
        for index in range(self.ui.content.layout().count()):
            widget_instance = self.ui.content.layout().itemAt(index).widget()
            widget_instance.deleteLater()
        self.value = None
        self.edited.emit()
        self.deleteLater()


    def show_child_action(self):
        """Showing child widgets, resizes the layout to hide or show child"""
        if not self.ui.show_child.isChecked():
            self.ui.content.setMaximumHeight(0)
        else:
            self.ui.content.setMaximumHeight(16666)

    #===========================================================<  Drag and drop  >=========================================================

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    def dropEvent(self, event):
        if event.source() == self:
            return

        mime_data = event.mimeData()
        if mime_data.hasText():
            if event.source() != self:
                source_index = self.widget_list.layout().indexOf(event.source())
                target_index = self.widget_list.layout().indexOf(self)

                widget: PropertyFrame = self.widget_list.layout().itemAt(target_index).widget()
                widget_property = widget.ui.content.layout().itemAt(0).widget()

                if source_index != -1 and target_index != -1:
                    if source_index < self.widget_list.layout().count():
                        source_widget = self.widget_list.layout().takeAt(source_index).widget()
                        if source_widget:
                            self.widget_list.layout().insertWidget(target_index, source_widget)

        event.accept()

