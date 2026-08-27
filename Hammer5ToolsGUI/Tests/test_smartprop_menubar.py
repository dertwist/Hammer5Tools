"""
Unit tests for the SmartProp Editor menubar refactor:
- SmartPropDocument owns and configures its own QMenuBar with File, Edit, Element, and View menus.
- SmartPropEditorMainWindow has fallback global shortcuts (Ctrl+N, Ctrl+O) and no top-level document menubar.
"""

import os
import sys
import pytest
from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtGui import QKeySequence

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
gui_root = os.path.join(repo_root, "Hammer5ToolsGUI")
if gui_root not in sys.path:
    sys.path.insert(0, gui_root)

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.smartprop_editor.document import SmartPropDocument
from gui.editors.smartprop_editor import main as smartprop_main
from gui.editors.smartprop_editor.main import SmartPropEditorMainWindow
from gui.settings.main import settings as _smartprop_settings

# SmartPropDocument persists its dock layout to the real, on-disk settings.ini
# (SmartPropEditorMainWindow/*_windowState_v5) and restores it via a deferred
# QTimer.singleShot(0, ...) in __init__. If a developer has ever run the actual
# app, that restore silently overwrites the freshly-built default layout as
# soon as the event loop turns over (e.g. via QApplication.processEvents()),
# which makes layout assertions depend on whatever happens to be saved on the
# machine running the tests. Clear those keys around every test in this file
# and restore whatever was there afterward so real user preferences aren't lost.
_SMARTPROP_WINDOW_STATE_KEYS = (
    "SmartPropEditorMainWindow/default_windowState_v5",
    "SmartPropEditorMainWindow/windowState_v5",
)


@pytest.fixture(autouse=True)
def _isolate_smartprop_window_state():
    saved = {key: _smartprop_settings.value(key) for key in _SMARTPROP_WINDOW_STATE_KEYS}
    for key in _SMARTPROP_WINDOW_STATE_KEYS:
        _smartprop_settings.remove(key)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                _smartprop_settings.remove(key)
            else:
                _smartprop_settings.setValue(key, value)


def test_smartprop_document_menubar_structure():
    """Verify SmartPropDocument initializes with complete document menubar."""
    doc = SmartPropDocument()

    menubar = doc.menuBar()
    assert menubar is not None, "SmartPropDocument should have a QMenuBar"
    assert menubar.property("h5Component") == "smartpropMenuBar"

    # Verify standard menus exist on document
    assert hasattr(doc, "file_menu")
    assert hasattr(doc, "edit_menu")
    assert hasattr(doc, "element_menu")
    assert hasattr(doc, "view_menu")
    assert hasattr(doc, "docks_menu")

    assert doc.file_menu.title() == "&File"
    assert doc.edit_menu.title() == "&Edit"
    assert doc.element_menu.title() == "&Element"
    assert doc.view_menu.title() == "&View"


def test_smartprop_document_file_actions():
    """Verify File menu actions and shortcuts on SmartPropDocument."""
    doc = SmartPropDocument()

    assert hasattr(doc, "action_new")
    assert hasattr(doc, "action_open")
    assert hasattr(doc, "action_save")
    assert hasattr(doc, "action_save_as")
    assert hasattr(doc, "action_save_all")
    assert hasattr(doc, "action_close")
    assert not hasattr(doc, "action_open_selected")
    assert not hasattr(doc, "action_exit")

    assert doc.action_new.shortcut().toString() == QKeySequence(QKeySequence.New).toString()
    assert doc.action_open.shortcut().toString() == QKeySequence(QKeySequence.Open).toString()
    assert doc.action_save.shortcut().toString() == QKeySequence(QKeySequence.Save).toString()
    assert doc.action_save_as.shortcut().toString() == QKeySequence(QKeySequence.SaveAs).toString()
    assert doc.action_close.shortcut().toString() == "Ctrl+W"


