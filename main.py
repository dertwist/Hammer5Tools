import sys, os, subprocess, threading, portalocker, tempfile, webbrowser, time, socket
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtGui import QIcon, QAction
from ui_form import Ui_Widget
from qt_styles.qt_global_stylesheet import QT_Stylesheet_global
from documentation.documentation import Documentation_Dialog
from preferences import PreferencesDialog, get_steam_path, get_cs2_path, get_addon_name, set_addon_name, get_config_bool, set_config_bool
from soudevent_editor.soundevent_editor_main import SoundEventEditorMainWidget
from loading_editor.loading_editor_main import Loading_editorMainWindow
from create_addon.create_addon_mian import Create_addon_Dialog
from minor_features.steamfixnologon import SteamNoLogoFixThreadClass
from minor_features.discord_status_main import discord_status_clear, update_discord_status
from minor_features.addon_functions import delete_addon, launch_addon
from minor_features.update_check import check_updates
from export_and_import_addon.export_and_import_addon import export_and_import_addon_dialog
from BatchCreator.BatchCreator_main import BatchCreatorMainWindow


steam_path = get_steam_path()
cs2_path = get_cs2_path()
stop_discord_thread = threading.Event()

LOCK_FILE = os.path.join(tempfile.gettempdir(), 'hammer5tools.lock')
SOCKET_HOST = 'localhost'
SOCKET_PORT = 65432

app_version = '1.2.0'
batchcreator_version = '1.0.0'


