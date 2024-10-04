from hotkey_editor.ui_dialog import Ui_Dialog
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt
class KeyDialog(QDialog):
    def __init__(self, parent=None):
        super(KeyDialog, self).__init__(parent)
        self.ui = Ui_Dialog()
        self.setup_ui_elements()

    def setup_ui_elements(self):
        self.ui.setupUi(self)
        self.ui.select_from_list.clicked.connect(self.toggle_visibility)
        self.toggle_visibility()

        self.ui.key_line.keyPressEvent = self.key_pressed_event
        self.ui.list.addItems(['NumEnter', 'Enter', 'Esc', 'Space', 'LMouse', 'RMouse', 'MMouse', 'MWheelUp', 'MWheelDn', 'LMouseDoubleClick', 'Up', 'Down', 'Left', 'Right', 'SELECTION_ADD_KEY', 'SELECTION_REMOVE_KEY', 'TOGGLE_SNAPPING_KEY'])


    def toggle_visibility(self):
        if self.ui.select_from_list.isChecked():
            self.ui.list.setHidden(False)
            self.ui.key_line.setHidden(True)
            self.ui.list.setFocus()
        else:
            self.ui.list.setHidden(True)
            self.ui.key_line.setHidden(False)
            self.ui.key_line.setFocus()

    def key_pressed_event(self, event: QKeyEvent):
        modifiers = event.modifiers()
        key_name = event.text()

        if modifiers & Qt.ShiftModifier:
            key_name = ''
        if modifiers & Qt.ControlModifier:
            key_name = ''
        if modifiers & Qt.AltModifier:
            key_name = ''

        self.ui.key_line.setText(key_name.upper())
