"""Plain-Python model behind the SmartProp editor's choices panel.

Deliberately free of any Qt import. The choices tree stores its state in the
widgets themselves, which left the same rules written out several times over:
the KV3 key aliases were read in `document._populate_choices` and
`vsmart.populate_choices`, the KV3 output was built in `vsmart.choices` and
`manual_editor._serialise_choices`, and every value editor in `choices.py`
re-parsed its raw value with its own slightly different coercion. Rules about
what a choice *is* belong here; `choices.py` renders them.

The state shape is the one the undo stack already passes around, plain dicts,
so `rename_references` can still walk it:

    [{'name': str, 'default': str, 'expanded': bool,
      'options': [{'name': str, 'expanded': bool,
                   'variables': [{'name': str, 'type': str, 'value': Any}]}]}]
"""

from __future__ import annotations

import ast

# A variable's KV3 class decides which editor renders its value. Both the bare
# spelling and the CSmartPropVariable_* class name occur in the wild.
KIND_BOOL = 'bool'
KIND_INT = 'int'
KIND_FLOAT = 'float'
KIND_COLOR = 'color'
KIND_VECTOR2D = 'vector2d'
KIND_VECTOR3D = 'vector3d'
KIND_VECTOR4D = 'vector4d'
KIND_STRING = 'string'

_KIND_BY_CLASS = {}


def _register(kind, *names):
    for name in names:
        _KIND_BY_CLASS[name] = kind
    return names


var_choice_identification_bool = _register(
    KIND_BOOL, 'boolean', 'bool', 'csmartpropvariable_bool')
var_choice_identification_int = _register(
    KIND_INT, 'integer', 'int', 'csmartpropvariable_int')
var_choice_identification_float = _register(
    KIND_FLOAT, 'float', 'csmartpropvariable_float')
var_choice_identification_color = _register(
    KIND_COLOR, 'color', 'csmartpropvariable_color')
var_choice_identification_vector2d = _register(
    KIND_VECTOR2D, 'vector2d', 'csmartpropvariable_vector2d')
var_choice_identification_vector4d = _register(
    KIND_VECTOR4D, 'vector4d', 'csmartpropvariable_vector4d')
var_choice_identification_vector3d = _register(
    KIND_VECTOR3D, 'vector3d', 'csmartpropvariable_vector3d', 'vector',
    'vector3', 'angles', 'csmartpropvariable_angles')
var_choice_identification_string = _register(
    KIND_STRING, 'string', 'csmartpropvariable_string',
    'model', 'csmartpropvariable_model',
    'material', 'csmartpropvariable_material',
    'materialgroup', 'csmartpropvariable_materialgroup',
    'scalemode', 'pickmode', 'tracenohit', 'applycolormode', 'choiceselectionmode',
    'colorselectionmode', 'orientationmode', 'coordinatespace', 'direction',
    'distributionmode', 'radiusplacementmode', 'gridplacementmode', 'gridoriginmode',
    'pathpositions', 'surfaceproperty')

# What an editor shows when it has nothing to show, and how wide the value is.
_DEFAULTS = {
    KIND_BOOL: (False, 0),
    KIND_INT: (0, 0),
    KIND_FLOAT: (0.0, 0),
    KIND_COLOR: ([255, 255, 255], 3),
    KIND_VECTOR2D: ([0.0, 0.0], 2),
    KIND_VECTOR3D: ([1.0, 1.0, 1.0], 3),
    KIND_VECTOR4D: ([0.0, 0.0, 0.0, 0.0], 4),
    KIND_STRING: ("", 0),
}

# The label an editor falls back to when the variable carries no class name.
DEFAULT_TYPE_NAME = {
    KIND_BOOL: 'Bool',
    KIND_INT: 'Int',
    KIND_FLOAT: 'Float',
    KIND_COLOR: 'Color',
    KIND_VECTOR2D: 'Vector2D',
    KIND_VECTOR3D: 'Vector3D',
    KIND_VECTOR4D: 'Vector4D',
    KIND_STRING: 'String',
}


