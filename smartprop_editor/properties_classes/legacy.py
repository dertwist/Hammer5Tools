import ast

from smartprop_editor.properties_classes.ui_legacy import Ui_Widget
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class PropertyLegacy(QWidget):
    edited = Signal()
    def __init__(self, value_class, value):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.value_class = value_class
        self.value = value

        self.ui.value.setText(str(self.value))
        self.ui.value_label.setText(str(self.value_class))
        self.ui.value.textChanged.connect(self.on_changed)


    def on_changed(self):
        self.value = {self.value_class: ast.literal_eval(self.ui.value.text())}
        self.edited.emit()