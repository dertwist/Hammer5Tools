from PySide6.QtWidgets import QMenu, QApplication
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

    # noinspection PyTypeChecker
    @staticmethod
    def show_context_menu(self, event, property_class):
        context_menu = QMenu()
        delete_action = QAction("Delete", context_menu)
        copy_action = QAction("Copy", context_menu)  # Change 'Duplicate' to 'Copy'
        context_menu.addActions([delete_action, copy_action])  # Replace 'duplicate_action' with 'copy_action'

        action = context_menu.exec(QCursor.pos())

        if action == delete_action:
            self.deleteLater()
            self.status_bar.setText(f"Deleted: {self.ui.label.text()}")

        elif action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setText(f"hammer5tools:soundeventeditor;;{self.name};;{self.value}")