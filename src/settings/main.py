import subprocess
import sys
import ast
import os

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QCheckBox, QSpacerItem,
    QSizePolicy, QFrame, QScrollArea, QFileDialog, QComboBox, QMessageBox
)
from src.settings.common import *
from src.common import enable_dark_title_bar, Presets_Path, app_dir, get_channel, get_build_channel
from src.widgets.common import Button  # Using the internal Button class
from src.styles.common import qt_stylesheet_checkbox, qt_stylesheet_combobox
from src.other.file_association import setup_all_associations


class ActionButtonsPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        h_layout_bottom = QHBoxLayout(self)
        h_layout_bottom.setContentsMargins(9, 9, 9, 9)
        # Create buttons using the internal Button class
        self.open_userdata_folder_button = Button(text=" Open UserData")
        self.open_userdata_folder_button.set_icon_folder_open()
        h_layout_bottom.addWidget(self.open_userdata_folder_button)

        h_layout_bottom.addStretch()
        self.version_label = QLabel("", self)
        h_layout_bottom.addWidget(self.version_label)
        self.checkBox_dev_channel = QCheckBox("Receive dev versions", self)
        self.checkBox_dev_channel.setStyleSheet(qt_stylesheet_checkbox)
        self.checkBox_dev_channel.setToolTip(
            "Update to pre-release (dev) builds. These are less tested than stable releases."
        )
        h_layout_bottom.addWidget(self.checkBox_dev_channel)
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
        self.tabWidget.setStyleSheet("background-color: #2e2e2e;")
        self.main_layout.addWidget(self.tabWidget)
        # Create tabs and bottom action panel
        self.create_appearance_tab()
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
        # Enforcing height of 2 pixels and divider color #424242
        divider.setFixedHeight(2)
        divider.setStyleSheet("background-color: #424242; border: none;")
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

    def create_appearance_tab(self):
        appearance_content = QWidget()
        layout = QVBoxLayout(appearance_content)
        layout.setContentsMargins(10, 10, 10, 10)
        # Interface Subcategory
        label_interface_header = QLabel("Interface", appearance_content)
        layout.addWidget(label_interface_header)
        frame_brightness = QFrame(appearance_content)
        layout_brightness = QHBoxLayout(frame_brightness)
        label_brightness = QLabel("Brightness:", frame_brightness)
        label_brightness.setMinimumWidth(130)
        layout_brightness.addWidget(label_brightness)
        self.appearance_combo_brightness = QComboBox(frame_brightness)
        self.appearance_combo_brightness.setStyleSheet(qt_stylesheet_combobox)
        self.appearance_combo_brightness.addItem("1 · Dark", 1)
        self.appearance_combo_brightness.addItem("2 · Standard", 2)
        self.appearance_combo_brightness.addItem("3 · Bright", 3)
        self.appearance_combo_brightness.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.appearance_combo_brightness.setMinimumWidth(200)
        layout_brightness.addWidget(self.appearance_combo_brightness)
        layout_brightness.addStretch()
        layout.addWidget(frame_brightness)
        hint_brightness = QLabel("Applies immediately to the whole interface.", appearance_content)
        hint_brightness.setStyleSheet("color: #a5a5a5; border: none;")
        layout.addWidget(hint_brightness)
        layout.addStretch()
        appearance_scroll = self.wrap_in_scroll_area(appearance_content)
        self.tabWidget.addTab(appearance_scroll, "Appearance")

    def create_general_tab(self):
        general_tab_content = QWidget()
        layout = QVBoxLayout(general_tab_content)
        layout.setContentsMargins(10, 10, 10, 10)
        # Paths Subcategory
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
        
        # CS2 Path row
        self.frame_cs2_path = QFrame(general_tab_content)
        layout_cs2_path = QHBoxLayout(self.frame_cs2_path)
        cs2_label = QLabel("CS2 path:", self.frame_cs2_path)
        cs2_label.setMinimumWidth(130)
        layout_cs2_path.addWidget(cs2_label)
        self.preferences_lineedit_cs2_path = QLineEdit(self.frame_cs2_path)
        layout_cs2_path.addWidget(self.preferences_lineedit_cs2_path)
        # Add "Browse" button for CS2 path
        self.browse_cs2_button = Button()
        self.browse_cs2_button.set_icon_folder_open()
        self.browse_cs2_button.set_size(27)
        layout_cs2_path.addWidget(self.browse_cs2_button)
        layout.addWidget(self.frame_cs2_path)
        # Add divider after Paths Subcategory
        layout.addWidget(self.create_divider(general_tab_content))
        # Other Subcategory
        label_other_header = QLabel("Other", general_tab_content)
        layout.addWidget(label_other_header)
        self.frame_other = QFrame(general_tab_content)
        layout_other = QVBoxLayout(self.frame_other)
        row_app = QHBoxLayout()
        self.checkBox_close_to_tray = QCheckBox("Minimize on Close", self.frame_other)
        self.checkBox_close_to_tray.setStyleSheet(qt_stylesheet_checkbox)
        row_app.addWidget(self.checkBox_close_to_tray)
        self.cleanup_model_browser_button = Button(text=" Cleanup model browser cache")
        self.cleanup_model_browser_button.set_icon_delete()
        self.cleanup_model_browser_button.setToolTip(
            "Delete the model browser's asset index and generated thumbnails. "
            "Both are rebuilt on the next browse."
        )
        row_app.addWidget(self.cleanup_model_browser_button)
        self.btn_force_association = Button(text=" Force Associate File Extensions (.vsmart, .vsndevts, .hbat)")
        self.btn_force_association.set_icon_sync()
        row_app.addWidget(self.btn_force_association)
        row_app.addStretch()
        layout_other.addLayout(row_app)

        row_git = QHBoxLayout()
        self.checkBox_git_generate_commit_messages = QCheckBox(
            "Git sync: Generate commit messages", self.frame_other)
        self.checkBox_git_generate_commit_messages.setStyleSheet(qt_stylesheet_checkbox)
        self.checkBox_git_generate_commit_messages.setToolTip(
            "Write the commit message automatically from the changed files. "
            "Turn off to be asked for a message each time you press Git Sync."
        )
        row_git.addWidget(self.checkBox_git_generate_commit_messages)
        row_git.addStretch()
        layout_other.addLayout(row_git)

        layout.addWidget(self.frame_other)
        layout.addStretch()
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
        self.spe_hide_experimental = QCheckBox("Hide experimental properties and elements", frame_interface)
        self.spe_hide_experimental.setStyleSheet(qt_stylesheet_checkbox)
        self.spe_hide_experimental.setToolTip(
            "When enabled, elements and criteria marked as experimental (not verified to work in CS2)\n"
            "are hidden from the Add Element / Add Operator / Add Criteria menus.\n"
            "Existing experimental nodes in an open file are still visible and editable."
        )
        layout_interface.addWidget(self.spe_hide_experimental)
        layout.addWidget(frame_interface)
        # Divider between subcategories
        layout.addWidget(self.create_divider(smartprop_content))
        # Format Subcategory
        label_format_header = QLabel("Format", smartprop_content)
        layout.addWidget(label_format_header)
        frame_format = QFrame(smartprop_content)
        layout_format = QVBoxLayout(frame_format)
        self.spe_export_properties = QCheckBox("Export properties in one line", frame_format)
        self.spe_export_properties.setStyleSheet(qt_stylesheet_checkbox)
        self.spe_export_properties.setChecked(True)
        layout_format.addWidget(self.spe_export_properties)
        layout.addWidget(frame_format)

        # Divider for VMAP Import Subcategory
        layout.addWidget(self.create_divider(smartprop_content))
        label_vmap_import = QLabel("VMAP Importing", smartprop_content)
        layout.addWidget(label_vmap_import)
        frame_vmap_import = QFrame(smartprop_content)
        layout_vmap_import = QVBoxLayout(frame_vmap_import)
        
        # VMAP Importing row (checkbox, label and combobox in one horizontal row)
        row_vmap_import = QHBoxLayout()
        
        self.spe_round_vmap_values = QCheckBox("Round values during VMAP import (recommended)", frame_vmap_import)
        self.spe_round_vmap_values.setStyleSheet(qt_stylesheet_checkbox)
        row_vmap_import.addWidget(self.spe_round_vmap_values)
        
        row_vmap_import.addSpacing(20)
        
        label_decimals = QLabel("Decimal places:", frame_vmap_import)
        row_vmap_import.addWidget(label_decimals)
        
        self.spe_round_vmap_decimals = QComboBox(frame_vmap_import)
        self.spe_round_vmap_decimals.setStyleSheet(qt_stylesheet_combobox)
        # Options: 2, 3, 4, 5, 6, 1, 0
        for opt in ["2", "3", "4", "5", "6", "1", "0"]:
            self.spe_round_vmap_decimals.addItem(opt, int(opt))
        row_vmap_import.addWidget(self.spe_round_vmap_decimals)
        row_vmap_import.addStretch()
        
        layout_vmap_import.addLayout(row_vmap_import)
        layout.addWidget(frame_vmap_import)

        # Divider for 3D Viewport Subcategory
        layout.addWidget(self.create_divider(smartprop_content))
        label_viewport = QLabel("3D Viewport", smartprop_content)
        layout.addWidget(label_viewport)
        frame_viewport = QFrame(smartprop_content)
        layout_viewport = QVBoxLayout(frame_viewport)

        # Anti-aliasing (MSAA) row
        row_msaa = QHBoxLayout()
        label_msaa = QLabel("Anti-aliasing (reopen file to apply):", frame_viewport)
        label_msaa.setMinimumWidth(130)
        row_msaa.addWidget(label_msaa)
        self.spe_viewport_msaa = QComboBox(frame_viewport)
        self.spe_viewport_msaa.setStyleSheet(qt_stylesheet_combobox)
        # Value stored is the MSAA sample count (0 == off).
        for text, samples in [("Off", 0), ("2x MSAA", 2), ("4x MSAA", 4), ("8x MSAA", 8)]:
            self.spe_viewport_msaa.addItem(text, samples)
        self.spe_viewport_msaa.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spe_viewport_msaa.setMinimumWidth(200)
        row_msaa.addWidget(self.spe_viewport_msaa)
        row_msaa.addStretch()
        layout_viewport.addLayout(row_msaa)
        layout.addWidget(frame_viewport)

        layout.addStretch()
        smartprop_scroll = self.wrap_in_scroll_area(smartprop_content)
        self.tabWidget.addTab(smartprop_scroll, "SmartProp Editor")

    def create_assetgroupmaker_tab(self):
        assetgroupmaker_content = QWidget()
        layout = QVBoxLayout(assetgroupmaker_content)
        layout.setContentsMargins(10, 10, 10, 10)
        # Monitor Subcategory
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
        layout.addStretch()
        sound_editor_scroll = self.wrap_in_scroll_area(sound_editor_content)
        self.tabWidget.addTab(sound_editor_scroll, "SoundEventEditor")


    def create_bottom_panel(self):
        # Use the new ActionButtonsPanel for the bottom buttons
        self.action_buttons_panel = ActionButtonsPanel(self)
        self.main_layout.addWidget(self.action_buttons_panel)

    def populate_preferences(self):
        # Interface brightness (Appearance tab)
        try:
            brightness_val = int(get_settings_value('APP', 'brightness_level', 2))
        except (TypeError, ValueError):
            brightness_val = 2
        brightness_idx = self.appearance_combo_brightness.findData(brightness_val)
        self.appearance_combo_brightness.setCurrentIndex(
            brightness_idx if brightness_idx != -1 else self.appearance_combo_brightness.findData(2))
        self.preferences_lineedit_archive_path.setText(get_settings_value('PATHS', 'archive'))
        # Populate CS2 path
        manual_cs2_path = get_manual_cs2_path()
        if manual_cs2_path:
            self.preferences_lineedit_cs2_path.setText(manual_cs2_path)
        else:
            # Show current detected path if any
            current_cs2_path = get_cs2_path()
            if current_cs2_path:
                self.preferences_lineedit_cs2_path.setPlaceholderText(f"Auto-detected: {current_cs2_path}")
            else:
                self.preferences_lineedit_cs2_path.setPlaceholderText("CS2 not found - set manually")
        self.checkBox_close_to_tray.setChecked(get_settings_bool('APP', 'minimize_to_tray', False))
        self.checkBox_git_generate_commit_messages.setChecked(
            get_settings_bool('GitSync', 'generate_commit_messages', True))
        # Same default as get_channel(), so a dev build shows the box already ticked
        self.action_buttons_panel.checkBox_dev_channel.setChecked(get_channel() == 'dev')
        # The label describes the running build, not the channel being followed
        version_text = f"Version: {self.app_version}"
        if get_build_channel() == 'dev':
            version_text += " (dev)"
        self.action_buttons_panel.version_label.setText(version_text)
        self.spe_export_properties.setChecked(get_settings_bool('SmartPropEditor', 'export_properties_in_one_line', True))
        self.spe_display_id_with_variable_class.setChecked(get_settings_bool('SmartPropEditor', 'display_id_with_variable_class', False))
        self.spe_hide_experimental.setChecked(get_settings_bool('SmartPropEditor', 'hide_experimental', True))
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

        # Populate VMAP Import settings
        self.spe_round_vmap_values.setChecked(get_settings_bool('SmartPropEditor', 'round_vmap_values', False))
        self.spe_round_vmap_decimals.setEnabled(self.spe_round_vmap_values.isChecked())
        
        decimals_val = get_settings_value('SmartPropEditor', 'round_vmap_decimals') or "4"
        idx = self.spe_round_vmap_decimals.findData(int(decimals_val))
        if idx != -1:
            self.spe_round_vmap_decimals.setCurrentIndex(idx)
        else:
            self.spe_round_vmap_decimals.setCurrentText("4")

        # Populate 3D Viewport anti-aliasing (MSAA sample count)
        try:
            msaa_val = int(get_settings_value('SmartPropEditor', 'viewport_msaa', 4))
        except (TypeError, ValueError):
            msaa_val = 4
        msaa_idx = self.spe_viewport_msaa.findData(msaa_val)
        self.spe_viewport_msaa.setCurrentIndex(msaa_idx if msaa_idx != -1 else self.spe_viewport_msaa.findData(4))

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

    def apply_brightness_level(self):
        level = int(self.appearance_combo_brightness.currentData())
        set_settings_value('APP', 'brightness_level', level)
        from src.styles import theme
        theme.set_brightness_level(level)
        theme.reapply()

    def connect_signals(self):
        self.appearance_combo_brightness.currentIndexChanged.connect(self.apply_brightness_level)
        self.preferences_lineedit_archive_path.textChanged.connect(
            lambda: set_settings_value('PATHS', 'archive', self.preferences_lineedit_archive_path.text())
        )
        self.preferences_lineedit_cs2_path.textChanged.connect(
            lambda: set_manual_cs2_path(self.preferences_lineedit_cs2_path.text())
        )
        self.browse_cs2_button.clicked.connect(self.browse_cs2_path)
        self.checkBox_close_to_tray.toggled.connect(
            lambda: set_settings_bool('APP', 'minimize_to_tray', self.checkBox_close_to_tray.isChecked())
        )
        self.action_buttons_panel.checkBox_dev_channel.toggled.connect(
            lambda checked: set_settings_bool('APP', 'dev_channel', checked)
        )
        self.checkBox_git_generate_commit_messages.toggled.connect(
            lambda checked: set_settings_bool('GitSync', 'generate_commit_messages', checked)
        )
        self.spe_display_id_with_variable_class.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'display_id_with_variable_class', self.spe_display_id_with_variable_class.isChecked())
        )
        self.spe_hide_experimental.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'hide_experimental', self.spe_hide_experimental.isChecked())
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
        self.action_buttons_panel.open_userdata_folder_button.clicked.connect(self.open_userdata_folder)
        self.cleanup_model_browser_button.clicked.connect(self.cleanup_model_browser_cache)
        self.action_buttons_panel.check_update_button.clicked.connect(self.check_update)
        self.browse_archive_button.clicked.connect(self.browse_archive)
        self.checkBox_play_on_click.toggled.connect(
            lambda: set_settings_bool('SoundEventEditor', 'play_on_click', self.checkBox_play_on_click.isChecked())
        )
        # Connect VMAP Import rounding signals
        self.spe_round_vmap_values.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'round_vmap_values', self.spe_round_vmap_values.isChecked())
        )
        self.spe_round_vmap_values.toggled.connect(self.spe_round_vmap_decimals.setEnabled)
        self.spe_round_vmap_decimals.currentIndexChanged.connect(
            lambda: set_settings_value('SmartPropEditor', 'round_vmap_decimals', str(self.spe_round_vmap_decimals.currentData()))
        )
        # Connect 3D Viewport anti-aliasing signal (stored as an int sample count)
        self.spe_viewport_msaa.currentIndexChanged.connect(
            lambda: set_settings_value('SmartPropEditor', 'viewport_msaa', int(self.spe_viewport_msaa.currentData()))
        )
        self.btn_force_association.clicked.connect(self.force_file_associations)

    def browse_archive(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Archive Path", os.getcwd())
        if selected_dir:
            self.preferences_lineedit_archive_path.setText(selected_dir)
            set_settings_value('PATHS', 'archive', selected_dir)

    def browse_cs2_path(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Counter Strike 2 Installation Path", os.getcwd())
        if selected_dir:
            # Validate that this looks like a CS2 installation
            cs2_exe_path = os.path.join(selected_dir, "game", "bin", "win64", "cs2.exe")
            if os.path.exists(cs2_exe_path):
                self.preferences_lineedit_cs2_path.setText(selected_dir)
                set_manual_cs2_path(selected_dir)
                # Show success message
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "CS2 Path Set", 
                                      f"CS2 path successfully set to:\n{selected_dir}\n\n"
                                      "Please restart the application for changes to take effect.")
            else:
                # Show error message
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid CS2 Path", 
                                  f"The selected directory does not appear to be a valid CS2 installation.\n\n"
                                  f"Expected to find: {cs2_exe_path}\n\n"
                                  "Please select the root CS2 installation directory.")

    def open_userdata_folder(self):
        from src.common import user_data_dir
        os.startfile(str(user_data_dir))

    def cleanup_model_browser_cache(self):
        """Delete the model browser's asset index and generated thumbnails.

        Both are derived data, so this is safe — the only cost is that the next
        browse rescans and re-renders. Useful after adding models to an addon, or
        after changing the thumbnail settings, since cached tiles are keyed by
        path and size and so survive a quality change.
        """
        from PySide6.QtWidgets import QMessageBox
        from src.widgets.model_browser.cache import cache_size, clear_cache, human_size

        total_bytes, file_count = cache_size()
        if not file_count:
            QMessageBox.information(self, "Cleanup model browser cache",
                                    "The model browser cache is already empty.")
            return

        reply = QMessageBox.question(
            self, "Cleanup model browser cache",
            f"Delete {file_count} cached file(s) ({human_size(total_bytes)})?\n\n"
            "The asset index and all model thumbnails will be rebuilt the next "
            "time the model browser is opened.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        freed, removed, errors = clear_cache()
        if errors:
            QMessageBox.warning(
                self, "Cleanup model browser cache",
                f"Removed {removed} file(s) ({human_size(freed)}).\n\n"
                "Failed:\n" + "\n".join(errors)
            )
        else:
            QMessageBox.information(
                self, "Cleanup model browser cache",
                f"Removed {removed} cached file(s), freeing {human_size(freed)}."
            )

    def check_update(self):
        self.action_buttons_panel.check_update_button.setEnabled(False)
        self.action_buttons_panel.version_label.setText("Checking for updates...")
        
        # We use a property on the parent to trigger the actual check
        if hasattr(self.parent(), "trigger_update_check"):
            self.parent().trigger_update_check()
        
        self.action_buttons_panel.check_update_button.setEnabled(True)
        self.populate_preferences()

    def force_file_associations(self):
        setup_all_associations(force=True, parent_window=self)
        QMessageBox.information(self, "File Associations", "File associations have been successfully updated.")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PreferencesDialog(app_version="1.0.0")
    dialog.show()
    sys.exit(app.exec())