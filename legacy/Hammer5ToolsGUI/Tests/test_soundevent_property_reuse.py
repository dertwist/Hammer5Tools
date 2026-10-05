"""Repopulating the properties window must reuse frames, not rebuild them.

Undo/redo and event switching both go through populate_properties(); rebuilding
every frame there is what made them stutter, so these tests pin both halves of
the contract: the same frame objects survive, and the values they show are still
correct afterwards.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.soundevent_editor.properties_window import (
    PropertyGroupHeader,
    SoundEventEditorPropertiesWindow,
)
from gui.editors.soundevent_editor.property.frame import SoundEventEditorPropertyFrame

EVENT = {
    "vsnd_files": ["sounds/ambient/a.vsnd", "sounds/ambient/b.vsnd"],
    "volume": 0.8,
    "pitch": 1.0,
    "enable_retrigger": False,
    "type": "csgo_mega",
    "position": [1.0, 2.0, 3.0],
}


def build(data=None):
    data = dict(data or EVENT)
    window = SoundEventEditorPropertiesWindow(value=dict(data))
    window.populate_properties(dict(data))
    return window


def frames(window):
    layout = window.ui.properties_layout
    return [
        layout.itemAt(i).widget()
        for i in range(layout.count())
        if isinstance(layout.itemAt(i).widget(), SoundEventEditorPropertyFrame)
    ]


def headers(window):
    layout = window.ui.properties_layout
    return [
        layout.itemAt(i).widget()
        for i in range(layout.count())
        if isinstance(layout.itemAt(i).widget(), PropertyGroupHeader)
    ]


def test_same_keys_reuse_the_same_frames():
    window = build()
    before = frames(window)
    window.populate_properties(dict(EVENT))
    assert frames(window) == before


def test_reused_frames_show_the_new_values():
    window = build()
    changed = dict(EVENT, volume=0.25, type="csgo_music", enable_retrigger=True)
    window.populate_properties(changed)
    result = window.get_properties_value()
    assert result["volume"] == 0.25
    assert result["type"] == "csgo_music"
    assert result["enable_retrigger"] is True


def test_reused_list_property_follows_the_new_length():
    """Shorter, longer and single-entry file lists all survive reuse."""
    window = build()
    for files in (["sounds/only.vsnd"], ["a.vsnd", "b.vsnd", "c.vsnd"], "one.vsnd"):
        data = dict(EVENT, vsnd_files=files)
        window.populate_properties(dict(data))
        assert window.get_properties_value() == build(data).get_properties_value()


def test_only_the_difference_is_built_or_destroyed():
    window = build()
    kept = {frame for frame in frames(window) if frame.name != "pitch"}

    smaller = {key: value for key, value in EVENT.items() if key != "pitch"}
    window.populate_properties(smaller)
    assert set(frames(window)) == kept
    assert "pitch" not in window.get_properties_value()

    window.populate_properties(dict(EVENT))
    assert kept.issubset(set(frames(window)))
    assert window.get_properties_value()["pitch"] == 1.0


def test_group_bar_disappears_with_its_last_property():
    window = build()
    group = window._frames_by_key["volume"].display_order[0]
    assert any(header.group_index == group for header in headers(window))

    without_group = {
        key: value for key, value in EVENT.items()
        if window._frames_by_key[key].display_order[0] != group
    }
    window.populate_properties(without_group)
    assert not any(header.group_index == group for header in headers(window))


def test_switching_between_events_keeps_the_shared_frames():
    window = build()
    volume_frame = window._frames_by_key["volume"]

    other = {"vsnd_files": "sounds/other.vsnd", "volume": 0.1, "type": "csgo_default"}
    window.populate_properties(dict(other))
    assert window._frames_by_key["volume"] is volume_frame
    # Reuse must land on exactly what a rebuild would have produced.
    assert window.get_properties_value() == build(other).get_properties_value()

    window.populate_properties(dict(EVENT))
    assert window._frames_by_key["volume"] is volume_frame
    assert list(window.get_properties_value()) == list(EVENT)


def test_reused_curve_follows_its_datapoints():
    """The plot is the expensive part; only the datapoint rows may change."""
    curve = [[0.0, 0.0, 0.0, 0.0, 2, 3], [1.0, 1.0, 0.0, 0.0, 2, 3]]
    data = dict(EVENT, time_volume_mapping_curve=curve)
    window = build(data)
    plot = window._frames_by_key["time_volume_mapping_curve"].property_instance

    for points in (curve[:1], curve, curve + [[2.0, 0.5, 0.0, 0.0, 2, 3]]):
        window.populate_properties(dict(data, time_volume_mapping_curve=points))
        assert window._frames_by_key["time_volume_mapping_curve"].property_instance is plot
        assert window.get_properties_value()["time_volume_mapping_curve"] == points


def test_reused_string_bool_keeps_its_coercion():
    """'true'/'false' strings from shipped music events must still reach a bool."""
    window = build(dict(EVENT, loop_track="false"))
    window.populate_properties(dict(EVENT, loop_track="true"))
    assert window.get_properties_value()["loop_track"] is True


def test_reuse_does_not_push_undo_entries():
    window = build()
    window._undo_enabled = True
    window.undo_stack.clear()
    window.populate_properties(dict(EVENT, volume=0.33))
    assert window.undo_stack.count() == 0


def test_selecting_and_undoing_through_the_tree():
    """The end-to-end path: tree selection and the undo stack both reuse frames."""
    other = {"vsnd_files": ["b.vsnd"], "volume": 0.2, "pitch": 1.5}
    tree = QTreeWidget()
    items = []
    for name, data in (("a", EVENT), ("b", other)):
        item = QTreeWidgetItem(tree)
        item.setText(0, name)
        item.setData(0, Qt.UserRole, dict(data))
        items.append(item)
    window = SoundEventEditorPropertiesWindow(value={}, tree=tree)

    window.switch_to_item(items[0])
    volume_frame = window._frames_by_key["volume"]
    assert window.get_properties_value() == EVENT

    window.switch_to_item(items[1])
    assert window._frames_by_key["volume"] is volume_frame
    assert window.get_properties_value() == other

    tree.setCurrentItem(items[1])
    volume_frame.property_instance.set_value(0.9)
    volume_frame.on_property_updated()
    assert window.undo_stack.count() == 1

    window.undo_stack.undo()
    assert window.get_properties_value()["volume"] == 0.2
    window.undo_stack.redo()
    assert window.get_properties_value()["volume"] == 0.9
    assert window._frames_by_key["volume"] is volume_frame

    window.switch_to_item(None)
    assert window._frames_by_key == {}
    assert window._frames_by_entry == {}
