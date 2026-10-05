from gui.editors.smartprop_editor.variables.ui_bool import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from gui.editors.smartprop_editor.property import compact


class BoolVariable(QWidget):
    edited = Signal(bool, str, str, str)
    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        compact.style_variable_body(self, "bool")
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
        state = self.ui.checkBox.isChecked()
        self.edited.emit(state, None, None, None)


Var_class_bool = BoolVariable