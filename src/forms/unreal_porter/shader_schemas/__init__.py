"""
CS2 shader schema package — single source of truth for shader authoring names,
texture slots, feature flags, blend modes, and .vmat section layout.

The schema is hand-transcribed from Hammer's own material-editor output (.vmat)
and, where available, VRF shader reconstructions. Each ShaderSchema carries a
`verified` flag: True means it has been byte-matched against reference vmats;
False means it was carried forward from the legacy hardcoded templates and is
awaiting verification.

Public API (kept backward-compatible with the old monolithic shader_schemas.py):
  SHADERS                          — list of shader file names (UI combos)
  get_shader_schema(shader)        — ShaderSchema for a shader name
  get_slots_for_shader(...)        — valid texture slot list (+ channel-filtered)
  get_channel_slots_for_shader(...)
  validate_feature_flags(...)      — enforce FeatureRule Requires gates
  format_vmat(schema, ctx)         — generic .vmat body emitter
  Ctx                              — runtime authoring context
"""

from typing import Any, Dict, List, Optional

from .core import (
    Ctx,
    Param, Block, FeatureDef, BlendMode, ShaderSchema,
    format_vmat,
    validate_feature_flags as _validate_flags_for_schema,
    KIND_SCALAR, KIND_INT, KIND_BOOL,
    KIND_VECTOR2, KIND_VECTOR3, KIND_IVECTOR2, KIND_COLOR, KIND_TEXTURE,
)

from .static_overlay import SCHEMA as _STATIC_OVERLAY
from .effects import SCHEMA as _EFFECTS
from .environment import (
    SCHEMA as _ENVIRONMENT,
    GLASS_SCHEMA as _GLASS,
    FOLIAGE_SCHEMA as _FOLIAGE,
    CHARACTER_SCHEMA as _CHARACTER,
)
from .environment_blend import SCHEMA as _ENVIRONMENT_BLEND
from .complex import SCHEMA as _COMPLEX


# Ordered list — drives the UI shader combo boxes (master_material_list, slot_mapping).
_SCHEMAS: List[ShaderSchema] = [
    _ENVIRONMENT,
    _ENVIRONMENT_BLEND,
    _COMPLEX,
    _EFFECTS,
    _STATIC_OVERLAY,
    _FOLIAGE,
    _GLASS,
    _CHARACTER,
]

# Public list of shader file names (preserves the old SHADERS shape).
SHADERS: List[str] = [s.shader for s in _SCHEMAS]

# Name -> schema. Aliases (shader name without .vfx) resolve to the same schema.
_SCHEMA_INDEX: Dict[str, ShaderSchema] = {}
for _s in _SCHEMAS:
    _SCHEMA_INDEX[_s.shader] = _s
    _SCHEMA_INDEX[_s.shader.replace(".vfx", "")] = _s


def get_shader_schema(shader: Optional[str]) -> Optional[ShaderSchema]:
    """Resolve a shader name (with or without .vfx) to its ShaderSchema, or None."""
    if not shader:
        return None
    key = str(shader).strip()
    return _SCHEMA_INDEX.get(key) or _SCHEMA_INDEX.get(key.lower())


def get_slots_for_shader(shader: Optional[str] = None,
                         feature_flags: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return the valid texture slot list for a shader. Falls back to a broad
    union of all known slots when the shader is unknown (matches legacy behavior)."""
    schema = get_shader_schema(shader)
    if schema is None:
        return _DEFAULT_SLOTS
    # Some shaders expose extra slots only under a feature flag (e.g. overlay's
    # Lighting/AO/Rough/Metal/Normal/Emissive under F_LIT). Honor that here.
    slots = list(schema.slots)
    for bm in schema.blend_modes:
        # blend modes don't add slots; this is reserved for feature-driven slots.
        pass
    # Overlay: when F_LIT is on, the lighting textures become valid targets too.
    if schema is _STATIC_OVERLAY and feature_flags and _truthy(feature_flags.get("F_LIT")):
        for extra in ("ao", "rough", "metal", "normal", "emissive"):
            if extra not in slots:
                slots.append(extra)
    return slots


def get_channel_slots_for_shader(shader: Optional[str] = None,
                                 feature_flags: Optional[Dict[str, Any]] = None) -> List[str]:
    """Single-channel slots suitable for channel splitting (excludes whole-color
    and whole-normal slots, which can't be meaningfully split)."""
    slots = get_slots_for_shader(shader, feature_flags=feature_flags)
    return [s for s in slots
            if not s.startswith("color") and not s.startswith("normal") and s != "emissive"]


def validate_feature_flags(shader: Optional[str], flags: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Enforce FeatureRule Requires gates for a shader's flags. Returns {} for
    empty input; returns flags unchanged if the shader has no schema or no rules."""
    if not flags:
        return {}
    schema = get_shader_schema(shader)
    if schema is None:
        return dict(flags)
    return _validate_flags_for_schema(schema, flags)


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip() not in ("", "0", "false", "False")
    return bool(v)


# Legacy fallback slot union (matches the old get_slots_for_shader(None) branch).
# Only layers 1-3 exist on the blend shader; layer 4 was a phantom entry.
_DEFAULT_SLOTS: List[str] = [
    "color", "normal", "rough", "metal", "ao", "height", "opacity", "emissive",
    "color2", "normal2", "rough2", "metal2", "ao2", "height2",
    "color3", "normal3", "rough3", "metal3", "ao3", "height3",
]


__all__ = [
    "SHADERS",
    "Ctx",
    "Param", "Block", "FeatureDef", "BlendMode", "ShaderSchema",
    "get_shader_schema",
    "get_slots_for_shader",
    "get_channel_slots_for_shader",
    "validate_feature_flags",
    "format_vmat",
]
