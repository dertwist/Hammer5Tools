import os
import shutil
import sys
import zipfile
import math
from typing import List, Dict, Optional, Set

# Local imports
from src.forms.cleanup.parse import get_vmap_references
from src.styles.common import qt_stylesheet_combobox, qt_stylesheet_checkbox, qt_stylesheet_button
from src.settings.main import get_cs2_path, get_addon_name, get_settings_value, get_addon_dir
from src.common import enable_dark_title_bar

# PySide6 imports
from PySide6.QtCore import Qt, QModelIndex, QUrl, QSize
from PySide6.QtGui import QIcon, QStandardItemModel, QStandardItem, QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QMessageBox, QFileDialog, QProgressDialog, QStyle, QTableView, QHeaderView,
    QTabWidget, QWidget, QLineEdit, QComboBox, QSizePolicy, QMenu
)

cs2_path = get_cs2_path()


class ExportAndImportAddonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        enable_dark_title_bar(self)
        self.setWindowTitle("Export and Import Addon")
        self.setMinimumSize(750, 650)
        try:
            self.setWindowIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        except AttributeError:
            pass

        self.vmap_files: List[str] = []
        self.vmap_ref_counts: Dict[str, int] = {}
        self.dependent_files_cache: Set[str] = set()

        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        self._create_simple_tab()
        self._create_advanced_tab()

        self.size_label = QLabel("Select export options to see the file list and size.")
        self.layout.addWidget(self.size_label)

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.ExtendedSelection)
        self.table_view.horizontalHeader().setMinimumSectionSize(50)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.file_model = QStandardItemModel(self)
        self.table_view.setModel(self.file_model)
        self.layout.addWidget(self.table_view)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.import_button = QPushButton("Import Addon")
        self.import_button.setStyleSheet(qt_stylesheet_button)
        self.import_button.setIcon(QIcon(":/icons/download_2_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        self.export_button = QPushButton("Export Addon")
        self.export_button.setStyleSheet(qt_stylesheet_button)
        self.export_button.setIcon(QIcon(":/icons/upload_2_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        btn_layout.addWidget(self.import_button)
        btn_layout.addWidget(self.export_button)
        self.layout.addLayout(btn_layout)

        self._connect_signals()
        self.update_export_preview()

    def _create_simple_tab(self):
        self.simple_tab = QWidget()
        simple_layout = QVBoxLayout(self.simple_tab)
        simple_layout.setAlignment(Qt.AlignTop)
        self.skip_non_default_checkbox = QCheckBox("Skip non-default folders in content/ folder")
        self.compiled_maps_checkbox = QCheckBox("Include compiled maps (.vpk)")
        self.compiled_materials_checkbox = QCheckBox("Include compiled materials (.vtex_c, .vmat_c)")
        self.compiled_models_checkbox = QCheckBox("Include compiled models (.vmdl_c)")
        self.ignore_vcs_checkbox = QCheckBox("Ignore VCS files (.git, .gitignore, .diversion)")
        checkboxes = [self.skip_non_default_checkbox, self.compiled_maps_checkbox, self.compiled_materials_checkbox,
                      self.compiled_models_checkbox, self.ignore_vcs_checkbox]
        for checkbox in checkboxes:
            checkbox.setStyleSheet(qt_stylesheet_checkbox)
            simple_layout.addWidget(checkbox)
        self.compiled_maps_checkbox.setChecked(True)
        self.compiled_materials_checkbox.setChecked(True)
        self.compiled_models_checkbox.setChecked(True)
        self.ignore_vcs_checkbox.setChecked(True)
        self.tabs.addTab(self.simple_tab, "Simple")

    def _create_advanced_tab(self):
        self.advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_tab)
        advanced_layout.setAlignment(Qt.AlignTop)
        self.only_deps_checkbox = QCheckBox("Only include dependencies from VMap files (Content)")
        self.only_deps_checkbox.setStyleSheet(qt_stylesheet_checkbox)
        advanced_layout.addWidget(self.only_deps_checkbox)
        self.vmap_widget_container = QWidget()
        vmap_layout = QVBoxLayout(self.vmap_widget_container)
        vmap_layout.setContentsMargins(20, 5, 0, 0)

        self.vmap_table_view = QTableView()
        self.vmap_model = QStandardItemModel(self)
        self.vmap_model.setHorizontalHeaderLabels(['', 'VMap File', 'References'])
        self.vmap_table_view.setModel(self.vmap_model)
        # FIXED: Set persistent resize modes for columns to stretch and fit content
        self.vmap_table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.vmap_table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.vmap_table_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)


        self.vmap_table_view.setAlternatingRowColors(True)
        self.vmap_table_view.setSortingEnabled(True)
        self.vmap_table_view.setSelectionBehavior(QTableView.SelectRows)
        self.vmap_table_view.setSelectionMode(QTableView.ExtendedSelection)  # Multi-selection enabled
        self.vmap_table_view.horizontalHeader().setMinimumSectionSize(50)
        self.vmap_table_view.horizontalHeader().setStretchLastSection(True)
        self.vmap_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.vmap_table_view.setMaximumHeight(120)

        self.add_vmap_button = QPushButton("Add VMap File...")
        self.add_vmap_button.setStyleSheet(qt_stylesheet_button)
        vmap_layout.addWidget(QLabel("Source VMap Files (defaults to main addon vmap):"))
        vmap_layout.addWidget(self.vmap_table_view)
        vmap_layout.addWidget(self.add_vmap_button)
        self.vmap_widget_container.setVisible(False)
        advanced_layout.addWidget(self.vmap_widget_container)
        advanced_layout.addWidget(QLabel("Ignore file extensions (comma separated):"))
        self.ignore_edit = QLineEdit(".bak, .bin")
        advanced_layout.addWidget(self.ignore_edit)
        advanced_layout.addWidget(QLabel("Archive Compression Level:"))
        self.compression_combo = QComboBox()
        self.compression_combo.setStyleSheet(qt_stylesheet_combobox)
        self.compression_combo.addItems(["Fastest", "Normal", "Ultra (Slow)"])
        self.compression_combo.setCurrentText("Normal")
        advanced_layout.addWidget(self.compression_combo, 0, Qt.AlignTop)
        self.tabs.addTab(self.advanced_tab, "Advanced")

    def _connect_signals(self):
        self.export_button.clicked.connect(self.do_export_addon)
        self.import_button.clicked.connect(self.do_import_addon)
        self.table_view.doubleClicked.connect(self.open_file_location)
        self.file_model.itemChanged.connect(self.recalculate_size)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_file_table_context_menu)
        for checkbox in [self.skip_non_default_checkbox, self.compiled_maps_checkbox, self.compiled_materials_checkbox,
                         self.compiled_models_checkbox, self.ignore_vcs_checkbox]:
            checkbox.stateChanged.connect(self.update_export_preview)
        self.only_deps_checkbox.stateChanged.connect(self.on_deps_mode_changed)
        self.add_vmap_button.clicked.connect(self.add_vmap_file)
        self.ignore_edit.textChanged.connect(self.update_export_preview)
        self.vmap_table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.vmap_table_view.customContextMenuRequested.connect(self.show_vmap_table_context_menu)
        self.vmap_model.itemChanged.connect(self.on_vmap_item_changed)

    def on_vmap_item_changed(self, item: Optional[QStandardItem] = None):
        # FIXED: Centralized handler for VMap changes. Triggers if called manually (item is None) or from a checkbox click.
        if item is None or item.column() == 0:
            self.dependent_files_cache.clear()
            self.update_export_preview()

    def on_deps_mode_changed(self):
        self.vmap_widget_container.setVisible(self.only_deps_checkbox.isChecked())
        self.dependent_files_cache.clear()
        self.update_export_preview()

    def add_vmap_file(self):
        addon_dir = get_addon_dir()
        if not addon_dir: return QMessageBox.warning(self, "Error", "Addon directory not found.")
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select VMap Files", addon_dir, "VMap Files (*.vmap)")
        added = False
        for file_path in file_paths:
            if file_path and file_path not in self.vmap_files:
                self.vmap_files.append(file_path)
                added = True
        if added:
            self._populate_vmap_table()
            self.on_vmap_item_changed()

    def _populate_vmap_table(self):
        try:
            self.vmap_model.itemChanged.disconnect(self.on_vmap_item_changed)
        except (RuntimeError, TypeError):
            pass

        self.vmap_model.clear()
        self.vmap_model.setHorizontalHeaderLabels(['', 'VMap File', 'References'])
        for vmap_path in self.vmap_files:
            item_check = QStandardItem()
            item_check.setCheckable(True)
            item_check.setCheckState(Qt.Checked)
            item_check.setEditable(False)
            item_name = QStandardItem(os.path.basename(vmap_path))
            item_name.setData(vmap_path, Qt.UserRole)
            item_name.setToolTip(vmap_path)
            item_name.setEditable(False)
            ref_count = self.vmap_ref_counts.get(vmap_path)
            item_refs = QStandardItem(str(ref_count) if ref_count is not None else "N/A")
            item_refs.setEditable(False)
            self.vmap_model.appendRow([item_check, item_name, item_refs])

        self.vmap_model.itemChanged.connect(self.on_vmap_item_changed)
        # FIXED: Removed redundant resize call. setSectionResizeMode handles this.

    def update_export_preview(self):
        if not get_addon_name():
            self.size_label.setText("Output size before archiving: Addon not selected.")
            self.file_model.clear()
            return
        if self.only_deps_checkbox.isChecked() and not self.dependent_files_cache:
            self.calculate_dependencies()
        else:
            self._populate_table()

    def calculate_dependencies(self):
        addon_dir = get_addon_dir()
        if not addon_dir: return QMessageBox.warning(self, "Error", "Addon directory not found.")
        self.table_view.setEnabled(False)
        self.export_button.setEnabled(False)
        self.size_label.setText("Calculating dependencies...")
        self.dependent_files_cache.clear()
        self.vmap_ref_counts.clear()
        vmaps_to_scan = []
        if self.vmap_model.rowCount() > 0:
            for row in range(self.vmap_model.rowCount()):
                if self.vmap_model.item(row, 0).checkState() == Qt.Checked:
                    vmaps_to_scan.append(self.vmap_model.item(row, 1).data(Qt.UserRole))
        if not vmaps_to_scan and not self.vmap_files:
            main_vmap_path = os.path.join(addon_dir, 'maps', f'{get_addon_name()}.vmap')
            if os.path.exists(main_vmap_path):
                vmaps_to_scan.append(main_vmap_path)
            else:
                QMessageBox.warning(self, "VMap Not Found", f"Default VMap not found. Add a VMap file manually.")
        for vmap_file in vmaps_to_scan:
            try:
                _, referenced_files_relative = get_vmap_references(addon_dir, vmap_file)
                self.vmap_ref_counts[vmap_file] = len(referenced_files_relative)
                absolute_paths = {os.path.normpath(os.path.join(addon_dir, p)) for p in referenced_files_relative}
                self.dependent_files_cache.update(absolute_paths)
            except Exception as e:
                QMessageBox.critical(self, "Dependency Error",
                                     f"Failed to parse {os.path.basename(vmap_file)}.\nError: {e}")
        self._populate_vmap_table()
        self._populate_table()
        self.table_view.setEnabled(True)
        self.export_button.setEnabled(True)

    def _populate_table(self):
        try:
            self.file_model.itemChanged.disconnect(self.recalculate_size)
        except (RuntimeError, TypeError):
            pass
        all_files = self.get_all_addon_files()
        if self.only_deps_checkbox.isChecked():
            all_files = {path: size for path, size in all_files.items() if
                         os.path.normpath(path) in self.dependent_files_cache}
        self.file_model.clear()
        self.file_model.setHorizontalHeaderLabels(['', 'File', 'Size', 'Path'])
        for path, size in sorted(all_files.items()):
            is_checked = True
            if not self.only_deps_checkbox.isChecked() and self.dependent_files_cache:
                is_checked = os.path.normpath(path) in self.dependent_files_cache
            item_include = QStandardItem()
            item_include.setCheckable(True)
            item_include.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
            item_filename = QStandardItem(os.path.basename(path))
            item_filename.setData(path, Qt.UserRole)
            item_path = QStandardItem(os.path.relpath(os.path.dirname(path), cs2_path))
            item_size = QStandardItem(self.convert_size(size))
            item_size.setData(size, Qt.UserRole)
            for item in [item_filename, item_path, item_size, item_include]:
                item.setEditable(False)
            self.file_model.appendRow([item_include, item_filename, item_size, item_path])
        self.table_view.resizeColumnsToContents()
        self.recalculate_size()
        self.file_model.itemChanged.connect(self.recalculate_size)

    def show_vmap_table_context_menu(self, pos):
        menu = QMenu(self)
        selection = self.vmap_table_view.selectionModel().selectedRows()
        if not selection: return
        remove_action = menu.addAction("Remove Selected")
        menu.addSeparator()
        check_action = menu.addAction("Check Selected")
        uncheck_action = menu.addAction("Uncheck Selected")
        action = menu.exec(self.vmap_table_view.mapToGlobal(pos))
        if action == remove_action:
            paths_to_remove = {self.vmap_model.item(index.row(), 1).data(Qt.UserRole) for index in selection}
            self.vmap_files = [p for p in self.vmap_files if p not in paths_to_remove]
            for p in paths_to_remove: self.vmap_ref_counts.pop(p, None)
            self._populate_vmap_table()
            self.on_vmap_item_changed()
        elif action == check_action:
            self.set_checked_state_for_selection(self.vmap_table_view, Qt.Checked)
        elif action == uncheck_action:
            self.set_checked_state_for_selection(self.vmap_table_view, Qt.Unchecked)

    def show_file_table_context_menu(self, pos):
        menu = QMenu(self)
        selection = self.table_view.selectionModel().selectedRows()
        if not selection: return
        check_action = menu.addAction("Check Selected")
        uncheck_action = menu.addAction("Uncheck Selected")
        action = menu.exec(self.table_view.mapToGlobal(pos))
        if action == check_action:
            self.set_checked_state_for_selection(self.table_view, Qt.Checked)
        elif action == uncheck_action:
            self.set_checked_state_for_selection(self.table_view, Qt.Unchecked)

    def set_checked_state_for_selection(self, table_view: QTableView, state: Qt.CheckState):
        model = table_view.model()
        selection = table_view.selectionModel().selectedRows()
        # FIXED: Refactored logic to be more robust and trigger a single, reliable update
        if model == self.file_model:
            try:
                model.itemChanged.disconnect(self.recalculate_size)
            except (RuntimeError, TypeError):
                pass
            for index in selection:
                item = model.item(index.row(), 0)
                if item.isCheckable(): item.setCheckState(state)
            model.itemChanged.connect(self.recalculate_size)
            self.recalculate_size()
        elif model == self.vmap_model:
            try:
                model.itemChanged.disconnect(self.on_vmap_item_changed)
            except (RuntimeError, TypeError):
                pass
            for index in selection:
                item = model.item(index.row(), 0)
                if item.isCheckable(): item.setCheckState(state)
            model.itemChanged.connect(self.on_vmap_item_changed)
            self.on_vmap_item_changed()

    # --- UNCHANGED METHODS ---

    def get_all_addon_files(self) -> Dict[str, int]:
        current_addon_name = get_addon_name()
        if not current_addon_name: return {}
        exclude_game_folders, include_content_folders = self.get_folder_filters()
        game_folder = os.path.join(cs2_path, 'game', 'csgo_addons', current_addon_name)
        content_folder = os.path.join(cs2_path, 'content', 'csgo_addons', current_addon_name)
        ignored_extensions = [ext.strip().lower() for ext in self.ignore_edit.text().split(',') if ext.strip()]
        vcs_ignore_dirs = {'.git', '.diversion'}
        vcs_ignore_files = {'.gitignore'}

        def collect(folder: str, include_subs: Optional[List[str]] = None, exclude_subs: Optional[List[str]] = None) -> \
        Dict[str, int]:
            files_map = {}
            if not os.path.isdir(folder): return {}
            for root, dirs, files in os.walk(folder):
                if self.ignore_vcs_checkbox.isChecked(): dirs[:] = [d for d in dirs if d not in vcs_ignore_dirs]
                if include_subs and root == folder: dirs[:] = [d for d in dirs if d in include_subs]
                if exclude_subs: dirs[:] = [d for d in dirs if d not in exclude_subs]
                if self.ignore_vcs_checkbox.isChecked(): files = [f for f in files if f not in vcs_ignore_files]
                for file in files:
                    if any(file.lower().endswith(ext) for ext in
                           ignored_extensions) or file in exclude_game_folders: continue
                    try:
                        file_path = os.path.join(root, file)
                        files_map[file_path] = os.path.getsize(file_path)
                    except OSError:
                        pass
            return files_map

        return {**collect(content_folder, include_subs=include_content_folders),
                **collect(game_folder, exclude_subs=exclude_game_folders)}

    def get_folder_filters(self) -> (List[str], List[str]):
        exclude_game_folders = ['tools_thumbnail_cache.bin']
        include_content_folders = None
        if not self.compiled_maps_checkbox.isChecked(): exclude_game_folders.append('maps')
        if not self.compiled_models_checkbox.isChecked(): exclude_game_folders.append('models')
        if not self.compiled_materials_checkbox.isChecked(): exclude_game_folders.append('materials')
        if self.skip_non_default_checkbox.isChecked():
            include_content_folders = ['maps', 'models', 'materials', 'postprocess', 'smartprops', 'soundevents',
                                       'sounds']
        return exclude_game_folders, include_content_folders

    def recalculate_size(self, item=None):
        total_size, file_count = 0, 0
        for row in range(self.file_model.rowCount()):
            if self.file_model.item(row, 0).checkState() == Qt.Checked:
                size_item = self.file_model.item(row, 2)
                if size_item:
                    total_size += size_item.data(Qt.UserRole)
                    file_count += 1
        self.size_label.setText(f'Selected for export: {file_count} files ({self.convert_size(total_size)})')

    def do_export_addon(self):
        if not get_addon_name(): return QMessageBox.warning(self, "Export Error", "No addon selected.")
        self.archive_addon()

    def do_import_addon(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Addon Archive", "", "Zip files (*.zip)")
        if not file_path: return
        addon_name = os.path.splitext(os.path.basename(file_path))[0]
        target_content_path = os.path.join(cs2_path, "content", "csgo_addons", addon_name)
        target_game_path = os.path.join(cs2_path, "game", "csgo_addons", addon_name)
        if os.path.exists(target_content_path) or os.path.exists(target_game_path):
            reply = QMessageBox.question(self, 'Addon Exists', f"The addon '{addon_name}' already exists. Overwrite?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No: return
            shutil.rmtree(target_content_path, ignore_errors=True)
            shutil.rmtree(target_game_path, ignore_errors=True)
        self.import_addon_process(file_path, addon_name)

    def import_addon_process(self, zip_file_path: str, addon_name: str):
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                progress = QProgressDialog(f"Importing {addon_name}...", "Cancel", 0, len(file_list), self)
                progress.setWindowModality(Qt.WindowModal);
                progress.setMinimumDuration(0)
                for i, member in enumerate(file_list):
                    zip_ref.extract(member, cs2_path)
                    progress.setValue(i + 1)
                    if progress.wasCanceled(): raise InterruptedError("Import canceled.")
                progress.setValue(len(file_list))
            QMessageBox.information(self, 'Import Successful', f"Addon '{addon_name}' imported successfully.")
        except Exception as e:
            QMessageBox.critical(self, 'Import Failed', f"Failed to import the addon.\nError: {str(e)}")

    def archive_addon(self):
        addon_name = get_addon_name()
        archive_path_setting = get_settings_value('PATHS', 'archive')
        if not all([addon_name, archive_path_setting, os.path.isdir(archive_path_setting)]):
            return QMessageBox.critical(self, "Archive Failed", "Archive path not set or invalid in settings.")
        files_to_archive = [self.file_model.item(row, 1).data(Qt.UserRole) for row in range(self.file_model.rowCount())
                            if self.file_model.item(row, 0).checkState() == Qt.Checked]
        if not files_to_archive: return QMessageBox.information(self, "Nothing to Archive", "No files selected.")
        destination_zip_path = os.path.join(archive_path_setting, addon_name + '.zip')
        if os.path.exists(destination_zip_path):
            if QMessageBox.question(self, 'File Exists', f"'{destination_zip_path}' already exists. Overwrite?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.No: return
        compression_map = {"Fastest": zipfile.ZIP_STORED, "Normal": zipfile.ZIP_DEFLATED,
                           "Ultra (Slow)": zipfile.ZIP_DEFLATED}
        level_map = {"Fastest": 0, "Normal": 6, "Ultra (Slow)": 9}
        compression = compression_map[self.compression_combo.currentText()]
        compresslevel = level_map[self.compression_combo.currentText()] if compression == zipfile.ZIP_DEFLATED else None
        progress = QProgressDialog("Archiving files...", "Cancel", 0, len(files_to_archive), self)
        progress.setWindowModality(Qt.WindowModal)
        try:
            with zipfile.ZipFile(destination_zip_path, 'w', compression, compresslevel=compresslevel) as zipf:
                for i, file_path in enumerate(files_to_archive):
                    progress.setValue(i);
                    if progress.wasCanceled(): raise InterruptedError("Archiving canceled.")
                    zipf.write(file_path, os.path.relpath(file_path, cs2_path))
                progress.setValue(len(files_to_archive))
            self.show_archive_completion_dialog(destination_zip_path)
        except Exception as e:
            if os.path.exists(destination_zip_path): os.remove(destination_zip_path)
            QMessageBox.critical(self, 'Archive Failed', f'Failed to archive the addon.\nError: {str(e)}')

    def show_archive_completion_dialog(self, zip_path: str):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Archive Completed")
        msg_box.setText(f"Addon successfully archived to:\n{zip_path}")
        open_button = msg_box.addButton("Open Archive Location", QMessageBox.ActionRole)
        msg_box.addButton(QMessageBox.Ok)
        msg_box.exec()
        if msg_box.clickedButton() == open_button: self.open_folder(os.path.dirname(zip_path))

    def open_file_location(self, index: QModelIndex):
        item = self.file_model.item(index.row(), 1)
        if item and (file_path := item.data(Qt.UserRole)) and os.path.exists(file_path):
            self.open_folder(os.path.dirname(file_path))

    def open_folder(self, path: str):
        if not os.path.isdir(path): return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @staticmethod
    def convert_size(size_bytes: int) -> str:
        if size_bytes == 0: return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024))) if size_bytes > 0 else 0
        s = round(size_bytes / math.pow(1024, i), 2)
        return f"{s} {size_name[i]}"