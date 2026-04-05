from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData, QTimer, QPoint
from PySide6.QtGui import QCursor, QDrag, QAction, QPixmap

class PropertyMethods:
    @staticmethod
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_position = event.pos()

    @staticmethod
    def startDragEvent():
        # Perform the drag event registration here
        pass

    @staticmethod
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        start = getattr(self, '_drag_start_position', None)
        if start is None:
            return
        if (event.pos() - start).manhattanLength() < 4:
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.name)

        # Include group_type in mime data if available
        group_type = getattr(self, '_group_type', None)
        if group_type:
            mime_data.setData('application/x-smartprop-group-type', group_type.encode('utf-8'))

        drag.setMimeData(mime_data)

        # Capture drag ghost from the entire frame, not just the header
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        drag.exec()

    @staticmethod
    def dragEnterEvent(self, event):
        event.accept()

    @staticmethod
    def dragMoveEvent(self, event):
        widget_list = getattr(self, 'widget_list', None)
        if widget_list is not None and hasattr(widget_list, '_show_drop_indicator'):
            # Compute target index based on cursor Y position within the layout
            layout = widget_list if hasattr(widget_list, 'count') else getattr(widget_list, 'layout', lambda: None)()
            if layout is not None and hasattr(layout, 'count'):
                pos = self.mapToGlobal(event.position().toPoint() if hasattr(event.position(), 'toPoint') else event.pos())
                best_index = layout.count()
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    w = item.widget() if item else None
                    if w is not None and w.isVisible():
                        widget_center = w.mapToGlobal(QPoint(0, w.height() // 2))
                        if pos.y() < widget_center.y():
                            best_index = i
                            break
                widget_list._show_drop_indicator(best_index)
        event.accept()

    @staticmethod
    def dragLeaveEvent(self, event):
        widget_list = getattr(self, 'widget_list', None)
        if widget_list is not None and hasattr(widget_list, '_hide_drop_indicator'):
            widget_list._hide_drop_indicator()

    @staticmethod
    def dropEvent(self, event):
        # Hide drop indicator
        widget_list = getattr(self, 'widget_list', None)
        if widget_list is not None and hasattr(widget_list, '_hide_drop_indicator'):
            widget_list._hide_drop_indicator()

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
                            
                            # Signal an edit action so undo stack correctly registers the structural rearrangement
                            if hasattr(self, "edited"):
                                self.edited.emit()

        event.accept()
