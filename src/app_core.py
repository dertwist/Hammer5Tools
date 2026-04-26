import os
import time
from PySide6.QtWidgets import (
    QSystemTrayIcon,
    QMenu,
    QDockWidget
)
from PySide6.QtGui import QAction
from PySide6.QtCore import (
    QPropertyAnimation,
    QPoint,
    QFileSystemWatcher,
)
from PySide6.QtNetwork import QLocalServer

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
from src.forms.ue2source_materials.main import UE2SourceMaterialsWidget
from src.forms.launch_options.main import LaunchOptionsDialog
from src.common import app_version, default_commands, JsonToKv3, compile as run_compile
from src.styles.qt_global_stylesheet import QT_Stylesheet_global
from src.dotnet import check_dotnet_runtime
from src.other.addon_validation import validate_addon_structure
from src.forms.cleanup.main import CleanupDialog
from src.forms.quick_create.main import QuickCreateDialog
from src.widgets import *

# Global paths
steam_path = get_steam_path()
cs2_path = get_cs2_path()
INSTANCE_KEY = "Hammer5ToolsIPC"

def activate_existing_window(hwnd):
    SW_RESTORE = 9
    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
    ctypes.windll.user32.UpdateWindow(hwnd)
    ctypes.windll.user32.SetForegroundWindow(hwnd)

