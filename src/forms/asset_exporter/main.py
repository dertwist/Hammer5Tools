import os
from PySide6.QtWidgets import QWidget, QFileSystemModel, QFileDialog, QMessageBox, QDockWidget, QMainWindow
from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtGui import QStandardItemModel, QStandardItem
from .ui_main import Ui_AssetExporterWidget
from .dependency_resolver import DependencyResolver
from .exporter import ExportWorker
from src.settings.main import get_addon_name, get_cs2_path
from src.common import enable_dark_title_bar
from src.styles.common import apply_stylesheets, qt_stylesheet_widgetlist2

class AssetExporterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_AssetExporterWidget()
        self.ui.setupUi(self)
        
        enable_dark_title_bar(self)
        apply_stylesheets(self)
        
        self.ui.deps_list.setStyleSheet(qt_stylesheet_widgetlist2)

        self.cs2_path = get_cs2_path()
        if not self.cs2_path:
            return

        self.addon_name = get_addon_name()
        self.addon_content_path = os.path.join(self.cs2_path, 'content', 'csgo_addons', self.addon_name)

        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("Export Asset")
        self.ui.source_tree.hide()
        self.ui.btn_resolve.hide()
        self.sources_to_export = []

        # Setup source tree model
        self.source_model = QFileSystemModel()
        self.source_model.setRootPath(self.addon_content_path)
        # Filter for supported types
        self.source_model.setNameFilters(['*.vmdl', '*.vsmart', '*.vmat', '*.vpcf', '*.vsndevts', '*.vsnd', '*.vtex'])
        self.source_model.setNameFilterDisables(False)

        self.ui.source_tree.setModel(self.source_model)
        self.ui.source_tree.setRootIndex(self.source_model.index(self.addon_content_path))
        self.ui.source_tree.setColumnWidth(0, 250)

        # Connect signals
        self.ui.btn_resolve.clicked.connect(self.resolve_dependencies)
        self.ui.btn_browse.clicked.connect(self.browse_output_dir)
        self.ui.btn_export.clicked.connect(self.start_export)
        self.ui.radio_thirdparty.toggled.connect(self.toggle_thirdparty_fields)
        self.ui.radio_preserve.toggled.connect(self.toggle_thirdparty_fields)

        self.toggle_thirdparty_fields()

        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        self.ui.edit_output_dir.setText(os.path.normpath(desktop_dir))
        
        from PySide6.QtWidgets import QCheckBox
        self.ui.checkbox_zip = QCheckBox("Export to ZIP Archive (name based on selected asset)")
        self.ui.checkbox_zip.setChecked(True)
        self.ui.verticalLayout.insertWidget(6, self.ui.checkbox_zip)
        
        self.deps_model = QStandardItemModel()
        self.ui.deps_list.setModel(self.deps_model)

    def toggle_thirdparty_fields(self):
        is_thirdparty = self.ui.radio_thirdparty.isChecked()
        self.ui.edit_addon_name.setVisible(is_thirdparty)
        self.ui.edit_asset_stem.setVisible(is_thirdparty)

    def select_file(self, full_paths):
        """Automatically select files and resolve their dependencies."""
        if isinstance(full_paths, str):
            full_paths = [full_paths]
        self.sources_to_export = full_paths
        self.resolve_dependencies()

    def resolve_dependencies(self):
        if not self.sources_to_export:
            return

        self.deps_model.clear()
        
        resolver = DependencyResolver(self.addon_content_path)
        resolved_files = set()
        all_missing_deps = set()

        for path in self.sources_to_export:
            if os.path.isfile(path):
                deps = resolver.resolve(path)
                resolved_files.update(deps)
                all_missing_deps.update(resolver.missing_deps)

        for dep in sorted(list(resolved_files)):
            item = QStandardItem(os.path.relpath(dep, self.addon_content_path))
            item.setCheckable(True)
            item.setCheckState(Qt.Checked)
            item.setData(dep, Qt.UserRole)
            self.deps_model.appendRow(item)
            
        if all_missing_deps:
            missing_str = "\n".join(list(all_missing_deps)[:10])
            if len(all_missing_deps) > 10:
                missing_str += f"\n... and {len(all_missing_deps) - 10} more."
            QMessageBox.warning(
                self, 
                "Missing Dependencies", 
                f"The following dependencies could not be found and will not be exported:\n\n{missing_str}"
            )

    def browse_output_dir(self):
        start_dir = self.ui.edit_output_dir.text() or os.path.join(os.path.expanduser("~"), "Desktop")
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory", start_dir)
        if d:
            self.ui.edit_output_dir.setText(os.path.normpath(d))

    def start_export(self):
        output_dir = self.ui.edit_output_dir.text()
        if not output_dir:
            QMessageBox.warning(self, "Warning", "Please select an output directory.")
            return

        is_thirdparty = self.ui.radio_thirdparty.isChecked()
        addon_name = self.ui.edit_addon_name.text()
        asset_stem = self.ui.edit_asset_stem.text()

        if is_thirdparty and (not addon_name or not asset_stem):
            QMessageBox.warning(self, "Warning", "Please enter Addon Name and Asset Stem for Third-Party layout.")
            return

        files_to_export = []
        for row in range(self.deps_model.rowCount()):
            item = self.deps_model.item(row)
            if item.checkState() == Qt.Checked:
                files_to_export.append(item.data(Qt.UserRole))

        if not files_to_export:
            QMessageBox.warning(self, "Warning", "No files selected to export.")
            return

        layout = 'thirdparty' if is_thirdparty else 'preserve'

        export_to_zip = self.ui.checkbox_zip.isChecked()
        zip_name = "Export"
        if self.sources_to_export:
            first_src = os.path.basename(self.sources_to_export[0])
            zip_name = os.path.splitext(first_src)[0]

        self.worker = ExportWorker(
            files_to_export,
            self.addon_content_path,
            output_dir,
            layout,
            addon_name,
            asset_stem,
            export_to_zip,
            zip_name
        )
        self.worker.progress.connect(self.ui.progress_bar.setValue)
        self.worker.finished_export.connect(self.on_export_finished)
        self.ui.btn_export.setEnabled(False)
        self.ui.progress_bar.setValue(0)
        self.worker.start()

    def on_export_finished(self, dest_root):
        self.ui.btn_export.setEnabled(True)
        QMessageBox.information(self, "Success", "Export finished successfully.")
        os.startfile(dest_root)
