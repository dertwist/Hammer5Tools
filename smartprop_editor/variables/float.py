from smartprop_editor.variables.ui_float import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

class Var_class_float(QWidget):
    edited = Signal(float, float, float, str)
    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.model = None
        if default == None:
            self.default = float(0)
        else:
            self.default = float(default)
        if min == None:
            self.ui.min_checkBox.setChecked(False)
            self.ui.min_doubleSpinBox.setEnabled(False)
        else:
            self.min = float(min)
            self.ui.min_checkBox.setChecked(True)
            self.ui.min_doubleSpinBox.setValue(self.min)
        if max == None:
            self.ui.max_checkBox.setChecked(False)
            self.ui.max_doubleSpinBox.setEnabled(False)
        else:
            self.max = float(max)
            self.ui.max_checkBox.setChecked(True)
            self.ui.max_doubleSpinBox.setValue(self.max)

        self.ui.value_doubleSpinBox.setValue(self.default)

        self.ui.min_checkBox.clicked.connect(lambda: self.checkbox_setEnabled(checkbox=self.ui.min_checkBox, doubleSpinBox=self.ui.min_doubleSpinBox))
        self.ui.max_checkBox.clicked.connect(lambda: self.checkbox_setEnabled(checkbox=self.ui.max_checkBox, doubleSpinBox=self.ui.max_doubleSpinBox))

        self.ui.min_checkBox.stateChanged.connect(self.on_changed)
        self.ui.max_checkBox.stateChanged.connect(self.on_changed)

        # Connect signal for spin boxes
        self.ui.min_doubleSpinBox.valueChanged.connect(self.on_changed)
        self.ui.max_doubleSpinBox.valueChanged.connect(self.on_changed)
        self.ui.value_doubleSpinBox.valueChanged.connect(self.on_changed)
    def checkbox_setEnabled(self, checkbox=None, doubleSpinBox=None):
        if checkbox.isChecked():
            doubleSpinBox.setEnabled(True)
        else:
            doubleSpinBox.setEnabled(False)
    def on_changed(self):
        self.min = self.ui.min_doubleSpinBox.value()
        self.max = self.ui.max_doubleSpinBox.value()
        self.default = self.ui.value_doubleSpinBox.value()
        self.edited.emit(self.default, self.min, self.max, str(self.model))
