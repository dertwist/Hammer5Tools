from src.editors.smartprop_editor.variables.ui_int import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

class Var_class_Int(QWidget):
    edited = Signal(int, int, int, str)
    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.model = None
        if default == None:
            self.default = int(0)
        else:
            try:
                self.default = int(default)
                self.ui.value_spinBox.setValue(self.default)
            except:
                pass
        if min == None:
            self.ui.min_checkBox.setChecked(False)
            self.ui.min_spinBox.setEnabled(False)
        else:
            self.min = int(min)
            self.ui.min_checkBox.setChecked(True)
            self.ui.min_spinBox.setValue(self.min)
        if max == None:
            self.ui.max_checkBox.setChecked(False)
            self.ui.max_spinBox.setEnabled(False)
        else:
            self.max = int(max)
            self.ui.max_checkBox.setChecked(True)
            self.ui.max_spinBox.setValue(self.max)





        self.ui.min_checkBox.clicked.connect(lambda: self.checkbox_setEnabled(checkbox=self.ui.min_checkBox, spinbox=self.ui.min_spinBox))
        self.ui.max_checkBox.clicked.connect(lambda: self.checkbox_setEnabled(checkbox=self.ui.max_checkBox, spinbox=self.ui.max_spinBox))

        self.ui.min_checkBox.stateChanged.connect(self.on_changed)
        self.ui.max_checkBox.stateChanged.connect(self.on_changed)

        # Connect signal for spin boxes
        self.ui.min_spinBox.valueChanged.connect(self.on_changed)
        self.ui.max_spinBox.valueChanged.connect(self.on_changed)
        self.ui.value_spinBox.valueChanged.connect(self.on_changed)
        self.on_changed()
    def checkbox_setEnabled(self, checkbox=None, spinbox=None):
        if checkbox.isChecked():
            spinbox.setEnabled(True)
        else:
            spinbox.setEnabled(False)
    def on_changed(self):
        self.min = self.ui.min_spinBox.value()
        self.max = self.ui.max_spinBox.value()
        self.default = self.ui.value_spinBox.value()
        self.edited.emit(int(self.default), self.min, self.max, str(self.model))
