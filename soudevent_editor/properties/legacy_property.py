from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.ui_legacy_property import Ui_LegacyPropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions

class LegacyProperty(QWidget):
    def __init__(self, name, value, status_bar, widget_list):
        super().__init__()
        self.ui = Ui_LegacyPropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.lineEdit.setAcceptDrops(False)
        self.widget_list = widget_list
        self.ui.lineEdit = self.ui.lineEdit
        self.name = name
        self.value = value
        self.status_bar = status_bar
        self.init_ui()


    def init_ui(self):
        self.ui.label.setText(self.name)
        self.ui.lineEdit.setText(self.value)
        self.ui.lineEdit.textChanged.connect(self.update_value_from_lineedit)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_value_from_lineedit(self):
        self.value = self.ui.lineEdit.text()
        self.status_bar.setText(f"{self.ui.lineEdit.text()}")

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
