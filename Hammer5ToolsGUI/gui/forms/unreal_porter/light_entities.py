"""
Unreal light / sky / reflection-capture actors -> CS2 map entity property sets.

The DEFAULTS below are the complete key/value sets Hammer writes for a freshly
placed entity of each class, lifted verbatim from a hand-authored vmap. Every
converted actor starts from its class default and overwrites only the keys we
can actually derive from Unreal, so a converted light opens in Hammer with the
same field set as one placed by hand — no missing keys, no invented ones.

ue_actor_to_entity() is the whole mapping and is pure data in / data out (no Qt,
no DMX), so the photometric and axis conventions are pinned by demo() below.

Photometry is the weak joint: Unreal and Source 2 do not agree on what a light's
intensity number means, and Unreal's "Unitless" mode has no defensible
conversion at all. Everything lands in lumens (see _to_lumens) and every light
keeps its `brightnessscale` key, which is the knob an artist turns in Hammer
when a converted scene comes out too hot or too dark.
"""

# Fields every point entity carries. Hammer writes these on any class.
_COMMON = {
    "vscripts": "",
    "targetname": "",
    "parentname": "",
    "parentAttachmentName": "",
    "useLocalOffset": "0",
    "local.origin": "",
    "local.angles": "",
    "local.scales": "",
}

# The light-style output block, identical across every light_* class.
_LIGHT_STYLE = {
    "light_style": "",
    "light_style_output_event0": "event_0",
    "light_style_output_event1": "event_1",
    "light_style_output_event2": "event_2",
    "light_style_output_event3": "event_3",
    "light_style_target0": "",
    "light_style_target1": "",
    "light_style_target2": "",
    "light_style_target3": "",
}

# Shared by light_omni2 / light_rect / light_barn.
_LIGHT_COMMON = {
    "clientSideEntity": "1",
    "brightness_units": "1",
    "brightness": "0",
    "brightness_legacy": "1",
    "enabled": "1",
    "directlight": "1",
    "colormode": "1",
    "color": "255 255 255",
    "colortemperature": "6600",
    "range": "256.0",
    "skirt": "0.1",
    "bouncelight": "-1",
    "bouncescale": "1.0",
    "bakespeculartocubemaps": "0",
    "bakespeculartocubemaps_scale": "1.0",
    "minroughness": "0",
    "castshadows": "2",
    "shadowmapsize": "-1",
    "shadowpriority": "-1",
    "pvs_modify_entity": "0",
    "shadowfade_size_start": ".10",
    "shadowfade_size_end": ".05",
    "rendertocubemaps": "1",
    "brightnessscale": "1.0",
    "fade_size_start": ".05",
    "fade_size_end": ".025",
    "transmit_always": "0",
}


def _entity(*parts):
    out = {}
    for p in parts:
        out.update(p)
    return out


