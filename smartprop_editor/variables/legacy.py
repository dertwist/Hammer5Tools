from smartprop_editor.variables.ui_legacy import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class Var_class_legacy(QWidget):
    edited = Signal(str, str, str, str)
    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.min = None
        self.max = None
        self.model = None
        if default == None:
            self.default = ''
        else:
            self.default = str(default)
        self.ui.value.setText(str(self.default))
        self.ui.value.textChanged.connect(self.on_changed)


    def on_changed(self):
        self.default = self.ui.value.text()
        self.edited.emit(self.default, self.min, self.max, str(self.model))