from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag,QAction

class PropertyActions:
    @staticmethod
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    @staticmethod
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.name)
            drag.setMimeData(mime_data)
            drag.exec()

    @staticmethod
    def dragEnterEvent(self, event):
        event.accept()

    @staticmethod
    def dropEvent(self, event):
        if event.source() == self:
            return

        mime_data = event.mimeData()
        if mime_data.hasText():
            name = mime_data.text()

            if event.source() != self:
                source_index = self.widget_list.layout().indexOf(event.source())
                target_index = self.widget_list.layout().indexOf(self)

                if source_index != -1 and target_index != -1:
                    if source_index < self.widget_list.layout().count():
                        source_widget = self.widget_list.layout().takeAt(source_index).widget()
                        if source_widget:
                            self.widget_list.layout().insertWidget(target_index, source_widget)

        event.accept()

    @staticmethod
    def show_context_menu(self, event, property_class):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        duplicate_action = QAction("Duplicate", context_menu)
        context_menu.addActions([delete_action, duplicate_action])

        action = context_menu.exec(QCursor.pos())

        if action == delete_action:
            self.deleteLater()
            self.status_bar.setText(f"Deleted: {self.ui.label.text()}")

        elif action == duplicate_action:
            new_item = property_class(name=self.ui.label.text(), value=self.ui.lineEdit.text(), status_bar=self.status_bar)
            new_item.setContextMenuPolicy(Qt.CustomContextMenu)
            new_item.customContextMenuRequested.connect(self.show_context_menu)
            self.widget_list.layout().addWidget(new_item)