DEFAULTS = {
    "light_omni2": _entity(_COMMON, _LIGHT_COMMON, {
        "brightness_candelas": "80",
        "brightness_nits": "9816",
        "brightness_lumens": "1000",
        "shape": "0",
        "size_params": "2.0 24.0 0.15",
        "outer_angle": "180.0",
        "inner_angle": "180.0",
        "lightcookie": "",
        "showlight": "0",
    }, _LIGHT_STYLE),

    "light_rect": _entity(_COMMON, _LIGHT_COMMON, {
        "brightness_candelas": "80",
        "brightness_nits": "120",
        "brightness_lumens": "250",
        "shape": "0",
        "size_params": "16.0 16.0 0.15",
        "showlight": "0",
    }, _LIGHT_STYLE),

    "light_barn": _entity(_COMMON, _LIGHT_COMMON, {
        "brightness_lumens": "224",
        "skirt_near": "0.05",
        "luminaire_shape": "1",
        "luminaire_size": "4",
        "luminaire_anisotropy": "0",
        "size_params": "16.0 16.0 0.0625",
        "shape": "1",
        "soft_x": "0.25",
        "soft_y": "0.25",
        "shear": "0.0 0.0",
        "lightcookie": "",
        "bakespeculartocubemaps_size": "6.0 6.0 0.0",
        "forceshadowsenabled": "0",
    }, _LIGHT_STYLE),

    "light_environment": {
        "enabled": "1",
        "color": "255 255 255",
        "brightness": "1.0",
        "directlight": "3",
        "rendertocubemaps": "1",
        "bouncescale": "1.0",
        "castshadows": "1",
        "angulardiameter": "1.0",
        "shadowpriority": "-1",
        "nearclipplane": "1",
        "skycolor": "255 255 255",
        "skyintensity": "1.0",
        "skytexture": "",
        "skytexturescale": "1.0",
        "skybouncescale": "1.0",
        "skyambientbounce": "0 0 0",
        "brightnessscale": "1.0",
        "style": "0",
        "pattern": "",
        "clientSideEntity": "1",
        "baked_light_indexing": "1",
        "allow_sst_generation": "0",
        "minroughness": "0",
        "ambient_occlusion_proxy_override": "0",
        "ambient_occlusion_proxy_position_0": "0 0 0",
        "ambient_occlusion_proxy_position_1": "0 0 0",
        "ambient_occlusion_proxy_position_2": "0 0 0",
        "ambient_occlusion_proxy_position_3": "0 0 0",
        "ambient_occlusion_proxy_cone_angle_0": "0.3",
        "ambient_occlusion_proxy_cone_angle_1": "0.3",
        "ambient_occlusion_proxy_cone_angle_2": "0.3",
        "ambient_occlusion_proxy_cone_angle_3": "0.3",
        "ambient_occlusion_proxy_strength_0": "0.5",
        "ambient_occlusion_proxy_strength_1": "0.5",
        "ambient_occlusion_proxy_strength_2": "0.5",
        "ambient_occlusion_proxy_strength_3": "0.5",
        "ambient_occlusion_proxy_ambient_strength": "1.0",
        "fademindist": "",
        "fademaxdist": "",
    },

    "env_sky": _entity(_COMMON, {
        "StartDisabled": "0",
        "skyname": "materials/dev/default_sky.vmat",
        "tint_color": "255 255 255",
        "brightnessscale": "1.0",
    }),

    "env_combined_light_probe_volume": _entity(_COMMON, {
        "StartDisabled": "0",
        "cubemaptexture": "",
        "bakefarz": "4096.0",
        "box_mins": "-72 -72 -72",
        "box_maxs": "72 72 72",
        "voxel_size": "48.0",
        "flood_fill": "1",
        "voxelize": "1",
        "indoor_outdoor_level": "0",
        "edge_fade_dists": "0 0 0",
        "clientSideEntity": "1",
    }),
}

# Which bridge componentType becomes which CS2 class.
CLASS_FOR_COMPONENT = {
    "PointLight": "light_omni2",
    "SpotLight": "light_omni2",
    "RectLight": "light_rect",
    "DirectionalLight": "light_environment",
    "SkyLight": "env_sky",
    "ReflectionCapture": "env_combined_light_probe_volume",
}

LIGHT_COMPONENTS = ("PointLight", "SpotLight", "RectLight", "DirectionalLight")
SKY_COMPONENTS = ("SkyLight",)
CUBEMAP_COMPONENTS = ("ReflectionCapture",)

# Unreal's default DirectionalLight is 10 lux; light_environment's default
# brightness is 1.0. Normalizing by this makes an untouched UE sun convert to an
# untouched Hammer sun instead of a 10x one.
_UE_DEFAULT_LUX = 10.0

# ponytail: Unreal's "Unitless" intensity has no physical definition to convert
# from, so it is passed through as lumens unchanged. If converted scenes come
# out consistently off, this is the single number to calibrate (or turn
# brightnessscale in Hammer, which is per-light and needs no re-convert).
_UNITLESS_TO_LUMENS = 1.0

_FOUR_PI = 12.566370614359172


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _num(value):
    """Format a float the way Hammer writes its entity values."""
    return f"{round(float(value), 4):g}"


def _to_lumens(light, is_spot):
    """Unreal intensity (in whatever units the component declares) -> lumens.

    Candelas are a per-steradian quantity, so the cone the light actually fills
    is what turns them back into a total flux: the full sphere for a point or
    rect light, the spot's own solid angle otherwise. Getting this wrong makes
    narrow spots read as blindingly bright.
    """
    import math

    intensity = _f(light.get("intensity"))
    units = str(light.get("intensityUnits") or "Unitless")
    if units.endswith("Lumens"):
        return intensity
    if units.endswith("Candelas"):
        if is_spot:
            outer = math.radians(max(_f(light.get("outerConeAngle"), 44.0), 1.0))
            return intensity * 2.0 * math.pi * (1.0 - math.cos(outer))
        return intensity * _FOUR_PI
    return intensity * _UNITLESS_TO_LUMENS


