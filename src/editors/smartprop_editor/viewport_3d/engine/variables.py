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
    """Build the map from a ``get_variables(only_names=False)`` result dict.

    A variable's ``default`` is usually a literal, but the editor also lets it be
    a binding to another variable (``{"m_SourceName": ...}``) or an expression
    (``{"m_Expression": ...}``) — the same value forms element fields use.  Those
    bindings are resolved here so the preview reflects them; literals that carry
    ``m_Components`` (whole-vector defaults) stay literal.
    """
    out = {}
    if not isinstance(raw, dict):
        return out

    bound = {}  # name -> (var_class, binding dict) resolved in a second pass
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
        if _is_binding(default):
            # Seed with a typed zero so a referencing variable still resolves
            # cleanly before its source has been evaluated.
            bound[name] = (var_class, default)
            out[name] = coerce_value(var_class, None)
        else:
            out[name] = coerce_value(var_class, default)

    if bound:
        _resolve_bound_defaults(out, bound)
    return out


def _is_binding(default):
    """True when a default is a variable/expression binding rather than a literal."""
    return isinstance(default, dict) and (
        "m_SourceName" in default or "m_Expression" in default
    )


def _resolve_bound_defaults(values, bound):
    """Resolve variable/expression default bindings against the value map.

    Bindings may chain (A's default references B, whose default references C), so
    we iterate until nothing changes.  The pass count is bounded by the number of
    bindings, which also makes reference cycles terminate (they settle on the
    seeded zero values instead of looping forever).
    """
    # Imported lazily to avoid any import-order coupling with the engine package.
    from src.editors.smartprop_editor.viewport_3d.engine.context import EvalContext

    for _ in range(len(bound) + 1):
        ctx = EvalContext(variables=values)
        changed = False
        for name, (var_class, binding) in bound.items():
            resolved = _resolve_binding(var_class, binding, ctx)
            if resolved != values.get(name):
                values[name] = resolved
                changed = True
        if not changed:
            break


def _resolve_binding(var_class, binding, ctx):
    """Resolve one binding to the natural typed value for ``var_class``."""
    c = (var_class or "").lower()
    if "vector" in c or "color" in c or c == "angles":
        zero = coerce_value(var_class, None)
        return ctx.resolve_vector(binding, zero)
    # Scalar / bool / string / enum. A direct variable reference adopts the
    # referenced variable's already-typed value (keeps strings as strings);
    # expressions and unresolved references fall back to numeric evaluation.
    if "m_SourceName" in binding and "m_Expression" not in binding:
        ref = ctx.var(binding["m_SourceName"])
        if ref is not None:
            return coerce_value(var_class, ref)
    return coerce_value(var_class, ctx.resolve_scalar(binding, 0.0))


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
