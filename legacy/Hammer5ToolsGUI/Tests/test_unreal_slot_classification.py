"""Slot classification rules derived from ten UE projects (26,960 assets,
3,247 materials). Each case below is a naming convention that appeared in that
corpus and that the heuristic previously got wrong."""

from gui.forms.unreal_porter.material_converter import (
    _classify_textures, is_non_surface_texture, packed_layout,
)


def test_packed_masks_are_decoded_from_their_channel_letters():
    # The corpus named packed masks ORD, AORM, MRA, ARD, DMAR and DR — the
    # hardcoded table covered none of them. The letters are the channel order.
    assert packed_layout("Texture_ORD", "T_Brick_ORD")[1] == {"r": "ao", "g": "rough", "b": "height"}
    assert packed_layout("Mask", "T_Barrel_01_AORM")[1] == {"r": "ao", "g": "rough", "b": "metal"}
    assert packed_layout("MRA", "T_decal_cracks_01_MRA")[1] == {"r": "metal", "g": "rough", "b": "ao"}
    assert packed_layout("DR", "T_Rock_DpR")[1] == {"r": "height", "g": "rough"}
    # Lower case is an ordinary word, not a mask: "Road", "Arm", "Harm".
    assert packed_layout("Road Texture", "T_Road_01_D")[0] is None
    # Letters outside the channel set never decode.
    assert packed_layout("BaseColor", "T_Wood_BC")[0] is None


def test_a_parameter_that_spells_its_channels_feeds_every_slot():
    """"MT(R) R(G) AO(B)" states its own layout; without reading it the texture
    could only fill one slot and the rest went to whatever else was lying about."""
    out = _classify_textures({
        "Base_Color": "/Game/T_cliff_BC",
        "MT(R) R(G) AO(B)": "/Game/T_cliff_MT_R_AO",
        "Normalmap": "/Game/T_cliff_N",
    }, shader="csgo_environment.vfx")
    assert out["color"][0] == "Base_Color"
    assert out["normal"][0] == "Normalmap"
    for slot, channel in (("metal", "r"), ("rough", "g"), ("ao", "b")):
        assert out[slot][0] == "MT(R) R(G) AO(B)" and out[slot][2] == channel, out


def test_a_secondary_map_never_outranks_the_base_map():
    out = _classify_textures({
        "Detail Normal": "/Game/T_detail_N",
        "Normal": "/Game/T_rock_N",
        "Cover Color": "/Game/T_moss_BC",
        "Base Color": "/Game/T_rock_BC",
    }, shader="csgo_environment.vfx")
    assert out["normal"][0] == "Normal"
    assert out["color"][0] == "Base Color"
    # …but it still binds when it is all there is.
    only = _classify_textures({"Detail Normal": "/Game/T_detail_N"}, shader="csgo_environment.vfx")
    assert only["normal"][0] == "Detail Normal"


def test_data_textures_never_take_a_slot():
    """Pivot-painter atlases, wind noise and cubemaps are shader-graph inputs,
    and several carry words ("position", "normals") that won real slots."""
    assert is_non_surface_texture("Position and Index Texture", "T_Blueberry_A1_PivotPos")
    assert is_non_surface_texture("WindTurbulenceVectorAndGustMagnitude", "")
    assert is_non_surface_texture("Reflection Cubemap", "Desert_Outer_HDR")
    assert not is_non_surface_texture("Normal", "T_Rock_N")

    out = _classify_textures({
        "Position and Index Texture": "/Game/T_Bush_PivotPos",
        "BillboardNormals": "/Game/T_Bush_billboard_N",
    }, shader="csgo_environment.vfx")
    assert all(v[0] != "Position and Index Texture" for v in out.values()), out


def test_one_letter_from_a_filename_cannot_claim_a_slot():
    """"Base Map" bound to T_beach_grass_01_BC_M yields the token "m", which
    claimed metal and consumed the material's only base colour."""
    out = _classify_textures({
        "Base Map": "/Game/T_beach_grass_01_BC_M",
        "Normal": "/Game/T_beach_grass_01_N",
    }, shader="csgo_environment.vfx")
    assert out["color"][0] == "Base Map"
    assert "metal" not in out, out
