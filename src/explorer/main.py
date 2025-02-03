import os
import re
import shutil
from PySide6.QtWidgets import QMainWindow, QTreeView, QVBoxLayout, QFileSystemModel, QStyledItemDelegate, QHeaderView, QMenu, QMessageBox, QFrame
from PySide6.QtGui import QIcon, QAction, QDesktopServices, QMouseEvent, QKeyEvent, QGuiApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Signal, Qt, QDir, QMimeData, QUrl, QFile, QFileInfo, QItemSelectionModel
from src.settings.main import get_config_value, set_config_value, get_cs2_path, get_addon_name, debug
from src.widgets_common import ErrorInfo

audio_extensions = ['wav', 'mp3', 'flac', 'aac', 'm4a', 'wma']
smartprop_extensions = ['vsmart', 'vdata']
generic_extensions = ['vpost', 'vsndevts', 'rect', 'keybindings', 'kv3']
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
            old_base_name = file_info.completeBaseName()
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
        self.model = CustomFileSystemModel()
        self.model.setRootPath(tree_directory)
        try:
            self.rootpath = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name())
        except Exception as e:
            error_dialog = ErrorInfo(text="Initialization Error", details=str(e))
            error_dialog.exec_()
            self.rootpath = tree_directory
        if not os.path.exists(tree_directory):
            os.makedirs(tree_directory)
        self.use_internal_player = use_internal_player
        if not self.use_internal_player:
            self.audio_player = None
        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(tree_directory))
        self.tree.setSortingEnabled(True)
        for column in range(self.model.columnCount()):
            if column not in (CustomFileSystemModel.NAME_COLUMN, CustomFileSystemModel.SIZE_COLUMN):
                self.tree.setColumnHidden(column, True)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.tree.setItemDelegateForColumn(CustomFileSystemModel.SIZE_COLUMN, QStyledItemDelegate())
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(CustomFileSystemModel.NAME_COLUMN, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(CustomFileSystemModel.SIZE_COLUMN, QHeaderView.Interactive)
        self.tree.header().setSortIndicator(CustomFileSystemModel.NAME_COLUMN, Qt.AscendingOrder)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QTreeView.InternalMove)
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.viewport().installEventFilter(self)
        self.tree.installEventFilter(self)
        self.addon = addon
        self.editor_name = editor_name
        self.tree_directory = tree_directory
        self.select_last_opened_path()
        self.frame = QFrame(self)
        self.frame.setLayout(self.layout)
        self.tree.selectionModel().currentChanged.connect(self.on_directory_changed)

    def select_last_opened_path(self):
        try:
            last_opened_path = get_config_value(self.editor_name + '_explorer_lath_path', self.addon)
            if last_opened_path:
                last_opened_index = self.model.index(last_opened_path)
                self.tree.selectionModel().select(last_opened_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self.tree.scrollTo(last_opened_index)
        except Exception as e:
            error_dialog = ErrorInfo(text="Selection Error", details=str(e))
            error_dialog.exec_()

    def save_current_path(self, path):
        set_config_value(self.editor_name + '_explorer_lath_path', self.addon, path)

    def on_directory_changed(self, current, previous):
        current_path = self.model.filePath(current)
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
            if self.model.isDir(index):
                self.add_folder_actions(menu, index)
            else:
                self.add_file_actions(menu, index)
        else:
            create_folder_action = QAction("Create Folder", self)
            create_folder_action.triggered.connect(lambda: self.create_folder(self.tree.rootIndex()))
            menu.addAction(create_folder_action)
            paste_action = QAction("Paste File", self)
            paste_action.triggered.connect(lambda: self.paste_file(index))
            menu.addAction(paste_action)
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_folder_actions(self, menu, index):
        open_folder_action = QAction("Open Folder in Explorer", self)
        open_folder_action.triggered.connect(lambda: self.open_folder_in_explorer(index))
        menu.addAction(open_folder_action)
        delete_action = QAction("Delete Folder", self)
        delete_action.triggered.connect(lambda: self.delete_item(index))
        menu.addAction(delete_action)
        new_folder_action = QAction("New Folder", self)
        new_folder_action.triggered.connect(lambda: self.create_folder(index))
        menu.addAction(new_folder_action)
        paste_action = QAction("Paste File", self)
        paste_action.triggered.connect(lambda: self.paste_file(index))
        menu.addAction(paste_action)

    def add_file_actions(self, menu, index):
        open_action = QAction("Open File", self)
        open_action.triggered.connect(lambda: self.open_file(index))
        menu.addAction(open_action)
        open_path_action = QAction("Open File Folder", self)
        open_path_action.triggered.connect(lambda: self.open_path_file(index))
        menu.addAction(open_path_action)
        delete_action = QAction("Delete File", self)
        delete_action.triggered.connect(lambda: self.delete_item(index))
        menu.addAction(delete_action)
        duplicate_action = QAction("Duplicate File", self)
        duplicate_action.triggered.connect(lambda: self.duplicate_file(index))
        menu.addAction(duplicate_action)
        copy_action = QAction("Copy File", self)
        copy_action.triggered.connect(lambda: self.copy_file(index))
        menu.addAction(copy_action)
        copy_relative_path_action = QAction("Copy relative path", self)
        copy_relative_path_action.triggered.connect(lambda: self.copy_relative_path(index, True))
        menu.addAction(copy_relative_path_action)
        file_path = self.model.filePath(index)
        file_extension = file_path.split('.')[-1]
        if file_extension in audio_extensions:
            copy_audio_path_action = QAction("Copy Audio Path", self)
            copy_audio_path_action.triggered.connect(lambda: self.copy_audio_path(index, True))
            menu.addAction(copy_audio_path_action)

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
            elif reply == QMessageBox.No:
                return False
            else:
                return False
        else:
            try:
                shutil.copyfile(file_path_from_clipboard, new_file_name)
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
        reply = QMessageBox.question(self, 'Remove Item', f"Are you sure you want to remove '{path}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
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

    def copy_relative_path(self, index, to_clipboard):
        file_path = self.model.filePath(index)
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
        paths = [self.model.filePath(index) for index in indexes if index.column() == CustomFileSystemModel.NAME_COLUMN]
        reply = QMessageBox.question(self, 'Remove Items', "Are you sure you want to remove the selected items?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
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
        self.tree.edit(new_folder_index)