import os
import re
import shutil
from PySide6.QtWidgets import QMainWindow, QTreeView, QVBoxLayout, QFileSystemModel, QStyledItemDelegate, QHeaderView, QMenu, QMessageBox, QFrame, QLineEdit, QHBoxLayout, QToolButton, QDialog, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtGui import QIcon, QAction, QDesktopServices, QMouseEvent, QKeyEvent, QGuiApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Signal, Qt, QDir, QMimeData, QUrl, QFile, QFileInfo, QItemSelectionModel, QSortFilterProxyModel

from src.settings.main import get_settings_value, set_settings_value, get_cs2_path, get_addon_name, debug, get_addon_dir
from src.widgets_common import ErrorInfo
from src.explorer.actions import QuickVmdlFile, QuickConfigFile, QuickProcess
from src.styles.common import *
from src.common import enable_dark_title_bar

audio_extensions = ['wav', 'mp3', 'flac', 'aac', 'm4a', 'wma']
smartprop_extensions = ['vsmart', 'vdata']
generic_extensions = ['vpost', 'vsndevts', 'rect', 'keybindings', 'kv3']
model_extensions = ['obj', 'fbx', 'dmx']

file_icons = {
    '.vsmart': '://icons/assettypes/vsmart_sm.png',
    '.vdata': '://icons/assettypes/vdata_sm.png',
    '.vmat': '://icons/assettypes/material_sm.png',
    '.vmap': '://icons/assettypes/map_sm.png',
    '.hbat': '://icons/assettypes/vcompmat_sm.png',
    '.vtex': '://icons/assettypes/texture_sm.png',
    '.vmdl': '://icons/assettypes/model_sm.png'
}

class CustomFileSystemModel(QFileSystemModel):
    NAME_COLUMN = 0
    SIZE_COLUMN = 1
    CACHE_LIMIT = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = {}

    def data(self, index, role):
        if role == Qt.DecorationRole and self.isDir(index) and index.column() != self.SIZE_COLUMN:
            return QIcon('://icons/folder_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg')
        elif role == Qt.DecorationRole and not self.isDir(index) and index.column() == self.NAME_COLUMN:
            file_path = self.filePath(index)
            for ext, icon_path in file_icons.items():
                if file_path.endswith(ext):
                    return QIcon(icon_path)
            if file_path.endswith(tuple(audio_extensions)):
                return QIcon('://icons/assettypes/vmix_sm.png')
            if file_path.endswith(tuple(generic_extensions)):
                return QIcon('://icons/assettypes/generic_sm.png')
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

    def mimeTypes(self):
        return ['text/uri-list']

    def mimeData(self, indexes):
        mime_data = QMimeData()
        urls = [self.filePath(index) for index in indexes]
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

