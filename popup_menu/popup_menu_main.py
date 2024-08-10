import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QScrollArea, QLabel, QDialog, QToolButton, QHBoxLayout
from PySide6.QtGui import QKeySequence, QShortcut, QCursor, QIcon
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QEvent, Qt, QSize
from PySide6.QtCore import Signal
from popup_menu.ui_popup_menu import Ui_PoPupMenu
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
class PopupMenu(QDialog):
    label_clicked = Signal(str)
    add_property_signal = Signal(str, str)

    def __init__(self, properties, parent=None):
        super().__init__(parent)
        self.properties = properties
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setGeometry(200, 200, 400, 300)


        self.ui.lineEdit.textChanged.connect(self.search_text_changed)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 2, 0)
        scroll_layout.addSpacerItem( QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))


        for item in self.properties:
            for key, value in item.items():
                label = QLabel(key)
                label.mousePressEvent = lambda event, key=key, value=value: self.add_property_signal.emit(key, value)

                element_layout = QHBoxLayout()
                element_layout.setContentsMargins(0, 0, 0, 0)
                element_layout.addWidget(label)
                scroll_layout.insertLayout(scroll_layout.count() - 1, element_layout)
                label.setStyleSheet("""
                QLabel {
                     font: 580 10pt "Segoe UI";
                    border-bottom: 0.5px solid black;  
                    border-radius: 0px; border-color: 
                    rgba(40, 40, 40, 255);
                    padding-top:8px;
                }
                QLabel:hover {
                    background-color: #414956;
                }
                """)

                scroll_layout.addLayout(element_layout)

        self.ui.scrollArea.setWidget(scroll_content)
        self.ui.lineEdit.setFocus()

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate:
            self.close()
            return True
        return super().event(event)

    def showEvent(self, event):
        cursor_pos = QCursor.pos()
        self.move(cursor_pos)
        super().showEvent(event)

    def search_text_changed(self):
        search_text = self.ui.lineEdit.text().lower()  # Get the text from the QLineEdit and convert to lowercase for case-insensitive search

        scroll_content = self.ui.scrollArea.widget()  # Get the scroll area widget contents
        for i in range(scroll_content.layout().count()):
            element_layout_item = scroll_content.layout().itemAt(i)

            if element_layout_item is not None:
                element_layout = element_layout_item.layout()  # Get the layout of each element

                if element_layout is not None:
                    label = element_layout.itemAt(0).widget()  # Get the label widget from the layout
                    # tool_button = element_layout.itemAt(1).widget()  # Get the tool button widget from the layout

                    if search_text in label.text().lower():  # Check if the search text is present in the label text
                        element_layout.itemAt(0).widget().show()  # Show the label if it matches the search text
                        # tool_button.show()  # Show the tool button if it matches the search text
                    else:
                        element_layout.itemAt(0).widget().hide()  # Hide the label if it doesn't match the search text
                        # tool_button.hide()  # Hide the tool button if it doesn't match the search text
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