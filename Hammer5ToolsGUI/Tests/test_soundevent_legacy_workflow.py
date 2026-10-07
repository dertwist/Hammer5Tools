"""Legacy panel workflows: filtering and safely previewing internal events."""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidgetItem

from gui.editors.soundevent_editor import main, internal_explorer, internal_soundevent_explorer
from gui.editors.soundevent_editor.properties_window import SoundEventEditorPropertiesWindow
from gui.editors.soundevent_editor.property_schema import GROUP_TITLES

app = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def editor(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "get_cs2_path", lambda: str(tmp_path))
    monkeypatch.setattr(main, "addon_content_dir", lambda: None)
    monkeypatch.setattr(internal_explorer, "_VSND_FOLDERS_CACHE", {})
    monkeypatch.setattr(internal_soundevent_explorer.InternalSoundEventExplorer, "reload", lambda self: None)
    window = main.SoundEventEditorMainWindow()
    data = {"base": "amb.base", "volume": 0.8}
    item = QTreeWidgetItem(window.ui.hierarchy_widget, ["addon.event"])
    item.setData(0, Qt.UserRole, dict(data))
    window.ui.hierarchy_widget.soundevent_document.events["addon.event"] = dict(data)
    window.ui.hierarchy_widget.setCurrentItem(item)
    monkeypatch.setattr(window.internal_soundevents_explorer, "get_event_data", lambda name: {
        "base": "amb.soundscapeParent.base", "enable_child_events": True,
        "soundevent_01": ["ambient_example.outdoors.birds", "ambient_example.outdoors.wind"],
    })
    yield window
    window.close()
    window.deleteLater()


def test_internal_preview_names_and_plays_the_displayed_event(editor):
    editor._preview_internal_soundevent("ambient_example.outdoors")
    assert "Properties: ambient_example.outdoors" in editor.ui.label.text()
    assert "3 properties" in editor.ui.label.text()
    assert editor.soundevent_player_widget._event_resolver() == "ambient_example.outdoors"
    assert editor.PropertiesWindow.readonly_mode
    assert not editor.property_browser_widget.prop_tree_widget.isEnabled()
    assert editor.property_browser_widget.tmpl_list_widget.isEnabled()


def test_preview_cannot_change_the_selected_addon_event(editor):
    before = dict(editor.ui.hierarchy_widget.soundevent_document.events["addon.event"])
    editor._preview_internal_soundevent("ambient_example.outdoors")
    editor.on_property_added_from_browser("Pitch", {"pitch": 1.0})
    editor.PropertiesWindow.new_property("Pitch", {"pitch": 1.0})
    QApplication.clipboard().setText("pitch = 1.0")
    editor.PropertiesWindow.paste_property()
    editor.update_properties_window()
    assert "pitch" not in editor.PropertiesWindow.value
    assert editor.ui.hierarchy_widget.soundevent_document.events["addon.event"] == before
    assert editor.undo_stack.count() == 0


def test_clicking_the_same_addon_event_restores_editing(editor):
    item = editor.ui.hierarchy_widget.currentItem()
    editor._preview_internal_soundevent("ambient_example.outdoors")
    editor.ui.hierarchy_widget.itemClicked.emit(item, 0)
    assert editor.current_event_name() == "addon.event"
    assert not editor.PropertiesWindow.readonly_mode
    assert editor.PropertiesWindow.value == {"base": "amb.base", "volume": 0.8}
    assert editor.property_browser_widget.prop_tree_widget.isEnabled()


def test_history_change_returns_from_internal_preview(editor):
    editor.PropertiesWindow.new_property("Pitch", {"pitch": 1.0})
    editor._preview_internal_soundevent("ambient_example.outdoors")
    editor.undo_stack.undo()
    assert editor.current_event_name() == "addon.event"
    assert not editor.PropertiesWindow.readonly_mode
    assert "pitch" not in editor.PropertiesWindow.value


def test_property_filter_preserves_collapsed_groups_and_hides_empty_headers():
    window = SoundEventEditorPropertiesWindow(value={})
    data = {"volume": 0.8, "unknown_future_key": "keep", "pitch": 1.0}
    window.populate_properties(data)
    custom = window._frames_by_key["unknown_future_key"]
    assert custom.isHidden()
    window.filter_properties("unknown")
    assert not custom.isHidden()
    assert window._group_headers["playback"].isHidden()
    assert not window._group_headers["custom"].show_child.isChecked()
    window.filter_properties("")
    assert custom.isHidden()
    assert not window._group_headers["playback"].isHidden()
    assert window.get_properties_value() == data


def test_group_toggle_and_event_switch_keep_the_current_filter():
    window = SoundEventEditorPropertiesWindow(value={})
    window.populate_properties({"volume": 0.8, "pitch": 1.0})
    window.filter_properties("volume")
    playback = window._group_headers["playback"]
    playback.show_child.setChecked(False)
    playback.apply()
    assert not window._frames_by_key["volume"].isHidden()
    assert window._frames_by_key["pitch"].isHidden()
    window.populate_properties({"volume": 0.2, "pitch": 0.5})
    assert window._frames_by_key["pitch"].isHidden()
    window.filter_properties("")
    assert window._frames_by_key["volume"].isHidden()
    window.filter_properties(GROUP_TITLES["playback"])
    assert not window._frames_by_key["volume"].isHidden()
    assert not window._frames_by_key["pitch"].isHidden()


@pytest.mark.parametrize("key,initial,extra", [
    ("soundevent_01", ["ambient.birds", "ambient.wind"], "ambient.airplanes"),
    ("vsnd_files", ["sounds/a.vsnd", "sounds/b.vsnd"], "sounds/c.vsnd"),
])
def test_list_add_appends_below_existing_rows(key, initial, extra):
    window = SoundEventEditorPropertiesWindow(value={})
    window.populate_properties({key: list(initial)})
    widget = window._frames_by_key[key].property_instance
    widget.add_element(extra)
    assert window.get_properties_value()[key] == initial + [extra]
    assert widget.vertical_layout.indexOf(widget.button) > max(
        widget.vertical_layout.indexOf(element) for element in widget._elements()
    )


def test_reused_empty_child_list_keeps_a_blank_entry_field():
    window = SoundEventEditorPropertiesWindow(value={})
    window.populate_properties({"soundevent_01": ["ambient.birds"]})
    frame = window._frames_by_key["soundevent_01"]
    window.populate_properties({"soundevent_01": ""})
    assert window._frames_by_key["soundevent_01"] is frame
    assert len(frame.property_instance._elements()) == 1
    assert frame.property_instance._elements()[0].editline.text() == ""
    assert window.get_properties_value() == {"soundevent_01": ""}
