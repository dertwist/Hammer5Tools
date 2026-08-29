from pathlib import Path
from PySide6.QtWidgets import QApplication
import pytest

from gui.forms.navmesh_radar.main import NavMeshRadarDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_navmesh_radar_dialog_widgets(qapp):
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
    assert not dialog.remove_offset_checkbox.isChecked()

    assert hasattr(dialog, "collapse_faces_checkbox")
    assert dialog.collapse_faces_checkbox.isChecked()

    # In NavMesh mode (index 0 / default), remove offset is visible, collapse faces is hidden
    assert not dialog.remove_offset_checkbox.isHidden()
    assert dialog.collapse_faces_checkbox.isHidden()

    # Switch to Baked bomb damage mode (index 1), collapse faces is visible, remove offset is hidden
    dialog.mode_combo.setCurrentIndex(1)
    assert dialog.collapse_faces_checkbox.isVisibleTo(dialog) or not dialog.collapse_faces_checkbox.isHidden()
    assert dialog.remove_offset_checkbox.isHidden()

    # Confirm add prefab entity checkbox exists and has expanding size policy
    assert hasattr(dialog, "add_prefab_checkbox")
    assert dialog.add_prefab_checkbox.isChecked()
    assert dialog.add_prefab_checkbox.sizePolicy().horizontalPolicy().name == "Expanding"
    assert dialog.collapse_faces_checkbox.sizePolicy().horizontalPolicy().name == "Expanding"
    assert dialog.remove_offset_checkbox.sizePolicy().horizontalPolicy().name == "Expanding"

    # Confirm progress bar and buttons exist
    assert hasattr(dialog, "progress_bar")
    assert hasattr(dialog, "generate_button")
    assert hasattr(dialog, "close_button")

    dialog.close()


def test_navmesh_radar_dialog_relative_paths(qapp, monkeypatch):
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
    assert dialog.output_field.text() == "content/csgo_addons/test_addon/maps/test_addon_navmesh_radar.vmap"
    assert "C:/fake/cs2" in dialog.vpk_field.toolTip().replace("\\", "/")
    assert "C:/fake/cs2" in dialog.output_field.toolTip().replace("\\", "/")

    dialog.close()

