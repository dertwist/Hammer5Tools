import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from gui.editors.hotkey_editor.dialog import KeyDialog


app = QApplication.instance() or QApplication([])


def test_special_input_list_covers_current_source_2_keys():
    dialog = KeyDialog()

    assert dialog.ui.list.isEditable()
    for value in ("Break", "Mouse5", "MWheelLeft", "NumDec", "PgUp", "Tab"):
        assert dialog.ui.list.findText(value) >= 0


def test_keyboard_modifiers_and_custom_chords_are_composed():
    dialog = KeyDialog()
    event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_K, Qt.ControlModifier, "k")

    dialog.key_pressed_event(event)
    assert dialog.value == "Ctrl+K"

    dialog.ui.select_from_list.setChecked(True)
    dialog.toggle_visibility()
    dialog.ui.ctrl.setChecked(False)
    dialog.ui.list.setCurrentText("N+MWheelUp")

    assert dialog.value == "N+MWheelUp"

    dialog.ui.ctrl.setChecked(True)
    dialog.ui.list.setCurrentText("Ctrl+Shift+K")

    assert dialog.value == "Ctrl+Shift+K"


def test_populate_editor_fills_missing_actions_with_defaults_and_preserves_custom():
    from gui.editors.hotkey_editor.main import HotkeyEditorMainWindow
    from gui.editors.hotkey_editor.document_model import HotkeyDocument, HotkeyBinding

    win = HotkeyEditorMainWindow()
    win.editor = "hammer"
    # Document has a custom binding for JumpToSavedCamera1, but lacks JumpToSavedCamera2
    win.document = HotkeyDocument(bindings=[
        HotkeyBinding("HammerEditorSession", "JumpToSavedCamera1", "CustomKey"),
    ])
    win.populate_editor()

    custom_binding = win.document.find("HammerEditorSession", "JumpToSavedCamera1")
    assert custom_binding is not None
    assert custom_binding.input == "CustomKey"

    missing_binding = win.document.find("HammerEditorSession", "JumpToSavedCamera2")
    assert missing_binding is not None
    assert missing_binding.input == "Shift+F2"

