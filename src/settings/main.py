import os
import subprocess
import sys

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QCheckBox, QSpacerItem,
    QSizePolicy, QFrame, QStyle, QFileDialog
)
from src.settings.common import *
from src.common import enable_dark_title_bar, Presets_Path
from src.other.NCM_mode_setup_main import NCM_mode_setup
from src.other.update_check import check_updates
from src.widgets_common import Button  # Using the internal Button class
from src.styles.common import qt_stylesheet_checkbox

class ActionButtonsPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        h_layout_bottom = QHBoxLayout(self)
        h_layout_bottom.setContentsMargins(9, 9, 9, 9)

        # Create buttons using the internal Button class
        self.open_settings_folder_button = Button(text=" Settings")
        self.open_settings_folder_button.set_icon_folder_open()
        h_layout_bottom.addWidget(self.open_settings_folder_button)

        self.open_presets_folder_button = Button(text=" Presets")
        self.open_presets_folder_button.set_icon_folder_open()
        h_layout_bottom.addWidget(self.open_presets_folder_button)

        h_layout_bottom.addStretch()

        self.version_label = QLabel("", self)
        h_layout_bottom.addWidget(self.version_label)

        self.check_update_button = Button()
        self.check_update_button.set_icon_sync()
        h_layout_bottom.addWidget(self.check_update_button)


