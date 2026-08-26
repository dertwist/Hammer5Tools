"""
NoteEditorWidget — Editable yellow note widget for SmartProp elements and modifiers.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.editors.smartprop_editor.note_utils import get_note, set_note
from gui.editors.smartprop_editor.props.model import ComponentRef
from gui.styles.property_icons import IconCache


class NoteEditorWidget(QWidget):
    """Editable yellow note editor for the currently selected SmartProp component."""

    noteEdited = Signal(object, str)  # (ComponentRef, note_text)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_ref: ComponentRef | None = None
        self._is_updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setPlaceholderText("Enter note here...")
        self.text_edit.setProperty("h5Component", "smartpropNoteEdit")
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit)

        # Debounce timer for saving note edits
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(200)
        self._debounce_timer.timeout.connect(self._flush_edit)

    def set_component(self, ref: ComponentRef | None):
        """Bind the note editor to a component ref and load its note content."""
        # Flush any pending edits from previous component before switching
        if self._debounce_timer.isActive():
            self._flush_edit()

        self._current_ref = ref
        self._is_updating = True
        try:
            if ref is None or ref.item is None:
                self.text_edit.setPlainText("")
                self.setEnabled(False)
                return

            self.setEnabled(True)
            data = ref.item.data(0, Qt.UserRole)
            target = ref.target(data) if isinstance(data, dict) else None
            note_text = get_note(target) if isinstance(target, dict) else ""
            self.text_edit.setPlainText(note_text)
        finally:
            self._is_updating = False

    def focus_editor(self):
        """Focus the note text editor and place cursor at the end."""
        self.text_edit.setFocus()
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

    def get_text(self) -> str:
        return self.text_edit.toPlainText()

    def _on_text_changed(self):
        if self._is_updating:
            return
        self._debounce_timer.start()

    def _flush_edit(self):
        self._debounce_timer.stop()
        if self._current_ref is None:
            return
        text = self.text_edit.toPlainText()
        self.noteEdited.emit(self._current_ref, text)
