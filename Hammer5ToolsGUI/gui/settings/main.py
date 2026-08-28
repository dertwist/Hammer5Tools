import sys
import os

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QCheckBox,
    QSizePolicy, QFrame, QScrollArea, QFileDialog, QComboBox, QMessageBox
)
from gui.settings.common import (
    get_cs2_path,
    get_manual_cs2_path,
    get_settings_bool,
    get_settings_value,
    set_manual_cs2_path,
    set_settings_bool,
    set_settings_value,
)
from gui.common import apply_title_bar_theme, refresh_title_bars, get_channel, get_build_channel
from gui.widgets.common import Button
from gui.other.file_association import setup_associations


class ActionButtonsPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        h_layout_bottom = QHBoxLayout(self)
        h_layout_bottom.setContentsMargins(9, 9, 9, 9)
        self.open_userdata_folder_button = Button(text=" Open UserData")
        self.open_userdata_folder_button.set_icon_folder_open()
        h_layout_bottom.addWidget(self.open_userdata_folder_button)

        self.btn_open_console = Button(text=" Open Console")
        self.btn_open_console.set_icon(":/icons/terminal_16dp.svg")
        self.btn_open_console.setToolTip("Open a console window for log output.")
        h_layout_bottom.addWidget(self.btn_open_console)

        h_layout_bottom.addStretch()
        self.version_label = QLabel("", self)
        h_layout_bottom.addWidget(self.version_label)
        self.checkBox_dev_channel = QCheckBox("Receive dev versions", self)
        self.checkBox_dev_channel.setProperty("h5Component", "legacyCheckbox")
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
        apply_title_bar_theme(self)
        self.setMinimumSize(830, 300)
        self.setWindowTitle('Settings')
        self.main_layout = QVBoxLayout(self)
        self.tabWidget = QTabWidget(self)
        self.tabWidget.setProperty("h5Component", "settingsTabWidget")
        self.main_layout.addWidget(self.tabWidget)
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
        divider.setFixedHeight(2)
        divider.setProperty("h5Component", "settingsDivider")
        return divider

    def wrap_in_scroll_area(self, widget):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setObjectName("customScrollArea")
        scroll_area.setProperty("h5Component", "settingsScrollArea")
        return scroll_area

    def create_general_tab(self):
        general_tab_content = QWidget()
        layout = QVBoxLayout(general_tab_content)
        layout.setContentsMargins(10, 10, 10, 10)
        label_paths_header = QLabel("Paths", general_tab_content)
        layout.addWidget(label_paths_header)
        self.frame_paths = QFrame(general_tab_content)
        layout_paths = QHBoxLayout(self.frame_paths)
        archive_label = QLabel("Archive path:", self.frame_paths)
        archive_label.setMinimumWidth(130)
        layout_paths.addWidget(archive_label)
        self.preferences_lineedit_archive_path = QLineEdit(self.frame_paths)
        layout_paths.addWidget(self.preferences_lineedit_archive_path)
        self.browse_archive_button = Button()
        self.browse_archive_button.set_icon_folder_open()
        self.browse_archive_button.set_size(27)
        layout_paths.addWidget(self.browse_archive_button)
        layout.addWidget(self.frame_paths)
        
        self.frame_cs2_path = QFrame(general_tab_content)
        layout_cs2_path = QHBoxLayout(self.frame_cs2_path)
        cs2_label = QLabel("CS2 path:", self.frame_cs2_path)
        cs2_label.setMinimumWidth(130)
        layout_cs2_path.addWidget(cs2_label)
        self.preferences_lineedit_cs2_path = QLineEdit(self.frame_cs2_path)
        layout_cs2_path.addWidget(self.preferences_lineedit_cs2_path)
        self.browse_cs2_button = Button()
        self.browse_cs2_button.set_icon_folder_open()
        self.browse_cs2_button.set_size(27)
        layout_cs2_path.addWidget(self.browse_cs2_button)
        layout.addWidget(self.frame_cs2_path)
        layout.addWidget(self.create_divider(general_tab_content))
        label_appearance_header = QLabel("Appearance", general_tab_content)
        layout.addWidget(label_appearance_header)
        frame_theme = QFrame(general_tab_content)
        layout_theme = QHBoxLayout(frame_theme)
        label_theme = QLabel("Theme:", frame_theme)
        label_theme.setMinimumWidth(130)
        layout_theme.addWidget(label_theme)
        self.appearance_combo_theme = QComboBox(frame_theme)
        self.appearance_combo_theme.setProperty("h5Component", "legacyCombobox")
        self.appearance_combo_theme.addItem("System", 0)
        self.appearance_combo_theme.addItem("Dark", 2)
        self.appearance_combo_theme.addItem("Bright", 3)
        self.appearance_combo_theme.addItem("Vintage Steam", 4)
        self.appearance_combo_theme.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.appearance_combo_theme.setMinimumWidth(200)
        layout_theme.addWidget(self.appearance_combo_theme)
        layout_theme.addStretch()
        layout.addWidget(frame_theme)
        layout.addWidget(self.create_divider(general_tab_content))
        label_app_header = QLabel("Application", general_tab_content)
        layout.addWidget(label_app_header)
        self.frame_app = QFrame(general_tab_content)
        layout_app = QHBoxLayout(self.frame_app)
        self.checkBox_close_to_tray = QCheckBox("Minimize on Close", self.frame_app)
        self.checkBox_close_to_tray.setProperty("h5Component", "legacyCheckbox")
        layout_app.addWidget(self.checkBox_close_to_tray)
        self.cleanup_model_browser_button = Button(text=" Cleanup model browser cache")
        self.cleanup_model_browser_button.set_icon_delete()
        self.cleanup_model_browser_button.setToolTip(
            "Delete the model browser's asset index and generated thumbnails. "
            "Both are rebuilt on the next browse."
        )
        layout_app.addWidget(self.cleanup_model_browser_button)
        layout_app.addStretch()
        layout.addWidget(self.frame_app)
        layout.addWidget(self.create_divider(general_tab_content))

        label_associations_header = QLabel("File Associations", general_tab_content)
        layout.addWidget(label_associations_header)
        self.frame_associations = QFrame(general_tab_content)
        layout_associations = QHBoxLayout(self.frame_associations)
        self.association_buttons = {}
        for ext, label in ((".vsmart", "SmartProp"), (".vsndevts", "SoundEvents"), (".hbat", "Hammer Batch")):
            button = Button(text=f" Associate {ext} ({label})")
            button.set_icon_sync()
            layout_associations.addWidget(button)
            self.association_buttons[ext] = button
        layout_associations.addStretch()
        layout.addWidget(self.frame_associations)
        layout.addWidget(self.create_divider(general_tab_content))

        label_git_header = QLabel("Git Sync", general_tab_content)
        layout.addWidget(label_git_header)
        self.frame_git = QFrame(general_tab_content)
        layout_git = QHBoxLayout(self.frame_git)
        self.checkBox_git_generate_commit_messages = QCheckBox(
            "Generate commit messages", self.frame_git)
        self.checkBox_git_generate_commit_messages.setProperty("h5Component", "legacyCheckbox")
        self.checkBox_git_generate_commit_messages.setToolTip(
            "Write the commit message automatically from the changed files. "
            "Turn off to be asked for a message each time you press Git Sync."
        )
        layout_git.addWidget(self.checkBox_git_generate_commit_messages)
        layout_git.addStretch()
        layout.addWidget(self.frame_git)

        layout.addStretch()
        general_scroll = self.wrap_in_scroll_area(general_tab_content)
        self.tabWidget.addTab(general_scroll, "General")

    def create_smartprop_tab(self):
        smartprop_content = QWidget()
        layout = QVBoxLayout(smartprop_content)
        layout.setContentsMargins(10, 10, 10, 10)
        label_interface_header = QLabel("Interface", smartprop_content)
        layout.addWidget(label_interface_header)
        frame_interface = QFrame(smartprop_content)
        layout_interface = QVBoxLayout(frame_interface)
        self.spe_display_id_with_variable_class = QCheckBox("Display ID with variable class (Reopen file)", frame_interface)
        self.spe_display_id_with_variable_class.setProperty("h5Component", "legacyCheckbox")
        layout_interface.addWidget(self.spe_display_id_with_variable_class)
        self.spe_hide_experimental = QCheckBox("Hide experimental properties and elements", frame_interface)
        self.spe_hide_experimental.setProperty("h5Component", "legacyCheckbox")
        self.spe_hide_experimental.setToolTip(
            "When enabled, elements and criteria marked as experimental (not verified to work in CS2)\n"
            "are hidden from the Add Element / Add Operator / Add Criteria menus.\n"
            "Existing experimental nodes in an open file are still visible and editable."
        )
        layout_interface.addWidget(self.spe_hide_experimental)
        layout.addWidget(frame_interface)

        layout.addWidget(self.create_divider(smartprop_content))
        label_vmap_import = QLabel("VMAP Importing", smartprop_content)
        layout.addWidget(label_vmap_import)
        frame_vmap_import = QFrame(smartprop_content)
        layout_vmap_import = QVBoxLayout(frame_vmap_import)
        
        row_vmap_import = QHBoxLayout()
        
        self.spe_round_vmap_values = QCheckBox("Round values during VMAP import (recommended)", frame_vmap_import)
        self.spe_round_vmap_values.setProperty("h5Component", "legacyCheckbox")
        row_vmap_import.addWidget(self.spe_round_vmap_values)
        
        row_vmap_import.addSpacing(20)
        
        label_decimals = QLabel("Decimal places:", frame_vmap_import)
        row_vmap_import.addWidget(label_decimals)
        
        self.spe_round_vmap_decimals = QComboBox(frame_vmap_import)
        self.spe_round_vmap_decimals.setProperty("h5Component", "legacyCombobox")
        for opt in ["2", "3", "4", "5", "6", "1", "0"]:
            self.spe_round_vmap_decimals.addItem(opt, int(opt))
        row_vmap_import.addWidget(self.spe_round_vmap_decimals)
        row_vmap_import.addStretch()
        
        layout_vmap_import.addLayout(row_vmap_import)
        layout.addWidget(frame_vmap_import)

        layout.addWidget(self.create_divider(smartprop_content))
        label_viewport = QLabel("3D Viewport", smartprop_content)
        layout.addWidget(label_viewport)
        frame_viewport = QFrame(smartprop_content)
        layout_viewport = QVBoxLayout(frame_viewport)

        row_msaa = QHBoxLayout()
        label_msaa = QLabel("Anti-aliasing (reopen file to apply):", frame_viewport)
        label_msaa.setMinimumWidth(130)
        row_msaa.addWidget(label_msaa)
        self.spe_viewport_msaa = QComboBox(frame_viewport)
        self.spe_viewport_msaa.setProperty("h5Component", "legacyCombobox")
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
        layout.addStretch()
        assetgroupmaker_scroll = self.wrap_in_scroll_area(assetgroupmaker_content)
        self.tabWidget.addTab(assetgroupmaker_scroll, "AssetGroupMaker")

    def create_sound_event_editor_tab(self):
        sound_editor_content = QWidget()
        layout = QVBoxLayout(sound_editor_content)
        layout.setContentsMargins(10, 10, 10, 10)
        label_audio_header = QLabel("AudioPlayer", sound_editor_content)
        layout.addWidget(label_audio_header)
        self.frame_audio = QFrame(sound_editor_content)
        layout_audio = QHBoxLayout(self.frame_audio)
        self.checkBox_play_on_click = QCheckBox("Play on Click", self.frame_audio)
        self.checkBox_play_on_click.setProperty("h5Component", "legacyCheckbox")
        layout_audio.addWidget(self.checkBox_play_on_click)
        layout.addWidget(self.frame_audio)
        layout.addStretch()
        sound_editor_scroll = self.wrap_in_scroll_area(sound_editor_content)
        self.tabWidget.addTab(sound_editor_scroll, "SoundEventEditor")


    def create_bottom_panel(self):
        self.action_buttons_panel = ActionButtonsPanel(self)
        self.btn_open_console = self.action_buttons_panel.btn_open_console
        self.main_layout.addWidget(self.action_buttons_panel)

    def populate_preferences(self):
        try:
            theme_level = int(get_settings_value('APP', 'theme_level', 0))
        except (TypeError, ValueError):
            theme_level = 0
        theme_idx = self.appearance_combo_theme.findData(theme_level)
        self.appearance_combo_theme.setCurrentIndex(
            theme_idx if theme_idx != -1 else self.appearance_combo_theme.findData(0))
        self.preferences_lineedit_archive_path.setText(get_settings_value('PATHS', 'archive'))
        manual_cs2_path = get_manual_cs2_path()
        if manual_cs2_path:
            self.preferences_lineedit_cs2_path.setText(manual_cs2_path)
        else:
            current_cs2_path = get_cs2_path()
            if current_cs2_path:
                self.preferences_lineedit_cs2_path.setPlaceholderText(f"Auto-detected: {current_cs2_path}")
            else:
                self.preferences_lineedit_cs2_path.setPlaceholderText("CS2 not found - set manually")
        self.checkBox_close_to_tray.setChecked(get_settings_bool('APP', 'minimize_to_tray', False))
        self.checkBox_git_generate_commit_messages.setChecked(
            get_settings_bool('GitSync', 'generate_commit_messages', True))
        self.action_buttons_panel.checkBox_dev_channel.setChecked(get_channel() == 'dev')
        version_text = f"Version: {self.app_version}"
        if get_build_channel() == 'dev':
            version_text += " (dev)"
        self.action_buttons_panel.version_label.setText(version_text)
        self.spe_display_id_with_variable_class.setChecked(get_settings_bool('SmartPropEditor', 'display_id_with_variable_class', False))
        self.spe_hide_experimental.setChecked(get_settings_bool('SmartPropEditor', 'hide_experimental', True))
        self.assetgroupmaker_lineedit_monitor.setText(get_settings_value('AssetGroupMaker', 'monitor_folders') or "models, materials, smartprops")
        self.checkBox_play_on_click.setChecked(get_settings_bool('SoundEventEditor', 'play_on_click', True))

        self.spe_round_vmap_values.setChecked(get_settings_bool('SmartPropEditor', 'round_vmap_values', False))
        self.spe_round_vmap_decimals.setEnabled(self.spe_round_vmap_values.isChecked())
        
        decimals_val = get_settings_value('SmartPropEditor', 'round_vmap_decimals') or "4"
        idx = self.spe_round_vmap_decimals.findData(int(decimals_val))
        if idx != -1:
            self.spe_round_vmap_decimals.setCurrentIndex(idx)
        else:
            self.spe_round_vmap_decimals.setCurrentText("4")

        try:
            msaa_val = int(get_settings_value('SmartPropEditor', 'viewport_msaa', 4))
        except (TypeError, ValueError):
            msaa_val = 4
        msaa_idx = self.spe_viewport_msaa.findData(msaa_val)
        self.spe_viewport_msaa.setCurrentIndex(msaa_idx if msaa_idx != -1 else self.spe_viewport_msaa.findData(4))

    def apply_theme_level(self):
        level = int(self.appearance_combo_theme.currentData())
        from gui.styles import theme
        from gui.styles import manager as style_manager
        # reapply() repolishes every live widget in the application, which costs
        # seconds on a loaded session. Re-selecting the level already in effect
        # must not pay that.
        if level == theme.selected():
            return
        set_settings_value('APP', 'theme_level', level)
        theme.set_level(level)
        style_manager.reapply(theme.get_theme())
        refresh_title_bars()

    def connect_signals(self):
        # activated, not currentIndexChanged: the latter also fires while the user
        # arrows through the list and on populate_preferences()'s setCurrentIndex(),
        # each one a full application repolish.
        self.appearance_combo_theme.activated.connect(self.apply_theme_level)
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
        self.action_buttons_panel.btn_open_console.clicked.connect(self._open_console)
        self.spe_display_id_with_variable_class.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'display_id_with_variable_class', self.spe_display_id_with_variable_class.isChecked())
        )
        self.spe_hide_experimental.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'hide_experimental', self.spe_hide_experimental.isChecked())
        )
        self.assetgroupmaker_lineedit_monitor.textChanged.connect(
            lambda: set_settings_value('AssetGroupMaker', 'monitor_folders', self.assetgroupmaker_lineedit_monitor.text())
        )
        self.action_buttons_panel.open_userdata_folder_button.clicked.connect(self.open_userdata_folder)
        self.cleanup_model_browser_button.clicked.connect(self.cleanup_model_browser_cache)
        self.action_buttons_panel.check_update_button.clicked.connect(self.check_update)
        self.browse_archive_button.clicked.connect(self.browse_archive)
        self.checkBox_play_on_click.toggled.connect(
            lambda: set_settings_bool('SoundEventEditor', 'play_on_click', self.checkBox_play_on_click.isChecked())
        )
        self.spe_round_vmap_values.toggled.connect(
            lambda: set_settings_bool('SmartPropEditor', 'round_vmap_values', self.spe_round_vmap_values.isChecked())
        )
        self.spe_round_vmap_values.toggled.connect(self.spe_round_vmap_decimals.setEnabled)
        self.spe_round_vmap_decimals.currentIndexChanged.connect(
            lambda: set_settings_value('SmartPropEditor', 'round_vmap_decimals', str(self.spe_round_vmap_decimals.currentData()))
        )
        self.spe_viewport_msaa.currentIndexChanged.connect(
            lambda: set_settings_value('SmartPropEditor', 'viewport_msaa', int(self.spe_viewport_msaa.currentData()))
        )
        for ext, button in self.association_buttons.items():
            button.clicked.connect(lambda _=False, ext=ext: self.force_file_association(ext))

    def browse_archive(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Archive Path", os.getcwd())
        if selected_dir:
            self.preferences_lineedit_archive_path.setText(selected_dir)
            set_settings_value('PATHS', 'archive', selected_dir)

    def browse_cs2_path(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Counter Strike 2 Installation Path", os.getcwd())
        if selected_dir:
            cs2_exe_path = os.path.join(selected_dir, "game", "bin", "win64", "cs2.exe")
            if os.path.exists(cs2_exe_path):
                self.preferences_lineedit_cs2_path.setText(selected_dir)
                set_manual_cs2_path(selected_dir)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "CS2 Path Set", 
                                      f"CS2 path successfully set to:\n{selected_dir}\n\n"
                                      "Please restart the application for changes to take effect.")
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid CS2 Path", 
                                  f"The selected directory does not appear to be a valid CS2 installation.\n\n"
                                  f"Expected to find: {cs2_exe_path}\n\n"
                                  "Please select the root CS2 installation directory.")

    def open_userdata_folder(self):
        from gui.common import user_data_dir
        os.startfile(str(user_data_dir))

    def cleanup_model_browser_cache(self):
        """Delete the model browser's asset index and generated thumbnails.

        Both are derived data, so this is safe — the only cost is that the next
        browse rescans and re-renders. Useful after adding models to an addon, or
        after changing the thumbnail settings, since cached tiles are keyed by
        path and size and so survive a quality change.
        """
        from PySide6.QtWidgets import QMessageBox
        from gui.widgets.model_browser.cache import cache_size, clear_cache, human_size

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
        
        if hasattr(self.parent(), "trigger_update_check"):
            self.parent().trigger_update_check()
        
        self.action_buttons_panel.check_update_button.setEnabled(True)
        self.populate_preferences()

    def _open_console(self):
        from gui.other.console import open_console
        open_console()

    def force_file_association(self, extension):
        setup_associations([extension])
        QMessageBox.information(self, "File Associations", f"{extension} is now associated with Hammer5Tools.")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = PreferencesDialog(app_version="1.0.0")
    dialog.show()
    sys.exit(app.exec())
