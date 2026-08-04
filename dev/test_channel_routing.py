"""Self-check for packed-mask channel routing (material_converter).

Covers the two things that silently produce wrong-looking materials: a packed
mask expanding to the wrong channels, and an alpha binding against a source
that has no alpha.

    python dev/test_channel_routing.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PIL import Image  # noqa: E402

from forms.unreal_porter.material_converter import (  # noqa: E402
    _classify_textures, packed_layout, convert_material, _pick_tint, _pick_scalar,
)


# Vector/scalar parameters as a real Master Material declares them — the base
# value sits alongside several secondary tints that must not be mistaken for it.
_MASTER_VECTORS = {
    "dirt color": {"r": 0.09, "g": 0.083, "b": 0.058, "a": 0.0},
    "diffuse color": {"r": 0.496, "g": 0.57, "b": 0.470, "a": 0.0},
    "metall color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 0.0},
    "fresnel color": {"r": 0.061, "g": 0.147, "b": 0.215, "a": 0.0},
}
_MASTER_SCALARS = {
    "Dirt str": 1.0, "Metallic": 0.0, "Dirt Roughness": 0.9,
    "Roughness": 0.35, "metall Roughness": 0.0,
}


def test_master_diffuse_colour_is_used():
    # "diffuse color" matched none of the old substring keys ("base color",
    # "diffuse tint", …), so these materials converted untinted white.
    assert _pick_tint(_MASTER_VECTORS) == (0.496, 0.57, 0.470)


def test_secondary_tints_never_win():
    assert _pick_tint({"dirt color": {"r": 1, "g": 0, "b": 0}}) is None
    assert _pick_tint({"fresnel color": {"r": 1, "g": 0, "b": 0}}) is None
    assert _pick_tint({"Base Color": {"r": 1, "g": 0, "b": 0}}) == (1, 0, 0)


def test_scalar_prefers_base_over_qualified():
    assert _pick_scalar(_MASTER_SCALARS, "roughness") == 0.35
    # "metal" is itself a secondary token; asking for it must still work.
    assert _pick_scalar(_MASTER_SCALARS, "metallic", "metalness", default=1.0) == 0.0
    # A qualified-only name must not stand in for the base value.
    assert _pick_scalar({"Dirt Roughness": 0.9}, "roughness", default=1.0) == 1.0
    # …but a differently-worded base name should still be found.
    assert _pick_scalar({"Roughness Multiplier": 0.7}, "roughness") == 0.7


def test_srmh_expands_to_channels():
    picks = _classify_textures({
        "Diffuse": "/Game/T/Box_D.Box_D",
        "Normal": "/Game/T/Box_N.Box_N",
        "SRMH": "/Game/T/Box_SRM.Box_SRM",
    })
    assert picks["color"][2] is None, "whole-texture bindings carry no channel"
    assert picks["rough"] == ("SRMH", "/Game/T/Box_SRM.Box_SRM", "g")
    assert picks["metal"] == ("SRMH", "/Game/T/Box_SRM.Box_SRM", "b")
    # S (specular) has no csgo_environment slot and must not leak into one.
    assert all(p[2] != "r" for p in picks.values())


def test_specific_param_beats_qualified_one():
    # "Dirt Normal" is a secondary detail map; the base slot must take the
    # plainly-named "Normal" even when the vaguer one is enumerated first.
    picks = _classify_textures({
        "Dirt Normal": "/Game/T/Dirt2_N.Dirt2_N",
        "Normal": "/Game/T/Box_N.Box_N",
    })
    assert picks["normal"][0] == "Normal", picks["normal"]


def test_orm_and_rma_differ():
    # Same channel index, different meaning — getting these confused swaps
    # roughness and occlusion, which is subtle enough to ship unnoticed.
    assert packed_layout("T_ORM")[1]["r"] == "ao"
    assert packed_layout("T_RMA")[1]["r"] == "rough"


def test_override_beats_heuristic():
    picks = _classify_textures(
        {"SRMH": "/Game/T/Box_SRM.Box_SRM"},
        {"SRMH": {"ao": "r", "rough": "g"}},
    )
    assert picks["ao"][2] == "r"
    assert picks["rough"][2] == "g"
    assert "metal" not in picks, "an explicit override replaces the layout"


def test_texture_filename_identifies_layout():
    # Neutrally-named param, layout token only on the file.
    picks = _classify_textures({"Mask": "/Game/T/Crate_ORM.Crate_ORM"})
    assert picks["ao"][2] == "r"
    assert picks["rough"][2] == "g"


def test_alpha_channel_skipped_when_source_has_none(tmp_dir):
    """A _SRMH param pointing at a 3-channel file must not emit a white height
    map — Image.convert('RGBA') would fabricate an opaque alpha."""
    bulk = os.path.join(tmp_dir, "bulk")
    out = os.path.join(tmp_dir, "out")
    os.makedirs(bulk)
    Image.new("RGB", (4, 4), (10, 120, 230)).save(os.path.join(bulk, "Box_SRM.tga"))

    res = convert_material(
        {"material": "IPP/Materials/Box.uasset",
         "textures": {"SRMH": "/Game/IPP/Textures/Box_SRM.Box_SRM"}},
        bulk, out,
    )
    written = os.listdir(os.path.join(out, os.path.dirname(res.vmat_path)))
    assert not any("height" in f for f in written), f"height map emitted: {written}"
    assert any("rough" in f for f in written), f"roughness missing: {written}"
    assert "height" in res.missing


def demo():
    import tempfile
    test_srmh_expands_to_channels()
    test_specific_param_beats_qualified_one()
    test_master_diffuse_colour_is_used()
    test_secondary_tints_never_win()
    test_scalar_prefers_base_over_qualified()
    test_orm_and_rma_differ()
    test_override_beats_heuristic()
    test_texture_filename_identifies_layout()
    with tempfile.TemporaryDirectory() as tmp:
        test_alpha_channel_skipped_when_source_has_none(tmp)
    print("ok")


if __name__ == "__main__":
    demo()
