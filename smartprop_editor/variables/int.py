from smartprop_editor.variables.ui_int import Ui_Widget

from PySide6.QtWidgets import QWidget

class Var_class_Int(QWidget):
    def __init__(self, default, min, max ):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.min_checkBox.clicked.connect(lambda: self.checkbox_setEnabled(checkbox=self.ui.min_checkBox, spinbox=self.ui.min_spinBox))
        self.ui.max_checkBox.clicked.connect(lambda: self.checkbox_setEnabled(checkbox=self.ui.max_checkBox, spinbox=self.ui.max_spinBox))
        print(default)
        if default == None:
            self.default = 0
        else:
            self.default = float(default)
        if min == None:
            self.ui.min_checkBox.setChecked(False)
            self.ui.min_spinBox.setEnabled(False)
        else:
            self.min = float(min)
            self.ui.min_checkBox.setChecked(True)
            self.ui.min_spinBox.setValue(self.min)
        if max == None:
            self.ui.max_checkBox.setChecked(False)
            self.ui.max_spinBox.setEnabled(False)
        else:
            self.max = float(max)
            self.ui.max_checkBox.setChecked(True)
            self.ui.max_spinBox.setValue(self.max)

        self.ui.value_spinBox.setValue(self.default)
    def checkbox_setEnabled(self, checkbox=None, spinbox=None):
        if checkbox.isChecked():
            spinbox.setEnabled(True)
        else:
            spinbox.setEnabled(False)