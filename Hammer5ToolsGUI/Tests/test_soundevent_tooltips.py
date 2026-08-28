"""Every property the browser offers must carry a tooltip."""

from __future__ import annotations

from gui.editors.soundevent_editor.objects import soundevent_editor_properties
from gui.editors.soundevent_editor.property_tooltips import (
    SOUNDEVENT_TOOLTIPS,
    get_tooltip,
)


def registry_keys() -> list[str]:
    """KV3 keys in property-browser order."""
    return [
        next(iter(payload))
        for entry in soundevent_editor_properties
        for payload in entry.values()
    ]


def test_every_registry_property_has_a_tooltip():
    missing = [key for key in registry_keys() if not get_tooltip(key)]
    assert missing == []


def test_no_tooltip_without_a_property():
    orphans = sorted(set(SOUNDEVENT_TOOLTIPS) - set(registry_keys()))
    assert orphans == []


def test_repeated_comment_keys_reuse_the_base_tooltip():
    assert get_tooltip("comment_2") == get_tooltip("comment")
    assert get_tooltip("comment_37") == get_tooltip("comment")


def test_unknown_key_is_empty_not_an_error():
    assert get_tooltip("not_a_property") == ""
    assert get_tooltip("") == ""
