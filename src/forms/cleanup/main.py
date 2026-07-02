from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QCheckBox, QLineEdit, \
    QDialog, QPushButton, QTableView, QComboBox, QMessageBox, QHeaderView, QMenu, QSizePolicy, QTextEdit, QProgressBar
from PySide6.QtCore import Qt, QSortFilterProxyModel, QThread, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction
import os, sys, re, subprocess, time
from src.styles.common import qt_stylesheet_combobox, qt_stylesheet_checkbox, qt_stylesheet_button, qt_stylesheet_table

from src.settings.main import get_addon_name, get_addon_dir, get_cs2_path
from src.widgets import qt_stylesheet_button, enable_dark_title_bar
from src.forms.cleanup.common import format_size
from src.forms.cleanup.parse import get_junk_files


class VerificationThread(QThread):
    output_signal = Signal(str)
    error_signal = Signal(str)
    finished_signal = Signal(list, dict)  # returns list of errors found, and dict of errors by map

    def __init__(self, cs2_path, addon_dir, vmap_paths):
        super().__init__()
        self.cs2_path = cs2_path
        self.addon_dir = addon_dir
        self.vmap_paths = vmap_paths
        self.errors_found = []
        self.errors_by_map = {path: [] for path in vmap_paths}
        self.is_aborted = False
        self.process = None

    def run(self):
        rc_exe = os.path.join(self.cs2_path, "game", "bin", "win64", "resourcecompiler.exe")
        if not os.path.exists(rc_exe):
            self.errors_found.append(f"Resource compiler not found at: {rc_exe}")
            self.finished_signal.emit(self.errors_found, self.errors_by_map)
            return

        for map_rel_path in self.vmap_paths:
            if self.is_aborted:
                break
            
            map_abs_path = os.path.join(self.addon_dir, map_rel_path)
            if not os.path.exists(map_abs_path):
                continue
                
            self.output_signal.emit(f"Checking map: {map_rel_path}...")
            
            cmd = [
                rc_exe,
                "-threads", str(os.cpu_count() or 4),
                "-fshallow",
                "-maxtextureres", "256",
                "-dxlevel", "110",
                "-quiet",
                "-unbufferedio",
                "-noassert",
                "-i", map_abs_path,
                "-world"
            ]
            
            try:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=self.addon_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors='ignore',
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
                
                start_time = time.time()
                while True:
                    if self.is_aborted:
                        self.process.terminate()
                        break
                        
                    if time.time() - start_time > 20.0:
                        self.output_signal.emit("Timeout reached, moving to next map.")
                        self.process.terminate()
                        break
                        
                    line = self.process.stdout.readline()
                    if not line and self.process.poll() is not None:
                        break
                        
                    if line:
                        line_stripped = line.strip()
                        self.output_signal.emit(line_stripped)
                        
                        lower_line = line_stripped.lower()
                        is_missing_ref = "failed loading resource" in lower_line or "doesn't exist in" in lower_line
                        
                        has_asset_ext = any(ext in lower_line for ext in [
                            '.vmat', '.vmt', '.vmdl', '.vmdl_prefab', '.vpcf', '.vsndevts', '.vtex',
                            '.vmat_c', '.vmt_c', '.vmdl_c', '.vmdl_prefab_c', '.vpcf_c', '.vsndevts_c', '.vtex_c'
                        ])
                        
                        if is_missing_ref and has_asset_ext:
                            self.errors_found.append(line_stripped)
                            self.errors_by_map[map_rel_path].append(line_stripped)
                            self.error_signal.emit(line_stripped)
                            
                        if "settling physics objects" in lower_line or "simulated" in lower_line or "--> map build finished" in lower_line:
                            self.output_signal.emit("File checks complete. Stopping compiler.")
                            self.process.terminate()
                            break
                            
                self.process.wait()
            except Exception as e:
                err_msg = f"Error compiling {map_rel_path}: {e}"
                self.errors_found.append(err_msg)
                self.errors_by_map[map_rel_path].append(err_msg)
                
        self.finished_signal.emit(self.errors_found, self.errors_by_map)

    def abort(self):
        self.is_aborted = True
        if self.process:
            try:
                if os.name == 'nt' and self.process.pid:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)],
                                   capture_output=True, check=False)
                else:
                    self.process.terminate()
            except Exception:
                pass


