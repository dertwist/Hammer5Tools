"""
EvalContext — resolves any SmartProp value form to a concrete number / vector.

Element fields come in several shapes (see property/float.py, property/vector3d.py):

    42.0                                    literal number
    "3.5"                                   numeric string
    {"m_SourceName": "my_var"}              variable binding
    {"m_Expression": "InstanceIndex()*32"}  expression binding
    {"m_Components": [cx, cy, cz]}          vector, each component any of the above
    {"m_SourceName": "my_vec"}              whole-vector variable binding
    [x, y, z]                               plain list

The old viewport (`render_area._get_vector`) only handled literals and collapsed
variable/expression bindings to 0.  ``EvalContext`` is the single place that turns
every form into a value, delegating expression strings to ``evaluate_expression``.
"""

import random

from src.editors.smartprop_editor.viewport_3d.engine.expression import evaluate_expression


class EvalContext:
    def __init__(self, variables=None, instance_index=0, instance_count=1,
                 seed=0, overrides=None):
        # name -> typed value (bool / int / float / list / str)
        self.variables = dict(variables) if variables else {}
        # live preview overrides (reserved for a future editable panel)
        self.overrides = dict(overrides) if overrides else {}
        self.instance_index = int(instance_index)
        self.instance_count = int(instance_count)
        self.rng = random.Random(seed)
        # Source 2 resolves variable names case-insensitively — real files bind
        # the same variable as e.g. "Sizer_X" and "sizer_x" — so keep lowercase
        # maps for a fallback lookup.
        self._lower_vars = self._build_lower(self.variables)
        self._lower_overrides = self._build_lower(self.overrides)

    @staticmethod
    def _build_lower(d):
        return {k.lower(): v for k, v in d.items() if isinstance(k, str)}

    # -- variable lookup ---------------------------------------------------
    def var(self, name):
        if not isinstance(name, str):
            return None
        if name in self.overrides:
            return self.overrides[name]
        if name in self.variables:
            return self.variables[name]
        low = name.lower()
        if low in self._lower_overrides:
            return self._lower_overrides[low]
        return self._lower_vars.get(low)

    def set_override(self, name, value):
        self.overrides[name] = value
        if isinstance(name, str):
            self._lower_overrides[name.lower()] = value

    # -- scalar ------------------------------------------------------------
    def resolve_scalar(self, value, default=0.0):
        """Resolve any scalar value form to a float."""
        if value is None:
            return float(default)
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            s = value.strip()
            if s == "":
                return float(default)
            try:
                return float(s)
            except ValueError:
                return evaluate_expression(s, self, default)
        if isinstance(value, dict):
            if "m_Expression" in value:
                return evaluate_expression(value["m_Expression"], self, default)
            if "m_SourceName" in value:
                return self._var_scalar(value["m_SourceName"], default)
            if "m_Components" in value:
                comps = value["m_Components"]
                return self.resolve_scalar(comps[0], default) if comps else float(default)
            return float(default)
        if isinstance(value, (list, tuple)):
            return self.resolve_scalar(value[0], default) if value else float(default)
        return float(default)

    def _var_scalar(self, name, default):
        v = self.var(name)
        if v is None:
            return float(default)
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, (list, tuple)):
            return float(v[0]) if v else float(default)
        try:
            return float(v)
        except (ValueError, TypeError):
            return evaluate_expression(str(v), self, default)

    # -- string ------------------------------------------------------------
    def resolve_string(self, value, default=""):
        """Resolve any string value form to a plain string.

        String fields (most importantly ``m_sModelName``) can be a literal path,
        a variable binding (``{"m_SourceName": "ModelName"}``) that must read the
        variable's default, or an expression whose text is the literal path.
        """
        if value is None:
            return default
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, dict):
            if "m_SourceName" in value:
                return self._var_string(value["m_SourceName"], default)
            if "m_Expression" in value:
                # String fields store the literal path as the expression text;
                # the numeric expression evaluator can't produce a string, so
                # hand the text back verbatim (empty falls back to default).
                expr = value["m_Expression"]
                return str(expr) if expr not in (None, "") else default
            return default
        try:
            return str(value)
        except Exception:
            return default

    def _var_string(self, name, default):
        v = self.var(name)
        if v is None:
            return default
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            return v
        return str(v)

    # -- vector ------------------------------------------------------------
    def resolve_vector(self, value, default=None):
        """Resolve any vector value form to ``[x, y, z]`` floats."""
        d = list(default) if default is not None else [0.0, 0.0, 0.0]
        while len(d) < 3:
            d.append(0.0)

        if value is None:
            return [float(x) for x in d[:3]]
        if isinstance(value, (list, tuple)):
            out = []
            for i in range(3):
                comp = value[i] if i < len(value) else d[i]
                out.append(self.resolve_scalar(comp, d[i]))
            return out
        if isinstance(value, dict):
            if "m_Components" in value:
                return self.resolve_vector(value["m_Components"], d)
            if "m_SourceName" in value:
                return self._var_vector(value["m_SourceName"], d)
            if "m_Expression" in value:
                s = evaluate_expression(value["m_Expression"], self, 0.0)
                return [s, s, s]
            return [float(x) for x in d[:3]]
        if isinstance(value, (int, float, bool)):
            s = self.resolve_scalar(value)
            return [s, s, s]
        # Objects exposing X/Y/Z or Pitch/Yaw/Roll (kv3 vector wrappers).
        for attrs in (("X", "Y", "Z"), ("Pitch", "Yaw", "Roll")):
            if all(hasattr(value, a) for a in attrs):
                try:
                    return [float(getattr(value, a)) for a in attrs]
                except (ValueError, TypeError):
                    return [float(x) for x in d[:3]]
        return [float(x) for x in d[:3]]

    def _var_vector(self, name, d):
        v = self.var(name)
        if isinstance(v, (list, tuple)):
            return [float(v[i]) if i < len(v) else d[i] for i in range(3)]
        if isinstance(v, (int, float, bool)):
            s = float(v)
            return [s, s, s]
        return [float(x) for x in d[:3]]
