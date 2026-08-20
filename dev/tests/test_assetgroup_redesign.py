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
             patch("src.settings.common.get_addon_name", return_value="test_addon"), \
             patch("src.settings.main.get_cs2_path", return_value=tmpdir), \
             patch("src.settings.common.get_cs2_path", return_value=tmpdir), \
             patch("src.common.get_cs2_path", return_value=tmpdir):
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
        assert tab.save_btn is not None
        assert tab.watch_changes_cb is not None
        assert tab.watch_changes_cb.isChecked() is False

        tab.reference_card.set_reference_path("models/props/crate/box_01.vmdl")
        assert tab.reference_card.get_reference_path() == "models/props/crate/box_01.vmdl"

        tab.watch_changes_cb.setChecked(True)
        tab.save_file()
        assert os.path.isfile(hbat_path)

        with open(hbat_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("version") == 2
        assert data["process"]["reference"] == "models/props/crate/box_01.vmdl"
        assert data["process"]["watch_changes"] is True
    finally:
        tab.deleteLater()


def test_main_window_layout_and_empty_state(qapp, fake_addon_dir):
    win = BatchCreatorMainWindow()
    try:
        # Check docks
        assert win.explorer_dock is not None
        assert win.config_dock is not None
        assert win.new_cfg_for_folder_btn is not None
        assert win.new_cfg_btn is not None
        assert win.global_watch_cb is not None
        assert win.monitoring_list is not None

        # When no tabs are open, empty state widget should be active
        assert win.tab_widget.count() == 0
        assert win.central_stack.currentWidget() == win.empty_state_widget

        # Create a new tab
        tab = win.create_new_batch_tab()
        assert win.tab_widget.count() == 1
        assert win.central_stack.currentWidget() == win.tab_widget
        assert tab.save_btn is not None
        assert tab.watch_changes_cb is not None

        # Close the tab
        win.close_tab(0)
        assert win.tab_widget.count() == 0
        assert win.central_stack.currentWidget() == win.empty_state_widget
    finally:
        win.deleteLater()


def test_file_item_watch_button_and_global_watch(qapp, fake_addon_dir):
    from src.editors.assetgroup_maker.monitor import MonitoringFileWatcher, FileItemWidget, is_watch_enabled, set_watch_enabled

    crate_dir = os.path.join(fake_addon_dir, "models", "props", "crate")
    hbat_path = os.path.join(crate_dir, "test_watch.hbat")
    with open(hbat_path, "w", encoding="utf-8") as f:
        json.dump({"version": 2, "process": {"watch_changes": True}}, f)

    widget = FileItemWidget(hbat_path)
    try:
        assert widget.watch_button is not None
        assert widget.watch_enabled is True

        # Toggle watch off
        widget.toggle_watch()
        assert widget.watch_enabled is False
        assert is_watch_enabled(hbat_path) is False

        # Toggle watch back on
        widget.toggle_watch()
        assert widget.watch_enabled is True
        assert is_watch_enabled(hbat_path) is True
    finally:
        widget.deleteLater()

    watcher = MonitoringFileWatcher(fake_addon_dir)
    try:
        assert watcher.is_global_watch_enabled() is False
        watcher.set_global_watch_enabled(True)
        assert watcher.is_global_watch_enabled() is True
    finally:
        watcher.deleteLater()


def test_asset_browser_multi_type_scan(fake_addon_dir):
    from src.widgets.model_browser.index import scan_all

    # Create dummy assets in addon
    os.makedirs(os.path.join(fake_addon_dir, "models", "props"), exist_ok=True)
    os.makedirs(os.path.join(fake_addon_dir, "materials", "props"), exist_ok=True)
    os.makedirs(os.path.join(fake_addon_dir, "smartprops"), exist_ok=True)

    with open(os.path.join(fake_addon_dir, "models", "props", "chair.vmdl"), "w") as f:
        f.write("<!-- kv3 -->")
    with open(os.path.join(fake_addon_dir, "materials", "props", "chair.vmat"), "w") as f:
        f.write("<!-- kv3 -->")
    with open(os.path.join(fake_addon_dir, "smartprops", "tree.vsmart"), "w") as f:
        f.write("<!-- kv3 -->")

    # Scan addon only
    entries = scan_all(active_addon="test_addon", addon_only=True)
    entry_paths = [e.path for e in entries]
    assert any("chair.vmdl" in p for p in entry_paths)
    assert any("chair.vmat" in p for p in entry_paths)
    assert any("tree.vsmart" in p for p in entry_paths)
    assert all(e.source == "Addon" for e in entries)


def test_prefix_and_suffix_affix_matching(fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import match_folder_assets, strip_known_affixes

    # Test affix stripper
    assert strip_known_affixes("phys_treedead") == "treedead"
    assert strip_known_affixes("treedead_phys") == "treedead"
    assert strip_known_affixes("col_crate_01") == "crate_01"
    assert strip_known_affixes("lod1_pine_tree") == "pine_tree"
    assert strip_known_affixes("pine_tree_lod1") == "pine_tree"

    # Create folder with pine trees and physics meshes
    pine_dir = os.path.join(fake_addon_dir, "models", "nature", "trees", "pine")
    os.makedirs(pine_dir, exist_ok=True)

    files_to_create = [
        "treedead.fbx", "phys_treedead.fbx",
        "treefar01.fbx", "phys_treefar01.fbx",
        "treefar02.fbx", "phys_treefar02.fbx",
        "treelarge.fbx", "phys_treelarge.fbx",
        "treemid.fbx", "phys_treemid.fbx",
        "treesmall.fbx", "phys_treesmall.fbx"
    ]
    for fn in files_to_create:
        with open(os.path.join(pine_dir, fn), "w") as f:
            f.write("FBX dummy")

    slots_def = {
        'mesh': {'label': 'Render Mesh', 'required': True},
        'collision': {'label': 'Collision Hull', 'required': False}
    }

    items = match_folder_assets(
        directory=pine_dir,
        slots=slots_def,
        extension="vmdl"
    )

    # 12 files should map to exactly 6 assets
    assert len(items) == 6
    item_names = [i.name for i in items]
    assert "treedead" in item_names
    assert "treefar01" in item_names
    assert "treesmall" in item_names

    treedead = next(i for i in items if i.name == "treedead")
    assert "mesh" in treedead.slots
    assert os.path.basename(treedead.slots["mesh"]) == "treedead.fbx"
    assert "collision" in treedead.slots
    assert os.path.basename(treedead.slots["collision"]) == "phys_treedead.fbx"
    assert treedead.status == "ready"


def test_analyzer_kv3_physics_and_render_mesh(fake_addon_dir):
    from src.editors.assetgroup_maker.analyzer import analyze_reference_file

    vmdl_content = '''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc41:version{12fc9d44-453a-4ae4-b4d9-7e2ac0bbd4e0} -->
{
    rootNode = 
    {
        _class = "RootNode"
        children = 
        [
            {
                _class = "PhysicsShapeList"
                children = 
                [
                    {
                        _class = "PhysicsHullFile"
                        filename = "models/firewatch/nature/trees/pine/phys_treedead.fbx"
                    }
                ]
            },
            {
                _class = "RenderMeshList"
                children = 
                [
                    {
                        _class = "RenderMeshFile"
                        filename = "models/firewatch/nature/trees/pine/treedead.fbx"
                    }
                ]
            }
        ]
    }
}'''
    vmdl_path = os.path.join(fake_addon_dir, "models", "nature", "treedead.vmdl")
    os.makedirs(os.path.dirname(vmdl_path), exist_ok=True)
    with open(vmdl_path, "w", encoding="utf-8") as f:
        f.write(vmdl_content)

    analysis = analyze_reference_file(vmdl_path)
    assert analysis.asset_type == "vmdl"
    assert "mesh" in analysis.slots
    assert analysis.slots["mesh"]["filename"] == "treedead.fbx"
    assert "collision" in analysis.slots
    assert analysis.slots["collision"]["filename"] == "phys_treedead.fbx"


def test_slot_assignment_dialog(qapp, fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import AssetGroupItem
    from src.editors.assetgroup_maker.widgets.slot_editor import SlotAssignmentDialog

    item = AssetGroupItem("treedead", "models/pine")
    item.available_candidates = [
        os.path.join(fake_addon_dir, "treedead.fbx"),
        os.path.join(fake_addon_dir, "phys_treedead.fbx"),
        os.path.join(fake_addon_dir, "alt_phys.fbx")
    ]
    item.slots = {
        'mesh': os.path.join(fake_addon_dir, "treedead.fbx"),
        'collision': os.path.join(fake_addon_dir, "phys_treedead.fbx")
    }

    slots_def = {
        'mesh': {'label': 'Render Mesh', 'required': True},
        'collision': {'label': 'Collision Hull', 'required': False}
    }

    dialog = SlotAssignmentDialog(item, slots_def)
    try:
        assert 'mesh' in dialog.combos
        assert 'collision' in dialog.combos
        # Change collision slot
        collision_combo = dialog.combos['collision']
        for i in range(collision_combo.count()):
            if "alt_phys.fbx" in collision_combo.itemText(i):
                collision_combo.setCurrentIndex(i)
                break

        dialog._apply_and_close()
        assert "alt_phys.fbx" in dialog.assigned_slots['collision']
    finally:
        dialog.deleteLater()



