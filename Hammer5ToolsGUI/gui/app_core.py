import logging
import ctypes
import os
import random
import sys
import time
import webbrowser
from PySide6.QtWidgets import (
    QSystemTrayIcon,
    QMenu,
    QDockWidget,
    QDialog,
    QMainWindow,
    QMessageBox,
    QWidget,
    QApplication,
)
from PySide6.QtGui import QAction, QPainter, QColor, QIcon
from PySide6.QtCore import (
    QPropertyAnimation,
    QPoint,
    QFileSystemWatcher,
    QEvent,
    QTimer,
    Qt,
)
from PySide6.QtNetwork import QLocalServer

from gui.shell.ipc_protocol import IPCMessage, IPCCommand
from gui.forms.about.main import AboutDialog
from gui.forms.mapbuilder.main import MapBuilderDialog
from gui.forms.git_sync.controller import GitController, SyncButton
from gui.settings.common import (
    get_cs2_path,
    get_addon_name,
    set_addon_name,
    get_settings_bool,
    set_settings_bool,
    get_settings_value,
    set_settings_value,
    settings,
    get_addon_dir,
    cs2_addons_dir,
)
from gui.settings.main import PreferencesDialog
from gui.editors.loading_editor.main import Loading_editorMainWindow
from gui.editors.hotkey_editor.main import HotkeyEditorMainWindow
from gui.forms.create_addon.main import Create_addon_Dialog
from gui.other.addon_functions import delete_addon, launch_addon
from gui.other.file_association import check_association, setup_all_associations
from gui.updater.check import check_updates
from gui.forms.export.main import ExportAndImportAddonDialog
from gui.editors.assetgroup_maker.main import BatchCreatorMainWindow
from gui.editors.smartprop_editor.main import SmartPropEditorMainWindow
from gui.editors.soundevent_editor.main import SoundEventEditorMainWindow
from gui.forms.unreal_porter.main import UnrealPorterWidget
from gui.forms.source_porter.main import SourcePorterWidget
from gui.forms.launch_options.main import LaunchOptionsDialog
from gui.common import app_version, default_commands, JsonToKv3, compile as run_compile, enable_dark_title_bar
from gui.other.addon_validation import validate_addon_structure
from gui.forms.cleanup.main import CleanupDialog
from gui.forms.quick_create.main import QuickCreateDialog
from gui.widgets import UnsavedFilesDialog, exception_handler
from gui.shell.addon_selector import AddonSelector, PLACEHOLDERS as ADDON_PLACEHOLDERS
from gui.shell.quick_actions import QuickActions
from gui.shell.tabs import insert_tab_after
from gui.shell.tray import TrayIcon, set_docks_visible
from gui.shell.vrad3_cache import cleanup_vrad3_cache
from gui.shell.window_state import WindowStateSaver

log = logging.getLogger(__name__)

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

