import ast

from src.smartprop_editor.property.ui_comment import Ui_Widget
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class PropertyComment(QWidget):
    edited = Signal()

    def __init__(self, value_class, value):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.value_class = value_class
        self.value = value

        self.ui.text_field.setPlainText(value)
        self.ui.text_field.textChanged.connect(self.on_changed)


        self.change_value()

    def on_changed(self):
        self.change_value()
        self.edited.emit()

    def change_value(self):
        value = self.ui.text_field.toPlainText()
        self.value = {self.value_class: str(value)}
