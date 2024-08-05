from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSlider, QLabel, QLineEdit, QHBoxLayout, QMenu, QFrame, QVBoxLayout
from PySide6.QtCore import Qt, QMimeData, QDataStream, QByteArray, QPoint, QPropertyAnimation, QParallelAnimationGroup
from PySide6.QtGui import QDrag, QClipboard, QAction, QPainter, QPen, QPixmap

class DraggableHandle(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedWidth(20)  # Increased width for better usability
        self.setStyleSheet("background-color: gray;")
        self.setCursor(Qt.OpenHandCursor)
        self.is_dragging_widget = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging_widget = True
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.parentWidget().objectName())
            drag.setMimeData(mime_data)

            # Create a pixmap of the widget to show under the cursor
            pixmap = self.parentWidget().grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())  # Updated to use position() and convert to QPoint

            # Fade out animation
            self.fade_out_animation(self.parentWidget())

            drag.exec(Qt.MoveAction)
            self.is_dragging_widget = False

    def fade_out_animation(self, widget):
        self.animation = QPropertyAnimation(widget, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.5)
        self.animation.start()

    def fade_in_animation(self, widget):
        self.animation = QPropertyAnimation(widget, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0.5)
        self.animation.setEndValue(1.0)
        self.animation.start()

class DraggableWidget(QWidget):
    def __init__(self, widget):
        super().__init__()
        self.setObjectName(widget.__class__.__name__)
        self.setStyleSheet("border: 2px solid black; padding: 10px;")  # Added padding
        self.setAcceptDrops(True)
        self.outline_position = None
        layout = QHBoxLayout(self)
        self.handle = DraggableHandle(self)
        layout.addWidget(self.handle)
        layout.addWidget(widget)
        layout.setContentsMargins(5, 5, 5, 5)  # Increased margins
        layout.setSpacing(10)  # Increased spacing

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if self.handle.is_dragging_widget:
            pos = event.position().toPoint()  # Updated to use position() and convert to QPoint
            if pos.y() < self.height() // 2:
                self.outline_position = 'top'
            else:
                self.outline_position = 'bottom'
            self.update()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            parent_layout = self.parentWidget().layout()
            index = parent_layout.indexOf(self)
            widget_name = event.mimeData().text()
            for i in range(parent_layout.count()):
                widget = parent_layout.itemAt(i).widget()
                if widget is not None and widget.objectName() == widget_name:
                    parent_layout.takeAt(i)
                    if self.outline_position == 'top':
                        parent_layout.insertWidget(index, widget)
                    else:
                        parent_layout.insertWidget(index + 1, widget)
                    self.animate_widget(widget)
                    self.handle.fade_in_animation(widget)
                    break
            self.outline_position = None
            self.update()
            event.acceptProposedAction()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.outline_position:
            painter = QPainter(self)
            pen = QPen(Qt.DashLine)
            pen.setColor(Qt.red)
            painter.setPen(pen)
            if self.outline_position == 'top':
                painter.drawLine(0, 0, self.width(), 0)
            elif self.outline_position == 'bottom':
                painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    def animate_widget(self, widget):
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(500)
        animation.setStartValue(widget.geometry())
        animation.setEndValue(widget.geometry())
        animation.start()

class DraggableLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setStyleSheet("font-size: 18px; padding: 5px;")  # Increased font size and padding

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.text())
            drag.setMimeData(mime_data)

            # Create a pixmap of the widget to show under the cursor
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())  # Updated to use position() and convert to QPoint

            drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.setText(event.mimeData().text())
        event.acceptProposedAction()

    def show_context_menu(self, pos):
        context_menu = QMenu(self)
        duplicate_action = QAction("Duplicate", self)
        remove_action = QAction("Remove", self)
        copy_action = QAction("Copy", self)

        duplicate_action.triggered.connect(self.duplicate)
        remove_action.triggered.connect(self.remove)
        copy_action.triggered.connect(self.copy)

        context_menu.addAction(duplicate_action)
        context_menu.addAction(remove_action)
        context_menu.addAction(copy_action)
        context_menu.exec(self.mapToGlobal(pos))

    def duplicate(self):
        new_label = DraggableLabel(self.text())
        self.parentWidget().layout().addWidget(DraggableWidget(new_label))

    def remove(self):
        self.parentWidget().deleteLater()

    def copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text())

