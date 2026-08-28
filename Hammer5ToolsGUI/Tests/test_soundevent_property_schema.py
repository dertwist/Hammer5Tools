"""The schema table must build exactly what the old elif chain built.

``data/soundevent_property_dispatch.json`` was recorded from the branch-per-key
version of ``property/frame.py``. Every property the browser offered back then
must still produce the same widget class with the same slider ranges, options
and serialized value.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QVBoxLayout

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.soundevent_editor.objects import soundevent_editor_properties
from gui.editors.soundevent_editor.property.frame import (
    _WIDGETS,
    SoundEventEditorPropertyFrame,
)
from gui.editors.soundevent_editor.property_schema import (
    GROUP_ORDER,
    PAIRED,
    SPECS,
    TOGGLE_DEPENDENTS,
    get_spec,
    sort_key,
)

BASELINE = json.loads(
    (Path(__file__).parent / "data" / "soundevent_property_dispatch.json").read_text("utf8")
)


def registry_defaults() -> dict:
    values = {}
    for entry in soundevent_editor_properties:
        for payload in entry.values():
            key, value = next(iter(payload.items()))
            values[key] = value
    return values


def fingerprint(key: str, value) -> dict:
    frame = SoundEventEditorPropertyFrame(_data={key: value}, widget_list=QVBoxLayout())
    widget = frame.property_instance
    row = {"cls": type(widget).__name__, "value": repr(frame.serialize_properties())}
    float_widget = getattr(widget, "float_widget_instance", None)
    if float_widget is not None:
        row["slider_range"] = list(float_widget.slider_range)
        row["only_positive"] = bool(float_widget.only_positive)
    axes = getattr(widget, "float_widget_instances", None)
    if axes:
        row["axes"] = len(axes)
        row["slider_range"] = list(axes[0].slider_range)
    combobox = getattr(widget, "combobox", None)
    if combobox is not None and hasattr(combobox, "items"):
        row["options"] = len(combobox.items)
    ui = getattr(widget, "ui", None)
    if ui is not None and hasattr(ui, "label_01"):
        row["labels"] = [ui.label_01.text(), ui.label_02.text()]
    frame.deleteLater()
    return row


@pytest.mark.parametrize("key", sorted(BASELINE))
def test_dispatch_matches_pre_refactor_baseline(key):
    defaults = registry_defaults()
    # Recorded before source_soundscape reached the registry: feed the
    # baseline its original input so this compares dispatch, not defaults.
    defaults["source_soundscape"] = ""
    assert fingerprint(key, defaults[key]) == BASELINE[key]


def test_every_registry_property_has_a_spec():
    unspecified = [key for key in registry_defaults() if key not in SPECS]
    assert unspecified == []


def test_every_spec_kind_has_a_builder():
    unbuildable = sorted({spec.kind for spec in SPECS.values()} - set(_WIDGETS))
    assert unbuildable == []


def test_every_spec_group_is_declared():
    unknown = sorted({spec.group for spec in SPECS.values()} - set(GROUP_ORDER))
    assert unknown == []


def test_toggles_and_pairs_reference_real_properties():
    referenced = set(TOGGLE_DEPENDENTS)
    for dependents in TOGGLE_DEPENDENTS.values():
        referenced.update(dependents)
    for low, high, _title in PAIRED:
        referenced.update((low, high))
    assert sorted(referenced - set(SPECS)) == []


def test_unknown_keys_sort_last_as_custom():
    assert get_spec("some_future_field").group == "custom"
    assert sort_key("some_future_field") > sort_key("volume")


def test_paired_keys_share_a_group():
    for low, high, _title in PAIRED:
        assert SPECS[low].group == SPECS[high].group, (low, high)
