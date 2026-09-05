import os
import sys
import json
import tempfile
import pytest
from unittest.mock import patch
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_dir = os.path.join(repo_root, "Hammer5ToolsGUI")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from gui.editors.assetgroup_maker.monitor import MonitoringFileWatcher, read_reference_from_file, get_reference_asset_path


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.parametrize("enabled", [False, True])
def test_monitor_watch_status_updates_editor_without_feedback(qapp, tmp_path, enabled):
    from PySide6.QtWidgets import QTabWidget, QWidget
    from gui.editors.assetgroup_maker.editor_tab import EditorTabWidget
    from gui.editors.assetgroup_maker.main import BatchCreatorMainWindow

    with patch.object(EditorTabWidget, '_apply_default_data'):
        editor = EditorTabWidget()
        other = EditorTabWidget()
        unsaved = EditorTabWidget()
    tabs = QTabWidget()
    try:
        editor.file_path = str(tmp_path / 'profile.hbat')
        other.file_path = str(tmp_path / 'other.hbat')
        for widget in (editor, other, unsaved, QWidget()):
            tabs.addTab(widget, 'Profile')
        editor.watch_changes_cb.blockSignals(True)
        editor.watch_changes_cb.setChecked(not enabled)
        editor.watch_changes_cb.blockSignals(False)
        changes = []
        editor.watch_changes_cb.toggled.connect(changes.append)

        BatchCreatorMainWindow._on_monitor_watch_status_changed(
            SimpleNamespace(tab_widget=tabs), editor.file_path.upper(), enabled
        )

        assert editor.watch_changes_cb.isChecked() is enabled
        assert not editor.watch_changes_cb.signalsBlocked()
        assert changes == []
        assert not editor.has_unsaved_changes()
        assert other.watch_changes_cb.isChecked()
        assert unsaved.watch_changes_cb.isChecked()
        with patch.object(editor.template_manager, 'get_data', return_value={'settings': {}}), \
                patch('gui.editors.assetgroup_maker.editor_tab.save_hbat_file', return_value=True) as save, \
                patch.object(MonitoringFileWatcher, '_instances', []):
            assert editor.save_file()
        assert save.call_args.args[1]['settings']['watch_changes'] is enabled
    finally:
        tabs.close()
        tabs.deleteLater()


@pytest.fixture
def fake_addon_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        addon_path = os.path.normpath(os.path.join(tmpdir, "content", "csgo_addons", "test_addon"))
        os.makedirs(os.path.join(addon_path, "models", "props", "crate"), exist_ok=True)
        os.makedirs(os.path.join(addon_path, "materials", "nature"), exist_ok=True)
        os.makedirs(os.path.join(addon_path, "smartprops", "dev"), exist_ok=True)
        os.makedirs(os.path.join(addon_path, "sounds", "weapons"), exist_ok=True)
        with patch("gui.editors.assetgroup_maker.monitor.get_addon_dir", return_value=addon_path), \
             patch("gui.settings.common.get_addon_dir", return_value=addon_path), \
             patch("gui.widgets.explorer.actions.get_addon_dir", return_value=addon_path):
            yield addon_path


def test_is_file_in_allowed_folder_forward_and_backward_slashes(qapp, fake_addon_dir):
    watcher = MonitoringFileWatcher(fake_addon_dir)
    try:
        # Forward slashes (Qt style)
        fwd_path = f"{fake_addon_dir.replace(os.sep, '/')}/models/props/crate/box.hbat"
        assert watcher.is_file_in_allowed_folder(fwd_path) is True

        # Backward slashes (Windows style)
        back_path = f"{fake_addon_dir}\\materials\\nature\\grass.hbat"
        assert watcher.is_file_in_allowed_folder(back_path) is True

        # SmartProps
        smart_path = f"{fake_addon_dir}/smartprops/dev/tree.hbat"
        assert watcher.is_file_in_allowed_folder(smart_path) is True

        # Disallowed folder
        sound_path = f"{fake_addon_dir}/sounds/weapons/gun.hbat"
        assert watcher.is_file_in_allowed_folder(sound_path) is False
    finally:
        watcher.close()


