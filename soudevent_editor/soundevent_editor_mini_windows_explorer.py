import os.path

from PySide6.QtWidgets import QMainWindow, QTreeView, QVBoxLayout, QFileSystemModel, QStyledItemDelegate, QHeaderView, QMenu, QInputDialog, QMessageBox
from PySide6.QtGui import QIcon, QAction, QDesktopServices, QMouseEvent, QKeyEvent, QGuiApplication
from PySide6.QtCore import Qt, QDir, QMimeData, QUrl, QFile, QModelIndex, QFileInfo, QItemSelectionModel

class CustomFileSystemModel(QFileSystemModel):
    def data(self, index, role):
        if role == Qt.DecorationRole:
            if self.isDir(index) and index.column() != 1:  # Assuming column 1 is the size column
                return QIcon('://icons/folder_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg')
        elif role == Qt.DisplayRole and index.column() == 0:  # Assuming column 0 is the name column
            file_name = super().data(index, role)
            if not self.isDir(index):
                file_name = QFileInfo(file_name).completeBaseName()  # Remove the file extension
            return file_name
        return super().data(index, role)

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

        for url in data.urls():
            source_path = url.toLocalFile()
            file_name = QDir(source_path).dirName()
            destination_path = self.filePath(parent) + '/' + file_name
            if QDir(source_path).exists():
                QDir().rename(source_path, destination_path)
            else:
                QFile().rename(source_path, destination_path)
        source_path = data.urls()[0].toLocalFile()
        print(source_path)
        return source_path



    def setData(self, index, value, role):
        if role == Qt.EditRole:
            old_path = self.filePath(index)
            new_path = QDir(old_path).absoluteFilePath(value)
            if QFile(old_path).rename(new_path):
                self.dataChanged.emit(index, index)
                return True
        return super().setData(index, value, role)

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid():
            return Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | default_flags
        return default_flags

class SoundEvent_Editor_MiniWindowsExplorer(QMainWindow):
    def __init__(self, parent=None, tree_directory=None):
        super().__init__(parent)
        self.model = CustomFileSystemModel()
        self.model.setRootPath(tree_directory)

        self.tree_directory = tree_directory

        # Set up the tree view
        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(tree_directory))

        # Hide all columns except "Name" (column 0) and "Size" (column 1)
        for column in range(self.model.columnCount()):
            if column not in (0, 1):
                self.tree.setColumnHidden(column, True)

        # Set up the layout for the widget
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Set the delegate for padding
        self.tree.setItemDelegateForColumn(1, QStyledItemDelegate())

        # Set the default width of the size column to 15% of the tree view's width
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Interactive)

        # Enable drag and drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QTreeView.InternalMove)

        # Enable multi-selection
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)

        # Connect context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        # Connect mouse events
        self.tree.viewport().installEventFilter(self)

        # Connect key events
        self.tree.installEventFilter(self)




    def closeEvent(self, event):
        del self.model  # Explicitly delete the CustomFileSystemModel instance
        event.accept()

    def eventFilter(self, source, event):
        if event.type() == QMouseEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                index = self.tree.indexAt(event.pos())
                if not index.isValid():
                    self.tree.clearSelection()
            elif event.button() == Qt.RightButton:
                index = self.tree.indexAt(event.pos())
                if not index.isValid():
                    self.tree.clearSelection()
        elif event.type() == QKeyEvent.KeyPress:
            if event.key() == Qt.Key_Delete:
                self.delete_selected_items()
        return super().eventFilter(source, event)

    def open_context_menu(self, position):
        index = self.tree.indexAt(position)
        menu = QMenu()

        if index.isValid():
            # Context menu for folders and files
            if self.model.isDir(index):
                rename_action = QAction("Rename Folder", self)
                rename_action.triggered.connect(lambda: self.rename_item(index))
                menu.addAction(rename_action)

                delete_action = QAction("Remove Folder", self)
                delete_action.triggered.connect(lambda: self.delete_item(index))
                menu.addAction(delete_action)
            else:
                open_action = QAction("Open File", self)
                open_action.triggered.connect(lambda: self.open_file(index))
                menu.addAction(open_action)

                rename_action = QAction("Rename File", self)
                rename_action.triggered.connect(lambda: self.rename_item(index))
                menu.addAction(rename_action)

                delete_action = QAction("Remove File", self)
                delete_action.triggered.connect(lambda: self.delete_item(index))
                menu.addAction(delete_action)

                copy_path_action = QAction("Copy File Path", self)
                copy_path_action.triggered.connect(lambda: self.copy_file_path(index))
                menu.addAction(copy_path_action)
        else:
            # Context menu for empty space
            create_folder_action = QAction("Create Folder", self)
            create_folder_action.triggered.connect(lambda: self.create_folder(self.tree.rootIndex()))
            menu.addAction(create_folder_action)

        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def open_file(self, index):
        file_path = self.model.filePath(index)
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def rename_item(self, index):
        old_name = self.model.fileName(index)
        new_name, ok = QInputDialog.getText(self, "Rename Item", "New name:", text=old_name)
        if ok and new_name:
            self.model.setData(index, new_name, Qt.EditRole)

    def delete_item(self, index):
        path = self.model.filePath(index)
        reply = QMessageBox.question(self, 'Remove Item', f"Are you sure you want to remove '{path}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.model.isDir(index):
                QDir(path).removeRecursively()
            else:
                QFile(path).remove()

    def delete_selected_items(self):
        indexes = self.tree.selectionModel().selectedIndexes()
        if not indexes:
            return

        paths = [self.model.filePath(index) for index in indexes if index.column() == 0]
        reply = QMessageBox.question(self, 'Remove Items', f"Are you sure you want to remove the selected items?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for path in paths:
                if QDir(path).exists():
                    QDir(path).removeRecursively()
                else:
                    QFile(path).remove()


    def copy_file_path(self, index):
        file_path = self.model.filePath(index)
        file_path = os.path.relpath(file_path, self.tree_directory)
        file_path = file_path.replace('\\', '/')
        file_path = file_path.lower()
        root, ext = os.path.splitext(file_path)
        file_path = root + '.vsnd'
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(file_path)

    def create_folder(self, parent_index):
        parent_path = self.model.filePath(parent_index)
        default_folder_name = "New Folder"
        new_folder_path = QDir(parent_path).absoluteFilePath(default_folder_name)

        # Ensure the folder name is unique
        counter = 1
        while QDir(new_folder_path).exists():
            new_folder_path = QDir(parent_path).absoluteFilePath(f"{default_folder_name} ({counter})")
            counter += 1

        QDir(parent_path).mkdir(QFileInfo(new_folder_path).fileName())

        # Find the index of the newly created folder
        new_folder_index = self.model.index(new_folder_path)

        # Switch to renaming mode
        self.tree.edit(new_folder_index)