class Explorer(QMainWindow):
    play_sound = Signal(str)

    def __init__(self, parent=None, tree_directory=None, addon=None, editor_name=None, use_internal_player: bool = True):
        super().__init__(parent)
        self.tree_directory = tree_directory
        self.addon = addon
        self.editor_name = editor_name
        self.use_internal_player = use_internal_player
        self.model = CustomFileSystemModel(self)
        self.model.setRootPath(tree_directory)
        try:
            self.rootpath = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name())
        except Exception:
            self.rootpath = tree_directory
        if not os.path.exists(tree_directory):
            os.makedirs(tree_directory)
        if not self.use_internal_player:
            self.audio_player = None
        self.filter_proxy_model = QSortFilterProxyModel(self)
        self.filter_proxy_model.setSourceModel(self.model)
        self.filter_proxy_model.setFilterKeyColumn(CustomFileSystemModel.NAME_COLUMN)
        self.filter_proxy_model.setDynamicSortFilter(True)
        self.filter_proxy_model.setRecursiveFilteringEnabled(True)
        self.tree = QTreeView(self)
        self.tree.setModel(self.filter_proxy_model)
        self.tree.setRootIndex(self.filter_proxy_model.mapFromSource(self.model.index(tree_directory)))
        self.tree.setSortingEnabled(True)
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
        self.tree.viewport().installEventFilter(self)
        self.tree.installEventFilter(self)
        self.top_layout = QHBoxLayout()
        self.filter_editline = QLineEdit(self)
        self.filter_editline.setPlaceholderText("Filter files...")
        self.filter_editline.textChanged.connect(self.update_filter)
        self.top_layout.addWidget(self.filter_editline)
        self.goto_button = QToolButton(self)
        self.goto_button.setIcon(QIcon("://icons/folder_open.svg"))
        self.goto_button.setToolTip("Goto a specific path")
        self.goto_button.clicked.connect(self.open_goto_dialog)
        self.goto_button.setMaximumHeight(26)
        self.goto_button.setMaximumWidth(26)
        self.goto_button.setStyleSheet(qt_stylesheet_toolbutton)
        self.top_layout.addWidget(self.goto_button)
        self.recent_button = QToolButton(self)
        self.recent_button.setIcon(QIcon("://icons/acute_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        self.recent_button.setToolTip("Recent Files")
        self.recent_button.setStyleSheet(qt_stylesheet_toolbutton)
        self.recent_button.setMaximumHeight(26)
        self.recent_button.setMaximumWidth(26)
        self.recent_button.clicked.connect(self.open_recent_files_dialog)
        self.top_layout.addWidget(self.recent_button)
        self.favorites_button = QToolButton(self)
        self.favorites_button.setIcon(QIcon("://icons/bookmark_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        self.favorites_button.setToolTip("Favorites")
        self.favorites_button.setStyleSheet(qt_stylesheet_toolbutton)
        self.favorites_button.setMaximumHeight(26)
        self.favorites_button.setMaximumWidth(26)
        self.favorites_button.clicked.connect(self.open_favorites_dialog)
        self.top_layout.addWidget(self.favorites_button)
        self.layout = QVBoxLayout(self)
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
            self.tree.restoreState(tree_state)
        self.recent_files = self.load_recent_files()
        self.favorites = self.load_favorites()
        self.select_last_opened_path()
        self.frame = QFrame(self)
        self.frame.setLayout(self.layout)

    def update_filter(self, text):
        self.filter_proxy_model.setFilterFixedString(text)
        if text.strip() == "":
            source_index = self.model.index(self.tree_directory)
            self.tree.setRootIndex(self.filter_proxy_model.mapFromSource(source_index))

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
        if normalized_path in normalized_favs:
            index = normalized_favs.index(normalized_path)
            favs.pop(index)
        favs.insert(0, normalized_path)
        if len(favs) > 30:
            favs = favs[:30]
        set_settings_value(self.editor_name + '_favorites', self.addon, favs)
        self.favorites = favs

    def load_favorites(self):
        fav = get_settings_value(self.editor_name + '_favorites', self.addon)
        if fav is None:
            return []
        return fav if isinstance(fav, list) else []

    def save_favorites(self):
        set_settings_value(self.editor_name + '_favorites', self.addon, self.favorites)

    def select_tree_item(self, path):
        self.add_recent_file(path)
        source_index = self.model.index(path)
        if not source_index.isValid():
            debug("select_tree_item: invalid path - %s" % path)
            return
        proxy_index = self.filter_proxy_model.mapFromSource(source_index)
        selection_model = self.tree.selectionModel()
        selection_model.clear()
        selection_model.select(proxy_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.tree.setCurrentIndex(proxy_index)
        self.tree.scrollTo(proxy_index)

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
        menu = QMenu()
        if index.isValid():
            source_index = self.filter_proxy_model.mapToSource(index)
            if self.model.isDir(source_index):
                self.add_folder_actions(menu, source_index)
            else:
                self.add_file_actions(menu, source_index)
            favorite_action = QAction("Add to Favorites", self)
            favorite_action.setIcon(QIcon(":/icons/bookmarks_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
            favorite_action.triggered.connect(lambda: self.add_favorite(self.model.filePath(source_index)))
            menu.addAction(favorite_action)
        else:
            create_folder_action = QAction("Create Folder", self)
            create_folder_action.setIcon(QIcon(":/icons/create_new_folder_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
            create_folder_action.triggered.connect(lambda: self.create_folder(self.model.index(self.tree_directory)))
            menu.addAction(create_folder_action)
            paste_action = QAction("Paste File", self)
            paste_action.setIcon(QIcon(":/icons/content_paste_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
            paste_action.triggered.connect(lambda: self.paste_file(self.model.index(self.tree_directory)))
            menu.addAction(paste_action)
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_folder_actions(self, menu, index):
        open_folder_action = QAction("Open Folder in Explorer", self)
        open_folder_action.setIcon(QIcon(":/icons/folder_open.svg"))
        open_folder_action.triggered.connect(lambda: self.open_folder_in_explorer(index))
        menu.addAction(open_folder_action)
        delete_folder_action = QAction("Delete Folder", self)
        delete_folder_action.setIcon(QIcon(":/icons/delete_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        delete_folder_action.triggered.connect(lambda: self.delete_item(index))
        menu.addAction(delete_folder_action)
        new_folder_action = QAction("New Folder", self)
        new_folder_action.setIcon(QIcon(":/icons/create_new_folder_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        new_folder_action.triggered.connect(lambda: self.create_folder(index))
        menu.addAction(new_folder_action)
        paste_action = QAction("Paste File", self)
        paste_action.setIcon(QIcon(":/icons/content_paste_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        paste_action.triggered.connect(lambda: self.paste_file(index))
        menu.addAction(paste_action)

    def add_file_actions(self, menu, index):
        open_action = QAction("Open File", self)
        open_action.setIcon(QIcon(":/icons/file_open_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        open_action.triggered.connect(lambda: self.open_file(index))
        menu.addAction(open_action)
        open_path_action = QAction("Open File Folder", self)
        open_path_action.setIcon(QIcon(":/icons/folder_open.svg"))
        open_path_action.triggered.connect(lambda: self.open_path_file(index))
        menu.addAction(open_path_action)
        delete_action = QAction("Delete File", self)
        delete_action.setIcon(QIcon(":/icons/delete_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        delete_action.triggered.connect(lambda: self.delete_item(index))
        menu.addAction(delete_action)
        duplicate_action = QAction("Duplicate File", self)
        duplicate_action.setIcon(QIcon(":/icons/content_copy_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        duplicate_action.triggered.connect(lambda: self.duplicate_file(index))
        menu.addAction(duplicate_action)
        copy_action = QAction("Copy File", self)
        copy_action.setIcon(QIcon(":/icons/content_copy_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        copy_action.triggered.connect(lambda: self.copy_file(index))
        menu.addAction(copy_action)
        copy_relative_path_action = QAction("Copy Relative Path", self)
        copy_relative_path_action.setIcon(QIcon(":/icons/attachment.png"))
        copy_relative_path_action.triggered.connect(lambda: self.copy_path(index, True))
        menu.addAction(copy_relative_path_action)

        copy_path_action = QAction("Copy Path", self)
        copy_path_action.setIcon(QIcon(":/icons/attachment.png"))
        copy_path_action.triggered.connect(lambda: self.copy_path(index, True, relative=False))
        menu.addAction(copy_path_action)
        file_path = self.model.filePath(index)
        file_extension = file_path.split('.')[-1].lower()
        if file_extension in audio_extensions:
            copy_audio_path_action = QAction("Copy Audio Path", self)
            copy_audio_path_action.setIcon(QIcon(":/icons/attachment.png"))
            copy_audio_path_action.triggered.connect(lambda: self.copy_audio_path(index, True))
            menu.addAction(copy_audio_path_action)
        if file_extension == "vmdl":
            quick_config_action = QAction("Quick Batch File", self)
            quick_config_action.setIcon(QIcon(":/icons/edit_document_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
            quick_config_action.triggered.connect(lambda: QuickConfigFile(file_path))
            menu.addAction(quick_config_action)
        if file_extension in model_extensions:
            quick_vmdl_action = QAction("Quick VMDL File", self)
            quick_vmdl_action.setIcon(QIcon(":/icons/edit_note_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
            quick_vmdl_action.triggered.connect(lambda: QuickVmdlFile(file_path))
            menu.addAction(quick_vmdl_action)
        if file_extension == ".hbat":
            quick_process_action = QAction("Quick Process", self)
            quick_process_action.setIcon(QIcon(":/icons/play_arrow_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
            quick_process_action.triggered.connect(lambda: QuickProcess(filepath=file_path).process())
            menu.addAction(quick_process_action)

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
            return True
        else:
            error_dialog = ErrorInfo(text="Duplication Error", details="Failed to duplicate the file.")
            error_dialog.exec_()
            return False

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

    def open_goto_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Goto Path")
        enable_dark_title_bar(dialog)
        layout = QVBoxLayout(dialog)
        path_edit = QLineEdit(dialog)
        path_edit.setPlaceholderText("Enter full path to focus...")
        layout.addWidget(path_edit)
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK", dialog)
        ok_button.setStyleSheet(qt_stylesheet_button)
        cancel_button = QPushButton("Cancel", dialog)
        cancel_button.setStyleSheet(qt_stylesheet_button)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        def on_ok():
            input_path = path_edit.text().strip()
            if input_path and os.path.exists(input_path):
                self.select_tree_item(input_path)
            dialog.accept()
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)
        dialog.exec_()

    def open_recent_files_dialog(self):
        dialog = QDialog(self)
        dialog.setMinimumWidth(500)
        dialog.setWindowTitle("Recent Files")
        enable_dark_title_bar(dialog)
        layout = QVBoxLayout(dialog)
        filter_edit = QLineEdit(dialog)
        filter_edit.setPlaceholderText("Filter recent files...")
        layout.addWidget(filter_edit)
        list_widget = QListWidget(dialog)
        for path in self.recent_files:
            if path:
                try:
                    relative_path = os.path.relpath(path, self.tree_directory)
                    item = QListWidgetItem(relative_path)
                    if os.path.isdir(path):
                        item.setIcon(QIcon("://icons/folder_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
                    else:
                        ext = os.path.splitext(path)[1].lower()
                        if ext in file_icons:
                            item.setIcon(QIcon(file_icons[ext]))
                        elif path.endswith(tuple(audio_extensions)):
                            item.setIcon(QIcon("://icons/assettypes/vmix_sm.png"))
                        elif path.endswith(tuple(generic_extensions)):
                            item.setIcon(QIcon("://icons/assettypes/generic_sm.png"))
                        else:
                            item.setIcon(QIcon("://icons/file.svg"))
                    list_widget.addItem(item)
                except Exception as e:
                    debug(f"Skipping invalid recent file path: {path} ({e})")
        layout.addWidget(list_widget)
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK", dialog)
        ok_button.setStyleSheet(qt_stylesheet_button)
        cancel_button = QPushButton("Cancel", dialog)
        cancel_button.setStyleSheet(qt_stylesheet_button)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        def on_item_double_clicked(item):
            selected_relative = item.text()
            full_path = os.path.join(self.tree_directory, selected_relative)
            if os.path.exists(full_path):
                self.select_tree_item(full_path)
            dialog.accept()
        def filter_items(text):
            for index in range(list_widget.count()):
                item = list_widget.item(index)
                item.setHidden(text.lower() not in item.text().lower())
        filter_edit.textChanged.connect(filter_items)
        list_widget.itemDoubleClicked.connect(on_item_double_clicked)
        ok_button.clicked.connect(lambda: dialog.accept())
        cancel_button.clicked.connect(dialog.reject)
        dialog.exec_()

    def open_favorites_dialog(self):
        dialog = QDialog(self)
        dialog.setMinimumWidth(500)
        dialog.setWindowTitle("Favorites")
        enable_dark_title_bar(dialog)
        layout = QVBoxLayout(dialog)
        filter_edit = QLineEdit(dialog)
        filter_edit.setPlaceholderText("Filter favorites...")
        layout.addWidget(filter_edit)
        list_widget = QListWidget(dialog)
        for path in self.favorites:
            if path:
                try:
                    relative_path = os.path.relpath(path, self.tree_directory)
                    item = QListWidgetItem(relative_path)
                    if os.path.isdir(path):
                        item.setIcon(QIcon("://icons/folder_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
                    else:
                        ext = os.path.splitext(path)[1].lower()
                        if ext in file_icons:
                            item.setIcon(QIcon(file_icons[ext]))
                        elif path.endswith(tuple(audio_extensions)):
                            item.setIcon(QIcon("://icons/assettypes/vmix_sm.png"))
                        elif path.endswith(tuple(generic_extensions)):
                            item.setIcon(QIcon("://icons/assettypes/generic_sm.png"))
                        else:
                            item.setIcon(QIcon("://icons/file.svg"))
                    list_widget.addItem(item)
                except Exception as e:
                    debug(f"Skipping invalid favorite file path: {path} ({e})")
        list_widget.setContextMenuPolicy(Qt.CustomContextMenu)

        def handle_context_menu(pos):
            item = list_widget.itemAt(pos)
            if item is None:
                return
            menu = QMenu()
            remove_action = QAction("Remove Favorite", dialog)
            remove_action.setIcon(QIcon(":/icons/delete_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))

            def remove_item():
                relative_path = item.text()
                full_path = os.path.join(self.tree_directory, relative_path)
                if full_path in self.favorites:
                    self.favorites.remove(full_path)
                    self.save_favorites()
                list_widget.takeItem(list_widget.row(item))

            remove_action.triggered.connect(remove_item)
            menu.addAction(remove_action)
            menu.exec_(list_widget.viewport().mapToGlobal(pos))

        list_widget.customContextMenuRequested.connect(handle_context_menu)
        layout.addWidget(list_widget)
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK", dialog)
        ok_button.setStyleSheet(qt_stylesheet_button)
        cancel_button = QPushButton("Cancel", dialog)
        cancel_button.setStyleSheet(qt_stylesheet_button)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_item_double_clicked(item):
            selected_relative = item.text()
            full_path = os.path.join(self.tree_directory, selected_relative)
            if os.path.exists(full_path):
                self.select_tree_item(full_path)
            dialog.accept()

        def filter_items(text):
            for index in range(list_widget.count()):
                item = list_widget.item(index)
                item.setHidden(text.lower() not in item.text().lower())

        filter_edit.textChanged.connect(filter_items)
        list_widget.itemDoubleClicked.connect(on_item_double_clicked)
        ok_button.clicked.connect(lambda: dialog.accept())
        cancel_button.clicked.connect(dialog.reject)
        dialog.exec_()

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
        tree_state = self.tree.saveState()
        set_settings_value(self.editor_name + '_tree_state', self.addon, tree_state)
        event.accept()