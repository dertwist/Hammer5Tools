"""The vmdl material remap takes UE's own slot table when the mesh asset could
be read, and falls back to matching FBX material names when it could not."""

from unittest.mock import patch

from gui.forms.unreal_porter.vmdl_writer import resolve_material_remaps


def _remaps(ue_materials, embedded=("MI_Cart_01", "MI_Wood_02")):
    with patch("gui.forms.unreal_porter.fbx_flatten.list_materials", return_value=list(embedded)), \
         patch("os.path.isfile", return_value=True):
        return resolve_material_remaps(fbx_path="cart.fbx", model_rel_path="models/props/cart.vmdl",
                                       ue_materials=ue_materials)


def test_ue_slot_table_resolves_each_slot_exactly():
    """UE records slot -> material; the FBX exports its slots in that order, so
    the mapping is known rather than reconstructed from the material's name."""
    out = _remaps([
        "/Game/Medieval/Materials/Instances/MI_Cart-01.MI_Cart-01",
        "/Game/Medieval/Materials/Instances/MI_Wood-02.MI_Wood-02",
    ])
    assert out == [
        # strip_ue_prefix normalises the hyphen, matching the name the
        # material pass writes for the same asset.
        {"from": "MI_Cart_01.vmat", "to": "materials/medieval/instances/cart_01.vmat"},
        {"from": "MI_Wood_02.vmat", "to": "materials/medieval/instances/wood_02.vmat"},
    ], out


def test_a_mismatched_or_missing_slot_table_falls_back_to_name_matching():
    # One UE slot, two FBX materials: the orders cannot be trusted to line up.
    fallback = _remaps(["/Game/M/MI_Cart-01.MI_Cart-01"])
    assert [r["from"] for r in fallback] == ["MI_Cart_01.vmat", "MI_Wood_02.vmat"]
    assert all("/Game/" not in r["to"] for r in fallback), fallback
    # No table at all (mesh unreadable) behaves exactly as before.
    assert _remaps(None) == fallback


def test_an_empty_slot_entry_does_not_silently_drop_a_material():
    """A slot with no material assigned must not produce a short remap list —
    that would leave the other slots unmapped too."""
    out = _remaps(["/Game/M/MI_Cart-01.MI_Cart-01", ""])
    assert [r["from"] for r in out] == ["MI_Cart_01.vmat", "MI_Wood_02.vmat"]