def test_track_new_file(qapp, fake_addon_dir):
    watcher = MonitoringFileWatcher(fake_addon_dir)
    try:
        hbat_path = os.path.join(fake_addon_dir, "models", "props", "crate", "box.hbat")
        # Write valid dummy hbat
        with open(hbat_path, "w") as f:
            json.dump({"process": {"reference": ""}, "replacements": {}, "file": {"content": ""}}, f)

        # Track new file
        added = watcher.track_new_file(hbat_path)
        assert added is True
        norm_path = os.path.normpath(hbat_path)
        assert norm_path in watcher.file_widgets
        assert watcher.count() >= 1

        # Non-hbat should return False
        assert watcher.track_new_file(os.path.join(fake_addon_dir, "models", "props", "crate", "box.vmdl")) is False

        # Disallowed folder should return False
        disallowed_path = os.path.join(fake_addon_dir, "sounds", "weapons", "sound.hbat")
        assert watcher.track_new_file(disallowed_path) is False
    finally:
        watcher.close()


def test_notify_new_file(qapp, fake_addon_dir):
    watcher = MonitoringFileWatcher(fake_addon_dir)
    try:
        hbat_path = os.path.join(fake_addon_dir, "materials", "nature", "rock.hbat")
        with open(hbat_path, "w") as f:
            json.dump({"process": {"reference": ""}, "replacements": {}, "file": {"content": ""}}, f)

        # Call class method notify_new_file
        MonitoringFileWatcher.notify_new_file(hbat_path)

        norm_path = os.path.normpath(hbat_path)
        assert norm_path in watcher.file_widgets
    finally:
        watcher.close()


def test_quick_config_file_notifies_watcher(qapp, fake_addon_dir):
    from gui.widgets.explorer.actions import QuickConfigFile

    watcher = MonitoringFileWatcher(fake_addon_dir)
    try:
        # Create a dummy .vmdl file inside a subfolder
        vmdl_dir = os.path.join(fake_addon_dir, "models", "props", "crate")
        vmdl_path = os.path.join(vmdl_dir, "crate_small.vmdl")
        with open(vmdl_path, "w") as f:
            f.write('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->\n{\n rootNode = {\n children = [\n {\n _class = "RenderMeshList"\n children = [\n {\n _class = "RenderMeshFile"\n filename = "models/props/crate/crate_small.fbx"\n }\n ]\n }\n ]\n }\n}')

        # Run QuickConfigFile
        QuickConfigFile(vmdl_path)

        # Expected output .hbat is in parent folder of crate dir (models/props/crate.hbat)
        expected_hbat = os.path.normpath(os.path.join(fake_addon_dir, "models", "props", "crate.hbat"))
        assert os.path.isfile(expected_hbat)
        assert expected_hbat in watcher.file_widgets
    finally:
        watcher.close()


def test_quick_create_dialog_notifies_watcher(qapp, fake_addon_dir):
    from gui.forms.quick_create.main import QuickCreateDialog

    watcher = MonitoringFileWatcher(fake_addon_dir)
    try:
        target_dir = os.path.join(fake_addon_dir, "smartprops", "dev")
        dialog = QuickCreateDialog(target_dir, "hbat")
        dialog.name_edit.setText("test_prop")
        dialog.accept()

        expected_hbat = os.path.normpath(os.path.join(target_dir, "test_prop.hbat"))
        assert os.path.isfile(expected_hbat)
        assert expected_hbat in watcher.file_widgets
    finally:
        watcher.close()


def test_collect_hbat_files_recursive(qapp, fake_addon_dir):
    # Create nested hbat files
    p1 = os.path.join(fake_addon_dir, "models", "props", "crate", "box1.hbat")
    p2 = os.path.join(fake_addon_dir, "materials", "nature", "rock1.hbat")
    for p in (p1, p2):
        with open(p, "w") as f:
            json.dump({"process": {"reference": ""}, "replacements": {}, "file": {"content": ""}}, f)

    watcher = MonitoringFileWatcher(fake_addon_dir)
    try:
        found = watcher.collect_hbat_files()
        assert os.path.normpath(p1) in found
        assert os.path.normpath(p2) in found
        assert os.path.normpath(p1) in watcher.file_widgets
        assert os.path.normpath(p2) in watcher.file_widgets
    finally:
        watcher.close()


def test_remove_file_widget(qapp, fake_addon_dir):
    hbat_path = os.path.join(fake_addon_dir, "models", "props", "crate", "box_del.hbat")
    with open(hbat_path, "w") as f:
        json.dump({"process": {"reference": ""}, "replacements": {}, "file": {"content": ""}}, f)

    watcher = MonitoringFileWatcher(fake_addon_dir)
    try:
        norm_path = os.path.normpath(hbat_path)
        assert norm_path in watcher.file_widgets

        watcher.remove_file_widget(norm_path)
        assert norm_path not in watcher.file_widgets
    finally:
        watcher.close()


