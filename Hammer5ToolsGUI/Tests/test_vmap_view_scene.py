import os

import numpy as np

from core.bridge import (
    ValveMapSceneDocument,
    ValveMapSceneMesh,
    ValveMapScenePlacement,
    ValveMapSceneSubMesh,
)
from gui.editors.vmap_view.scene import (
    BRUSH_PATH_PREFIX,
    apply_variable_overrides,
    build_scene,
    resolve_content_path,
)


def _quad_mesh():
    return ValveMapSceneMesh(
        "brush",
        np.array([0, 0, 0, 16, 0, 0, 16, 16, 0, 0, 16, 0], dtype=np.float32),
        np.array([0, 0, 1] * 4, dtype=np.float32),
        np.zeros(8, dtype=np.float32),
        np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32),
        (ValveMapSceneSubMesh(0, 6, "materials/dev/grid.vmat"),),
    )


def _translation(x, y, z):
    matrix = np.eye(4, dtype=np.float32)
    matrix[3, :3] = (x, y, z)
    return tuple(matrix.reshape(-1))


def test_build_scene_maps_meshes_props_and_smartprops_to_draw_infos():
    document = ValveMapSceneDocument(
        "maps/example.vmap",
        (_quad_mesh(),),
        (ValveMapScenePlacement("prop", "prop_static", "models/example.vmdl",
                                _translation(10, 20, 30), {}),),
        (ValveMapScenePlacement("smart", "CMapSmartProp", "smartprops/fence.vsmart",
                                _translation(0, 0, 0), {}),),
        (),
    )
    smart_prop_models = [(0, "models/fence.vmdl", np.eye(4, dtype=np.float32))]

    infos, meshes = build_scene(document, smart_prop_models, lambda _name: None)

    assert list(meshes) == [f"{BRUSH_PATH_PREFIX}0"]
    assert [info["path"] for info in infos] == [
        f"{BRUSH_PATH_PREFIX}0", "models/example.vmdl", "models/fence.vmdl",
    ]
    # Ids must be unique and non-zero so the viewport can pick each item.
    assert sorted(info["id"] for info in infos) == [1, 2, 3]
    assert infos[1]["position"] == [10.0, 20.0, 30.0]
    # Brush geometry is already in world space, so it draws at the origin.
    assert infos[0]["position"] == [0.0, 0.0, 0.0]

    mesh = meshes[f"{BRUSH_PATH_PREFIX}0"]
    assert mesh.vertices.shape == (4, 3)
    assert mesh.submeshes[0].material.name == "materials/dev/grid.vmat"
    assert list(mesh.bbox_max) == [16.0, 16.0, 0.0]


def test_apply_variable_overrides_replaces_defaults_by_name():
    document = {"m_Variables": [
        {"m_VariableName": "length", "m_DefaultValue": 1.0},
        {"m_VariableName": "height", "m_DefaultValue": 2.0},
    ]}

    apply_variable_overrides(document, {"length": 8.0, "missing": 5.0})

    assert [variable["m_DefaultValue"] for variable in document["m_Variables"]] == [8.0, 2.0]


def test_resolve_content_path_prefers_the_addon_named_in_the_reference(tmp_path):
    content = tmp_path / "csgo_addons"
    (content / "other" / "smartprops").mkdir(parents=True)
    target = content / "other" / "smartprops" / "fence.vsmart"
    target.write_text("{}", encoding="utf-8")

    resolved = resolve_content_path(
        "csgo_addons/other/smartprops/fence.vsmart",
        lambda addon: str(content / addon),
        "active",
    )

    assert os.path.normpath(resolved) == str(target)
    assert resolve_content_path("smartprops/missing.vsmart",
                                lambda addon: str(content / addon), "active") is None
