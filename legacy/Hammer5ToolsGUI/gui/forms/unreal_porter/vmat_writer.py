"""Source 2 .vmat writer — thin schema-driven wrapper.

All shader layout (parameter names, section ordering, defaults, feature-flag
gating, blend modes, UnusedVariables policy) lives in shader_schemas. This
module just resolves the schema for the requested shader, builds an authoring
context from the caller's slots/overrides/flags, and writes the formatted body.

Preserved public signature (callers in material_converter/converter/vmdl_writer):
  write_vmat(output_path, slots, shader, color_tint, roughness_scale,
             metalness_scale, extra_params, alpha_test_ref, render_backfaces,
             extra_scalars, extra_vectors)

New kwargs:
  feature_flags  — {F_*: "0"/"1"} from the Feature Inspector (now wired through)
  blend_mode     — int F_BLEND_MODE value for static_overlay (0=default)
"""

import os

from gui.common import app_version

from .shader_schemas import get_shader_schema, format_vmat, Ctx


def write_vmat(
    output_path: str,
    slots: dict,
    shader: str = "csgo_environment.vfx",
    color_tint=None,
    roughness_scale: float = 1.0,
    metalness_scale: float = 1.0,
    extra_params: dict = None,
    alpha_test_ref: float = None,
    render_backfaces: bool = False,
    extra_scalars: dict = None,
    extra_vectors: dict = None,
    feature_flags: dict = None,
    blend_mode: int = 0,
):
    """Write a Source 2 .vmat for the given shader and slot bindings.

    slots = {
        "color": "materials/path/name_color.tga",
        "normal": "materials/path/name_normal.tga",
        "rough": "materials/path/name_rough.tga",
        "metal": "materials/path/name_metal.tga" or None,
        "ao": "materials/path/name_ao.tga",
        "height": "materials/path/name_height.tga" or None,
        "trans"/"opacity": "materials/path/name_trans.tga" or None,
    }

    feature_flags: {F_*: "0"/"1"} from the Feature Inspector — these now reach
    the writer and toggle sections (F_LIT, F_RENDER_BACKFACES, F_ALPHA_TEST,
    F_DEPTH_FEATHER, F_WETNESS, ...). Previously this output was discarded.

    blend_mode: F_BLEND_MODE int for static_overlay (0=Default, 1=Translucent,
    2=Alpha Test, 3=Mod2x, 4=Additive, 5=Multiply, 6=ModThenAdd).

    extra_scalars ({g_flName: float}) / extra_vectors ({g_vName: (r,g,b)}) are
    typed authoring overrides that take precedence over schema defaults.
    extra_params is the legacy stringly-typed channel (quoted verbatim); it is
    folded into feature_flags for F_* keys and into values for g_*/Texture* keys.
    """
    schema = get_shader_schema(shader)
    if schema is None:
        # Unknown shader — fall back to environment so we never crash a conversion.
        schema = get_shader_schema("csgo_environment.vfx")

    flags = dict(feature_flags or {})
    values = {}

    # color_tint -> g_vColorTint
    if color_tint and len(color_tint) >= 3:
        values["g_vColorTint"] = (color_tint[0], color_tint[1], color_tint[2])

    # scale params (environment family reads these via default_fn for unbound
    # metalness/roughness textures)
    values["g_flRoughnessScale"] = roughness_scale
    values["g_flMetalnessScale"] = metalness_scale

    # typed scalar/vector overrides
    if extra_scalars:
        values.update(extra_scalars)
    if extra_vectors:
        for k, v in extra_vectors.items():
            if v and len(v) >= 3:
                values[k] = (v[0], v[1], v[2])

    # alpha-test reference
    if alpha_test_ref is not None:
        values["g_flAlphaTestReference"] = alpha_test_ref
        flags.setdefault("F_ALPHA_TEST", "1")

    if render_backfaces:
        flags.setdefault("F_RENDER_BACKFACES", "1")

    # legacy extra_params: route F_* to flags, everything else to values
    if extra_params:
        for k, v in extra_params.items():
            if k.startswith("F_"):
                flags.setdefault(k, str(v))
            else:
                values.setdefault(k, v)

    # 'trans' slot alias -> 'opacity' (environment schema uses 'trans' slot name;
    # static_overlay uses 'opacity'). Bind both so either resolves.
    resolved_slots = dict(slots or {})
    if resolved_slots.get("trans") and not resolved_slots.get("opacity"):
        resolved_slots["opacity"] = resolved_slots["trans"]
    if resolved_slots.get("opacity") and not resolved_slots.get("trans"):
        resolved_slots["trans"] = resolved_slots["opacity"]

    if schema.shader != "csgo_static_overlay.vfx" and (resolved_slots.get("trans") or resolved_slots.get("opacity")) and "F_ALPHA_TEST" not in flags:
        flags["F_ALPHA_TEST"] = "1"
        values.setdefault("g_flAlphaTestReference", 0.5)

    ctx = Ctx(flags=flags, blend_mode=blend_mode, slots=resolved_slots, values=values)
    body = format_vmat(schema, ctx)

    content = f"// Generated with Hammer 5 Tools {app_version}\n\nLayer0\n{{\n{body}\n}}"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    # newline=None lets the platform translate \n -> \r\n on Windows, matching
    # Hammer's CRLF authoring format.
    with open(output_path, "w", encoding="utf-8", newline=None) as f:
        f.write(content)
