import subprocess
import sys
import ast

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QCheckBox, QSpacerItem,
    QSizePolicy, QFrame, QScrollArea, QFileDialog, QComboBox
)
from src.settings.common import *
from src.common import enable_dark_title_bar, Presets_Path
from src.updater.check import check_updates
from src.widgets.common import Button  # Using the internal Button class
from src.styles.common import qt_stylesheet_checkbox, qt_stylesheet_combobox
from src.widgets import FloatWidget  # Using the internal FloatWidget for float properties


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
        self.setMinimumSize(830, 300)
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
        self.create_sound_event_editor_tab()
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

    def wrap_in_scroll_area(self, widget):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setObjectName("customScrollArea")
        scroll_area.setStyleSheet("""
            QScrollArea#customScrollArea {
                border: none;
            }
        """)
        return scroll_area

    def create_general_tab(self):
        # Create the general tab content widget
        general_tab_content = QWidget()
        layout = QVBoxLayout(general_tab_content)
        layout.setContentsMargins(10, 10, 10, 10)
        # ------------- Paths Subcategory -------------
        label_paths_header = QLabel("Paths", general_tab_content)
        layout.addWidget(label_paths_header)
        self.frame_paths = QFrame(general_tab_content)
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
        layout.addWidget(self.create_divider(general_tab_content))
        # ------------- Discord Status Subcategory -------------
        label_discord_header = QLabel("Discord Status", general_tab_content)
        layout.addWidget(label_discord_header)
        self.frame_discord = QFrame(general_tab_content)
        layout_discord = QVBoxLayout(self.frame_discord)
        row_status = QHBoxLayout()
        self.checkBox_show_in_hammer_discord_status = QCheckBox("Show status", self.frame_discord)
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
        layout.addWidget(self.create_divider(general_tab_content))
        # ------------- Other Subcategory -------------
        label_other_header = QLabel("Other", general_tab_content)
        layout.addWidget(label_other_header)
        self.frame_other = QFrame(general_tab_content)
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
        # Wrap the general tab content in a scroll area
        general_scroll = self.wrap_in_scroll_area(general_tab_content)
        self.tabWidget.addTab(general_scroll, "General")

    def create_smartprop_tab(self):
        smartprop_content = QWidget()
        layout = QVBoxLayout(smartprop_content)
        layout.setContentsMargins(10, 10, 10, 10)
        # ------------- Interface Subcategory -------------
        label_interface_header = QLabel("Interface", smartprop_content)
        layout.addWidget(label_interface_header)
        frame_interface = QFrame(smartprop_content)
        layout_interface = QVBoxLayout(frame_interface)
        self.spe_display_id_with_variable_class = QCheckBox("Display ID with variable class (Reopen file)", frame_interface)
        self.spe_display_id_with_variable_class.setStyleSheet(qt_stylesheet_checkbox)
        layout_interface.addWidget(self.spe_display_id_with_variable_class)
        layout.addWidget(frame_interface)
        # Divider between subcategories
        layout.addWidget(self.create_divider(smartprop_content))
        # ------------- Format Subcategory -------------
        label_format_header = QLabel("Format", smartprop_content)
        layout.addWidget(label_format_header)
        frame_format = QFrame(smartprop_content)
        layout_format = QVBoxLayout(frame_format)
        self.spe_export_properties = QCheckBox("Export properties in one line", frame_format)
        self.spe_export_properties.setStyleSheet(qt_stylesheet_checkbox)
        self.spe_export_properties.setChecked(True)
        layout_format.addWidget(self.spe_export_properties)
        layout.addWidget(frame_format)
        # Divider for Realtime Saving Subcategory
        layout.addWidget(self.create_divider(smartprop_content))
        label_rt_saving = QLabel("Realtime Saving", smartprop_content)
        layout.addWidget(label_rt_saving)
        frame_rt_saving = QFrame(smartprop_content)
        layout_rt_saving = QVBoxLayout(frame_rt_saving)
        # Enable Transparency window while realtime saving
        row_enable_transparency = QHBoxLayout()
        self.spe_enable_transparency_window = QCheckBox("Enable Transparency Window", frame_rt_saving)
        self.spe_enable_transparency_window.setChecked(True)
        self.spe_enable_transparency_window.setStyleSheet(qt_stylesheet_checkbox)
        row_enable_transparency.addWidget(self.spe_enable_transparency_window)
        layout_rt_saving.addLayout(row_enable_transparency)
        # Transparency Window row
        row_transparency = QHBoxLayout()
        label_transparency = QLabel("Transparency Window (%):", frame_rt_saving)
        label_transparency.setMinimumWidth(130)
        row_transparency.addWidget(label_transparency)
        self.spe_transparency_window = FloatWidget(frame_rt_saving,
                                                   slider_range=[10, 100],
                                                   lock_range=True,
                                                   spacer_enable=False,
                                                   digits=0,
                                                   only_positive=True,
                                                   value=70)
        row_transparency.addWidget(self.spe_transparency_window)
        layout_rt_saving.addLayout(row_transparency)
        layout.addWidget(frame_rt_saving)
        # Relative Saving Delay row
        row_rt_delay = QHBoxLayout()
        label_rt_delay = QLabel("Realtime Saving Delay (milliseconds):", frame_rt_saving)
        label_rt_delay.setMinimumWidth(130)
        row_rt_delay.addWidget(label_rt_delay)
        self.spe_realtime_saving_delay = FloatWidget(frame_rt_saving,
                                                     slider_range=[5, 1000],
                                                     lock_range=True,
                                                     spacer_enable=False,
                                                     digits=3,
                                                     only_positive=True,
                                                     value=5,
                                                     value_step=15,
                                                     slider_scale=5
                                                     )
        row_rt_delay.addWidget(self.spe_realtime_saving_delay)
        layout_rt_saving.addLayout(row_rt_delay)

        layout.addStretch()
        smartprop_scroll = self.wrap_in_scroll_area(smartprop_content)
        self.tabWidget.addTab(smartprop_scroll, "SmartProp Editor")

    def create_assetgroupmaker_tab(self):
        assetgroupmaker_content = QWidget()
        layout = QVBoxLayout(assetgroupmaker_content)
        layout.setContentsMargins(10, 10, 10, 10)
        # ------------- Monitor Subcategory -------------
        label_monitor_header = QLabel("Monitor", assetgroupmaker_content)
        layout.addWidget(label_monitor_header)
        frame_monitor = QFrame(assetgroupmaker_content)
        layout_monitor = QHBoxLayout(frame_monitor)
        monitor_label = QLabel("Folders to monitor (restart program to apply changes):", assetgroupmaker_content)
        monitor_label.setMinimumWidth(130)
        layout_monitor.addWidget(monitor_label)
        self.assetgroupmaker_lineedit_monitor = QLineEdit(frame_monitor)
        layout_monitor.addWidget(self.assetgroupmaker_lineedit_monitor)
        layout.addWidget(frame_monitor)
        # Divider before Default File Subcategory
        layout.addWidget(self.create_divider(assetgroupmaker_content))
        # ------------- Default File Subcategory -------------
        label_default_file = QLabel("Default File", assetgroupmaker_content)
        layout.addWidget(label_default_file)
        frame_default_file = QFrame(assetgroupmaker_content)
        layout_default_file = QVBoxLayout(frame_default_file)
        # Extension editline
        row_ext = QHBoxLayout()
        label_ext = QLabel("Extension:", frame_default_file)
        label_ext.setMinimumWidth(130)
        row_ext.addWidget(label_ext)
        self.assetgroupmaker_edit_extension = QLineEdit(frame_default_file)
        row_ext.addWidget(self.assetgroupmaker_edit_extension)
        layout_default_file.addLayout(row_ext)
        # Ignore List editline
        row_ignore = QHBoxLayout()
        label_ignore = QLabel("Ignore List:", frame_default_file)
        label_ignore.setMinimumWidth(130)
        row_ignore.addWidget(label_ignore)
        self.assetgroupmaker_edit_ignore_list = QLineEdit(frame_default_file)
        row_ignore.addWidget(self.assetgroupmaker_edit_ignore_list)
        layout_default_file.addLayout(row_ignore)
        # Algorithm combobox
        row_algo = QHBoxLayout()
        label_algo = QLabel("Algorithm:", frame_default_file)
        label_algo.setMinimumWidth(130)
        row_algo.addWidget(label_algo)
        self.assetgroupmaker_combo_algorithm = QComboBox(frame_default_file)
        self.assetgroupmaker_combo_algorithm.setStyleSheet(qt_stylesheet_combobox)
        # Add the two algorithm options:
        self.assetgroupmaker_combo_algorithm.addItem("Process without interpretation", 0)
        self.assetgroupmaker_combo_algorithm.addItem("Remove underscore from the end", 1)
        self.assetgroupmaker_combo_algorithm.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.assetgroupmaker_combo_algorithm.setMinimumWidth(200)
        row_algo.addWidget(self.assetgroupmaker_combo_algorithm)
        row_algo.addStretch()
        layout_default_file.addLayout(row_algo)
        # Ignore Extensions editline
        row_ignore_ext = QHBoxLayout()
        label_ignore_ext = QLabel("Ignore Extensions:", frame_default_file)
        label_ignore_ext.setMinimumWidth(130)
        row_ignore_ext.addWidget(label_ignore_ext)
        self.assetgroupmaker_edit_ignore_ext = QLineEdit(frame_default_file)
        row_ignore_ext.addWidget(self.assetgroupmaker_edit_ignore_ext)
        layout_default_file.addLayout(row_ignore_ext)
        layout.addWidget(frame_default_file)
        # Divider after Default File Subcategory
        layout.addWidget(self.create_divider(assetgroupmaker_content))
        layout.addSpacerItem(QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Expanding))
        assetgroupmaker_scroll = self.wrap_in_scroll_area(assetgroupmaker_content)
        self.tabWidget.addTab(assetgroupmaker_scroll, "AssetGroupMaker")

    def create_sound_event_editor_tab(self):
        # Create the SoundEventEditor tab with AudioPlayer subcategory and Internal Sounds subcategory
        sound_editor_content = QWidget()
        layout = QVBoxLayout(sound_editor_content)
        layout.setContentsMargins(10, 10, 10, 10)
        # ------------- AudioPlayer Subcategory -------------
        label_audio_header = QLabel("AudioPlayer", sound_editor_content)
        layout.addWidget(label_audio_header)
        self.frame_audio = QFrame(sound_editor_content)
        layout_audio = QHBoxLayout(self.frame_audio)
        self.checkBox_play_on_click = QCheckBox("Play on Click", self.frame_audio)
        self.checkBox_play_on_click.setStyleSheet(qt_stylesheet_checkbox)
        layout_audio.addWidget(self.checkBox_play_on_click)
        layout.addWidget(self.frame_audio)
        # ------------- Internal Sounds Subcategory -------------
        layout.addWidget(self.create_divider(sound_editor_content))
        label_internal = QLabel("Internal Sounds", sound_editor_content)
        layout.addWidget(label_internal)
        self.frame_internal_sounds = QFrame(sound_editor_content)
        layout_internal = QVBoxLayout(self.frame_internal_sounds)
        # Maximum cache size property using FloatWidget (float property, default 400)
        row_cache_size = QHBoxLayout()
        label_max_cache = QLabel("Maximum cache size:", self.frame_internal_sounds)
        label_max_cache.setMinimumWidth(130)
        row_cache_size.addWidget(label_max_cache)
        self.floatWidget_max_cache_size = FloatWidget(self.frame_internal_sounds,
                                                       slider_range=[50, 4000],
                                                       lock_range=True,
                                                       spacer_enable=False,
                                                       digits=0,
                                                       only_positive=True,
                                                       value=400)
        row_cache_size.addWidget(self.floatWidget_max_cache_size)
        layout_internal.addLayout(row_cache_size)
        layout.addWidget(self.frame_internal_sounds)
        layout.addStretch()
        sound_editor_scroll = self.wrap_in_scroll_area(sound_editor_content)
        self.tabWidget.addTab(sound_editor_scroll, "SoundEventEditor")

    def create_bottom_panel(self):
        # Use the new ActionButtonsPanel for the bottom buttons
        self.action_buttons_panel = ActionButtonsPanel(self)
        self.main_layout.addWidget(self.action_buttons_panel)

    def populate_preferences(self):
        self.preferences_lineedit_archive_path.setText(get_settings_value('PATHS', 'archive'))
        self.checkBox_show_in_hammer_discord_status.setChecked(get_settings_bool('DISCORD_STATUS', 'show_status'))
        self.checkBox_hide_project_name_discord_status.setChecked(get_settings_bool('DISCORD_STATUS', 'show_project_name'))
        self.editline_custom_discord_status.setText(get_settings_value('DISCORD_STATUS', 'custom_status'))
        self.launch_addon_after_nosteamlogon_fix.setChecked(get_settings_bool('OTHER', 'launch_addon_after_nosteamlogon_fix'))
        self.checkBox_start_with_system.setChecked(get_settings_bool('APP', 'start_with_system'))
        self.checkBox_close_to_tray.setChecked(get_settings_bool('APP', 'minimize_to_tray', True))
        self.spe_display_id_with_variable_class.setChecked(get_settings_bool('SmartPropEditor', 'display_id_with_variable_class', False))
        self.spe_export_properties.setChecked(get_settings_bool('SmartPropEditor', 'export_properties_in_one_line', True))
        self.action_buttons_panel.version_label.setText(f"Version: {self.app_version}")
        # Populate the monitor editline; default to provided value if not set
        self.assetgroupmaker_lineedit_monitor.setText(get_settings_value('AssetGroupMaker', 'monitor_folders') or "models, materials, smartprops")
        # Populate Default File Subcategory fields
        try:
            default_file = ast.literal_eval(get_settings_value('AssetGroupMaker', 'default_file') or "{}")
            process = default_file.get('process', {})
        except Exception:
            process = {}
        self.assetgroupmaker_edit_extension.setText(process.get('extension', 'vmdl'))
        self.assetgroupmaker_edit_ignore_list.setText(process.get('ignore_list', ''))
        algo = process.get('algorithm', 0)
        # Set combobox current index based on stored algorithm value
        index = 0 if algo == 0 else 1
        self.assetgroupmaker_combo_algorithm.setCurrentIndex(index)
        self.assetgroupmaker_edit_ignore_ext.setText(process.get('ignore_extensions', 'mb,ma,max,st,blend,blend1,vmdl,vmat,vsmart,tga,png,jpg,exr,hdr'))
        # Populate SoundEventEditor preferences
        self.checkBox_play_on_click.setChecked(get_settings_bool('SoundEventEditor', 'play_on_click', True))
        try:
            max_cache = float(get_settings_value('SoundEventEditor', 'max_cache_size') or 400)
        except ValueError:
            max_cache = 400
        self.floatWidget_max_cache_size.set_value(max_cache)
        # Populate new SmartPropEditor Realtime Saving preferences
        try:
            rt_delay = float(get_settings_value('SmartPropEditor', 'realtime_saving_delay') or 0.01)
        except ValueError:
            rt_delay = 0.01
        self.spe_realtime_saving_delay.set_value(rt_delay)
        self.spe_enable_transparency_window.setChecked(get_settings_bool('SmartPropEditor', 'enable_transparency_window', False))
        try:
            trans_win = float(get_settings_value('SmartPropEditor', 'transparency_window') or 50)
        except ValueError:
            trans_win = 50
        self.spe_transparency_window.set_value(trans_win)

    def update_default_file_setting(self):
        # Collect current settings from Default File subcategory fields (removed folder options)
        process = {
            'extension': self.assetgroupmaker_edit_extension.text(),
            'ignore_list': self.assetgroupmaker_edit_ignore_list.text(),
            'algorithm': self.assetgroupmaker_combo_algorithm.currentData(),
            'ignore_extensions': self.assetgroupmaker_edit_ignore_ext.text()
        }
        default_file = {'process': process}
        set_settings_value('AssetGroupMaker', 'default_file', str(default_file))

    def connect_signals(self):
        self.preferences_lineedit_archive_path.textChanged.connect(
            lambda: set_settings_value('PATHS', 'archive', self.preferences_lineedit_archive_path.text())
        )
        self.checkBox_show_in_hammer_discord_status.toggled.connect(
            lambda: set_settings_bool('DISCORD_STATUS', 'show_status', self.checkBox_show_in_hammer_discord_status.isChecked())
        )
        self.checkBox_hide_project_name_discord_status.toggled.connect(
            lambda: set_settings_bool('DISCORD_STATUS', 'show_project_name', self.checkBox_hide_project_name_discord_status.isChecked())
        )
        self.editline_custom_discord_status.textChanged.connect(
            lambda: set_settings_value('DISCORD_STATUS', 'custom_status', self.editline_custom_discord_status.text())
        )
        self.launch_addon_after_nosteamlogon_fix.toggled.connect(
            lambda: set_settings_bool('OTHER', 'launch_addon_after_nosteamlogon_fix', self.launch_addon_after_nosteamlogon_fix.isChecked())
        )
        self.checkBox_start_with_system.toggled.connect(self.start_with_system)
        self.checkBox_close_to_tray.toggled.connect(
            lambda: set_settings_bool('APP', 'minimize_to_tray', self.checkBox_close_to_tray.isChecked())
        )
        self.spe_display_id_with_variable_class.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'display_id_with_variable_class', self.spe_display_id_with_variable_class.isChecked())
        )
        self.spe_export_properties.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'export_properties_in_one_line', self.spe_export_properties.isChecked())
        )
        self.assetgroupmaker_lineedit_monitor.textChanged.connect(
            lambda: set_settings_value('AssetGroupMaker', 'monitor_folders', self.assetgroupmaker_lineedit_monitor.text())
        )
        # Connect Default File subcategory widgets to update_default_file_setting
        self.assetgroupmaker_edit_extension.textChanged.connect(self.update_default_file_setting)
        self.assetgroupmaker_edit_ignore_list.textChanged.connect(self.update_default_file_setting)
        self.assetgroupmaker_combo_algorithm.currentIndexChanged.connect(self.update_default_file_setting)
        self.assetgroupmaker_edit_ignore_ext.textChanged.connect(self.update_default_file_setting)
        self.action_buttons_panel.open_settings_folder_button.clicked.connect(self.open_settings_folder)
        self.action_buttons_panel.open_presets_folder_button.clicked.connect(self.open_presets_folder)
        self.action_buttons_panel.check_update_button.clicked.connect(self.check_update)
        self.browse_archive_button.clicked.connect(self.browse_archive)
        self.checkBox_play_on_click.toggled.connect(
            lambda: set_settings_bool('SoundEventEditor', 'play_on_click', self.checkBox_play_on_click.isChecked())
        )
        # Connect using the FloatWidget's "edited" signal instead of "valueChanged"
        self.floatWidget_max_cache_size.edited.connect(
            lambda val: set_settings_value('SoundEventEditor', 'max_cache_size', str(val))
        )
        # Connect new SmartPropEditor Realtime Saving signals
        self.spe_realtime_saving_delay.edited.connect(
            lambda val: set_settings_value('SmartPropEditor', 'realtime_saving_delay', str(val))
        )
        self.spe_enable_transparency_window.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'enable_transparency_window', self.spe_enable_transparency_window.isChecked())
        )
        self.spe_transparency_window.edited.connect(
            lambda val: set_settings_value('SmartPropEditor', 'transparency_window', str(val))
        )

    def browse_archive(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Archive Path", os.getcwd())
        if selected_dir:
            self.preferences_lineedit_archive_path.setText(selected_dir)
            set_settings_value('PATHS', 'archive', selected_dir)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PreferencesDialog(app_version="1.0.0")
    dialog.show()
    sys.exit(app.exec())