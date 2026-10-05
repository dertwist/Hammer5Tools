"""The project material scan runs its Core dumps in parallel; grouping must not
depend on which one finishes first."""

import threading

from gui.forms.unreal_porter.converter import scan_master_materials, seed_shader_for


class FakeBridge:
    """Answers dump_material out of order and records how many run at once."""

    def __init__(self, materials):
        self.materials = materials
        self.peak_concurrency = 0
        self._live = 0
        self._lock = threading.Lock()
        self._barrier = threading.Barrier(len(materials), timeout=5)

    def is_available(self):
        return True

    def list_materials(self):
        return [f"{path}.uasset" for path in self.materials] + ["Game/Notes.txt"]

    def dump_material(self, path):
        with self._lock:
            self._live += 1
            self.peak_concurrency = max(self.peak_concurrency, self._live)
        # Every dump waits for the others, so the results can only be in key
        # order if the scan puts them there rather than appending as they land.
        self._barrier.wait()
        with self._lock:
            self._live -= 1
        data = self.materials[path]
        if isinstance(data, Exception):
            raise data
        return data


def test_material_scan_is_parallel_and_keeps_key_order():
    bridge = FakeBridge({
        "Game/MI_A": {"flags": {}, "parent": "/Game/M_Master.M_Master", "textures": {"Base": "/Game/T_A"}},
        "Game/MI_B": {"flags": {}, "parent": "/Game/M_Master.M_Master", "textures": {}},
        "Game/MI_C": {"flags": {}, "parent": "/Game/M_Master.M_Master", "textures": {}},
    })

    groups = scan_master_materials("", None, bridge)

    assert bridge.peak_concurrency > 1, "dumps ran one at a time"
    assert list(groups) == ["M_Master"], groups
    instances = [stem for stem, _path, _data in groups["M_Master"]["instances"]]
    assert instances == ["MI_A", "MI_B", "MI_C"], instances
    assert groups["M_Master"]["count"] == 3
    assert groups["M_Master"]["textures"] == {"Base": "/Game/T_A"}


def test_material_scan_skips_the_assets_core_cannot_read():
    bridge = FakeBridge({
        "Game/MI_A": {"flags": {}, "parent": "/Game/M_Master.M_Master", "textures": {}},
        "Game/MI_Broken": RuntimeError("unreadable"),
    })
    warnings = []

    groups = scan_master_materials("", None, bridge, log_cb=lambda msg, level="info": warnings.append((level, msg)))

    assert [stem for stem, _p, _d in groups["M_Master"]["instances"]] == ["MI_A"]
    assert any(level == "warn" and "MI_Broken" in msg for level, msg in warnings), warnings


def test_material_scan_rejects_assets_that_are_not_materials():
    """list_materials() selects by folder and filename, so material functions,
    parameter collections, curves, textures and MM_-prefixed animations reach the
    scan. Only a Material/MaterialInstance package resolves flags; without that
    check each of those became its own Master Material with a guessed shader."""
    bridge = FakeBridge({
        "Game/Materials/M_Real": {"flags": {"blendMode": "BLEND_Masked"}, "parent": None, "textures": {}},
        "Game/Materials/Functions/MF_Tiling": {"flags": None, "parent": None, "textures": {}},
        "Game/Animations/MM_Idle": {"flags": None, "parent": None, "textures": {}},
    })
    logged = []

    groups = scan_master_materials("", None, bridge, log_cb=lambda msg, level="info": logged.append((level, msg)))

    assert list(groups) == ["M_Real"], groups
    assert any("not materials" in msg for _level, msg in logged), logged


def test_seed_shader_reads_the_material_before_its_name():
    """Every foliage master in a real project is masked MSM_TwoSidedFoliage;
    almost none of them is named "grass" or "foliage"."""
    assert seed_shader_for("M_Yarrow_Inst", {
        "blendMode": "BLEND_Masked", "shadingModel": "MSM_TwoSidedFoliage", "twoSided": True,
    }) == "csgo_foliage.vfx"
    # Unlit translucency/additive is a glow card, not glass.
    assert seed_shader_for("M_GodRay_MASTER", {
        "blendMode": "BLEND_Additive", "shadingModel": "MSM_Unlit",
    }) == "csgo_effects.vfx"
    assert seed_shader_for("M_Master_Glass", {"blendMode": "BLEND_Translucent"}) == "csgo_glass.vfx"
    assert seed_shader_for("M_decal_tint", {"domain": "MD_DeferredDecal"}) == "csgo_static_overlay.vfx"
    # Opaque and flagless: the name rules still decide, as before.
    assert seed_shader_for("M_Standard_ORD", {"blendMode": None}) == "csgo_environment.vfx"
    assert seed_shader_for("M_Tree_Bark", {}) == "csgo_foliage.vfx"
