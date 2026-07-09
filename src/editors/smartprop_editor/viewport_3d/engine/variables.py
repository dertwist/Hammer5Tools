"""
Build the variable name -> typed default-value map that feeds ``EvalContext``.

Variables live as ``VariableFrame`` widgets in the variables panel; the document
exposes them via ``get_variables(layout, only_names=False)`` which returns
``{index: [name, var_class, var_value, visible, display_name]}`` where
``var_value`` is a dict carrying ``default`` (plus min/max/model/id).  See
variables_viewport.py / document.py.

Canonical ``var_class`` strings come from variable_frame.py:
``Int, Float, Bool, Color, Vector2D, Vector3D, Vector4D, Angles, String,
MaterialGroup, Material, Model`` and the enum types.
"""


def build_variable_map(document):
    """Read the document's variables and return name -> typed default value.

    Never raises; returns ``{}`` if the variables panel is unavailable.
    """
    try:
        layout = document.variable_viewport.ui.variables_scrollArea
        raw = document.get_variables(layout, only_names=False)
    except Exception:
        return {}
    return build_variable_map_from_raw(raw)


def build_variable_map_from_raw(raw):
    """Build the map from a ``get_variables(only_names=False)`` result dict."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for entry in raw.values():
        if not entry or len(entry) < 3:
            continue
        name, var_class, var_value = entry[0], entry[1], entry[2]
        if not name or not isinstance(name, str):
            continue
        # Category boundary markers are layout sugar, not real variables.
        if name.startswith("hammer5tools_category_"):
            continue
        default = var_value.get("default") if isinstance(var_value, dict) else None
        out[name] = coerce_value(var_class, default)
    return out


def coerce_value(var_class, default):
    """Coerce a stored default to the natural Python type for its class."""
    c = (var_class or "").lower()

    if default is None:
        # Zeroed defaults so a bound-but-unset variable still resolves cleanly.
        if "bool" in c:
            return False
        if c == "int":
            return 0
        if c == "float":
            return 0.0
        if "vector2d" in c:
            return [0.0, 0.0]
        if "vector3d" in c or c == "angles":
            return [0.0, 0.0, 0.0]
        if "vector4d" in c or "color" in c:
            return [0.0, 0.0, 0.0, 0.0]
        return None

    try:
        if "bool" in c:
            if isinstance(default, str):
                return default.strip().lower() in ("1", "true", "yes")
            return bool(default)
        if c == "int":
            return int(float(default))
        if c == "float":
            return float(default)
        if "vector" in c or "color" in c or c == "angles":
            return _to_list(default)
    except (ValueError, TypeError):
        return default
    # String / enum / asset types pass through unchanged.
    return default


def _to_list(v):
    if isinstance(v, (list, tuple)):
        return [_safe_float(x) for x in v]
    if isinstance(v, dict) and "m_Components" in v:
        return [_safe_float(x) for x in v["m_Components"]]
    if isinstance(v, str):
        import re
        out = []
        for part in re.split(r"[,\s]+", v.strip()):
            if part == "":
                continue
            try:
                out.append(float(part))
            except ValueError:
                pass
        return out
    try:
        return [float(v)]
    except (ValueError, TypeError):
        return []


def _safe_float(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0
