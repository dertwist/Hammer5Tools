from src.editors.smartprop_editor.variables.ui_material_group import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class Var_class_material_group(QWidget):
    edited = Signal(str, str, str, str)
    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.min = None
        self.max = None
        if default == None:
            self.default = ''
        else:
            self.default = str(default)

        if model == None:
            self.model = ''
        else:
            self.model = str(model)
        self.ui.value.setText(str(self.default))
        self.ui.model.setText(str(self.model))
        self.ui.value.textChanged.connect(self.on_changed)
        self.ui.model.textChanged.connect(self.on_changed)

    def on_changed(self):
        self.default = self.ui.value.text()
        self.model = self.ui.model.text()
        self.edited.emit(self.default, self.min, self.max, self.model)