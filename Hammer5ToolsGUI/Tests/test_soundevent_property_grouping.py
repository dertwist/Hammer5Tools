"""Grouped display must not change what gets written back to the file."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.soundevent_editor.properties_window import (
    PropertyGroupHeader,
    SoundEventEditorPropertiesWindow,
)
from gui.editors.soundevent_editor.property.frame import SoundEventEditorPropertyFrame
from gui.editors.soundevent_editor.property_schema import COLLAPSED_BY_DEFAULT

# Deliberately out of canonical order, and with keys from several groups.
EVENT = {
    "vsnd_files": "sounds/ambient/test.vsnd",
    "volume": 0.8,
    "enable_retrigger": False,
    "retrigger_interval_max": 30.0,
    "type": "csgo_mega",
    "retrigger_interval_min": 10.0,
    "some_unknown_future_key": "keep me",
    "use_time_volume_mapping_curve": True,
    "retrigger_radius": 500.0,
}


def build(data=None):
    window = SoundEventEditorPropertiesWindow(value=dict(data or EVENT))
    window.populate_properties(dict(data or EVENT))
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


def test_serialized_key_order_matches_the_source_file():
    window = build()
    assert list(window.get_properties_value()) == list(EVENT)


def test_serialized_values_are_unchanged():
    window = build()
    result = window.get_properties_value()
    assert result["type"] == "csgo_mega"
    assert result["some_unknown_future_key"] == "keep me"
    assert result["retrigger_interval_min"] == 10.0
    assert result["retrigger_interval_max"] == 30.0


def test_display_order_is_grouped_not_source_order():
    window = build()
    order = [frame.display_order for frame in frames(window)]
    assert order == sorted(order)
    # 'type' is in the first group; the unknown key lands last, in custom.
    first = frames(window)[0]
    last = frames(window)[-1]
    assert "type" in first.value
    assert "some_unknown_future_key" in last.value


def test_min_max_pair_shares_one_frame():
    window = build()
    pair = window._frames_by_key["retrigger_interval_min"]
    assert pair is window._frames_by_key["retrigger_interval_max"]
    assert set(pair.value) == {"retrigger_interval_min", "retrigger_interval_max"}
    assert pair.ui.property_class.text() == "Retrigger Interval"


def test_toggle_disables_its_dependents():
    window = build()
    # enable_retrigger is False in EVENT
    assert not window._frames_by_key["retrigger_radius"].isEnabled()
    assert not window._frames_by_key["retrigger_interval_min"].isEnabled()
    # use_time_volume_mapping_curve is True but the curve is not on this event
    assert window._frames_by_key["volume"].isEnabled()


def test_toggle_reenables_dependents_when_switched_on():
    window = build()
    toggle = window._frames_by_key["enable_retrigger"]
    toggle.value = {"enable_retrigger": True}
    window._apply_toggle_dependencies()
    assert window._frames_by_key["retrigger_radius"].isEnabled()


def test_unknown_keys_land_in_a_custom_group_header():
    window = build()
    groups = [header.group for header in headers(window)]
    assert groups == sorted(groups, key=lambda g: [h.group for h in headers(window)].index(g))
    assert "custom" in groups


def test_collapsed_groups_hide_their_properties_but_still_serialize():
    window = build()
    for header in headers(window):
        if header.group in COLLAPSED_BY_DEFAULT:
            assert not header.show_child.isChecked()
    custom = window._frames_by_key["some_unknown_future_key"]
    assert custom.isHidden()
    assert "some_unknown_future_key" in window.get_properties_value()


def test_group_header_toggle_hides_and_shows_members():
    window = build()
    header = next(h for h in headers(window) if h.group == "retrigger")
    members = [window._frames_by_key["enable_retrigger"], window._frames_by_key["retrigger_radius"]]
    header.show_child.setChecked(False)
    header.apply()
    assert all(m.isHidden() for m in members)
    header.show_child.setChecked(True)
    header.apply()
    assert all(not m.isHidden() for m in members)


def test_property_added_later_lands_in_its_group():
    window = build()
    window.create_property("pitch", 1.0)
    order = [frame.display_order for frame in frames(window)]
    assert order == sorted(order)
    # And it is appended to the file, not inserted mid-order.
    assert list(window.get_properties_value())[-1] == "pitch"


def test_clear_resets_group_state():
    window = build()
    window.properties_clear()
    assert frames(window) == []
    assert headers(window) == []
    assert window._frames_by_key == {}
    assert window.get_properties_value() == {}


def test_group_children_have_left_offset():
    window = build()
    for frame in frames(window):
        margins = frame.ui.verticalLayout.contentsMargins()
        assert margins.left() > 0

