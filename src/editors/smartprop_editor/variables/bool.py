from src.editors.smartprop_editor.variables.ui_bool import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class Var_class_bool(QWidget):
    edited = Signal(bool, str, str, str)
    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.min = None
        self.max = None
        self.model = None
        if default == None:
            self.default = False
        else:
            self.default = bool(default)
        self.ui.checkBox.setChecked(self.default)
        self.ui.checkBox.stateChanged.connect(self.on_changed)
        self.on_changed()

    def on_changed(self):
        self.default = self.ui.checkBox.isChecked()

        if self.default == None:
            self.default = False
        self.ui.checkBox.setText(str(self.default))
        self.edited.emit(self.default, self.min, self.max, self.model)