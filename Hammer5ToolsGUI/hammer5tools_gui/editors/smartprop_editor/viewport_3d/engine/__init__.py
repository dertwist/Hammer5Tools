"""
SmartProp evaluation engine.

A small, self-contained emulation of the Source 2 Hammer SmartProp process used
by the 3D viewport preview: it evaluates ``m_Expression`` strings and resolves
``m_SourceName`` variable bindings to concrete values, and extracts the editing
widgets (locators / rotators / PickOne handles) that Hammer draws in-viewport.

Preview-only — nothing here changes how ``.vsmart`` files are authored or saved.

Modules:
    expression          -- safe evaluator for the SmartProp expression language.
    context             -- EvalContext: resolves any value form to a number / vector.
    variables           -- builds the variable name -> typed-default map from a document.
    modifier_evaluator  -- sequential modifier evaluation and widget extraction.
    process             -- extracts widget display specs from element data.
"""

from hammer5tools_gui.editors.smartprop_editor.viewport_3d.engine.expression import (
    evaluate_expression, EvalError,
)
from hammer5tools_gui.editors.smartprop_editor.viewport_3d.engine.context import EvalContext
from hammer5tools_gui.editors.smartprop_editor.viewport_3d.engine.variables import (
    build_variable_map, build_variable_map_from_raw, coerce_value,
)
from hammer5tools_gui.editors.smartprop_editor.viewport_3d.engine.modifier_evaluator import (
    evaluate_element_modifiers, evaluate_single_modifier, resolve_color,
)
from hammer5tools_gui.editors.smartprop_editor.viewport_3d.engine.process import (
    extract_widget_specs,
)

__all__ = [
    "evaluate_expression",
    "EvalError",
    "EvalContext",
    "build_variable_map",
    "build_variable_map_from_raw",
    "coerce_value",
    "evaluate_element_modifiers",
    "evaluate_single_modifier",
    "resolve_color",
    "extract_widget_specs",
]
