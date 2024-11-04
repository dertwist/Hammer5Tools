from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.ui_checkbox_property import Ui_PropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions
from distutils.util import strtobool

class CheckboxProperty(QWidget):
    def __init__(self, name, display_name, value, widget_list):
        super().__init__()
        self.ui = Ui_PropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.checkBox.setAcceptDrops(False)
        self.widget_list = widget_list
        self.name = name
        self.ui.label.setText(display_name)
        self.value = bool(strtobool(value))
        self.ui.checkBox.setChecked(self.value)
        self.init_ui()

    def init_ui(self):

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    def update_checkbox_on_change(self):
        self.ui.checkBox.isChecked(self.value)


    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
