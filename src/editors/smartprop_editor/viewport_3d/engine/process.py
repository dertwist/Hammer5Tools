"""
Widget extraction for the SmartProp preview.

Given an element's data dict and an ``EvalContext``, produce the display *specs*
for the Hammer editing widgets it defines:

* ``CreateLocator``  operation  -> ``locator``  (RGB axis cross)
* ``CreateRotator``  operation  -> ``rotator``  (radius circle + handle)
* ``PickOne``        element     -> ``pickone``  (handle marker)

Specs are plain dicts with *local* parameters already resolved to numbers
(offset in the element's local space, radius, axis, colour, …).  The render area
places each spec into world space using the element's world matrix and draws it
with the gizmo shader.  This module has no Qt/OpenGL/numpy dependency so it stays
unit-testable.
"""


def _resolve_color(value, ctx, default):
    """Resolve a colour field (None / [r,g,b] 0-255 or 0-1 / binding) to 0-1 rgb."""
    if value is None:
        return list(default)
    vec = ctx.resolve_vector(value, default)
    rgb = [vec[i] if i < len(vec) else 0.0 for i in range(3)]
    # Hammer stores colours as 0-255 ints; normalize if they look like bytes.
    if any(c > 1.0 for c in rgb):
        rgb = [c / 255.0 for c in rgb]
    return [max(0.0, min(1.0, c)) for c in rgb]


def extract_widget_specs(data, ctx):
    """Return a list of widget spec dicts for ``data`` (never raises)."""
    specs = []
    if not isinstance(data, dict):
        return specs

    try:
        cls = data.get("_class", "")

        if cls == "CSmartPropElement_PickOne":
            # Valve's format uses the triple-f "m_vHandleOfffset"; the project's
            # objects.py used the two-f spelling — accept either.
            handle_offset = data.get("m_vHandleOfffset")
            if handle_offset is None:
                handle_offset = data.get("m_vHandleOffset")
            specs.append({
                "type": "pickone",
                "offset": ctx.resolve_vector(handle_offset, [0.0, 0.0, 0.0]),
                "size": max(1.0, ctx.resolve_scalar(data.get("m_HandleSize"), 8.0)),
                "color": _resolve_color(data.get("m_HandleColor"), ctx, [0.6, 0.6, 0.6]),
                "shape": str(data.get("m_HandleShape") or "SQUARE").upper(),
                "name": str(data.get("m_OutputChoiceVariableName") or ""),
            })

        for mod in data.get("m_Modifiers") or []:
            if not isinstance(mod, dict):
                continue
            if mod.get("m_bEnabled", True) is False:
                continue
            mcls = mod.get("_class", "")
            if mcls == "CSmartPropOperation_CreateLocator":
                specs.append({
                    "type": "locator",
                    "offset": ctx.resolve_vector(mod.get("m_vOffset"), [0.0, 0.0, 0.0]),
                    "scale": max(0.01, ctx.resolve_scalar(mod.get("m_flDisplayScale"), 1.0)),
                    "name": str(mod.get("m_LocatorName") or ""),
                })
            elif mcls == "CSmartPropOperation_CreateRotator":
                specs.append({
                    "type": "rotator",
                    "offset": ctx.resolve_vector(mod.get("m_vOffset"), [0.0, 0.0, 0.0]),
                    "axis": ctx.resolve_vector(mod.get("m_vRotationAxis"), [0.0, 0.0, 1.0]),
                    "radius": max(1.0, ctx.resolve_scalar(mod.get("m_flDisplayRadius"), 16.0)),
                    "angle": ctx.resolve_scalar(mod.get("m_flInitialAngle"), 0.0),
                    "color": _resolve_color(mod.get("m_DisplayColor"), ctx, [0.85, 0.85, 0.2]),
                    "name": str(mod.get("m_Name") or ""),
                })
    except Exception:
        # Widget extraction must never break the viewport rebuild.
        return specs

    return specs
