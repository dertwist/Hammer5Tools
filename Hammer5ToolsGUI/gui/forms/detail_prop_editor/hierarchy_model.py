"""Document rules for the detail-prop hierarchy.

The tree is still the source of truth for ordering -- that is what makes
drag-and-drop reordering free -- but deciding what the *document* becomes
afterwards is not a widget concern. Qt's InternalMove serialises items through
mime data and rebuilds them as plain QTreeWidgetItems, so a model can land at
top level or nested under another model, and the result has to be normalised
back into well-formed types. Those rules live here, with no Qt import.
"""

from __future__ import annotations

import os

from .schema import default_model, default_type

DEFAULT_TYPE_NAME = "detail_type"


def is_model(data: dict) -> bool:
    """A payload is a model if it names one; a detail type never does."""
    return "m_ModelName" in data


def model_label(model: dict) -> str:
    name = (model.get("m_ModelName") or "").strip()
    return os.path.basename(name) if name else "<no model>"


def model_summary(model: dict) -> str:
    name = (model.get("m_ModelName") or "").strip()
    return name or "no model assigned"


def unique_name(base: str, existing) -> str:
    """`base`, or base_2, base_3 ... until it is not taken."""
    existing = set(existing)
    if base not in existing:
        return base
    suffix = 2
    while f"{base}_{suffix}" in existing:
        suffix += 1
    return f"{base}_{suffix}"


def normalize_dropped(rows) -> dict:
    """Rebuild {name: type} from the post-drop top-level rows.

    Each row is (label, payload, models) where `models` is every model payload
    at or below that row, in visual order.
    """
    types = {}
    for label, data, models in rows:
        if is_model(data):
            # A model dropped at top level becomes a type of its own.
            detail_type = default_type()
            detail_type["m_Models"] = models
        else:
            detail_type = dict(data)
            # A type with nothing under it still needs one model to be valid.
            detail_type["m_Models"] = models or [default_model()]
        types[unique_name(label or DEFAULT_TYPE_NAME, types)] = detail_type
    return types
