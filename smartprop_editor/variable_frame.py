from smartprop_editor.ui_variable_frame import Ui_Form


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.property_actions import PropertyActions
import ast

class VariableFrame(QWidget):
    def __init__(self, name, widget_list):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.name = name

        self.init_ui()


    def init_ui(self):

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
