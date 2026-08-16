import os
import sys
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_dir = os.path.join(repo_root, "src")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.editors.assetgroup_maker.analyzer import analyze_reference_file
from src.editors.assetgroup_maker.matcher import match_folder_assets, strip_known_suffix, is_file_ignored
from src.editors.assetgroup_maker.process import perform_batch_processing, render_asset_template
from src.editors.assetgroup_maker.matcher import AssetGroupItem
from src.editors.assetgroup_maker.main import BatchCreatorMainWindow
from src.editors.assetgroup_maker.editor_tab import EditorTabWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def fake_addon_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        addon_path = os.path.normpath(os.path.join(tmpdir, "content", "csgo_addons", "test_addon"))
        os.makedirs(os.path.join(addon_path, "models", "props", "crate"), exist_ok=True)
        os.makedirs(os.path.join(addon_path, "materials", "nature"), exist_ok=True)
        os.makedirs(os.path.join(addon_path, "smartprops", "dev"), exist_ok=True)
        with patch("src.settings.main.get_addon_dir", return_value=addon_path), \
             patch("src.settings.common.get_addon_dir", return_value=addon_path), \
             patch("src.settings.main.get_addon_name", return_value="test_addon"), \
             patch("src.settings.main.get_cs2_path", return_value=tmpdir):
            yield addon_path


def test_analyzer_vmdl(fake_addon_dir):
    vmdl_path = os.path.join(fake_addon_dir, "models", "props", "crate", "box_01.vmdl")
    vmdl_content = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{
    rootNode = {
        _class = "RootNode"
        children = [
            {
                _class = "RenderMeshList"
                children = [
                    {
                        _class = "RenderMeshFile"
                        filename = "models/props/crate/box_01.fbx"
                    }
                ]
            },
            {
                _class = "PhysicsShapeList"
                children = [
                    {
                        _class = "PhysicsHullFile"
                        filename = "models/props/crate/box_01_phys.fbx"
                    }
                ]
            },
            {
                _class = "MaterialGroupList"
                children = [
                    {
                        _class = "DefaultMaterialGroup"
                        global_default_material = "materials/props/crate/box_01.vmat"
                    }
                ]
            }
        ]
    }
}
"""
    with open(vmdl_path, "w", encoding="utf-8") as f:
        f.write(vmdl_content)

    res = analyze_reference_file(vmdl_path)
    assert res.asset_type == "vmdl"
    assert res.base_name == "box_01"
    assert "mesh" in res.slots
    assert res.slots["mesh"]["filename"] == "box_01.fbx"
    assert "collision" in res.slots
    assert res.slots["collision"]["filename"] == "box_01_phys.fbx"
    assert "material" in res.slots
    assert res.slots["material"]["filename"] == "box_01.vmat"
    assert "#$MESH$#" in res.template_content
    assert "#$COLLISION$#" in res.template_content
    assert "#$MATERIAL$#" in res.template_content


def test_analyzer_vmat(fake_addon_dir):
    vmat_path = os.path.join(fake_addon_dir, "materials", "nature", "rock_01.vmat")
    vmat_content = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
Layer0
{
    shader "csgo_complex.vfx"
    g_tColor = resource:"materials/nature/rock_01_color.png"
    g_tNormal = resource:"materials/nature/rock_01_normal.png"
    g_tRoughness = resource:"materials/nature/rock_01_rough.png"
    g_tAmbientOcclusion = resource:"materials/nature/rock_01_ao.png"
}
"""
    with open(vmat_path, "w", encoding="utf-8") as f:
        f.write(vmat_content)

    res = analyze_reference_file(vmat_path)
    assert res.asset_type == "vmat"
    assert res.base_name == "rock_01"
    assert "color" in res.slots
    assert res.slots["color"]["filename"] == "rock_01_color.png"
    assert "normal" in res.slots
    assert res.slots["normal"]["filename"] == "rock_01_normal.png"
    assert "roughness" in res.slots
    assert "ao" in res.slots


