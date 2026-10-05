"""The compact property row: rail, selection, hotkeys and the modified marker.

The row lost its header bar, its collapse box and its copy/delete buttons, so
everything those did now has to work through selection plus Ctrl+C / Delete —
these tests hold that contract, along with the one marker that replaced the
header: the rail, neutral until the value differs from the saved file.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QLabel, QTreeWidget, QTreeWidgetItem

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.soundevent_editor.properties_window import (
    SoundEventEditorPropertiesWindow,
    registry_defaults,
)
from gui.editors.soundevent_editor.property.frame import SoundEventEditorPropertyFrame

EVENT = {
    "vsnd_files": ["sounds/a.vsnd"],
    "volume": 0.8,
    "pitch": 1.0,
    "type": "csgo_mega",
    "some_unknown_future_key": "keep me",
}


def build(data=None, tree=None):
    data = dict(data or EVENT)
    window = SoundEventEditorPropertiesWindow(value=dict(data), tree=tree)
    window.populate_properties(dict(data))
    return window


def press(widget, key, modifiers=Qt.NoModifier):
    """Deliver a key straight to the row's handler, and hand back the event.

    Not QApplication.sendEvent: another editor's application-wide shortcut can
    claim the key first, which would make these depend on whatever else the
    test session has built.
    """
    event = QKeyEvent(QKeyEvent.KeyPress, key, modifiers)
    widget.keyPressEvent(event)
    return event


def test_row_has_no_header_collapse_or_buttons():
    window = build()
    frame = window._frames_by_key["volume"]
    assert not hasattr(frame, "ui")            # the whole generated header form
    assert not hasattr(frame, "show_child_action")
    assert frame.rail is not None and frame.info_button is not None


def test_the_rail_is_the_only_state_marker():
    """One line per row: neutral by default, the modified colour when changed.
    Nothing else on the row may carry a state."""
    window = build()
    for frame in (window._frames_by_key["volume"], window._frames_by_key["type"]):
        assert frame.rail.property("h5State") in (None, "")
        assert frame.property("h5State") is None


def test_info_button_only_where_there_is_something_to_tell():
    window = build()
    documented = window._frames_by_key["volume"]
    assert documented.info_button.isVisibleTo(documented)
    assert documented.info_button.toolTip()

    undocumented = window._frames_by_key["some_unknown_future_key"]
    assert not undocumented.info_button.isVisibleTo(undocumented)


def test_selection_moves_between_rows():
    window = build()
    first = window._frames_by_key["volume"]
    second = window._frames_by_key["pitch"]

    window.select_frame(first)
    assert first.property("selected") is True

    window.select_frame(second)
    assert first.property("selected") is False
    assert second.property("selected") is True


def test_focusing_a_row_selects_it():
    window = build()
    frame = window._frames_by_key["pitch"]
    frame.activated.emit()          # what focusInEvent raises
    assert window._selected_frame is frame


def test_ctrl_c_copies_the_focused_row():
    window = build()
    frame = window._frames_by_key["volume"]
    QApplication.clipboard().clear()

    press(frame, Qt.Key_C, Qt.ControlModifier)
    assert QApplication.clipboard().text() == "volume = 0.8"


def test_delete_key_removes_the_row():
    window = build()
    frame = window._frames_by_key["pitch"]

    press(frame, Qt.Key_Delete)
    assert "pitch" not in window._frames_by_key
    assert "pitch" not in window.get_properties_value()


def test_a_focused_row_passes_panel_shortcuts_through():
    """Paste and new-property belong to the panel; the row must leave those
    keys unaccepted so they reach the properties window's own handler."""
    window = build()
    frame = window._frames_by_key["volume"]

    for key in (Qt.Key_V, Qt.Key_F):
        assert not press(frame, key, Qt.ControlModifier).isAccepted()

    assert press(frame, Qt.Key_C, Qt.ControlModifier).isAccepted()


def test_window_hotkeys_act_on_the_selection():
    window = build()
    window.select_frame(window._frames_by_key["volume"])
    QApplication.clipboard().clear()

    window.copy_selected_property()
    assert QApplication.clipboard().text() == "volume = 0.8"

    window.delete_selected_property()
    assert "volume" not in window.get_properties_value()


def test_readonly_mode_blocks_deleting_the_selection():
    window = build()
    window.set_readonly_mode(True)
    window.select_frame(window._frames_by_key["volume"])

    window.delete_selected_property()
    assert "volume" in window.get_properties_value()