def _apply_color(props, light):
    color = light.get("color") or {}
    r, g, b = (int(_f(color.get(c), 255.0)) for c in ("r", "g", "b"))
    props["color"] = f"{r} {g} {b}"
    if light.get("useTemperature"):
        props["colortemperature"] = _num(_f(light.get("temperature"), 6600.0))
    # colormode 1 selects the temperature field, 0 the colour picker. Both
    # values are always written, so a wrong guess here is visible and harmless.
    props["colormode"] = "1" if light.get("useTemperature") else "0"


def ue_actor_to_entity(actor: dict, unit_scale: float = 1.0):
    """One bridge scene actor -> (classname, entity property dict), or None.

    `actor` is a dump-scene entry whose componentType is one of
    CLASS_FOR_COMPONENT's keys and which carries a "light" sub-object of raw
    Unreal component properties. Distances are multiplied by unit_scale, the
    same factor the placement transform uses, so a light's range keeps matching
    the geometry it lights.
    """
    comp = actor.get("componentType", "")
    classname = CLASS_FOR_COMPONENT.get(comp)
    if not classname:
        return None

    # classname is a property of the entity, not just the template's key —
    # without it Hammer loads the node with every field set and no class.
    props = {"classname": classname, **DEFAULTS[classname]}
    light = actor.get("light") or {}

    if comp in ("PointLight", "SpotLight", "RectLight"):
        is_spot = comp == "SpotLight"
        _apply_color(props, light)
        props["brightness_lumens"] = _num(_to_lumens(light, is_spot))
        props["brightness_units"] = "1"          # lumens
        props["castshadows"] = "2" if light.get("castShadows", True) else "0"
        radius = _f(light.get("attenuationRadius"))
        if radius:
            props["range"] = _num(radius * unit_scale)
        if is_spot:
            # Unreal cone angles are half-angles, and so are Hammer's.
            props["outer_angle"] = _num(_f(light.get("outerConeAngle"), 44.0))
            props["inner_angle"] = _num(_f(light.get("innerConeAngle"), 0.0))
        if comp == "RectLight":
            w = _f(light.get("sourceWidth"), 64.0) * unit_scale
            h = _f(light.get("sourceHeight"), 64.0) * unit_scale
            # Third component is the emitter's thickness; Unreal has no
            # equivalent, so the class default is kept.
            props["size_params"] = f"{_num(w)} {_num(h)} 0.15"
        else:
            src = _f(light.get("sourceRadius")) * unit_scale
            if src:
                props["size_params"] = f"{_num(src)} 24.0 0.15"

    elif comp == "DirectionalLight":
        _apply_color(props, light)
        props["brightness"] = _num(_f(light.get("intensity"), _UE_DEFAULT_LUX) / _UE_DEFAULT_LUX)
        props["castshadows"] = "1" if light.get("castShadows", True) else "0"
        angle = _f(light.get("sourceAngle"))
        if angle:
            props["angulardiameter"] = _num(angle)

    elif comp == "SkyLight":
        props["targetname"] = "sky"
        intensity = _f(light.get("intensity"), 1.0)
        props["brightnessscale"] = _num(intensity if intensity else 1.0)

    elif comp == "ReflectionCapture":
        extent = light.get("boxExtent")
        if extent:
            hx = _f(extent.get("x"), 72.0) * unit_scale
            hy = _f(extent.get("y"), 72.0) * unit_scale
            hz = _f(extent.get("z"), 72.0) * unit_scale
        else:
            r = (_f(light.get("influenceRadius"), 72.0) or 72.0) * unit_scale
            hx = hy = hz = r
        props["box_mins"] = f"{_num(-hx)} {_num(-hy)} {_num(-hz)}"
        props["box_maxs"] = f"{_num(hx)} {_num(hy)} {_num(hz)}"

    return classname, props


