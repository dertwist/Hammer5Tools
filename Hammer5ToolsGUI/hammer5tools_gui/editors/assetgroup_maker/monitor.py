import os
import json
from pathlib import Path
from typing import Optional, Dict, Tuple, List

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QMenu, QListWidget, QListWidgetItem, QApplication, QMessageBox
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Signal, QSize, QFileSystemWatcher, QTimer

from hammer5tools_gui.settings.main import get_addon_dir, debug
from hammer5tools_gui.styles.common import qt_stylesheet_button_icon, qt_stylesheet_widgetlist
from hammer5tools_gui.editors.assetgroup_maker.process import StartProcess
from hammer5tools_gui.editors.assetgroup_maker.objects import load_hbat_file, save_hbat_file
from hammer5tools_gui.settings.common import get_settings_value
try:
    from hammer5tools_gui.other.cs2_netcon import CS2Netcon
except Exception:
    CS2Netcon = None


def is_watch_enabled(config_path: str) -> bool:
    """
    Check if watch_changes is enabled for this .hbat config. Defaults to True.
    """
    try:
        data = load_hbat_file(config_path)
        return bool(data.get('settings', {}).get('watch_changes', True))
    except Exception:
        return True


def set_watch_enabled(config_path: str, enabled: bool):
    """
    Set watch_changes setting in .hbat file.
    """
    try:
        if not os.path.isfile(config_path):
            return
        data = load_hbat_file(config_path)
        if 'settings' not in data:
            data['settings'] = {}
        data['settings']['watch_changes'] = enabled
        save_hbat_file(config_path, data)
    except Exception as e:
        debug(f"Error updating watch_changes in {config_path}: {e}")


def read_reference_from_file(config_path: str) -> Optional[str]:
    """
    Read the reference path from a configuration file.
    """
    try:
        data = load_hbat_file(config_path)
        templates = data.get('templates', [])
        addon_dir = get_addon_dir()
        for tpl in templates:
            reference = tpl.get('reference', '')
            if reference:
                if os.path.isabs(reference):
                    return reference
                if addon_dir:
                    return str(Path(addon_dir) / reference)
                return reference
    except Exception as e:
        debug(f"Error reading {config_path}: {e}")
    return None


def get_reference_asset_path(config_path: str) -> Optional[str]:
    """
    Read the relative asset reference path from a configuration file for the open_asset command.
    """
    try:
        data = load_hbat_file(config_path)
        templates = data.get('templates', [])
        for tpl in templates:
            reference = tpl.get('reference', '')
            if reference:
                addon_dir = get_addon_dir()
                if os.path.isabs(reference) and addon_dir:
                    try:
                        reference = os.path.relpath(reference, addon_dir)
                    except ValueError:
                        pass
                return reference.replace('\\', '/').strip('/')
    except Exception as e:
        debug(f"Error getting asset path for {config_path}: {e}")
    return None


def validate_reference_file(reference_path: str) -> bool:
    """
    Validates the referenced file.
    - Must exist.
    - Must not be binary (checked via presence of null bytes in first 1024 bytes).
    - Must not be empty (after decoding as UTF-8).
    Returns True if valid, else False.
    """
    ref_path = Path(reference_path)
    if not ref_path.exists():
        debug(f"Reference file does not exist: {reference_path}")
        return False
    try:
        with ref_path.open('rb') as f:
            sample = f.read(1024)
            if b'\0' in sample:
                debug(f"Reference file is binary: {reference_path}")
                return False
            content = sample.decode('utf-8', errors='replace')
            if not any(char for char in content if not char.isspace()):
                remaining = f.read()
                if not any(char for char in remaining.decode('utf-8', errors='replace') if not char.isspace()):
                    debug(f"Reference file is empty or contains only whitespace: {reference_path}")
                    return False
        return True
    except Exception as e:
        debug(f"Error validating reference file {reference_path}: {e}")
        return False


