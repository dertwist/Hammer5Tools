import os
import sys
import pytest
from PySide6.QtWidgets import QApplication, QDockWidget, QPlainTextEdit, QCheckBox, QPushButton
from PySide6.QtCore import Qt

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
gui_root = os.path.join(repo_root, "Hammer5ToolsGUI")
if gui_root not in sys.path:
    sys.path.insert(0, gui_root)

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.loading_editor.main import LoadingEditorMainWindow, SvgPreviewWidget
from gui.settings.common import settings as _settings


@pytest.fixture
def loading_window(tmp_path):
    # Isolate window settings
    saved_geo = _settings.value("LoadingEditor/geometry")
    saved_state = _settings.value("LoadingEditor/window_state")
    _settings.remove("LoadingEditor/geometry")
    _settings.remove("LoadingEditor/window_state")

    window = LoadingEditorMainWindow()
    try:
        yield window
    finally:
        window.close()
        window.deleteLater()
        if saved_geo is not None:
            _settings.setValue("LoadingEditor/geometry", saved_geo)
        else:
            _settings.remove("LoadingEditor/geometry")
        if saved_state is not None:
            _settings.setValue("LoadingEditor/window_state", saved_state)
        else:
            _settings.remove("LoadingEditor/window_state")


def test_loading_editor_docks_initialized(loading_window):
    """Verify that all groups are converted to non-closable QDockWidgets."""
    assert isinstance(loading_window.screenshots_dock, QDockWidget)
    assert isinstance(loading_window.icon_dock, QDockWidget)
    assert isinstance(loading_window.description_dock, QDockWidget)

    assert loading_window.screenshots_dock.windowTitle() == "Screenshots"
    assert loading_window.icon_dock.windowTitle() == "Icon"
    assert loading_window.description_dock.windowTitle() == "Description"

    expected_features = QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable

    assert loading_window.screenshots_dock.features() == expected_features
    assert loading_window.icon_dock.features() == expected_features
    assert loading_window.description_dock.features() == expected_features

    # Verify not closable
    assert not (loading_window.screenshots_dock.features() & QDockWidget.DockWidgetClosable)
    assert not (loading_window.icon_dock.features() & QDockWidget.DockWidgetClosable)
    assert not (loading_window.description_dock.features() & QDockWidget.DockWidgetClosable)


def test_loading_editor_central_widget(loading_window):
    """Verify that the image viewer is set as the central widget."""
    central = loading_window.centralWidget()
    assert central is not None
    assert central is loading_window.image_viewer


def test_loading_editor_widgets_exist_and_functional(loading_window):
    """Verify all UI controls are created and accessible."""
    # Screenshots controls
    assert loading_window.screenshots_tabwidget.count() == 2
    assert loading_window.screenshots_tabwidget.tabText(0) == "Explorer"
    assert loading_window.screenshots_tabwidget.tabText(1) == "Timeline"

    assert isinstance(loading_window.refresh, QPushButton)
    assert isinstance(loading_window.generate_gifs, QPushButton)
    assert isinstance(loading_window.take_history_shots, QPushButton)
    assert isinstance(loading_window.take_loading_screen_shots, QPushButton)
    assert isinstance(loading_window.delete_existings, QCheckBox)
    assert isinstance(loading_window.camera_name_mode, QCheckBox)
    assert isinstance(loading_window.apply_screenshots_button, QPushButton)

    # Icon controls
    assert isinstance(loading_window.svg_preview_widget, SvgPreviewWidget)
    assert isinstance(loading_window.fit_viewbox_checkbox, QCheckBox)
    assert isinstance(loading_window.apply_icon_button, QPushButton)

    # Description controls
    assert isinstance(loading_window.PlainTextEdit_Description_2, QPlainTextEdit)
    assert isinstance(loading_window.apply_description_button, QPushButton)


def test_loading_editor_tab_switch(loading_window):
    """Verify tab change between Explorer and Timeline."""
    loading_window.screenshots_tabwidget.setCurrentIndex(1)
    assert loading_window.screenshots_tabwidget.currentIndex() == 1
    loading_window.screenshots_tabwidget.setCurrentIndex(0)
    assert loading_window.screenshots_tabwidget.currentIndex() == 0


def test_loading_editor_preview_data(loading_window):
    """Verify preview data provider reflects current editor state."""
    loading_window.PlainTextEdit_Description_2.setPlainText("Test Map Description")
    loading_window.camera_name_mode.setChecked(True)

    data = loading_window.get_loading_preview_data()
    assert data["description_html"] == "Test Map Description"
    assert data["show_camera_name"] is True
    assert data["gamemode_text"] == "Competitive"


def test_loading_editor_layout_persistence(loading_window):
    """Verify save and restore of dock layout state."""
    loading_window._save_layout_state()
    geo = _settings.value("LoadingEditor/geometry")
    state = _settings.value("LoadingEditor/window_state")
    assert geo is not None
    assert state is not None

    # Restoring should succeed without error
    loading_window._restore_layout_state()
