from documentation.ui_documentation_dialog import Ui_documentation_dialog
from PySide6.QtWidgets import QDialog
class Documentation_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_documentation_dialog()
        self.ui.setupUi(self)