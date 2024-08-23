from soudevent_editor.ui_create_new_soundevent_dialog import Ui_Dialog
from PySide6.QtWidgets import QDialog
class CreateNewSoundEventOptions_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setModal(True)