class Widget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setup_tray_icon()
        self.setup_tabs()
        self.populate_addon_combobox()
        self.setup_buttons()
        self.preferences_dialog = None
        self.Create_addon_Dialog = None
        self.Delete_addon_Dialog = None
        check_updates("https://github.com/dertwist/Hammer5Tools", app_version)

        try:
            if get_config_bool('APP', 'first_launch'):
                self.open_documentation()
                set_config_bool('APP', 'first_launch', 'False')
        except:
            pass
        self.start_socket_server()

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
        self.LoadingEditorMainWindow = Loading_editorMainWindow()
        self.ui.Loading_Editor_Tab.layout().addWidget(self.LoadingEditorMainWindow)

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
        addon = get_addon_name()
        self.ui.ComboBoxSelectAddon.clear()
        self.populate_addon_combobox()
        print(addon)
        self.ui.ComboBoxSelectAddon.setCurrentText(addon)

    def setup_buttons(self):
        self.ui.Launch_Addon_Button.clicked.connect(launch_addon)
        self.ui.FixNoSteamLogon_Button.clicked.connect(self.SteamNoLogonFix)
        self.ui.ComboBoxSelectAddon.currentIndexChanged.connect(self.selected_addon_name)
        # if index 0, loads tabs
        if self.ui.ComboBoxSelectAddon.currentText() == get_addon_name():
            self.selected_addon_name()
        self.ui.ComboBoxSelectAddon.setCurrentText(get_addon_name())

        self.ui.preferences_button.clicked.connect(self.open_preferences_dialog)
        self.ui.create_new_addon_button.clicked.connect(self.open_create_addon_dialog)
        self.ui.delete_addon_button.clicked.connect(self.delete_addon)
        self.ui.export_and_import_addon_button.clicked.connect(self.open_export_and_import_addon)
        self.ui.check_Box_NCM_Mode.setChecked(get_config_bool('LAUNCH', 'ncm_mode'))
        self.ui.check_Box_NCM_Mode.stateChanged.connect(self.handle_ncm_mode_checkbox)
        self.ui.open_addons_folder_button.clicked.connect(self.open_addons_folder)
        self.ui.my_twitter_button.clicked.connect(self.open_my_twitter)
        self.ui.documentation_button.clicked.connect(self.open_documentation)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.show_minimize_message_once()

    def selected_addon_name(self):
        set_addon_name(self.ui.ComboBoxSelectAddon.currentText())
        try:
            self.ui.soundeditor_tab.layout().removeWidget(self.SoundEventEditorMainWidget)
            self.SoundEventEditorMainWidget.deleteLater()
        except:
            pass
        self.SoundEventEditorMainWidget = SoundEventEditorMainWidget()
        self.ui.soundeditor_tab.layout().addWidget(self.SoundEventEditorMainWidget)



        try:
            layout = self.ui.BatchCreator_tab.layout()
            if self.BatchCreator_MainWindow:
                layout.removeWidget(self.BatchCreator_MainWindow)
                self.BatchCreator_MainWindow.deleteLater()
                self.BatchCreator_MainWindow = None
        except Exception as e:
            print(f"Error while cleaning up BatchCreator_MainWindow: {e}")
        self.BatchCreator_MainWindow = BatchCreatorMainWindow(batchcreator_version)
        self.ui.BatchCreator_tab.layout().addWidget(self.BatchCreator_MainWindow)

    def open_addons_folder(self):
        addon_name = self.ui.ComboBoxSelectAddon.currentText()
        folder_name = self.ui.open_addons_folder_downlist.currentText()
        folder_path = r"\game\csgo_addons" if folder_name == "Game" else r"\content\csgo_addons"
        os.startfile(f"{cs2_path}{folder_path}\\{addon_name}")

    def open_preferences_dialog(self):
        if self.preferences_dialog is None:
            self.preferences_dialog = PreferencesDialog(self)
            self.preferences_dialog.show()
            self.preferences_dialog.finished.connect(self.preferences_dialog_closed)

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
        self.thread = SteamNoLogoFixThreadClass(parent=None, addon_name=get_addon_name(),
                                                NCM_mode=get_config_bool('LAUNCH', 'ncm_mode'))
        self.thread.start()
        self.thread.stop()

    def handle_ncm_mode_checkbox(self):
        set_config_bool('LAUNCH', 'ncm_mode', self.ui.check_Box_NCM_Mode.isChecked())

    def open_my_twitter(self):
        webbrowser.open("https://twitter.com/der_twist")

    def open_documentation(self):
        Documentation_Dialog(app_version, self).show()


    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

    def show_minimize_message_once(self):
        if get_config_bool('APP', 'minimize_message_shown'):
            self.tray_icon.showMessage("Hammer5Tools", "Application minimized to tray.", QSystemTrayIcon.Information,
                                       2000)
            set_config_bool('APP', 'minimize_message_shown', 'False')

    def exit_application(self):
        discord_status_clear()
        stop_discord_thread.set()

        # Ensure all threads are properly stopped
        if hasattr(self, 'discord_thread') and self.discord_thread.is_alive():
            self.discord_thread.join()

        # Explicitly delete the tray icon
        self.tray_icon.hide()
        self.tray_icon.deleteLater()

        QApplication.quit()
        QApplication.instance().quit()
        QApplication.exit(1)

    def start_socket_server(self):
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket_server.bind((SOCKET_HOST, SOCKET_PORT))
            self.socket_server.listen(1)
            threading.Thread(target=self.listen_for_connections, daemon=True).start()
        except socket.error:
            print("Socket already in use. Another instance might be running.")
            sys.exit(0)

    def listen_for_connections(self):
        while True:
            conn, _ = self.socket_server.accept()
            conn.recv(1024)  # Read the message
            self.show()
            self.raise_()
            self.activateWindow()
            conn.close()

def DiscordStatusMain_do():
    while not stop_discord_thread.is_set():
        update_discord_status()
        time.sleep(1)

if __name__ == "__main__":
    # Check for updates at launc

    # Create a lock file to ensure single instance
    lock_file = open(LOCK_FILE, 'w')
    try:
        portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except portalocker.LockException:
        # If the lock file is already locked, bring the existing instance to the foreground
        print("Another instance is already running. Bringing it to the foreground.")
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SOCKET_HOST, SOCKET_PORT))
            client_socket.send(b"SHOW")
            client_socket.close()
        except socket.error:
            print("Failed to connect to the existing instance.")
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyleSheet(QT_Stylesheet_global)
    widget = Widget()
    widget.show()

    try:
        if get_config_bool('DISCORD_STATUS', 'show_status'):
            widget.discord_thread = threading.Thread(target=DiscordStatusMain_do)
            widget.discord_thread.start()
        else:
            print('Discord status updates are disabled.')
    except:
        "The status of the discord was not started"

    sys.exit(app.exec())