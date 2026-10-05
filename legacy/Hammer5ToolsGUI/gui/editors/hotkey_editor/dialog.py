from gui.editors.hotkey_editor.ui_dialog import Ui_Dialog
from PySide6.QtWidgets import QComboBox, QDialog
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt
from gui.common import apply_title_bar_theme


SPECIAL_INPUTS = (
    "",
    "NumEnter", "Enter", "Esc", "Space", "Tab", "Backspace", "Del",
    "Home", "End", "Ins", "PgUp", "PgDn", "Break",
    "LMouse", "RMouse", "MMouse", "Mouse4", "Mouse5",
    "LMouseDoubleClick", "RMouseDoubleClick",
    "MWheelUp", "MWheelDn", "MWheelLeft", "MWheelRight",
    "Up", "Down", "Left", "Right",
    "Num0", "Num1", "Num2", "Num3", "Num4", "Num5", "Num6", "Num7",
    "Num8", "Num9", "NumAdd", "NumSub", "NumDec",
    "Ctrl", "Shift", "Alt",
    "SELECTION_ADD_KEY", "SELECTION_REMOVE_KEY", "SELECTION_ADJUST_KEY",
    "TOGGLE_SNAPPING_KEY",
)


KEY_NAMES = {
    Qt.Key_Backspace: "Backspace",
    Qt.Key_Tab: "Tab",
    Qt.Key_Return: "Enter",
    Qt.Key_Enter: "NumEnter",
    Qt.Key_Escape: "Esc",
    Qt.Key_Space: "Space",
    Qt.Key_Delete: "Del",
    Qt.Key_Home: "Home",
    Qt.Key_End: "End",
    Qt.Key_Insert: "Ins",
    Qt.Key_PageUp: "PgUp",
    Qt.Key_PageDown: "PgDn",
    Qt.Key_Up: "Up",
    Qt.Key_Down: "Down",
    Qt.Key_Left: "Left",
    Qt.Key_Right: "Right",
    Qt.Key_Pause: "Break",
}


class KeyDialog(QDialog):
    def __init__(self, parent=None):
        super(KeyDialog, self).__init__(parent)
        self.ui = Ui_Dialog()
        apply_title_bar_theme(self)
        self.value = ''
        self.setup_ui_elements()


    def setup_ui_elements(self):
        self.ui.setupUi(self)
        self.ui.select_from_list.clicked.connect(self.toggle_visibility)
        self.toggle_visibility()

        self.ui.key_line.keyPressEvent = self.key_pressed_event
        self.ui.list.setEditable(True)
        self.ui.list.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.ui.list.addItems(SPECIAL_INPUTS)
        self.ui.list.currentTextChanged.connect(self.do_out)
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

        if Qt.Key_F1 <= key <= Qt.Key_F24:
            key_name = f'F{key - Qt.Key_F1 + 1}'
        else:
            key_name = KEY_NAMES.get(key, event.text())

        if modifiers & Qt.ShiftModifier:
            self.ui.shift.setChecked(True)
        if modifiers & Qt.ControlModifier:
            self.ui.ctrl.setChecked(True)
        if modifiers & Qt.AltModifier:
            self.ui.alt.setChecked(True)

        if key in {Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt}:
            key_name = ''

        self.ui.key_line.setText(key_name.upper() if len(key_name) == 1 else key_name)
        self.do_out()

    def do_out(self):
        if self.ui.select_from_list.isChecked():
            key = self.ui.list.currentText().strip()
        else:
            key = self.ui.key_line.text().strip()

        parts = []
        for enabled, name in (
            (self.ui.ctrl.isChecked(), 'Ctrl'),
            (self.ui.shift.isChecked(), 'Shift'),
            (self.ui.alt.isChecked(), 'Alt'),
        ):
            if enabled:
                parts.append(name)
        known_parts = {part.casefold() for part in parts}
        for key_part in key.split('+'):
            key_part = key_part.strip()
            if key_part and key_part.casefold() not in known_parts:
                parts.append(key_part)
                known_parts.add(key_part.casefold())
        self.value = '+'.join(parts)