def restore_window(hwnd):
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
                QTimer.singleShot(500, self.open_preferences_dialog)

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
        
        QTimer.singleShot(2000, self.check_file_associations)

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

    def trigger_update_check(self):
        check_updates("https://github.com/dertwist/Hammer5Tools", app_version, False)

    def deferred_update_check(self):
        try:
            check_updates("https://github.com/dertwist/Hammer5Tools", app_version, True)
        except Exception as e:
            print(f"Error checking updates: {e}")

    def check_file_associations(self):
        if not get_settings_bool('APP', 'check_associations', True):
            return
        _, is_us = check_association('.vsmart')
        if not is_us:
            dialog = FileAssociationPromptDialog(self)
            if dialog.exec() == QDialog.Accepted:
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
        if not self.SmartPropEditorMainWindow:
            print("SmartProp Editor not initialized")
            return
        smartprop_tab_index = self.ui.MainWindowTools_tabs.indexOf(self.ui.smartpropeditor_tab)
        if smartprop_tab_index >= 0:
            self.ui.MainWindowTools_tabs.setCurrentIndex(smartprop_tab_index)
        self.SmartPropEditorMainWindow.open_file(filename=file_path)

    def open_quick_create_dialog(self, folder_path, file_type):
        dialog = QuickCreateDialog(folder_path, file_type, self)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def check_addon_mismatch(self, addon_hint):
        if not addon_hint: return True
        current_addon = get_addon_name()
        if addon_hint.lower() == current_addon.lower(): return True
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
            return True
        elif msg_box.clickedButton() == keep_button: return True
        else: return False

    def handle_quick_vmdl(self, path):
        if os.path.isfile(path):
            folder = os.path.dirname(path)
            basename = os.path.splitext(os.path.basename(path))[0]
            vmdl_path = os.path.join(folder, f"{basename}.vmdl")
            addon_dir = get_addon_dir()
            try: rel_mesh = os.path.relpath(path, addon_dir).replace('\\', '/')
            except (ValueError, Exception): rel_mesh = ""
            from src.editors.assetgroup_maker.objects import DEFAULT_VMDL
            from src.common import fast_deepcopy
            vmdl_content = fast_deepcopy(DEFAULT_VMDL)
            for child in vmdl_content.get('rootNode', {}).get('children', []):
                if child.get('_class') == 'RenderMeshList':
                    for mesh_file in child.get('children', []):
                        if mesh_file.get('_class') == 'RenderMeshFile': mesh_file['filename'] = rel_mesh
                if child.get('_class') == 'PhysicsShapeList':
                    for phys_file in child.get('children', []):
                        if phys_file.get('_class') == 'PhysicsHullFile':
                            phys_file['filename'] = rel_mesh
                            phys_file['name'] = basename
            kv3_content = JsonToKv3(vmdl_content, format='vmdl')
            try:
                with open(vmdl_path, 'w') as f: f.write(kv3_content)
                self.update_title(text=f"Created VMDL: {os.path.basename(vmdl_path)}")
            except Exception as e: QMessageBox.critical(self, "Error", f"Failed to create VMDL: {e}")
        else: self.open_quick_create_dialog(path, "vmdl")

    def handle_quick_batch(self, path):
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
                with open(bat_path, 'w') as f: f.write(bat_content)
                self.update_title(text=f"Created Batch: {os.path.basename(bat_path)}")
            except Exception as e: QMessageBox.critical(self, "Error", f"Failed to create Batch file: {e}")

    def handle_quick_process(self, path):
        if os.path.isdir(path):
            self.update_title(text=f"Processing folder: {os.path.basename(path)}...")
            run_compile(os.path.join(path, "*.vmdl"))
            run_compile(os.path.join(path, "*.vmat"))

    def handle_quick_process_file(self, path):
        if os.path.isfile(path):
            self.update_title(text=f"Processing file: {os.path.basename(path)}...")
            run_compile(path)

    def setup_tabs(self):
        self.HotkeyEditorMainWindow_instance = HotkeyEditorMainWindow()
        self.ui.hotkeyeditor_tab.layout().addWidget(self.HotkeyEditorMainWindow_instance)
        
    def populate_addon_combobox(self):
        exclude_addons = {"workshop_items", "addon_template"}
        if cs2_path is None:
            self.ui.ComboBoxSelectAddon.addItem("CS2 Path Not Set")
            self.ui.ComboBoxSelectAddon.setCurrentIndex(0)
            return
        addons_folder = os.path.join(cs2_path, "content", "csgo_addons")
        found_any = False
        try:
            if not os.path.exists(addons_folder):
                self.ui.ComboBoxSelectAddon.addItem("Addons Folder Not Found")
                self.ui.ComboBoxSelectAddon.setCurrentIndex(0)
                return
            for item in os.listdir(addons_folder):
                full_path = os.path.join(addons_folder, item)
                if os.path.isdir(full_path) and item not in exclude_addons:
                    self.ui.ComboBoxSelectAddon.addItem(item)
                    found_any = True
            if not found_any:
                response = QMessageBox.question(self, "No Addon Found", "No addons found. Would you like to create one now?", QMessageBox.Yes | QMessageBox.No)
                if response == QMessageBox.Yes:
                    Create_addon_Dialog(self).exec()
                    self.refresh_addon_combobox()
                    return
                else:
                    self.ui.ComboBoxSelectAddon.addItem("")
                    self.ui.ComboBoxSelectAddon.setCurrentIndex(0)
            if not get_addon_name() and found_any: set_addon_name(self.ui.ComboBoxSelectAddon.currentText())
        except Exception as e: print("Failed to load addons:", e)

    def refresh_addon_combobox(self):
        try: self.ui.ComboBoxSelectAddon.currentTextChanged.disconnect(self.selected_addon_name)
        except Exception: pass
        addon = get_addon_name()
        self.ui.ComboBoxSelectAddon.clear()
        self.populate_addon_combobox()
        self.ui.ComboBoxSelectAddon.setCurrentText(addon)
        self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)
        tools = ["SoundEventEditorMainWindow", "SmartPropEditorMainWindow", "BatchCreator_MainWindow", "LoadingEditorMainWindow"]
        if not any(getattr(self, tool, None) for tool in tools): self.selected_addon_name()

    def animate_launch_button(self):
        button = self.ui.Launch_Addon_Button
        overlay = QWidget(button)
        overlay.setObjectName("launchOverlay")
        overlay.setAttribute(Qt.WA_StyledBackground, True)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay.setStyleSheet("QWidget#launchOverlay { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 rgba(65,73,86,0.25), stop: 0.2 rgba(65,73,86,0.40), stop: 0.8 rgba(65,73,86,0.40), stop: 1 rgba(65,73,86,0.25)); }")
        button_width, button_height = button.width(), button.height()
        overlay.setGeometry(-button_width, 0, button_width, button_height)
        overlay.show()
        overlay.lower()
        animation = QPropertyAnimation(overlay, b"pos", self)
        animation.setDuration(1200)
        animation.setStartValue(QPoint(-button_width, 0))
        animation.setEndValue(QPoint(button_width, 0))
        animation.finished.connect(overlay.deleteLater)
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
        if addon not in combo_items: self.refresh_addon_combobox()
        if self.ui.ComboBoxSelectAddon.currentText() == get_addon_name(): self.selected_addon_name()
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

    def updateLaunchAddonButton(self):
        commands = get_settings_value("LAUNCH", "commands", default_commands)
        self.ui.Launch_Addon_Button.setText("Edit map" if commands and "-asset" in commands else "Launch Tools")

    def closeEvent(self, event):
        if get_settings_bool("APP", "minimize_to_tray", False):
            event.ignore()
            self.hide()
            for dock in self.findChildren(QDockWidget): dock.hide()
            for child in self.findChildren(QMainWindow):
                for dock in child.findChildren(QDockWidget): dock.hide()
            self.show_minimize_message_once()
        else: self.exit_application()

    @exception_handler
    def selected_addon_name(self, text=None):
        new_addon = self.ui.ComboBoxSelectAddon.currentText()
        if not new_addon: return
        if get_addon_name() == new_addon and getattr(self, 'SmartPropEditorMainWindow', None): return
        set_addon_name(new_addon)
        if getattr(self, 'SoundEventEditorMainWindow', None):
            self.SoundEventEditorMainWindow.close(); self.SoundEventEditorMainWindow.deleteLater(); self.SoundEventEditorMainWindow = None
        if getattr(self, 'SmartPropEditorMainWindow', None):
            self.ui.smartpropeditor_tab.layout().removeWidget(self.SmartPropEditorMainWindow)
            self.SmartPropEditorMainWindow.close(); self.SmartPropEditorMainWindow.deleteLater(); self.SmartPropEditorMainWindow = None
        if getattr(self, 'BatchCreator_MainWindow', None):
            self.BatchCreator_MainWindow.close(); self.BatchCreator_MainWindow.deleteLater(); self.BatchCreator_MainWindow = None
        if getattr(self, 'LoadingEditorMainWindow', None):
            self.LoadingEditorMainWindow.close(); self.LoadingEditorMainWindow.deleteLater(); self.LoadingEditorMainWindow = None
        self.BatchCreator_MainWindow = BatchCreatorMainWindow(update_title=self.update_title, parent=self)
        self.ui.BatchCreator_tab.layout().addWidget(self.BatchCreator_MainWindow)
        if cs2_path is not None:
            self.SoundEventEditorMainWindow = SoundEventEditorMainWindow(update_title=self.update_title, parent=self)
            self.ui.soundeditor_tab.layout().addWidget(self.SoundEventEditorMainWindow)
            self.SmartPropEditorMainWindow = SmartPropEditorMainWindow(update_title=self.update_title, parent=self)
            self.ui.smartpropeditor_tab.layout().addWidget(self.SmartPropEditorMainWindow)
            self.LoadingEditorMainWindow = Loading_editorMainWindow(parent=self)
            self.ui.Loading_Editor_Tab.layout().addWidget(self.LoadingEditorMainWindow)

    @exception_handler
    def open_addons_folder(self):
        if cs2_path is None:
            QMessageBox.warning(self, "CS2 Path Not Set", "CS2 installation path is not set. Please set it in Settings > General > CS2 Path."); return
        addon_name = self.ui.ComboBoxSelectAddon.currentText()
        folder_path = r"\game\csgo_addons" if self.ui.open_addons_folder_downlist.currentText() == "Game" else r"\content\csgo_addons"
        full_path = f"{cs2_path}{folder_path}\\{addon_name}"
        if os.path.exists(full_path): os.startfile(full_path)
        else: QMessageBox.warning(self, "Folder Not Found", f"The addon folder does not exist:\n{full_path}")

    @exception_handler
    def open_selected_dialog(self):
        selection = self.ui.dialog_selection_combobox.currentText()
        if selection == "Cleanup": CleanupDialog(self).show()
        elif selection == "Material Importer": self.material_importer_dialog = UE2SourceMaterialsWidget(parent=self); self.material_importer_dialog.show()

    @exception_handler
    def open_mapbuilder_dialog(self):
        if self.mapbuilder_dialog is None: self.mapbuilder_dialog = MapBuilderDialog(self)
        self.mapbuilder_dialog.show(); self.mapbuilder_dialog.raise_(); self.mapbuilder_dialog.activateWindow()

    @exception_handler
    def open_preferences_dialog(self):
        if self.preferences_dialog is None:
            self.preferences_dialog = PreferencesDialog(app_version, self); self.preferences_dialog.show()
            self.preferences_dialog.finished.connect(lambda: setattr(self, 'preferences_dialog', None))

    @exception_handler
    def open_launch_options(self):
        if self.launch_options is None:
            self.launch_options = LaunchOptionsDialog(); self.launch_options.show()
            self.launch_options.finished.connect(lambda: setattr(self, 'launch_options', None))

    def exit_application(self):
        self.current_tab(True)
        if self.tray_icon: self.tray_icon.hide()
        QApplication.quit()

    def SteamNoLogonFix(self):
        self.steam_fix_thread = SteamNoLogoFixThreadClass()
        self.steam_fix_thread.start()
        self.update_title(text="Applying Steam No-Logon Fix...")

    def open_about(self):
        AboutDialog(app_version, self).exec()

    def open_create_addon_dialog(self):
        dialog = Create_addon_Dialog(self)
        if dialog.exec() == QDialog.Accepted: self.refresh_addon_combobox()

    def delete_addon(self):
        addon = get_addon_name()
        if not addon: return
        msg = QMessageBox.question(self, "Delete Addon", f"Are you sure you want to delete addon '{addon}'?\nThis will delete BOTH content and game folders!", QMessageBox.Yes | QMessageBox.No)
        if msg == QMessageBox.Yes:
            delete_addon(addon)
            self.refresh_addon_combobox()

    def open_export_and_import_addon(self):
        ExportAndImportAddonDialog(self).exec()

    def open_my_twitter(self): webbrowser.open("https://twitter.com/dertwist")
    def open_discord(self): webbrowser.open("https://discord.gg/6X88yX8Y")
    def _restore_user_prefs(self): pass
    def show_minimize_message_once(self): pass

