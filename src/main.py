import sys
import os
import ctypes
import threading
import webbrowser
import time
import argparse

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
    QTabWidget
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

from about.main import AboutDialog
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
    debug
)
from loading_editor.main import Loading_editorMainWindow
from hotkey_editor.main import HotkeyEditorMainWindow
from create_addon.create_addon_mian import Create_addon_Dialog
from other.steam_restart import SteamNoLogoFixThreadClass
from other.addon_functions import delete_addon, launch_addon
from src.updater.check import check_updates
from archive_addon.main import ExportAndImportAddonDialog
from assetgroup_maker.main import BatchCreatorMainWindow
from smartprop_editor.main import SmartPropEditorMainWindow
from soundevent_editor.main import SoundEventEditorMainWindow
from src.launch_options.main import LaunchOptionsDialog
from styles.qt_global_stylesheet import QT_Stylesheet_global
from src.common import enable_dark_title_bar, app_version, default_commands, app_dir
import qdarktheme
# Global paths
steam_path = get_steam_path()
cs2_path = get_cs2_path()
stop_discord_thread = threading.Event()
INSTANCE_KEY = "Hammer5ToolsInstance"

from src.common import Decompiler_path
print(f"Decompiler path: {Decompiler_path}")

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
        self.setLayout(layout)

class Widget(QMainWindow):
    def __init__(self, parent=None, dev_mode=False):
        super().__init__(parent)
        from ui_main import Ui_MainWindow  # Ensure proper dependency resolution
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)


        #Checking for Counter Strike 2 installation

        if cs2_path == app_dir:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Counter Strike 2 Not Installed")
            msg_box.setText("Counter Strike 2 is not installed on your system.")
            exit_button = msg_box.addButton("Exit", QMessageBox.RejectRole)
            continue_button = msg_box.addButton("Continue Anyway", QMessageBox.AcceptRole)
            msg_box.setDefaultButton(exit_button)
            msg_box.exec()
            if msg_box.clickedButton() == exit_button:
                sys.exit(1)

        # Setup tray icon early so that restoration has a fallback.
        self.setup_tray_icon()
        self.setup_tabs()
        self.populate_addon_combobox()
        self.setup_buttons()
        self.preferences_dialog = None
        self.launch_options = None
        self.Create_addon_Dialog = None
        self.Delete_addon_Dialog = None
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

        # Setup filesystem watcher for addon folder.
        self.addon_watcher = QFileSystemWatcher(self)
        self.addon_watcher.addPath(os.path.join(cs2_path, "content", "csgo_addons"))
        self.addon_watcher.directoryChanged.connect(self.refresh_addon_combobox)

        for dock in self.findChildren(QDockWidget):
            dock.show()
        for child in self.findChildren(QMainWindow):
            for dock in child.findChildren(QDockWidget):
                dock.show()

    def deferred_update_check(self):
        try:
            check_updates("https://github.com/dertwist/Hammer5Tools", app_version, True)
        except Exception as e:
            print(f"Error checking updates: {e}")

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


    def setup_tabs(self):
        self.HotkeyEditorMainWindow_instance = HotkeyEditorMainWindow()
        self.ui.hotkeyeditor_tab.layout().addWidget(self.HotkeyEditorMainWindow_instance)

    def populate_addon_combobox(self):
        exclude_addons = {"workshop_items", "addon_template"}
        addons_folder = os.path.join(cs2_path, "content", "csgo_addons")
        found_any = False
        try:
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
                    self.open_create_addon_dialog()
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
        self.updateLaunchAddonButton()

    def updateLaunchAddonButton(self):
        commands = get_settings_value("LAUNCH", "commands", default_commands)
        if commands and "-asset" in commands:
            self.ui.Launch_Addon_Button.setText("Edit map")
        else:
            self.ui.Launch_Addon_Button.setText("Launch Tools")

    def closeEvent(self, event):
        if settings.value("APP/minimize_to_tray", type=bool, defaultValue=True):
            event.ignore()
            self.hide()

            for dock in self.findChildren(QDockWidget):
                dock.hide()
            for child in self.findChildren(QMainWindow):
                for dock in child.findChildren(QDockWidget):
                    dock.hide()
            settings.setValue("APP/minimize_to_tray", True)
            self.show_minimize_message_once()
        else:
            self.exit_application()

    def selected_addon_name(self):
        new_addon = self.ui.ComboBoxSelectAddon.currentText()
        if get_addon_name() == new_addon and getattr(self, 'SmartPropEditorMainWindow', None):
            return

        set_addon_name(new_addon)
        try:
            if getattr(self, 'SoundEventEditorMainWindow', None):
                self.SoundEventEditorMainWindow.close()
                self.SoundEventEditorMainWindow.deleteLater()
                self.SoundEventEditorMainWindow = None
        except Exception as e:
            print(f"Error while cleaning up SoundEventEditorMainWindow: {e}")
        try:
            if getattr(self, 'SmartPropEditorMainWindow', None):
                layout = self.ui.smartpropeditor_tab.layout()
                layout.removeWidget(self.SmartPropEditorMainWindow)
                self.SmartPropEditorMainWindow.close()   # call close(), not closeEvent(self.event)
                self.SmartPropEditorMainWindow.deleteLater()
                self.SmartPropEditorMainWindow = None
        except Exception as e:
            print(f"Error while cleaning up SmartPropEditorMainWindow: {e}")
        try:
            if getattr(self, 'BatchCreator_MainWindow', None):
                self.BatchCreator_MainWindow.close()
                self.BatchCreator_MainWindow.deleteLater()
                self.BatchCreator_MainWindow = None
        except Exception as e:
            print('Error while cleaning up BatchCreator_MainWindow:', e)
        try:
            if getattr(self, 'LoadingEditorMainWindow', None):
                self.LoadingEditorMainWindow.close()
                self.LoadingEditorMainWindow.deleteLater()
                self.LoadingEditorMainWindow = None
        except Exception as e:
            print('Error while cleaning up LoadingEditorMainWindow:', e)

        # INITIALIZE NEW EDITOR INSTANCES
        try:
            self.BatchCreator_MainWindow = BatchCreatorMainWindow(update_title=self.update_title)
            self.ui.BatchCreator_tab.layout().addWidget(self.BatchCreator_MainWindow)
        except Exception as e:
            print('Error while setting up BatchCreator_MainWindow:', e)
        try:
            self.SoundEventEditorMainWindow = SoundEventEditorMainWindow(update_title=self.update_title)
            self.ui.soundeditor_tab.layout().addWidget(self.SoundEventEditorMainWindow)
        except Exception as e:
            print(f"Error while setting up SoundEventEditorMainWindow: {e}")
        try:
            self.SmartPropEditorMainWindow = SmartPropEditorMainWindow(update_title=self.update_title, parent=self)
            self.ui.smartpropeditor_tab.layout().addWidget(self.SmartPropEditorMainWindow)
        except Exception as e:
            print(f"Error while setting up SmartPropEditorMainWindow: {e}")
        try:
            self.LoadingEditorMainWindow = Loading_editorMainWindow()
            self.ui.Loading_Editor_Tab.layout().addWidget(self.LoadingEditorMainWindow)
        except Exception as e:
            print(f"Error while setting up LoadingEditorMainWindow: {e}")

    def open_addons_folder(self):
        addon_name = self.ui.ComboBoxSelectAddon.currentText()
        folder_name = self.ui.open_addons_folder_downlist.currentText()
        folder_path = r"\game\csgo_addons" if folder_name == "Game" else r"\content\csgo_addons"
        os.startfile(f"{cs2_path}{folder_path}\\{addon_name}")

    def open_preferences_dialog(self):
        if self.preferences_dialog is None:
            self.preferences_dialog = PreferencesDialog(app_version, self)
            self.preferences_dialog.show()
            self.preferences_dialog.finished.connect(self.preferences_dialog_closed)

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
        try:
            from other.discord_status import discord_status_clear
            discord_status_clear()
        except Exception:
            pass
        stop_discord_thread.set()
        if hasattr(self, 'discord_thread') and self.discord_thread.is_alive():
            self.discord_thread.join()
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

