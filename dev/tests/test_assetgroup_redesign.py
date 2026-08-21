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
    from src.editors.assetgroup_maker.objects import load_hbat_file

    crate_dir = os.path.join(fake_addon_dir, "models", "props", "crate")
    hbat_path = os.path.join(crate_dir, "test_editor.hbat")

    tab = EditorTabWidget(file_path=hbat_path)
    try:
        assert tab.file_path == os.path.normpath(hbat_path)
        assert tab.custom_output_edit.text() == ""
        assert tab.save_btn is not None
        assert tab.watch_changes_cb is not None
        assert tab.watch_changes_cb.isChecked() is False
        assert len(tab.template_manager.template_cards) >= 1

        first_card = tab.template_manager.template_cards[0]
        first_card.set_reference_path("models/props/crate/box_01.vmdl")
        assert first_card.ref_edit.text() == "models/props/crate/box_01.vmdl"

        tab.watch_changes_cb.setChecked(True)
        tab.save_file()
        assert os.path.isfile(hbat_path)

        data = load_hbat_file(hbat_path)
        assert data.get("version") == 3
        assert data["templates"][0]["reference"] == "models/props/crate/box_01.vmdl"
        assert data["settings"]["watch_changes"] is True
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
    from src.editors.assetgroup_maker.widgets.slot_editor import TemplateSlotMappingDialog

    template_data = {
        'id': 'template_0',
        'extension': 'vmdl',
        'reference': 'models/props/box.vmdl',
        'skipped_slots': []
    }

    dialog = TemplateSlotMappingDialog(template_data)
    try:
        assert 'mesh' in dialog.slot_check_boxes
        assert 'collision' in dialog.slot_check_boxes
        assert dialog.slot_check_boxes['mesh'].isChecked() is True
        assert dialog.slot_check_boxes['collision'].isChecked() is True

        # Toggle collision to skip
        dialog.slot_check_boxes['collision'].setChecked(False)
        dialog._apply_and_close()

        assert 'collision' in dialog.skipped_slots
        assert 'mesh' not in dialog.skipped_slots
    finally:
        dialog.deleteLater()


def test_kv3_hbat_io_and_no_raw_text(fake_addon_dir):
    from src.editors.assetgroup_maker.objects import load_hbat_file, save_hbat_file

    hbat_path = os.path.join(fake_addon_dir, "models", "props", "crate", "test.hbat")
    data = {
        'version': 3,
        'settings': {
            'watch_changes': True,
            'ignore_extensions': 'tga,png',
            'ignore_list': 'draft_*',
            'custom_output': 'relative_path',
            'algorithm': 0
        },
        'templates': [
            {
                'id': 'template_0',
                'extension': 'vmdl',
                'reference': 'models/props/crate/box_01.vmdl',
                'replacements': [{'from': 'box_01.fbx', 'to': '#$MESH$#'}]
            },
            {
                'id': 'template_1',
                'extension': 'vmat',
                'reference': 'materials/nature/rock_01.vmat',
                'replacements': [{'from': 'rock_01_color.png', 'to': '#$COLOR$#'}]
            }
        ]
    }

    # Save to file
    saved = save_hbat_file(hbat_path, data)
    assert saved is True
    assert os.path.isfile(hbat_path)

    # Verify file content is KeyValues3 text and does NOT have raw content
    with open(hbat_path, 'r', encoding='utf-8') as f:
        text = f.read()

    assert '<!-- kv3' in text
    assert 'version = 3' in text
    assert 'box_01.vmdl' in text
    assert 'rock_01.vmat' in text
    assert 'content =' not in text  # No raw embedded text!

    # Load back
    loaded = load_hbat_file(hbat_path)
    assert loaded['version'] == 3
    assert loaded['settings']['watch_changes'] is True
    assert len(loaded['templates']) == 2
    assert loaded['templates'][0]['extension'] == 'vmdl'
    assert loaded['templates'][1]['extension'] == 'vmat'


