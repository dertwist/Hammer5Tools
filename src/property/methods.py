from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData, QTimer
from PySide6.QtGui import QCursor, QDrag,QAction

class PropertyMethods:
    @staticmethod
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag_start_position = None
            drag_timer = QTimer()
            drag_start_position = event.pos()
            drag_timer.setSingleShot(True)
            drag_timer.timeout.connect(lambda: self.startDragEvent())
            drag_timer.start(1000)

    @staticmethod
    def startDragEvent():
        # Perform the drag event registration here
        pass

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

            if event.source() != self:
                source_index = self.widget_list.layout().indexOf(event.source())
                target_index = self.widget_list.layout().indexOf(self)

                if source_index != -1 and target_index != -1:
                    if source_index < self.widget_list.layout().count():
                        source_widget = self.widget_list.layout().takeAt(source_index).widget()
                        if source_widget:
                            self.widget_list.layout().insertWidget(target_index, source_widget)

        event.accept()
