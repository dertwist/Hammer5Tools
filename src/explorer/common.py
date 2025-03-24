import os

from PySide6.QtWidgets import QFileSystemModel
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QMimeData, QUrl, QFileInfo, QDir

from src.settings.main import debug

# Supported file extensions
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
        # Decorate folders and recognized file extensions with icons
        if role == Qt.DecorationRole and self.isDir(index) and index.column() != self.SIZE_COLUMN:
            return QIcon('://icons/folder_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg')
        elif role == Qt.DecorationRole and not self.isDir(index) and index.column() == self.NAME_COLUMN:
            file_path = self.filePath(index)
            # Check for known file icons
            for ext, icon_path in file_icons.items():
                if file_path.endswith(ext):
                    return QIcon(icon_path)
            # Generic fallback icons
            from .common import audio_extensions, generic_extensions  # safely re-import for clarity
            if file_path.endswith(tuple(audio_extensions)):
                return QIcon('://icons/assettypes/vmix_sm.png')
            if file_path.endswith(tuple(generic_extensions)):
                return QIcon('://icons/assettypes/generic_sm.png')

        # Cache the display name to speed up repeated lookups
        if role == Qt.DisplayRole and index.column() == self.NAME_COLUMN:
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
                # moving files
                from PySide6.QtCore import QFile
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
            from PySide6.QtCore import QFile
            if QFile.exists(new_path):
                return False
            if QFile.rename(old_path, new_path):
                if old_path in self._cache:
                    del self._cache[old_path]
                self._cache[new_path] = value
                self.dataChanged.emit(index, index)
                # Update selection after renaming action if parent has a matching method
                if self.parent() is not None and hasattr(self.parent(), 'select_tree_item'):
                    self.parent().select_tree_item(new_path)
                return True

        return super().setData(index, value, role)

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid() and index.column() == self.NAME_COLUMN:
            return Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | default_flags
        return default_flags



