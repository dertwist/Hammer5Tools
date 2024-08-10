from PySide6.QtWidgets import QWidget, QVBoxLayout,QMenu
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QAction,QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu, QLabel, QLineEdit
from soudevent_editor.properties.ui_legacy_property import Ui_LegacyPropertyWidet

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QDrag

class LegacyProperty(QWidget):
    def __init__(self, name, value, status_bar, widget_list):
        super().__init__()
        self.ui = Ui_LegacyPropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.widget_list = widget_list
        self.name = name
        self.value = value
        self.status_bar = status_bar
        self.init_ui()


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.name)
            drag.setMimeData(mime_data)
            drag.exec()

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if event.source() == self:
            return

        mime_data = event.mimeData()
        if mime_data.hasText():
            name = mime_data.text()
            source_index = self.widget_list.layout().indexOf(self)
            target_index = self.widget_list.layout().indexOf(event.source())

            if source_index != -1 and target_index != -1:
                self.widget_list.layout().takeAt(source_index)
                self.widget_list.layout().insertWidget(target_index, self)

        event.accept()
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