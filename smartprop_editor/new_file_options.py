from PySide6.QtWidgets import QDialog
from smartprop_editor.ui_new_file_options import Ui_Form
from preferences import get_config_value, set_config_value
class NewFileOptions(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setModal(True)
        self.ui.comboBox.setCurrentText(get_config_value('SmartpropEditor', 'Extension'))
        self.ui.comboBox.currentTextChanged.connect(self.changed)
    def changed(self):
        set_config_value('SmartpropEditor', 'Extension', self.ui.comboBox.currentText())