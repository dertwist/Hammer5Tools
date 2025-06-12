from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QCheckBox, QLineEdit, \
    QDialog, QPushButton, QTableView, QComboBox, QMessageBox, QHeaderView, QMenu, QSizePolicy
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction
import os
from src.styles.common import qt_stylesheet_combobox, qt_stylesheet_checkbox, qt_stylesheet_button

from src.settings.main import get_addon_name, get_addon_dir
from src.widgets import qt_stylesheet_button, enable_dark_title_bar
from src.forms.cleanup.common import format_size
from src.forms.cleanup.parse import get_junk_files


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

        filters_frame = QFrame()
        filters_frame.setFrameShape(QFrame.StyledPanel)
        filters_frame.setContentsMargins(8, 4, 8, 4)

        filters_layout = QHBoxLayout(filters_frame)
        filters_layout.setSpacing(10)

        # Search Label + Input
        search_label = QLabel("Search:")
        filters_layout.addWidget(search_label)

        self.search_box = QLineEdit()
        self.search_box.setMinimumWidth(256)
        self.search_box.setPlaceholderText("Filter by name...")
        self.search_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filters_layout.addWidget(self.search_box)

        # File Type Label + ComboBox
        file_type_label = QLabel("File Type:")
        filters_layout.addSpacing(20)
        filters_layout.addWidget(file_type_label)

        self.filter_combo = QComboBox()
        self.filter_combo.setStyleSheet(qt_stylesheet_combobox)
        self.filter_combo.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        filters_layout.addWidget(self.filter_combo)

        # Spacer to push everything to the left
        filters_layout.addStretch()

        # Add to main layout
        main_layout.addWidget(filters_frame)

        # Table view
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.ExtendedSelection)  # Multi-selection enabled
        self.table_view.horizontalHeader().setMinimumSectionSize(50)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table_view)

        # Context menu for checkbox toggling
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)

        # Stats
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel()
        stats_layout.addWidget(self.stats_label)
        main_layout.addLayout(stats_layout)

        footer_layout = QHBoxLayout()

        # Stats label on the left
        self.stats_label = QLabel()
        footer_layout.addWidget(self.stats_label, 1, Qt.AlignLeft)

        # Wrap buttons in their own layout for better alignment control
        button_layout = QHBoxLayout()
        self.recalculate_button = QPushButton("Recalculate")
        self.recalculate_button.setStyleSheet(qt_stylesheet_button)
        button_layout.addWidget(self.recalculate_button)

        self.cleanup_button = QPushButton("Delete Selected Files")
        self.cleanup_button.setStyleSheet(qt_stylesheet_button)
        self.cleanup_button.setDefault(True)
        button_layout.addWidget(self.cleanup_button)

        footer_layout.addLayout(button_layout)
        main_layout.addLayout(footer_layout)


        # Data & model setup
        vmap_path = os.path.join(get_addon_dir(), "maps", f"{get_addon_name()}.vmap")
        self.junk_files = get_junk_files(addon_dir=get_addon_dir(), vmap=vmap_path)
        extensions = set(os.path.splitext(file)[1].lower() for file, _ in self.junk_files)
        self.filter_combo.addItem("All")
        for ext in sorted(extensions):
            self.filter_combo.addItem(ext)

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

        self.proxy_model = FileFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortRole(Qt.UserRole)
        self.table_view.setModel(self.proxy_model)

        # Signals
        self.search_box.textChanged.connect(self.proxy_model.setSearchText)
        self.filter_combo.currentTextChanged.connect(self.proxy_model.setFileType)
        self.model.itemChanged.connect(self.update_statistics)
        self.proxy_model.layoutChanged.connect(self.update_statistics)

        self.update_statistics()

    def update_statistics(self):
        total_junk = self.model.rowCount()
        visible_junk = self.proxy_model.rowCount()
        selected_files = sum(
            1 for row in range(total_junk)
            if self.model.item(row, 0).checkState() == Qt.Checked
        )
        selected_size = sum(
            self.model.item(row, 1).data(Qt.UserRole)
            for row in range(total_junk)
            if self.model.item(row, 0).checkState() == Qt.Checked
        )
        self.stats_label.setText(
            f"Selected: {selected_files} | Visible: {visible_junk}/{total_junk} | Size: {format_size(selected_size)}"
        )

    def recalculate(self):
        self.junk_files = get_junk_files()

        self.model.clear()
        self.model.setHorizontalHeaderLabels(["File Path", "Size"])
        for file, size in self.junk_files:
            item_path = QStandardItem(file)
            item_path.setCheckable(True)
            item_path.setCheckState(Qt.Checked)
            item_path.setData(file, Qt.UserRole)
            item_size = QStandardItem(format_size(size))
            item_size.setData(size, Qt.UserRole)
            self.model.appendRow([item_path, item_size])

        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        extensions = set(os.path.splitext(file)[1].lower() for file, _ in self.junk_files)
        self.filter_combo.addItem("All")
        for ext in sorted(extensions):
            self.filter_combo.addItem(ext)
        self.filter_combo.blockSignals(False)

        self.proxy_model.invalidateFilter()
        self.update_statistics()

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

    def show_context_menu(self, position):
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        menu = QMenu()
        select_action = QAction("Check Selected", self)
        deselect_action = QAction("Uncheck Selected", self)

        select_action.triggered.connect(lambda: self.set_selected_rows_checked(indexes, Qt.Checked))
        deselect_action.triggered.connect(lambda: self.set_selected_rows_checked(indexes, Qt.Unchecked))

        menu.addAction(select_action)
        menu.addAction(deselect_action)
        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def set_selected_rows_checked(self, indexes, state):
        for proxy_index in indexes:
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.model.item(source_index.row(), 0)
            if item is not None:
                item.setCheckState(state)