def test_matcher_multi_file_pairing(fake_addon_dir):
    crate_dir = os.path.join(fake_addon_dir, "models", "props", "crate")
    files = [
        "barrel_01.fbx",
        "barrel_01_phys.fbx",
        "chest_02.fbx",
        "chest_02_col.fbx",
        "chest_02_lod1.fbx",
        "trash_temp.blend",
        "draft_chair.fbx"
    ]
    for f in files:
        with open(os.path.join(crate_dir, f), "w") as fp:
            fp.write("dummy")

    slots_def = {
        'mesh': {'required': True},
        'collision': {'required': False, 'fallback': 'mesh'}
    }

    items = match_folder_assets(
        directory=crate_dir,
        slots=slots_def,
        extension="vmdl",
        ignore_extensions_str="blend, png, jpg",
        ignore_list_str="draft_*, *temp*",
        algorithm=0
    )

    names = [item.name for item in items]
    assert "barrel_01" in names
    assert "chest_02" in names
    assert "trash_temp" not in names
    assert "draft_chair" not in names

    barrel_item = next(i for i in items if i.name == "barrel_01")
    assert "mesh" in barrel_item.slots
    assert barrel_item.slots["mesh"].endswith("barrel_01.fbx")
    assert "collision" in barrel_item.slots
    assert barrel_item.slots["collision"].endswith("barrel_01_phys.fbx")
    assert barrel_item.status == "ready"

    chest_item = next(i for i in items if i.name == "chest_02")
    assert "collision" in chest_item.slots
    assert chest_item.slots["collision"].endswith("chest_02_col.fbx")
    assert "lod1" in chest_item.slots
    assert chest_item.slots["lod1"].endswith("chest_02_lod1.fbx")


def test_batch_process_with_conditional_blocks(fake_addon_dir):
    crate_dir = os.path.join(fake_addon_dir, "models", "props", "crate")
    hbat_path = os.path.join(crate_dir, "batch.hbat")

    with open(os.path.join(crate_dir, "box_a.fbx"), "w") as f:
        f.write("box_a")
    with open(os.path.join(crate_dir, "box_a_phys.fbx"), "w") as f:
        f.write("box_a_phys")

    template = """<!-- kv3 -->
{
    mesh = "#$FOLDER_PATH$#/#$MESH$#"
    <!-- IF COLLISION -->
    collision = "#$FOLDER_PATH$#/#$COLLISION$#"
    <!-- ENDIF -->
}
"""
    process_data = {
        "reference": "",
        "extension": "vmdl",
        "load_from_the_folder": True,
        "output_to_the_folder": True,
        "ignore_extensions": "blend,hbat",
        "ignore_list": ""
    }

    created = perform_batch_processing(
        file_path=hbat_path,
        process=process_data,
        preview=False,
        replacements={},
        content_template=template
    )

    assert len(created) >= 1
    out_vmdl = os.path.join(crate_dir, "box_a.vmdl")
    assert os.path.isfile(out_vmdl)

    with open(out_vmdl, "r") as f:
        content = f.read()
    assert "box_a.fbx" in content
    assert "box_a_phys.fbx" in content
    assert "<!-- IF" not in content


def test_editor_tab_widget(qapp, fake_addon_dir):
    crate_dir = os.path.join(fake_addon_dir, "models", "props", "crate")
    hbat_path = os.path.join(crate_dir, "test_editor.hbat")

    tab = EditorTabWidget(file_path=hbat_path)
    try:
        assert tab.file_path == os.path.normpath(hbat_path)
        assert tab.same_folder_cb.isChecked() is True

        tab.reference_card.set_reference_path("models/props/crate/box_01.vmdl")
        assert tab.reference_card.get_reference_path() == "models/props/crate/box_01.vmdl"

        tab.save_file()
        assert os.path.isfile(hbat_path)

        with open(hbat_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("version") == 2
        assert data["process"]["reference"] == "models/props/crate/box_01.vmdl"
    finally:
        tab.deleteLater()
