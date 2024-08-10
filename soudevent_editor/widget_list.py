# Import necessary modules
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMenu, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QCursor
from soudevent_editor.ui_soundevenet_editor_mainwindow import Ui_SoundEvent_Editor_MainWindow
from preferences import get_config_value, get_cs2_path, get_addon_name
from soudevent_editor.soundevent_editor_mini_windows_explorer import SoundEvent_Editor_MiniWindowsExplorer
from soudevent_editor.soundevent_editor_properties_popup import PropertiesPopup
from soudevent_editor.properties.legacy_property import LegacyProperty
from PySide6.QtWidgets import QStatusBar

selected_item = None  # Initialize selected_item as a global variable

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    main_widget = QWidget()
    main_layout = QVBoxLayout(main_widget)

    widget_list = QWidget()
    widget_layout = QVBoxLayout(widget_list)
    status_bar = QStatusBar()
    main_window.setStatusBar(status_bar)

    # Create a QScrollArea and set its maximum height to 400 pixels
    scroll_area = QScrollArea()
    scroll_area.setMaximumHeight(400)
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(widget_list)

    for number in range(8):
        legacy_property = LegacyProperty(name=f"{number + 1}: test", value='example_value', status_bar=status_bar)
        legacy_property.setProperty("customData", legacy_property)
        widget_layout.addWidget(legacy_property)
        print(f"Element {number + 1}: {legacy_property.name} - {legacy_property.value}")

    main_layout.addWidget(scroll_area)  # Add the scroll area to the main layout
    main_window.setCentralWidget(main_widget)
    main_window.show()

    sys.exit(app.exec())