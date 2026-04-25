import sys
import os
import ctypes
import threading
import webbrowser
import time
import argparse

# ==========================================================================================
# VELOPACK / SQUIRREL HOOKS
# This MUST run before any other imports (especially Qt) to prevent the GUI from opening
# during installation, uninstallation, or updates.
# ==========================================================================================
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
    QLabel,
    QCheckBox,
    QDockWidget,
    QDialog
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QPoint,
    QFileSystemWatcher,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from src.ipc.protocol import IPCMessage, IPCCommand
from src.forms.about.main import AboutDialog
from src.forms.mapbuilder.main import MapBuilderDialog
from src.settings.main import (
    PreferencesDialog,
    get_steam_path,
    get_cs2_path,
    get_addon_name,
    set_addon_name,
    get_settings_bool,
    set_settings_bool,
    get_settings_value,
    set_settings_value,
    settings,
    debug,
    get_addon_dir
)
from src.editors.loading_editor.main import Loading_editorMainWindow
from src.editors.hotkey_editor.main import HotkeyEditorMainWindow
from src.forms.create_addon.main import Create_addon_Dialog
from src.other.steam_restart import SteamNoLogoFixThreadClass
from src.other.addon_functions import delete_addon, launch_addon
from src.forms.file_association_prompt.main import FileAssociationPromptDialog
from src.other.file_association import check_association
from src.updater.check import check_updates
from src.forms.export.main import ExportAndImportAddonDialog
from src.editors.assetgroup_maker.main import BatchCreatorMainWindow
from src.editors.smartprop_editor.main import SmartPropEditorMainWindow
from src.editors.soundevent_editor.main import SoundEventEditorMainWindow
from src.editors.ue2source_materials.main import UE2SourceMaterialsWidget
from src.forms.launch_options.main import LaunchOptionsDialog
from src.styles.qt_global_stylesheet import QT_Stylesheet_global
from src.common import enable_dark_title_bar, app_version, default_commands, app_dir, JsonToKv3, compile as run_compile
from src.dotnet import check_dotnet_runtime
from src.other.addon_validation import validate_addon_structure
from src.forms.cleanup.main import CleanupDialog
from src.forms.quick_create.main import QuickCreateDialog
# from src.updater.velopack_manager import VelopackManager



from src.widgets import *
# Global paths
steam_path = get_steam_path()
cs2_path = get_cs2_path()
print(f'Cs2: {get_cs2_path()}')
stop_discord_thread = threading.Event()
INSTANCE_KEY = "Hammer5ToolsIPC"

def activate_existing_window(hwnd):
    """
    Activate and redraw an existing window identified by hwnd
    using Win32 API calls.
    """
    SW_RESTORE = 9
    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
    ctypes.windll.user32.UpdateWindow(hwnd)
    ctypes.windll.user32.SetForegroundWindow(hwnd)

def restore_window(hwnd):
    """
    Force restoration of window using Win32 API.
    """
    SW_NORMAL = 1
    SW_RESTORE = 9
    SW_SHOW = 5
    ctypes.windll.user32.ShowWindow(hwnd, SW_NORMAL)
    time.sleep(0.1)
    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
    ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    ctypes.windll.user32.BringWindowToTop(hwnd)
    ctypes.windll.user32.SwitchToThisWindow(hwnd, True)

def allocate_console():
    """
    Allocate a console window for a GUI application built with --windowed.
    This allows console output if '--console' flag is provided.
    """
    if not ctypes.windll.kernel32.GetConsoleWindow():
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")
        
class DevWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Development Widget")
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout()
        label = QLabel("Development Mode Active", self)
        layout.addWidget(label)
        self.checkBox_debug_info = QCheckBox("Enable Debug Info", self)
        self.checkBox_debug_info.setChecked(get_settings_bool('OTHER', 'debug_info', False))
        self.checkBox_debug_info.toggled.connect(
            lambda: set_settings_bool('OTHER', 'debug_info', self.checkBox_debug_info.isChecked())
        )
        layout.addWidget(self.checkBox_debug_info)
        from src.widgets.property.viewport import PropertyViewport
        window = PropertyViewport()
        window.resize(500, 300)
        window.show()
        self.setLayout(layout)
        
