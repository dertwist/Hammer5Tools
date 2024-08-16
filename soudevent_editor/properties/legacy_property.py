from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.ui_legacy_property import Ui_LegacyPropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions
import ast

class LegacyProperty(QWidget):
    def __init__(self, name, value, widget_list):
        super().__init__()
        self.ui = Ui_LegacyPropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.lineEdit.setAcceptDrops(False)
        self.widget_list = widget_list
        self.ui.lineEdit = self.ui.lineEdit
        self.name = name

        if '[' in value and ']' in value:
            self.value = ast.literal_eval(value)
            for item in self.value:
                print(item)
        else:
            self.value = value

        self.init_ui()


    def init_ui(self):
        self.ui.label.setText(self.name)
        self.ui.lineEdit.setText(str(self.value))
        self.ui.lineEdit.textChanged.connect(self.update_value_from_lineedit)
        self.ui.lineEdit.setClearButtonEnabled(True)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_value_from_lineedit(self):
        self.value = ast.literal_eval(self.ui.lineEdit.text())

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