def handle_new_connection(server, widget):
    socket = server.nextPendingConnection()
    if socket.waitForReadyRead(1000):
        data = socket.readAll().data()
        message = IPCMessage.parse(data)
        if message:
            command = message.get("command")
            if command == IPCCommand.SHOW_WINDOW.value:
                widget.show_from_tray()
            elif command == IPCCommand.OPEN_FILE.value:
                file_path = message.get("file_path")
                if file_path:
                    widget.show_from_tray()
                    widget.open_file_in_smartprop(file_path)
            elif command == IPCCommand.CREATE_VMDL.value:
                widget.show_from_tray()
                widget.open_quick_create_dialog(message.get("file_path"), "vmdl")
            elif command == IPCCommand.QUICK_VMDL.value:
                widget.show_from_tray()
                widget.handle_quick_vmdl(message.get("file_path"))
            elif command == IPCCommand.QUICK_BATCH.value:
                widget.show_from_tray()
                widget.handle_quick_batch(message.get("file_path"))
            elif command == IPCCommand.QUICK_PROCESS.value:
                widget.show_from_tray()
                widget.handle_quick_process(message.get("file_path"))
            elif command == IPCCommand.QUICK_PROCESS_FILE.value:
                widget.show_from_tray()
                widget.handle_quick_process_file(message.get("file_path"))
    socket.disconnectFromServer()

def start_instance_server(widget):
    from src.ipc.server_utils import set_ipc_server
    server = QLocalServer()
    set_ipc_server(server)
    if server.listen(INSTANCE_KEY):
        server.newConnection.connect(lambda: handle_new_connection(server, widget))
    return server
