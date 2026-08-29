from pathlib import Path
from PySide6.QtWidgets import QApplication
import pytest

from gui.forms.navmesh_radar.main import NavMeshRadarDialog


class _FakeStatus:
    def __init__(self, generated_vmap_path, prefab_present):
        self.generated_vmap_path = generated_vmap_path
        self.prefab_present = prefab_present
        self.diagnostics = ()


def _fake_core(monkeypatch, generated_vmap_path, prefab_present):
    """Stands in for the Core so the dialog never touches the native library in tests."""

    class FakeBridge:
        @staticmethod
        def instance():
            return FakeBridge()

        def navmesh_radar_status(self, main_vmap_path):
            return _FakeStatus(generated_vmap_path, prefab_present)

    monkeypatch.setattr("gui.forms.navmesh_radar.main.CoreBridge", FakeBridge)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_navmesh_radar_dialog_widgets(qapp, monkeypatch):
    _fake_core(monkeypatch, None, False)
    dialog = NavMeshRadarDialog()
    assert dialog.windowTitle() == "NavMesh Radar"

    # Confirm offset spinbox is removed
    assert not hasattr(dialog, "offset_spin")

    # Confirm status/ready label is removed
    assert not hasattr(dialog, "status_label")

    # Confirm combo modes with NavMesh as default
    items = [dialog.mode_combo.itemText(i) for i in range(dialog.mode_combo.count())]
    assert items == ["NavMesh", "Baked bomb damage"]
    assert dialog.mode_combo.currentText() == "NavMesh"

    # Confirm description and warning labels are removed
    assert not hasattr(dialog, "warning_label")

    # Confirm remove offset and collapse faces checkboxes exist
    assert hasattr(dialog, "remove_offset_checkbox")
    assert dialog.remove_offset_checkbox.isChecked()

    assert hasattr(dialog, "collapse_faces_checkbox")
    assert dialog.collapse_faces_checkbox.isChecked()
    assert hasattr(dialog, "collapse_ngons_checkbox")
    assert not dialog.collapse_ngons_checkbox.isChecked()
    assert dialog.collapse_ngons_checkbox.isEnabled()

    # In NavMesh mode (index 0 / default), remove offset is visible and collapse options are hidden
    assert dialog.remove_offset_checkbox.isVisibleTo(dialog) or not dialog.remove_offset_checkbox.isHidden()
    assert dialog.collapse_faces_checkbox.isHidden()
    assert dialog.collapse_ngons_checkbox.isHidden()

    # Switch to Baked bomb damage mode (index 1), collapse options are visible, remove offset is hidden
    dialog.mode_combo.setCurrentIndex(1)
    assert not dialog.collapse_faces_checkbox.isHidden()
    assert not dialog.collapse_ngons_checkbox.isHidden()
    assert dialog.remove_offset_checkbox.isHidden()

    dialog.collapse_faces_checkbox.setChecked(False)
    assert not dialog.collapse_ngons_checkbox.isEnabled()
    dialog.collapse_faces_checkbox.setChecked(True)

    # Confirm add prefab entity checkbox exists and has expanding size policy
    assert hasattr(dialog, "add_prefab_checkbox")
    assert dialog.add_prefab_checkbox.isChecked()
    assert dialog.add_prefab_checkbox.sizePolicy().horizontalPolicy().name == "Expanding"
    assert dialog.collapse_faces_checkbox.sizePolicy().horizontalPolicy().name == "Expanding"
    assert dialog.collapse_ngons_checkbox.sizePolicy().horizontalPolicy().name == "Expanding"
    assert dialog.remove_offset_checkbox.sizePolicy().horizontalPolicy().name == "Expanding"

    # Confirm progress bar and buttons exist
    assert hasattr(dialog, "progress_bar")
    assert hasattr(dialog, "generate_button")
    assert hasattr(dialog, "close_button")

    dialog.close()


def test_navmesh_radar_dialog_relative_paths(qapp, monkeypatch):
    _fake_core(
        monkeypatch,
        "C:/fake/cs2/content/csgo_addons/test_addon/maps/test_addon_generated_radar.vmap",
        False,
    )
    monkeypatch.setattr("gui.forms.navmesh_radar.main.get_addon_name", lambda: "test_addon")
    monkeypatch.setattr("gui.forms.navmesh_radar.main.get_cs2_path", lambda: "C:/fake/cs2")
    monkeypatch.setattr(
        "gui.forms.navmesh_radar.main.addon_content_dir",
        lambda addon: Path("C:/fake/cs2/content/csgo_addons/test_addon"),
    )
    monkeypatch.setattr(
        "gui.forms.navmesh_radar.main.addon_game_dir",
        lambda addon: Path("C:/fake/cs2/game/csgo_addons/test_addon"),
    )

    dialog = NavMeshRadarDialog()
    assert dialog.vpk_field.text() == "game/csgo_addons/test_addon/maps/test_addon.vpk"
    assert dialog.output_field.text() == "content/csgo_addons/test_addon/maps/test_addon_generated_radar.vmap"
    assert "C:/fake/cs2" in dialog.vpk_field.toolTip().replace("\\", "/")
    assert "C:/fake/cs2" in dialog.output_field.toolTip().replace("\\", "/")

    # No prefab in the main map yet, so adding one is still on offer.
    assert dialog.add_prefab_checkbox.isEnabled()
    assert dialog.add_prefab_checkbox.isChecked()

    dialog.close()


def test_add_prefab_is_disabled_when_the_main_map_already_references_it(qapp, monkeypatch):
    _fake_core(
        monkeypatch,
        "C:/fake/cs2/content/csgo_addons/test_addon/maps/test_addon_generated_radar.vmap",
        True,
    )
    monkeypatch.setattr("gui.forms.navmesh_radar.main.get_addon_name", lambda: "test_addon")
    monkeypatch.setattr("gui.forms.navmesh_radar.main.get_cs2_path", lambda: "C:/fake/cs2")
    monkeypatch.setattr(
        "gui.forms.navmesh_radar.main.addon_content_dir",
        lambda addon: Path("C:/fake/cs2/content/csgo_addons/test_addon"),
    )
    monkeypatch.setattr(
        "gui.forms.navmesh_radar.main.addon_game_dir",
        lambda addon: Path("C:/fake/cs2/game/csgo_addons/test_addon"),
    )

    dialog = NavMeshRadarDialog()

    assert not dialog.add_prefab_checkbox.isEnabled()
    assert not dialog.add_prefab_checkbox.isChecked()
    assert "already references" in dialog.add_prefab_checkbox.toolTip()

    dialog.close()

