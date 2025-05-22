from smartprop_editor.variables.ui_vector2d import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

class Var_class_vector2d(QWidget):
    edited = Signal(list, str, str, str)
    def __init__(self, default):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.model = None
        self.min = None
        self.max = None
        if default == None:
            self.default = [0, 0]
        else:
            try:
                self.default = list(default)
                self.ui.vector_x.setValue(self.default[0])
                self.ui.vector_y.setValue(self.default[1])
            except:
                pass


        # Connect signal for spin boxes
        self.ui.vector_x.valueChanged.connect(self.on_changed)
        self.ui.vector_y.valueChanged.connect(self.on_changed)


    def on_changed(self):
        self.default = [self.ui.vector_x.value(), self.ui.vector_y.value()]
        self.edited.emit(list(self.default), self.min, self.max, str(self.model))