class AlternatingMenu(QMenu):
    """QMenu with alternating row backgrounds (QMenu items aren't view rows,
    so this can't be done via stylesheet). Paints a subtle band over odd,
    non-separator rows on top of the normal render."""
    ALT_COLOR = QColor(255, 255, 255, 14)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        row = 0
        for action in self.actions():
            if action.isSeparator():
                continue
            if row % 2 == 1:
                painter.fillRect(self.actionGeometry(action), self.ALT_COLOR)
            row += 1


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        from gui.ui_main import Ui_MainWindow
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)

        self.preferences_dialog = None
        # Editors are built on first tab activation: every live widget makes an
        # app-wide stylesheet repolish (live theme switching) superlinearly
        # slower, so tabs nobody looked at stay empty.
        self._tab_builders = {}
        self._addon_initialised = False
        self.mapbuilder_dialog = None
        self.launch_options = None
        self.Create_addon_Dialog = None
        self.Delete_addon_Dialog = None

        if get_cs2_path() is None:
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

        self.tray = TrayIcon(self)
        self.quick_actions = QuickActions(self)
        self.addon_selector = AddonSelector(self)
        self.setup_tabs()
        self.setup_buttons()
        self.current_tab(False)
        self.settings = settings
        self.window_state = WindowStateSaver(self, settings)

        self.setWindowTitle("Hammer 5 Tools")

        self.launchOptionPoller = QTimer(self)
        self.launchOptionPoller.setInterval(1000)
        self.launchOptionPoller.timeout.connect(self.addon_selector.update_launch_button_text)
        self.launchOptionPoller.start()

        QTimer.singleShot(100, self.deferred_update_check)
        self.window_state.restore()
        if get_settings_bool('APP', 'show_about_on_startup', True):
            QTimer.singleShot(500, self.open_about)
        
        QTimer.singleShot(2000, self.quick_actions.prompt_for_file_associations)

        self.addon_watcher = QFileSystemWatcher(self)
        addons_dir = cs2_addons_dir("content")
        if addons_dir is not None and addons_dir.exists():
            self.addon_watcher.addPath(str(addons_dir))
            self.addon_watcher.directoryChanged.connect(self.addon_selector.refresh)

        set_docks_visible(self, True)
        validate_addon_structure()

    def trigger_update_check(self):
        check_updates("https://github.com/dertwist/Hammer5Tools", app_version, False)

    def deferred_update_check(self):
        try:
            check_updates("https://github.com/dertwist/Hammer5Tools", app_version, True)
        except Exception as e:
            log.error(f"Error checking updates: {e}")

    @exception_handler
    def update_title(self, status=None, file_path=None, text=None):
        # Feeds the persistent console line only; window title stays static.
        if file_path:
            if status == "saved":
                msg = f"Saved file [{file_path}]"
            elif status == "opened":
                msg = f"Opened file [{file_path}]"
            else:
                return
        elif text:
            msg = text
        else:
            return
        try: self.ui.console_label.setText(msg)
        except Exception: pass

    def _hook_undo_console(self, stack):
        """Report a QUndoStack's actions to the console line. A fresh push and a
        redo both advance the index by one, so count() disambiguates them."""
        if stack is None:
            return
        try:
            state = {"idx": stack.index(), "count": stack.count()}
        except (RuntimeError, AttributeError):
            return

        def on_index_changed(new_idx):
            try:
                prev_idx, prev_count = state["idx"], state["count"]
                count = stack.count()
                state["idx"], state["count"] = new_idx, count
                if count == 0:
                    return
                if count > prev_count:                       # new command pushed
                    txt = stack.text(new_idx - 1)
                    if txt: self.update_title(text=txt[:1].upper() + txt[1:])
                elif new_idx < prev_idx:                     # undo
                    txt = stack.text(new_idx)
                    if txt: self.update_title(text=f"Undo [{txt}]")
                elif new_idx > prev_idx:                     # redo
                    txt = stack.text(new_idx - 1)
                    if txt: self.update_title(text=f"Redo [{txt}]")
            except (RuntimeError, AttributeError):
                pass

        try:
            stack.indexChanged.connect(on_index_changed)
        except (RuntimeError, AttributeError):
            pass

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

    def open_file_in_batchcreator(self, file_path):
        # Same shape as the two below: switch first so the tab builds, then open.
        idx = self.ui.MainWindowTools_tabs.indexOf(self.ui.BatchCreator_tab)
        if idx >= 0:
            self.ui.MainWindowTools_tabs.setCurrentIndex(idx)
            self._ensure_tab()
        if not getattr(self, 'BatchCreator_MainWindow', None):
            print("AssetGroup Maker not initialized")
            return
        self.BatchCreator_MainWindow.open_filepath(file_path)

    def open_file_in_smartprop(self, file_path):
        if not file_path:
            return
        file_path = os.path.normpath(file_path)
        if "csgo_addons" in file_path.lower():
            parts = file_path.split(os.sep)
            for i, part in enumerate(parts):
                if part.lower() == "csgo_addons" and i + 1 < len(parts):
                    addon_hint = parts[i + 1]
                    if not self.quick_actions.confirm_addon_for(addon_hint):
                        return
                    break

        # Switch first: currentChanged fires synchronously and builds the editor.
        smartprop_tab_index = self.ui.MainWindowTools_tabs.indexOf(self.ui.smartpropeditor_tab)
        if smartprop_tab_index >= 0:
            self.ui.MainWindowTools_tabs.setCurrentIndex(smartprop_tab_index)
            self._ensure_tab()
        if not getattr(self, 'SmartPropEditorMainWindow', None):
            print("SmartProp Editor not initialized")
            return
        self.SmartPropEditorMainWindow.open_file(filename=file_path)

    def open_file_in_soundevent(self, file_path):
        if not file_path:
            return
        file_path = os.path.normpath(file_path)
        if "csgo_addons" in file_path.lower():
            parts = file_path.split(os.sep)
            for i, part in enumerate(parts):
                if part.lower() == "csgo_addons" and i + 1 < len(parts):
                    addon_hint = parts[i + 1]
                    if not self.quick_actions.confirm_addon_for(addon_hint):
                        return
                    break

        # Switch first: currentChanged fires synchronously and builds the editor.
        soundevent_tab_index = self.ui.MainWindowTools_tabs.indexOf(self.ui.soundeditor_tab)
        if soundevent_tab_index >= 0:
            self.ui.MainWindowTools_tabs.setCurrentIndex(soundevent_tab_index)
            self._ensure_tab()
        if not getattr(self, 'SoundEventEditorMainWindow', None):
            print("SoundEvent Editor not initialized")
            return
        self.SoundEventEditorMainWindow.load_soundevents(filepath=file_path)

    def setup_tabs(self):
        self.HotkeyEditorMainWindow_instance = HotkeyEditorMainWindow()
        self.ui.hotkeyeditor_tab.layout().addWidget(self.HotkeyEditorMainWindow_instance)

        # Programmatically create DetailProp Editor tab
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        from PySide6.QtGui import QIcon
        self.detailpropeditor_tab = QWidget()
        self.detailpropeditor_tab.setObjectName("detailpropeditor_tab")
        layout = QVBoxLayout(self.detailpropeditor_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        insert_tab_after(
            self.ui.MainWindowTools_tabs, self.ui.hotkeyeditor_tab, self.detailpropeditor_tab,
            QIcon(":/valve_common/icons/tools/hammer/displacement_tool_icon.png"), "DetailProp Editor",
        )

        # Programmatically create Audio Editor tab (addon-independent, created once)
        from gui.editors.soundevent_editor.wave_editor import AudioEditor
        self.audio_editor_tab = QWidget()
        self.audio_editor_tab.setObjectName("audio_editor_tab")
        ae_layout = QVBoxLayout(self.audio_editor_tab)
        ae_layout.setContentsMargins(0, 0, 0, 0)
        self.AudioEditor_instance = AudioEditor(parent=self)
        ae_layout.addWidget(self.AudioEditor_instance)
        insert_tab_after(
            self.ui.MainWindowTools_tabs, self.ui.soundeditor_tab, self.audio_editor_tab,
            QIcon(":/valve_common/icons/tools/common/control_play.png"), "Audio Editor",
        )

        self.ui.MainWindowTools_tabs.currentChanged.connect(self._ensure_tab)

    def _ensure_tab(self, index=None):
        """Build the editor of the tab at `index` (the current one by default) if
        it hasn't been built yet. Popping the builder makes it run exactly once."""
        tabs = self.ui.MainWindowTools_tabs
        page = tabs.widget(tabs.currentIndex() if index is None else index)
        build = self._tab_builders.pop(page, None)
        if build is not None:
            build()

    def _build_batchcreator(self):
        self.BatchCreator_MainWindow = BatchCreatorMainWindow(update_title=self.update_title, parent=self)
        self.ui.BatchCreator_tab.layout().addWidget(self.BatchCreator_MainWindow)

    def _build_soundevent(self):
        self.SoundEventEditorMainWindow = SoundEventEditorMainWindow(update_title=self.update_title, parent=self)
        self.ui.soundeditor_tab.layout().addWidget(self.SoundEventEditorMainWindow)
        self._hook_undo_console(getattr(self.SoundEventEditorMainWindow, 'undo_stack', None))

    def _build_smartprop(self):
        self.SmartPropEditorMainWindow = SmartPropEditorMainWindow(update_title=self.update_title, parent=self)
        self.ui.smartpropeditor_tab.layout().addWidget(self.SmartPropEditorMainWindow)
        self._hook_undo_console(getattr(self.SmartPropEditorMainWindow, 'undo_stack', None))

    def _build_loading(self):
        self.LoadingEditorMainWindow = Loading_editorMainWindow(parent=self)
        self.ui.Loading_Editor_Tab.layout().addWidget(self.LoadingEditorMainWindow)

    def _build_detailprop(self):
        from gui.forms.detail_prop_editor.main import DetailPropEditorWidget
        self.DetailPropEditorWidget_instance = DetailPropEditorWidget(parent=self)
        self.detailpropeditor_tab.layout().addWidget(self.DetailPropEditorWidget_instance)
        self._hook_undo_console(getattr(self.DetailPropEditorWidget_instance, 'undo_stack', None))

    def setup_buttons(self):
        self.git_sync_button = SyncButton(self.centralWidget())
        _combo_idx = self.ui.horizontalLayout_2.indexOf(self.ui.ComboBoxSelectAddon)
        self.ui.horizontalLayout_2.insertWidget(_combo_idx + 1, self.git_sync_button)
        self.git = GitController(self, self.git_sync_button)
        self.ui.Launch_Addon_Button.clicked.connect(self.addon_selector.launch)
        self.ui.ComboBoxSelectAddon.wheelEvent = lambda event: None
        self.ui.ComboBoxSelectAddon.view().setAlternatingRowColors(True)
        self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)
        addon = get_addon_name()
        combo_items = [self.ui.ComboBoxSelectAddon.itemText(i) for i in range(self.ui.ComboBoxSelectAddon.count())]
        if addon not in combo_items: self.addon_selector.refresh()
        if self.ui.ComboBoxSelectAddon.currentText() == get_addon_name(): self.selected_addon_name()
        self.ui.ComboBoxSelectAddon.setCurrentText(get_addon_name())
        self.ui.ComboBoxSelectAddon.activated.connect(self.addon_selector.refresh)
        self.ui.preferences_button.clicked.connect(self.open_preferences_dialog)
        self.ui.my_twitter_button.clicked.connect(self.open_my_twitter)
        self.ui.discord.clicked.connect(self.open_discord)
        self.ui.documentation_button.clicked.connect(self.open_about)
        self.ui.mapbuilder.clicked.connect(self.open_mapbuilder_dialog)
        self._build_addon_actions_menu()
        self._build_utilities_menu()
        # Hide the dropdown arrow on menu tool buttons and ensure uniform height across the bottom bar.
        for b in (self.ui.utilities_button, self.ui.addon_actions_button):
            b.setProperty("h5Component", "mainMenuToolButton")
        self.ui.utilities_button.setMinimumWidth(0)

        h = 32
        for w in (
            self.ui.my_twitter_button,
            self.ui.discord,
            self.ui.documentation_button,
            self.ui.preferences_button,
            self.ui.utilities_button,
            self.ui.addon_actions_button,
            self.ui.ComboBoxSelectAddon,
            self.git_sync_button,
            self.ui.Launch_Addon_Button,
            self.ui.mapbuilder,
        ):
            w.setFixedHeight(h)
        self.ui.console_label.setText("Ready")
        self.addon_selector.update_launch_button_text()

    def _build_addon_actions_menu(self):
        menu = AlternatingMenu(self)
        menu.addAction("Edit launch parameters", self.open_launch_options)
        menu.addSeparator()
        menu.addAction("Create new addon", self.open_create_addon_dialog)
        menu.addAction("Delete addon", self.delete_addon)
        menu.addSeparator()
        menu.addAction("Export addon", self.open_export_and_import_addon)
        menu.addAction("Import addon", self.import_addon_action)
        menu.addSeparator()
        menu.addAction("Open content folder", lambda: self.open_addons_folder("content"))
        menu.addAction("Open game folder", lambda: self.open_addons_folder("game"))
        self.ui.addon_actions_button.setMenu(menu)

    def _build_utilities_menu(self):
        menu = AlternatingMenu(self)
        menu.addAction("SourcePorter", self._open_source_porter)
        menu.addAction("UnrealPorter", self._open_unreal_porter)
        menu.addAction("Cleanup Content", lambda: CleanupDialog(self).show())
        menu.addAction("Cleanup _vrad3 cache", lambda: cleanup_vrad3_cache(self))
        self.ui.utilities_button.setMenu(menu)

    def _open_source_porter(self):
        self.source_porter_dialog = SourcePorterWidget(parent=self)
        self.source_porter_dialog.show()

    def _open_unreal_porter(self):
        self.unreal_porter_dialog = UnrealPorterWidget(parent=self)
        self.unreal_porter_dialog.show()

    def closeEvent(self, event):
        # Capture geometry (including maximized/fullscreen state) while the
        # window is still visible, before it is hidden or destroyed.
        self.window_state.save()
        if get_settings_bool("APP", "minimize_to_tray", False):
            event.ignore()
            self.hide()
            set_docks_visible(self, False)
            self.show_minimize_message_once()
        else: self.exit_application()

    def collect_unsaved_files(self):
        """(editor_name, file_label, save_callable) for every unsaved file in the open editors."""
        editors = (
            ('BatchCreator_MainWindow', "AssetGroup Maker"),
            ('SmartPropEditorMainWindow', "SmartProp Editor"),
            ('SoundEventEditorMainWindow', "SoundEvent Editor"),
            ('AudioEditor_instance', "Wave Editor"),
            ('DetailPropEditorWidget_instance', "DetailProp Editor"),
        )
        unsaved = []
        for attr, editor_name in editors:
            editor = getattr(self, attr, None)
            if editor is None:
                continue
            for label, save in getattr(editor, 'unsaved_files', list)():
                unsaved.append((editor_name, label, save))
        return unsaved

    @exception_handler
    def selected_addon_name(self, text=None):
        new_addon = self.ui.ComboBoxSelectAddon.currentText()
        if not new_addon or new_addon in ADDON_PLACEHOLDERS: return
        current_addon = get_addon_name()
        if current_addon == new_addon and self._addon_initialised: return

        unsaved = self.collect_unsaved_files()
        if unsaved and current_addon and current_addon != new_addon:
            if UnsavedFilesDialog(unsaved, self).exec() != QDialog.Accepted:
                try:
                    self.ui.ComboBoxSelectAddon.currentTextChanged.disconnect(self.selected_addon_name)
                    self.ui.ComboBoxSelectAddon.setCurrentText(current_addon)
                finally:
                    self.ui.ComboBoxSelectAddon.currentTextChanged.connect(self.selected_addon_name)
                return

        set_addon_name(new_addon)
        if getattr(self, 'SoundEventEditorMainWindow', None):
            self.SoundEventEditorMainWindow.close(); self.SoundEventEditorMainWindow.deleteLater(); self.SoundEventEditorMainWindow = None
        if getattr(self, 'SmartPropEditorMainWindow', None):
            self.ui.smartpropeditor_tab.layout().removeWidget(self.SmartPropEditorMainWindow)
            self.SmartPropEditorMainWindow.close(); self.SmartPropEditorMainWindow.deleteLater(); self.SmartPropEditorMainWindow = None
        if getattr(self, 'DetailPropEditorWidget_instance', None) and hasattr(self, 'detailpropeditor_tab'):
            self.detailpropeditor_tab.layout().removeWidget(self.DetailPropEditorWidget_instance)
            self.DetailPropEditorWidget_instance.close(); self.DetailPropEditorWidget_instance.deleteLater(); self.DetailPropEditorWidget_instance = None
        if getattr(self, 'BatchCreator_MainWindow', None):
            self.BatchCreator_MainWindow.close(); self.BatchCreator_MainWindow.deleteLater(); self.BatchCreator_MainWindow = None
        if getattr(self, 'LoadingEditorMainWindow', None):
            self.LoadingEditorMainWindow.close(); self.LoadingEditorMainWindow.deleteLater(); self.LoadingEditorMainWindow = None
        self._tab_builders.clear()
        self._tab_builders[self.ui.BatchCreator_tab] = self._build_batchcreator
        cs2_path = get_cs2_path()
        # SmartProp can be opened as a standalone editor for authoring and GUI
        # testing even when CS2 is unavailable. Its explorer falls back to the
        # current working directory; CS2-dependent operations remain guarded.
        self._tab_builders[self.ui.smartpropeditor_tab] = self._build_smartprop
        if cs2_path is not None:
            self._tab_builders[self.ui.soundeditor_tab] = self._build_soundevent
            self._tab_builders[self.ui.Loading_Editor_Tab] = self._build_loading
            if hasattr(self, 'detailpropeditor_tab'):
                self._tab_builders[self.detailpropeditor_tab] = self._build_detailprop

            if getattr(self, 'AudioEditor_instance', None):
                self.AudioEditor_instance.set_root(
                    os.path.join(cs2_path, 'content', 'csgo_addons', new_addon, 'sounds'))
        self._addon_initialised = True
        self._ensure_tab()

        if getattr(self, 'git', None):
            self.git.refresh()

    @exception_handler
    def open_addons_folder(self, folder_type="content"):
        cs2_path = get_cs2_path()
        if cs2_path is None:
            QMessageBox.warning(self, "CS2 Path Not Set", "CS2 installation path is not set. Please set it in Settings > General > CS2 Path."); return
        addon_name = self.ui.ComboBoxSelectAddon.currentText()
        folder_path = r"\game\csgo_addons" if folder_type == "game" else r"\content\csgo_addons"
        full_path = f"{cs2_path}{folder_path}\\{addon_name}"
        if os.path.exists(full_path): os.startfile(full_path)
        else: QMessageBox.warning(self, "Folder Not Found", f"The addon folder does not exist:\n{full_path}")

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
        # Only overwrite the saved geometry when the window is actually visible;
        # exiting from the tray (window hidden) would otherwise clobber the
        # maximized state captured in closeEvent with a stale/normal geometry.
        if self.isVisible():
            self.window_state.save()
        if getattr(self, "tray", None) and getattr(self.tray, "icon", None):
            self.tray.icon.hide()
        QApplication.quit()


    def open_about(self):
        AboutDialog(app_version, self).exec()

    def open_create_addon_dialog(self):
        dialog = Create_addon_Dialog(self)
        if dialog.exec() == QDialog.Accepted: self.addon_selector.refresh()

    def delete_addon(self):
        if delete_addon(self.ui):
            self.addon_selector.refresh()

    def open_export_and_import_addon(self):
        ExportAndImportAddonDialog(self).exec()

    def import_addon_action(self):
        dialog = ExportAndImportAddonDialog(self)
        dialog.do_import_addon()
        self.addon_selector.refresh()

    def open_my_twitter(self): webbrowser.open("https://twitter.com/dertwist")
    def open_discord(self): webbrowser.open("https://discord.gg/6X88yX8Y")

    # Qt virtual overrides: they keep Qt's camelCase and stay on the window.
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.window_state.schedule_save()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.window_state.schedule_save()

    def changeEvent(self, event):
        super().changeEvent(event)
        # Persist maximize/restore/fullscreen transitions promptly.
        if event.type() == QEvent.WindowStateChange:
            self.window_state.save()

    def show_minimize_message_once(self): pass

