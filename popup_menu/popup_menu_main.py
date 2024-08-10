import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QScrollArea, QLabel, QDialog, QToolButton, QHBoxLayout
from PySide6.QtGui import QKeySequence, QShortcut, QCursor, QIcon
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QEvent, Qt, QSize
from PySide6.QtCore import Signal
from popup_menu.ui_popup_menu import Ui_PoPupMenu
class PopupMenu(QDialog):
    label_clicked = Signal(str)  # Define a signal that takes a string as an argument
    add_property_signal = Signal(str,str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout(self.ui.scrollArea)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0,0,2,0)

        for i in range(16):
            label = QLabel(f"Element {i + 1}")
            label.mousePressEvent = lambda event, text=label.text(): self.label_clicked.emit(text)


            element_layout = QHBoxLayout()
            element_layout.setContentsMargins(0,0,0,0)
            element_layout.addWidget(label)

            label.setStyleSheet("""
            QLabel {
                border-bottom: 0.5px solid black;  
                border-radius: 0px; border-color: 
                rgba(40, 40, 40, 255);
            }
            QLabel:hover {
                background-color: #414956;
            }
            """)

            tool_button = QToolButton()

            tool_button.setStyleSheet("""QToolButton {
                font: 700 10pt "Segoe UI";
                border: 2px solid black;
                border-radius: 2px;
                border-color: rgba(80, 80, 80, 255);
                height:12px;
                width:12px;
                color: #E3E3E3;
                background-color: #1C1C1C;
            }
            QToolButton:hover {
                background-color: #414956;
                color: white;
            }
            QToolButton:pressed {
                background-color: #1C1C1C;
                margin:  0px;
                margin-left: 0px;
                margin-right: 0px;
                font: 700 10pt "Sego";
            
            }
            """)

            bookmark_icon_added = QIcon("://icons/bookmark_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")
            bookmark_icon_add = QIcon("://icons/bookmark_add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")
            tool_button.setIcon(bookmark_icon_add)
            tool_button.setIconSize(QSize(24, 24))
            element_layout.addWidget(tool_button)

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