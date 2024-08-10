import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QScrollArea, QLabel, QDialog, QToolButton, QHBoxLayout
from PySide6.QtGui import QKeySequence, QShortcut, QCursor, QIcon
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QEvent, Qt, QSize
from PySide6.QtCore import Signal
from popup_menu.ui_popup_menu import Ui_PoPupMenu
class PopupMenu(QDialog):
    label_clicked = Signal(str)  # Define a signal that takes a string as an argument

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout(self.ui.scrollArea)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        for i in range(16):
            label = QLabel(f"Element {i + 1}")
            label.mousePressEvent = lambda event, text=label.text(): self.label_clicked.emit(text)

            # Create a horizontal layout for each element
            element_layout = QHBoxLayout()
            element_layout.addWidget(label)  # Add the label to the horizontal layout

            # Create and add QToolButtons to the same horizontal layout as the label
            for j in range(2):  # Add 2 QToolButtons to each element
                tool_button = QToolButton()
                tool_button.setText(f"Button {j + 1}")
                element_layout.addWidget(tool_button)  # Add the button to the horizontal layout

            scroll_layout.addLayout(element_layout)

        self.ui.scrollArea.setWidget(scroll_content)

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

        self.overlay_widget = PopupMenu(self)  # Set the parent widget as MyWindow

        # Create a shortcut to trigger overlay_widget.show() when Ctrl + F is pressed
        shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut.activated.connect(self.show_overlay)

        self.label = QLabel("Hello, World!", self)  # Define label as an attribute of MyWindow
        self.label.move(50, 50)  # Set the position of the label

        # Create a QPushButton to trigger the overlay_widget
        button = QPushButton("Show Overlay", self)
        button.clicked.connect(self.overlay_widget.show)  # Show the existing instance of OverlayDialog
        self.overlay_widget = PopupMenu(self)
        self.overlay_widget.label_clicked.connect(self.set_main_window_label)

    def set_main_window_label(self, text):
        # Set the label in the main window
        self.label.setText(text)

    def show_overlay(self):
        self.overlay_widget.show()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())