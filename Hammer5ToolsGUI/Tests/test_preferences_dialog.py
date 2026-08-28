from PySide6.QtWidgets import QApplication
import pytest
from gui.settings.main import PreferencesDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_preferences_dialog_initialization(qapp):
    dialog = PreferencesDialog(app_version="1.0.0")
    assert dialog.windowTitle() == "Settings"

    # Verify General tab exists
    assert dialog.tabWidget.count() >= 1
    assert dialog.tabWidget.tabText(0) == "General"

    # Verify categories in General tab
    assert hasattr(dialog, "frame_paths")
    assert hasattr(dialog, "frame_app")
    assert hasattr(dialog, "frame_associations")
    assert hasattr(dialog, "frame_git")

    # Verify widgets exist in respective categories
    assert hasattr(dialog, "checkBox_close_to_tray")
    assert hasattr(dialog, "cleanup_model_browser_button")
    assert hasattr(dialog, "association_buttons")
    assert ".vsmart" in dialog.association_buttons
    assert hasattr(dialog, "checkBox_git_generate_commit_messages")

    # Verify ActionButtonsPanel contains Open Console after Open UserData
    panel = dialog.action_buttons_panel
    assert hasattr(panel, "open_userdata_folder_button")
    assert hasattr(panel, "btn_open_console")
    assert dialog.btn_open_console is panel.btn_open_console

    # Verify order in ActionButtonsPanel layout
    layout = panel.layout()
    userdata_idx = -1
    console_idx = -1
    for i in range(layout.count()):
        item = layout.itemAt(i)
        w = item.widget() if item else None
        if w is panel.open_userdata_folder_button:
            userdata_idx = i
        elif w is panel.btn_open_console:
            console_idx = i

    assert userdata_idx != -1
    assert console_idx == userdata_idx + 1

    # Verify SmartProp Editor tab settings
    assert hasattr(dialog, "spe_display_id_with_variable_class")
    assert hasattr(dialog, "spe_hide_experimental")
    assert hasattr(dialog, "spe_round_vmap_values")
    assert hasattr(dialog, "spe_round_vmap_decimals")
    assert hasattr(dialog, "spe_viewport_msaa")
    assert not hasattr(dialog, "spe_export_properties")

    # Verify AssetGroupMaker tab settings
    assert hasattr(dialog, "assetgroupmaker_lineedit_monitor")
    assert not hasattr(dialog, "assetgroupmaker_edit_extension")
    assert not hasattr(dialog, "assetgroupmaker_edit_ignore_list")
    assert not hasattr(dialog, "assetgroupmaker_combo_algorithm")
    assert not hasattr(dialog, "assetgroupmaker_edit_ignore_ext")
    assert not hasattr(dialog, "update_default_file_setting")

    dialog.close()