def value_kind(var_class) -> str:
    """Which editor renders a variable of this KV3 class. Unknown -> string."""
    return _KIND_BY_CLASS.get(str(var_class or '').lower().strip(), KIND_STRING)


def parse_seq(val, default, count: int) -> list:
    """Coerce `val` to a list of exactly `count` numbers, padding from `default`."""
    if val is None:
        return list(default)
    if isinstance(val, str):
        try:
            val = ast.literal_eval(val)
        except Exception:
            return list(default)
    if not isinstance(val, (list, tuple)):
        return list(default)
    out = list(val)
    while len(out) < count:
        out.append(default[len(out)] if len(out) < len(default) else 0)
    return out[:count]


def coerce(kind, raw):
    """The value an editor of `kind` holds for `raw`, whatever `raw` arrived as."""
    default, count = _DEFAULTS[kind]
    if kind == KIND_STRING:
        return "" if raw is None else str(raw)
    if raw is None:
        return list(default) if count else default
    if kind == KIND_BOOL:
        if isinstance(raw, str):
            return raw.lower() in ('true', '1', 'yes')
        return bool(raw)
    if kind == KIND_INT:
        return to_int(raw)
    if kind == KIND_FLOAT:
        return to_float(raw)
    parsed = parse_seq(raw, default, count)
    if kind == KIND_COLOR:
        return [clamp_channel(x) for x in parsed]
    return [to_float(x) for x in parsed]


def to_int(text, default: int = 0) -> int:
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return default


def to_float(text, default: float = 0.0) -> float:
    try:
        return float(text)
    except (ValueError, TypeError):
        return default


def clamp_channel(text) -> int:
    """A colour channel, clamped to 0-255. Unreadable input reads as full."""
    try:
        return max(0, min(255, int(float(text))))
    except (ValueError, TypeError):
        return 255


def _first(mapping, *keys, default=""):
    for key in keys:
        value = mapping.get(key)
        if value:
            return value
    return default


def parse_choices(data) -> list[dict]:
    """Read a KV3 `m_Choices` list into the editor's state shape."""
    state = []
    for choice in data or []:
        options = []
        for option in choice.get("m_Options", []) or []:
            variables = []
            for variable in option.get("m_VariableValues", []) or []:
                variables.append({
                    'name': _first(
                        variable, "m_TargetName", "m_sVariableName",
                        "m_VariableName", "m_Name"),
                    'type': _first(
                        variable, "m_DataType", "m_sDataType", "m_Type"),
                    'value': variable.get("m_Value", variable.get("m_sValue", "")),
                })
            options.append({
                'name': _first(option, "m_Name", "m_sName", "m_sOptionName",
                               default="Option"),
                'expanded': False,
                'variables': variables,
            })
        state.append({
            'name': _first(choice, "m_Name", "m_sChoiceName", "m_sName",
                           default="Choice"),
            'default': choice.get("m_DefaultOption") or "",
            'expanded': False,
            'options': options,
        })
    return state


def format_choices(state) -> list[dict]:
    """Write the editor's state shape back out as KV3 `m_Choices` dicts.

    Element IDs are the caller's job -- they come from a stateful generator and
    only the on-disk writer wants them.
    """
    choices = []
    for choice in state:
        options = []
        for option in choice.get('options', []):
            options.append({
                "_class": "CSmartPropChoiceOption",
                "m_Name": option.get('name', 'Option'),
                "m_VariableValues": [
                    {
                        "m_TargetName": variable.get('name', ''),
                        "m_DataType": variable.get('type') or 'String',
                        "m_Value": variable.get('value', ''),
                    }
                    for variable in option.get('variables', [])
                ],
            })
        default = choice.get('default') or ""
        choices.append({
            "_class": "CSmartPropChoice",
            "m_Name": choice.get('name', 'Choice'),
            "m_Options": options,
            "m_DefaultOption": "" if default == "None" else default,
        })
    return choices
