"""Self-check for the direct compiled-asset reader.

Runnable without a Qt app or a GL context:

    python dev/test_vmdl_reader.py

Needs CS2 installed (models are read from pak01_dir.vpk).  Fails loudly if the
reader regresses on geometry, index validity, orientation, submesh coverage, or
material decoding.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.common import get_cs2_path
from src.editors.smartprop_editor.viewport_3d.vmdl_reader import load_model

# A plain single-material prop, a two-material prop with an alpha-tested leaf
# card, and the largest model CS2 ships (multi-drawcall, layered shader).
SIMPLE = "models/props/de_aztec/hr_aztec/aztec_trims/aztec_decotrim_set3_frame_angle_02"
TWO_MATERIAL = "models/props/de_inferno/hr_i/ivy_a/ivy_a"
LARGE = "models/props/de_train/hr_train_s2/train_railcars/train_locomotive_shunter_01"


def check_structure(mesh, name):
    assert mesh is not None, f"{name}: returned None"
    assert len(mesh.vertices) > 0, f"{name}: no vertices"
    assert len(mesh.indices) > 0, f"{name}: no indices"
    assert len(mesh.indices) % 3 == 0, f"{name}: index count {len(mesh.indices)} is not a triangle list"

    # Every index must address a real vertex, otherwise the GPU draw reads
    # garbage.  This is what catches a bad per-drawcall base-vertex offset.
    assert int(mesh.indices.max()) < len(mesh.vertices), (
        f"{name}: index {int(mesh.indices.max())} out of range for {len(mesh.vertices)} vertices")

    assert mesh.vertices.dtype == np.float32, f"{name}: vertices are {mesh.vertices.dtype}"
    assert mesh.indices.dtype == np.uint32, f"{name}: indices are {mesh.indices.dtype}"
    assert mesh.uvs is not None and len(mesh.uvs) == len(mesh.vertices), f"{name}: UV count mismatch"
    assert len(mesh.normals) == len(mesh.vertices), f"{name}: normal count mismatch"
    assert np.isfinite(mesh.vertices).all(), f"{name}: non-finite vertex"

    # Normals are unit length (or exactly zero where the buffer had none).
    lengths = np.linalg.norm(mesh.normals, axis=1)
    non_zero = lengths > 1e-6
    assert np.allclose(lengths[non_zero], 1.0, atol=1e-3), f"{name}: normals not normalised"

    # Submeshes must tile the index buffer exactly — gaps mean dropped geometry,
    # overlaps mean double-drawn triangles.
    covered = 0
    for sub in mesh.submeshes:
        assert sub.index_offset == covered, (
            f"{name}: submesh starts at {sub.index_offset}, expected {covered}")
        covered += sub.index_count
    assert covered == len(mesh.indices), (
        f"{name}: submeshes cover {covered} of {len(mesh.indices)} indices")

    assert (mesh.bbox_max >= mesh.bbox_min).all(), f"{name}: inverted bbox"


def main():
    if not get_cs2_path():
        print("SKIP: CS2 path not configured")
        return 0

    mesh = load_model(SIMPLE)
    check_structure(mesh, "simple")
    assert len(mesh.submeshes) >= 1

    mesh = load_model(TWO_MATERIAL)
    check_structure(mesh, "two_material")
    assert len(mesh.submeshes) == 2, f"expected 2 submeshes, got {len(mesh.submeshes)}"
    names = [s.material.name for s in mesh.submeshes]
    assert len(set(names)) == 2, f"submeshes share a material: {names}"
    # The leaf card is alpha-tested and two-sided; losing that makes ivy render
    # as opaque rectangles.
    assert any(s.material.alpha_mode == "MASK" for s in mesh.submeshes), "no alpha-tested submesh"
    assert any(s.material.double_sided for s in mesh.submeshes), "no double-sided submesh"
    for sub in mesh.submeshes:
        img = sub.material.base_color_img
        assert img is not None, f"{sub.material.name}: no base colour"
        assert img.ndim == 3 and img.shape[2] == 4, f"{sub.material.name}: base colour is {img.shape}"
        assert img.dtype == np.uint8

    # Source space is Z-up: this model stands taller than it is deep.
    height = float(mesh.bbox_max[2] - mesh.bbox_min[2])
    depth = float(mesh.bbox_max[1] - mesh.bbox_min[1])
    assert height > depth, f"model is not Z-up (height {height:.1f} <= depth {depth:.1f})"

    start = time.perf_counter()
    mesh = load_model(LARGE)
    elapsed = time.perf_counter() - start
    check_structure(mesh, "large")
    # The glTF path split vertices per material and emitted every LoD, inflating
    # this model to 375,960 vertices; reading draw calls directly keeps the real
    # count. Guard against silently regressing to the duplicated form.
    assert len(mesh.vertices) < 150_000, (
        f"large model has {len(mesh.vertices)} vertices — LoD/material duplication is back")
    # Layered shader (csgo_environment.vfx) uses g_tColor1, not g_tColor.
    assert any(s.material.base_color_img is not None for s in mesh.submeshes), \
        "layered-shader materials resolved no textures"
    assert any(s.material.mr_img is not None for s in mesh.submeshes), \
        "no metallic-roughness built (roughness comes from the normal map's alpha)"

    print(f"OK  large model: {len(mesh.vertices)} verts, {len(mesh.submeshes)} submeshes, {elapsed:.2f}s")

    # Test agent model with mesh groups (bodygroups)
    agent = load_model("agents/models/ctm_sas/ctm_sas")
    check_structure(agent, "ctm_sas")
    # ctm_sas has 6 embedded meshes across 6 mesh groups; default mask filters out 1 non-default group (sleeve/firstperson).
    assert len(agent.submeshes) == 5, f"ctm_sas: expected 5 default submeshes, got {len(agent.submeshes)}"


    # Test material groups (skins)
    glove_skin0 = load_model("agents/models/shared/arms/glove_bloodhound/glove_bloodhound", skin=0)
    glove_skin1 = load_model("agents/models/shared/arms/glove_bloodhound/glove_bloodhound", skin=1)
    check_structure(glove_skin0, "glove_skin0")
    check_structure(glove_skin1, "glove_skin1")
    assert glove_skin0.submeshes[0].material.name != glove_skin1.submeshes[0].material.name, \
        "skin 0 and skin 1 resolved same material"

    # Test texture wrap mode attributes
    for sub in mesh.submeshes:
        assert hasattr(sub.material, "wrap_u") and hasattr(sub.material, "wrap_v")

    print("OK  all checks passed")
    return 0



if __name__ == "__main__":
    sys.exit(main())
