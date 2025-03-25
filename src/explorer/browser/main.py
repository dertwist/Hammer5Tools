import os
import sys
import json
import shutil
import re
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QInputDialog
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

        # Instead of initializing the FileTreeManager, we now initialize Explorer
        # Explorer is expected to provide a QTreeView via its "tree" property and
        # similar helper functions as FileTreeManager.
        self.explorer = Explorer(parent=self, tree_directory=root, addon=None, editor_name=editor)
        # Embed the Explorer widget into the designated container in the UI.
        # For example, if Ui_MainWindow has a layout placeholder "filetree_container":
        self.ui.filetree_container.layout().addWidget(self.explorer.tree)

        # Use the Explorer's tree in lieu of ui.filetree from now on.
        # (Adjust any additional adapter code as needed.)

        # Store incoming arguments or load from settings.
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
                # Delegate cache usage to Explorer if needed.
                # For example, if Explorer has an add_to_cache_queue method:
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
        self.ui.recent_list.itemClicked.connect(lambda item: self.focusOnFileInTree(item.data(Qt.UserRole)["path"]))
        self.ui.favorites_list.itemClicked.connect(lambda item: self.focusOnFileInTree(item.data(Qt.UserRole)["path"]))

        # Connect Explorer tree signals in place of ui.filetree signals.
        self.explorer.tree.itemDoubleClicked.connect(self.treeItemDoubleClicked)
        # If Explorer emits additional signals (like expanded), connect accordingly.

    def setupContextMenus(self):
        # Configure context menus on the Explorer tree instead of the original filetree widget.
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
        # Assuming the Explorer tree supports internal drag‐drop movement:
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
        # Delegates the loading to Explorer. If Explorer does not expose a load method,
        # update the tree model's root index manually.
        if not self.ui.filter.text():
            # If Explorer has a load method, use it.
            if hasattr(self.explorer, 'load'):
                self.explorer.load(directory)
            else:
                self.explorer.model.setRootPath(directory)
                self.explorer.tree.setRootIndex(self.explorer.model.index(directory))
        else:
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
        filter_text = self.ui.filter.text().lower()
        include_subdir = self.ui.subdir.isChecked()
        current_path = self.ui.path.text().strip() or os.getcwd()
        # Clear the Explorer tree (if supported)
        if hasattr(self.explorer, 'clear'):
            self.explorer.clear()
        # When no filter is applied, simply load the directory.
        if not filter_text:
            self.loadFileTree()
            if self.lastFocusedFile and os.path.exists(self.lastFocusedFile):
                self.focusOnFileInTree(self.lastFocusedFile)
            return
        # If Explorer provides filtering/search functionality,
        # then use that instead of the old filetree_manager methods.
        if include_subdir:
            # For deep search; assuming explorer has a perform_deep_search method.
            if hasattr(self.explorer, 'perform_deep_search'):
                matches = self.explorer.perform_deep_search(current_path, filter_text)
            else:
                matches = []
        else:
            if hasattr(self.explorer, 'perform_shallow_search'):
                matches = self.explorer.perform_shallow_search(current_path, filter_text)
            else:
                matches = []
        # Repopulate the Explorer tree with the matching items.
        # (You may need to adjust this section depending on Explorer's API.)
        for full_path, rel_path in matches:
            # Create a temporary tree widget item and add it into the Explorer tree.
            # This example assumes that Explorer.tree is a QTreeWidget.
            from PySide6.QtWidgets import QTreeWidgetItem
            item = QTreeWidgetItem(self.explorer.tree)
            item.setText(0, rel_path)
            item.setData(0, Qt.UserRole, full_path)
            item.setToolTip(0, full_path)
            if os.path.isdir(full_path):
                # Assume Explorer handles icons internally; otherwise add your icon.
                pass
            else:
                try:
                    from PySide6.QtCore import QFileInfo
                    file_info = QFileInfo(full_path)
                    size = self.explorer.format_file_size(file_info.size()) if hasattr(self.explorer, 'format_file_size') else ""
                    modified = file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss")
                    item.setText(1, size)
                    item.setText(2, modified)
                except Exception:
                    pass

    def navigateUp(self):
        current_path = self.ui.path.text().strip()
        if not current_path:
            return
        parent_dir = os.path.dirname(current_path)
        if parent_dir and os.path.exists(parent_dir):
            self.ui.path.setText(parent_dir)
            self.loadFileTree()

    def createNewFile(self):
        # Determine the directory: if a tree item is selected, use its path.
        selected_item = self.explorer.tree.currentItem()
        if selected_item:
            selected_path = selected_item.data(0, Qt.UserRole)
            directory = selected_path if os.path.isdir(selected_path) else os.path.dirname(selected_path)
        else:
            directory = self.ui.path.text().strip() or os.getcwd()
        filename, ok = QInputDialog.getText(self, "Create New File", "Enter filename:", text="newfile")
        filename = f"{filename}.{self.extension}"
        if not ok or not filename:
            return
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
            # If the Explorer holds any cache information, refresh it.
            if hasattr(self.explorer, 'cache_timestamps') and directory in self.explorer.cache_timestamps:
                del self.explorer.cache_timestamps[directory]
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
        selected = self.explorer.tree.currentItem()
        if selected:
            file_path = selected.data(0, Qt.UserRole)
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

    def treeItemDoubleClicked(self, item, column):
        file_path = item.data(0, Qt.UserRole)
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
            if os.path.isdir(file_path):
                self.ui.path.setText(file_path)
                self.loadFileTree()
            else:
                self.openFileWithDefaultApp(file_path)
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
            if os.path.isdir(file_path):
                self.ui.path.setText(file_path)
                self.loadFileTree()
            else:
                self.openFileWithDefaultApp(file_path)
        else:
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            self._removePathFromList(self.favorite_paths, file_path)
            self.populateFavoritesList()
            self.saveConfig()

    def focusOnFileInTree(self, file_path):
        if not os.path.exists(file_path):
            return
        self.lastFocusedFile = file_path
        # Delegate focus logic to the Explorer
        if hasattr(self.explorer, 'select_tree_item'):
            self.explorer.select_tree_item(file_path)
        else:
            # Fallback: try to find and select the item manually.
            if self.explorer.tree.findItems(os.path.basename(file_path), Qt.MatchRecursive):
                item = self.explorer.tree.findItems(os.path.basename(file_path), Qt.MatchRecursive)[0]
                self.explorer.tree.setCurrentItem(item)
                self.explorer.tree.scrollToItem(item)
            else:
                directory = os.path.dirname(file_path)
                if directory != self.ui.path.text():
                    self.ui.path.setText(directory)
                    self.loadFileTree()
                # If Explorer has a method to expand a partial path, use it.
                if hasattr(self.explorer, 'expand_partial_path'):
                    self.explorer.expand_partial_path(file_path)

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
        # Use the Explorer's tree instead of ui.filetree.
        item = self.explorer.tree.itemAt(position)
        if not item:
            return
        file_path = item.data(0, Qt.UserRole)
        if not file_path or not os.path.exists(file_path):
            return
        # Create the context menu based on the current file.
        menu = self.explorer.tree.createStandardContextMenu()  # Alternatively, build your own menu.
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

    def showRecentContextMenu(self, position):
        item = self.ui.recent_list.itemAt(position)
        if not item:
            return
        path_info = item.data(Qt.UserRole)
        if not path_info:
            return
        file_path = path_info["path"]
        menu = self.ui.recent_list.createStandardContextMenu()
        open_action = menu.addAction("Open")
        open_action.triggered.connect(lambda: self.openFileWithDefaultApp(file_path))
        rem_action = menu.addAction("Remove from Recent")
        rem_action.triggered.connect(lambda: self._removeFromRecentAndRefresh(file_path))
        if os.path.exists(file_path):
            fav_action = menu.addAction("Add to Favorites")
            fav_action.triggered.connect(lambda: self.addToFavoritesFromPath(file_path))
            if os.path.isfile(file_path):
                cont_action = menu.addAction("Open Containing Folder")
                cont_action.triggered.connect(lambda: self.openContainingFolder(file_path))
        menu.exec_(self.ui.recent_list.mapToGlobal(position))

    def showFavoritesContextMenu(self, position):
        item = self.ui.favorites_list.itemAt(position)
        if not item:
            return
        path_info = item.data(Qt.UserRole)
        if not path_info:
            return
        file_path = path_info["path"]
        menu = self.ui.favorites_list.createStandardContextMenu()
        open_action = menu.addAction("Open")
        open_action.triggered.connect(lambda: self.openFileWithDefaultApp(file_path))
        rem_action = menu.addAction("Remove from Favorites")
        rem_action.triggered.connect(lambda: self._removeFromFavoritesAndRefresh(file_path))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            cont_action = menu.addAction("Open Containing Folder")
            cont_action.triggered.connect(lambda: self.openContainingFolder(file_path))
        menu.exec_(self.ui.favorites_list.mapToGlobal(position))

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

    def addToFavoritesFromPath(self, file_path):
        if file_path and os.path.exists(file_path) and not self._inFavorites(file_path):
            display_name = self._computeDisplayName(file_path)
            self.favorite_paths.append({"display": display_name, "path": file_path})
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