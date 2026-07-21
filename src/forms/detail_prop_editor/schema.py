"""
Schema for scripts/detail_prop_types.vdata (CDetailPropType / CDetailPropModel).

Mirrors the Source 2 schema published at
https://s2v.app/SchemaExplorer/cs2/toolutils2 — field order, defaults,
friendly names, ranges and descriptions are taken from there so the editor
presents the same properties Hammer's own vdata outliner does.
"""

from dataclasses import dataclass, field
from typing import Optional

GENERIC_DATA_TYPE = "CDetailPropType"
VDATA_RELATIVE_PATH = "scripts/detail_prop_types.vdata"


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str                      # 'float' | 'bool' | 'model' | 'string' | 'qangle'
    default: object
    description: str = ""
    range: Optional[tuple] = None  # (min, max) for float/qangle
    digits: int = 3


# CDetailPropType — the detail type itself. m_Models is handled by the tree.
TYPE_FIELDS = [
    Field("m_flDensity", "Density", "float", 1.0,
          "Specifies the number of props placed per square foot.", None, 4),
]


# CDetailPropModel — one model entry inside a detail type.
MODEL_FIELDS = [
    Field("m_ModelName", "Model", "model", "",
          "Model to be displayed."),
    Field("m_MaterialGroup", "Material Group", "string", "",
          "Material group (skin) to assign to use with the model."),
    Field("m_flWeight", "Weight", "float", 1.0,
          "A weight determining the frequency at which this model is placed relative to "
          "other models within the detail type. The weights of all models are summed and "
          "the probability of selecting this model is its weight divided by the sum weight."),
    Field("m_flStartFadeSize", "Start fade out size", "float", 0.02,
          "Screen space size [0, 1] (where 1 is the whole screen) at which the model will "
          "begin to fade out. Anything larger will be fully visible, anything smaller will "
          "start to fade out.", (0.001, 1.0), 4),
    Field("m_flEndFadeSize", "Complete fade out size", "float", 0.0125,
          "Screen space size [0, 1] at which the model will be completely faded out. "
          "Anything smaller than this size will not be visible.", (0.001, 1.0), 4),
    Field("m_bWorldSpaceOrientation", "Use World Space Up", "bool", False,
          "If enabled, the up direction will be evaluated in world space, such that the "
          "object orientation does not affect the surface slope filtering."),
    Field("m_flOrientToSurface", "Orient To Surface", "float", 1.0,
          "Value indicating if the model's up direction should be matched to the surface. "
          "0 means model up is used and the surface direction ignored, 1 means the model up "
          "will exactly match the surface normal.", (0.0, 1.0)),
    Field("m_flMinSurfaceSlope", "Min Surface Slope", "float", 0.0,
          "Minimum slope on which the target will be placed. Slope is a [0, 180] value based "
          "on the surface normal where a floor is 0, a wall is 90 and a ceiling is 180.",
          (0.0, 180.0), 2),
    Field("m_flMaxSurfaceSlope", "Max Surface Slope", "float", 180.0,
          "Maximum slope on which the target will be placed.", (0.0, 180.0), 2),
    Field("m_flRandomVerticalOffsetMin", "Random Vertical Offset Min", "float", 0.0,
          "Minimum range of random offset to apply along the model's local up direction."),
    Field("m_flRandomVerticalOffsetMax", "Random Vertical Offset Max", "float", 0.0,
          "Maximum range of random offset to apply along the model's local up direction."),
    Field("m_vRandomRotationMin", "Random Rotation Min", "qangle", [0.0, 0.0, 0.0],
          "Minimum range of the random rotation to apply to the model. Random rotation is "
          "applied in the local space of the model. Values are ordered pitch, yaw, roll.",
          (-360.0, 360.0), 2),
    Field("m_vRandomRotationMax", "Random Rotation Max", "qangle", [0.0, 360.0, 0.0],
          "Maximum range of the random rotation to apply to the model.", (-360.0, 360.0), 2),
    Field("m_flRandomScaleMin", "Random Scale Min", "float", 1.0,
          "Minimum random scale value to apply to the model."),
    Field("m_flRandomScaleMax", "Random Scale Max", "float", 1.0,
          "Maximum random scale value to apply to the model."),
    Field("m_flDensityMinScale", "Density Scale", "float", 1.0,
          "Minimum scale to apply to the model based on the painted detail prop density. The "
          "minimum of the detail and blend weight scale values is multiplied with the random "
          "scale value to determine the final scale.", (0.01, 1.0)),
    Field("m_flBlendWeightMinScale", "Blend Weight Scale", "float", 1.0,
          "Minimum scale to apply to the model based on the final material layer blend weight. "
          "Set this if you want the model to scale up as the material blend fades in.",
          (0.01, 1.0)),
    Field("m_flBlendWeightMin", "Min Blend Weight", "float", 0.25,
          "Minimum blend weight value for which the model will be placed. If the blend weight "
          "is less than this value, the model will not be placed.", (0.01, 1.0)),
    Field("m_flBlendWeightMax", "Max Blend Weight", "float", 1.0,
          "Maximum blend weight value for which the model will be placed. If the blend weight "
          "is more than this value, the model will not be placed.", (0.01, 1.0)),
    Field("m_flBlendWeightFullDenstity", "Full Density Blend Weight", "float", 0.75,
          "Blend weight at which the model will be at full density. Must be between the "
          "minimum and maximum blend weight values.", (0.01, 1.0)),
    Field("m_bCastStaticShadows", "Cast Static Shadows", "bool", False,
          "Should instances of this model generate shadows in the lightmap. Note that shadows "
          "in the light map will persist even after the model fades out."),
]

MODEL_FIELDS_BY_KEY = {f.key: f for f in MODEL_FIELDS}
TYPE_FIELDS_BY_KEY = {f.key: f for f in TYPE_FIELDS}

# Groups used to lay the property editor out in collapsible sections.
MODEL_FIELD_GROUPS = [
    ("Model", ["m_ModelName", "m_MaterialGroup", "m_flWeight"]),
    ("Fade", ["m_flStartFadeSize", "m_flEndFadeSize"]),
    ("Orientation", ["m_bWorldSpaceOrientation", "m_flOrientToSurface",
                     "m_vRandomRotationMin", "m_vRandomRotationMax"]),
    ("Placement", ["m_flMinSurfaceSlope", "m_flMaxSurfaceSlope",
                   "m_flRandomVerticalOffsetMin", "m_flRandomVerticalOffsetMax"]),
    ("Scale", ["m_flRandomScaleMin", "m_flRandomScaleMax",
               "m_flDensityMinScale", "m_flBlendWeightMinScale"]),
    ("Blend Weight", ["m_flBlendWeightMin", "m_flBlendWeightMax",
                      "m_flBlendWeightFullDenstity"]),
    ("Lighting", ["m_bCastStaticShadows"]),
]


def default_model() -> dict:
    """A new CDetailPropModel with every field at its schema default."""
    out = {}
    for f in MODEL_FIELDS:
        out[f.key] = list(f.default) if isinstance(f.default, list) else f.default
    return out


def default_type() -> dict:
    """A new CDetailPropType holding a single default model."""
    out = {f.key: f.default for f in TYPE_FIELDS}
    out["m_Models"] = [default_model()]
    return out
