"""
Widget extraction for the SmartProp preview.

Provides backward-compatible widget extraction utilities and delegates to the
sequential modifier evaluator (modifier_evaluator.py).
"""
from src.editors.smartprop_editor.viewport_3d.engine.modifier_evaluator import (
    resolve_color, evaluate_element_modifiers, evaluate_single_modifier,
)

_resolve_color = resolve_color


def extract_widget_specs(data, ctx):
    """Return a list of widget spec dicts for ``data`` (never raises)."""
    try:
        _, _, _, widgets = evaluate_element_modifiers(data, ctx)
        return widgets
    except Exception:
        return []
