import os.path
import re
from PySide6.QtWidgets import QMainWindow, QTreeView, QVBoxLayout, QFileSystemModel, QStyledItemDelegate, QHeaderView, QMenu, QInputDialog, QMessageBox, QLineEdit, QTreeWidgetItem, QPushButton, QHBoxLayout
from PySide6.QtGui import QIcon, QAction, QDesktopServices, QMouseEvent, QKeyEvent, QGuiApplication
from PySide6.QtCore import Qt, QDir, QMimeData, QUrl, QFile, QFileInfo, QItemSelectionModel
from preferences import get_config_value, set_config_value, get_cs2_path, get_addon_name
from PySide6.QtCore import QModelIndex
import shutil
audio_extensions = ['wav', 'mp3', 'flac', 'aac', 'm4a', 'wma']
smartprop_extensions = ['vsmart', 'vdata']
generic_extensions = ['vpost', 'vsndevts', 'rect', 'keybindings']
file_icons = {
    '.vsmart': '://icons/assettypes/vsmart_sm.png',
    '.vdata': '://icons/assettypes/vdata_sm.png',
    '.vmat': '://icons/assettypes/material_sm.png',
    '.vmap': '://icons/assettypes/map_sm.png',
    '.h5t_batch': '://icons/assettypes/vcompmat_sm.png',
    '.vtex': '://icons/assettypes/texture_sm.png',
    '.vmdl': '://icons/assettypes/model_sm.png'
}
class CustomFileSystemModel(QFileSystemModel):
    NAME_COLUMN = 0
    SIZE_COLUMN = 1
    CACHE_LIMIT = 100  # Set a limit for the cache size

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = {}

    def data(self, index, role):
        if role == Qt.DecorationRole and self.isDir(index) and index.column() != self.SIZE_COLUMN:
            # return QIcon('://icons/folder_open.svg')  # Icon for the opened folder
            return QIcon('://icons/folder_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg')  # Default folder icon
        # Rest of the method remains the same
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
                self._clean_cache()  # Clean up the cache if it exceeds the limit
            return file_name
        return super().data(index, role)

    def _clean_cache(self):
        # Implement logic to clean up the cache, for example, removing the oldest entries
        # Here you can decide how to clean up the cache based on your requirements
        self._cache = {}  # Resetting the cache in this example
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
            if not value:  # Check if the new value is empty
                return False

            old_path = self.filePath(index)
            new_path = QDir(os.path.dirname(old_path)).absoluteFilePath(value)  # Assuming rootPath() is the base directory

            if QFile.exists(new_path):
                # Handle the case where the new name already exists
                return False

            if QFile.rename(old_path, new_path):
                # Update the cache if needed
                if old_path in self._cache:
                    del self._cache[old_path]
                self._cache[new_path] = value
                self.dataChanged.emit(index, index)
                return True
        return super().setData(index, value, role)

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid():
            return Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | default_flags
        return default_flags


# Add necessary imports
from PySide6.QtWidgets import QFrame