class Widget(QMainWindow):
    def __init__(self, parent=None, dev_mode=False):
        super().__init__(parent)
        from src.ui_main import Ui_MainWindow
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)

        self.preferences_dialog = None
        self.mapbuilder_dialog = None
        self.launch_options = None
        self.Create_addon_Dialog = None
        self.Delete_addon_Dialog = None

        #Checking for Counter Strike 2 installation
        if cs2_path is None:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Counter Strike 2 Not Found")
            msg_box.setText("Counter Strike 2 installation was not found automatically.\n\n"
                          "You can manually set the CS2 path in Settings > General > CS2 Path.\n\n"
                          "Would you like to continue anyway?")
            exit_button = msg_box.addButton("Exit", QMessageBox.RejectRole)
            settings_button = msg_box.addButton("Open Settings", QMessageBox.ActionRole)
            continue_button = msg_box.addButton("Continue Anyway", QMessageBox.AcceptRole)
            msg_box.setDefaultButton(settings_button)
            result = msg_box.exec()
            
            if msg_box.clickedButton() == exit_button:
                sys.exit(1)
            elif msg_box.clickedButton() == settings_button:
                # We'll open settings after the main window is fully initialized
                QTimer.singleShot(500, self.open_preferences_dialog)

        # Setup tray icon early so that restoration has a fallback.
        self.setup_tray_icon()
        self.setup_tabs()
        self.setup_buttons()
        self.current_tab(False)
        self.settings = settings

        self.default_title = "Hammer 5 Tools"
        self.setWindowTitle(self.default_title)

        self.title_reset_timer = QTimer(self)
        self.title_reset_timer.setSingleShot(True)
        self.title_reset_timer.timeout.connect(self.reset_title)

        self.launchOptionPoller = QTimer(self)
        self.launchOptionPoller.setInterval(1000)
        self.launchOptionPoller.timeout.connect(self.updateLaunchAddonButton)
        self.launchOptionPoller.start()

        if dev_mode:
            self.dev_widget = DevWidget(self)
            self.ui.centralwidget.layout().addWidget(self.dev_widget)

        QTimer.singleShot(100, self.deferred_update_check)
        self._restore_user_prefs()
        if get_settings_bool('APP', 'first_launch'):
            self.open_about()
            set_settings_bool('APP', 'first_launch', False)
        
        # Check for file associations after a short delay
        QTimer.singleShot(2000, self.check_file_associations)

        # Setup filesystem watcher for addon folder.
        self.addon_watcher = QFileSystemWatcher(self)
        if cs2_path is not None:
            addon_folder_path = os.path.join(cs2_path, "content", "csgo_addons")
            if os.path.exists(addon_folder_path):
                self.addon_watcher.addPath(addon_folder_path)
                self.addon_watcher.directoryChanged.connect(self.refresh_addon_combobox)

        for dock in self.findChildren(QDockWidget):
            dock.show()
        for child in self.findChildren(QMainWindow):
            for dock in child.findChildren(QDockWidget):
                dock.show()
        validate_addon_structure()
        # self.velopack_manager = VelopackManager(self)
        # self.velopack_manager.check_for_updates(interactive=False)

    def trigger_update_check(self):
        """Called from settings dialog to manually trigger a check."""
        check_updates("https://github.com/dertwist/Hammer5Tools", app_version, False)



    def deferred_update_check(self):
        try:
            check_updates("https://github.com/dertwist/Hammer5Tools", app_version, True)
        except Exception as e:
            print(f"Error checking updates: {e}")

    def check_file_associations(self):
        """Checks if .vsmart files are associated with the app and prompts if not."""
        if not get_settings_bool('APP', 'check_associations', True):
            return
            
        _, is_us = check_association('.vsmart')
        if not is_us:
            dialog = FileAssociationPromptDialog(self)
            if dialog.exec() == QDialog.Accepted:
                # Associations registered inside dialog
                pass
            
            if dialog.dont_ask_again:
                set_settings_bool('APP', 'check_associations', False)

    @exception_handler
    def update_title(self, status=None, file_path=None, text=None):
        base_title = "Hammer 5 Tools"
        new_title = base_title
        if file_path:
            if status == "saved":
                new_title = f"{base_title} [ Saved file --- {file_path} ]"
            elif status == "opened":
                new_title = f"{base_title} [ Opened file --- {file_path} ]"
        elif text:
            new_title = f"{base_title} [ {text} ]"
        self.setWindowTitle(new_title)
        self.title_reset_timer.start(5000)

    def reset_title(self):
        self.setWindowTitle(self.default_title)

    def current_tab(self, set_flag):
        if set_flag:
            try:
                set_settings_value('APP', 'current_tab', str(self.ui.MainWindowTools_tabs.currentIndex()))
            except Exception:
                pass
        else:
            try:
                current_tab = int(get_settings_value('APP', 'current_tab'))
                self.ui.MainWindowTools_tabs.setCurrentIndex(current_tab)
            except Exception:
                pass

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme(":/icons/appicon.ico"), self)
        self.tray_icon.setToolTip("Hammer5Tools")
        self.tray_menu = QMenu()
        show_action = QAction("Show", self, triggered=self.show_from_tray)
        exit_action = QAction("Exit", self, triggered=self.exit_application)
        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_from_tray()

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        hwnd = self.winId().__int__()
        restore_window(hwnd)

        for dock in self.findChildren(QDockWidget):
            dock.show()
        for child in self.findChildren(QMainWindow):
            for dock in child.findChildren(QDockWidget):
                dock.show()

    def open_file_in_smartprop(self, file_path):
        """
        Open a file in SmartProp Editor. If already open, focus that document.
        
        Args:
            file_path: Absolute path to the .vsmart or .vdata file
        """
        if not self.SmartPropEditorMainWindow:
            print("SmartProp Editor not initialized")
            return
        
        # Switch to SmartProp Editor tab
        smartprop_tab_index = self.ui.MainWindowTools_tabs.indexOf(
            self.ui.smartpropeditor_tab
        )
        if smartprop_tab_index >= 0:
            self.ui.MainWindowTools_tabs.setCurrentIndex(smartprop_tab_index)
        
        # Open the file (will focus if already open)
        self.SmartPropEditorMainWindow.open_file(filename=file_path)

    def open_quick_create_dialog(self, folder_path, file_type):
        """
        Open the quick create dialog for VMDL/VMAT.
        
        Args:
            folder_path: Directory where to create the file
            file_type: 'vmdl' or 'vmat'
        """
        dialog = QuickCreateDialog(folder_path, file_type, self)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def check_addon_mismatch(self, addon_hint):
        """
        Check if the action is intended for a different addon.
        If so, ask the user to switch.
        """
        if not addon_hint:
            return True
        current_addon = get_addon_name()
        if addon_hint.lower() == current_addon.lower():
            return True
        
        # Mismatch!
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Addon Mismatch")
        msg_box.setText(f"This file belongs to addon '{addon_hint}', but Hammer5Tools is currently using '{current_addon}'.")
        msg_box.setInformativeText("Would you like to switch to the correct addon before proceeding?")
        
        switch_button = msg_box.addButton("Switch Addon", QMessageBox.AcceptRole)
        keep_button = msg_box.addButton("Keep Current", QMessageBox.RejectRole)
        cancel_button = msg_box.addButton(QMessageBox.Cancel)
        
        msg_box.setDefaultButton(switch_button)
        msg_box.exec()
        
        if msg_box.clickedButton() == switch_button:
            self.ui.ComboBoxSelectAddon.setCurrentText(addon_hint)
            # setCurrentText will trigger selected_addon_name if it changed
            return True
        elif msg_box.clickedButton() == keep_button:
            return True
        else:
            return False

    def handle_quick_vmdl(self, path):
        """Create a VMDL file next to a mesh or in a folder."""
        if os.path.isfile(path):
            folder = os.path.dirname(path)
            basename = os.path.splitext(os.path.basename(path))[0]
            vmdl_path = os.path.join(folder, f"{basename}.vmdl")
            
            # Extract relative path for mesh reference
            addon_dir = get_addon_dir()
            try:
                rel_mesh = os.path.relpath(path, addon_dir).replace('\\', '/')
            except (ValueError, Exception):
                rel_mesh = ""
            
            from src.editors.assetgroup_maker.objects import DEFAULT_VMDL
            from src.common import fast_deepcopy
            
            vmdl_content = fast_deepcopy(DEFAULT_VMDL)
            
            # Populate the template with the mesh path
            for child in vmdl_content.get('rootNode', {}).get('children', []):
                if child.get('_class') == 'RenderMeshList':
                    for mesh_file in child.get('children', []):
                        if mesh_file.get('_class') == 'RenderMeshFile':
                            mesh_file['filename'] = rel_mesh
                if child.get('_class') == 'PhysicsShapeList':
                    for phys_file in child.get('children', []):
                        if phys_file.get('_class') == 'PhysicsHullFile':
                            phys_file['filename'] = rel_mesh
                            phys_file['name'] = basename

            kv3_content = JsonToKv3(vmdl_content, format='vmdl')
            try:
                with open(vmdl_path, 'w') as f:
                    f.write(kv3_content)
                self.update_title(text=f"Created VMDL: {os.path.basename(vmdl_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create VMDL: {e}")
        else:
            # Create blank VMDL in folder
            self.open_quick_create_dialog(path, "vmdl")

    def handle_quick_batch(self, path):
        """Create a .bat stub for ResourceCompiler in the folder (or file's folder)."""
        target_dir = path if os.path.isdir(path) else os.path.dirname(path)
        
        if os.path.isdir(target_dir):
            cs2_path = get_cs2_path()
            if not cs2_path:
                QMessageBox.warning(self, "CS2 Not Found", "CS2 installation path not set.")
                return
            rc_exe = os.path.join(cs2_path, "game", "bin", "win64", "resourcecompiler.exe")
            
            bat_content = f'@echo off\n"{rc_exe}" -i "*.vmdl" "*.vmat"\npause'
            bat_path = os.path.join(target_dir, "compile_assets.bat")
            try:
                with open(bat_path, 'w') as f:
                    f.write(bat_content)
                self.update_title(text=f"Created Batch: {os.path.basename(bat_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create Batch file: {e}")

    def handle_quick_process(self, path):
        """Run a compile job on the folder."""
        if os.path.isdir(path):
            self.update_title(text=f"Processing folder: {os.path.basename(path)}...")
            run_compile(os.path.join(path, "*.vmdl"))
            run_compile(os.path.join(path, "*.vmat"))

    def handle_quick_process_file(self, path):
        """Trigger a compile on a specific asset file."""
        if os.path.isfile(path):
            self.update_title(text=f"Processing file: {os.path.basename(path)}...")
            run_compile(path)

    def setup_tabs(self):
        self.HotkeyEditorMainWindow_instance = HotkeyEditorMainWindow()
        self.ui.hotkeyeditor_tab.layout().addWidget(self.HotkeyEditorMainWindow_instance)
        
    def populate_addon_combobox(self):
        exclude_addons = {"workshop_items", "addon_template"}
        
        # Check if CS2 path is available
        if cs2_path is None:
            print("CS2 path not set, cannot populate addon combobox")
            self.ui.ComboBoxSelectAddon.addItem("CS2 Path Not Set")
            self.ui.ComboBoxSelectAddon.setCurrentIndex(0)
            return
            
        addons_folder = os.path.join(cs2_path, "content", "csgo_addons")
        found_any = False
        try:
            if not os.path.exists(addons_folder):
                print(f"Addons folder does not exist: {addons_folder}")
                self.ui.ComboBoxSelectAddon.addItem("Addons Folder Not Found")
                self.ui.ComboBoxSelectAddon.setCurrentIndex(0)
                return
                
            for item in os.listdir(addons_folder):
                full_path = os.path.join(addons_folder, item)
                if os.path.isdir(full_path) and item not in exclude_addons:
                    self.ui.ComboBoxSelectAddon.addItem(item)
                    found_any = True

            if not found_any:
                response = QMessageBox.question(
                    self,
                    "No Addon Found",
                    "No addons found. Would you like to create one now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if response == QMessageBox.Yes:
                    Create_addon_Dialog(self).exec()
                    self.refresh_addon_combobox()
                    return
                else:
                    self.ui.ComboBoxSelectAddon.addItem("")
                    self.ui.ComboBoxSelectAddon.setCurrentIndex(0)

            if not get_addon_name() and found_any:
                set_addon_name(self.ui.ComboBoxSelectAddon.currentText())
        except Exception as e:
            print("Failed to load addons:", e)

    def refresh_addon_combobox(self):
        try:
            self.ui.ComboBoxSelectAddon.currentTextChanged.disconnect(self.selected_addon_name)
        except Exception:
            pass

        addon = get_addon_name()
        self.ui.ComboBoxSelectAddon.clear()
        self.populate_addon_combobox()
        self.ui.ComboBoxSelectAddon.setCurrentText(addon)
        self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)

        tools = [
            "SoundEventEditorMainWindow",
            "SmartPropEditorMainWindow",
            "BatchCreator_MainWindow",
            "LoadingEditorMainWindow",
        ]
        if not any(getattr(self, tool, None) for tool in tools):
            self.selected_addon_name()

    def animate_launch_button(self):
        button = self.ui.Launch_Addon_Button
        overlay = QWidget(button)
        overlay.setObjectName("launchOverlay")
        overlay.setAttribute(Qt.WA_StyledBackground, True)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay.setStyleSheet(
            """
            QWidget#launchOverlay {
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 1, y2: 0,
                    stop: 0 rgba(65,73,86,0.25),
                    stop: 0.2 rgba(65,73,86,0.40),
                    stop: 0.8 rgba(65,73,86,0.40),
                    stop: 1 rgba(65,73,86,0.25)
                );
            }
            """
        )
        button_width = button.width()
        button_height = button.height()
        overlay.setGeometry(-button_width, 0, button_width, button_height)
        overlay.show()
        overlay.lower()
        animation = QPropertyAnimation(overlay, b"pos", self)
        animation.setDuration(1200)
        animation.setStartValue(QPoint(-button_width, 0))
        animation.setEndValue(QPoint(button_width, 0))
        def on_animation_finished():
            overlay.deleteLater()
        animation.finished.connect(on_animation_finished)
        animation.start()

    def launch_addon_action(self):
        self.animate_launch_button()
        self.update_title(text=f'Launched addon --- {get_addon_name()}')
        launch_addon()

    def setup_buttons(self):
        self.ui.Launch_Addon_Button.clicked.connect(self.launch_addon_action)
        self.ui.FixNoSteamLogon_Button.clicked.connect(self.SteamNoLogonFix)
        self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)
        addon = get_addon_name()
        combo_items = [self.ui.ComboBoxSelectAddon.itemText(i) for i in range(self.ui.ComboBoxSelectAddon.count())]
        if addon not in combo_items:
            self.refresh_addon_combobox()
            self.selected_addon_name()
        if self.ui.ComboBoxSelectAddon.currentText() == get_addon_name():
            self.selected_addon_name()
        self.ui.ComboBoxSelectAddon.setCurrentText(get_addon_name())
        self.ui.ComboBoxSelectAddon.activated.connect(self.refresh_addon_combobox)
        self.ui.preferences_button.clicked.connect(self.open_preferences_dialog)
        self.ui.create_new_addon_button.clicked.connect(self.open_create_addon_dialog)
        self.ui.delete_addon_button.clicked.connect(self.delete_addon)
        self.ui.launch_settings.clicked.connect(self.open_launch_options)
        self.ui.export_and_import_addon_button.clicked.connect(self.open_export_and_import_addon)
        self.ui.open_addons_folder_button.clicked.connect(self.open_addons_folder)
        self.ui.my_twitter_button.clicked.connect(self.open_my_twitter)
        self.ui.discord.clicked.connect(self.open_discord)
        self.ui.documentation_button.clicked.connect(self.open_about)
        self.ui.mapbuilder.clicked.connect(self.open_mapbuilder_dialog)
        self.ui.open_dialog_button.clicked.connect(self.open_selected_dialog)
        

        self.updateLaunchAddonButton()

    def open_asset_exporter(self):
        from src.editors.asset_exporter.main import AssetExporterWidget
        self.asset_exporter_window = AssetExporterWidget()
        self.asset_exporter_window.show()

    def open_asset_manager(self):
        from src.editors.asset_manager.main import AssetManagerWidget
        self.asset_manager_window = AssetManagerWidget()
        self.asset_manager_window.show()

    def updateLaunchAddonButton(self):
        commands = get_settings_value("LAUNCH", "commands", default_commands)
        if commands and "-asset" in commands:
            self.ui.Launch_Addon_Button.setText("Edit map")
        else:
            self.ui.Launch_Addon_Button.setText("Launch Tools")

    def closeEvent(self, event):
        if get_settings_bool("APP", "minimize_to_tray", False):
            event.ignore()
            self.hide()

            for dock in self.findChildren(QDockWidget):
                dock.hide()
            for child in self.findChildren(QMainWindow):
                for dock in child.findChildren(QDockWidget):
                    dock.hide()
            self.show_minimize_message_once()
        else:
            self.exit_application()


    @exception_handler
    def selected_addon_name(self, text=None):
        new_addon = self.ui.ComboBoxSelectAddon.currentText()
        # If no addon selected, do nothing until user selects one
        if not new_addon:
            return
        if get_addon_name() == new_addon and getattr(self, 'SmartPropEditorMainWindow', None):
            return

        set_addon_name(new_addon)
        if getattr(self, 'SoundEventEditorMainWindow', None):
            self.SoundEventEditorMainWindow.close()
            self.SoundEventEditorMainWindow.deleteLater()
            self.SoundEventEditorMainWindow = None
        if getattr(self, 'SmartPropEditorMainWindow', None):
            layout = self.ui.smartpropeditor_tab.layout()
            layout.removeWidget(self.SmartPropEditorMainWindow)
            self.SmartPropEditorMainWindow.close()
            self.SmartPropEditorMainWindow.deleteLater()
            self.SmartPropEditorMainWindow = None
        if getattr(self, 'BatchCreator_MainWindow', None):
            self.BatchCreator_MainWindow.close()
            self.BatchCreator_MainWindow.deleteLater()
            self.BatchCreator_MainWindow = None
        if getattr(self, 'LoadingEditorMainWindow', None):
            self.LoadingEditorMainWindow.close()
            self.LoadingEditorMainWindow.deleteLater()
            self.LoadingEditorMainWindow = None


        # INITIALIZE NEW EDITOR INSTANCES
        self.BatchCreator_MainWindow = BatchCreatorMainWindow(update_title=self.update_title, parent=self)
        self.ui.BatchCreator_tab.layout().addWidget(self.BatchCreator_MainWindow)
        if cs2_path is not None:
            self.SoundEventEditorMainWindow = SoundEventEditorMainWindow(update_title=self.update_title, parent=self)
        else:
            print("SoundEventEditor: CS2 path not set, skipping initialization")
            self.SoundEventEditorMainWindow = None
        self.ui.soundeditor_tab.layout().addWidget(self.SoundEventEditorMainWindow)
        if cs2_path is not None:
            self.SmartPropEditorMainWindow = SmartPropEditorMainWindow(update_title=self.update_title, parent=self)
        else:
            self.SmartPropEditorMainWindow = None
        self.ui.smartpropeditor_tab.layout().addWidget(self.SmartPropEditorMainWindow)
        if cs2_path is not None:
            self.LoadingEditorMainWindow = Loading_editorMainWindow(parent=self)
        else:
            print("LoadingEditor: CS2 path not set, skipping initialization")
            self.LoadingEditorMainWindow = None
        self.ui.Loading_Editor_Tab.layout().addWidget(self.LoadingEditorMainWindow)

    @exception_handler
    def open_addons_folder(self):
        if cs2_path is None:
            QMessageBox.warning(self, "CS2 Path Not Set", 
                              "CS2 installation path is not set. Please set it in Settings > General > CS2 Path.")
            return
            
        addon_name = self.ui.ComboBoxSelectAddon.currentText()
        folder_name = self.ui.open_addons_folder_downlist.currentText()
        folder_path = r"\game\csgo_addons" if folder_name == "Game" else r"\content\csgo_addons"
        full_path = f"{cs2_path}{folder_path}\\{addon_name}"
        
        if os.path.exists(full_path):
            os.startfile(full_path)
        else:
            QMessageBox.warning(self, "Folder Not Found", 
                              f"The addon folder does not exist:\n{full_path}")

    @exception_handler
    def open_selected_dialog(self):
        selection = self.ui.dialog_selection_combobox.currentText()
        if selection == "Cleanup":
            CleanupDialog(self).show()
        elif selection == "Material Importer":
            self.material_importer_dialog = UE2SourceMaterialsWidget(parent=self)
            self.material_importer_dialog.show()

    @exception_handler
    def open_mapbuilder_dialog(self):
        if self.mapbuilder_dialog is None:
            self.mapbuilder_dialog = MapBuilderDialog(self)

        self.mapbuilder_dialog.show()
        self.mapbuilder_dialog.raise_()
        self.mapbuilder_dialog.activateWindow()

    def mapbuilder_dialog_closed(self):
        self.mapbuilder_dialog = None
        
    @exception_handler
    def open_preferences_dialog(self):
        if self.preferences_dialog is None:
            self.preferences_dialog = PreferencesDialog(app_version, self)
            self.preferences_dialog.show()
            self.preferences_dialog.finished.connect(self.preferences_dialog_closed)

    @exception_handler
    def open_launch_options(self):
        if self.launch_options is None:
            self.launch_options = LaunchOptionsDialog()
            self.launch_options.show()
            self.launch_options.finished.connect(self.closed_launch_options)

    def closed_launch_options(self):
        self.launch_options = None
        self.updateLaunchAddonButton()

    def preferences_dialog_closed(self):
        self.preferences_dialog = None

    def open_create_addon_dialog(self):
        if self.Create_addon_Dialog is None:
            self.Create_addon_Dialog = Create_addon_Dialog(self)
            self.Create_addon_Dialog.show()
            self.Create_addon_Dialog.finished.connect(self.create_addon_dialog_closed)

    def create_addon_dialog_closed(self):
        self.Create_addon_Dialog = None
        self.refresh_addon_combobox()

    def delete_addon(self):
        delete_addon(self.ui, cs2_path, get_addon_name)

    def open_export_and_import_addon(self):
        dialog = ExportAndImportAddonDialog(self)
        dialog.finished.connect(self.refresh_addon_combobox)
        dialog.show()

    def SteamNoLogonFix(self):
        self.thread = SteamNoLogoFixThreadClass()
        self.thread.start()
        self.thread.stop()

    def open_my_twitter(self):
        webbrowser.open("https://twitter.com/der_twist")

    def open_bluesky(self):
        webbrowser.open("https://bsky.app/profile/der-twist.bsky.social")

    def open_discord(self):
        webbrowser.open("https://discord.gg/DvCXEyhssd")

    def open_about(self):
        AboutDialog(app_version, self).show()

    def show_minimize_message_once(self):
        if get_settings_bool('APP', 'minimize_message_shown'):
            self.tray_icon.showMessage(
                "Hammer5Tools",
                "Application minimized to tray.",
                QSystemTrayIcon.Information,
                2000
            )
            set_settings_bool('APP', 'minimize_message_shown', False)
    
    def exit_application(self):
        self.tray_icon.hide()
        self.tray_icon.deleteLater()
        self._save_user_prefs()
        try:
            self.SmartPropEditorMainWindow.closeEvent(self.event)
        except Exception:
            pass
        try:
            self.SoundEventEditorMainWindow.closeEvent(self.event)
        except Exception:
            pass
        self.current_tab(True)
        QApplication.quit()
        sys.exit(0)

    def _restore_user_prefs(self):
        geo = self.settings.value("MainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)
        state = self.settings.value("MainWindow/windowState")
        if state:
            self.restoreState(state)

    def _save_user_prefs(self):
        self.settings.setValue("MainWindow/geometry", self.saveGeometry())
        self.settings.setValue("MainWindow/windowState", self.saveState())


def start_instance_server(widget):
    """
    Start the QLocalServer to accept connections from any subsequent instance.
    When a new connection is received, read the message and bring the window to front.
    """
    from src.ipc.server_utils import set_ipc_server
    server = QLocalServer()
    set_ipc_server(server)
    if server.listen(INSTANCE_KEY):
        server.newConnection.connect(lambda: handle_new_connection(server, widget))
    return server

def handle_new_connection(server, widget):
    """
    Handle incoming IPC messages from new instances.
    Supports both legacy 'show' message and new JSON-based protocol.
    """
    client_connection = server.nextPendingConnection()
    if client_connection:
        client_connection.waitForReadyRead(1000)
        msg_bytes = bytes(client_connection.readAll())
        
        message = IPCMessage.parse(msg_bytes)
        if message:
            command = message.get("command")
            
            if command == IPCCommand.SHOW_WINDOW.value:
                widget.show_from_tray()
            
            elif command == IPCCommand.OPEN_FILE.value:
                file_path = message.get("file_path")
                editor_type = message.get("editor_type", "smartprop")
                
                # Show window first
                widget.show_from_tray()
                
                # Route to appropriate editor
                if editor_type == "smartprop":
                    widget.open_file_in_smartprop(file_path)
                # Add other editor types as needed
            
            elif command == IPCCommand.CREATE_VMDL.value:
                folder_path = message.get("file_path")
                widget.show_from_tray()
                widget.open_quick_create_dialog(folder_path, "vmdl")
            
            elif command == IPCCommand.CREATE_VMAT.value:
                folder_path = message.get("file_path")
                widget.show_from_tray()
                widget.open_quick_create_dialog(folder_path, "vmat")

            elif command == IPCCommand.QUICK_VMDL.value:
                file_path = message.get("file_path")
                addon_hint = message.get("addon_hint")
                widget.show_from_tray()
                if widget.check_addon_mismatch(addon_hint):
                    widget.handle_quick_vmdl(file_path)

            elif command == IPCCommand.QUICK_BATCH.value:
                file_path = message.get("file_path")
                addon_hint = message.get("addon_hint")
                widget.show_from_tray()
                if widget.check_addon_mismatch(addon_hint):
                    widget.handle_quick_batch(file_path)

            elif command == IPCCommand.QUICK_PROCESS.value:
                file_path = message.get("file_path")
                addon_hint = message.get("addon_hint")
                widget.show_from_tray()
                if widget.check_addon_mismatch(addon_hint):
                    widget.handle_quick_process(file_path)
            
            elif command == IPCCommand.QUICK_PROCESS_FILE.value:
                file_path = message.get("file_path")
                addon_hint = message.get("addon_hint")
                widget.show_from_tray()
                if widget.check_addon_mismatch(addon_hint):
                    widget.handle_quick_process_file(file_path)
        
        client_connection.disconnectFromServer()

def _handle_velopack_hook(argv):
    """
    Back up / restore the ``userdata`` folder around Velopack (un)install hooks.

    Background
    ----------
    Velopack installs the app to ``%LocalAppData%\\Hammer5Tools\\`` with the
    following layout::

         <install_root>/
             current/Hammer5Tools.exe
             packages/...
             Update.exe
             userdata/                 <-- our persistent user data

    When the user runs ``Setup.exe`` on top of an existing install, Velopack
    invokes ``Update.exe --uninstall`` first, which calls our exe with
    ``--velopack-uninstall`` and then **deletes the entire install root** --
    including ``userdata/``.  After the new version is laid down, our exe is
    called again with ``--velopack-install`` / ``--velopack-updated``.

    To keep ``userdata`` persistent across Setup runs we:
      * on any *uninstall* / *obsolete* hook: copy ``<install_root>/userdata``
        to a location **outside** the Velopack-managed tree
        (``%LocalAppData%\\Hammer5Tools.Backup\\userdata``).
      * on any *install* / *updated* hook: if the backup exists, restore it
        and then remove the backup.

    The hook must be fast and must not require any GUI / Qt imports, so this
    runs before the rest of ``main`` is touched.
    """
    import shutil
    from pathlib import Path

    uninstall_hooks = {
        '--velopack-uninstall', '--velopack-obsolete', '--velopack-obsoleted',
        '--squirrel-uninstall', '--squirrel-obsolete', '--squirrel-obsoleted',
    }
    install_hooks = {
        '--velopack-install', '--velopack-updated',
        '--squirrel-install', '--squirrel-updated',
    }

    active = set(argv) & (uninstall_hooks | install_hooks)
    if not active:
        return

    try:
        # sys.executable points at <install_root>/current/Hammer5Tools.exe
        exe_path = Path(sys.executable).resolve()
        current_dir = exe_path.parent                      # <install_root>/current
        install_root = current_dir.parent                  # <install_root>
        userdata_path = install_root / "userdata"

        # Backup location: a sibling of the install root that Velopack never
        # manages, so it survives uninstall/reinstall cycles.
        local_appdata = Path(
            os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local')
        )
        backup_root = local_appdata / "Hammer5Tools.Backup"
        backup_userdata = backup_root / "userdata"
        backup_sentinel = backup_root / "USERDATA_BACKUP_VALID"

        def _log(msg):
            # Hooks run without a console; try to leave a breadcrumb in the
            # backup root in case we need to debug a failed migration.
            try:
                backup_root.mkdir(parents=True, exist_ok=True)
                with open(backup_root / "hook.log", "a", encoding="utf-8") as fh:
                    timestamp = time.strftime('%Y-%m-%dT%H:%M:%S')
                    fh.write(f"{timestamp} {' '.join(argv[1:])} :: {msg}\n")
            except Exception:
                pass

        if active & uninstall_hooks:
            _log(f"Starting backup from {userdata_path}")
            if userdata_path.is_dir():
                try:
                    # Remove old backup if it exists
                    if backup_userdata.exists():
                        shutil.rmtree(backup_userdata, ignore_errors=True)
                    
                    # Create backup directory
                    backup_root.mkdir(parents=True, exist_ok=True)
                    
                    # Perform the backup
                    shutil.copytree(userdata_path, backup_userdata)
                    _log(f"BACKUP SUCCESS: copied {userdata_path} ({_get_dir_size(userdata_path)} bytes) -> {backup_userdata}")
                    
                    # Verify backup completed successfully
                    if backup_userdata.exists() and any(backup_userdata.iterdir()):
                        # Write sentinel file to mark successful backup
                        backup_sentinel.write_text("valid", encoding="utf-8")
                        _log("BACKUP VERIFIED: sentinel file written")
                    else:
                        _log("BACKUP VERIFICATION FAILED: backup directory is empty or missing")
                except Exception as e:
                    _log(f"BACKUP FAILED: {type(e).__name__}: {e}")
            else:
                _log(f"NO USERDATA FOUND at {userdata_path}, nothing to back up")

        if active & install_hooks:
            _log(f"Starting restore to {userdata_path}")
            if backup_userdata.is_dir() and backup_sentinel.exists():
                try:
                    # Check if backup is valid
                    if not any(backup_userdata.iterdir()):
                        _log("RESTORE SKIPPED: backup directory is empty")
                        return
                    
                    # Remove current userdata if it exists (always restore from backup)
                    if userdata_path.exists():
                        _log(f"Removing existing userdata at {userdata_path}")
                        shutil.rmtree(userdata_path, ignore_errors=True)
                    
                    # Ensure parent directory exists
                    userdata_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Perform the restore
                    shutil.copytree(backup_userdata, userdata_path)
                    backup_size = _get_dir_size(backup_userdata)
                    _log(f"RESTORE SUCCESS: copied {backup_userdata} ({backup_size} bytes) -> {userdata_path}")
                    
                    # Verify restore completed
                    if userdata_path.exists() and any(userdata_path.iterdir()):
                        _log("RESTORE VERIFIED: userdata directory populated successfully")
                        
                        # Clean up backup after successful restore
                        try:
                            shutil.rmtree(backup_userdata, ignore_errors=True)
                            backup_sentinel.unlink(missing_ok=True)
                            try:
                                backup_root.rmdir()  # only succeeds if empty
                            except OSError:
                                pass
                            _log("Backup cleanup completed")
                        except Exception as e:
                            _log(f"Warning: failed to clean up backup: {e}")
                    else:
                        _log("RESTORE VERIFICATION FAILED: userdata still missing or empty after restore")
                except Exception as e:
                    _log(f"RESTORE FAILED: {type(e).__name__}: {e}")
            elif backup_userdata.is_dir():
                _log("RESTORE SKIPPED: backup exists but sentinel file missing (possible incomplete backup)")
            else:
                _log(f"NO BACKUP FOUND at {backup_userdata}, nothing to restore")
    except Exception as e:
        # Never let a hook error break the installer.
        try:
            print(f"[Hammer5Tools hook] CRITICAL ERROR: {e}", file=sys.stderr)
        except Exception:
            pass


if __name__ == "__main__":
    def _handle_velopack_hook(argv):
        import shutil
        from pathlib import Path
        
        # Internal helper for directory size logging
        def _get_dir_size(path):
            from pathlib import Path
            try:
                return sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())
            except Exception:
                return 0

        uninstall_hooks = {
            '--velopack-uninstall', '--velopack-obsolete', '--velopack-obsoleted',
            '--squirrel-uninstall', '--squirrel-obsolete', '--squirrel-obsoleted',
        }
        install_hooks = {
            '--velopack-install', '--velopack-updated',
            '--squirrel-install', '--squirrel-updated',
        }

        active = set(argv) & (uninstall_hooks | install_hooks)
        if not active:
            return

        try:
            exe_path = Path(sys.executable).resolve()
            current_dir = exe_path.parent
            install_root = current_dir.parent
            userdata_path = install_root / "userdata"

            local_appdata = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
            backup_root = local_appdata / "Hammer5Tools.Backup"
            backup_userdata = backup_root / "userdata"
            backup_sentinel = backup_root / "USERDATA_BACKUP_VALID"

            def _log(msg):
                try:
                    backup_root.mkdir(parents=True, exist_ok=True)
                    with open(backup_root / "hook.log", "a", encoding="utf-8") as fh:
                        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S')
                        fh.write(f"{timestamp} {' '.join(argv[1:])} :: {msg}\n")
                except Exception:
                    pass

            if active & uninstall_hooks:
                _log(f"Starting backup from {userdata_path}")
                if userdata_path.is_dir():
                    try:
                        if backup_userdata.exists():
                            shutil.rmtree(backup_userdata, ignore_errors=True)
                        backup_root.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(userdata_path, backup_userdata)
                        if backup_userdata.exists() and any(backup_userdata.iterdir()):
                            backup_sentinel.write_text("valid", encoding="utf-8")
                    except Exception as e:
                        _log(f"BACKUP FAILED: {e}")

            if active & install_hooks:
                if backup_userdata.is_dir() and backup_sentinel.exists():
                    try:
                        if userdata_path.exists():
                            shutil.rmtree(userdata_path, ignore_errors=True)
                        userdata_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(backup_userdata, userdata_path)
                        if userdata_path.exists() and any(userdata_path.iterdir()):
                            shutil.rmtree(backup_userdata, ignore_errors=True)
                            backup_sentinel.unlink(missing_ok=True)
                    except Exception as e:
                        _log(f"RESTORE FAILED: {e}")
        except Exception:
            pass
        sys.exit(0)

    # Check hooks BEFORE anything else in main
    _handle_velopack_hook(sys.argv)

    parser = argparse.ArgumentParser(description="Hammer 5 Tools Application")
    parser.add_argument('--dev', action='store_true', help='Enable development mode')
    parser.add_argument('--console', action='store_true', help='Enable console output for debug purposes')
    parser.add_argument('--create-vmdl', help='Create VMDL in folder')
    parser.add_argument('--quick-vmdl', help='Quick create VMDL from mesh')
    parser.add_argument('--quick-vmdl-dir', help='Quick create VMDL in folder')
    parser.add_argument('--quick-batch', help='Quick create batch in folder')
    parser.add_argument('--quick-process', help='Quick process folder')
    parser.add_argument('--quick-process-file', help='Quick process specific file')
    parser.add_argument('file', nargs='?', help='File to open (.vsmart, .vdata, etc.)')
    args, unknown = parser.parse_known_args()

    # Allocate a console window if requested (works when built with --windowed)
    if args.console:
        allocate_console()

    # Instance management via QLocalSocket/QLocalServer.
    existing_socket = QLocalSocket()
    existing_socket.connectToServer(INSTANCE_KEY)
    if existing_socket.waitForConnected(500):
        # Another instance is already running
        if args.create_vmdl:
            message = IPCMessage.create_quick_action(IPCCommand.CREATE_VMDL, os.path.abspath(args.create_vmdl))
            existing_socket.write(message.encode('utf-8'))
        elif args.quick_vmdl or args.quick_vmdl_dir:
            path = args.quick_vmdl or args.quick_vmdl_dir
            message = IPCMessage.create_quick_action(IPCCommand.QUICK_VMDL, os.path.abspath(path))
            existing_socket.write(message.encode('utf-8'))
        elif args.quick_batch:
            message = IPCMessage.create_quick_action(IPCCommand.QUICK_BATCH, os.path.abspath(args.quick_batch))
            existing_socket.write(message.encode('utf-8'))
        elif args.quick_process:
            message = IPCMessage.create_quick_action(IPCCommand.QUICK_PROCESS, os.path.abspath(args.quick_process))
            existing_socket.write(message.encode('utf-8'))
        elif args.quick_process_file:
            message = IPCMessage.create_quick_action(IPCCommand.QUICK_PROCESS_FILE, os.path.abspath(args.quick_process_file))
            existing_socket.write(message.encode('utf-8'))
        elif args.file:
            # Send file open command
            file_path = os.path.abspath(args.file)
            message = IPCMessage.create_open_file(file_path)
            existing_socket.write(message.encode('utf-8'))
        else:
            # Just show the window
            message = IPCMessage.create_show()
            existing_socket.write(message.encode('utf-8'))
        
        existing_socket.flush()
        existing_socket.waitForBytesWritten(1000)
        sys.exit(0)

    # No instance running, so create the server.
    app = QApplication(sys.argv)
    #Checking .NET runtime
    app.setStyleSheet(QT_Stylesheet_global)
    check_dotnet_runtime()
    widget = Widget(dev_mode=args.dev)
    widget.show()
    instance_server = start_instance_server(widget)

    # Handle initial arguments for first instance
    def handle_initial_args():
        if args.create_vmdl:
            widget.open_quick_create_dialog(os.path.abspath(args.create_vmdl), "vmdl")
        elif args.quick_vmdl or args.quick_vmdl_dir:
            path = args.quick_vmdl or args.quick_vmdl_dir
            widget.handle_quick_vmdl(os.path.abspath(path))
        elif args.quick_batch:
            widget.handle_quick_batch(os.path.abspath(args.quick_batch))
        elif args.quick_process:
            widget.handle_quick_process(os.path.abspath(args.quick_process))
        elif args.quick_process_file:
            widget.handle_quick_process_file(os.path.abspath(args.quick_process_file))
        elif args.file:
            file_path = os.path.abspath(args.file)
            extension = os.path.splitext(file_path)[1].lower()
            if extension in ('.vsmart', '.vdata'):
                widget.open_file_in_smartprop(file_path)

    # Small delay to ensure widget is fully initialized
    QTimer.singleShot(200, handle_initial_args)

    sys.exit(app.exec())