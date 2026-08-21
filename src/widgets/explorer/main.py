import os
import re
import shutil
import winreg
from PySide6.QtWidgets import QMainWindow, QFileSystemModel, QStyledItemDelegate, QMenu, QMessageBox, \
    QToolButton, QListWidgetItem, QInputDialog, QLineEdit, QFrame, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QListWidget, QApplication
from PySide6.QtGui import QIcon, QAction, QDesktopServices, QMouseEvent, QKeyEvent, QGuiApplication, QPainter, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Signal, Qt, QDir, QMimeData, QUrl, QFile, QFileInfo, QItemSelectionModel, QSortFilterProxyModel, QTimer, QDirIterator
from shiboken6 import isValid

from src.settings.main import get_settings_value, set_settings_value, get_cs2_path, get_addon_name, get_addon_dir, debug
from src.widgets.common import ErrorInfo
from src.widgets.explorer.actions import QuickVmdlFile, QuickConfigFile, QuickProcess, FixPBRRange, QuickVsmart
from src.widgets.tree import BranchTreeView
from src.styles.common import *
from src.common import enable_dark_title_bar

class ZebraMenu(QMenu):
    """QMenu with alternating (zebra-striped) row backgrounds, since QSS has no nth-child selector for QMenu::item."""

    def paintEvent(self, event):
        painter = QPainter(self)
        from src.styles import theme
        even = theme.qcolor("#2f2f31")
        odd = theme.qcolor("#37373c")
        for i, action in enumerate(self.actions()):
            if action.isSeparator():
                continue
            rect = self.actionGeometry(action)
            painter.fillRect(rect, odd if i % 2 else even)
        painter.end()
        super().paintEvent(event)

audio_extensions = ['wav', 'mp3', 'flac', 'aac', 'm4a', 'wma']
smartprop_extensions = ['vsmart', 'vdata']
generic_extensions = ['vpost', 'rect', 'keybindings', 'kv3']
model_extensions = ['obj', 'fbx', 'dmx']

file_icons = {
    '.vsmart': '://icons/tools/assettypes/vsmart_sm.png',
    '.vdata': '://icons/tools/assettypes/vdata_sm.png',
    '.vmat': '://icons/tools/assettypes/material_sm.png',
    '.vmap': '://icons/tools/assettypes/map_sm.png',
    '.hbat': '://icons/tools/assettypes/vcompmat_sm.png',
    '.vtex': '://icons/tools/assettypes/texture_sm.png',
    '.vmdl': '://icons/tools/assettypes/model_sm.png',
    '.vsnd': '://icons/tools/assettypes/vmix_sm.png',
    '.vsndevts': '://icons/tools/assettypes/vmix_sm.png'
}

class CustomFileSystemModel(QFileSystemModel):
    NAME_COLUMN = 0
    SIZE_COLUMN = 1
    CACHE_LIMIT = 5000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = {}
        self._folder_icon = QIcon('://valve_common/icons/tools/common/folder_sm.png')
        self._folder_icon.addFile('://valve_common/icons/tools/common/folder.png')

    def data(self, index, role):
        if role == Qt.DecorationRole and self.isDir(index) and index.column() != self.SIZE_COLUMN:
            return self._folder_icon
        elif role == Qt.DecorationRole and not self.isDir(index) and index.column() == self.NAME_COLUMN:
            file_path = self.filePath(index)
            for ext, icon_path in file_icons.items():
                if file_path.endswith(ext):
                    return QIcon(icon_path)
            if file_path.endswith(tuple(audio_extensions)):
                return QIcon('://icons/tools/assettypes/vmix_sm.png')
            if file_path.endswith(tuple(generic_extensions)):
                return QIcon('://icons/tools/assettypes/generic_sm.png')
        elif role == Qt.DisplayRole and index.column() == self.NAME_COLUMN:
            file_path = self.filePath(index)
            if file_path in self._cache:
                return self._cache[file_path]
            file_name = super().data(index, role)
            if not self.isDir(index):
                file_name = QFileInfo(file_name).completeBaseName()
            self._cache[file_path] = file_name
            if len(self._cache) > self.CACHE_LIMIT:
                self._clean_cache()
            return file_name
        return super().data(index, role)

    def _clean_cache(self):
        self._cache = {}

    def supportedDropActions(self):
        return Qt.MoveAction

    def supportedDragActions(self):
        # CopyAction must be offered so external drop targets (e.g. the SmartProp
        # hierarchy) can accept as a copy — accepting as Move makes the source view
        # removeRows() the dragged files off disk.
        return Qt.CopyAction | Qt.MoveAction

    def mimeTypes(self):
        return ['text/uri-list']

    def mimeData(self, indexes):
        # One index per visible column is selected for each row, so only the name
        # column is taken — otherwise every dragged file is listed once per column.
        mime_data = QMimeData()
        urls = [self.filePath(index) for index in indexes if index.column() == self.NAME_COLUMN]
        mime_data.setUrls([QUrl.fromLocalFile(url) for url in urls])
        return mime_data

    def dropMimeData(self, data, action, row, column, parent):
        if action == Qt.IgnoreAction:
            return True
        if not data.hasUrls():
            return False
        parent_path = self.filePath(parent)
        for url in data.urls():
            source_path = url.toLocalFile()
            file_name = QDir(source_path).dirName()
            destination_path = QDir(parent_path).absoluteFilePath(file_name)
            if QDir(source_path).exists():
                QDir().rename(source_path, destination_path)
            else:
                QFile().rename(source_path, destination_path)
        return True

    def setData(self, index, value, role):
        if role == Qt.EditRole:
            if not value:
                return False
            old_path = self.filePath(index)
            file_info = QFileInfo(old_path)
            file_dir = file_info.dir()
            extension = file_info.suffix()
            debug(f'Renaming file value: {value}')
            new_name = value.replace('.' + extension, '') + ('.' + extension if extension else '')
            new_path = file_dir.absoluteFilePath(new_name)
            if QFile.exists(new_path):
                return False
            if QFile.rename(old_path, new_path):
                if old_path in self._cache:
                    del self._cache[old_path]
                self._cache[new_path] = value
                self.dataChanged.emit(index, index)
                if self.parent() is not None and hasattr(self.parent(), 'select_tree_item'):
                    self.parent().select_tree_item(new_path)
                return True
        return super().setData(index, value, role)

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid() and index.column() == self.NAME_COLUMN:
            return Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | default_flags
        return default_flags

def get_default_application(file_extension):
    """
    Get the default application associated with a file extension on Windows.
    Returns the application name and path, or None if not found.
    """
    try:
        # Remove the dot from extension if present
        if file_extension.startswith('.'):
            file_extension = file_extension[1:]
        
        file_type = None
        
        # 1. Try getting from UserChoice first (Windows 8+)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.{file_extension}\\UserChoice") as key:
                file_type, _ = winreg.QueryValueEx(key, "ProgId")
        except (FileNotFoundError, OSError, winreg.error):
            pass
            
        # 2. Fallback to HKEY_CLASSES_ROOT
        if not file_type:
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f".{file_extension}") as key:
                    file_type, _ = winreg.QueryValueEx(key, "")
            except (FileNotFoundError, OSError, winreg.error):
                return None
        
        if not file_type:
            return None
            
        command = None
        # 3. Get the command associated with the file type
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{file_type}\\shell\\open\\command") as key:
                command, _ = winreg.QueryValueEx(key, "")
        except (FileNotFoundError, OSError, winreg.error):
            # Try alternative path
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{file_type}\\shell\\edit\\command") as key:
                    command, _ = winreg.QueryValueEx(key, "")
            except (FileNotFoundError, OSError, winreg.error):
                pass
        
        if command:
            # Extract the executable path from the command
            # Commands often contain quotes and parameters like: "C:\Program Files\App\app.exe" "%1"
            import shlex
            try:
                parts = shlex.split(command, posix=False)
                if parts:
                    exe_path = parts[0].strip('"')
                    app_name = os.path.basename(exe_path)
                    return app_name, exe_path
            except ValueError:
                # Fallback for malformed commands
                if command.startswith('"'):
                    end_quote = command.find('"', 1)
                    if end_quote != -1:
                        exe_path = command[1:end_quote]
                        app_name = os.path.basename(exe_path)
                        return app_name, exe_path
                else:
                    # Simple case without quotes
                    parts = command.split()
                    if parts:
                        exe_path = parts[0]
                        app_name = os.path.basename(exe_path)
                        return app_name, exe_path
        
        return None
        
    except (FileNotFoundError, OSError, winreg.error):
        return None

class ExplorerFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, root_directory="", parent=None):
        super().__init__(parent)
        self._root_directory = self._normalize_dir(root_directory)
        self._filter_text = ""
        self._matching_dirs = set()
        self._matching_files = set()
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def _normalize_dir(self, path):
        if not path:
            return ""
        return os.path.normpath(path).lower()

    def set_root_directory(self, root_directory: str):
        self._root_directory = self._normalize_dir(root_directory)
        self._matching_dirs.clear()
        self._matching_files.clear()
        if self._filter_text:
            self._rebuild_match_index()
        self.invalidateFilter()

    def set_filter_text(self, text: str):
        new_filter = text.lower().strip()
        if new_filter == self._filter_text:
            return
        self._filter_text = new_filter
        self._rebuild_match_index()
        self.invalidateFilter()

    def _rebuild_match_index(self):
        self._matching_dirs.clear()
        self._matching_files.clear()
        if not self._filter_text or not self._root_directory or not os.path.exists(self._root_directory):
            return

        search_term = self._filter_text.replace('\\', '/')
        has_slash = "/" in search_term

        # Fast single-pass scanner using os.scandir with directory pruning
        def _scan(dir_path):
            try:
                with os.scandir(dir_path) as it:
                    has_match = False
                    for entry in it:
                        name_lower = entry.name.lower()
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name in ("__pycache__", ".git", "node_modules", ".vs"):
                                continue
                            norm_entry = os.path.normpath(entry.path).lower()
                            if has_slash:
                                try:
                                    rel_p = os.path.relpath(norm_entry, self._root_directory).replace('\\', '/').lower()
                                    if search_term in rel_p:
                                        self._matching_dirs.add(norm_entry)
                                        has_match = True
                                except Exception:
                                    pass
                            elif search_term in name_lower:
                                self._matching_dirs.add(norm_entry)
                                has_match = True

                            if _scan(norm_entry):
                                self._matching_dirs.add(norm_entry)
                                has_match = True
                        else:
                            norm_entry = os.path.normpath(entry.path).lower()
                            matched = False
                            if has_slash:
                                try:
                                    rel_p = os.path.relpath(norm_entry, self._root_directory).replace('\\', '/').lower()
                                    matched = (search_term in rel_p)
                                except Exception:
                                    pass
                            else:
                                matched = (search_term in name_lower)

                            if matched:
                                self._matching_files.add(norm_entry)
                                has_match = True
                    return has_match
            except (PermissionError, OSError):
                return False

        _scan(self._root_directory)

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._filter_text:
            return True

        model = self.sourceModel()
        source_index = model.index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False

        file_path = model.filePath(source_index)
        norm_path = os.path.normpath(file_path).lower()

        # 1. Always accept ancestors of the root directory so the root index is never broken
        if self._root_directory:
            if self._root_directory == norm_path:
                return True
            if self._root_directory.startswith(norm_path + os.sep):
                return True
            # Exclude anything completely outside the active root directory
            if not norm_path.startswith(self._root_directory):
                return False

        # 2. O(1) Instant set lookups
        if model.isDir(source_index):
            if norm_path in self._matching_dirs:
                model.fetchMore(source_index)
                return True
            return False
        else:
            return norm_path in self._matching_files

