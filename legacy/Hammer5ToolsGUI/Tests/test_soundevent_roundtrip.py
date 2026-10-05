"""Loading an event into the grouped property editor must not rewrite the file.

The property list is displayed in schema group order, which is not the order
keys appear in a .vsndevts. Serialization has to undo that, or opening a file
and saving it would produce a diff on every event.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.soundevent_editor.document_model import SoundEventDocument
from gui.editors.soundevent_editor.properties_window import (
    SoundEventEditorPropertiesWindow,
)

SAMPLE = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
    // Ambient loops for the tunnel section
    "amb.tunnel.loop" =
    {
        type = "csgo_mega"
        vsnd_files =
        [
            "sounds/ambient/tunnel_loop.vsnd",
        ]
        volume = 0.8
        enable_retrigger = false
        retrigger_interval_max = 30.000000
        retrigger_interval_min = 10.000000
        base = "amb.base"
        mixgroup = "Ambient"
        position = [ 0.000000, 0.000000, 0.000000 ]
        use_distance_volume_mapping_curve = true
    }

    "music.round.start" =
    {
        type = "csgo_mega"
        volume = 1.000000
        startpoint_01 = 0.000000
        vsnd_files =
        [
            "sounds/music/round_start.vsnd",
        ]
    }
}
"""


def load_through_editor(text: str) -> SoundEventDocument:
    """Round-trip every event in a document through the property editor."""
    document = SoundEventDocument.from_text(text)
    for name, data in list(document.events.items()):
        window = SoundEventEditorPropertiesWindow(value=dict(data))
        window.populate_properties(dict(data))
        document.events[name] = window.get_properties_value()
        window.deleteLater()
    return document


def test_key_order_survives_a_trip_through_the_editor():
    original = SoundEventDocument.from_text(SAMPLE)
    reloaded = load_through_editor(SAMPLE)
    for name, data in original.events.items():
        assert list(reloaded.events[name]) == list(data), name


def test_values_survive_a_trip_through_the_editor():
    original = SoundEventDocument.from_text(SAMPLE)
    reloaded = load_through_editor(SAMPLE)
    for name, data in original.events.items():
        for key, value in data.items():
            assert reloaded.events[name][key] == value, (name, key)


def test_serialized_text_is_unchanged():
    baseline = SoundEventDocument.from_text(SAMPLE).to_text()
    assert load_through_editor(SAMPLE).to_text() == baseline


def test_event_comments_are_still_preserved():
    reloaded = load_through_editor(SAMPLE)
    assert "tunnel section" in reloaded.event_comments["amb.tunnel.loop"]


def test_a_scalar_vsnd_files_is_widened_to_a_list():
    """Known, pre-refactor behaviour, pinned here so it cannot change silently.

    The file list widget always serializes a list, so an event that stores a
    bare string comes back as a one-element array.
    """
    scalar = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
    "music.round.start" =
    {
        type = "csgo_mega"
        vsnd_files = "sounds/music/round_start.vsnd"
    }
}
"""
    reloaded = load_through_editor(scalar)
    assert reloaded.events["music.round.start"]["vsnd_files"] == [
        "sounds/music/round_start.vsnd"
    ]


def test_a_string_bool_is_narrowed_to_a_real_bool():
    """Known, pre-refactor behaviour, pinned here so it cannot change silently.

    Shipped csgo_music events store these flags as the strings "true"/"false".
    The editor builds a real checkbox for them, so they come back as bools.
    """
    stringy = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
    "music.round.start" =
    {
        type = "csgo_mega"
        loop_track = "true"
    }
}
"""
    reloaded = load_through_editor(stringy)
    assert reloaded.events["music.round.start"]["loop_track"] is True