def test_legacy_json_automatic_conversion(fake_addon_dir):
    from src.editors.assetgroup_maker.objects import load_hbat_file

    legacy_json_path = os.path.join(fake_addon_dir, "models", "props", "crate", "legacy.hbat")
    legacy_dict = {
        "version": 2,
        "process": {
            "extension": "vmdl",
            "reference": "models/props/crate/box_01.vmdl",
            "ignore_extensions": "mb,ma,max,blend",
            "ignore_list": "temp_*",
            "custom_output": "relative_path",
            "algorithm": 0,
            "watch_changes": True
        },
        "replacements": {
            "0": {
                "replacement": [
                    "models/props/crate/box_01.fbx",
                    "#$FOLDER_PATH$#/#$MESH$#"
                ]
            }
        },
        "file": {
            "content": "<!-- kv3 raw embedded modeldoc content that should be discarded -->"
        }
    }

    with open(legacy_json_path, 'w', encoding='utf-8') as f:
        json.dump(legacy_dict, f, indent=4)

    # Load legacy file -> should auto-convert to clean v3 structure
    upgraded = load_hbat_file(legacy_json_path)

    assert upgraded['version'] == 3
    assert upgraded['settings']['watch_changes'] is True
    assert upgraded['settings']['ignore_extensions'] == "mb,ma,max,blend"
    assert upgraded['settings']['ignore_list'] == "temp_*"
    assert 'file' not in upgraded or upgraded.get('file') is None  # Raw content stripped!

    assert len(upgraded['templates']) == 1
    t0 = upgraded['templates'][0]
    assert t0['extension'] == 'vmdl'
    assert t0['reference'] == "models/props/crate/box_01.vmdl"
    assert len(t0['replacements']) == 1
    assert t0['replacements'][0]['from'] == "models/props/crate/box_01.fbx"
    assert t0['replacements'][0]['to'] == "#$FOLDER_PATH$#/#$MESH$#"


