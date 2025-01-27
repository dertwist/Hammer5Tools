import ctypes
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtGui import QAction
from about.main import AboutDialog
from src.settings.main import PreferencesDialog, get_steam_path, get_cs2_path, get_addon_name, set_addon_name, get_config_bool, set_config_bool, get_config_value, set_config_value, settings, debug
from loading_editor.main import Loading_editorMainWindow
from hotkey_editor.main import HotkeyEditorMainWindow
from create_addon.create_addon_mian import Create_addon_Dialog
from other.steamfixnologon import SteamNoLogoFixThreadClass
from other.addon_functions import delete_addon, launch_addon
from other.update_check import check_updates
from archive_addon.main import ExportAndImportAddonDialog
from assetgroup_maker.main import BatchCreatorMainWindow
from smartprop_editor.main import SmartPropEditorMainWindow
from soundevent_editor.main import SoundEventEditorMainWindow
from src.launch_options.main import LaunchOptionsDialog
from PySide6.QtWidgets import QLabel, QCheckBox
import sys
import os
import threading
import portalocker
import tempfile
import webbrowser
import time
import argparse
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from ui_main import Ui_MainWindow
from styles.qt_global_stylesheet import QT_Stylesheet_global
from PySide6.QtCore import QTimer
from PySide6.QtCore import QFileSystemWatcher
from src.common import enable_dark_title_bar

# Variables
steam_path = get_steam_path()
cs2_path = get_cs2_path()
stop_discord_thread = threading.Event()
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'hammer5tools.lock')

# Versions
app_version = '4.0.0'


class DevWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Development Widget")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        # Label indicating development mode
        label = QLabel("Development Mode Active", self)
        layout.addWidget(label)

        # Checkbox for toggling debug info
        self.checkBox_debug_info = QCheckBox("Enable Debug Info", self)
        self.checkBox_debug_info.setChecked(get_config_bool('OTHER', 'debug_info', False))
        self.checkBox_debug_info.toggled.connect(lambda: set_config_bool('OTHER', 'debug_info', self.checkBox_debug_info.isChecked()))
        layout.addWidget(self.checkBox_debug_info)

        self.setLayout(layout)
class Notification(QMessageBox):
    def __init__(self, parent=None):
        super(Notification, self).__init__(parent)
        self.setWindowTitle("Hammer 5 Tools")
        self.setTextFormat(Qt.RichText)

        # Set the message box icon to a warning icon
        self.setIcon(QMessageBox.Warning)

        self.setText("Another instance of the program is running")
        self.setStandardButtons(QMessageBox.Ok)
        self.buttonClicked.connect(self.bring_to_front)
        self.hwnd = ctypes.windll.user32.FindWindowW(None, "Hammer 5 Tools")

    def bring_to_front(self):

        if self.hwnd:
            ctypes.windll.user32.SetForegroundWindow(self.hwnd)

