import os
import sys
import json
import shutil
import re
from PySide6.QtCore import Qt, QUrl, QSortFilterProxyModel, QRegularExpression
from PySide6.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QInputDialog, QMenu
from PySide6.QtGui import QDesktopServices, QGuiApplication

# Import Explorer from the main explorer module instead of FileTreeManager
from src.explorer.main import Explorer

# Import UI definition (generated from ui_browser.ui)
from src.explorer.browser.ui_main import Ui_MainWindow
# Import additional actions
from src.explorer.actions import QuickVmdlFile, QuickConfigFile
from src.explorer.common import audio_extensions, model_extensions
from src.settings.main import get_settings_value, set_settings_value

def get_editor_or_default(editor_value):
    return editor_value if editor_value else "Hammer5Tools"

class FileBrowser(QMainWindow):
    def __init__(self, parent=None, root=None, extension=None, editor=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("File Browser")

        # Instead of initializing the FileTreeManager, we now initialize Explorer.
        self.explorer = Explorer(parent=self, tree_directory=root, addon=None, editor_name=editor)
        self.ui.filetree_container.layout().addWidget(self.explorer.tree)

        self.root = root
        self.extension = extension
        self.editor = editor
        self.recent_files = []   # List of dicts: {'display': str, 'path': str}
        self.favorite_paths = [] # Same as above
        self.max_recent = 20
        self.lastFocusedFile = None
        self.path_history = []
        self.current_path_index = -1
        self.max_history = 50

        # Set up a QSortFilterProxyModel for filtering the Explorer's model
        self.filterProxyModel = QSortFilterProxyModel(self)
        self.filterProxyModel.setSourceModel(self.explorer.model)
        self.filterProxyModel.setDynamicSortFilter(True)
        # We will filter by name only, i.e. column 0 in the underlying model
        self.filterProxyModel.setFilterKeyColumn(0)
        # Ensure we ignore case
        self.filterProxyModel.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # Make the tree in Explorer use our filterProxyModel
        self.explorer.tree.setModel(self.filterProxyModel)

        self.loadConfig()
        # Override the path field if root is provided:
        if self.root:
            self.ui.path.setText(self.root)
        if not self.ui.path.text():
            self.ui.path.setText(os.getcwd())

        self.connectSignals()
        self.populateRecentList()
        self.populateFavoritesList()
        self.loadFileTree()
        self.setupContextMenus()
        self.setupDragAndDrop()

    def loadConfig(self):
        try:
            editor_key = get_editor_or_default(self.editor)
            if not self.root:
                self.root = get_settings_value(f"{editor_key}\\FileBrowser", "Root")
            if not self.extension:
                self.extension = get_settings_value(f"{editor_key}\\FileBrowser", "Extension")
            last_path = get_settings_value(f"{editor_key}\\FileBrowser", "LastPath")
            recent_str = get_settings_value(f"{editor_key}\\FileBrowser", "RecentFiles", default="[]")
            favorites_str = get_settings_value(f"{editor_key}\\FileBrowser", "FavoriteFiles", default="[]")
            try:
                self.recent_files = json.loads(recent_str)
            except:
                self.recent_files = []
            try:
                self.favorite_paths = json.loads(favorites_str)
            except:
                self.favorite_paths = []
            if last_path and os.path.exists(last_path):
                self.ui.path.setText(last_path)
                if hasattr(self.explorer, 'add_to_cache_queue'):
                    self.explorer.add_to_cache_queue(last_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load configuration:\n{str(e)}")

    def saveConfig(self):
        try:
            editor_key = get_editor_or_default(self.editor)
            self.recent_files = self.recent_files[:self.max_recent]
            recents_data = json.dumps(self.recent_files)
            favorites_data = json.dumps(self.favorite_paths)
            set_settings_value(f"{editor_key}\\FileBrowser", "RecentFiles", recents_data)
            set_settings_value(f"{editor_key}\\FileBrowser", "FavoriteFiles", favorites_data)
            set_settings_value(f"{editor_key}\\FileBrowser", "LastPath", self.ui.path.text())
            if self.root:
                set_settings_value(f"{editor_key}\\FileBrowser", "Root", self.root)
            if self.extension:
                set_settings_value(f"{editor_key}\\FileBrowser", "Extension", self.extension)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save configuration:\n{str(e)}")

    def connectSignals(self):
        self.ui.path.returnPressed.connect(self.loadFileTree)
        self.ui.filter.textChanged.connect(self.applyFilter)
        self.ui.subdir.stateChanged.connect(self.applyFilter)
        self.ui.new_file.clicked.connect(self.createNewFile)
        self.ui.open_file.clicked.connect(self.openFile)
        self.ui.add_to_favorites.clicked.connect(self.addToFavorites)
        self.ui.up_dir.clicked.connect(self.navigateUp)
        self.ui.actionNew_file.triggered.connect(self.createNewFile)
        self.ui.actionOpen_file.triggered.connect(self.openFile)
        self.ui.actionAdd_To_Favorites.triggered.connect(self.addToFavorites)
        self.ui.actionClear_All_Recent.triggered.connect(self.clearRecent)
        self.ui.actionClear_All_Favorites.triggered.connect(self.clearFavorites)
        self.ui.actionOpen_current_path_in_Explorer.triggered.connect(self.openCurrentPath)
        self.ui.recent_list.itemDoubleClicked.connect(self.openRecentItem)
        self.ui.favorites_list.itemDoubleClicked.connect(self.openFavoriteItem)
        self.ui.recent_list.itemClicked.connect(
            lambda item: self.focusOnFileInTree(item.data(Qt.UserRole)["path"])
        )
        self.ui.favorites_list.itemClicked.connect(
            lambda item: self.focusOnFileInTree(item.data(Qt.UserRole)["path"])
        )
        # Connect Explorer tree signals in place of ui.filetree signals.
        self.explorer.tree.doubleClicked.connect(self.treeItemDoubleClicked)

    def setupContextMenus(self):
        self.explorer.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.explorer.tree.customContextMenuRequested.connect(self.showFileTreeContextMenu)
        self.ui.recent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.recent_list.customContextMenuRequested.connect(self.showRecentContextMenu)
        self.ui.favorites_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.favorites_list.customContextMenuRequested.connect(self.showFavoritesContextMenu)

    def setupDragAndDrop(self):
        self.explorer.tree.setDragEnabled(True)
        self.explorer.tree.setAcceptDrops(True)
        self.explorer.tree.setDropIndicatorShown(True)
        self.explorer.tree.setDragDropMode(self.explorer.tree.DragDropMode.DragDrop)
        self.ui.favorites_list.setDragEnabled(True)
        self.ui.recent_list.setDragEnabled(True)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    self.openFileWithDefaultApp(file_path)
                elif os.path.isdir(file_path):
                    self.ui.path.setText(file_path)
                    self.loadFileTree()
            event.acceptProposedAction()

    def loadFileTree(self):
        directory = self.ui.path.text().strip() or os.getcwd()
        self.addToPathHistory(directory)

        # Update the root index in the source model
        dirIndex = self.explorer.model.index(directory)
        if dirIndex.isValid():
            # Map the source model index through the proxy
            proxyIndex = self.filterProxyModel.mapFromSource(dirIndex)
            self.explorer.tree.setRootIndex(proxyIndex)
        else:
            # Fallback if invalid directory
            QMessageBox.warning(self, "Invalid Directory", f"Directory does not exist:\n{directory}")

        # After setting the root, apply any current filter
        self.applyFilter()

    def addToPathHistory(self, path):
        if self.path_history and self.path_history[-1] == path:
            return
        self.path_history.append(path)
        self.current_path_index = len(self.path_history) - 1
        if len(self.path_history) > self.max_history:
            self.path_history = self.path_history[-self.max_history:]
            self.current_path_index = len(self.path_history) - 1

    def applyFilter(self):
        filter_text = self.ui.filter.text().strip()
        include_subdir = self.ui.subdir.isChecked()

        # For Qt 6, we can do this to filter recursively
        if hasattr(self.filterProxyModel, 'setRecursiveFilteringEnabled'):
            self.filterProxyModel.setRecursiveFilteringEnabled(include_subdir)

        # Use wildcards or a RegularExpression-based search
        if filter_text:
            # Example: match anywhere in the filename
            pattern = f".*{re.escape(filter_text)}.*"
            regex = QRegularExpression(pattern, QRegularExpression.CaseInsensitiveOption)
            self.filterProxyModel.setFilterRegularExpression(regex)
        else:
            # Clear any filter
            self.filterProxyModel.setFilterRegularExpression(QRegularExpression())

    def navigateUp(self):
        current_path = self.ui.path.text().strip()
        if not current_path:
            return
        parent_dir = os.path.dirname(current_path)
        if parent_dir and os.path.exists(parent_dir):
            self.ui.path.setText(parent_dir)
            self.loadFileTree()

    def createNewFile(self):
        selected_index = self.explorer.tree.currentIndex()
        # We must map through the proxy to the underlying model
        source_index = self.filterProxyModel.mapToSource(selected_index)
        selected_path = self.explorer.model.filePath(source_index) if source_index.isValid() else None

        directory = None
        if selected_path and os.path.isdir(selected_path):
            directory = selected_path
        elif selected_path and os.path.isfile(selected_path):
            directory = os.path.dirname(selected_path)

        if not directory:
            directory = self.ui.path.text().strip() or os.getcwd()

        filename, ok = QInputDialog.getText(self, "Create New File", "Enter filename:", text="newfile")
        if not ok or not filename:
            return

        if self.extension:
            filename = f"{filename}.{self.extension}"

        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            reply = QMessageBox.question(self, "File Exists", f"File {filename} already exists. Overwrite?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
        try:
            with open(file_path, "w") as f:
                f.write("")
            self.addToRecent(file_path)
            self.loadFileTree()
            self.focusOnFileInTree(file_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create file:\n{str(e)}")

    def openFile(self):
        starting_dir = self.ui.path.text().strip() or os.getcwd()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", starting_dir)
        if file_name:
            self.openFileWithDefaultApp(file_name)

    def openFileWithDefaultApp(self, file_path):
        if os.path.exists(file_path):
            self.addToRecent(file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        else:
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")

    def addToFavorites(self):
        selected_index = self.explorer.tree.currentIndex()
        source_index = self.filterProxyModel.mapToSource(selected_index)
        file_path = self.explorer.model.filePath(source_index) if source_index.isValid() else None

        if file_path and os.path.exists(file_path) and not self._inFavorites(file_path):
            display_name = self._computeDisplayName(file_path)
            self.favorite_paths.append({"display": display_name, "path": file_path})
            self.populateFavoritesList()
            self.saveConfig()

    def addToFavoritesFromPath(self, file_path):
        if file_path and os.path.exists(file_path) and not self._inFavorites(file_path):
            display_name = self._computeDisplayName(file_path)
            self.favorite_paths.append({"display": display_name, "path": file_path})
            self.populateFavoritesList()
            self.saveConfig()

    def addToRecent(self, file_path):
        self._removePathFromList(self.recent_files, file_path)
        display_name = self._computeDisplayName(file_path)
        self.recent_files.insert(0, {"display": display_name, "path": file_path})
        if len(self.recent_files) > self.max_recent:
            self.recent_files = self.recent_files[:self.max_recent]
        self.populateRecentList()
        self.saveConfig()

    def clearRecent(self):
        self.recent_files = []
        self.ui.recent_list.clear()
        self.saveConfig()

    def clearFavorites(self):
        self.favorite_paths = []
        self.ui.favorites_list.clear()
        self.saveConfig()

    def openCurrentPath(self):
        directory = self.ui.path.text().strip() or os.getcwd()
        QDesktopServices.openUrl(QUrl.fromLocalFile(directory))

    def treeItemDoubleClicked(self, proxied_index):
        # Convert from proxy to source
        src_index = self.filterProxyModel.mapToSource(proxied_index)
        file_path = self.explorer.model.filePath(src_index)
        if not file_path:
            return
        if os.path.isdir(file_path):
            self.ui.path.setText(file_path)
            self.loadFileTree()
        elif os.path.isfile(file_path):
            self.openFileWithDefaultApp(file_path)

    def openRecentItem(self, item):
        path_info = item.data(Qt.UserRole)
        if not path_info:
            return
        file_path = path_info["path"]
        if os.path.exists(file_path):
            self.focusOnFileInTree(file_path)
        else:
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            self._removePathFromList(self.recent_files, file_path)
            self.populateRecentList()
            self.saveConfig()

    def openFavoriteItem(self, item):
        path_info = item.data(Qt.UserRole)
        if not path_info:
            return
        file_path = path_info["path"]
        if os.path.exists(file_path):
            self.focusOnFileInTree(file_path)
        else:
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            self._removePathFromList(self.favorite_paths, file_path)
            self.populateFavoritesList()
            self.saveConfig()

    def focusOnFileInTree(self, file_path):
        if not os.path.exists(file_path):
            return
        self.lastFocusedFile = file_path

        # Convert path to a model index
        src_index = self.explorer.model.index(file_path)
        if not src_index.isValid():
            return

        # Map to proxy
        proxy_index = self.filterProxyModel.mapFromSource(src_index)
        if proxy_index.isValid():
            self.explorer.tree.setCurrentIndex(proxy_index)
            self.explorer.tree.scrollTo(proxy_index)

    def _computeDisplayName(self, path_str):
        norm_path = os.path.normpath(path_str)
        parts = norm_path.split(os.sep)
        if len(parts) >= 2:
            return parts[-2] + os.sep + parts[-1]
        else:
            return parts[-1] if parts else path_str

    def _removePathFromList(self, items_list, file_path):
        for idx, info in enumerate(items_list):
            if info.get("path") == file_path:
                items_list.pop(idx)
                break

    def _inFavorites(self, file_path):
        return any(x for x in self.favorite_paths if x["path"] == file_path)

    def showRecentContextMenu(self, position):
        item = self.ui.recent_list.itemAt(position)
        if not item:
            return
        path_info = item.data(Qt.UserRole)
        if not path_info:
            return
        file_path = path_info["path"]
        menu = QMenu(self.ui.recent_list)
        open_action = menu.addAction("Open with Default Program")
        open_action.triggered.connect(lambda: self.openFileWithDefaultApp(file_path))
        copy_action = menu.addAction("Copy Path to Clipboard")
        copy_action.triggered.connect(lambda: self.copyFile(file_path))
        explorer_action = menu.addAction("Open in Explorer")
        explorer_action.triggered.connect(lambda: self.openContainingFolder(file_path))
        remove_action = menu.addAction("Remove from List")
        remove_action.triggered.connect(lambda: self._removeFromRecentAndRefresh(file_path))
        menu.exec_(self.ui.recent_list.mapToGlobal(position))

    def showFavoritesContextMenu(self, position):
        item = self.ui.favorites_list.itemAt(position)
        if not item:
            return
        path_info = item.data(Qt.UserRole)
        if not path_info:
            return
        file_path = path_info["path"]
        menu = QMenu(self.ui.favorites_list)
        open_action = menu.addAction("Open with Default Program")
        open_action.triggered.connect(lambda: self.openFileWithDefaultApp(file_path))
        copy_action = menu.addAction("Copy Path to Clipboard")
        copy_action.triggered.connect(lambda: self.copyFile(file_path))
        explorer_action = menu.addAction("Open in Explorer")
        explorer_action.triggered.connect(lambda: self.openContainingFolder(file_path))
        remove_action = menu.addAction("Remove from List")
        remove_action.triggered.connect(lambda: self._removeFromFavoritesAndRefresh(file_path))
        menu.exec_(self.ui.favorites_list.mapToGlobal(position))

    def populateRecentList(self):
        self.ui.recent_list.clear()
        valid_items = []
        for item in self.recent_files:
            if not isinstance(item, dict):
                continue
            path_value = item.get("path")
            if path_value and os.path.exists(path_value):
                valid_items.append(item)
        self.recent_files = valid_items
        for path_info in self.recent_files:
            display_name = path_info.get("display", "")
            list_index = self.ui.recent_list.count()
            self.ui.recent_list.addItem(display_name)
            self.ui.recent_list.item(list_index).setData(Qt.UserRole, path_info)
            self.ui.recent_list.item(list_index).setToolTip(path_info["path"])

    def populateFavoritesList(self):
        self.ui.favorites_list.clear()
        valid_items = []
        for item in self.favorite_paths:
            if not isinstance(item, dict):
                continue
            path_value = item.get("path")
            if path_value and os.path.exists(path_value):
                valid_items.append(item)
        self.favorite_paths = valid_items
        for path_info in self.favorite_paths:
            display_name = path_info.get("display", "")
            list_index = self.ui.favorites_list.count()
            self.ui.favorites_list.addItem(display_name)
            self.ui.favorites_list.item(list_index).setData(Qt.UserRole, path_info)
            self.ui.favorites_list.item(list_index).setToolTip(path_info["path"])

    def showFileTreeContextMenu(self, position):
        # Because we are using a proxy, we must convert the proxy index to the source model's index
        proxy_index = self.explorer.tree.indexAt(position)
        if not proxy_index.isValid():
            return
        src_index = self.filterProxyModel.mapToSource(proxy_index)

        file_path = self.explorer.model.filePath(src_index)
        if not file_path or not os.path.exists(file_path):
            return

        menu = QMenu(self.explorer.tree)
        open_action = menu.addAction("Open")
        open_action.triggered.connect(lambda: self.openFileWithDefaultApp(file_path))
        fav_action = menu.addAction("Add to Favorites")
        fav_action.triggered.connect(lambda: self.addToFavoritesFromPath(file_path))

        if os.path.isdir(file_path):
            root_action = menu.addAction("Set as Root")
            root_action.triggered.connect(lambda: self.setPathAsRoot(file_path))
            exp_action = menu.addAction("Open in Explorer")
            exp_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)))
        if os.path.isfile(file_path):
            cont_action = menu.addAction("Open Containing Folder")
            cont_action.triggered.connect(lambda: self.openContainingFolder(file_path))
            dup_action = menu.addAction("Duplicate File")
            dup_action.triggered.connect(lambda: self.duplicateFileAndRefresh(file_path))
            copy_action = menu.addAction("Copy File")
            copy_action.triggered.connect(lambda: self.copyFile(file_path))
            rel_action = menu.addAction("Copy Relative Path")
            rel_action.triggered.connect(lambda: self.copyRelativePath(file_path))
            if file_path.lower().endswith(tuple(audio_extensions)):
                audio_action = menu.addAction("Copy Audio Path")
                audio_action.triggered.connect(lambda: self.copyAudioPath(file_path))
            if file_path.lower().endswith(".vmdl"):
                batch_action = menu.addAction("Quick Batch File")
                batch_action.triggered.connect(lambda: QuickConfigFile(file_path))
            if any(file_path.lower().endswith(ext) for ext in model_extensions):
                vmdl_action = menu.addAction("Quick VMDL File")
                vmdl_action.triggered.connect(lambda: QuickVmdlFile(file_path))

        menu.exec_(self.explorer.tree.mapToGlobal(position))

    def setPathAsRoot(self, path):
        if os.path.isdir(path):
            self.ui.path.setText(path)
            self.loadFileTree()

    def openContainingFolder(self, file_path):
        if os.path.exists(file_path):
            parent = os.path.dirname(file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(parent))

    def _removeFromRecentAndRefresh(self, file_path):
        self._removePathFromList(self.recent_files, file_path)
        self.populateRecentList()
        self.saveConfig()

    def _removeFromFavoritesAndRefresh(self, file_path):
        self._removePathFromList(self.favorite_paths, file_path)
        self.populateFavoritesList()
        self.saveConfig()

    def duplicateFile(self, file_path):
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        match = re.match(r'^(.*?)(?:_(\d+))?$', name)
        new_base = match.group(1) if match else name
        counter = 1
        new_file = os.path.join(os.path.dirname(file_path), f"{new_base}_{counter:02d}{ext}")
        while os.path.exists(new_file):
            counter += 1
            new_file = os.path.join(os.path.dirname(file_path), f"{new_base}_{counter:02d}{ext}")
        try:
            shutil.copyfile(file_path, new_file)
            return new_file
        except Exception as e:
            QMessageBox.warning(self, "Duplication Error", f"Failed to duplicate file:\n{e}")
            return None

    def duplicateFileAndRefresh(self, file_path):
        new_file = self.duplicateFile(file_path)
        if new_file:
            self.loadFileTree()
            self.focusOnFileInTree(new_file)

    def copyFile(self, file_path):
        QGuiApplication.clipboard().setText(file_path)

    def copyRelativePath(self, file_path):
        base = self.root if self.root else os.getcwd()
        rel = os.path.relpath(file_path, base)
        QGuiApplication.clipboard().setText(rel)

    def copyAudioPath(self, file_path):
        base = self.root if self.root else os.getcwd()
        rel = os.path.relpath(file_path, base)
        rel = rel.replace("\\", "/").lower()
        root_part, _ = os.path.splitext(rel)
        QGuiApplication.clipboard().setText(root_part + ".vsnd")

    def closeEvent(self, event):
        self.saveConfig()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileBrowser()
    window.show()
    sys.exit(app.exec())