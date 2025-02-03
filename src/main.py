import ctypes
import sys
import os
import threading
import tempfile
import webbrowser
import time
import argparse

import portalocker
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
    QLabel,
    QCheckBox
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QTimer, QFileSystemWatcher, QPropertyAnimation, QPoint

from about.main import AboutDialog
from src.settings.main import (
    PreferencesDialog,
    get_steam_path,
    get_cs2_path,
    get_addon_name,
    set_addon_name,
    get_config_bool,
    set_config_bool,
    get_config_value,
    set_config_value,
    settings,
    debug
)
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
from styles.qt_global_stylesheet import QT_Stylesheet_global
from src.common import enable_dark_title_bar, app_version, default_commands

steam_path = get_steam_path()
cs2_path = get_cs2_path()
stop_discord_thread = threading.Event()
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'hammer5tools.lock')


class DevWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Development Widget")
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout()
        label = QLabel("Development Mode Active", self)
        layout.addWidget(label)
        self.checkBox_debug_info = QCheckBox("Enable Debug Info", self)
        self.checkBox_debug_info.setChecked(get_config_bool('OTHER', 'debug_info', False))
        self.checkBox_debug_info.toggled.connect(
            lambda: set_config_bool('OTHER', 'debug_info', self.checkBox_debug_info.isChecked())
        )
        layout.addWidget(self.checkBox_debug_info)
        self.setLayout(layout)


class Notification(QMessageBox):
    def __init__(self, parent=None):
        super(Notification, self).__init__(parent)
        self.setWindowTitle("Hammer 5 Tools")
        self.setTextFormat(Qt.RichText)
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
        from ui_main import Ui_MainWindow  # Import here to ensure proper dependency resolution
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

        self.launchOptionPoller = QTimer(self)
        self.launchOptionPoller.setInterval(1000)
        self.launchOptionPoller.timeout.connect(self.updateLaunchAddonButton)
        self.launchOptionPoller.start()

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

    def current_tab(self, set_flag):
        if set_flag:
            try:
                set_config_value('APP', 'current_tab', str(self.ui.MainWindowTools_tabs.currentIndex()))
            except Exception:
                pass
        else:
            try:
                current_tab = int(get_config_value('APP', 'current_tab'))
                self.ui.MainWindowTools_tabs.setCurrentIndex(current_tab)
            except Exception:
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
        if any(getattr(self, tool, None) for tool in tools):
            pass
        else:
            self.selected_addon_name()

    def animate_launch_button(self):
        """
        Creates a gradient overlay effect behind the button text by placing
        the overlay below the text. The animation moves from left to right,
        and then the overlay is removed. Duration: ~1.2 seconds.
        """
        button = self.ui.Launch_Addon_Button

        # Create overlay child widget
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

        # Position the overlay just to the left of the entire button
        overlay.setGeometry(-button_width, 0, button_width, button_height)

        # Show overlay, then move it behind the button's text
        overlay.show()
        overlay.lower()

        # Animate from left to right
        animation = QPropertyAnimation(overlay, b"pos", self)
        animation.setDuration(1200)
        animation.setStartValue(QPoint(-button_width, 0))
        animation.setEndValue(QPoint(button_width, 0))

        # Remove overlay after animation completes
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
        combo_items = [
            self.ui.ComboBoxSelectAddon.itemText(i)
            for i in range(self.ui.ComboBoxSelectAddon.count())
        ]
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
        commands = get_config_value("LAUNCH", "commands", default_commands)
        if commands and "-asset" in commands:
            self.ui.Launch_Addon_Button.setText("Edit map")
        else:
            self.ui.Launch_Addon_Button.setText("Launch Tools")

    def closeEvent(self, event):
        if settings.value("APP/minimize_to_tray", type=bool, defaultValue=True):
            event.ignore()
            self.hide()
            settings.setValue("APP/minimize_to_tray", True)
            self.show_minimize_message_once()
        else:
            self.exit_application()

    def selected_addon_name(self):
        set_addon_name(self.ui.ComboBoxSelectAddon.currentText())
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

        try:
            self.BatchCreator_MainWindow = BatchCreatorMainWindow(update_title=self.update_title)
            self.ui.BatchCreator_tab.layout().addWidget(self.BatchCreator_MainWindow)
        except Exception as e:
            print('Error while setting up BatchCreator_MainWindow:', e)

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

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

    def show_minimize_message_once(self):
        if get_config_bool('APP', 'minimize_message_shown'):
            self.tray_icon.showMessage(
                "Hammer5Tools",
                "Application minimized to tray.",
                QSystemTrayIcon.Information,
                2000
            )
            set_config_bool('APP', 'minimize_message_shown', False)

    def exit_application(self):
        try:
            from other.discord_status_main import discord_status_clear
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
    from other.discord_status_main import update_discord_status
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