class FileItemWidget(QWidget):
    """
    Widget representing a file item with options to toggle watch changes, open, process, or open reference asset.
    """
    open_requested = Signal(str)
    process_requested = Signal(str)
    open_reference_requested = Signal(str)
    watch_toggled = Signal(str, bool)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.watch_enabled = is_watch_enabled(self.file_path)
        self.setup_ui()

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width(), max(hint.height(), 28))

    def setup_ui(self):
        """
        Set up the user interface for the file item widget.
        """
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        addon_dir = get_addon_dir()
        relative_path = os.path.relpath(self.file_path, addon_dir) if addon_dir else os.path.basename(self.file_path)
        path_parts = relative_path.replace('\\', '/').split('/')
        text = '/'.join(path_parts[-2:]) if len(path_parts) >= 2 else relative_path

        self.label = QLabel(text)
        self.label.setStyleSheet("background: transparent;")
        self.setToolTip(self.file_path)

        button_size = QSize(22, 22)
        icon_size = QSize(16, 16)

        self.watch_button = QPushButton()
        self.watch_button.setFixedSize(button_size)
        self.watch_button.setIconSize(icon_size)
        self.watch_button.setStyleSheet(qt_stylesheet_button_icon)
        self.update_watch_ui(self.watch_enabled)

        self.play_button = QPushButton()
        self.open_button = QPushButton()
        self.open_ref_button = QPushButton()

        for btn, icon, tip in [
            (self.play_button, ":/valve_common/icons/tools/common/control_play.png", "Process batch file"),
            (self.open_button, ":/valve_common/icons/tools/common/edit.png", "Open config in editor"),
            (self.open_ref_button, ":/valve_common/icons/tools/common/browse.png", "Open reference asset in CS2 Tools"),
        ]:
            btn.setFixedSize(button_size)
            btn.setIconSize(icon_size)
            btn.setIcon(QIcon(icon))
            btn.setStyleSheet(qt_stylesheet_button_icon)
            btn.setToolTip(tip)

        layout.addWidget(self.label, 1)
        layout.addWidget(self.watch_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.open_button)
        layout.addWidget(self.open_ref_button)

        self.watch_button.clicked.connect(self.toggle_watch)
        self.play_button.clicked.connect(self.start_process)
        self.open_button.clicked.connect(self.open_file)
        self.open_ref_button.clicked.connect(self.open_reference_asset)

    def toggle_watch(self):
        new_val = not is_watch_enabled(self.file_path)
        self.watch_enabled = new_val
        set_watch_enabled(self.file_path, new_val)
        self.update_watch_ui(new_val)
        self.watch_toggled.emit(self.file_path, new_val)

    def update_watch_ui(self, enabled: bool):
        self.watch_enabled = enabled
        if enabled:
            self.watch_button.setIcon(QIcon(":/icons/visibility_24dp.png"))
            self.watch_button.setToolTip("Watch changes: Enabled (Click to disable auto-processing)")
        else:
            self.watch_button.setIcon(QIcon(":/icons/visibility_off_24dp.png"))
            self.watch_button.setToolTip("Watch changes: Disabled (Click to enable auto-processing)")

    def start_process(self):
        """
        Emit a signal to start processing the file.
        """
        self.process_requested.emit(self.file_path)

    def open_file(self):
        """
        Emit a signal to open the file.
        """
        self.open_requested.emit(self.file_path)

    def open_reference_asset(self):
        """
        Open the reference asset in CS2 tools via netcon open_asset command.
        """
        asset_path = get_reference_asset_path(self.file_path)
        if not asset_path:
            QMessageBox.warning(self, "No Reference Asset", f"No reference asset found in '{os.path.basename(self.file_path)}'.")
            return

        command = f"open_asset {asset_path}"
        debug(f"[AssetGroupMaker] Sending CS2 command: {command}")
        if CS2Netcon is None or not CS2Netcon.send(command):
            QMessageBox.warning(
                self,
                "CS2 Not Reachable",
                "Could not send command to CS2.\n"
                "Make sure CS2 is running with -netconport 2121."
            )
        else:
            self.open_reference_requested.emit(asset_path)
            curr = self.parentWidget() if hasattr(self, 'parentWidget') else self.parent()
            while curr is not None:
                if hasattr(curr, 'update_title') and callable(curr.update_title):
                    curr.update_title(text=f"Opened reference asset [{asset_path}] in CS2 Tools")
                    break
                if hasattr(curr, 'parentWidget') and callable(curr.parentWidget):
                    curr = curr.parentWidget()
                elif hasattr(curr, 'parent'):
                    curr = curr.parent() if callable(curr.parent) else curr.parent
                else:
                    curr = None

    def contextMenuEvent(self, event):
        """
        Create a context menu for additional actions.
        """
        menu = QMenu(self)
        open_ref_action = QAction("Open Reference Asset", self)
        open_ref_action.setIcon(QIcon(":/valve_common/icons/tools/common/browse.png"))
        open_ref_action.triggered.connect(self.open_reference_asset)
        menu.addAction(open_ref_action)

        menu.addSeparator()

        open_folder_action = QAction("Open Folder", self)
        open_folder_action.triggered.connect(self.open_folder)
        menu.addAction(open_folder_action)
        menu.exec(event.globalPos())

    def open_folder(self):
        """
        Open the folder containing the file.
        """
        folder_path = os.path.dirname(self.file_path)
        os.startfile(folder_path)


