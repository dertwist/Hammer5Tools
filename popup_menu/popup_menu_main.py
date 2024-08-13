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

    def __init__(self, properties, add_once=False, parent=None):
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
        self.scroll_layout = scroll_layout


        for item in self.properties:
            for key, value in item.items():
                label = QLabel(key)
                if add_once:
                    label.mousePressEvent = lambda event, key=key, value=value: self.remove_element(label, key, value)
                else:
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

    def remove_element(self, label, key, value):
        self.add_property_signal.emit(key, value)
        scroll_content = self.ui.scrollArea.widget()
        for i in range(scroll_content.layout().count()):
            element_layout_item = scroll_content.layout().itemAt(i)

            if element_layout_item is not None:
                element_layout = element_layout_item.layout()

                if element_layout is not None:
                    current_label = element_layout.itemAt(0).widget()

                    if current_label.text() == key:
                        item = scroll_content.layout().takeAt(i)
                        if item is not None:
                            widget = item.widget()
                            if widget is not None and not isinstance(widget, QSpacerItem):
                                widget.deleteLater()
                                print(key)
                        break
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
        search_text = self.ui.lineEdit.text().lower()

        scroll_content = self.ui.scrollArea.widget()
        for i in range(scroll_content.layout().count()):
            element_layout_item = scroll_content.layout().itemAt(i)

            if element_layout_item is not None:
                element_layout = element_layout_item.layout()

                if element_layout is not None:
                    label = element_layout.itemAt(0).widget()

                    if search_text in label.text().lower():
                        element_layout.itemAt(0).widget().show()
                    else:
                        element_layout.itemAt(0).widget().hide()