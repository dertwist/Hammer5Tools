from src.smartprop_editor.variables.ui_combobox import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from src.preferences import debug

class Var_class_combobox(QWidget):
    edited = Signal(str, str, str, str)
    def __init__(self, default, elements):
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

        self.ui.value.addItems(elements)
        self.ui.value.setCurrentText(str(self.default))
        self.on_changed()
        self.ui.value.currentTextChanged.connect(self.on_changed)



    def on_changed(self):
        self.default = self.ui.value.currentText()
        self.edited.emit(self.default, self.min, self.max, str(self.model))