"""Copy and paste speak KV3 — the format the .vsndevts itself is written in.

Copying writes a KV3 body (no encoding header, no outer braces) so the text can
go either back into the editor or straight into the file. Pasting takes that,
a whole KV3 document, or the Python dict repr older builds put on the clipboard.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

app = QApplication.instance() or QApplication(sys.argv)

from gui.common import JsonToKv3
from gui.editors.soundevent_editor.properties_window import SoundEventEditorPropertiesWindow
from gui.editors.soundevent_editor.property.frame import kv3_snippet

CURVE = [
    [0.0, 1.0, -0.001763, -0.013763, 1.4, 4.0],
    [1000.0, 0.5, -0.000526, 0.053474, 1.0, 1.0],
    [18000.0, 0.0, 0.0, 0.0, 2.0, 3.0],
]
EVENT = {
    "vsnd_files": ["sounds/a.vsnd", "sounds/b.vsnd"],
    "volume": 0.8,
    "distance_volume_mapping_curve": CURVE,
}


def build(data=None):
    data = dict(data if data is not None else EVENT)
    tree = QTreeWidget()
    item = QTreeWidgetItem(tree)
    item.setText(0, "event_a")
    item.setData(0, Qt.UserRole, dict(data))
    window = SoundEventEditorPropertiesWindow(value={}, tree=tree)
    tree.setCurrentItem(item)
    window.switch_to_item(item)
    return window


def test_copy_writes_a_pasteable_kv3_body():
    window = build()
    window._frames_by_key["volume"].copy_action()
    text = QApplication.clipboard().text()

    assert text == "volume = 0.8"
    assert "<!--" not in text and not text.startswith("{")


def test_a_copied_curve_survives_the_round_trip():
    window = build()
    window._frames_by_key["distance_volume_mapping_curve"].copy_action()

    text = QApplication.clipboard().text()
    assert SoundEventEditorPropertiesWindow.parse_clipboard(text) == {
        "distance_volume_mapping_curve": CURVE
    }


def test_paste_accepts_kv3_a_whole_document_and_the_legacy_repr():
    parse = SoundEventEditorPropertiesWindow.parse_clipboard
    expected = {"volume": 0.35}

    assert parse(kv3_snippet(expected)) == expected          # what copy writes
    assert parse(JsonToKv3(expected)) == expected            # a whole KV3 file
    assert parse(str(expected)) == expected                  # older builds
    assert parse("not a property") is None
    assert parse("") is None


def test_pasting_a_curve_adds_it_to_the_event():
    window = build({"volume": 0.8})
    QApplication.clipboard().setText(kv3_snippet({"distance_volume_mapping_curve": CURVE}))

    window.paste_property()
    assert window.get_properties_value()["distance_volume_mapping_curve"] == CURVE


def test_paste_adds_every_property_in_the_clipboard():
    """A copied min/max pair is two keys; pasting must not drop one."""
    window = build({"volume": 0.8})
    pair = {"volume_falloff_min": 200.0, "volume_falloff_max": 1800.0}
    QApplication.clipboard().setText(kv3_snippet(pair))

    window.paste_property()
    result = window.get_properties_value()
    assert result["volume_falloff_min"] == 200.0
    assert result["volume_falloff_max"] == 1800.0
    assert window.undo_stack.count() == 1       # one entry for the whole paste


def test_paste_skips_properties_the_event_already_has():
    """A key already on the event keeps its value; the rest still paste."""
    window = build({"volume": 0.8})
    QApplication.clipboard().setText(kv3_snippet({"volume": 0.1, "pitch": 1.5}))

    window.paste_property()
    result = window.get_properties_value()
    assert result["volume"] == 0.8      # untouched
    assert result["pitch"] == 1.5       # added
