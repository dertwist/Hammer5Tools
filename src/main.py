import os, threading, portalocker, tempfile, webbrowser, time, socket, logging, ctypes, hashlib, sys, subprocess, datetime
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QMainWindow, QMessageBox, QDialog, QLabel, QMessageBox
from PySide6.QtGui import QIcon, QAction, QTextCursor
from PySide6.QtCore import QObject, Signal, Qt
from ui_main import Ui_MainWindow
from qt_styles.qt_global_stylesheet import QT_Stylesheet_global
from documentation.documentation import Documentation_Dialog
from preferences import PreferencesDialog, get_steam_path, get_cs2_path, get_addon_name, set_addon_name, get_config_bool, set_config_bool, get_config_value, set_config_value, settings, debug
from loading_editor.loading_editor_main import Loading_editorMainWindow
from hotkey_editor.main import HotkeyEditorMainWindow
from create_addon.create_addon_mian import Create_addon_Dialog
from minor_features.steamfixnologon import SteamNoLogoFixThreadClass
from minor_features.addon_functions import delete_addon, launch_addon
from minor_features.update_check import check_updates
from export_and_import_addon.export_and_import_addon import export_and_import_addon_dialog
from BatchCreator.BatchCreator_main import BatchCreatorMainWindow
from smartprop_editor.main import SmartPropEditorMainWindow
from soundevent_editor.main import SoundEventEditorMainWindow
from minor_features.assettypes import AssetTypesModify

# Variables
steam_path = get_steam_path()
cs2_path = get_cs2_path()
stop_discord_thread = threading.Event()
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'hammer5tools.lock')

# Versions
app_version = '3.0.0'
batchcreator_version = '1.2.2'
soundevent_editor_version = '2.0.0'
smartprop_editor_version = '0.9.4'
hotkey_editor_version = '1.1.0'
loading_editor_version = '1.0.0'



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

class Stream(QObject):
    newText = Signal(str)

    def write(self, text):
        self.newText.emit(str(text))

    def flush(self):
        pass
