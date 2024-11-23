import sys
import webbrowser
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QScrollArea, QLabel, QToolButton, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtCore import QEvent, Qt, Signal, QSize
from src.popup_menu.ui_popup_menu import Ui_PoPupMenu
from src.widgets import ErrorInfo


class PopupMenu(QDialog):
    label_clicked = Signal(str)
    add_property_signal = Signal(str, str)

    def __init__(self, properties: list, add_once: bool = False, parent=None, help_url: str = None):
        super().__init__(parent)
        self.help_url = help_url
        self.properties = properties
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setGeometry(200, 200, 400, 400)

        self.ui.lineEdit.textChanged.connect(self.search_text_changed)

        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setContentsMargins(0, 0, 2, 0)
        self.scroll_layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.populate_properties(add_once)

        scroll_content = QWidget()
        scroll_content.setLayout(self.scroll_layout)
        self.ui.scrollArea.setWidget(scroll_content)
        self.ui.lineEdit.setFocus()

    def populate_properties(self, add_once):
        for item in self.properties:
            for key, value in item.items():
                label = QLabel(key)
                label.mousePressEvent = self.create_label_event(label, key, value, add_once)

                element_layout = QHBoxLayout()
                element_layout.setContentsMargins(0, 0, 0, 0)
                element_layout.addWidget(label)

                if self.help_url:
                    element_layout.addWidget(self.create_help_button(key))

                self.scroll_layout.insertLayout(self.scroll_layout.count() - 1, element_layout)
                label.setStyleSheet(self.get_label_stylesheet())

    def create_label_event(self, label, key, value, add_once):
        if add_once:
            return lambda event: self.remove_element(label, key, str(value))
        else:
            return lambda event: self.add_property_signal.emit(key, str(value))

    def create_help_button(self, label):
        button = QToolButton()
        button.setIcon(QIcon(":/icons/help_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        button.clicked.connect(lambda: self.open_wiki_page(label=label, url=self.help_url))
        return button

    def get_label_stylesheet(self):
        return """
            QLabel {
                font: 580 10pt "Segoe UI";
                border-bottom: 0.5px solid black;  
                border-radius: 0px; 
                border-color: rgba(40, 40, 40, 255);
                padding-top: 8px;
            }
            QLabel:hover {
                background-color: #414956;
            }
        """

    def remove_element(self, label, key, value):
        self.add_property_signal.emit(key, value)
        scroll_content = self.ui.scrollArea.widget()
        for i in range(scroll_content.layout().count()):
            element_layout_item = scroll_content.layout().itemAt(i)
            if element_layout_item:
                element_layout = element_layout_item.layout()
                if element_layout:
                    current_label = element_layout.itemAt(0).widget()
                    if current_label.text() == key:
                        item = scroll_content.layout().takeAt(i)
                        if item:
                            widget = item.widget()
                            if widget and not isinstance(widget, QSpacerItem):
                                widget.deleteLater()
                        break

    def open_wiki_page(self, label=None, url=None):
        if url is None:
            url = ''
        base_url = "https://developer.valvesoftware.com/wiki/"
        label = self.clean_spaces(label or "Workflow")
        full_url = f"{base_url + url}#{label}"

        try:
            webbrowser.open(full_url)
        except Exception as e:
            ErrorInfo(f"Failed to open the URL: {e}").exec()

    def clean_spaces(self, text: str) -> str:
        return text.replace(" ", "_")

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate:
            self.close()
            return True
        return super().event(event)

    def showEvent(self, event):
        self.move(QCursor.pos())
        super().showEvent(event)

    def search_text_changed(self):
        search_text = self.ui.lineEdit.text().lower()
        scroll_content = self.ui.scrollArea.widget()
        for i in range(scroll_content.layout().count()):
            element_layout_item = scroll_content.layout().itemAt(i)
            if element_layout_item:
                element_layout = element_layout_item.layout()
                if element_layout:
                    label = element_layout.itemAt(0).widget()
                    if search_text in label.text().lower():
                        label.show()
                        if element_layout.count() > 1:
                            element_layout.itemAt(1).widget().show()
                    else:
                        label.hide()
                        if element_layout.count() > 1:
                            element_layout.itemAt(1).widget().hide()