class MonitoringFileWatcher(QListWidget):
    """
    Widget to monitor file changes and manage file processing, enforcing an exact folder match.
    It collects all .hbat files under the root path from allowed folders, validates referenced files before processing,
    and uses a 500ms debounce delay for updates.
    """
    open_file = Signal(str)
    watch_status_changed = Signal(str, bool)
    _instances: List['MonitoringFileWatcher'] = []

    def __init__(self, root_path: str):
        super().__init__()
        if self not in MonitoringFileWatcher._instances:
            MonitoringFileWatcher._instances.append(self)
        self.root_path: Path = Path(root_path)
        self.file_system_watcher = QFileSystemWatcher(self)
        self.file_widgets: Dict[str, Tuple[QListWidgetItem, FileItemWidget]] = {}
        self.config_references: Dict[str, str] = {}
        self.reference_configs: Dict[str, set] = {}
        self.process_threads: Dict[str, StartProcess] = {}
        self.watched_directories: set = set()
        self._global_watch_enabled: bool = True

        # Debounce timer for update delays (500ms)
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(500)
        self.debounce_timer.timeout.connect(self.update_file_list)

        self.setAlternatingRowColors(True)
        self.initialize_watcher()
        self.setStyleSheet(qt_stylesheet_widgetlist)

    def set_global_watch_enabled(self, enabled: bool):
        self._global_watch_enabled = enabled
        debug(f"[MonitoringFileWatcher] Global watch set to: {enabled}")

    def is_global_watch_enabled(self) -> bool:
        return self._global_watch_enabled

    def update_watch_status(self, config_path: str, enabled: bool):
        path = os.path.normpath(config_path)
        if path in self.file_widgets:
            _, widget = self.file_widgets[path]
            widget.update_watch_ui(enabled)

    @classmethod
    def notify_new_file(cls, file_path: str):
        """
        Notify all active MonitoringFileWatcher instances about a newly created or modified .hbat file.
        """
        file_path = os.path.normpath(str(file_path))
        for instance in list(cls._instances):
            try:
                instance.track_new_file(file_path)
            except Exception as e:
                debug(f"Error notifying watcher of new file {file_path}: {e}")

    def initialize_watcher(self):
        """
        Initialize the file system watcher for the root path using optimized scanning.
        """
        if not self.root_path.exists() or not self.root_path.is_dir():
            debug("Invalid root path provided to MonitoringFileWatcher.")
            return

        # Watch the root directory; additional directories will be added later if necessary.
        self.add_directory_watch(str(self.root_path))
        self.update_file_list()
        self.file_system_watcher.directoryChanged.connect(self.on_directory_changed)
        self.file_system_watcher.fileChanged.connect(self.on_file_changed)

    def add_directory_watch(self, directory: str):
        """
        Add a directory to the file system watcher if not already watched.
        """
        directory = os.path.normpath(directory)
        if directory not in self.watched_directories and os.path.isdir(directory):
            self.file_system_watcher.addPath(directory)
            self.watched_directories.add(directory)

    def remove_directory_watch(self, directory: str):
        """
        Remove a directory from the file system watcher.
        """
        directory = os.path.normpath(directory)
        if directory in self.watched_directories:
            if directory in self.file_system_watcher.directories():
                self.file_system_watcher.removePath(directory)
            self.watched_directories.remove(directory)

    def is_file_in_allowed_folder(self, file_path: str) -> bool:
        """
        Check if the file is in one of the allowed folders.
        Allowed folders are retrieved from configuration 'AssetGroupMaker/monitor_folders'.
        Only files whose relative path (from the add-on directory) contains one of the allowed folder names are accepted.
        """
        allowed = get_settings_value('AssetGroupMaker', 'monitor_folders') or "models, materials, smartprops"
        allowed_set = {x.strip().lower() for x in allowed.split(',') if x.strip()}
        addon_dir = get_addon_dir()
        if not addon_dir:
            return False
        try:
            relative_path = os.path.relpath(file_path, addon_dir)
        except Exception as e:
            debug(f"Error obtaining relative path for {file_path}: {e}")
            return False
        path_parts = relative_path.replace('\\', '/').split('/')
        for folder in path_parts:
            if folder.lower() in allowed_set:
                return True
        return False

    def collect_hbat_files(self) -> List[str]:
        """
        Collect all .hbat files under the root path from allowed folders.
        Uses os.scandir for a faster directory traversal.
        """
        collected_files = []

        def scan_dir(path: Path):
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        entry_path = Path(entry.path)
                        dir_str = str(entry_path)
                        if entry.is_dir(follow_symlinks=False):
                            if self.is_file_in_allowed_folder(dir_str):
                                self.add_directory_watch(dir_str)
                            scan_dir(entry_path)
                        elif entry.is_file() and entry.name.lower().endswith('.hbat') and self.is_file_in_allowed_folder(dir_str):
                            collected_files.append(os.path.normpath(dir_str))
            except OSError as e:
                debug(f"Error scanning directory {path}: {e}")

        scan_dir(self.root_path)
        debug(f"Collected {len(collected_files)} .hbat files in allowed folders.")
        return collected_files

    def update_file_list(self):
        """
        Update the list of file widgets based on current .hbat files in allowed folders of the project.
        """
        current_files = set(self.file_widgets.keys())
        found_files = set(self.collect_hbat_files())

        new_files = found_files - current_files
        removed_files = current_files - found_files

        for path in new_files:
            self.add_file_widget(path)
        for path in removed_files:
            self.remove_file_widget(path)
        for path in found_files & current_files:
            self.update_reference(path)

        # Add new directories from found files if not already watched.
        for file_path in found_files:
            directory = os.path.dirname(file_path)
            self.add_directory_watch(directory)

    def track_new_file(self, file_path: str) -> bool:
        """
        Public method to allow external modules (like the assetgroup maker main file or src.explorer)
        to add a new file to tracking immediately.
        Returns True if the file was added, False otherwise.
        """
        file_path = os.path.normpath(str(Path(file_path)))
        if not file_path.lower().endswith('.hbat'):
            return False

        if not self.is_file_in_allowed_folder(file_path):
            return False

        # Ensure the parent directory is watched
        self.add_directory_watch(os.path.dirname(file_path))

        if file_path not in self.file_widgets:
            self.add_file_widget(file_path)
            return True
        else:
            self.update_reference(file_path)
            return True

    def add_file_widget(self, path: str):
        """
        Add a file widget for a new .hbat file.
        """
        path = os.path.normpath(path)
        if path in self.file_widgets:
            return
        item = QListWidgetItem(self)
        widget = FileItemWidget(path)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)
        self.file_widgets[path] = (item, widget)

        widget.open_requested.connect(self.open_file.emit)
        widget.process_requested.connect(self.start_processing)
        widget.watch_toggled.connect(self.watch_status_changed.emit)

        # Ensure parent directory is watched
        self.add_directory_watch(os.path.dirname(path))

        # Watch the file for changes if not already watched.
        if os.path.isfile(path) and path not in self.file_system_watcher.files():
            self.file_system_watcher.addPath(path)
        self.update_reference(path)

    def remove_file_widget(self, path: str):
        """
        Remove a file widget for a deleted or disallowed .hbat.
        """
        path = os.path.normpath(path)
        self.stop_processing(path)
        if path in self.file_system_watcher.files():
            self.file_system_watcher.removePath(path)
        item, _ = self.file_widgets.pop(path, (None, None))
        if item:
            self.takeItem(self.row(item))
        self.untrack_reference(path)

    def update_reference(self, config_path: str):
        """
        Update the reference path for a .hbat file. Validate the referenced file
        and track it if valid.
        """
        config_path = os.path.normpath(config_path)
        reference_path = read_reference_from_file(config_path)
        if reference_path:
            reference_path = os.path.normpath(reference_path)
            if validate_reference_file(reference_path):
                self.track_reference(config_path, reference_path)
            else:
                self.untrack_reference(config_path)
        else:
            self.untrack_reference(config_path)

    def track_reference(self, config_path: str, reference_path: str):
        """
        Track a reference path for a configuration file and watch it.
        """
        config_path = os.path.normpath(config_path)
        reference_path = os.path.normpath(reference_path)
        old_ref = self.config_references.get(config_path)
        if old_ref and old_ref != reference_path:
            self.untrack_reference(config_path)
        self.config_references[config_path] = reference_path
        if reference_path not in self.reference_configs:
            self.reference_configs[reference_path] = set()
            if os.path.exists(reference_path) and reference_path not in self.file_system_watcher.files():
                self.file_system_watcher.addPath(reference_path)
        self.reference_configs[reference_path].add(config_path)

    def untrack_reference(self, config_path: str):
        """
        Untrack a reference path for a configuration file.
        """
        config_path = os.path.normpath(config_path)
        reference_path = self.config_references.pop(config_path, None)
        if reference_path:
            configs = self.reference_configs.get(reference_path)
            if configs:
                configs.discard(config_path)
                if not configs:
                    self.reference_configs.pop(reference_path, None)
                    if reference_path in self.file_system_watcher.files():
                        self.file_system_watcher.removePath(reference_path)

    def on_directory_changed(self, path: str):
        """
        Handle directory change events using debouncing to minimize rescans.
        """
        debug(f"Directory changed: {path}")
        self.debounce_timer.start(500)

    def on_file_changed(self, path: str):
        """
        Handle file change events.
        For .hbat files or reference files, trigger appropriate updates.
        """
        path = os.path.normpath(path)
        debug(f"File changed: {path}")
        if not self._global_watch_enabled:
            debug(f"[MonitoringFileWatcher] Global watch disabled. Skipping file change processing for: {path}")
            if os.path.exists(path) and path in self.file_widgets:
                self.update_reference(path)
            return

        if os.path.exists(path):
            if os.path.isfile(path) and path not in self.file_system_watcher.files():
                self.file_system_watcher.addPath(path)
            if path in self.file_widgets:
                self.update_reference(path)
                if is_watch_enabled(path):
                    self.stop_processing(path)
                    self.start_processing(path)
            elif path in self.reference_configs:
                configs = list(self.reference_configs[path])
                for config_path in configs:
                    if is_watch_enabled(config_path):
                        self.stop_processing(config_path)
                        self.start_processing(config_path)
        else:
            if path in self.file_widgets:
                self.remove_file_widget(path)
            elif path in self.reference_configs:
                configs = self.reference_configs.pop(path, set())
                for config_path in list(configs):
                    self.config_references.pop(config_path, None)
                    self.stop_processing(config_path)
                if path in self.file_system_watcher.files():
                    self.file_system_watcher.removePath(path)
                    debug(f"Removed non-existent reference: {path}")

    def start_processing(self, config_path: str):
        """
        Start processing a config file using StartProcess.
        Avoid duplicate processing threads.
        """
        config_path = os.path.normpath(config_path)
        if config_path in self.process_threads:
            debug(f"Processing already started for: {config_path}")
            return
        process_thread = StartProcess(config_path)
        process_thread.finished.connect(lambda: self.on_process_finished(config_path))
        process_thread.start()
        self.process_threads[config_path] = process_thread

    def stop_processing(self, config_path: str):
        """
        Stop processing if the thread is running.
        """
        config_path = os.path.normpath(config_path)
        if config_path in self.process_threads:
            thread = self.process_threads.pop(config_path)
            if thread.isRunning():
                thread.stop()
                thread.wait()

    def on_process_finished(self, config_path: str):
        """
        Clean up a finished processing thread.
        """
        config_path = os.path.normpath(config_path)
        self.process_threads.pop(config_path, None)
        debug(f"Finished processing: {config_path}")

    def closeEvent(self, event):
        """
        Gracefully close all running threads and disconnect signals.
        """
        debug("Closing MonitoringFileWatcher.")
        if self in MonitoringFileWatcher._instances:
            MonitoringFileWatcher._instances.remove(self)
        try:
            self.debounce_timer.stop()
            self.file_system_watcher.directoryChanged.disconnect()
            self.file_system_watcher.fileChanged.disconnect()
        except Exception as e:
            debug(f"Error disconnecting signals: {e}")
        for thread in list(self.process_threads.values()):
            if thread.isRunning():
                thread.stop()
                thread.wait()
        event.accept()


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    root = os.getcwd()
    watcher = MonitoringFileWatcher(root)
    watcher.show()
    sys.exit(app.exec())