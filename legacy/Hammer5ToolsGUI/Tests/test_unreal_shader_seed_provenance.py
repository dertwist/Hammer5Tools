"""A saved shader that is only last run's automatic guess must not outrank a
better guess from a newer seeder — but a choice the user made must."""

import os

from gui.forms.unreal_porter.converter import (
    apply_saved_swaps, load_material_swaps_kv3, save_material_swaps_kv3,
)


def _addon(tmp_path):
    os.makedirs(tmp_path / "hammer5tools" / "unrealporter", exist_ok=True)
    return str(tmp_path)


def test_an_old_auto_seed_is_replaced_by_the_new_one(tmp_path):
    out = _addon(tmp_path)
    # Last run seeded M_Fern_01 to environment and recorded that it did so.
    save_material_swaps_kv3(out, {"M_Fern_01": "csgo_environment.vfx"},
                            auto_seed={"M_Fern_01": "csgo_environment.vfx"})

    groups = apply_saved_swaps({"M_Fern_01": {"shader": "csgo_foliage.vfx"}}, out)
    assert groups["M_Fern_01"]["shader"] == "csgo_foliage.vfx"


def test_a_choice_the_user_made_still_wins(tmp_path):
    out = _addon(tmp_path)
    # Seeded to environment, then changed to glass in the Materials tab.
    save_material_swaps_kv3(out, {"M_Fern_01": "csgo_glass.vfx"},
                            auto_seed={"M_Fern_01": "csgo_environment.vfx"})

    groups = apply_saved_swaps({"M_Fern_01": {"shader": "csgo_foliage.vfx"}}, out)
    assert groups["M_Fern_01"]["shader"] == "csgo_glass.vfx"


def test_a_table_with_no_provenance_is_treated_as_user_choices(tmp_path):
    """Tables written before provenance existed must keep behaving as they did,
    rather than silently discarding the picks recorded in them."""
    out = _addon(tmp_path)
    save_material_swaps_kv3(out, {"M_Fern_01": "csgo_environment.vfx"}, auto_seed={})

    groups = apply_saved_swaps({"M_Fern_01": {"shader": "csgo_foliage.vfx"}}, out)
    assert groups["M_Fern_01"]["shader"] == "csgo_environment.vfx"


def test_rewriting_only_the_shader_table_keeps_the_provenance(tmp_path):
    """The convert path saves shaders without passing provenance; dropping the
    section there would make every entry look like a user choice next run."""
    out = _addon(tmp_path)
    save_material_swaps_kv3(out, {"M_Fern_01": "csgo_environment.vfx"},
                            auto_seed={"M_Fern_01": "csgo_environment.vfx"})
    save_material_swaps_kv3(out, {"M_Fern_01": "csgo_environment.vfx"})

    assert load_material_swaps_kv3(out)[5] == {"M_Fern_01": "csgo_environment.vfx"}


def test_every_caller_unpacks_the_loader_correctly(tmp_path):
    """The loader's return is unpacked positionally at several call sites, so
    adding a field breaks them at runtime and not at import — the convert run
    died with "too many values to unpack (expected 5)" after the last one."""
    import ast
    import pathlib

    porter = pathlib.Path(__file__).resolve().parents[1] / "gui" / "forms" / "unreal_porter"
    arity = len(load_material_swaps_kv3(_addon(tmp_path)))
    unpackers = 0
    for source in porter.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            if getattr(func, "id", None) != "load_material_swaps_kv3":
                continue
            for target in node.targets:
                if isinstance(target, (ast.Tuple, ast.List)):
                    unpackers += 1
                    assert len(target.elts) == arity, (
                        f"{source.name} unpacks {len(target.elts)} of {arity} values"
                    )
    assert unpackers, "no positional unpacking found — update or drop this test"