class Widget(QMainWindow):
    def __init__(self, parent=None, dev_mode=False):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        enable_dark_title_bar(self)
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

        if dev_mode:
            self.dev_widget = DevWidget(self)
            self.ui.centralwidget.layout().addWidget(self.dev_widget)

        try:
            check_updates("https://github.com/dertwist/Hammer5Tools", app_version, True)
        except Exception as e:
            print(f"Error checking updates: {e}")

        self._restore_user_prefs()
        if get_config_bool('APP', 'first_launch'):
            self.open_about()
            set_config_bool('APP', 'first_launch', False)

        self.addon_watcher = QFileSystemWatcher(self)
        self.addon_watcher.addPath(os.path.join(cs2_path, "content", "csgo_addons"))
        self.addon_watcher.directoryChanged.connect(self.refresh_addon_combobox)

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
        self.setWindowTitle("Hammer 5 Tools")


    def current_tab(self, set):
        if set:
            try:
                set_config_value('APP', 'current_tab', str(self.ui.MainWindowTools_tabs.currentIndex()))
            except:
                pass
        else:
            try:
                current_tab = int(get_config_value('APP', 'current_tab'))
                self.ui.MainWindowTools_tabs.setCurrentIndex(current_tab)
            except:
                pass
    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme(":/icons/appicon.ico"), self)
        self.tray_icon.setToolTip("Hammer5Tools")
        self.tray_menu = QMenu()
        self.tray_menu.addAction(QAction("Show", self, triggered=self.show))
        self.tray_menu.addAction(QAction("Exit", self, triggered=self.exit_application))
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

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

            # If no addons were found, suggest creating an addon
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
                    # Optionally add a placeholder in the combobox or leave it empty
                    self.ui.ComboBoxSelectAddon.addItem("")
                    self.ui.ComboBoxSelectAddon.setCurrentIndex(0)

            # If there is a stored addon name but it doesn't exist or is empty, set addon selection
            if not get_addon_name() and found_any:
                set_addon_name(self.ui.ComboBoxSelectAddon.currentText())

        except Exception as e:
            print("Failed to load addons:", e)
    def refresh_addon_combobox(self):
        self.ui.ComboBoxSelectAddon.currentTextChanged.disconnect(self.selected_addon_name)

        addon = get_addon_name()
        self.ui.ComboBoxSelectAddon.clear()
        self.populate_addon_combobox()
        self.ui.ComboBoxSelectAddon.setCurrentText(addon)

        self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)

        # for those who didn't have editors
        tools = [
            "SoundEventEditorMainWindow",
            "SmartPropEditorMainWindow",
            "BatchCreator_MainWindow",
            "LoadingEditorMainWindow",
        ]

        if any(getattr(self, tool, None) for tool in tools):
            pass
        else:
            self.selected_addon_name()

    def launch_addon_action(self):
        self.update_title(text=f'Launched addon --- {get_addon_name()}')
        launch_addon()

    def setup_buttons(self):
        self.ui.Launch_Addon_Button.clicked.connect(self.launch_addon_action)
        self.ui.FixNoSteamLogon_Button.clicked.connect(self.SteamNoLogonFix)
        self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)

        addon = get_addon_name()
        combo_items = [
            self.ui.ComboBoxSelectAddon.itemText(i)
            for i in range(self.ui.ComboBoxSelectAddon.count())
        ]

        if addon not in combo_items:
            self.refresh_addon_combobox()
            self.selected_addon_name()

        # if index 0, loads tabs
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
        # self.ui.bluesky_button.clicked.connect(self.open_bluesky)
        self.ui.discord.clicked.connect(self.open_discord)
        self.ui.documentation_button.clicked.connect(self.open_about)

    def closeEvent(self, event):
        if settings.value("APP/minimize_to_tray", type=bool, defaultValue=True):
            event.ignore()
            self.hide()
            settings.setValue("APP/minimize_to_tray", type=bool, value=True)
            self.show_minimize_message_once()
        else:
            self.exit_application()

    def selected_addon_name(self):
        set_addon_name(self.ui.ComboBoxSelectAddon.currentText())
        # These tabs should be updated when addon name was changed

        # SoundEventEditor

        # Clean up SoundEventEditorMainWidget
        try:
            if hasattr(self, 'SoundEventEditorMainWindow') and self.SoundEventEditorMainWindow:
                self.SoundEventEditorMainWindow.closeEvent(self.event)
                self.SoundEventEditorMainWindow.deleteLater()
        except Exception as e:
            print(f"Error while cleaning up SoundEventEditorMainWidget: {e}")

        try:
            if hasattr(self, 'SmartPropEditorMainWindow') and self.SmartPropEditorMainWindow:
                self.SmartPropEditorMainWindow.closeEvent(self.event)
                self.SmartPropEditorMainWindow.deleteLater()
        except Exception as e:
            print(f"Error while cleaning up SoundEventEditorMainWidget: {e}")

        try:
            if hasattr(self, 'BatchCreator_MainWindow') and self.BatchCreator_MainWindow:
                self.BatchCreator_MainWindow.close()
        except Exception as e:
            print('Error while cleaning up BatchCreator_MainWindow:', e)

        try:
            if hasattr(self, 'LoadingEditorMainWindow') and self.LoadingEditorMainWindow:
                self.LoadingEditorMainWindow.close()
                self.LoadingEditorMainWindow.deleteLater()
        except Exception as e:
            print('Error while cleaning up Loading_editorMainWindow:', e)

        # Create a new instance of BatchCreatorMainWindow
        try:
            self.BatchCreator_MainWindow = BatchCreatorMainWindow(update_title=self.update_title)

            self.ui.BatchCreator_tab.layout().addWidget(self.BatchCreator_MainWindow)
        except Exception as e:
            print('Error while setting up BatchCreator_MainWindow:', e)

        # Smartprop editior

        try:
            self.SoundEventEditorMainWindow = SoundEventEditorMainWindow(update_title=self.update_title)
            self.ui.soundeditor_tab.layout().addWidget(self.SoundEventEditorMainWindow)
        except Exception as e:
            print(f"Error while cleaning up SoundEventEditorMainWidget: {e}")

        try:
            self.SmartPropEditorMainWindow = SmartPropEditorMainWindow(update_title=self.update_title)
            self.ui.smartpropeditor_tab.layout().addWidget(self.SmartPropEditorMainWindow)
        except Exception as e:
            print(f"Error while cleaning up SmartPropEditorMainWindow: {e}")

        try:
            self.LoadingEditorMainWindow = Loading_editorMainWindow()
            self.ui.Loading_Editor_Tab.layout().addWidget(self.LoadingEditorMainWindow)
        except Exception as e:
            print(f"Error while cleaning up Loading_editorMainWindow: {e}")


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


    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

    def show_minimize_message_once(self):
        if get_config_bool('APP', 'minimize_message_shown'):
            self.tray_icon.showMessage("Hammer5Tools", "Application minimized to tray.", QSystemTrayIcon.Information,
                                       2000)
            set_config_bool('APP', 'minimize_message_shown', False)

    def exit_application(self):
        try:
            discord_status_clear()
        except:
            pass
        stop_discord_thread.set()

        # Ensure all threads are properly stopped
        if hasattr(self, 'discord_thread') and self.discord_thread.is_alive():
            self.discord_thread.join()

        # Explicitly delete the tray icon
        self.tray_icon.hide()
        self.tray_icon.deleteLater()
        self._save_user_prefs()

        # Close editors
        try:
            self.SmartPropEditorMainWindow.closeEvent(self.event)
        except:
            pass
        try:
            self.SoundEventEditorMainWindow.closeEvent(self.event)
        except:
            pass
        self.current_tab(True)
        QApplication.quit()
        QApplication.instance().quit()
        QApplication.exit(1)
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
    while not stop_discord_thread.is_set():
        update_discord_status()
        time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hammer 5 Tools Application")
    parser.add_argument('--dev', action='store_true', help='Enable development mode')
    args, unknown = parser.parse_known_args()

    lock_file = open(LOCK_FILE, 'w')
    try:
        portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except portalocker.LockException:
        app = QApplication(sys.argv)
        widget = Notification()
        app.setStyleSheet(QT_Stylesheet_global)
        widget.show()
        sys.exit(app.exec())

    app = QApplication(sys.argv)
    app.setStyleSheet(QT_Stylesheet_global)

    widget = Widget(dev_mode=args.dev)
    widget.show()

    if get_config_bool('DISCORD_STATUS', 'show_status'):
        from other.discord_status_main import discord_status_clear, update_discord_status
        widget.discord_thread = threading.Thread(target=DiscordStatusMain_do)
        widget.discord_thread.start()
    else:
        debug('Discord status updates are disabled.')

    sys.exit(app.exec())