def test_reset_to_default_restores_the_registry_value():
    window = build(dict(EVENT, volume=0.15))
    frame = window._frames_by_key["volume"]
    window.select_frame(frame)
    window._undo_enabled = True     # switch_to_item does this in the real panel

    window.reset_selected_property()
    assert window.get_properties_value()["volume"] == registry_defaults()["volume"]
    assert window.undo_stack.count() == 1       # undoable like any other edit


def test_reset_is_offered_only_where_a_default_exists():
    window = build()
    assert window._defaults_for(window._frames_by_key["volume"])
    # Nothing in the registry ever offered this key, so there is nothing to
    # go back to and the menu entry stays disabled.
    assert window._defaults_for(window._frames_by_key["some_unknown_future_key"]) == {}


def test_readonly_mode_blocks_resetting():
    window = build(dict(EVENT, volume=0.15))
    window.set_readonly_mode(True)
    window.select_frame(window._frames_by_key["volume"])

    window.reset_selected_property()
    assert window.get_properties_value()["volume"] == 0.15


def test_a_deleted_row_stops_being_the_selection():
    """Hotkeys must never reach a row whose C++ object is gone."""
    window = build()
    frame = window._frames_by_key["volume"]
    window.select_frame(frame)

    frame.delete_action()
    assert window._selected_frame is None
    window.copy_selected_property()      # must not raise
    window.delete_selected_property()
    window.reset_selected_property()


def test_up_and_down_ask_the_window_to_move_focus():
    window = build()
    frame = window._frames_by_key["volume"]
    steps = []
    frame.navigate.connect(steps.append)

    press(frame, Qt.Key_Down)
    press(frame, Qt.Key_Up)
    assert steps == [1, -1]


def test_modified_rail_tracks_the_saved_file():
    tree = QTreeWidget()
    item = QTreeWidgetItem(tree)
    item.setText(0, "event_a")
    item.setData(0, Qt.UserRole, dict(EVENT))
    window = SoundEventEditorPropertiesWindow(value={}, tree=tree)
    tree.setCurrentItem(item)
    window.set_saved_baseline({"event_a": dict(EVENT)})
    window.switch_to_item(item)

    volume = window._frames_by_key["volume"]
    assert volume.rail.property("h5State") == ""

    volume.property_instance.set_value(0.25)
    volume.on_property_updated()
    assert volume.rail.property("h5State") == "modified"

    # Back to the saved value: no longer modified.
    volume.property_instance.set_value(0.8)
    volume.on_property_updated()
    assert volume.rail.property("h5State") == ""


def test_a_property_missing_from_the_saved_file_reads_as_modified():
    tree = QTreeWidget()
    item = QTreeWidgetItem(tree)
    item.setText(0, "event_a")
    item.setData(0, Qt.UserRole, dict(EVENT))
    window = SoundEventEditorPropertiesWindow(value={}, tree=tree)
    tree.setCurrentItem(item)
    window.set_saved_baseline({"event_a": {key: EVENT[key] for key in EVENT if key != "pitch"}})
    window.switch_to_item(item)

    assert window._frames_by_key["pitch"].rail.property("h5State") == "modified"
    assert window._frames_by_key["volume"].rail.property("h5State") == ""


def test_curve_rows_are_named_and_told_their_event():
    """A curve editor draws no label of its own, so the row supplies one and
    forwards the event name into the plot title."""
    curve = [[0.0, 0.0, 0.0, 0.0, 2, 3], [1.0, 1.0, 0.0, 0.0, 2, 3]]
    tree = QTreeWidget()
    item = QTreeWidgetItem(tree)
    item.setText(0, "event_a")
    data = dict(EVENT, time_volume_mapping_curve=curve)
    item.setData(0, Qt.UserRole, dict(data))
    window = SoundEventEditorPropertiesWindow(value={}, tree=tree)
    tree.setCurrentItem(item)
    window.switch_to_item(item)

    frame = window._frames_by_key["time_volume_mapping_curve"]
    assert frame.property_instance.current_element_name == "event_a"
    labels = [label.text() for label in frame.content.findChildren(QLabel)]
    assert frame.display_name in labels


def test_frames_still_serialize_without_their_generated_form():
    window = build()
    assert window.get_properties_value() == EVENT
    assert isinstance(window._frames_by_key["volume"], SoundEventEditorPropertyFrame)
