"""
SmartProp note helper utilities.

Provides helper functions for reading and writing notes on element, modifier,
and selection criteria dictionary data, supporting legacy comment keys for backward compatibility.
"""

from __future__ import annotations
from typing import Any

# Primary note key used in modern SmartProps / ModelDoc
NOTE_KEY = "m_sNote"

# Legacy comment / note keys for backward compatibility
LEGACY_NOTE_KEYS = ("m_Comment", "m_sComment", "note", "_comment")


def get_note(data: Any) -> str:
    """Extract note text from an element/modifier data dictionary."""
    if not isinstance(data, dict):
        return ""
    # Check primary key first
    val = data.get(NOTE_KEY)
    if val is not None and str(val).strip():
        return str(val)
    # Fallback to legacy comment keys
    for k in LEGACY_NOTE_KEYS:
        val = data.get(k)
        if val is not None and str(val).strip():
            return str(val)
    return ""


def has_note(data: Any) -> bool:
    """Return True if the data dictionary contains a non-empty note."""
    return bool(get_note(data))


def set_note(data: dict, text: str) -> None:
    """Set or clear the note on a data dictionary, pruning empty notes and cleaning legacy keys."""
    if not isinstance(data, dict):
        return
    text = str(text) if text is not None else ""
    if text.strip():
        data[NOTE_KEY] = text
        # Clean up legacy keys once updated
        for k in LEGACY_NOTE_KEYS:
            data.pop(k, None)
    else:
        # Clear note and legacy keys
        data.pop(NOTE_KEY, None)
        for k in LEGACY_NOTE_KEYS:
            data.pop(k, None)
