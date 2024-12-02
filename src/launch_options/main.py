
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QSettings, Signal
import os,subprocess
import winreg as reg
from src.preferences import get_addon_name, get_config_value, get_config_bool
from src.launch_options.ui_main import Ui_preferences_dialog
from src.minor_features.addon_functions import assemble_commands

class LaunchOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_preferences_dialog()
        self.ui.setupUi(self)
        self.commands = get_config_value("LAUNCH", "commands")
        if not self.commands:
            self.commands = " -addon " + 'addon_name' + ' -tool hammer' + ' -asset maps/' + 'addon_name' + '.vmap' + " -tools -steam -retail -gpuraytracing  -noinsecru +install_dlc_workshoptools_cvar 1"
        self.__connections()
    def __connections(self):
        """Adding connections to the buttons and checkboxes"""
        self.ui.checkBox_gpuraytracing.checkStateChanged.connect(self.on_update)
        self.ui.checkBox_steam.checkStateChanged.connect(self.on_update)
        self.ui.checkBox_open_tools.checkStateChanged.connect(self.on_update)
        self.ui.checkBox_open_vmap.checkStateChanged.connect(self.on_update)
        self.ui.checkBox_show_retail.checkStateChanged.connect(self.on_update)
        self.ui.checkBox_show_retail.checkStateChanged.connect(self.on_update)
        self.ui.checkBox_no_insecure.checkStateChanged.connect(self.on_update)
        self.ui.checkBox_nocustomer_machine.checkStateChanged.connect(self.on_update)

        self.ui.lineEdit_preview.textChanged.connect(self.on_update)
        self.ui.lineEdit_custom.textChanged.connect(self.on_update)
    def populate_widgets(self):
        """Set the checkboxes and fill the custom commands line form the settings"""
        __commands = self.commands
    def assemble_commands(self):
        """Assembles all commands into one line"""
    def on_update(self):
        """Adding commands to the settings"""
        self.preview()
    def preview(self):
        """Assembles the commands for preview line, and sets the text to it"""
        self.ui.lineEdit_preview.setText(assemble_commands(self.commands, get_addon_name()))