class Widget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        sys.stdout = Stream(newText=self.on_update)
        self.setup_tray_icon()
        self.setup_tabs()
        self.populate_addon_combobox()
        self.setup_buttons()
        self.preferences_dialog = None
        self.Create_addon_Dialog = None
        self.Delete_addon_Dialog = None
        self.current_tab(False)
        self.settings = settings
        try:
            check_updates("https://github.com/dertwist/Hammer5Tools", app_version, True)
        except Exception as e:
            print(f"Error checking updates: {e}")

        print(f'SmartProp Editor version: {smartprop_editor_version}')
        print(f'Hotkey Editor version: {hotkey_editor_version}')
        print(f"Soundevent Editor version: v{soundevent_editor_version}")
        print(f"BatchCreator version: {batchcreator_version}")
        print(f"Loading Editor version: {loading_editor_version}")
        try:
            AssetTypesModify()
        except Exception as e:
            debug(f"Error: {e}")

        self._restore_user_prefs()
        if get_config_bool('APP', 'first_launch'):
            self.open_documentation()
            self.settings.setValue("MainWindow/default_windowState", self.saveState())
            set_config_bool('APP', 'first_launch', False)

    # def __del__(self):
    #     sys.stdout = sys.__stdout__
    def on_update(self, text):
        cursor = self.ui.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.ui.console.setTextCursor(cursor)
        self.ui.console.ensureCursorVisible()
        # cursor = self.ui.console.textCursor()
        cursor.removeSelectedText()

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
        try:
            for item in os.listdir(os.path.join(cs2_path, "content", "csgo_addons")):
                if os.path.isdir(os.path.join(cs2_path, "content", "csgo_addons", item)) and item not in exclude_addons:
                    self.ui.ComboBoxSelectAddon.addItem(item)
            if not get_addon_name():
                set_addon_name(self.ui.ComboBoxSelectAddon.currentText())
        except:
            print("Wrong Cs2 Path")
    def refresh_addon_combobox(self):
        self.ui.ComboBoxSelectAddon.currentTextChanged.disconnect(self.selected_addon_name)

        addon = get_addon_name()
        self.ui.ComboBoxSelectAddon.clear()
        self.populate_addon_combobox()
        self.ui.ComboBoxSelectAddon.setCurrentText(addon)

        self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)

    def setup_buttons(self):
        self.ui.Launch_Addon_Button.clicked.connect(launch_addon)
        self.ui.FixNoSteamLogon_Button.clicked.connect(self.SteamNoLogonFix)
        self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)
        # if index 0, loads tabs
        if self.ui.ComboBoxSelectAddon.currentText() == get_addon_name():
            self.selected_addon_name()
        self.ui.ComboBoxSelectAddon.setCurrentText(get_addon_name())

        self.ui.ComboBoxSelectAddon.activated.connect(self.refresh_addon_combobox)

        self.ui.preferences_button.clicked.connect(self.open_preferences_dialog)
        self.ui.create_new_addon_button.clicked.connect(self.open_create_addon_dialog)
        self.ui.delete_addon_button.clicked.connect(self.delete_addon)
        self.ui.export_and_import_addon_button.clicked.connect(self.open_export_and_import_addon)
        self.ui.check_Box_NCM_Mode.setChecked(get_config_bool('LAUNCH', 'ncm_mode'))
        self.ui.check_Box_NCM_Mode.stateChanged.connect(self.handle_ncm_mode_checkbox)
        self.ui.open_addons_folder_button.clicked.connect(self.open_addons_folder)
        self.ui.my_twitter_button.clicked.connect(self.open_my_twitter)
        self.ui.bluesky_button.clicked.connect(self.open_bluesky)
        self.ui.discord.clicked.connect(self.open_discord)
        self.ui.documentation_button.clicked.connect(self.open_documentation)

    def closeEvent(self, event):
        if settings.value("APP/minimize_to_tray", type=bool, defaultValue=True):
            event.ignore()
            self.hide()
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
            self.BatchCreator_MainWindow = BatchCreatorMainWindow(batchcreator_version)

            self.ui.BatchCreator_tab.layout().addWidget(self.BatchCreator_MainWindow)
        except Exception as e:
            print('Error while setting up BatchCreator_MainWindow:', e)

        # Smartprop editior

        try:
            self.SoundEventEditorMainWindow = SoundEventEditorMainWindow()
            self.ui.soundeditor_tab.layout().addWidget(self.SoundEventEditorMainWindow)
        except Exception as e:
            print(f"Error while cleaning up SoundEventEditorMainWidget: {e}")

        try:
            self.SmartPropEditorMainWindow = SmartPropEditorMainWindow()
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

    def reset_window(self):
        state = self.settings.value("MainWindow/default_windowState")
        self.restoreState(state)
    def open_preferences_dialog(self):
        if self.preferences_dialog is None:
            self.preferences_dialog = PreferencesDialog(app_version, self)
            self.preferences_dialog.show()
            self.preferences_dialog.finished.connect(self.preferences_dialog_closed)
            self.preferences_dialog.reset_window_signal.connect(self.reset_window)

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
        dialog = export_and_import_addon_dialog(self)
        dialog.finished.connect(self.refresh_addon_combobox)
        dialog.show()
    def SteamNoLogonFix(self):
        self.thread = SteamNoLogoFixThreadClass()
        self.thread.start()
        self.thread.stop()

    def handle_ncm_mode_checkbox(self):
        set_config_bool('LAUNCH', 'ncm_mode', self.ui.check_Box_NCM_Mode.isChecked())

    def open_my_twitter(self):
        webbrowser.open("https://twitter.com/der_twist")
    def open_bluesky(self):
        webbrowser.open("https://bsky.app/profile/der-twist.bsky.social")
    def open_discord(self):
        webbrowser.open("https://discord.gg/DvCXEyhssd")

    def open_documentation(self):
        Documentation_Dialog(app_version, self).show()


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


    # Create a lock file to ensure single instance
    lock_file = open(LOCK_FILE, 'w')
    try:
        portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except portalocker.LockException:
        # If the lock file is already locked, bring the existing instance to the foreground
        app = QApplication(sys.argv)
        widget = Notification()  # Ensure to pass the parent if needed
        app.setStyleSheet(QT_Stylesheet_global)
        widget.show()
        sys.exit(app.exec())

    app = QApplication(sys.argv)
    app.setStyleSheet(QT_Stylesheet_global)

    # import qtvscodestyle as qtvsc
    #
    # stylesheet = qtvsc.load_stylesheet(qtvsc.Theme.DARK_VS)
    # app.setStyleSheet(stylesheet)
    # app.setStyle('fusion')
    widget = Widget()
    widget.show()

    try:
        if get_config_bool('DISCORD_STATUS', 'show_status'):
            from minor_features.discord_status_main import discord_status_clear, update_discord_status
            widget.discord_thread = threading.Thread(target=DiscordStatusMain_do)
            widget.discord_thread.start()
        else:
            print('Discord status updates are disabled.')
    except:
        "The status of the discord was not started"

    sys.exit(app.exec())