def handle_new_connection(server, widget):
    socket = server.nextPendingConnection()
    if socket.waitForReadyRead(1000):
        data = socket.readAll().data()
        message = IPCMessage.parse(data)
        if message:
            command = message.get("command")
            if command == IPCCommand.SHOW_WINDOW.value:
                widget.tray.restore_window()
            elif command == IPCCommand.OPEN_FILE.value:
                file_path = message.get("file_path")
                editor_type = message.get("editor_type")
                if file_path:
                    widget.tray.restore_window()
                    ext = os.path.splitext(file_path)[1].lower()
                    if editor_type == "soundevent" or ext == '.vsndevts':
                        widget.open_file_in_soundevent(file_path)
                    else:
                        widget.open_file_in_smartprop(file_path)
            elif command == IPCCommand.CREATE_VMDL.value:
                widget.tray.restore_window()
                widget.quick_actions.open_quick_create_dialog(message.get("file_path"), "vmdl")
            elif command == IPCCommand.QUICK_VMDL.value:
                widget.tray.restore_window()
                widget.quick_actions.create_vmdl(message.get("file_path"))
            elif command == IPCCommand.QUICK_BATCH.value:
                widget.tray.restore_window()
                widget.quick_actions.create_compile_batch(message.get("file_path"))
            elif command == IPCCommand.QUICK_PROCESS.value:
                widget.tray.restore_window()
                widget.quick_actions.compile_folder(message.get("file_path"))
            elif command == IPCCommand.QUICK_PROCESS_FILE.value:
                widget.tray.restore_window()
                widget.quick_actions.compile_file(message.get("file_path"))
    socket.disconnectFromServer()

def start_instance_server(widget):
    from gui.shell.ipc_server_utils import set_ipc_server
    server = QLocalServer()
    set_ipc_server(server)
    if not server.listen(INSTANCE_KEY):
        # On POSIX/macOS, a stale socket file from an unclean exit can prevent listen.
        QLocalServer.removeServer(INSTANCE_KEY)
        if not server.listen(INSTANCE_KEY):
            raise RuntimeError(f"Could not start the instance IPC server: {server.errorString()}")
    server.newConnection.connect(lambda: handle_new_connection(server, widget))
    return server



Widget = MainWindow