class VerificationDialog(QDialog):
    def __init__(self, cs2_path, addon_dir, vmap_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Verification - Cleanup Addon")
        enable_dark_title_bar(self)
        self.setMinimumSize(700, 450)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Verifying Addon Cleanup")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #E3E3E3;")
        layout.addWidget(title)
        
        self.status_label = QLabel("Initializing compilation check...")
        self.status_label.setStyleSheet("color: #E3E3E3;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #505050;
                border-radius: 2px;
                text-align: center;
                color: white;
                background-color: #1C1C1C;
            }
            QProgressBar::chunk {
                background-color: #1a528a;
            }
        """)
        self.progress_bar.setRange(0, len(vmap_paths))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas, Courier New, monospace;
                font-size: 11px;
                border: 1px solid #333333;
            }
        """)
        layout.addWidget(self.log_view)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setStyleSheet(qt_stylesheet_button)
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        
        self.abort_btn = QPushButton("Abort")
        self.abort_btn.setStyleSheet(qt_stylesheet_button)
        self.abort_btn.clicked.connect(self.abort_verification)
        
        btn_layout.addWidget(self.close_btn)
        btn_layout.addWidget(self.abort_btn)
        layout.addLayout(btn_layout)
        
        self.thread = VerificationThread(cs2_path, addon_dir, vmap_paths)
        self.thread.output_signal.connect(self.append_log)
        self.thread.error_signal.connect(self.append_error)
        self.thread.finished_signal.connect(self.verification_finished)
        
        self.errors_count = 0
        self.vmap_paths = vmap_paths
        self.current_index = 0
        
        self.thread.start()

    def append_log(self, text):
        if text.startswith("Checking map:"):
            self.status_label.setText(text)
            self.current_index += 1
            self.progress_bar.setValue(self.current_index)
        self.log_view.append(text)

    def append_error(self, error):
        self.errors_count += 1
        self.log_view.append(f'<span style="color: #F44336; font-weight: bold;">[ERROR] {error}</span>')

    def abort_verification(self):
        self.thread.abort()
        self.log_view.append('<span style="color: #FF9800; font-weight: bold;">Verification aborted by user.</span>')
        self.status_label.setText("Verification aborted.")
        self.abort_btn.setEnabled(False)
        self.close_btn.setEnabled(True)

    def verification_finished(self, errors, errors_by_map):
        self.abort_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        
        # Split the report from the actual log using - symbols
        self.log_view.append("\n")
        self.log_view.append('<span style="color: #555555;">----------------------------------------------------------------------</span>\n')
        
        # Extract unique missing paths across all maps
        all_unique_missing = []
        
        def extract_missing_path(err):
            import re
            m = re.search(r'"([^"]+)"', err)
            if m:
                path = m.group(1)
                if path.endswith('_c'):
                    path = path[:-2]
                return path
            if "doesn't exist in" in err:
                parts = err.split("doesn't exist in")
                if len(parts) > 1:
                    path = parts[1].strip().rstrip('!')
                    if path.endswith('_c'):
                        path = path[:-2]
                    return path
            return err

        if errors:
            self.status_label.setText(f"Verification complete. Detected {len(errors)} error(s)!")
            self.log_view.append(f'<span style="color: #F44336; font-weight: bold; font-size: 13px;">'
                                 f'WARNING: {len(errors)} missing resource references found! Please review the log above.</span>\n')
            
            self.log_view.append('<span style="color: #E3E3E3; font-weight: bold;">Missing files per vmap file</span>\n')
            
            for map_rel_path, map_errors in errors_by_map.items():
                if map_errors:
                    self.log_view.append(f'<span style="color: #F44336; font-weight: bold;">{map_rel_path} (missing {len(map_errors)}):</span>')
                    
                    unique_map_paths = []
                    for err in map_errors:
                        path = extract_missing_path(err)
                        if path not in unique_map_paths:
                            unique_map_paths.append(path)
                        if path not in all_unique_missing:
                            all_unique_missing.append(path)
                            
                    for path in unique_map_paths:
                        self.log_view.append(f'<span style="color: #FF7043;">- {path}</span>')
                    self.log_view.append("")  # blank line after map with errors
                else:
                    self.log_view.append(f'<span style="color: #4CAF50;">{map_rel_path} (missing 0)</span>')
            
            self.log_view.append('\n<span style="color: #E3E3E3; font-weight: bold;">Missing files (all missing files combined):</span>')
            for path in sorted(all_unique_missing):
                self.log_view.append(f'<span style="color: #FF7043;">- {path}</span>')
            self.log_view.append("")
            
            QMessageBox.warning(self, "Verification Warning", 
                                f"Detected {len(errors)} missing materials/models reference(s)!\n"
                                "Please review the log to make sure nothing important was deleted.")
        else:
            self.status_label.setText("Verification complete. No errors detected!")
            
            self.log_view.append('<span style="color: #4CAF50; font-weight: bold; font-size: 13px;">'
                                 'SUCCESS: No missing materials or models detected.</span>\n')
            
            self.log_view.append('<span style="color: #E3E3E3; font-weight: bold;">Missing files per vmap file</span>\n')
            for map_rel_path in errors_by_map.keys():
                self.log_view.append(f'<span style="color: #4CAF50;">{map_rel_path} (missing 0)</span>')
            
            self.log_view.append('\n<span style="color: #E3E3E3; font-weight: bold;">Missing files (all missing files combined):</span>')
            self.log_view.append('<span style="color: #4CAF50;">None</span>\n')
            
            QMessageBox.information(self, "Verification Success", 
                                    "No missing materials or models references detected.")


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
            "\n\nWarning! .vmdl files that don't have any of the following properties: DefaultMaterialGroup, ReplaceMaterial, or MaterialGroup will have no material references!\n"
        )
        instructions_label.setWordWrap(True)
        main_layout.addWidget(instructions_label)

        # Checkbox option for mesh scanning
        self.scan_meshes_checkbox = QCheckBox("Scan source mesh files (.fbx, .dmx) for material references")
        self.scan_meshes_checkbox.setStyleSheet(qt_stylesheet_checkbox)
        self.scan_meshes_checkbox.setChecked(True)
        main_layout.addWidget(self.scan_meshes_checkbox)

        # Dirtlist row
        dirtlist_layout = QHBoxLayout()
        dirtlist_label = QLabel(
            'Files listed in <b>.dirtlist</b> will be ignored during cleanup.'
        )
        dirtlist_label.setStyleSheet("color: #999999; font-size: 11px; background-color: transparent;")
        dirtlist_layout.addWidget(dirtlist_label)
        dirtlist_layout.addStretch()

        self.dirtlist_button = QPushButton("Open .dirtlist")
        self.dirtlist_button.setStyleSheet(qt_stylesheet_button)
        self.dirtlist_button.setFixedWidth(120)
        self.dirtlist_button.clicked.connect(self.open_dirtlist)
        dirtlist_layout.addWidget(self.dirtlist_button)

        main_layout.addLayout(dirtlist_layout)

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
        self.table_view.setStyleSheet(qt_stylesheet_table)
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

        self.verify_button = QPushButton("Verify")
        self.verify_button.setStyleSheet(qt_stylesheet_button)
        button_layout.addWidget(self.verify_button)

        self.cleanup_button = QPushButton("Delete Selected Files")
        self.cleanup_button.setStyleSheet(qt_stylesheet_button)
        self.cleanup_button.setDefault(True)
        button_layout.addWidget(self.cleanup_button)

        # Connect buttons to their respective actions
        self.recalculate_button.clicked.connect(self.recalculate)
        self.verify_button.clicked.connect(self.run_verification)
        self.cleanup_button.clicked.connect(self.cleanup_addon)

        footer_layout.addLayout(button_layout)
        main_layout.addLayout(footer_layout)


        # Data & model setup
        self.addon_dir = get_addon_dir()
        self.vmap_path = os.path.join(self.addon_dir, "maps", f"{get_addon_name()}.vmap")
        self.junk_files = get_junk_files(addon_dir=self.addon_dir, vmap=self.vmap_path, scan_meshes=self.scan_meshes_checkbox.isChecked())
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
        self.scan_meshes_checkbox.stateChanged.connect(self.recalculate)

        # Style labels for dark mode
        for label in self.findChildren(QLabel):
            label.setStyleSheet("color: #E3E3E3; background-color: transparent;")

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
        # Recalculate junk files based on current addon dir and vmap path
        scan_meshes = self.scan_meshes_checkbox.isChecked()
        self.junk_files = get_junk_files(addon_dir=self.addon_dir, vmap=self.vmap_path, scan_meshes=scan_meshes)

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
        open_explorer_action = QAction("Open in Explorer", self)

        select_action.triggered.connect(lambda: self.set_selected_rows_checked(indexes, Qt.Checked))
        deselect_action.triggered.connect(lambda: self.set_selected_rows_checked(indexes, Qt.Unchecked))
        open_explorer_action.triggered.connect(lambda: self.open_in_explorer(indexes))

        menu.addAction(select_action)
        menu.addAction(deselect_action)
        menu.addAction(open_explorer_action)
        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def open_in_explorer(self, indexes):
        if not indexes:
            return
        # Open the folder containing the first selected file
        proxy_index = indexes[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        item = self.model.item(source_index.row(), 0)
        if item is not None:
            file_path = item.data(Qt.UserRole)
            addon_dir = os.path.join(get_addon_dir())
            abs_path = os.path.abspath(os.path.join(addon_dir, file_path))
            folder = os.path.dirname(abs_path)
            if os.path.exists(folder):
                try:
                    if os.name == 'nt':
                        os.startfile(folder)
                    elif sys.platform == 'darwin':
                        import subprocess
                        subprocess.Popen(['open', folder])
                    else:
                        import subprocess
                        subprocess.Popen(['xdg-open', folder])
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not open folder: {e}")

    def set_selected_rows_checked(self, indexes, state):
        for proxy_index in indexes:
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.model.item(source_index.row(), 0)
            if item is not None:
                item.setCheckState(state)
    def open_dirtlist(self):
        """Open the .dirtlist file in the default text editor. Create it if it doesn't exist."""
        dirtlist_path = os.path.join(self.addon_dir, '.dirtlist')
        if not os.path.exists(dirtlist_path):
            try:
                with open(dirtlist_path, 'w', encoding='utf-8') as f:
                    f.write("# Dirtlist - Files listed here will be ignored during cleanup.\n"
                            "# Add one relative file path per line (relative to addon directory).\n"
                            "# Lines starting with # are comments.\n"
                            "# Example:\n"
                            "# models/props/my_model.vmdl\n"
                            "# materials/my_texture.tga\n")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create .dirtlist file: {e}")
                return
        try:
            if os.name == 'nt':
                os.startfile(dirtlist_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', dirtlist_path])
            else:
                subprocess.Popen(['xdg-open', dirtlist_path])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open .dirtlist file: {e}")

    def run_verification(self):
        cs2_path = get_cs2_path()
        if not cs2_path:
            QMessageBox.critical(self, "Error", "CS2 installation path not found. Please set it in settings.")
            return
            
        try:
            from src.forms.cleanup.parse import get_vmap_references
            _, referenced_files = get_vmap_references(
                self.addon_dir, 
                self.vmap_path, 
                scan_meshes=self.scan_meshes_checkbox.isChecked()
            )
            vmaps = [f for f in referenced_files if f.lower().endswith('.vmap')]
            
            main_rel = os.path.relpath(self.vmap_path, self.addon_dir).replace('\\', '/').lower()
            if main_rel in vmaps:
                vmaps.remove(main_rel)
                vmaps.insert(0, main_rel)
                
            if not vmaps:
                QMessageBox.information(self, "No Maps", "No maps found to verify.")
                return
                
            verify_dialog = VerificationDialog(cs2_path, self.addon_dir, vmaps, self)
            for label in verify_dialog.findChildren(QLabel):
                label.setStyleSheet("color: #E3E3E3; background-color: transparent;")
            verify_dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Verification Error", f"Failed to start verification: {e}")
