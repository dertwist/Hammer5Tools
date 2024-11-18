import ast

from src.soudevent_editor.ui_properties_window import Ui_MainWindow
from src.preferences import settings, debug
from src.soudevent_editor.property.frame import SoundEventEditorPropertyFrame
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt, Signal

class SoundEventEditorPropertiesWindow(QMainWindow):
    edited = Signal(dict)
    def __init__(self, parent=None, value: str = None):
        """
        The properties window is supposed to store property frame instances in the layout.
        When any of the frames are edited, the value updates and
        sends a signal that can be used to save the file or update the tree item in the hierarchy.
        """

        # TOOD remove self.value and value, load value
        super().__init__(parent)

        # Load ui file
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Init QT settings variable from preferences
        self.settings = settings

        # Init common state variables
        self.realtime_save = False

        # Init value variable:
        self.value = self.load_value(value)

        # Init context menu connection
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

        # Hide properties on start
        self.properties_groups_hide()

    #=============================================================<  Load value  >==========================================================
    def load_value(self, value):
        if isinstance(value, str):
            return ast.literal_eval(value)
        elif isinstance(value, dict):
            return value

    #=======================================================<  Properties widget  >=====================================================

    def properties_groups_hide(self):
        """Hide properties and show placeholder"""
        self.ui.properties_spacer.hide()
        self.ui.properties_placeholder.show()
        self.ui.CommetSeciton.hide()
    def properties_groups_show(self):
        """Show properties and hide placeholder"""
        self.ui.properties_placeholder.hide()
        self.ui.properties_spacer.show()
        self.ui.CommetSeciton.show()
    def properties_clear(self):
        for i in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(i).widget()
            if isinstance(widget, SoundEventEditorPropertyFrame):
                widget.deleteLater()
    def populate_properties(self, _data):
        """Loading properties from given data"""
        if isinstance(_data, dict):
            # Reverse input data and use insertWidget with index 0 because in that way all widgets will be upper spacer
            debug(f"_data \n {_data}")
            for item, value in reversed(_data.items()):
                self.create_property(item,value)
        else:
            print(f"[SoundEventEditorProperties]: Wrong input data format. Given data: \n {_data} \n {type(_data)}")

    #=============================================================<  Property  >==========================================================
    def create_property(self, key, value):
        """Create frame widget instance"""
        widget_instance = SoundEventEditorPropertyFrame(_data={key: value}, widget_list=self.ui.properties_layout)
        widget_instance.edited.connect(self.on_update)
        self.ui.properties_layout.insertWidget(0, widget_instance)

    def get_property_value(self, index):
        """Getting dict value from widget instance frame"""
        widget_instance = self.ui.properties_layout.itemAt(index).widget()
        if isinstance(widget_instance, SoundEventEditorPropertyFrame):
            value = widget_instance.value
            debug(f"Getting SoundEventEditorPropertyFrame Value: \n {value}")
            return value
        else:
            return {}
    def get_properties_value(self):
        """Getting all values from frame widget which in layout"""
        _data: dict = {}
        for index in range(self.ui.properties_layout.count()):
            _data.update(self.get_property_value(index))
        return _data

    #==============================================================<  Updating  >===========================================================
    def on_update(self):
        """Updating dict value and send signal"""
        _data = self.get_properties_value()
        debug(f"Some of widget instance were edited, Data: \n {_data}")
        self.edited.emit(_data)

    #============================================================<  Context menu  >=========================================================
    def open_context_menu(self, position):
        """Layout context menu"""
        menu = QMenu()
        menu.addSeparator()
        # New Property action
        new_property = menu.addAction("New Property")
        new_property.setShortcut(QKeySequence(QKeySequence("Ctrl + F")))
        # Paste action
        paste = menu.addAction("Paste")
        paste.setShortcut(QKeySequence(QKeySequence("Ctrl + V")))
        menu.exec(self.ui.scrollArea.viewport().mapToGlobal(position))