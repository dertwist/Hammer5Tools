from hotkey_editor.ui_dialog import Ui_Dialog
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt
from preferences import debug
class KeyDialog(QDialog):
    def __init__(self, parent=None):
        super(KeyDialog, self).__init__(parent)
        self.ui = Ui_Dialog()
        self.setup_ui_elements()
        self.value = ''


    def setup_ui_elements(self):
        self.ui.setupUi(self)
        self.ui.select_from_list.clicked.connect(self.toggle_visibility)
        self.toggle_visibility()

        self.ui.key_line.keyPressEvent = self.key_pressed_event
        self.ui.list.addItems(['NumEnter', 'Enter', 'Esc', 'Space', 'LMouse', 'RMouse', 'MMouse', 'MWheelUp', 'MWheelDn', 'LMouseDoubleClick', 'Up', 'Down', 'Left', 'Right', 'SELECTION_ADD_KEY', 'SELECTION_REMOVE_KEY', 'TOGGLE_SNAPPING_KEY'])
        self.ui.list.currentIndexChanged.connect(self.do_out)
        self.ui.ctrl.stateChanged.connect(self.do_out)
        self.ui.shift.stateChanged.connect(self.do_out)
        self.ui.alt.stateChanged.connect(self.do_out)


    def toggle_visibility(self):
        if self.ui.select_from_list.isChecked():
            self.ui.list.setHidden(False)
            self.ui.key_line.setHidden(True)
            self.ui.list.setFocus()
        else:
            self.ui.list.setHidden(True)
            self.ui.key_line.setHidden(False)
            self.ui.key_line.setFocus()
        self.do_out()

    def key_pressed_event(self, event: QKeyEvent):
        modifiers = event.modifiers()
        key = event.key()

        if key >= Qt.Key_F1 and key <= Qt.Key_F12:
            key_name = f'F{key - Qt.Key_F1 + 1}'
        else:
            key_name = event.text()

        if modifiers & Qt.ShiftModifier:
            key_name = ''
        if modifiers & Qt.ControlModifier:
            key_name = ''
        if modifiers & Qt.AltModifier:
            key_name = ''

        self.ui.key_line.setText(key_name.upper())
        self.do_out()
    def do_out(self):
        if self.ui.select_from_list.isChecked():
            key = self.ui.list.currentText()
        else:
            key = self.ui.key_line.text()
        if self.ui.ctrl.isChecked():
            ctrl = 'Ctrl+'
        else:
            ctrl = ''
        if self.ui.shift.isChecked():
            shift = 'Shift+'
        else:
            shift = ''
        if self.ui.alt.isChecked():
            alt = 'Alt+'
        else:
            alt = ''
        self.value = f'{ctrl+shift+alt+key}'
        debug(self.value)