class PreferencesDialog(QDialog):
    def __init__(self, app_version, parent=None):
        super().__init__(parent)
        self.app_version = app_version
        enable_dark_title_bar(self)

        # Set the minimum size and window title
        self.setMinimumSize(700, 300)
        self.setWindowTitle('Settings')

        self.main_layout = QVBoxLayout(self)
        self.tabWidget = QTabWidget(self)
        # Set background color of tab widget to #1c1c1c
        self.tabWidget.setStyleSheet("background-color: #1c1c1c;")
        self.main_layout.addWidget(self.tabWidget)

        # Create tabs and bottom action panel
        self.create_general_tab()
        self.create_smartprop_tab()
        self.create_assetgroupmaker_tab()
        self.create_bottom_panel()

        self.populate_preferences()
        self.connect_signals()

    def create_divider(self, parent):
        divider = QFrame(parent)
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setLineWidth(2)
        # Enforcing height of 2 pixels and divider color #323232
        divider.setFixedHeight(2)
        divider.setStyleSheet("background-color: #323232; border: none;")
        return divider

    def create_general_tab(self):
        self.general_tab = QWidget()
        layout = QVBoxLayout(self.general_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # ------------- Paths Subcategory -------------
        label_paths_header = QLabel("Paths", self.general_tab)
        layout.addWidget(label_paths_header)
        self.frame_paths = QFrame(self.general_tab)
        layout_paths = QHBoxLayout(self.frame_paths)
        archive_label = QLabel("Archive path:", self.frame_paths)
        archive_label.setMinimumWidth(130)
        layout_paths.addWidget(archive_label)
        self.preferences_lineedit_archive_path = QLineEdit(self.frame_paths)
        layout_paths.addWidget(self.preferences_lineedit_archive_path)
        # Add "Browse" button using internal Button class to locate archive path
        self.browse_archive_button = Button()
        self.browse_archive_button.set_icon_folder_open()
        self.browse_archive_button.set_size(27)
        layout_paths.addWidget(self.browse_archive_button)
        layout.addWidget(self.frame_paths)

        # Add divider after Paths Subcategory
        layout.addWidget(self.create_divider(self.general_tab))

        # ------------- Discord Status Subcategory -------------
        label_discord_header = QLabel("Discord Status", self.general_tab)
        layout.addWidget(label_discord_header)
        self.frame_discord = QFrame(self.general_tab)
        layout_discord = QVBoxLayout(self.frame_discord)
        row_status = QHBoxLayout()
        self.checkBox_show_in_hammer_discord_status = QCheckBox("Show hammer status in Discord", self.frame_discord)
        self.checkBox_show_in_hammer_discord_status.setStyleSheet(qt_stylesheet_checkbox)
        row_status.addWidget(self.checkBox_show_in_hammer_discord_status)
        self.checkBox_hide_project_name_discord_status = QCheckBox("Hide project name", self.frame_discord)
        self.checkBox_hide_project_name_discord_status.setStyleSheet(qt_stylesheet_checkbox)
        row_status.addWidget(self.checkBox_hide_project_name_discord_status)
        layout_discord.addLayout(row_status)
        row_custom = QHBoxLayout()
        custom_label = QLabel("Custom status:", self.frame_discord)
        custom_label.setMinimumWidth(130)
        row_custom.addWidget(custom_label)
        self.editline_custom_discord_status = QLineEdit(self.frame_discord)
        row_custom.addWidget(self.editline_custom_discord_status)
        layout_discord.addLayout(row_custom)
        layout.addWidget(self.frame_discord)

        # Add divider after Discord Status Subcategory
        layout.addWidget(self.create_divider(self.general_tab))

        # ------------- Other Subcategory -------------
        label_other_header = QLabel("Other", self.general_tab)
        layout.addWidget(label_other_header)
        self.frame_other = QFrame(self.general_tab)
        layout_other = QVBoxLayout(self.frame_other)
        self.launch_addon_after_nosteamlogon_fix = QCheckBox("Start Hammer editor after Steam restarting", self.frame_other)
        self.launch_addon_after_nosteamlogon_fix.setStyleSheet(qt_stylesheet_checkbox)
        layout_other.addWidget(self.launch_addon_after_nosteamlogon_fix)
        row_app = QHBoxLayout()
        self.checkBox_start_with_system = QCheckBox("Start with system", self.frame_other)
        self.checkBox_start_with_system.setStyleSheet(qt_stylesheet_checkbox)
        row_app.addWidget(self.checkBox_start_with_system)
        self.checkBox_close_to_tray = QCheckBox("Minimize on Close", self.frame_other)
        self.checkBox_close_to_tray.setStyleSheet(qt_stylesheet_checkbox)
        row_app.addWidget(self.checkBox_close_to_tray)
        layout_other.addLayout(row_app)
        layout.addWidget(self.frame_other)

        layout.addStretch()

        self.tabWidget.addTab(self.general_tab, "General")

    def create_smartprop_tab(self):
        self.smartprop_tab = QWidget()
        layout = QVBoxLayout(self.smartprop_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        frame_smart = QFrame(self.smartprop_tab)
        h_layout_smart = QHBoxLayout(frame_smart)
        self.spe_display_id_with_variable_class = QCheckBox("Display ID with variable class (Reopen file)", self.smartprop_tab)
        self.spe_display_id_with_variable_class.setStyleSheet(qt_stylesheet_checkbox)
        h_layout_smart.addWidget(self.spe_display_id_with_variable_class)
        layout.addWidget(frame_smart)
        layout.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.tabWidget.addTab(self.smartprop_tab, "SmartProp Editor")

    def create_assetgroupmaker_tab(self):
        self.assetgroupmaker_tab = QWidget()
        layout = QVBoxLayout(self.assetgroupmaker_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # ------------- Monitor Subcategory -------------
        label_monitor_header = QLabel("Monitor", self.assetgroupmaker_tab)
        layout.addWidget(label_monitor_header)
        frame_monitor = QFrame(self.assetgroupmaker_tab)
        layout_monitor = QHBoxLayout(frame_monitor)
        monitor_label = QLabel("Folders to monitor:", self.assetgroupmaker_tab)
        monitor_label.setMinimumWidth(130)
        layout_monitor.addWidget(monitor_label)
        self.assetgroupmaker_lineedit_monitor = QLineEdit(frame_monitor)
        layout_monitor.addWidget(self.assetgroupmaker_lineedit_monitor)
        layout.addWidget(frame_monitor)

        # Divider
        layout.addWidget(self.create_divider(self.assetgroupmaker_tab))

        layout.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.tabWidget.addTab(self.assetgroupmaker_tab, "AssetGroupMaker")


    def create_bottom_panel(self):
        # Use the new ActionButtonsPanel for the bottom buttons
        self.action_buttons_panel = ActionButtonsPanel(self)
        self.main_layout.addWidget(self.action_buttons_panel)

    def populate_preferences(self):
        self.preferences_lineedit_archive_path.setText(get_config_value('PATHS', 'archive'))
        self.checkBox_show_in_hammer_discord_status.setChecked(get_config_bool('DISCORD_STATUS', 'show_status'))
        self.checkBox_hide_project_name_discord_status.setChecked(get_config_bool('DISCORD_STATUS', 'show_project_name'))
        self.editline_custom_discord_status.setText(get_config_value('DISCORD_STATUS', 'custom_status'))
        self.launch_addon_after_nosteamlogon_fix.setChecked(get_config_bool('OTHER', 'launch_addon_after_nosteamlogon_fix'))
        self.checkBox_start_with_system.setChecked(get_config_bool('APP', 'start_with_system'))
        self.checkBox_close_to_tray.setChecked(get_config_bool('APP', 'minimize_to_tray', True))
        self.spe_display_id_with_variable_class.setChecked(get_config_bool('SmartPropEditor', 'display_id_with_variable_class', False))
        self.action_buttons_panel.version_label.setText(f"Version: {self.app_version}")

        # Populate the monitor editline; default to empty if not set
        self.assetgroupmaker_lineedit_monitor.setText(get_config_value('AssetGroupMaker', 'monitor_folders') or "models, materials, smartprops")

    def connect_signals(self):
        self.preferences_lineedit_archive_path.textChanged.connect(
            lambda: set_config_value('PATHS', 'archive', self.preferences_lineedit_archive_path.text())
        )
        self.checkBox_show_in_hammer_discord_status.toggled.connect(
            lambda: set_config_bool('DISCORD_STATUS', 'show_status', self.checkBox_show_in_hammer_discord_status.isChecked())
        )
        self.checkBox_hide_project_name_discord_status.toggled.connect(
            lambda: set_config_bool('DISCORD_STATUS', 'show_project_name', self.checkBox_hide_project_name_discord_status.isChecked())
        )
        self.editline_custom_discord_status.textChanged.connect(
            lambda: set_config_value('DISCORD_STATUS', 'custom_status', self.editline_custom_discord_status.text())
        )
        self.launch_addon_after_nosteamlogon_fix.toggled.connect(
            lambda: set_config_bool('OTHER', 'launch_addon_after_nosteamlogon_fix', self.launch_addon_after_nosteamlogon_fix.isChecked())
        )
        self.checkBox_start_with_system.toggled.connect(self.start_with_system)
        self.checkBox_close_to_tray.toggled.connect(
            lambda: set_config_bool('APP', 'minimize_to_tray', self.checkBox_close_to_tray.isChecked())
        )
        self.spe_display_id_with_variable_class.toggled.connect(
            lambda: set_config_bool('SmartPropEditor', 'display_id_with_variable_class', self.spe_display_id_with_variable_class.isChecked())
        )
        # Connect the monitor editline's text change to update configuration
        self.assetgroupmaker_lineedit_monitor.textChanged.connect(
            lambda: set_config_value('AssetGroupMaker', 'monitor_folders', self.assetgroupmaker_lineedit_monitor.text())
        )
        self.action_buttons_panel.open_settings_folder_button.clicked.connect(self.open_settings_folder)
        self.action_buttons_panel.open_presets_folder_button.clicked.connect(self.open_presets_folder)
        self.action_buttons_panel.check_update_button.clicked.connect(self.check_update)
        self.browse_archive_button.clicked.connect(self.browse_archive)

    def browse_archive(self):
        # Open a folder selection dialog and update the archive path
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Archive Path", os.getcwd())
        if selected_dir:
            self.preferences_lineedit_archive_path.setText(selected_dir)
            set_config_value('PATHS', 'archive', selected_dir)

    def open_settings_folder(self):
        subprocess.Popen(f'explorer "{os.getcwd()}"')

    def open_presets_folder(self):
        os.startfile(Presets_Path)

    def check_update(self):
        check_updates("https://github.com/dertwist/Hammer5Tools", self.app_version, False)

    def start_with_system(self):
        path_to_exe = os.path.join(os.getcwd(), 'hammer5tools.exe')
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "Hammer5Tools"
        if self.checkBox_start_with_system.isChecked():
            if os.path.exists(path_to_exe):
                try:
                    import winreg as reg
                    with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE) as reg_key:
                        reg.SetValueEx(reg_key, app_name, 0, reg.REG_SZ, path_to_exe)
                    print(f"Successfully added {path_to_exe} to startup")
                except Exception as e:
                    print(f"Failed to add {path_to_exe} to startup: {e}")
            else:
                print("Executable not found at the specified path")
        else:
            try:
                import winreg as reg
                with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE | reg.KEY_WRITE) as reg_key:
                    reg.DeleteValue(reg_key, app_name)
                print(f"Successfully removed {app_name} from startup")
            except FileNotFoundError:
                print(f"{app_name} not found in startup")
            except Exception as e:
                print(f"Failed to remove {app_name} from startup: {e}")