class DraggableSlider(QSlider):
    def __init__(self, orientation):
        super().__init__(orientation)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setStyleSheet("padding: 10px;")  # Added padding

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(self.value()))
            drag.setMimeData(mime_data)

            # Create a pixmap of the widget to show under the cursor
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())  # Updated to use position() and convert to QPoint

            drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            text = event.mimeData().text()
            try:
                value = int(text)
                self.setValue(value)
            except ValueError:
                print(f"Cannot convert '{text}' to an integer.")
        event.acceptProposedAction()

    def show_context_menu(self, pos):
        context_menu = QMenu(self)
        duplicate_action = QAction("Duplicate", self)
        remove_action = QAction("Remove", self)
        copy_action = QAction("Copy", self)

        duplicate_action.triggered.connect(self.duplicate)
        remove_action.triggered.connect(self.remove)
        copy_action.triggered.connect(self.copy)

        context_menu.addAction(duplicate_action)
        context_menu.addAction(remove_action)
        context_menu.addAction(copy_action)
        context_menu.exec(self.mapToGlobal(pos))

    def duplicate(self):
        new_slider = DraggableSlider(self.orientation())
        new_slider.setValue(self.value())
        self.parentWidget().layout().addWidget(DraggableWidget(new_slider))

    def remove(self):
        self.parentWidget().deleteLater()

    def copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(str(self.value()))

class DraggableLineEdit(QLineEdit):
    def __init__(self, placeholder_text):
        super().__init__()
        self.setPlaceholderText(placeholder_text)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setStyleSheet("font-size: 18px; padding: 5px;")  # Increased font size and padding

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.text())
            drag.setMimeData(mime_data)

            # Create a pixmap of the widget to show under the cursor
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())  # Updated to use position() and convert to QPoint

            drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.setText(event.mimeData().text())
        event.acceptProposedAction()

    def show_context_menu(self, pos):
        context_menu = QMenu(self)
        duplicate_action = QAction("Duplicate", self)
        remove_action = QAction("Remove", self)
        copy_action = QAction("Copy", self)

        duplicate_action.triggered.connect(self.duplicate)
        remove_action.triggered.connect(self.remove)
        copy_action.triggered.connect(self.copy)

        context_menu.addAction(duplicate_action)
        context_menu.addAction(remove_action)
        context_menu.addAction(copy_action)
        context_menu.exec(self.mapToGlobal(pos))

    def duplicate(self):
        new_line_edit = DraggableLineEdit(self.placeholderText())
        new_line_edit.setText(self.text())
        self.parentWidget().layout().addWidget(DraggableWidget(new_line_edit))

    def remove(self):
        self.parentWidget().deleteLater()

    def copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text())

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSlider, QLabel, QHBoxLayout
from PySide6.QtCore import Qt

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the main layout
        main_layout = QVBoxLayout()

        # Volume controller
        volume_label = DraggableLabel("Volume Controller")
        volume_slider = DraggableSlider(Qt.Horizontal)
        volume_slider.setMinimum(0)
        volume_slider.setMaximum(100)
        main_layout.addWidget(DraggableWidget(volume_label))
        main_layout.addWidget(DraggableWidget(volume_slider))

        # Pitch controller
        pitch_label = DraggableLabel("Pitch Controller")
        pitch_slider = DraggableSlider(Qt.Horizontal)
        pitch_slider.setMinimum(0)
        pitch_slider.setMaximum(100)
        main_layout.addWidget(DraggableWidget(pitch_label))
        main_layout.addWidget(DraggableWidget(pitch_slider))

        # Set the main layout for the window
        self.setLayout(main_layout)
        self.setWindowTitle("Widget List Example")

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()