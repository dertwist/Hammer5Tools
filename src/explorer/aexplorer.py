import os
import sys
import json
import time
from datetime import datetime
from functools import partial
from collections import defaultdict
from PySide6.QtCore import Qt, QUrl, QDir, QFileInfo, QMimeData, QTimer
from PySide6.QtWidgets import (QMainWindow, QApplication, QMessageBox,
                               QFileDialog, QTreeWidgetItem, QMenu, QInputDialog)
from PySide6.QtGui import QDesktopServices, QIcon, QAction, QDrag
from src.explorer.ui_aexplorer import Ui_MainWindow

class ExplorerMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("File Explorer")
        self.config_file = os.path.join(os.path.expanduser("~"), ".aexplorer_config.json")
        self.recent_files = []
        self.favorite_paths = []
        self.max_recent = 20
        self.lastFocusedFile = None
        self.file_cache = {}
        self.cache_timestamps = {}
        self.cache_expiry = 30
        self.pending_cache_updates = set()
        self.cache_timer = QTimer(self)
        self.cache_timer.timeout.connect(self.updatePendingCaches)
        self.cache_timer.start(5000)
        self.path_history = []
        self.current_path_index = -1
        self.max_history = 50
        self.dir_mtimes = {}
        self.tree_item_index = {}
        self.loadConfig()
        self.setupFileTree()
        if not self.ui.path.text():
            self.ui.path.setText(os.getcwd())
        self.connectSignals()
        self.populateRecentList()
        self.populateFavoritesList()
        self.loadFileTree()
        self.setupContextMenus()
        self.setupDragAndDrop()

    def setupFileTree(self):
        self.ui.filetree.setHeaderLabels(["Name", "Size", "Modified"])
        self.ui.filetree.setColumnWidth(0, 300)
        self.ui.filetree.setSortingEnabled(True)

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
        self.ui.recent_list.itemClicked.connect(self.focusOnRecentItem)
        self.ui.favorites_list.itemClicked.connect(self.focusOnFavoriteItem)
        self.ui.filetree.itemDoubleClicked.connect(self.treeItemDoubleClicked)
        self.ui.filetree.itemExpanded.connect(self.onItemExpanded)

    def setupContextMenus(self):
        self.ui.filetree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.filetree.customContextMenuRequested.connect(self.showFileTreeContextMenu)
        self.ui.recent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.recent_list.customContextMenuRequested.connect(self.showRecentContextMenu)
        self.ui.favorites_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.favorites_list.customContextMenuRequested.connect(self.showFavoritesContextMenu)

    def setupDragAndDrop(self):
        self.ui.filetree.setDragEnabled(True)
        self.ui.filetree.setAcceptDrops(True)
        self.ui.filetree.setDropIndicatorShown(True)
        self.ui.filetree.setDragDropMode(self.ui.filetree.DragDropMode.DragDrop)
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

    def loadConfig(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.recent_files = config.get('recent', [])
                    self.favorite_paths = config.get('favorites', [])
                    last_path = config.get('last_path')
                    if last_path and os.path.exists(last_path):
                        self.ui.path.setText(last_path)
                        self.addToCacheQueue(last_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load configuration:\n{str(e)}")

    def saveConfig(self):
        try:
            config = {
                'recent': self.recent_files[:self.max_recent],
                'favorites': self.favorite_paths,
                'last_path': self.ui.path.text()
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save configuration:\n{str(e)}")

    def shortenPath(self, path):
        parts = path.replace('\\', '/').split('/')
        if len(parts) <= 2:
            return path
        shortened = '/'.join(parts[-3:])
        return shortened.replace('/', os.sep)

    def populateRecentList(self):
        self.ui.recent_list.clear()
        for path in self.recent_files:
            if os.path.exists(path):
                self.ui.recent_list.addItem(path)
                index = self.ui.recent_list.count() - 1
                self.ui.recent_list.item(index).setData(Qt.UserRole, path)
                self.ui.recent_list.item(index).setText(self.shortenPath(path))
                if os.path.isfile(path):
                    parent_dir = os.path.dirname(path)
                    self.addToCacheQueue(parent_dir)

    def populateFavoritesList(self):
        self.ui.favorites_list.clear()
        for path in self.favorite_paths:
            if os.path.exists(path):
                self.ui.favorites_list.addItem(path)
                index = self.ui.favorites_list.count() - 1
                self.ui.favorites_list.item(index).setData(Qt.UserRole, path)
                self.ui.favorites_list.item(index).setText(self.shortenPath(path))
                if os.path.isfile(path):
                    parent_dir = os.path.dirname(path)
                    self.addToCacheQueue(parent_dir)

    def addToCacheQueue(self, directory):
        if os.path.isdir(directory):
            self.pending_cache_updates.add(directory)

    def updatePendingCaches(self):
        if not self.pending_cache_updates:
            return
        dirs_to_process = list(self.pending_cache_updates)[:5]
        for directory in dirs_to_process:
            self.pending_cache_updates.remove(directory)
            self.updateDirectoryCache(directory)

    def updateDirectoryCache(self, directory):
        try:
            current_mtime = os.path.getmtime(directory)
            if directory in self.dir_mtimes and self.dir_mtimes[directory] == current_mtime:
                return
            self.dir_mtimes[directory] = current_mtime
            entries = os.listdir(directory)
            entries.sort(key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower()))
            dir_cache = {}
            for entry in entries:
                full_path = os.path.join(directory, entry)
                if os.path.isdir(full_path):
                    dir_cache[entry] = None
                else:
                    try:
                        file_info = QFileInfo(full_path)
                        dir_cache[entry] = {
                            'size': file_info.size(),
                            'modified': file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss"),
                            'is_file': True
                        }
                    except:
                        dir_cache[entry] = {'is_file': True}
            self.file_cache[directory] = dir_cache
            self.cache_timestamps[directory] = time.time()
        except Exception:
            pass

    def isCacheValid(self, directory):
        if directory not in self.cache_timestamps:
            return False
        if time.time() - self.cache_timestamps[directory] > self.cache_expiry:
            return False
        try:
            current_mtime = os.path.getmtime(directory)
            if directory in self.dir_mtimes and self.dir_mtimes[directory] != current_mtime:
                return False
        except:
            return False
        return True

    def loadFileTree(self):
        directory = self.ui.path.text().strip() or os.getcwd()
        self.ui.path.setText(directory)
        self.ui.filetree.clear()
        self.tree_item_index.clear()
        self.addToPathHistory(directory)
        if not self.ui.filter.text():
            try:
                self.populateFileTree(directory, self.ui.filetree)
                self.addToCacheQueue(directory)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Directory not found: {str(e)}")
        else:
            self.applyFilter()

    def addToPathHistory(self, path):
        if self.current_path_index < len(self.path_history) - 1:
            self.path_history = self.path_history[:self.current_path_index + 1]
        if self.path_history and self.path_history[-1] == path:
            return
        self.path_history.append(path)
        self.current_path_index = len(self.path_history) - 1
        if len(self.path_history) > self.max_history:
            self.path_history = self.path_history[-self.max_history:]
            self.current_path_index = len(self.path_history) - 1

    def populateFileTree(self, directory, parent_item):
        try:
            if self.isCacheValid(directory):
                cached_entries = self.file_cache[directory]
                for entry, metadata in cached_entries.items():
                    full_path = os.path.join(directory, entry)
                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, entry)
                    item.setData(0, Qt.UserRole, full_path)
                    self.tree_item_index[full_path] = item
                    if metadata is None or not metadata.get('is_file', False):
                        item.setIcon(0, QIcon.fromTheme("folder"))
                        placeholder = QTreeWidgetItem(item)
                        placeholder.setText(0, "Loading...")
                        item.setData(0, Qt.UserRole + 1, "directory")
                    else:
                        size = self.formatFileSize(metadata.get('size', 0))
                        item.setText(1, size)
                        item.setText(2, metadata.get('modified', ''))
                        item.setIcon(0, QIcon.fromTheme("text-x-generic"))
            else:
                entries = os.listdir(directory)
                entries.sort(key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower()))
                dir_cache = {}
                for entry in entries:
                    full_path = os.path.join(directory, entry)
                    file_info = QFileInfo(full_path)
                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, entry)
                    item.setData(0, Qt.UserRole, full_path)
                    self.tree_item_index[full_path] = item
                    if file_info.isFile():
                        size = self.formatFileSize(file_info.size())
                        modified = file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss")
                        item.setText(1, size)
                        item.setText(2, modified)
                        item.setIcon(0, QIcon.fromTheme("text-x-generic"))
                        dir_cache[entry] = {
                            'size': file_info.size(),
                            'modified': modified,
                            'is_file': True
                        }
                    else:
                        item.setIcon(0, QIcon.fromTheme("folder"))
                        placeholder = QTreeWidgetItem(item)
                        placeholder.setText(0, "Loading...")
                        item.setData(0, Qt.UserRole + 1, "directory")
                        dir_cache[entry] = None
                self.file_cache[directory] = dir_cache
                self.cache_timestamps[directory] = time.time()
                self.dir_mtimes[directory] = os.path.getmtime(directory)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def applyFilter(self):
        filter_text = self.ui.filter.text().lower()
        include_subdir = self.ui.subdir.isChecked()
        current_path = self.ui.path.text().strip() or os.getcwd()
        self.ui.filetree.clear()
        self.tree_item_index.clear()
        if not filter_text:
            self.loadFileTree()
            if self.lastFocusedFile and os.path.exists(self.lastFocusedFile):
                self.focusOnFileInTree(self.lastFocusedFile)
            return
        if include_subdir:
            self.performDeepSearch(current_path, filter_text)
        else:
            self.performShallowSearch(current_path, filter_text)

    def performShallowSearch(self, directory, filter_text):
        try:
            if self.isCacheValid(directory):
                cached_entries = self.file_cache[directory]
                dir_cache = {}
                for entry, metadata in cached_entries.items():
                    full_path = os.path.join(directory, entry)
                    if filter_text in entry.lower():
                        item = QTreeWidgetItem(self.ui.filetree)
                        item.setText(0, entry)
                        item.setData(0, Qt.UserRole, full_path)
                        self.tree_item_index[full_path] = item
                        if metadata is None or not metadata.get('is_file', False):
                            item.setIcon(0, QIcon.fromTheme("folder"))
                            placeholder = QTreeWidgetItem(item)
                            placeholder.setText(0, "Loading...")
                            item.setData(0, Qt.UserRole + 1, "directory")
                        else:
                            item.setText(1, self.formatFileSize(metadata.get('size', 0)))
                            item.setText(2, metadata.get('modified', ''))
                            item.setIcon(0, QIcon.fromTheme("text-x-generic"))
                    dir_cache[entry] = metadata
                self.file_cache[directory] = dir_cache
            else:
                entries = os.listdir(directory)
                entries.sort(key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower()))
                dir_cache = {}
                for entry in entries:
                    full_path = os.path.join(directory, entry)
                    if filter_text in entry.lower():
                        item = QTreeWidgetItem(self.ui.filetree)
                        item.setText(0, entry)
                        item.setData(0, Qt.UserRole, full_path)
                        self.tree_item_index[full_path] = item
                        if os.path.isdir(full_path):
                            item.setIcon(0, QIcon.fromTheme("folder"))
                            placeholder = QTreeWidgetItem(item)
                            placeholder.setText(0, "Loading...")
                            item.setData(0, Qt.UserRole + 1, "directory")
                            dir_cache[entry] = None
                        else:
                            file_info = QFileInfo(full_path)
                            size = self.formatFileSize(file_info.size())
                            modified = file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss")
                            item.setText(1, size)
                            item.setText(2, modified)
                            item.setIcon(0, QIcon.fromTheme("text-x-generic"))
                            dir_cache[entry] = {
                                'size': file_info.size(),
                                'modified': modified,
                                'is_file': True
                            }
                    elif os.path.exists(os.path.join(directory, entry)):
                        if os.path.isdir(os.path.join(directory, entry)):
                            dir_cache[entry] = None
                        else:
                            try:
                                file_info = QFileInfo(os.path.join(directory, entry))
                                dir_cache[entry] = {
                                    'size': file_info.size(),
                                    'modified': file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss"),
                                    'is_file': True
                                }
                            except:
                                dir_cache[entry] = {'is_file': True}
                self.file_cache[directory] = dir_cache
                self.cache_timestamps[directory] = time.time()
                self.dir_mtimes[directory] = os.path.getmtime(directory)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def performDeepSearch(self, root_dir, filter_text):
        matches = []
        dirs_to_search = [root_dir]
        searched_dirs = set()
        while dirs_to_search and len(matches) < 1000:
            current_dir = dirs_to_search.pop(0)
            if current_dir in searched_dirs:
                continue
            searched_dirs.add(current_dir)
            try:
                if self.isCacheValid(current_dir):
                    cached_entries = self.file_cache[current_dir]
                    dir_cache = {}
                    for entry, metadata in cached_entries.items():
                        full_path = os.path.join(current_dir, entry)
                        rel_path = os.path.relpath(full_path, root_dir)
                        if filter_text in entry.lower():
                            matches.append((full_path, rel_path))
                        if metadata is None or not metadata.get('is_file', False):
                            dirs_to_search.append(full_path)
                        dir_cache[entry] = metadata
                    self.file_cache[current_dir] = dir_cache
                else:
                    try:
                        entries = os.listdir(current_dir)
                        entries.sort(key=lambda x: (not os.path.isdir(os.path.join(current_dir, x)), x.lower()))
                        dir_cache = {}
                        for entry in entries:
                            full_path = os.path.join(current_dir, entry)
                            rel_path = os.path.relpath(full_path, root_dir)
                            if filter_text in entry.lower():
                                matches.append((full_path, rel_path))
                            if os.path.isdir(full_path):
                                dirs_to_search.append(full_path)
                                dir_cache[entry] = None
                            else:
                                try:
                                    file_info = QFileInfo(full_path)
                                    dir_cache[entry] = {
                                        'size': file_info.size(),
                                        'modified': file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss"),
                                        'is_file': True
                                    }
                                except:
                                    dir_cache[entry] = {'is_file': True}
                        self.file_cache[current_dir] = dir_cache
                        self.cache_timestamps[current_dir] = time.time()
                        self.dir_mtimes[current_dir] = os.path.getmtime(current_dir)
                    except:
                        pass
            except:
                pass
        for full_path, rel_path in matches:
            item = QTreeWidgetItem(self.ui.filetree)
            item.setText(0, f"{rel_path}")
            item.setData(0, Qt.UserRole, full_path)
            self.tree_item_index[full_path] = item
            if os.path.isdir(full_path):
                item.setIcon(0, QIcon.fromTheme("folder"))
            else:
                item.setIcon(0, QIcon.fromTheme("text-x-generic"))
                try:
                    file_info = QFileInfo(full_path)
                    size = self.formatFileSize(file_info.size())
                    modified = file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss")
                    item.setText(1, size)
                    item.setText(2, modified)
                except:
                    pass

    def onItemExpanded(self, item):
        if item.data(0, Qt.UserRole + 1) == "directory":
            for i in range(item.childCount()):
                if item.child(i).text(0) == "Loading...":
                    item.removeChild(item.child(i))
                    break
            directory = item.data(0, Qt.UserRole)
            self.populateFileTree(directory, item)
            self.addToCacheQueue(directory)
            if self.ui.filter.text():
                filter_text = self.ui.filter.text().lower()
                self.filterItems(item, filter_text)

    def filterItems(self, parent_item, filter_text):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            child.setHidden(filter_text not in child.text(0).lower())

    def formatFileSize(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def navigateUp(self):
        current_path = self.ui.path.text().strip()
        if not current_path:
            return
        parent_dir = os.path.dirname(current_path)
        if parent_dir and os.path.exists(parent_dir):
            self.ui.path.setText(parent_dir)
            self.loadFileTree()

    def createNewFile(self):
        directory = self.ui.path.text().strip() or os.getcwd()
        filename, ok = QInputDialog.getText(self, "Create New File", "Enter filename:", text="newfile.txt")
        if not ok or not filename:
            return
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            reply = QMessageBox.question(self, "File Exists",
                                         f"File {filename} already exists. Overwrite?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
        try:
            with open(file_path, 'w') as f:
                f.write("")
            self.addToRecent(file_path)
            if directory in self.cache_timestamps:
                del self.cache_timestamps[directory]
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
        selected = self.ui.filetree.currentItem()
        if selected:
            file_path = selected.data(0, Qt.UserRole)
            if file_path and os.path.exists(file_path) and file_path not in self.favorite_paths:
                self.favorite_paths.append(file_path)
                self.populateFavoritesList()
                self.saveConfig()

    def addToRecent(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
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
        file_path = item.data(Qt.UserRole)
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                self.ui.path.setText(file_path)
                self.loadFileTree()
            else:
                self.openFileWithDefaultApp(file_path)
        else:
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            self.recent_files.remove(file_path)
            self.populateRecentList()
            self.saveConfig()

    def openFavoriteItem(self, item):
        file_path = item.data(Qt.UserRole)
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                self.ui.path.setText(file_path)
                self.loadFileTree()
            else:
                self.openFileWithDefaultApp(file_path)
        else:
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            self.favorite_paths.remove(file_path)
            self.populateFavoritesList()
            self.saveConfig()

    def focusOnRecentItem(self, item):
        file_path = item.data(Qt.UserRole)
        self.focusOnFileInTree(file_path)

    def focusOnFavoriteItem(self, item):
        file_path = item.data(Qt.UserRole)
        self.focusOnFileInTree(file_path)

    def focusOnFileInTree(self, file_path):
        if not os.path.exists(file_path):
            return
        self.lastFocusedFile = file_path
        if file_path in self.tree_item_index:
            item = self.tree_item_index[file_path]
            self.ui.filetree.setCurrentItem(item)
            self.ui.filetree.scrollToItem(item)
            return
        if os.path.isdir(file_path):
            self.ui.path.setText(file_path)
            self.loadFileTree()
            return
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        current_dir = self.ui.path.text()
        if directory != current_dir:
            self.ui.path.setText(directory)
            self.loadFileTree()
        self.expandPartialPath(file_path, filename)

    def expandPartialPath(self, target_file, target_name):
        parts = os.path.normpath(target_file).split(os.sep)
        if len(parts) < 2:
            return
        root = self.ui.filetree.invisibleRootItem()
        self.expandNextLevel(root, parts, 0, target_name, target_file)

    def expandNextLevel(self, parent_item, path_parts, index, target_name, full_target):
        if index >= len(path_parts):
            return
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            item_path = item.data(0, Qt.UserRole)
            if item_path and os.path.basename(item_path) == path_parts[index]:
                if item.data(0, Qt.UserRole + 1) == "directory":
                    self.ui.filetree.expandItem(item)
                    self.onItemExpanded(item)
                if index == len(path_parts) - 1 and item_path == full_target:
                    self.ui.filetree.setCurrentItem(item)
                    self.ui.filetree.scrollToItem(item)
                    return
                self.expandNextLevel(item, path_parts, index + 1, target_name, full_target)
                return

    def findAndSelectItem(self, parent_item, filename, full_path):
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            item_path = item.data(0, Qt.UserRole)
            if item_path == full_path:
                self.ui.filetree.setCurrentItem(item)
                self.ui.filetree.scrollToItem(item)
                return True
            if item.text(0) == filename:
                self.ui.filetree.setCurrentItem(item)
                self.ui.filetree.scrollToItem(item)
                return True
            if os.path.isdir(item_path):
                self.ui.filetree.expandItem(item)
                self.onItemExpanded(item)
                if self.findAndSelectItem(item, filename, full_path):
                    return True
        return False

    def createContextMenuAction(self, menu, text, callback, icon_name=None):
        action = QAction(text, self)
        action.triggered.connect(callback)
        if icon_name:
            icon = QIcon.fromTheme(icon_name)
            if icon.isNull():
                icon_path = f":/valve_common/icons/tools/common/{icon_name}.png"
                icon = QIcon(icon_path)
            if not icon.isNull():
                action.setIcon(icon)
        menu.addAction(action)
        return action

    def showFileTreeContextMenu(self, position):
        item = self.ui.filetree.itemAt(position)
        if not item:
            return
        file_path = item.data(0, Qt.UserRole)
        if not file_path or not os.path.exists(file_path):
            return
        context_menu = QMenu(self)
        self.createContextMenuAction(context_menu, "Open",
                                     lambda: self.openFileWithDefaultApp(file_path), "open")
        self.createContextMenuAction(context_menu, "Add to Favorites",
                                     lambda: self.addToFavoritesFromPath(file_path), "bookmark")
        if os.path.isdir(file_path):
            self.createContextMenuAction(context_menu, "Set as Root",
                                         lambda: self.setPathAsRoot(file_path), "folder")
            self.createContextMenuAction(context_menu, "Open in Explorer",
                                         lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)),
                                         "folder-open")
        if os.path.isfile(file_path):
            self.createContextMenuAction(context_menu, "Open Containing Folder",
                                         lambda: self.openContainingFolder(file_path), "folder-open")
        context_menu.exec_(self.ui.filetree.mapToGlobal(position))

    def showRecentContextMenu(self, position):
        item = self.ui.recent_list.itemAt(position)
        if not item:
            return
        file_path = item.data(Qt.UserRole)
        context_menu = QMenu(self)
        self.createContextMenuAction(context_menu, "Open",
                                     lambda: self.openFileWithDefaultApp(file_path), "open")
        self.createContextMenuAction(context_menu, "Remove from Recent",
                                     lambda: self.removeFromRecent(file_path), "clear_list_sm")
        if os.path.exists(file_path):
            self.createContextMenuAction(context_menu, "Add to Favorites",
                                         lambda: self.addToFavoritesFromPath(file_path), "bookmark")
            if os.path.isfile(file_path):
                self.createContextMenuAction(context_menu, "Open Containing Folder",
                                             lambda: self.openContainingFolder(file_path), "folder-open")
        context_menu.exec_(self.ui.recent_list.mapToGlobal(position))

    def showFavoritesContextMenu(self, position):
        item = self.ui.favorites_list.itemAt(position)
        if not item:
            return
        file_path = item.data(Qt.UserRole)
        context_menu = QMenu(self)
        self.createContextMenuAction(context_menu, "Open",
                                     lambda: self.openFileWithDefaultApp(file_path), "open")
        self.createContextMenuAction(context_menu, "Remove from Favorites",
                                     lambda: self.removeFromFavorites(file_path), "clear_list_sm")
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.createContextMenuAction(context_menu, "Open Containing Folder",
                                         lambda: self.openContainingFolder(file_path), "folder-open")
        context_menu.exec_(self.ui.favorites_list.mapToGlobal(position))

    def setPathAsRoot(self, path):
        if os.path.isdir(path):
            self.ui.path.setText(path)
            self.loadFileTree()

    def openContainingFolder(self, file_path):
        if os.path.exists(file_path):
            parent_dir = os.path.dirname(file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(parent_dir))

    def removeFromRecent(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
            self.populateRecentList()
            self.saveConfig()

    def removeFromFavorites(self, file_path):
        if file_path in self.favorite_paths:
            self.favorite_paths.remove(file_path)
            self.populateFavoritesList()
            self.saveConfig()

    def addToFavoritesFromPath(self, file_path):
        if file_path and os.path.exists(file_path) and file_path not in self.favorite_paths:
            self.favorite_paths.append(file_path)
            self.populateFavoritesList()
            self.saveConfig()

    def closeEvent(self, event):
        self.saveConfig()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ExplorerMainWindow()
    window.show()
    sys.exit(app.exec())