def test_smartprop_document_edit_actions():
    """Verify Edit menu actions and shortcuts on SmartPropDocument."""
    doc = SmartPropDocument()

    assert hasattr(doc, "action_undo")
    assert hasattr(doc, "action_redo")
    assert hasattr(doc, "action_cut")
    assert hasattr(doc, "action_copy")
    assert hasattr(doc, "action_paste")
    assert hasattr(doc, "action_paste_replace")
    assert hasattr(doc, "action_duplicate")
    assert hasattr(doc, "action_delete")
    assert hasattr(doc, "action_group")

    assert doc.action_undo.shortcut().toString() == QKeySequence(QKeySequence.Undo).toString()
    assert doc.action_cut.shortcut().toString() == QKeySequence(QKeySequence.Cut).toString()
    assert doc.action_copy.shortcut().toString() == QKeySequence(QKeySequence.Copy).toString()
    assert doc.action_paste.shortcut().toString() == QKeySequence(QKeySequence.Paste).toString()
    assert doc.action_paste_replace.shortcut().toString() == "Ctrl+Shift+V"
    assert doc.action_duplicate.shortcut().toString() == "Ctrl+D"
    assert doc.action_delete.shortcut().toString() in ("Del", "Delete")
    assert doc.action_group.shortcut().toString() == "Ctrl+G"


def test_smartprop_document_element_and_view_actions():
    """Verify Element and View menu actions on SmartPropDocument."""
    doc = SmartPropDocument()

    assert hasattr(doc, "action_add_element")
    assert hasattr(doc, "action_add_preset")
    assert hasattr(doc, "action_add_operator")
    assert hasattr(doc, "action_add_criteria")
    assert hasattr(doc, "action_add_choice")
    assert hasattr(doc, "action_add_variable")
    assert hasattr(doc, "action_bulk_import")
    assert hasattr(doc, "action_load_vmap")
    assert hasattr(doc, "action_isolate")
    assert hasattr(doc, "action_save_layout")
    assert hasattr(doc, "action_reset_layout")

    assert doc.action_add_element.shortcut().toString() == "Ctrl+F"
    assert doc.action_isolate.shortcut().toString() == "Ctrl+H"


def test_smartprop_document_docks_menu():
    """Verify docks menu updates with document dock widgets."""
    doc = SmartPropDocument()
    doc._update_docks_menu()

    dock_actions = doc.docks_menu.actions()
    action_texts = [a.text() for a in dock_actions if not a.isSeparator()]
    assert len(action_texts) > 0


def test_smartprop_main_window_fallback_shortcuts(monkeypatch, tmp_path):
    """Verify SmartPropEditorMainWindow has fallback global shortcuts and no document menubar."""
    # The module captures get_cs2_path() at import time, so on a machine with no
    # CS2 path configured (every CI runner) it is None and the explorer's
    # os.path.join raises. Give it a directory instead of requiring an install.
    monkeypatch.setattr(smartprop_main, "cs2_path", str(tmp_path), raising=False)

    window = SmartPropEditorMainWindow()

    assert hasattr(window, "action_new_global")
    assert hasattr(window, "action_open_global")

    assert window.action_new_global.shortcut().toString() == QKeySequence(QKeySequence.New).toString()
    assert window.action_open_global.shortcut().toString() == QKeySequence(QKeySequence.Open).toString()

    # The main window should not have document-specific action attributes like action_undo, action_paste
    assert not hasattr(window, "action_undo")
    assert not hasattr(window, "action_paste")
    assert not hasattr(window, "action_duplicate")


def test_smartprop_document_layout_single_splitter():
    """Verify SmartPropDocument uses nested single-splitter layout without a dummy central widget."""
    doc = SmartPropDocument()
    assert doc.isDockNestingEnabled(), "Dock nesting must be enabled for single-splitter layout"
    assert doc.centralWidget() is None, "Central widget should be None so no duplicate separator is created"

    doc.resize(1600, 900)
    doc.show()
    QApplication.processEvents()

    # Verify Property Editor and Viewport are adjacent with a single 4px separator
    p_rect = doc._property_dock.geometry()
    v_rect = doc._viewport_dock.geometry()
    gap = v_rect.left() - (p_rect.left() + p_rect.width())
    # The separator width is style-dependent (4px on Windows, 6px on Fusion), so
    # compare against the metric: one extent means one separator, not two.
    separator = doc.style().pixelMetric(QStyle.PM_DockWidgetSeparatorExtent)
    assert gap == separator, (
        f"Expected a single {separator}px separator between Property and Viewport, got {gap}px"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