def test_multi_template_matching_vmdl_and_vmat(fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import match_multi_template_folder_assets

    target_dir = os.path.join(fake_addon_dir, "models", "props", "multi_test")
    os.makedirs(target_dir, exist_ok=True)

    # 4 FBX files + 2 VMAT/texture files
    files = [
        "crate_small.fbx",
        "crate_small_phys.fbx",
        "crate_large.fbx",
        "crate_large_phys.fbx",
        "wood_bark_color.png",
        "wood_bark_normal.png"
    ]
    for fn in files:
        with open(os.path.join(target_dir, fn), "w") as f:
            f.write("dummy")

    templates = [
        {
            'id': 'template_vmdl',
            'extension': 'vmdl',
            'reference': 'models/props/crate/box_01.vmdl'
        },
        {
            'id': 'template_vmat',
            'extension': 'vmat',
            'reference': 'materials/nature/rock_01.vmat'
        }
    ]

    slots_map = {
        'template_vmdl': {
            'mesh': {'label': 'Render Mesh', 'required': True},
            'collision': {'label': 'Collision Hull', 'required': False}
        },
        'template_vmat': {
            'color': {'label': 'Color Map', 'required': True},
            'normal': {'label': 'Normal Map', 'required': False}
        }
    }

    items = match_multi_template_folder_assets(
        directory=target_dir,
        templates=templates,
        analyzed_slots_map=slots_map
    )

    # Should have matched crate_small & crate_large for VMDL, and wood_bark for VMAT
    assert len(items) == 3

    vmdl_items = [i for i in items if i.extension == 'vmdl']
    vmat_items = [i for i in items if i.extension == 'vmat']

    assert len(vmdl_items) == 2
    assert {i.name for i in vmdl_items} == {'crate_small', 'crate_large'}
    for vi in vmdl_items:
        assert 'mesh' in vi.slots
        assert 'collision' in vi.slots
        assert vi.target_output.endswith('.vmdl')

    assert len(vmat_items) == 1
    assert vmat_items[0].name == 'wood_bark'
    assert 'color' in vmat_items[0].slots
    assert 'normal' in vmat_items[0].slots
    assert vmat_items[0].target_output == 'wood_bark.vmat'


def test_multi_template_batch_processing(fake_addon_dir):
    from src.editors.assetgroup_maker.process import perform_batch_processing

    # Setup template references
    vmdl_ref = os.path.join(fake_addon_dir, "models", "props", "ref_model.vmdl")
    with open(vmdl_ref, "w") as f:
        f.write('<!-- kv3 -->\n{\n  mesh = "#$FOLDER_PATH$#/#$MESH$#"\n  name = "#$ASSET_NAME$#"\n}')

    vmat_ref = os.path.join(fake_addon_dir, "materials", "props", "ref_mat.vmat")
    os.makedirs(os.path.dirname(vmat_ref), exist_ok=True)
    with open(vmat_ref, "w") as f:
        f.write('<!-- kv3 -->\n{\n  color = "#$FOLDER_PATH$#/#$COLOR$#"\n  mat_name = "#$ASSET_NAME$#"\n}')

    # Setup source directory with 2 models and 1 texture
    batch_dir = os.path.join(fake_addon_dir, "models", "props", "batch_run")
    os.makedirs(batch_dir, exist_ok=True)

    with open(os.path.join(batch_dir, "box_a.fbx"), "w") as f: f.write("fbx")
    with open(os.path.join(batch_dir, "box_b.fbx"), "w") as f: f.write("fbx")
    with open(os.path.join(batch_dir, "wood_color.png"), "w") as f: f.write("png")

    hbat_path = os.path.join(batch_dir, "batch_run.hbat")
    config = {
        'version': 3,
        'settings': {
            'watch_changes': False,
            'custom_output': 'relative_path',
            'algorithm': 0
        },
        'templates': [
            {
                'id': 'tpl_vmdl',
                'extension': 'vmdl',
                'reference': 'models/props/ref_model.vmdl',
                'replacements': []
            },
            {
                'id': 'tpl_vmat',
                'extension': 'vmat',
                'reference': 'materials/props/ref_mat.vmat',
                'replacements': []
            }
        ]
    }

    created = perform_batch_processing(hbat_path, config_data=config)

    # Should create box_a.vmdl, box_b.vmdl, and wood.vmat!
    assert len(created) == 3
    created_basenames = [os.path.basename(p) for p in created]
    assert "box_a.vmdl" in created_basenames
    assert "box_b.vmdl" in created_basenames
    assert "wood.vmat" in created_basenames

    # Verify generated content
    box_a_vmdl = os.path.join(batch_dir, "box_a.vmdl")
    assert os.path.isfile(box_a_vmdl)
    with open(box_a_vmdl, "r") as f:
        c = f.read()
        assert 'name = "box_a"' in c
        assert 'box_a.fbx' in c

    wood_vmat = os.path.join(batch_dir, "wood.vmat")
    assert os.path.isfile(wood_vmat)
    with open(wood_vmat, "r") as f:
        c = f.read()
        assert 'mat_name = "wood"' in c
        assert 'wood_color.png' in c


def test_create_new_config_for_selected_folder_without_browser(qapp, fake_addon_dir, monkeypatch):
    from unittest.mock import MagicMock
    from src.editors.assetgroup_maker.main import BatchCreatorMainWindow
    from PySide6.QtWidgets import QFileDialog

    # Ensure QFileDialog is never called
    mock_file_dialog = MagicMock()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", mock_file_dialog)

    win = BatchCreatorMainWindow()
    try:
        target_dir = os.path.join(fake_addon_dir, "models", "props", "crate")
        os.makedirs(target_dir, exist_ok=True)

        # Mock selected folder in explorer
        monkeypatch.setattr(win, "_get_selected_folder_from_explorer", lambda: target_dir)

        # 1. Create first config
        win.create_new_config_for_selected_folder()

        mock_file_dialog.assert_not_called()
        expected_first = os.path.join(target_dir, "crate.hbat")
        assert os.path.isfile(expected_first)
        assert win.tab_widget.count() == 1
        assert os.path.normpath(win.tab_widget.currentWidget().file_path) == os.path.normpath(expected_first)

        # 2. Create second config in same folder -> should create crate_1.hbat without prompting
        win.create_new_config_for_selected_folder()

        mock_file_dialog.assert_not_called()
        expected_second = os.path.join(target_dir, "crate_1.hbat")
        assert os.path.isfile(expected_second)
        assert win.tab_widget.count() == 2
        assert os.path.normpath(win.tab_widget.currentWidget().file_path) == os.path.normpath(expected_second)
    finally:
        win.deleteLater()


def test_per_template_ignore_settings(fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import match_multi_template_folder_assets

    target_dir = os.path.join(fake_addon_dir, "models", "props", "ignore_test")
    os.makedirs(target_dir, exist_ok=True)

    files = [
        "barrel_01.fbx",
        "barrel_01_phys.fbx",
        "barrel_01_color.png",
        "barrel_01_normal.png",
        "temp_trash.fbx",
        "draft_texture.png"
    ]
    for fn in files:
        with open(os.path.join(target_dir, fn), "w") as f:
            f.write("dummy")

    templates = [
        {
            'id': 'tpl_vmdl',
            'extension': 'vmdl',
            'reference': '',
            'ignore_extensions': 'png,jpg,tga',
            'ignore_list': 'temp_*'
        },
        {
            'id': 'tpl_vmat',
            'extension': 'vmat',
            'reference': '',
            'ignore_extensions': 'fbx,obj',
            'ignore_list': 'draft_*'
        }
    ]

    items = match_multi_template_folder_assets(
        directory=target_dir,
        templates=templates
    )

    vmdl_items = [i for i in items if i.extension == 'vmdl']
    vmat_items = [i for i in items if i.extension == 'vmat']

    # VMDL should only have barrel_01 (temp_trash ignored by list, pngs ignored by ext)
    assert len(vmdl_items) == 1
    assert vmdl_items[0].name == 'barrel_01'
    assert 'mesh' in vmdl_items[0].slots

    # VMAT should only have barrel_01 (draft_texture ignored by list, fbx ignored by ext)
    assert len(vmat_items) == 1
    assert vmat_items[0].name == 'barrel_01'
    assert 'color' in vmat_items[0].slots
    assert 'normal' in vmat_items[0].slots


def test_material_shader_slots_orm_emissive_height(fake_addon_dir):
    from src.editors.assetgroup_maker.analyzer import analyze_reference_file
    from src.editors.assetgroup_maker.matcher import match_folder_assets

    vmat_path = os.path.join(fake_addon_dir, "materials", "props", "complex_box.vmat")
    os.makedirs(os.path.dirname(vmat_path), exist_ok=True)
    vmat_content = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
Layer0
{
    shader "csgo_environment.vfx"
    g_tColor = resource:"materials/props/box_color.png"
    g_tNormal = resource:"materials/props/box_normal.png"
    g_tORM = resource:"materials/props/box_orm.png"
    g_tHeight = resource:"materials/props/box_height.png"
    g_tEmissiveMask = resource:"materials/props/box_emissive.png"
    g_tTranslucency = resource:"materials/props/box_opacity.png"
}
"""
    with open(vmat_path, "w", encoding="utf-8") as f:
        f.write(vmat_content)

    analysis = analyze_reference_file(vmat_path)
    assert analysis.asset_type == "vmat"
    assert "color" in analysis.slots
    assert "normal" in analysis.slots
    assert "orm" in analysis.slots
    assert "height" in analysis.slots
    assert "emissive" in analysis.slots
    assert "opacity" in analysis.slots

    # Test matcher pairing with ORM and emissive textures
    tex_dir = os.path.join(fake_addon_dir, "materials", "props", "test_mats")
    os.makedirs(tex_dir, exist_ok=True)

    files = [
        "crate_color.png",
        "crate_normal.png",
        "crate_orm.png",
        "crate_height.png",
        "crate_emissive.png"
    ]
    for fn in files:
        with open(os.path.join(tex_dir, fn), "w") as f:
            f.write("tex")

    items = match_folder_assets(
        directory=tex_dir,
        slots=analysis.slots,
        extension="vmat"
    )

    assert len(items) == 1
    crate_mat = items[0]
    assert crate_mat.name == "crate"
    assert "color" in crate_mat.slots
    assert "normal" in crate_mat.slots
    assert "orm" in crate_mat.slots
    assert "height" in crate_mat.slots
    assert "emissive" in crate_mat.slots
    assert crate_mat.status == "ready"


def test_ignore_list_spaces_and_prefix_patterns(fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import match_folder_assets

    target_dir = os.path.join(fake_addon_dir, "models", "props", "filter_test")
    os.makedirs(target_dir, exist_ok=True)

    files = [
        "treedead.fbx",
        "phys_treedead.fbx",
        "treedead.png",
        "treedead.vmat",
        "rock.blend",
        "rock.fbx"
    ]
    for fn in files:
        with open(os.path.join(target_dir, fn), "w") as f:
            f.write("dummy")

    # Comma-separated list with spaces, prefix pattern 'phys_', and extensions
    ignore_str = "mb,ma,max,st,blend,blend1, vmdl, vmat,vsmart,tga,png,jpg,exr,hdr, phys_"

    items = match_folder_assets(
        directory=target_dir,
        slots={'mesh': {'label': 'Render Mesh', 'required': True}},
        extension="vmdl",
        ignore_extensions_str=ignore_str,
        filter_mode="exclude"
    )

    item_names = [i.name for i in items]
    assert "treedead" in item_names
    assert "rock" in item_names
    assert "phys_treedead" not in item_names

    # treedead should only have treedead.fbx as mesh, phys_treedead was ignored
    treedead_item = next(i for i in items if i.name == "treedead")
    assert os.path.basename(treedead_item.slots['mesh']) == "treedead.fbx"
    assert 'collision' not in treedead_item.slots


def test_include_filter_mode(fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import match_folder_assets

    target_dir = os.path.join(fake_addon_dir, "models", "props", "include_test")
    os.makedirs(target_dir, exist_ok=True)

    files = [
        "box_01.fbx",
        "box_01_col.obj",
        "box_01.blend",
        "box_01_color.png",
        "box_01_normal.tga",
        "trash_note.txt"
    ]
    for fn in files:
        with open(os.path.join(target_dir, fn), "w") as f:
            f.write("dummy")

    # In INCLUDE mode: only process fbx and obj
    include_str = " fbx, obj "
    items = match_folder_assets(
        directory=target_dir,
        slots={'mesh': {'label': 'Render Mesh', 'required': True}},
        extension="vmdl",
        ignore_extensions_str=include_str,
        filter_mode="include"
    )

    assert len(items) == 1
    assert items[0].name == "box_01"
    assert os.path.basename(items[0].slots['mesh']) == "box_01.fbx"


def test_template_skipped_slots(fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import match_folder_assets
    from src.editors.assetgroup_maker.process import render_asset_template, perform_batch_processing

    batch_dir = os.path.join(fake_addon_dir, "models", "props", "skip_test")
    os.makedirs(batch_dir, exist_ok=True)

    with open(os.path.join(batch_dir, "pillar.fbx"), "w") as f:
        f.write("mesh")

    # Template defines required mesh and required collision
    slots_def = {
        'mesh': {'label': 'Render Mesh', 'required': True},
        'collision': {'label': 'Collision Mesh', 'required': True}
    }

    # When collision is in skipped_slots, status should be READY instead of ERROR
    items = match_folder_assets(
        directory=batch_dir,
        slots=slots_def,
        extension="vmdl",
        skipped_slots=["collision"]
    )

    assert len(items) == 1
    pillar = items[0]
    assert pillar.status == "ready"

    # Test rendering skips collision conditional block
    tpl_content = """<!-- kv3 -->
{
    mesh = "#$MESH$#"
    <!-- IF COLLISION -->
    collision = "#$COLLISION$#"
    <!-- ENDIF -->
}"""
    rendered = render_asset_template(
        content_template=tpl_content,
        asset_item=pillar,
        relative_batch_path="models/props/skip_test",
        skipped_slots=["collision"]
    )
    assert 'mesh = "pillar.fbx"' in rendered
    assert 'collision' not in rendered


def test_asset_table_context_menu_show(qapp, fake_addon_dir, monkeypatch):
    from unittest.mock import MagicMock
    from PySide6.QtCore import QPoint
    import src.editors.assetgroup_maker.widgets.asset_table as at_mod
    from src.editors.assetgroup_maker.widgets.asset_table import AssetTableWidget
    from src.editors.assetgroup_maker.matcher import AssetGroupItem

    widget = AssetTableWidget()
    try:
        item = AssetGroupItem("treedead", "models/props")
        item.target_output = "models/props/treedead.vmdl"
        widget.set_items([item])

        # Select row 0
        widget.table.selectRow(0)

        # Mock QMenu to verify menu builds and doesn't crash
        mock_menu = MagicMock()
        monkeypatch.setattr(at_mod, "QMenu", lambda *args, **kwargs: mock_menu)

        widget._show_context_menu(QPoint(10, 10))
        mock_menu.exec.assert_called_once()
    finally:
        widget.deleteLater()


def test_firewatch_trees_pine_scenario(fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import match_multi_template_folder_assets

    pine_dir = os.path.join(fake_addon_dir, "models", "firewatch", "nature", "trees", "pine")
    os.makedirs(pine_dir, exist_ok=True)

    # 1. Models
    tree_names = ["treedead", "treefar01", "treefar02", "treelarge", "treemid", "treesmall"]
    for t in tree_names:
        with open(os.path.join(pine_dir, f"{t}.fbx"), "w") as f:
            f.write("mesh")
        with open(os.path.join(pine_dir, f"phys_{t}.fbx"), "w") as f:
            f.write("phys")

    # 2. Textures for Material
    with open(os.path.join(pine_dir, "armor_color.png"), "w") as f:
        f.write("color_tex")
    with open(os.path.join(pine_dir, "armor_normal.png"), "w") as f:
        f.write("normal_tex")

    templates = [
        {
            'id': 'template_vmdl',
            'extension': 'vmdl',
            'reference': 'models/firewatch/nature/trees/pine/treedead.vmdl',
            'filter_mode': 'include',
            'ignore_extensions': 'fbx',
            'ignore_list': 'temp_*, draft_*, *backup*'
        },
        {
            'id': 'template_vmat',
            'extension': 'vmat',
            'reference': 'models/firewatch/nature/trees/pine/armor.vmat',
            'filter_mode': 'include',
            'ignore_extensions': 'color',
            'ignore_list': 'temp_*, draft_*, *backup*'
        }
    ]

    items = match_multi_template_folder_assets(
        directory=pine_dir,
        templates=templates
    )

    vmdl_items = [i for i in items if i.extension == 'vmdl']
    vmat_items = [i for i in items if i.extension == 'vmat']

    # 1. ModelDoc items should only be the 6 tree meshes
    assert len(vmdl_items) == 6
    for item in vmdl_items:
        assert item.name in tree_names
        assert item.target_output == f"{item.name}.vmdl"
        assert "mesh" in item.slots
        assert "collision" in item.slots
        assert item.slots["mesh"].endswith(f"{item.name}.fbx")
        assert item.slots["collision"].endswith(f"phys_{item.name}.fbx")

    # 2. Material items should ONLY be armor.vmat, NOT treedead.vmat!
    assert len(vmat_items) == 1
    armor_vmat = vmat_items[0]
    assert armor_vmat.name == "armor"
    assert armor_vmat.target_output == "armor.vmat"
    assert "color" in armor_vmat.slots
    assert armor_vmat.slots["color"].endswith("armor_color.png")
    assert "normal" in armor_vmat.slots
    assert armor_vmat.slots["normal"].endswith("armor_normal.png")
    assert "collision" not in armor_vmat.slots


def test_firewatch_multi_template_batch_execution(fake_addon_dir):
    from src.editors.assetgroup_maker.process import perform_batch_processing
    from src.editors.assetgroup_maker.objects import save_hbat_file

    pine_dir = os.path.join(fake_addon_dir, "models", "firewatch", "nature", "trees", "pine")
    os.makedirs(pine_dir, exist_ok=True)
    hbat_path = os.path.join(fake_addon_dir, "models", "firewatch", "nature", "trees", "pine.hbat")

    # 1. Create reference VMDL file
    ref_vmdl = os.path.join(pine_dir, "treedead.vmdl")
    vmdl_raw = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec4278-4302-4dd9-9b53-44f42a1f104c} -->
{
    rootNode = 
    {
        _class = "RootNode"
        children = 
        [
            {
                _class = "RenderMeshFile"
                filename = "models/firewatch/nature/trees/pine/treedead.fbx"
            },
            {
                _class = "PhysicsHullFile"
                filename = "models/firewatch/nature/trees/pine/phys_treedead.fbx"
            },
        ]
    }
}
"""
    with open(ref_vmdl, "w", encoding="utf-8") as f:
        f.write(vmdl_raw)

    # 2. Create reference VMAT file
    ref_vmat = os.path.join(pine_dir, "armor.vmat")
    vmat_raw = """<!-- kv3 -->
Layer0
{
    shader "csgo_environment.vfx"
    g_tColor = resource:"materials/firewatch/nature/trees/pine/armor_color.png"
    g_tNormal = resource:"materials/firewatch/nature/trees/pine/armor_normal.png"
}
"""
    with open(ref_vmat, "w", encoding="utf-8") as f:
        f.write(vmat_raw)

    # 3. Create models and texture source files
    tree_names = ["treedead", "treefar01", "treefar02", "treelarge", "treemid", "treesmall"]
    for t in tree_names:
        with open(os.path.join(pine_dir, f"{t}.fbx"), "w") as f:
            f.write(f"{t} mesh")
        with open(os.path.join(pine_dir, f"phys_{t}.fbx"), "w") as f:
            f.write(f"{t} phys")

    with open(os.path.join(pine_dir, "armor_color.png"), "w") as f:
        f.write("armor color")
    with open(os.path.join(pine_dir, "armor_normal.png"), "w") as f:
        f.write("armor normal")

    # 4. Save and run batch config
    config_data = {
        'version': 3,
        'settings': {
            'watch_changes': False,
            'custom_output': '',
            'algorithm': 0
        },
        'templates': [
            {
                'id': 'template_vmdl',
                'extension': 'vmdl',
                'reference': 'models/firewatch/nature/trees/pine/treedead.vmdl',
                'filter_mode': 'include',
                'ignore_extensions': 'fbx',
                'ignore_list': 'temp_*, draft_*, *backup*'
            },
            {
                'id': 'template_vmat',
                'extension': 'vmat',
                'reference': 'models/firewatch/nature/trees/pine/armor.vmat',
                'filter_mode': 'include',
                'ignore_extensions': 'color',
                'ignore_list': 'temp_*, draft_*, *backup*'
            }
        ]
    }
    save_hbat_file(hbat_path, config_data)

    created = perform_batch_processing(
        file_path=hbat_path,
        config_data=config_data
    )

    assert len(created) >= 5  # 5 other tree vmdls (treedead was the reference)

    for other_tree in ["treefar01", "treefar02", "treelarge", "treemid", "treesmall"]:
        vmdl_file = os.path.join(pine_dir, f"{other_tree}.vmdl")
        assert os.path.isfile(vmdl_file)
        with open(vmdl_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert f"{other_tree}.fbx" in content
        assert f"phys_{other_tree}.fbx" in content


def test_template_filter_and_ignore_serialization(fake_addon_dir):
    from src.editors.assetgroup_maker.objects import save_hbat_file, load_hbat_file

    save_path = os.path.join(fake_addon_dir, "models", "test_roundtrip.hbat")
    data_to_save = {
        'version': 3,
        'settings': {
            'watch_changes': True,
            'filter_mode': 'include',
            'ignore_extensions': 'fbx, obj',
            'ignore_list': 'draft_*, temp_*',
            'custom_output': 'models/custom',
            'algorithm': 1,
            'custom_files': []
        },
        'templates': [
            {
                'id': 'template_0',
                'extension': 'vmdl',
                'reference': 'models/props/box.vmdl',
                'filter_mode': 'include',
                'ignore_extensions': 'fbx',
                'ignore_list': 'test_ignore_*',
                'skipped_slots': ['collision', 'lod1'],
                'custom_tokens': {'mesh': '#$CUSTOM_MESH$#'},
                'replacements': [{'from': 'box', 'to': '#$ASSET_NAME$#'}]
            },
            {
                'id': 'template_1',
                'extension': 'vmat',
                'reference': 'materials/props/box.vmat',
                'filter_mode': 'exclude',
                'ignore_extensions': 'png, tga',
                'ignore_list': 'backup_*',
                'skipped_slots': ['roughness'],
                'custom_tokens': {},
                'replacements': []
            }
        ]
    }

    assert save_hbat_file(save_path, data_to_save) is True
    assert os.path.isfile(save_path)

    loaded = load_hbat_file(save_path)
    assert loaded['version'] == 3
    assert loaded['settings']['filter_mode'] == 'include'
    assert loaded['settings']['ignore_extensions'] == 'fbx, obj'
    assert loaded['settings']['ignore_list'] == 'draft_*, temp_*'
    assert loaded['settings']['watch_changes'] is True

    assert len(loaded['templates']) == 2
    t0 = loaded['templates'][0]
    assert t0['id'] == 'template_0'
    assert t0['filter_mode'] == 'include'
    assert t0['ignore_extensions'] == 'fbx'
    assert t0['ignore_list'] == 'test_ignore_*'
    assert t0['skipped_slots'] == ['collision', 'lod1']
    assert t0['custom_tokens'] == {'mesh': '#$CUSTOM_MESH$#'}

    t1 = loaded['templates'][1]
    assert t1['id'] == 'template_1'
    assert t1['filter_mode'] == 'exclude'
    assert t1['ignore_extensions'] == 'png, tga'
    assert t1['ignore_list'] == 'backup_*'
    assert t1['skipped_slots'] == ['roughness']


def test_preview_equals_output_11_assets(fake_addon_dir):
    from src.editors.assetgroup_maker.matcher import match_multi_template_folder_assets
    from src.editors.assetgroup_maker.process import perform_batch_processing
    from src.editors.assetgroup_maker.objects import save_hbat_file

    pine_dir = os.path.join(fake_addon_dir, "models", "firewatch", "nature", "trees", "pine")
    os.makedirs(pine_dir, exist_ok=True)
    hbat_path = os.path.join(fake_addon_dir, "models", "firewatch", "nature", "trees", "pine.hbat")

    # 1. 6 Models
    tree_names = ["treedead", "treefar01", "treefar02", "treelarge", "treemid", "treesmall"]
    for t in tree_names:
        with open(os.path.join(pine_dir, f"{t}.fbx"), "w") as f:
            f.write("mesh")
        with open(os.path.join(pine_dir, f"phys_{t}.fbx"), "w") as f:
            f.write("phys")

    # 2. 5 Materials
    mat_names = ["armor", "ash", "bear_pelt", "bed_double", "bed_single"]
    for m in mat_names:
        with open(os.path.join(pine_dir, f"{m}_color.tga"), "w") as f:
            f.write("color")
        with open(os.path.join(pine_dir, f"{m}_normal.tga"), "w") as f:
            f.write("normal")

    # 3. Create dummy reference templates
    with open(os.path.join(pine_dir, "treedead.vmdl"), "w") as f:
        f.write('<!-- kv3 -->\n{\n filename = "models/firewatch/nature/trees/pine/treedead.fbx"\n}\n')
    with open(os.path.join(pine_dir, "armor.vmat"), "w") as f:
        f.write('<!-- kv3 -->\nLayer0\n{\n g_tColor = resource:"materials/firewatch/nature/trees/pine/armor_color.tga"\n}\n')

    # Config matching user screenshot:
    # Global ignore: Exclude with large blacklist
    # Templates: Include with empty include extensions (placeholder) and ignore list
    config_data = {
        'version': 3,
        'settings': {
            'watch_changes': False,
            'filter_mode': 'exclude',
            'ignore_extensions': 'mb,ma,max,st,blend,blend1,vmdl,vmat,vsmart,tga,png,jpg,exr,hdr,phys_',
            'ignore_list': 'temp_*, draft_*, *backup*, .git*',
            'custom_output': '',
            'algorithm': 0
        },
        'templates': [
            {
                'id': 'template_vmdl',
                'extension': 'vmdl',
                'reference': 'models/firewatch/nature/trees/pine/treedead.vmdl',
                'filter_mode': 'include',
                'ignore_extensions': '',
                'ignore_list': 'temp_*, draft_*, *backup*'
            },
            {
                'id': 'template_vmat',
                'extension': 'vmat',
                'reference': 'models/firewatch/nature/trees/pine/armor.vmat',
                'filter_mode': 'include',
                'ignore_extensions': '',
                'ignore_list': 'temp_*, draft_*, *backup*'
            }
        ]
    }
    save_hbat_file(hbat_path, config_data)

    # 1. Preview Matching check (treedead.vmdl and armor.vmat exist in folder as references -> excluded from overwrite)
    matched_items = match_multi_template_folder_assets(
        directory=pine_dir,
        templates=config_data['templates'],
        settings=config_data['settings']
    )
    assert len(matched_items) == 9

    # 2. Batch Processing Output check
    created_files = perform_batch_processing(
        file_path=hbat_path,
        config_data=config_data
    )
    assert len(created_files) == 9


def test_editor_tab_splitter_and_scroll_bar(qapp, fake_addon_dir):
    from PySide6.QtWidgets import QSplitter, QScrollArea
    from PySide6.QtCore import Qt

    crate_dir = os.path.join(fake_addon_dir, "models", "props", "crate")
    hbat_path = os.path.join(crate_dir, "test_splitter.hbat")

    tab = EditorTabWidget(file_path=hbat_path)
    try:
        # Check splitter existence and properties
        assert hasattr(tab, "splitter")
        assert isinstance(tab.splitter, QSplitter)
        assert tab.splitter.orientation() == Qt.Vertical
        assert tab.splitter.childrenCollapsible() is False
        assert tab.splitter.count() == 2
        assert tab.splitter.widget(0) == tab.template_manager
        assert tab.splitter.widget(1) == tab.asset_table

        # Check template manager scroll area
        tm = tab.template_manager
        assert hasattr(tm, "scroll_area")
        assert isinstance(tm.scroll_area, QScrollArea)
        assert tm.scroll_area.widgetResizable() is True
        assert tm.scroll_content is not None
        assert tm.cards_layout is not None

        # Add multiple templates to test scrolling container
        card1 = tm.add_template({"id": "t1", "extension": "vmat", "reference": "materials/test.vmat"})
        card2 = tm.add_template({"id": "t2", "extension": "vsmart", "reference": "smartprops/test.vsmart"})
        assert len(tm.template_cards) >= 3
        assert tm.cards_layout.count() >= 3

        # Test splitter moved callback saves state
        tab._on_splitter_moved(300, 0)
        from src.settings.main import get_settings_value
        saved_state = get_settings_value("AssetGroupMaker", "editor_splitter_state")
        assert saved_state is not None
        assert len(saved_state) > 0
    finally:
        tab.deleteLater()


def test_main_window_dock_rescaling_and_persistence(qapp, fake_addon_dir):
    from PySide6.QtCore import Qt
    from src.settings.main import get_settings_value, set_settings_value

    win = BatchCreatorMainWindow()
    try:
        # Verify minimum widths for flexible layout rescaling
        assert win.explorer_dock.minimumWidth() >= 180
        assert win.config_dock.minimumWidth() >= 180
        assert win.central_container.minimumWidth() >= 260

        # Test saving layout state
        win._save_layout_state()
        geo = get_settings_value("AssetGroupMaker", "geometry")
        state = get_settings_value("AssetGroupMaker", "window_state")
        assert geo is not None
        assert state is not None

        # Test restoring layout state
        win._restore_layout_state()
    finally:
        win.deleteLater()


def test_assetgroup_maker_uses_system_file_dialogs(qapp, fake_addon_dir, monkeypatch):
    from unittest.mock import MagicMock
    from PySide6.QtWidgets import QFileDialog
    from src.editors.assetgroup_maker.main import BatchCreatorMainWindow

    mock_open_file = MagicMock(return_value=("", ""))
    mock_save_file = MagicMock(return_value=("", ""))
    mock_existing_dir = MagicMock(return_value="")

    monkeypatch.setattr(QFileDialog, "getOpenFileName", mock_open_file)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", mock_save_file)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", mock_existing_dir)

    win = BatchCreatorMainWindow()
    try:
        # 1. Open file dialog in main window
        win._open_file_dialog()
        mock_open_file.assert_called_once()
        _, kwargs = mock_open_file.call_args
        opts = kwargs.get("options")
        if opts is not None:
            assert not (opts & QFileDialog.Option.DontUseNativeDialog)

        # 2. Save file dialog in main window
        win.create_new_config_dialog(target_folder=fake_addon_dir, force_file_dialog=True)
        mock_save_file.assert_called_once()
        _, kwargs = mock_save_file.call_args
        opts = kwargs.get("options")
        if opts is not None:
            assert not (opts & QFileDialog.Option.DontUseNativeDialog)

        # 3. Editor tab browse output and save
        tab = win.create_new_batch_tab()
        if tab:
            tab._on_browse_output()
            mock_existing_dir.assert_called_once()
            _, kwargs = mock_existing_dir.call_args
            opts = kwargs.get("options")
            if opts is not None:
                assert not (opts & QFileDialog.Option.DontUseNativeDialog)

            tab.save_file()
            assert mock_save_file.call_count == 2
            _, kwargs = mock_save_file.call_args
            opts = kwargs.get("options")
            if opts is not None:
                assert not (opts & QFileDialog.Option.DontUseNativeDialog)
    finally:
        win.deleteLater()








