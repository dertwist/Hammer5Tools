from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QHBoxLayout, \
    QCheckBox, QLineEdit, QDialog, QPushButton, QTableView, QComboBox, QMessageBox, QHeaderView
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from src.settings.main import get_addon_name, get_addon_dir
from src.widgets import qt_stylesheet_button, enable_dark_title_bar
from src.dotnet import extract_vmap_references
import unittest
import os
from src.common import Kv3ToJson
import vdf
from PySide6.QtCore import QSortFilterProxyModel
from collections import deque

def format_size(size):
    """Convert bytes to a human-readable format."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"

class FileFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_text = ""
        self.file_type = "All"

    def setSearchText(self, text):
        self.search_text = text.lower()
        self.invalidateFilter()

    def setFileType(self, file_type):
        self.file_type = file_type
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        file_path = model.data(index, Qt.DisplayRole)
        if self.search_text and self.search_text not in file_path.lower():
            return False
        if self.file_type != "All":
            ext = os.path.splitext(file_path)[1].lower()
            if ext != self.file_type.lower():
                return False
        return True

def get_material_references(vmat_path):
    """Extract texture and material references from a .vmat file."""
    try:
        file = vdf.load(open(vmat_path, 'r'))
    except FileNotFoundError:
        print(f"Error: File '{vmat_path}' not found")
        return [], []
    except Exception as e:
        print(f"Error parsing '{vmat_path}': {e}")
        return [], []

    texture_references = []
    material_references = []

    def extract_references(d):
        if isinstance(d, dict):
            for key, value in d.items():
                if key.startswith('Texture') and value and value != '':
                    texture_references.append(value)
                elif key.startswith('MaterialLayerReference') and value:
                    material_references.append(value)
                elif isinstance(value, dict):
                    extract_references(value)

    extract_references(file)
    return texture_references, material_references

def get_model_references(vmdl_path):
    """Extract references from a .vmdl or .vmdl_prefab file."""
    try:
        with open(vmdl_path, 'r') as f:
            kv3_data = f.read()
        file = Kv3ToJson(kv3_data)
    except FileNotFoundError:
        print(f"Error: File '{vmdl_path}' not found")
        return []
    except Exception as e:
        print(f"Error parsing '{vmdl_path}': {e}")
        return []

    references = []

    def extract_references(d):
        if isinstance(d, dict):
            for key, value in d.items():
                if key in ('filename', 'target_file', 'from', 'to') and isinstance(value, str) and value:
                    references.append(value)
                elif isinstance(value, (dict, list)):
                    if isinstance(value, dict):
                        extract_references(value)
                    else:
                        for item in value:
                            extract_references(item)

    extract_references(file)
    return references

def get_references(file_path, addon_dir):
    """Extract references from a file based on its type."""
    ext = os.path.splitext(file_path)[1].lower()
    full_path = os.path.join(addon_dir, file_path)
    if ext in ['.vmdl', '.vmdl_prefab']:
        return get_model_references(full_path)
    elif ext == '.vmat':
        texture_refs, mat_refs = get_material_references(full_path)
        return texture_refs + mat_refs
    return []

def get_junk_files(addon_name=None, addon_dir=None):
    """
    Identify unused (junk) files in the addon, including textures and meshes.
    Returns a list of tuples (file_path, size).
    """
    if addon_name is None:
        addon_name = get_addon_name()
    if addon_dir is None:
        addon_dir = get_addon_dir()

    # Define file extensions
    asset_extensions = ['.vmat', '.vmdl', '.vmdl_prefab', '.vsndevts', '.vsmart', '.vmap',
                        '.png', '.tga', '.fbx', '.obj']
    directories_to_search = ['maps', 'models', 'materials', 'sounds']
    directories_to_ignore = ['materials\\default']

    # Get the main .vmap file path
    vmap_path = os.path.join(addon_dir, 'maps', f"{addon_name}.vmap")
    vmap_relative_path = os.path.relpath(vmap_path, addon_dir).replace('\\', '/')
    vmap_assets_references = extract_vmap_references(vmap_path)
    print(f"Found {len(vmap_assets_references)} direct references in the addon '{addon_name}'.")

    # Collect all asset files in the addon
    assets_collection = []
    for directory in directories_to_search:
        for root, dirs, files in os.walk(os.path.join(addon_dir, directory)):
            if any(ignored in root for ignored in directories_to_ignore):
                continue
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file_path)[1].lower()
                if ext in asset_extensions:
                    relative_path = os.path.relpath(file_path, addon_dir).replace('\\', '/')
                    assets_collection.append(relative_path)

    print(f"Found {len(assets_collection)} assets in the addon '{addon_name}'.")

    # Filter out default CS:GO library assets
    addon_assets = [file for file in assets_collection if
                    not (file.startswith('csgo/') or file.startswith('csgo_addons/'))]

    # Recursively collect all referenced files
    referenced_files = set([vmap_relative_path])
    queue = deque(vmap_assets_references)
    while queue:
        current_file = queue.popleft()
        if current_file not in referenced_files:
            referenced_files.add(current_file)
            refs = get_references(current_file, addon_dir)
            for ref in refs:
                if ref not in referenced_files:
                    queue.append(ref)

    # Identify junk files
    junk_collection = []
    for file in addon_assets:
        if file not in referenced_files:
            full_path = os.path.join(addon_dir, file)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            junk_collection.append((file, size))

    print(f"Identified {len(junk_collection)} junk files in the addon '{addon_name}'.")
    return junk_collection

class TestJunkCollect(unittest.TestCase):
    def test_junkcollect(self):
        addon_name = "kk"
        addon_dir = os.path.normpath(
            r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\kk")
        junk_files = get_junk_files(addon_name, addon_dir)
        print(f'Junk collect for addon: {addon_name}: {len(junk_files)}')

class CleanupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cleanup Addon")
        enable_dark_title_bar(self)
        self.setMinimumSize(600, 400)
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        main_layout = QVBoxLayout(self)

        # Title and instructions
        title_label = QLabel("Cleanup Addon")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title_label)

        instructions_label = QLabel(
            "This tool will remove all unused files from your addon (content).\n"
            f"It will keep only the files referenced in the {get_addon_name()}.vmap file."
            "\n\n To complete the cleanup, you need to cleanup in Asset Browser in the editor.\n"
        )
        instructions_label.setWordWrap(True)
        main_layout.addWidget(instructions_label)

        # Search and filter
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        main_layout.addLayout(search_layout)

        filter_layout = QHBoxLayout()
        filter_label = QLabel("File Type:")
        self.filter_combo = QComboBox()
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_combo)
        main_layout.addLayout(filter_layout)

        # Table view
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.horizontalHeader().setMinimumSectionSize(50)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)  # Resize all columns to content
        main_layout.addWidget(self.table_view)

        # Compact statistics
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel()
        stats_layout.addWidget(self.stats_label)
        main_layout.addLayout(stats_layout)

        # Cleanup button
        cleanup_button = QPushButton("Cleanup Addon")
        cleanup_button.clicked.connect(self.cleanup_addon)
        main_layout.addWidget(cleanup_button)

        # Populate data
        self.junk_files = get_junk_files()
        extensions = set(os.path.splitext(file)[1].lower() for file, _ in self.junk_files)
        self.filter_combo.addItem("All")
        for ext in sorted(extensions):
            self.filter_combo.addItem(ext)

        # Set up model
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["File Path", "Size"])
        for file, size in self.junk_files:
            item_path = QStandardItem(file)
            item_path.setCheckable(True)
            item_path.setCheckState(Qt.Checked)
            item_path.setData(file, Qt.UserRole)
            item_size = QStandardItem(format_size(size))
            item_size.setData(size, Qt.UserRole)
            self.model.appendRow([item_path, item_size])

        # Set up proxy model
        self.proxy_model = FileFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortRole(Qt.UserRole)
        self.table_view.setModel(self.proxy_model)

        # Connect signals
        self.search_box.textChanged.connect(self.proxy_model.setSearchText)
        self.filter_combo.currentTextChanged.connect(self.proxy_model.setFileType)
        self.model.itemChanged.connect(self.update_statistics)
        self.proxy_model.layoutChanged.connect(self.update_statistics)

        # Initial update
        self.update_statistics()

    def update_statistics(self):
        total_junk = self.model.rowCount()
        visible_junk = self.proxy_model.rowCount()
        selected_files = sum(1 for row in range(total_junk) if self.model.item(row, 0).checkState() == Qt.Checked)
        selected_size = sum(self.model.item(row, 1).data(Qt.UserRole) for row in range(total_junk) if self.model.item(row, 0).checkState() == Qt.Checked)
        visible_size = sum(self.proxy_model.data(self.proxy_model.index(row, 1), Qt.UserRole) for row in range(visible_junk))
        self.stats_label.setText(f"Selected: {selected_files} | Visible: {visible_junk}/{total_junk} | Size: {format_size(selected_size)}")

    def cleanup_addon(self):
        files_to_delete = []
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 0)
            if item.checkState() == Qt.Checked:
                file_path = item.data(Qt.UserRole)
                files_to_delete.append(file_path)

        if not files_to_delete:
            QMessageBox.information(self, "No Selection", "No files selected for cleanup.")
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {len(files_to_delete)} files?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        addon_dir = os.path.join(get_addon_dir())
        deleted_files = []
        for file in files_to_delete:
            file_path = os.path.join(addon_dir, file)
            try:
                os.remove(file_path)
                deleted_files.append(file_path)
            except Exception as e:
                print(f"Error deleting '{file_path}': {e}")

        QMessageBox.information(self, "Cleanup Completed", f"Deleted {len(deleted_files)} files")
        self.accept()

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = CleanupDialog()
    dialog.exec()