class Explorer(QMainWindow):
    play_sound = Signal(str)

    def __init__(self, parent=None, tree_directory=None, addon=None, editor_name=None, use_internal_player: bool = True, base_directories: dict = None, show_root_selector: bool = True):
        super().__init__(parent)
        self.tree_directory = self._normalize_path(tree_directory)
        if not self.tree_directory:
            self.tree_directory = os.getcwd()
        self.addon = addon
        self.editor_name = editor_name or 'Explorer'
        self.use_internal_player = use_internal_player
        self.base_directories = {label: self._normalize_path(path) for label, path in (base_directories or {}).items()}
        self.show_root_selector = show_root_selector
        self.model = CustomFileSystemModel(self)
        self.model.setRootPath(self.tree_directory)
        cs2_path = get_cs2_path()
        if cs2_path:
            self.rootpath = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
        else:
            self.rootpath = self.tree_directory
        if not os.path.exists(self.tree_directory):
            os.makedirs(self.tree_directory)
        if not self.use_internal_player:
            self.audio_player = None
        self.filter_proxy_model = ExplorerFilterProxyModel(root_directory=self.tree_directory, parent=self)
        self.filter_proxy_model.setSourceModel(self.model)
        self.filter_proxy_model.setFilterKeyColumn(CustomFileSystemModel.NAME_COLUMN)
        self.filter_proxy_model.setDynamicSortFilter(True)
        self.tree = BranchTreeView(self)
        self.tree.setModel(self.filter_proxy_model)
        self.tree.setRootIndex(self.filter_proxy_model.mapFromSource(self.model.index(self.tree_directory)))

        # Debounced expansion timer to prevent repetitive layout calculations
        self._expand_timer = QTimer(self)
        self._expand_timer.setSingleShot(True)
        self._expand_timer.setInterval(30)
        self._expand_timer.timeout.connect(self._expand_all_filtered)

        self.model.directoryLoaded.connect(lambda path: self._expand_timer.start() if self.filter_editline.text().strip() else None)
        self.filter_proxy_model.rowsInserted.connect(lambda *args: self._expand_timer.start() if self.filter_editline.text().strip() else None)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        for column in range(self.model.columnCount()):
            if column not in (CustomFileSystemModel.NAME_COLUMN, CustomFileSystemModel.SIZE_COLUMN):
                self.tree.setColumnHidden(column, True)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QTreeView.InternalMove)
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.doubleClicked.connect(self._on_tree_double_clicked)
        self.tree.viewport().installEventFilter(self)
        self.tree.installEventFilter(self)

        # Debounced filter timer for instant responsive typing
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(120)
        self._filter_timer.timeout.connect(self._apply_filter_debounced)

        self.top_layout = QHBoxLayout()
        self.filter_editline = QLineEdit(self)
        self.filter_editline.setPlaceholderText("Filter files...")
        self.filter_editline.textChanged.connect(lambda text: self._filter_timer.start())
        self.top_layout.addWidget(self.filter_editline)

        if self.base_directories:
            self.root_selector = QComboBox(self)
            for label in self.base_directories:
                self.root_selector.addItem(label)
            
            # Set initial selection to User if available, otherwise Internal
            if "User" in self.base_directories:
                self.root_selector.setCurrentText("User")
                self.tree_directory = self.base_directories["User"]
            elif "Internal" in self.base_directories:
                self.root_selector.setCurrentText("Internal")
                self.tree_directory = self.base_directories["Internal"]

            self.root_selector.currentIndexChanged.connect(self.on_root_changed)
            if self.show_root_selector:
                self.top_layout.addWidget(self.root_selector)
        self.goto_button = QToolButton(self)
        self.goto_button.setIcon(QIcon("://icons/folder_open.svg"))
        self.goto_button.setToolTip("Go to path from clipboard")
        self.goto_button.clicked.connect(self.goto_clipboard_path)
        self.goto_button.setMaximumHeight(26)
        self.goto_button.setMaximumWidth(26)
        self.goto_button.setStyleSheet(qt_stylesheet_toolbutton)
        self.top_layout.addWidget(self.goto_button)
        self.recent_button = QToolButton(self)
        self.recent_button.setIcon(QIcon("://icons/acute_24dp.svg"))
        self.recent_button.setToolTip("Show recent files")
        self.recent_button.setStyleSheet(qt_stylesheet_toolbutton)
        self.recent_button.setMaximumHeight(26)
        self.recent_button.setMaximumWidth(26)
        self.recent_button.clicked.connect(lambda: self._toggle_panel("recent"))
        self.top_layout.addWidget(self.recent_button)
        self.favorites_button = QToolButton(self)
        self.favorites_button.setIcon(QIcon("://icons/bookmark_24dp.svg"))
        self.favorites_button.setToolTip("Show favorites")
        self.favorites_button.setStyleSheet(qt_stylesheet_toolbutton)
        self.favorites_button.setMaximumHeight(26)
        self.favorites_button.setMaximumWidth(26)
        self.favorites_button.clicked.connect(lambda: self._toggle_panel("favorites"))
        self.top_layout.addWidget(self.favorites_button)
        self._panel_mode = None  # "recent" or "favorites"
        self._panel_frame = self._build_panel()
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.top_layout)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.tree.setItemDelegateForColumn(CustomFileSystemModel.SIZE_COLUMN, QStyledItemDelegate())
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(CustomFileSystemModel.NAME_COLUMN, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(CustomFileSystemModel.SIZE_COLUMN, QHeaderView.Interactive)
        self.tree.header().setSortIndicator(CustomFileSystemModel.NAME_COLUMN, Qt.AscendingOrder)
        self.tree.selectionModel().currentChanged.connect(self.on_directory_changed)
        tree_state = get_settings_value(self.editor_name + '_tree_state', self.addon)
        if tree_state:
            self.tree.header().restoreState(tree_state)
        self.recent_files = self.load_recent_files()
        self.favorites = self.load_favorites()
        self.select_last_opened_path()
        self.frame = QFrame(self)
        self.frame.setLayout(self.layout)

    def get_selected_files(self):
        indexes = self.tree.selectionModel().selectedIndexes()
        selected_paths = []
        for idx in indexes:
            if idx.column() == CustomFileSystemModel.NAME_COLUMN:
                src_idx = self.filter_proxy_model.mapToSource(idx)
                selected_paths.append(self.model.filePath(src_idx))
        return selected_paths

    def _normalize_path(self, path):
        if path is None:
            return None
        try:
            return os.fspath(path)
        except (TypeError, ValueError):
            return None

    def on_root_changed(self, index):
        label = self.root_selector.itemText(index)
        new_path = self.base_directories.get(label)
        if new_path and os.path.exists(new_path):
            self.tree_directory = new_path
            self.filter_proxy_model.set_root_directory(new_path)
            self.model.setRootPath(new_path)
            source_index = self.model.index(new_path)
            self.tree.setRootIndex(self.filter_proxy_model.mapFromSource(source_index))
            debug(f"Explorer root changed to: {new_path}")

    def _apply_filter_debounced(self):
        if hasattr(self, 'filter_editline') and isValid(self.filter_editline):
            self.update_filter(self.filter_editline.text())

    def update_filter(self, text):
        self.filter_proxy_model.set_filter_text(text)
        source_index = self.model.index(self.tree_directory)
        self.tree.setRootIndex(self.filter_proxy_model.mapFromSource(source_index))
        if text.strip() != "":
            self._expand_all_filtered()

    def _expand_all_filtered(self):
        if not hasattr(self, 'filter_editline') or not self.filter_editline.text().strip():
            return
        if hasattr(self, 'tree') and isValid(self.tree):
            self.tree.expandAll()

    def add_recent_file(self, path):
        if not path:
            return
        normalized_path = os.path.normpath(path)
        recent = self.load_recent_files()
        normalized_recent = [os.path.normpath(p) for p in recent if p]
        if normalized_path in normalized_recent:
            index = normalized_recent.index(normalized_path)
            recent.pop(index)
        recent.insert(0, normalized_path)
        if len(recent) > 30:
            recent = recent[:30]
        set_settings_value(self.editor_name + '_recent_files', self.addon, recent)
        self.recent_files = recent

    def load_recent_files(self):
        rf = get_settings_value(self.editor_name + '_recent_files', self.addon)
        if rf is None:
            return []
        return rf if isinstance(rf, list) else []

    def save_recent_files(self):
        set_settings_value(self.editor_name + '_recent_files', self.addon, self.recent_files)

    def add_favorite(self, path):
        if not path:
            return
        normalized_path = os.path.normpath(path)
        favs = self.load_favorites()
        normalized_favs = [os.path.normpath(p) for p in favs if p]
        if normalized_path not in normalized_favs:
            favs.append(normalized_path)
            set_settings_value(self.editor_name + '_favorites', self.addon, favs)
            self.favorites = favs

    def load_favorites(self):
        favs = get_settings_value(self.editor_name + '_favorites', self.addon)
        if favs is None:
            return []
        return favs if isinstance(favs, list) else []

    def save_favorites(self):
        set_settings_value(self.editor_name + '_favorites', self.addon, self.favorites)

    def resolve_path(self, path: str) -> str | None:
        """
        Resolves an absolute or relative path to an existing filesystem path within
        the explorer's scope (active tree directory, base directories, addon dir, CS2 mounts).
        """
        if not path:
            return None

        path_str = str(path).strip().strip('\'"')
        if not path_str:
            return None

        # Convert file:// URL to local file path if applicable
        if path_str.startswith(('file:///', 'file://')):
            url = QUrl(path_str)
            if url.isValid() and url.isLocalFile():
                path_str = url.toLocalFile()
            else:
                path_str = path_str.replace('file:///', '').replace('file://', '')

        # Standardize slashes
        norm_input = os.path.normpath(path_str)

        # 1. Check if direct path exists as absolute path
        # On Windows, os.path.isabs('/models/...') returns True even without a drive letter.
        # Check splitdrive to ensure it actually has a drive letter or UNC prefix.
        drive, _ = os.path.splitdrive(norm_input)
        if drive and os.path.exists(norm_input):
            return norm_input

        # Check compiled/source swap for absolute path (e.g. .vmdl_c -> .vmdl or game -> content)
        if drive:
            candidates = []
            if norm_input.endswith(('_c', '.vmdl_c', '.vmat_c', '.vsnd_c', '.vtex_c', '.vsmart_c', '.vpcf_c')):
                candidates.append(re.sub(r'_c$', '', norm_input))
            if f"{os.sep}game{os.sep}" in norm_input:
                content_path = norm_input.replace(f"{os.sep}game{os.sep}", f"{os.sep}content{os.sep}")
                candidates.append(content_path)
                if content_path.endswith(('_c', '.vmdl_c', '.vmat_c', '.vsnd_c', '.vtex_c', '.vsmart_c', '.vpcf_c')):
                    candidates.append(re.sub(r'_c$', '', content_path))
            for cand in candidates:
                if os.path.exists(cand):
                    return cand

        # 2. Treat as relative path
        clean_rel = path_str.replace('/', os.sep).replace('\\', os.sep).lstrip(os.sep)

        rel_variations = [clean_rel]
        if clean_rel.endswith(('_c', '.vmdl_c', '.vmat_c', '.vsnd_c', '.vtex_c', '.vsmart_c', '.vpcf_c')):
            rel_variations.append(re.sub(r'_c$', '', clean_rel))

        # Strip common container prefixes if user copied e.g. "content/csgo_addons/addon_name/models/..."
        for prefix in ['content' + os.sep, 'game' + os.sep]:
            if clean_rel.lower().startswith(prefix):
                stripped = clean_rel[len(prefix):]
                rel_variations.append(stripped)
                if stripped.lower().startswith('csgo_addons' + os.sep):
                    parts = stripped.split(os.sep)
                    if len(parts) > 2:
                        rel_variations.append(os.sep.join(parts[2:]))

        if clean_rel.lower().startswith('csgo_addons' + os.sep):
            parts = clean_rel.split(os.sep)
            if len(parts) > 2:
                rel_variations.append(os.sep.join(parts[2:]))

        unique_variations = []
        for var in rel_variations:
            if var and var not in unique_variations:
                unique_variations.append(var)

        # Candidate base directories
        base_dirs = []

        if hasattr(self, 'tree_directory') and self.tree_directory:
            base_dirs.append(self.tree_directory)

        if hasattr(self, 'base_directories') and self.base_directories:
            for label, bdir in self.base_directories.items():
                if bdir and bdir not in base_dirs:
                    base_dirs.append(bdir)

        try:
            addon_dir = get_addon_dir()
            if addon_dir and addon_dir not in base_dirs:
                base_dirs.append(addon_dir)
        except Exception:
            pass

        if hasattr(self, 'rootpath') and self.rootpath and self.rootpath not in base_dirs:
            base_dirs.append(self.rootpath)

        try:
            cs2_path = get_cs2_path()
            if cs2_path:
                addon_name = self.addon or get_addon_name()
                if addon_name:
                    addon_content = os.path.join(cs2_path, "content", "csgo_addons", addon_name)
                    if addon_content not in base_dirs:
                        base_dirs.append(addon_content)
                    addon_game = os.path.join(cs2_path, "game", "csgo_addons", addon_name)
                    if addon_game not in base_dirs:
                        base_dirs.append(addon_game)

                for mount in ["csgo", "csgo_imported", "csgo_core", "core"]:
                    c_mount = os.path.join(cs2_path, "content", mount)
                    if c_mount not in base_dirs:
                        base_dirs.append(c_mount)
                    g_mount = os.path.join(cs2_path, "game", mount)
                    if g_mount not in base_dirs:
                        base_dirs.append(g_mount)

                if cs2_path not in base_dirs:
                    base_dirs.append(cs2_path)
        except Exception:
            pass

        for bdir in base_dirs:
            if not os.path.exists(bdir):
                continue
            bdir_name = os.path.basename(os.path.normpath(bdir)).lower()
            for var in unique_variations:
                cand = os.path.normpath(os.path.join(bdir, var))
                if os.path.exists(cand):
                    return cand

                var_parts = var.split(os.sep)
                if len(var_parts) > 1 and var_parts[0].lower() == bdir_name:
                    sub_cand = os.path.normpath(os.path.join(bdir, *var_parts[1:]))
                    if os.path.exists(sub_cand):
                        return sub_cand

                parent_cand = os.path.normpath(os.path.join(os.path.dirname(bdir), var))
                if os.path.exists(parent_cand):
                    return parent_cand

        return None

    def select_tree_item(self, path):
        target_path = self.resolve_path(path)
        if not target_path:
            target_path = self._normalize_path(path)
            if target_path and not os.path.exists(target_path):
                norm_path = target_path.replace('/', '\\')
                if os.path.exists(norm_path):
                    target_path = norm_path
                else:
                    debug("select_tree_item: path does not exist - %s" % path)
                    return
            elif not target_path:
                return

        # If the target path belongs to a different base directory, switch the root selector if available
        if hasattr(self, 'base_directories') and self.base_directories and hasattr(self, 'root_selector'):
            norm_target = os.path.normcase(os.path.normpath(target_path))
            for label, bdir in self.base_directories.items():
                if bdir and norm_target.startswith(os.path.normcase(os.path.normpath(bdir))):
                    if self.root_selector.currentText() != label:
                        self.root_selector.setCurrentText(label)
                    break

        self.add_recent_file(target_path)
        source_index = self.model.index(target_path)
        if not source_index.isValid():
            debug("select_tree_item: invalid index for path - %s" % target_path)
            return

        proxy_index = self.filter_proxy_model.mapFromSource(source_index)

        # If proxy index is invalid because an active filter hides this item, clear the filter
        if not proxy_index.isValid() and hasattr(self, 'filter_editline') and self.filter_editline.text():
            self.filter_editline.clear()
            proxy_index = self.filter_proxy_model.mapFromSource(source_index)

        if not proxy_index.isValid():
            debug("select_tree_item: invalid proxy index for path - %s" % target_path)
            return

        # Ensure all parents are expanded
        parent_index = proxy_index.parent()
        while parent_index.isValid():
            self.tree.expand(parent_index)
            parent_index = parent_index.parent()

        selection_model = self.tree.selectionModel()
        selection_model.clear()
        selection_model.select(proxy_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.tree.setCurrentIndex(proxy_index)

        # Use singleShot to allow the UI to process expansion before scrolling.
        # Re-resolve indices by target_path at callback time to avoid dangling QModelIndex pointers.
        QTimer.singleShot(50, lambda: self._safe_scroll_to_path(target_path))
        self.tree.setFocus()

    def _safe_scroll_to_path(self, target_path: str):
        if not isValid(self) or not hasattr(self, 'tree') or not isValid(self.tree):
            return
        if not hasattr(self, 'model') or not isValid(self.model):
            return
        if not hasattr(self, 'filter_proxy_model') or not isValid(self.filter_proxy_model):
            return
        source_index = self.model.index(target_path)
        if source_index.isValid():
            proxy_index = self.filter_proxy_model.mapFromSource(source_index)
            if proxy_index.isValid():
                parent_index = proxy_index.parent()
                while parent_index.isValid():
                    self.tree.expand(parent_index)
                    parent_index = parent_index.parent()
                self.tree.scrollTo(proxy_index, QTreeView.PositionAtCenter)

    def select_last_opened_path(self):
        try:
            last_opened_path = get_settings_value(self.editor_name + '_explorer_lath_path', self.addon)
            if last_opened_path:
                self.select_tree_item(last_opened_path)
        except Exception as e:
            error_dialog = ErrorInfo(text="Selection Error", details=str(e))
            error_dialog.exec_()

    def save_current_path(self, path):
        set_settings_value(self.editor_name + '_explorer_lath_path', self.addon, path)

    def on_directory_changed(self, current, previous):
        current_path = self.model.filePath(self.filter_proxy_model.mapToSource(current))
        self.save_current_path(current_path)
        if not os.path.isdir(current_path):
            self.play_audio_file(current_path)

    def play_audio_file(self, file_path):
        debug(f"Playing {file_path}")
        if file_path.endswith(tuple(audio_extensions)):
            if self.use_internal_player:
                self.play_sound.emit(file_path)
            else:
                try:
                    if self.audio_player is not None:
                        self.audio_player.deleteLater()
                    self.audio_player = QMediaPlayer()
                    self.audio_output = QAudioOutput()
                    self.audio_player.setAudioOutput(self.audio_output)
                    self.audio_player.setSource(QUrl.fromLocalFile(file_path))
                    self.audio_player.play()
                except Exception as e:
                    error_dialog = ErrorInfo(text="Audio Playback Error", details=str(e))
                    error_dialog.exec_()

    def eventFilter(self, source, event):
        if event.type() == QMouseEvent.MouseButtonPress:
            if event.button() in (Qt.LeftButton, Qt.RightButton):
                index = self.tree.indexAt(event.pos())
                if not index.isValid():
                    self.tree.clearSelection()
        elif event.type() == QKeyEvent.KeyPress and event.key() == Qt.Key_Delete:
            if self.tree.selectionModel().hasSelection():
                self.delete_selected_items()
        return super().eventFilter(source, event)

    def open_context_menu(self, position):
        index = self.tree.indexAt(position)
        menu = ZebraMenu()
        if index.isValid():
            source_index = self.filter_proxy_model.mapToSource(index)
            if self.model.isDir(source_index):
                self.add_folder_actions(menu, source_index)
            else:
                self.add_file_actions(menu, source_index)
            favorite_action = QAction("Add to Favorites", self)
            favorite_action.setIcon(QIcon(":/icons/bookmarks_16dp.svg"))
            favorite_action.triggered.connect(lambda: self.add_favorite(self.model.filePath(source_index)))
            menu.addAction(favorite_action)
        else:
            create_folder_action = QAction("Create Folder", self)
            create_folder_action.setIcon(QIcon(":/icons/create_new_folder_16dp.svg"))
            create_folder_action.triggered.connect(lambda: self.create_folder(self.model.index(self.tree_directory)))
            menu.addAction(create_folder_action)
            paste_action = QAction("Paste File", self)
            paste_action.setIcon(QIcon(":/icons/content_paste_24dp.svg"))
            paste_action.triggered.connect(lambda: self.paste_file(self.model.index(self.tree_directory)))
            menu.addAction(paste_action)
        menu.adjustSize()
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_folder_actions(self, menu, index):
        from src.forms.quick_create.main import QuickCreateDialog
        from src.common import compile as run_compile
        folder_path = self.model.filePath(index)

        # --- Navigation ---
        menu.addSection("Folder")
        open_folder_action = QAction("Open in Explorer", self)
        open_folder_action.setIcon(QIcon(":/icons/folder_open.svg"))
        open_folder_action.triggered.connect(lambda: self.open_folder_in_explorer(index))
        menu.addAction(open_folder_action)

        menu.addSection("Create")
        new_folder_action = QAction("New Folder", self)
        new_folder_action.setIcon(QIcon(":/icons/create_new_folder_16dp.svg"))
        new_folder_action.triggered.connect(lambda: self.create_folder(index))
        menu.addAction(new_folder_action)

        quick_batch_action = QAction("Quick AssetGroup file", self)
        quick_batch_action.setIcon(QIcon(":/icons/tools/assettypes/vcompmat_sm.png"))
        quick_batch_action.triggered.connect(lambda: QuickCreateDialog(folder_path, "hbat", self).exec_())
        menu.addAction(quick_batch_action)

        menu.addSection("Process")
        quick_process_action = QAction("Quick Process AssetGroup folder", self)
        quick_process_action.setIcon(QIcon(":/icons/auto_towing_16dp.svg"))
        quick_process_action.triggered.connect(lambda: (run_compile(os.path.join(folder_path, "*.vmdl")), run_compile(os.path.join(folder_path, "*.vmat"))))
        menu.addAction(quick_process_action)

        menu.addSection("Organize")
        paste_action = QAction("Paste File", self)
        paste_action.setIcon(QIcon(":/icons/content_paste_24dp.svg"))
        paste_action.triggered.connect(lambda: self.paste_file(index))
        menu.addAction(paste_action)

        asset_manager_action = QAction("Move Assets", self)
        asset_manager_action.setIcon(QIcon(":/icons/folder_open.svg"))
        asset_manager_action.triggered.connect(lambda: self.open_asset_manager(index))
        menu.addAction(asset_manager_action)

        rename_asset_action = QAction("Rename Asset", self)
        rename_asset_action.setIcon(QIcon(":/icons/edit_document_16dp.svg"))
        rename_asset_action.triggered.connect(lambda: self.open_asset_renamer(index))
        menu.addAction(rename_asset_action)

        export_action = QAction("Export Asset", self)
        export_action.setIcon(QIcon(":/icons/file_open_16dp.svg"))
        export_action.triggered.connect(lambda: self.open_asset_exporter(index))
        menu.addAction(export_action)

        delete_folder_action = QAction("Delete Folder", self)
        delete_folder_action.setIcon(QIcon(":/icons/delete_16dp.svg"))
        delete_folder_action.triggered.connect(lambda: self.delete_item(index))
        menu.addAction(delete_folder_action)

    def add_file_actions(self, menu, index):
        from src.common import compile as run_compile
        file_path = self.model.filePath(index)
        file_extension = file_path.split('.')[-1].lower()
        image_extensions = ["png", "tga", "jpg", "jpeg", "tif", "tiff"]

        # Open
        menu.addSection("Open")
        if file_extension == "hbat":
            open_config_action = QAction("Open AssetGroup Config", self)
            open_config_action.setIcon(QIcon(file_icons['.hbat']))
            open_config_action.triggered.connect(lambda: self.open_config(file_path))
            menu.addAction(open_config_action)

            open_ref_action = QAction("Open Reference Asset", self)
            open_ref_action.setIcon(QIcon(":/valve_common/icons/tools/common/browse.png"))
            open_ref_action.triggered.connect(lambda: self.open_reference_asset(file_path))
            menu.addAction(open_ref_action)

        if file_extension == "vsmart":
            open_vsmart_action = QAction("Open SmartProp", self)
            open_vsmart_action.setIcon(QIcon(file_icons['.vsmart']))
            open_vsmart_action.triggered.connect(lambda: self.open_vsmart(file_path))
            menu.addAction(open_vsmart_action)

        if file_extension == "vsndevts":
            open_vsndevts_action = QAction("Open SoundEvent", self)
            open_vsndevts_action.setIcon(QIcon(file_icons['.vsndevts']))
            open_vsndevts_action.triggered.connect(lambda: self.open_vsndevts(file_path))
            menu.addAction(open_vsndevts_action)

        default_app = get_default_application(file_extension)
        if default_app:
            app_name, app_path = default_app
            open_action = QAction(f"Open with {app_name.replace('.exe', '')}", self)
        else:
            open_action = QAction("Open File", self)
        open_action.setIcon(QIcon(":/icons/file_open_16dp.svg"))
        open_action.triggered.connect(lambda: self.open_file(index))
        menu.addAction(open_action)

        if default_app and 'hammer5tools' in default_app[0].lower():
            import subprocess
            open_notepad_action = QAction("Open with Notepad", self)
            open_notepad_action.setIcon(QIcon(":/icons/edit_document_16dp.svg"))
            open_notepad_action.triggered.connect(lambda checked=False, p=file_path: subprocess.Popen(['notepad.exe', p]))
            menu.addAction(open_notepad_action)

        open_path_action = QAction("Open File Folder", self)
        open_path_action.setIcon(QIcon(":/icons/folder_open.svg"))
        open_path_action.triggered.connect(lambda: self.open_path_file(index))
        menu.addAction(open_path_action)

        # --- Quick Actions (type-specific, Source 2 compiled assets only) ---
        has_quick = (
            file_extension in model_extensions or
            file_extension in ("vmdl", "vmat", "hbat") or
            file_extension in smartprop_extensions or
            file_extension == "vsndevts"
        )
        if has_quick:
            menu.addSection("Quick Actions")

            if file_extension in model_extensions:
                # Mesh files: only useful action is generating a .vmdl stub
                quick_vmdl_action = QAction("Quick create vmdl", self)
                quick_vmdl_action.setIcon(QIcon(":/icons/tools/assettypes/model_sm.png"))
                quick_vmdl_action.triggered.connect(lambda: QuickVmdlFile(file_path))
                menu.addAction(quick_vmdl_action)

            if file_extension == "vmdl":
                quick_config_action = QAction("Quick AssetGroup file", self)
                quick_config_action.setIcon(QIcon(":/icons/edit_document_16dp.svg"))
                quick_config_action.triggered.connect(lambda: QuickConfigFile(file_path))
                menu.addAction(quick_config_action)

            if file_extension in ("vmdl", "vmat") or file_extension in smartprop_extensions or file_extension == "vsndevts":
                quick_process_action = QAction("Quick Process file", self)
                quick_process_action.setIcon(QIcon(":/icons/auto_towing_16dp.svg"))
                quick_process_action.triggered.connect(lambda: run_compile(file_path))
                menu.addAction(quick_process_action)

            quick_vsmart_action = QAction("Quick VSmart", self)
            quick_vsmart_action.setIcon(QIcon(file_icons['.vsmart']))
            quick_vsmart_action.triggered.connect(lambda checked=False, p=file_path: QuickVsmart(self.get_selected_files() or [p]))
            menu.addAction(quick_vsmart_action)

            if file_extension == "hbat":
                quick_process_action = QAction("Quick Process AssetGroup", self)
                quick_process_action.setIcon(QIcon(":/icons/auto_towing_16dp.svg"))
                quick_process_action.triggered.connect(lambda: QuickProcess(filepath=file_path).process())
                menu.addAction(quick_process_action)

        # Fix PBR Range for images (standalone utility, not a compile action)
        if file_extension in image_extensions:
            menu.addSection("Image Tools")
            fix_pbr_action = QAction("Fix PBR Range", self)
            fix_pbr_action.setIcon(QIcon(":/icons/contrast_24dp.png"))
            fix_pbr_action.triggered.connect(lambda: FixPBRRange(file_path))
            menu.addAction(fix_pbr_action)

        # --- Audio Tools (convert between wav/mp3) ---
        if file_extension in ("mp3", "wav"):
            menu.addSection("Audio Tools")
            target = "wav" if file_extension == "mp3" else "mp3"
            convert_action = QAction(f"Convert to {target.upper()}", self)
            convert_action.setIcon(QIcon(":/icons/auto_towing_16dp.svg"))
            convert_action.triggered.connect(
                lambda checked=False, p=file_path, t=target: self.convert_audio_file(p, t)
            )
            menu.addAction(convert_action)

        menu.addSection("Organize")
        asset_manager_action = QAction("Move Assets", self)
        asset_manager_action.setIcon(QIcon(":/icons/folder_open.svg"))
        asset_manager_action.triggered.connect(lambda: self.open_asset_manager(index))
        menu.addAction(asset_manager_action)

        rename_asset_action = QAction("Rename Asset", self)
        rename_asset_action.setIcon(QIcon(":/icons/edit_document_16dp.svg"))
        rename_asset_action.triggered.connect(lambda: self.open_asset_renamer(index))
        menu.addAction(rename_asset_action)

        export_action = QAction("Export Asset", self)
        export_action.setIcon(QIcon(":/icons/file_open_16dp.svg"))
        export_action.triggered.connect(lambda: self.open_asset_exporter(index))
        menu.addAction(export_action)

        duplicate_action = QAction("Duplicate File", self)
        duplicate_action.setIcon(QIcon(":/icons/content_copy_24dp.svg"))
        duplicate_action.triggered.connect(lambda: self.duplicate_file(index))
        menu.addAction(duplicate_action)

        copy_action = QAction("Copy File", self)
        copy_action.setIcon(QIcon(":/icons/content_copy_24dp.svg"))
        copy_action.triggered.connect(lambda: self.copy_file(index))
        menu.addAction(copy_action)

        paste_action = QAction("Paste File", self)
        paste_action.setIcon(QIcon(":/icons/content_paste_24dp.svg"))
        paste_action.triggered.connect(lambda: self.paste_file(self.model.index(os.path.dirname(file_path))))
        menu.addAction(paste_action)

        delete_action = QAction("Delete File", self)
        delete_action.setIcon(QIcon(":/icons/delete_16dp.svg"))
        delete_action.triggered.connect(lambda: self.delete_item(index))
        menu.addAction(delete_action)

        # Paths
        menu.addSection("Path")
        copy_relative_path_action = QAction("Copy Relative Path", self)
        copy_relative_path_action.setIcon(QIcon(":/icons/attachment.png"))
        copy_relative_path_action.triggered.connect(lambda: self.copy_path(index, True))
        menu.addAction(copy_relative_path_action)

        copy_path_action = QAction("Copy Path", self)
        copy_path_action.setIcon(QIcon(":/icons/attachment.png"))
        copy_path_action.triggered.connect(lambda: self.copy_path(index, True, relative=False))
        menu.addAction(copy_path_action)

        if file_extension in audio_extensions:
            copy_audio_path_action = QAction("Copy Audio Path", self)
            copy_audio_path_action.setIcon(QIcon(":/icons/attachment.png"))
            copy_audio_path_action.triggered.connect(lambda: self.copy_audio_path(index, True))
            menu.addAction(copy_audio_path_action)

    def convert_audio_file(self, file_path, target_ext):
        """Convert an mp3<->wav file in place (writes a sibling with the new ext)."""
        from src.editors.soundevent_editor.audio_convert import convert_audio
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            out = convert_audio(file_path, target_ext)
        except Exception as error:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Conversion failed", str(error))
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(
            self, "Conversion complete",
            f"Created:\n{out}"
        )

    def duplicate_file(self, index):
        file_path = self.model.filePath(index)
        base_name_with_ext = os.path.basename(file_path)
        base_name, extension = os.path.splitext(base_name_with_ext)
        match = re.match(r'^(.*?)(?:_(\d+))?$', base_name)
        new_base_name = match.group(1)
        counter = 1
        new_file_name = f"{new_base_name}_{counter:02d}{extension}"
        new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
        while QFile.exists(new_file_path):
            counter += 1
            new_file_name = f"{new_base_name}_{counter:02d}{extension}"
            new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
        if QFile.copy(file_path, new_file_path):
            if new_file_path.lower().endswith('.hbat'):
                from src.editors.assetgroup_maker.monitor import MonitoringFileWatcher
                MonitoringFileWatcher.notify_new_file(new_file_path)
            return True
        else:
            error_dialog = ErrorInfo(text="Duplication Error", details="Failed to duplicate the file.")
            error_dialog.exec_()
            return False

    def _on_tree_double_clicked(self, index):
        if not index.isValid():
            return
        source_index = self.filter_proxy_model.mapToSource(index)
        if self.model.isDir(source_index):
            return
        file_path = self.model.filePath(source_index)
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.vsmart', '.vdata'):
            self.open_vsmart(file_path)
        elif ext == '.vsndevts':
            self.open_vsndevts(file_path)
        elif ext == '.hbat':
            self.open_config(file_path)
        elif ext in [f".{e}" for e in audio_extensions] or ext[1:] in audio_extensions:
            if self.use_internal_player:
                self.play_sound.emit(file_path)
            else:
                self.play_audio_file(file_path)
        else:
            self.open_file(source_index)

    def open_config(self, filepath):
        parent = self.parent()
        curr = parent
        while curr is not None:
            if hasattr(curr, 'BatchCreator_MainWindow') and curr.BatchCreator_MainWindow is not None:
                curr.BatchCreator_MainWindow.open_filepath(filepath)
                return
            curr = curr.parent() if hasattr(curr, 'parent') else None
        if parent and hasattr(parent, 'BatchCreator_MainWindow'):
            parent.BatchCreator_MainWindow.open_filepath(filepath)

    def open_reference_asset(self, filepath: str):
        from src.editors.assetgroup_maker.monitor import get_reference_asset_path
        try:
            from src.other.cs2_netcon import CS2Netcon
        except Exception:
            CS2Netcon = None

        asset_path = get_reference_asset_path(filepath)
        if not asset_path:
            QMessageBox.warning(self, "No Reference Asset", f"No reference asset found in '{os.path.basename(filepath)}'.")
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
            curr = self.parent()
            while curr is not None:
                if hasattr(curr, 'update_title') and callable(curr.update_title):
                    curr.update_title(text=f"Opened reference asset [{asset_path}] in CS2 Tools")
                    break
                curr = curr.parent() if hasattr(curr, 'parent') else None

    def open_vsmart(self, filepath):
        parent = self.parent()
        curr = parent
        while curr is not None:
            if hasattr(curr, 'open_file_in_smartprop'):
                curr.open_file_in_smartprop(filepath)
                return
            elif hasattr(curr, 'SmartPropEditorMainWindow') and curr.SmartPropEditorMainWindow is not None:
                curr.SmartPropEditorMainWindow.open_file(external=False, filename=filepath)
                return
            curr = curr.parent() if hasattr(curr, 'parent') else None
        if parent and hasattr(parent, 'SmartPropEditorMainWindow') and parent.SmartPropEditorMainWindow:
            parent.SmartPropEditorMainWindow.open_file(external=False, filename=filepath)

    def open_vsndevts(self, filepath):
        parent = self.parent()
        curr = parent
        while curr is not None:
            if hasattr(curr, 'open_file_in_soundevent'):
                curr.open_file_in_soundevent(filepath)
                return
            elif hasattr(curr, 'SoundEventEditorMainWindow') and curr.SoundEventEditorMainWindow is not None:
                curr.SoundEventEditorMainWindow.load_soundevents(filepath=filepath)
                return
            curr = curr.parent() if hasattr(curr, 'parent') else None
        if parent and hasattr(parent, 'SoundEventEditorMainWindow') and parent.SoundEventEditorMainWindow:
            parent.SoundEventEditorMainWindow.load_soundevents(filepath=filepath)


    def copy_file(self, index):
        file_path = self.model.filePath(index)
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(file_path)

    def paste_file(self, destination_index):
        clipboard = QGuiApplication.clipboard()
        file_path_from_clipboard = clipboard.text()
        if not file_path_from_clipboard:
            return False
        destination_path = self.model.filePath(destination_index)
        if not destination_path:
            destination_path = self.tree_directory
        new_file_name = os.path.join(destination_path, QFileInfo(file_path_from_clipboard).fileName())
        if QFile.exists(new_file_name):
            reply = QMessageBox.question(self, 'File Exists',
                                         f"The file '{new_file_name}' already exists. Do you want to replace it?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                try:
                    shutil.copyfile(file_path_from_clipboard, new_file_name)
                    if new_file_name.lower().endswith('.hbat'):
                        from src.editors.assetgroup_maker.monitor import MonitoringFileWatcher
                        MonitoringFileWatcher.notify_new_file(new_file_name)
                    return True
                except shutil.Error as e:
                    error_dialog = ErrorInfo(text="Paste Error", details=str(e))
                    error_dialog.exec_()
                    return False
            else:
                return False
        else:
            try:
                shutil.copyfile(file_path_from_clipboard, new_file_name)
                self.select_tree_item(new_file_name)
                if new_file_name.lower().endswith('.hbat'):
                    from src.editors.assetgroup_maker.monitor import MonitoringFileWatcher
                    MonitoringFileWatcher.notify_new_file(new_file_name)
                return True
            except shutil.Error as e:
                error_dialog = ErrorInfo(text="Paste Error", details=str(e))
                error_dialog.exec_()
                return False

    def open_folder_in_explorer(self, index):
        folder_path = self.model.filePath(index)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def open_file(self, index):
        file_path = self.model.filePath(index)
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def open_path_file(self, index):
        file_path = self.model.filePath(index)
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(file_path)))

    def delete_item(self, index):
        path = self.model.filePath(index)
        reply = QMessageBox.question(self, 'Remove Item',
                                     f"Are you sure you want to remove '{path}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if self.model.isDir(index):
                    if not QDir(path).removeRecursively():
                        raise Exception("Failed to remove directory.")
                else:
                    if not QFile.remove(path):
                        raise Exception("Failed to remove file.")
            except Exception as e:
                error_dialog = ErrorInfo(text="Deletion Error", details=str(e))
                error_dialog.exec_()

    def open_asset_manager(self, index):
        indexes = self.tree.selectionModel().selectedIndexes()
        selected_paths = []
        for idx in indexes:
            if idx.column() == CustomFileSystemModel.NAME_COLUMN:
                src_idx = self.filter_proxy_model.mapToSource(idx)
                selected_paths.append(self.model.filePath(src_idx))
        
        # fallback if nothing selected
        if not selected_paths and index.isValid():
            src_idx = self.filter_proxy_model.mapToSource(index)
            selected_paths.append(self.model.filePath(src_idx))

        from src.forms.asset_manager.main import AssetManagerWidget
        self.asset_manager_window = AssetManagerWidget()
        self.asset_manager_window.set_files_to_move(selected_paths)
        self.asset_manager_window.show()

    def open_asset_exporter(self, index):
        indexes = self.tree.selectionModel().selectedIndexes()
        selected_paths = []
        for idx in indexes:
            if idx.column() == CustomFileSystemModel.NAME_COLUMN:
                src_idx = self.filter_proxy_model.mapToSource(idx)
                selected_paths.append(self.model.filePath(src_idx))
        
        # fallback if nothing selected
        if not selected_paths and index.isValid():
            src_idx = self.filter_proxy_model.mapToSource(index)
            selected_paths.append(self.model.filePath(src_idx))

        from src.forms.asset_exporter.main import AssetExporterWidget
        self.asset_exporter_window = AssetExporterWidget()
        self.asset_exporter_window.select_file(selected_paths)
        self.asset_exporter_window.show()

    def open_asset_renamer(self, index):
        if not index.isValid():
            return

        source_index = self.filter_proxy_model.mapToSource(index)
        old_path = self.model.filePath(source_index)
        old_name = os.path.basename(old_path)

        new_name, ok = QInputDialog.getText(self, "Rename Asset", "Enter new name:", QLineEdit.Normal, old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            if os.path.exists(new_path):
                QMessageBox.warning(self, "Rename Error", f"The file '{new_name}' already exists.")
                return

            from src.forms.asset_manager.move_worker import MoveWorker
            # Explorer uses self.rootpath as the addon content path
            self.worker = MoveWorker([(old_path, new_path)], self.rootpath)
            self.worker.log.connect(lambda msg: debug(f"[Rename] {msg}"))
            self.worker.finished_move.connect(self.on_rename_finished)

            # Disable UI or show progress if needed, but for now just start
            self.worker.start()

    def on_rename_finished(self):
        QMessageBox.information(self, "Success", "Asset renamed and references updated successfully.")

    def copy_audio_path(self, index, to_clipboard):
        file_path = self.model.filePath(index)
        file_path = os.path.relpath(file_path, self.tree_directory)
        file_path = file_path.replace('\\', '/').lower()
        root, ext = os.path.splitext(file_path)
        file_path = root + '.vsnd'
        if to_clipboard:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(file_path)
        else:
            return file_path

    def copy_path(self, index, to_clipboard, relative=True):
        file_path = self.model.filePath(index)
        if relative:
            file_path = os.path.relpath(file_path, self.rootpath)
        file_path = file_path.replace('\\', '/').lower()
        root, ext = os.path.splitext(file_path)
        file_path = root + ext
        if to_clipboard:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(file_path)
        else:
            return file_path

    def delete_selected_items(self):
        indexes = self.tree.selectionModel().selectedIndexes()
        if not indexes:
            return
        paths = [self.model.filePath(self.filter_proxy_model.mapToSource(index))
                 for index in indexes if index.column() == CustomFileSystemModel.NAME_COLUMN]
        reply = QMessageBox.question(self, 'Remove Items',
                                     "Are you sure you want to remove the selected items?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for path in paths:
                try:
                    if QDir(path).exists():
                        if not QDir(path).removeRecursively():
                            raise Exception(f"Failed to remove directory '{path}'")
                    else:
                        if not QFile.remove(path):
                            raise Exception(f"Failed to remove file '{path}'")
                except Exception as e:
                    error_dialog = ErrorInfo(text="Deletion Error", details=str(e))
                    error_dialog.exec_()

    def create_folder(self, parent_index):
        parent_path = self.model.filePath(parent_index)
        default_folder_name = "New Folder"
        new_folder_path = QDir(parent_path).absoluteFilePath(default_folder_name)
        counter = 1
        while QDir(new_folder_path).exists():
            new_folder_path = QDir(parent_path).absoluteFilePath(f"{default_folder_name} ({counter})")
            counter += 1
        QDir(parent_path).mkdir(QFileInfo(new_folder_path).fileName())
        new_folder_index = self.model.index(new_folder_path)
        self.tree.edit(self.filter_proxy_model.mapFromSource(new_folder_index))
        self.select_tree_item(new_folder_path)

    def goto_clipboard_path(self):
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            return
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return
        input_path = lines[0].strip('\'" \t\r\n')
        if input_path:
            self.select_tree_item(input_path)

    # Inline recent-files / favorites panel

    def _build_panel(self):
        """Create the floating overlay popup widget matching program stylesheet."""
        frame = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        frame.setObjectName("explorerOverlayPanel")
        frame.setStyleSheet(
            "QFrame#explorerOverlayPanel {"
            "  background-color: #2e2e2e;"
            "  border: 2px solid black;"
            "  border-color: rgba(94, 94, 94, 255);"
            "  border-radius: 0px;"
            "}"
        )
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(4)

        # Header row: label + close button
        header = QHBoxLayout()
        self._panel_title = QLabel("", frame)
        self._panel_title.setStyleSheet("color: #e5e5e5; font: 580 9pt \"Segoe UI\"; font-weight: bold; background-color: transparent;")
        header.addWidget(self._panel_title)
        header.addStretch()
        close_btn = QToolButton(frame)
        close_btn.setText("✕")
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(
            "QToolButton { color: #a5a5a5; border: none; font-size: 11px; padding: 1px 4px; background-color: transparent; }"
            "QToolButton:hover { color: #FFFFFF; background-color: #515965; }"
        )
        close_btn.setMaximumHeight(20)
        close_btn.clicked.connect(self._hide_panel)
        header.addWidget(close_btn)
        vbox.addLayout(header)

        self._panel_filter = QLineEdit(frame)
        self._panel_filter.setPlaceholderText("Filter...")
        self._panel_filter.setStyleSheet(
            "QLineEdit {"
            "  font: 580 9pt \"Segoe UI\";"
            "  background-color: #272727;"
            "  color: #e5e5e5;"
            "  border: 1px solid rgba(94, 94, 94, 255);"
            "  border-radius: 0px;"
            "  padding: 3px 6px;"
            "}"
        )
        self._panel_filter.textChanged.connect(self._filter_panel_items)
        vbox.addWidget(self._panel_filter)

        self._panel_list = QListWidget(frame)
        self._panel_list.setStyleSheet(
            "QListWidget {"
            "  background-color: #2e2e2e;"
            "  color: #e5e5e5;"
            "  font: 580 9pt \"Segoe UI\";"
            "  border: none;"
            "  outline: none;"
            "}"
            "QListWidget::item {"
            "  padding: 4px 6px;"
            "  border-radius: 0px;"
            "  border-bottom: 0.5px solid rgba(255, 255, 255, 10);"
            "}"
            "QListWidget::item:hover {"
            "  background-color: #38383a;"
            "  color: #e5e5e5;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: #515965;"
            "  color: white;"
            "}"
        )
        self._panel_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._panel_list.customContextMenuRequested.connect(self._panel_context_menu)
        self._panel_list.itemClicked.connect(self._on_panel_item_clicked)
        vbox.addWidget(self._panel_list)

        return frame

    def _toggle_panel(self, mode):
        """Show the overlay panel in *mode* ('recent'/'favorites'), anchored to button."""
        target_btn = self.recent_button if mode == "recent" else self.favorites_button
        
        if self._panel_frame.isVisible() and self._panel_mode == mode:
            self._hide_panel()
            return

        self._panel_mode = mode
        self._populate_panel()

        # Size and position overlay popup relative to button
        self._panel_frame.setFixedWidth(320)
        max_h = min(300, max(120, self._panel_list.count() * 26 + 65))
        self._panel_list.setFixedHeight(max(60, max_h - 60))
        self._panel_frame.adjustSize()

        # Position below the button
        btn_pos = target_btn.mapToGlobal(target_btn.rect().bottomLeft())
        # Shift slightly left if overflow right
        self._panel_frame.move(btn_pos)
        self._panel_frame.show()
        self._panel_filter.setFocus()

    def _hide_panel(self):
        self._panel_frame.hide()
        self._panel_mode = None
        self._panel_filter.clear()

    def _populate_panel(self):
        """Fill the list widget according to the current panel mode."""
        self._panel_list.clear()
        self._panel_filter.clear()

        if self._panel_mode == "recent":
            self._panel_title.setText("Recent Files")
            paths = self.load_recent_files()
        else:
            self._panel_title.setText("Favorites")
            paths = self.load_favorites()

        for path in paths:
            if not path:
                continue
            try:
                basename = os.path.basename(path)
                item = QListWidgetItem(basename)
                item.setToolTip(path)
                item.setData(Qt.UserRole, path)  # store absolute path
                if os.path.isdir(path):
                    item.setIcon(QIcon("://valve_common/icons/tools/common/folder_sm.png"))
                else:
                    ext = os.path.splitext(path)[1].lower()
                    if ext in file_icons:
                        item.setIcon(QIcon(file_icons[ext]))
                    elif path.endswith(tuple(audio_extensions)):
                        item.setIcon(QIcon("://icons/tools/assettypes/vmix_sm.png"))
                    elif path.endswith(tuple(generic_extensions)):
                        item.setIcon(QIcon("://icons/tools/assettypes/generic_sm.png"))
                    else:
                        item.setIcon(QIcon("://icons/file_present_24dp.png"))
                self._panel_list.addItem(item)
            except Exception as e:
                debug(f"Skipping invalid panel path: {path} ({e})")

    def _filter_panel_items(self, text):
        for i in range(self._panel_list.count()):
            item = self._panel_list.item(i)
            full_path = item.data(Qt.UserRole) or ""
            match = text.lower() in item.text().lower() or text.lower() in full_path.lower()
            item.setHidden(not match)

    def _on_panel_item_clicked(self, item):
        full_path = item.data(Qt.UserRole)
        if full_path and os.path.exists(full_path):
            self.select_tree_item(full_path)
        self._hide_panel()

    def _panel_context_menu(self, pos):
        """Context menu for the panel list (favorites: remove; recent: always available)."""
        item = self._panel_list.itemAt(pos)
        if item is None:
            return
        menu = ZebraMenu(self)
        if self._panel_mode == "favorites":
            remove_action = QAction("Remove Favorite", self)
            remove_action.setIcon(QIcon(":/icons/delete_16dp.svg"))
            def _remove():
                full_path = item.data(Qt.UserRole)
                if full_path and full_path in self.favorites:
                    self.favorites.remove(full_path)
                    self.save_favorites()
                self._panel_list.takeItem(self._panel_list.row(item))
            remove_action.triggered.connect(_remove)
            menu.addAction(remove_action)
        elif self._panel_mode == "recent":
            remove_action = QAction("Remove from Recent", self)
            remove_action.setIcon(QIcon(":/icons/delete_16dp.svg"))
            def _remove_recent():
                full_path = item.data(Qt.UserRole)
                recent = self.load_recent_files()
                if full_path and full_path in recent:
                    recent.remove(full_path)
                    self.recent_files = recent
                    self.save_recent_files()
                self._panel_list.takeItem(self._panel_list.row(item))
            remove_action.triggered.connect(_remove_recent)
            menu.addAction(remove_action)
        if not menu.isEmpty():
            menu.exec_(self._panel_list.viewport().mapToGlobal(pos))

    def get_current_path(self, absolute=False):
            current_index = self.tree.currentIndex()
            if current_index.isValid():
                source_index = self.filter_proxy_model.mapToSource(current_index)
                path = self.model.filePath(source_index)
                if absolute:
                    path = os.path.abspath(path)
                return path
            else:
                error_dialog = ErrorInfo(text="No file selected", details="Please select a file.")
                error_dialog.exec_()
                return None

    def get_current_folder(self, absolute=False):
        filepath = self.get_current_path(absolute=absolute)
        if filepath and os.path.isdir(filepath):
            return filepath
        elif filepath:
            # If not a directory, return the folder part of the absolute path if absolute flag is set.
            folder = os.path.dirname(filepath) if absolute else os.path.basename(filepath)
            return folder
        else:
            return None

    def closeEvent(self, event):
        tree_state = self.tree.header().saveState()
        set_settings_value(self.editor_name + '_tree_state', self.addon, tree_state)
        event.accept()