def demo():
    import math

    # Every class default must be complete: a missing key is a field Hammer
    # shows blank, which is how a converted light silently loses its shadows.
    for cls, props in DEFAULTS.items():
        assert props, cls
        assert all(isinstance(v, str) for v in props.values()), cls
    for cls in CLASS_FOR_COMPONENT.values():
        assert cls in DEFAULTS, cls

    # Defaults are copied, never shared — one converted light must not be able
    # to edit the template every later light starts from.
    a = ue_actor_to_entity({"componentType": "PointLight", "light": {}})[1]
    a["color"] = "0 0 0"
    assert DEFAULTS["light_omni2"]["color"] == "255 255 255"

    # Every emitted entity carries its own classname. Without it Hammer opens
    # the map with a node that has all its fields and no class at all, which is
    # not distinguishable from a broken entity.
    for comp in CLASS_FOR_COMPONENT:
        cls, props = ue_actor_to_entity({"componentType": comp, "light": {}})
        assert props.get("classname") == cls, (comp, props.get("classname"))

    # Candelas -> lumens: a point light fills the whole sphere...
    cls, p = ue_actor_to_entity({
        "componentType": "PointLight",
        "light": {"intensity": 8.0, "intensityUnits": "Candelas", "attenuationRadius": 1000.0},
    })
    assert cls == "light_omni2"
    assert abs(float(p["brightness_lumens"]) - 8.0 * _FOUR_PI) < 0.01, p["brightness_lumens"]
    assert p["range"] == "1000"

    # ...a spot only its own cone, which is far less flux for the same candelas.
    _, spot = ue_actor_to_entity({
        "componentType": "SpotLight",
        "light": {"intensity": 8.0, "intensityUnits": "Candelas",
                  "outerConeAngle": 30.0, "innerConeAngle": 10.0},
    })
    want = 8.0 * 2.0 * math.pi * (1.0 - math.cos(math.radians(30.0)))
    assert abs(float(spot["brightness_lumens"]) - want) < 0.01, spot["brightness_lumens"]
    assert float(spot["brightness_lumens"]) < float(p["brightness_lumens"])
    assert spot["outer_angle"] == "30" and spot["inner_angle"] == "10"

    # Lumens pass through untouched.
    _, lm = ue_actor_to_entity({
        "componentType": "PointLight",
        "light": {"intensity": 1700.0, "intensityUnits": "Lumens"},
    })
    assert lm["brightness_lumens"] == "1700"

    # unit_scale reaches every distance, not just the placement.
    _, inch = ue_actor_to_entity({
        "componentType": "RectLight",
        "light": {"attenuationRadius": 254.0, "sourceWidth": 254.0, "sourceHeight": 127.0},
    }, unit_scale=1.0 / 2.54)
    assert inch["range"] == "100", inch["range"]
    assert inch["size_params"] == "100 50 0.15", inch["size_params"]

    # Colour and temperature are both always written; only the mode switches.
    _, col = ue_actor_to_entity({
        "componentType": "PointLight",
        "light": {"color": {"r": 255, "g": 128, "b": 0}},
    })
    assert col["color"] == "255 128 0" and col["colormode"] == "0"
    _, tmp = ue_actor_to_entity({
        "componentType": "PointLight",
        "light": {"useTemperature": True, "temperature": 3200.0},
    })
    assert tmp["colormode"] == "1" and tmp["colortemperature"] == "3200"

    # An untouched UE sun converts to an untouched Hammer sun.
    _, sun = ue_actor_to_entity({
        "componentType": "DirectionalLight",
        "light": {"intensity": _UE_DEFAULT_LUX},
    })
    assert sun["brightness"] == "1", sun["brightness"]

    # A reflection capture's radius becomes a box centred on the actor.
    _, cube = ue_actor_to_entity({
        "componentType": "ReflectionCapture", "light": {"influenceRadius": 300.0},
    })
    assert cube["box_mins"] == "-300 -300 -300" and cube["box_maxs"] == "300 300 300"

    # The sky entity must be named, or env_cubemap_fog's default reference to
    # "sky" resolves to nothing.
    _, sky = ue_actor_to_entity({"componentType": "SkyLight", "light": {"intensity": 2.0}})
    assert sky["targetname"] == "sky" and sky["brightnessscale"] == "2"

    assert ue_actor_to_entity({"componentType": "StaticMeshComponent"}) is None
    print("ok")


if __name__ == "__main__":
    demo()