class Explorer(QMainWindow):
    def __init__(self, parent=None, tree_directory=None, addon=None, editor_name=None):
        super().__init__(parent)

        self.model = CustomFileSystemModel()
        self.model.setRootPath(tree_directory)
        self.rootpath = (os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name()))
        if os.path.exists(tree_directory):
            pass
        else:
            os.makedirs(tree_directory)


        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(tree_directory))
        self.tree.setSortingEnabled(True)

        for column in range(self.model.columnCount()):
            if column not in (CustomFileSystemModel.NAME_COLUMN, CustomFileSystemModel.SIZE_COLUMN):
                self.tree.setColumnHidden(column, True)

        self.layout = QVBoxLayout(self)

        # Assuming self.layout is a QVBoxLayout
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
        self.tree.selectionModel().currentChanged.connect(self.on_directory_changed)
        self.select_last_opened_path()

        # Add all widgets to a frame
        self.frame = QFrame(self)
        self.frame.setLayout(self.layout)





    def select_last_opened_path(self):
        try:
            last_opened_path = get_config_value(self.editor_name + '_explorer_lath_path', self.addon)
            if last_opened_path:
                last_opened_index = self.model.index(last_opened_path)
                self.tree.selectionModel().select(last_opened_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self.tree.scrollTo(last_opened_index)
        except:
            pass

    def save_current_path(self, path):
        set_config_value(self.editor_name + '_explorer_lath_path', self.addon, path)

    def on_directory_changed(self, current, previous):
        current_path = self.model.filePath(current)
        self.save_current_path(current_path)

    def eventFilter(self, source, event):
        if event.type() == QMouseEvent.MouseButtonPress:
            if event.button() in (Qt.LeftButton, Qt.RightButton):
                index = self.tree.indexAt(event.pos())
                if not index.isValid():
                    self.tree.clearSelection()
        elif event.type() == QKeyEvent.KeyPress and event.key() == Qt.Key_Delete:
            if self.tree.selectionModel().hasSelection():  # Check if there is any selection
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

            # Add Paste File action
            paste_action = QAction("Paste File", self)
            paste_action.triggered.connect(lambda: self.paste_file(index))
            menu.addAction(paste_action)

        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_folder_actions(self, menu, index):
        open_folder_action = QAction("Open Folder in Explorer", self)
        open_folder_action.triggered.connect(lambda: self.open_folder_in_explorer(index))
        menu.addAction(open_folder_action)

        rename_action = QAction("Delete Folder", self)
        rename_action.triggered.connect(lambda: self.rename_item(index))
        menu.addAction(rename_action)

        delete_action = QAction("Delete Folder", self)
        delete_action.triggered.connect(lambda: self.delete_item(index))
        menu.addAction(delete_action)

        new_folder_action = QAction("New Folder", self)
        new_folder_action.triggered.connect(lambda: self.create_folder(index))
        menu.addAction(new_folder_action)

        # Add Paste File action
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

        # Add Copy File action
        copy_action = QAction("Copy File", self)
        copy_action.triggered.connect(lambda: self.copy_file(index))
        menu.addAction(copy_action)


        file_path = self.model.filePath(index)
        file_extension = file_path.split('.')[-1]  # Get the file extension from the file path
        if file_extension in audio_extensions:
            copy_audio_path_action = QAction("Copy Audio Path", self)  # Updated action text for clarity
            copy_audio_path_action.triggered.connect(lambda: self.copy_audio_path(index, True))
            menu.addAction(copy_audio_path_action)

        elif file_extension in smartprop_extensions:
            copy_smartprop_path_action = QAction("Copy Smartprop Path", self)  # Updated action text for clarity
            copy_smartprop_path_action.triggered.connect(lambda: self.copy_smartprop_path(index, True))
            menu.addAction(copy_smartprop_path_action)

    def duplicate_file(self, index):
        file_path = self.model.filePath(index)

        base_name, extension = os.path.splitext(os.path.basename(file_path))
        counter = 1

        # Extract the numeric part from the base name
        numeric_part = base_name.split('_')[-1]
        if numeric_part.isdigit():
            new_base_name = base_name.rsplit('_', 1)[0] + '_'  # Extract the base name without the numeric part
            new_file_name = f"{new_base_name}{counter:02d}{extension}"
        else:
            new_file_name = f"{base_name}_{counter:02d}{extension}"  # Initialize new_file_name before the loop

        new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)

        while QFile.exists(new_file_path):
            counter += 1
            new_file_name = f"{new_base_name}{counter:02d}{extension}"
            new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)

        if QFile.copy(file_path, new_file_path):
            return True
        return False

    def copy_file(self, index):
        file_path = self.model.filePath(index)
        # self._copied_file_path = file_path

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(file_path)

    def paste_file(self, destination_index):
        clipboard = QGuiApplication.clipboard()
        file_path_from_clipboard = clipboard.text()

        if not file_path_from_clipboard:
            return False

        destination_path = self.model.filePath(destination_index)
        if destination_path:
            pass
        else:
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
                    # Handle the case where the file copy fails
                    return False
            elif reply == QMessageBox.No:
                # Handle the case where the user chooses not to replace the file
                # You can add your custom logic here
                return False
            else:
                # Handle the case where the user cancels the operation
                # You can add your custom logic here
                return False
        else:
            try:
                shutil.copyfile(file_path_from_clipboard, new_file_name)
                return True
            except shutil.Error as e:
                # Handle the case where the file copy fails
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
            if self.model.isDir(index):
                QDir(path).removeRecursively()
            else:
                QFile(path).remove()

    def copy_audio_path(self, index, to_clipboard):
        if to_clipboard:
            file_path = self.model.filePath(index)
            file_path = os.path.relpath(file_path, self.tree_directory)
            file_path = file_path.replace('\\', '/')
            file_path = file_path.lower()
            root, ext = os.path.splitext(file_path)
            file_path = root + '.vsnd'
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(file_path)
        else:
            file_path = self.model.filePath(index)
            file_path = os.path.relpath(file_path, self.tree_directory)
            file_path = file_path.replace('\\', '/')
            file_path = file_path.lower()
            root, ext = os.path.splitext(file_path)
            file_path = root + '.vsnd'
            return file_path

    def copy_smartprop_path(self, index, to_clipboard):
        if to_clipboard:
            file_path = self.model.filePath(index)
            file_path = os.path.relpath(file_path, self.rootpath)
            file_path = file_path.replace('\\', '/')
            file_path = file_path.lower()
            root, ext = os.path.splitext(file_path)
            file_path = root + '.vsmart'
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(file_path)
        else:
            file_path = self.model.filePath(index)
            file_path = os.path.relpath(file_path, self.rootpath)
            file_path = file_path.replace('\\', '/')
            file_path = file_path.lower()
            root, ext = os.path.splitext(file_path)
            file_path = root + '.vsmart'
            return file_path

    def delete_selected_items(self):
        indexes = self.tree.selectionModel().selectedIndexes()
        if not indexes:
            return

        paths = [self.model.filePath(index) for index in indexes if index.column() == CustomFileSystemModel.NAME_COLUMN]
        reply = QMessageBox.question(self, 'Remove Items', f"Are you sure you want to remove the selected items?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for path in paths:
                if QDir(path).exists():
                    QDir(path).removeRecursively()
                else:
                    QFile(path).remove()

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