def DiscordStatusMain_do():
    from other.discord_status import update_discord_status
    while not stop_discord_thread.is_set():
        update_discord_status()
        time.sleep(1)

def start_instance_server(widget):
    """
    Start the QLocalServer to accept connections from any subsequent instance.
    When a new connection is received, read the message and bring the window to front.
    """
    server = QLocalServer()
    if server.listen(INSTANCE_KEY):
        server.newConnection.connect(lambda: handle_new_connection(server, widget))
    return server

def handle_new_connection(server, widget):
    client_connection = server.nextPendingConnection()
    if client_connection:
        client_connection.waitForReadyRead(1000)
        msg = bytes(client_connection.readAll()).decode().strip()
        # If the message is "show", restore the window.
        if msg == "show":
            widget.show_from_tray()
        client_connection.disconnectFromServer()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hammer 5 Tools Application")
    parser.add_argument('--dev', action='store_true', help='Enable development mode')
    parser.add_argument('--console', action='store_true', help='Enable console output for debug purposes')
    args, unknown = parser.parse_known_args()

    # Allocate a console window if requested (works when built with --windowed)
    if args.console:
        allocate_console()

    # Instance management via QLocalSocket/QLocalServer.
    existing_socket = QLocalSocket()
    existing_socket.connectToServer(INSTANCE_KEY)
    if existing_socket.waitForConnected(500):
        # Another instance is already running. Send a message to show the window.
        existing_socket.write(b"show")
        existing_socket.flush()
        existing_socket.waitForBytesWritten(500)
        sys.exit(0)

    # No instance running, so create the server.
    app = QApplication(sys.argv)
    app.setStyleSheet(QT_Stylesheet_global)
    widget = Widget(dev_mode=args.dev)
    widget.show()
    instance_server = start_instance_server(widget)

    if get_settings_bool('DISCORD_STATUS', 'show_status'):
        from other.discord_status import discord_status_clear, update_discord_status
        widget.discord_thread = threading.Thread(target=DiscordStatusMain_do)
        widget.discord_thread.start()
    else:
        debug('Discord status updates are disabled.')
    sys.exit(app.exec())