from PySide6.QtWidgets import QWidget, QVBoxLayout,QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction,QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu, QLabel, QLineEdit
from soudevent_editor.properties.ui_legacy_property import Ui_LegacyPropertyWidet

class LegacyProperty(QWidget):
    def __init__(self, name, value, status_bar):
        super().__init__()
        self.ui = Ui_LegacyPropertyWidet()
        self.ui.setupUi(self)
        self.name = name
        self.value = value
        self.status_bar = status_bar  # Make status_bar an instance variable
        self.init_ui()

    def init_ui(self):
        self.ui.label.setText(self.name)
        self.ui.lineEdit.setText(self.value)
        self.ui.lineEdit.textChanged.connect(self.update_value_from_lineedit)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_value_from_lineedit(self):
        self.value = self.ui.lineEdit.text()
        self.status_bar.showMessage(f"{self.ui.lineEdit.text()}")

    def show_context_menu(self, event):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        duplicate_action = QAction("Duplicate", context_menu)
        context_menu.addActions([delete_action, duplicate_action])

        action = context_menu.exec(QCursor.pos())

        if action == delete_action:
            self.deleteLater()
            self.status_bar.showMessage(f"Deleted: {self.ui.label.text()}")

        elif action == duplicate_action:
            new_item = LegacyProperty(name=self.label.text(), value=self.ui.lineEdit.text(), status_bar=self.status_bar)
            new_item.setContextMenuPolicy(Qt.CustomContextMenu)
            new_item.customContextMenuRequested.connect(self.show_context_menu)
            widget_list.layout().addWidget(new_item)