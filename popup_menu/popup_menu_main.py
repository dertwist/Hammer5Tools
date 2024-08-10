import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QScrollArea, QLabel, QDialog
from PySide6.QtGui import QKeySequence, QShortcut, QCursor
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QEvent, Qt
from PySide6.QtCore import Signal
class OverlayDialog(QDialog):
    label_clicked = Signal(str)  # Define a signal that takes a string as an argument

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)  # Disable window title and buttons
        self.setGeometry(200, 200, 400, 300)
        self.initial = 0

        layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        for i in range(16):
            label = QLabel(f"Element {i + 1}")
            label.mousePressEvent = lambda event, text=label.text(): self.label_clicked.emit(text)
            scroll_layout.addWidget(label)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate:
            self.close()
            return True  # Return True after handling the event

        return super().event(event)  # Return the result of the base class event method if the condition is not met

    def showEvent(self, event):
        cursor_pos = QCursor.pos()
        self.move(cursor_pos)
        super().showEvent(event)
class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Simple Window with Popup Menu")
        self.setGeometry(100, 100, 400, 200)

        self.overlay_widget = OverlayDialog(self)  # Set the parent widget as MyWindow

        # Create a shortcut to trigger overlay_widget.show() when Ctrl + F is pressed
        shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut.activated.connect(self.show_overlay)

        self.label = QLabel("Hello, World!", self)  # Define label as an attribute of MyWindow
        self.label.move(50, 50)  # Set the position of the label

        # Create a QPushButton to trigger the overlay_widget
        button = QPushButton("Show Overlay", self)
        button.clicked.connect(self.overlay_widget.show)  # Show the existing instance of OverlayDialog
        self.overlay_widget = OverlayDialog(self)
        self.overlay_widget.label_clicked.connect(self.set_main_window_label)

    def set_main_window_label(self, text):
        # Set the label in the main window
        self.label.setText(text)

    def show_overlay(self):
        self.overlay_widget.show()  # Show the existing instance of OverlayDialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())