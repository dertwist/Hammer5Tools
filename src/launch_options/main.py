from PySide6.QtWidgets import QDialog
from src.settings.preferences import get_addon_name, get_config_value, set_config_value
from src.launch_options.ui_main import Ui_preferences_dialog
from src.other.addon_functions import assemble_commands
from src.common import *
from src.common import enable_dark_title_bar

class LaunchOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_preferences_dialog()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)
        self.commands = get_config_value("LAUNCH", "commands")
        if not self.commands:
            self.commands = default_commands
            set_config_value("LAUNCH", "commands", self.commands)
        self.populate_widgets()
        self.__connections()
        self.on_update()

    def __connections(self):
        """Adding connections to the buttons and checkboxes"""
        self.ui.checkBox_gpuraytracing.stateChanged.connect(self.on_update)
        self.ui.checkBox_steam.stateChanged.connect(self.on_update)
        self.ui.checkBox_open_tools.stateChanged.connect(self.on_update)
        self.ui.checkBox_open_vmap.stateChanged.connect(self.on_update)
        self.ui.checkBox_show_retail.stateChanged.connect(self.on_update)
        self.ui.checkBox_no_insecure.stateChanged.connect(self.on_update)
        self.ui.checkBox_nocustomer_machine.stateChanged.connect(self.on_update)

        self.ui.lineEdit_preview.textChanged.connect(self.on_update)
        self.ui.lineEdit_custom.textChanged.connect(self.on_update)

    def populate_widgets(self):
        """Set the checkboxes and fill the custom commands line from the settings"""
        __commands = self.commands
        if '-tool hammer -asset maps/' + 'addon_name' + '.vmap' in __commands:
            __commands = __commands.replace(" -tool hammer -asset maps/" + 'addon_name' + '.vmap', '')
            self.ui.checkBox_open_vmap.setChecked(True)
        if '-noinsecru' in __commands:
            __commands = __commands.replace('-noinsecru', '')
            self.ui.checkBox_no_insecure.setChecked(True)
        if '-steam' in __commands:
            __commands = __commands.replace('-steam', '')
            self.ui.checkBox_steam.setChecked(True)
        if '-gpuraytracing' in __commands:
            __commands = __commands.replace('-gpuraytracing', '')
            self.ui.checkBox_gpuraytracing.setChecked(True)
        if '-retail' in __commands:
            __commands = __commands.replace('-retail', '')
            self.ui.checkBox_show_retail.setChecked(True)
        if '-nocustomermachine' in __commands:
            __commands = __commands.replace('-nocustomermachine', '')
            self.ui.checkBox_nocustomer_machine.setChecked(True)
        if '-tools' in __commands:
            __commands = __commands.replace('-tools', '')
            self.ui.checkBox_open_tools.setChecked(True)

        __commands = __commands.replace(' -addon ' + 'addon_name', '')

        self.ui.lineEdit_custom.setText(__commands.strip())

    def assemble_commands(self):
        """Assembles all commands into one line"""
        commands = " -addon " + 'addon_name '
        if self.ui.checkBox_open_vmap.isChecked():
            commands += " -tool hammer -asset maps/" + 'addon_name' + ".vmap "
        if self.ui.checkBox_no_insecure.isChecked():
            commands += " -noinsecru "
        if self.ui.checkBox_steam.isChecked():
            commands += " -steam "
        if self.ui.checkBox_gpuraytracing.isChecked():
            commands += " -gpuraytracing "
        if self.ui.checkBox_show_retail.isChecked():
            commands += " -retail "
        if self.ui.checkBox_nocustomer_machine.isChecked():
            commands += " -nocustomermachine "
        if self.ui.checkBox_open_tools.isChecked():
            commands += "-tools "

        custom_commands = self.ui.lineEdit_custom.text().strip()
        if custom_commands:
            commands += " " + custom_commands

        return commands

    def on_update(self):
        """Adding commands to the settings"""
        self.commands = self.assemble_commands()
        set_config_value("LAUNCH", "commands", self.commands)
        self.preview()

    def preview(self):
        """Assembles the commands for preview line, and sets the text to it"""
        self.ui.lineEdit_preview.setText(assemble_commands(self.commands, get_addon_name()))