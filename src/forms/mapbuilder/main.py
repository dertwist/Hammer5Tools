from src.forms.mapbuilder.ui_main import Ui_mapbuilder_dialog
from PySide6.QtWidgets import QDialog, QApplication, QToolButton,  QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtGui import QIcon
from src.settings.main import get_addon_name, get_settings_value, set_settings_value
from src.common import *
from src.common import enable_dark_title_bar

import dataclasses

@dataclasses.dataclass
class BuildSettings:
    build_world: bool = True
    build_vis_geometry: bool = True
@dataclasses.dataclass
class BuildPreset:
    name: str
    default: bool
    settings: BuildSettings
@dataclasses.dataclass
class BuildLog:
    timestamp: str
    log: str
    elapsed_time: float

class BuildSettingsGroup(QWidget):
    def __init__(self, parent=None, group_name: str = "Settings"):
        """Category of settings, used to group settings or buttons together."""
        super().__init__(parent)
        self.group_header = QHBoxLayout()
        self.group_collapse_button = QToolButton(self)
        self.group_label = QLabel(group_name, self)
        self.group_content = QVBoxLayout()
        self.serialization_key = group_name.lower()

        self.layout = QVBoxLayout(self)
        self.layout.addLayout(self.group_header)
        self.layout.addLayout(self.group_content)
        self.group_header.addWidget(self.group_label)
        self.group_header.addWidget(self.group_collapse_button)

class BuildPresetButton(QWidget):
    def __init__(self, parent=None):
        """
        A preset of settings to build map, user can add a new preset by clicking the + button. This actions will capture all current settings and save them as a preset
        Default preset cannot be deleted or renamed.
        """
        super().__init__(parent)

    def rename(self):
        pass
    def delete(self):
        pass



class MapBuilderDialog(QDialog):
    """
    A tool to compile VPK map for Counter Strike 2.
    Output tab - raw HTML output of the compilation process.
    Logs tab - compilation logs (saved next to the hammer5tools executable, path:Logs/MapBuilder/addon/timestamp.log).
    Report tab - a beautiful report of the compilation process. This tab will process the raw HTML output and generate a nice looking report.
        Also have a system minotor at the bottom to show how much PC resources is used (self.ui.system_monitor Qframe).
        self.ui.report_widget shows warning, issues and errors item by item, have copy button next to each item.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_mapbuilder_dialog()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)
        self.populate_widgets()
        self.__connections()

    def __connections(self):
        """Adding connections to the buttons and checkboxes"""

    def populate_widgets(self):
        """Set the checkboxes and fill the custom commands line from the settings"""
        self.settings_group = BuildSettingsGroup(self, 'Settings')
        self.ui.build_settings_area.widget().layout().insertWidget(0, self.settings_group)
        self.world_group = BuildSettingsGroup(self, 'World')
        self.ui.build_settings_area.widget().layout().insertWidget(0, self.world_group)