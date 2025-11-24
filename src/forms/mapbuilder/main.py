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