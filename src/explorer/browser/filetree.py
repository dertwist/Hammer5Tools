import os
import time
import re
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtWidgets import QTreeWidgetItem, QMessageBox
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QFileInfo

# A helper function to choose an appropriate icon based on file type.
def get_file_icon(path=None, is_folder=False):
    from PySide6.QtGui import QIcon
    # if folder, use folder icon
    if is_folder:
        return QIcon.fromTheme("folder") or QIcon(":/icons/folder.png")
    if not path:
        return QIcon.fromTheme("text-x-generic") or QIcon(":/icons/file.png")
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext in [".png", ".jpg", ".jpeg", ".gif"]:
        return QIcon.fromTheme("image-x-generic") or QIcon(":/icons/image.png")
    elif ext in [".txt", ".log"]:
        return QIcon.fromTheme("text-x-generic") or QIcon(":/icons/text.png")
    elif ext in [".py"]:
        return QIcon.fromTheme("text-x-python") or QIcon(":/icons/python.png")
    else:
        return QIcon.fromTheme("text-x-generic") or QIcon(":/icons/file.png")

class FileTreeManager:
    def __init__(self, tree_widget, path_line_edit, root=None):
        """
        Manages file tree operations: loading the directory structure,
        caching file metadata, filtering, and handling expansion.
        """
        self.tree_widget = tree_widget
        self.path_line_edit = path_line_edit
        self.root = root
        self.file_cache = {}        # { directory: dict(entry: metadata) }
        self.cache_timestamps = {}  # { directory: timestamp }
        self.cache_expiry = 30      # seconds
        self.pending_cache_updates = set()
        self.tree_item_index = {}   # Map file path -> QTreeWidgetItem
        self.dir_mtimes = {}        # Cache of directory modification times

        self.timer = QTimer()
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.update_pending_caches)
        self.timer.start()

    def setup(self):
        """Set header and basic configuration for the tree widget."""
        self.tree_widget.setHeaderLabels(["Name", "Size", "Modified"])
        self.tree_widget.setColumnWidth(0, 300)
        self.tree_widget.setSortingEnabled(True)

    def clear(self):
        """Clear the tree widget and internal index."""
        self.tree_widget.clear()
        self.tree_item_index.clear()

    def load(self, directory):
        """Loads the directory into the tree widget."""
        self.path_line_edit.setText(directory)
        self.clear()
        if not os.path.exists(directory):
            QMessageBox.warning(self.tree_widget, "Error", f"Directory not found: {directory}")
            return
        self.populate_file_tree(directory, self.tree_widget)
        self.add_to_cache_queue(directory)

    def populate_file_tree(self, directory, parent_item):
        """
        Populate a QTreeWidget (or child item) with file and folder entries.
        Uses cached entries if available.
        """
        try:
            if self.is_cache_valid(directory):
                cached_entries = self.file_cache[directory]
                for entry, metadata in cached_entries.items():
                    full_path = os.path.join(directory, entry)
                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, entry)
                    item.setData(0, Qt.UserRole, full_path)
                    item.setToolTip(0, full_path)
                    self.tree_item_index[full_path] = item
                    if metadata is None or not metadata.get("is_file", False):
                        item.setIcon(0, get_file_icon(None, is_folder=True))
                        placeholder = QTreeWidgetItem(item)
                        placeholder.setText(0, "Loading...")
                        item.setData(0, Qt.UserRole + 1, "directory")
                    else:
                        size = self.format_file_size(metadata.get("size", 0))
                        item.setText(1, size)
                        item.setText(2, metadata.get("modified", ""))
                        item.setIcon(0, get_file_icon(full_path, is_folder=False))
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
                    item.setToolTip(0, full_path)
                    self.tree_item_index[full_path] = item
                    if file_info.isFile():
                        size = self.format_file_size(file_info.size())
                        modified = file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss")
                        item.setText(1, size)
                        item.setText(2, modified)
                        item.setIcon(0, get_file_icon(full_path, is_folder=False))
                        dir_cache[entry] = {"size": file_info.size(), "modified": modified, "is_file": True}
                    else:
                        item.setIcon(0, get_file_icon(None, is_folder=True))
                        placeholder = QTreeWidgetItem(item)
                        placeholder.setText(0, "Loading...")
                        item.setData(0, Qt.UserRole + 1, "directory")
                        dir_cache[entry] = None
                self.file_cache[directory] = dir_cache
                self.cache_timestamps[directory] = time.time()
                self.dir_mtimes[directory] = os.path.getmtime(directory)
        except Exception as e:
            QMessageBox.warning(self.tree_widget, "Error", str(e))

    def is_cache_valid(self, directory):
        """Returns True if cache for a directory is still valid."""
        if directory not in self.cache_timestamps:
            return False
        if time.time() - self.cache_timestamps[directory] > self.cache_expiry:
            return False
        try:
            current_mtime = os.path.getmtime(directory)
            if directory in self.dir_mtimes and self.dir_mtimes[directory] != current_mtime:
                return False
        except Exception:
            return False
        return True

    def add_to_cache_queue(self, directory):
        if os.path.isdir(directory):
            self.pending_cache_updates.add(directory)

    def update_pending_caches(self):
        if not self.pending_cache_updates:
            return
        dirs_to_process = list(self.pending_cache_updates)[:5]
        for directory in dirs_to_process:
            self.pending_cache_updates.remove(directory)
            self.update_directory_cache(directory)

    def update_directory_cache(self, directory):
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
                            "size": file_info.size(),
                            "modified": file_info.lastModified().toString("yyyy-MM-dd hh:mm:ss"),
                            "is_file": True,
                        }
                    except Exception:
                        dir_cache[entry] = {"is_file": True}
            self.file_cache[directory] = dir_cache
            self.cache_timestamps[directory] = time.time()
        except Exception:
            pass

    def format_file_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def perform_shallow_search(self, directory, filter_text):
        """
        Perform a shallow search in the given directory using cache if available.
        Returns a list of (full_path, display_relative_path) tuples.
        """
        results = []
        try:
            if self.is_cache_valid(directory):
                cached_entries = self.file_cache[directory]
                for entry, metadata in cached_entries.items():
                    full_path = os.path.join(directory, entry)
                    if filter_text in entry.lower():
                        results.append((full_path, entry))
            else:
                entries = os.listdir(directory)
                entries.sort(key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower()))
                for entry in entries:
                    full_path = os.path.join(directory, entry)
                    if filter_text in entry.lower():
                        results.append((full_path, entry))
        except Exception as e:
            QMessageBox.warning(self.tree_widget, "Error", str(e))
        return results

    def perform_deep_search(self, root_dir, filter_text):
        """
        Perform a deep search (recursively) starting from root_dir.
        Returns a list of tuples: (full_path, relative_path).
        """
        matches = []
        dirs_to_search = [root_dir]
        searched_dirs = set()
        while dirs_to_search and len(matches) < 1000:
            current_dir = dirs_to_search.pop(0)
            if current_dir in searched_dirs:
                continue
            searched_dirs.add(current_dir)
            try:
                if self.is_cache_valid(current_dir):
                    cached_entries = self.file_cache[current_dir]
                    for entry, metadata in cached_entries.items():
                        full_path = os.path.join(current_dir, entry)
                        rel_path = os.path.relpath(full_path, root_dir)
                        if filter_text in entry.lower():
                            matches.append((full_path, rel_path))
                        if metadata is None or not metadata.get("is_file", False):
                            dirs_to_search.append(full_path)
                else:
                    entries = os.listdir(current_dir)
                    entries.sort(key=lambda x: (not os.path.isdir(os.path.join(current_dir, x)), x.lower()))
                    for entry in entries:
                        full_path = os.path.join(current_dir, entry)
                        rel_path = os.path.relpath(full_path, root_dir)
                        if filter_text in entry.lower():
                            matches.append((full_path, rel_path))
                        if os.path.isdir(full_path):
                            dirs_to_search.append(full_path)
                    # Update cache for this directory
                    self.populate_file_tree(current_dir, self.tree_widget.invisibleRootItem())
            except Exception:
                pass
        return matches

    def expand_partial_path(self, target_file):
        """
        Expand the tree so that the item matching target_file is visible.
        """
        if not os.path.exists(target_file):
            return
        parts = os.path.normpath(target_file).split(os.sep)
        if len(parts) < 2:
            return
        root = self.tree_widget.invisibleRootItem()
        self.expand_next_level(root, parts, 0, target_file)

    def expand_next_level(self, parent_item, path_parts, index, full_target):
        if index >= len(path_parts):
            return
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            item_path = item.data(0, Qt.UserRole)
            if item_path and os.path.basename(item_path) == path_parts[index]:
                # If folder, expand it and load its children
                if item.data(0, Qt.UserRole + 1) == "directory":
                    self.tree_widget.expandItem(item)
                if index == len(path_parts) - 1 and item_path == full_target:
                    self.tree_widget.setCurrentItem(item)
                    self.tree_widget.scrollToItem(item)
                    return
                self.expand_next_level(item, path_parts, index + 1, full_target)
                return

# End of browser_filetree.py