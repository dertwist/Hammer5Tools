import os
from typing import Optional, Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QMessageBox, QFrame, QCheckBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, QByteArray
from PySide6.QtGui import QIcon

from src.settings.main import (
    get_addon_dir, get_cs2_path, get_addon_name, debug,
    get_settings_value, set_settings_value
)
from src.editors.assetgroup_maker.widgets.reference_card import MultiTemplateManagerWidget
from src.editors.assetgroup_maker.widgets.asset_table import AssetTableWidget
from src.editors.assetgroup_maker.matcher import match_multi_template_folder_assets, AssetGroupItem
from src.editors.assetgroup_maker.process import perform_batch_processing
from src.editors.assetgroup_maker.objects import load_hbat_file, save_hbat_file, get_default_file
from src.styles.common import qt_stylesheet_button, qt_stylesheet_checkbox, qt_stylesheet_lineedit, apply_stylesheets


class EditorTabWidget(QWidget):
    """
    Self-contained editor widget for a multi-template .hbat batch profile document.
    Includes MultiTemplateManager, AssetTable, and Action Footer.
    """

    dirty_changed = Signal(bool)
    title_changed = Signal(str)
    status_updated = Signal(str)

    def __init__(self, file_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.file_path: Optional[str] = file_path
        self._dirty: bool = False
        self.created_files: List[str] = []

        self._build_ui()
        self._connect_signals()

        if self.file_path and os.path.isfile(self.file_path):
            self.load_file(self.file_path)
        else:
            self._apply_default_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # Splitter dividing Template Manager and Asset Table
        self.splitter = QSplitter(Qt.Vertical, self)
        self.splitter.setObjectName("AssetGroup_EditorSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(4)

        # 1. Top Multi-Template Manager (Cards in ScrollArea + Global Ignore Settings + Add Template button)
        self.template_manager = MultiTemplateManagerWidget(self)
        self.splitter.addWidget(self.template_manager)

        # 2. Center Asset Table
        self.asset_table = AssetTableWidget(self)
        self.splitter.addWidget(self.asset_table)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        self._restore_splitter_state()
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        root.addWidget(self.splitter, 1)

        # 3. Bottom Action Footer
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: #2E2E2E;
                border: 1px solid #464649;
                border-radius: 2px;
            }
        """)
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(8, 8, 8, 8)
        footer_layout.setSpacing(6)

        # Output Directory Row
        opt_row = QHBoxLayout()
        opt_row.setSpacing(8)

        output_lbl = QLabel("Output Directory:")
        output_lbl.setStyleSheet("color: #A5A5A5; font: 580 9pt 'Segoe UI';")
        output_lbl.setFixedHeight(28)
        opt_row.addWidget(output_lbl)

        self.custom_output_edit = QLineEdit()
        self.custom_output_edit.setStyleSheet(qt_stylesheet_lineedit)
        self.custom_output_edit.setPlaceholderText("Output directory relative to addon (leave blank to output in asset folder)...")
        self.custom_output_edit.setFixedHeight(28)
        self.custom_output_edit.textChanged.connect(self._on_output_text_changed)
        opt_row.addWidget(self.custom_output_edit, 1)

        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.setIcon(QIcon(":/valve_common/icons/tools/common/open.png"))
        self.browse_output_btn.setStyleSheet(qt_stylesheet_button)
        self.browse_output_btn.setFixedHeight(28)
        self.browse_output_btn.clicked.connect(self._on_browse_output)
        opt_row.addWidget(self.browse_output_btn)

        footer_layout.addLayout(opt_row)

        # Actions and Status row
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.status_label = QLabel("No assets loaded")
        self.status_label.setStyleSheet("color: #A5A5A5; font: 580 9pt 'Segoe UI';")
        self.status_label.setFixedHeight(28)
        action_row.addWidget(self.status_label, 1)

        self.watch_changes_cb = QCheckBox("Watch the changes")
        self.watch_changes_cb.setStyleSheet(qt_stylesheet_checkbox)
        self.watch_changes_cb.setToolTip("Automatically monitor asset files and live-update batch configuration on changes")
        self.watch_changes_cb.setChecked(False)
        self.watch_changes_cb.setFixedHeight(28)
        self.watch_changes_cb.toggled.connect(self._on_watch_changes_toggled)
        action_row.addWidget(self.watch_changes_cb)

        self.save_btn = QPushButton("Save")
        self.save_btn.setIcon(QIcon(":/valve_common/icons/tools/common/save.png"))
        self.save_btn.setStyleSheet(qt_stylesheet_button)
        self.save_btn.setFixedHeight(28)
        self.save_btn.setToolTip("Save this Batch Profile (Ctrl+S)")
        self.save_btn.clicked.connect(lambda: self.save_file())
        action_row.addWidget(self.save_btn)

        self.revert_btn = QPushButton("Revert Batch")
        self.revert_btn.setStyleSheet(qt_stylesheet_button)
        self.revert_btn.setEnabled(False)
        self.revert_btn.setFixedHeight(28)
        self.revert_btn.setToolTip("Delete files created by the last batch process")
        self.revert_btn.clicked.connect(self.revert_created_files)
        action_row.addWidget(self.revert_btn)

        self.process_btn = QPushButton("Process Batch")
        self.process_btn.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.process_btn.setStyleSheet(qt_stylesheet_button)
        self.process_btn.setFixedHeight(28)
        self.process_btn.clicked.connect(self.process_all)
        action_row.addWidget(self.process_btn)

        footer_layout.addLayout(action_row)
        root.addWidget(footer_frame)

        apply_stylesheets(self)

    def _restore_splitter_state(self):
        saved_state = get_settings_value('AssetGroupMaker', 'editor_splitter_state')
        if saved_state:
            try:
                self.splitter.restoreState(QByteArray.fromHex(saved_state.encode('utf-8')))
                return
            except Exception as e:
                debug(f"Error restoring editor splitter state: {e}")
        self.splitter.setSizes([220, 480])

    def _on_splitter_moved(self, pos: int, index: int):
        try:
            state_hex = self.splitter.saveState().toHex().data().decode('utf-8')
            set_settings_value('AssetGroupMaker', 'editor_splitter_state', state_hex)
        except Exception as e:
            debug(f"Error saving editor splitter state: {e}")

    def _connect_signals(self):
        self.template_manager.data_changed.connect(self._on_template_data_changed)
        self.template_manager.analysis_updated.connect(self.refresh_matching)
        self.asset_table.files_dropped.connect(self._on_files_dropped)
        self.asset_table.slots_modified.connect(self._on_table_slots_modified)

    def _on_template_data_changed(self):
        self._mark_dirty()
        self.refresh_matching()

    def _on_output_text_changed(self):
        self._mark_dirty()

    def _on_table_slots_modified(self, item):
        self._mark_dirty()
        items = self.asset_table.get_items()
        ready_count = sum(1 for i in items if i.status == "ready")
        warn_count = sum(1 for i in items if i.status == "warning")
        err_count = sum(1 for i in items if i.status == "error")
        self.status_label.setText(
            f"Total: {len(items)} assets | Ready: {ready_count} | Warnings: {warn_count} | Errors: {err_count}"
        )

    def _apply_default_data(self):
        default = get_default_file()
        self.template_manager.set_data(default)
        custom_out = default.get('settings', {}).get('custom_output', '')
        if custom_out.lower() == 'relative_path':
            custom_out = ''
        self.custom_output_edit.setText(custom_out)
        self.watch_changes_cb.blockSignals(True)
        self.watch_changes_cb.setChecked(default.get('settings', {}).get('watch_changes', False))
        self.watch_changes_cb.blockSignals(False)
        self.refresh_matching()
        self._dirty = False
        self.dirty_changed.emit(False)

    def _on_watch_changes_toggled(self, checked: bool):
        self._mark_dirty()
        if self.file_path:
            from src.editors.assetgroup_maker.monitor import MonitoringFileWatcher
            for watcher in MonitoringFileWatcher._instances:
                watcher.update_watch_status(self.file_path, checked)

    def _on_browse_output(self):
        addon_dir = get_addon_dir() or ""
        chosen = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", addon_dir
        )
        if chosen:
            if addon_dir:
                try:
                    rel = os.path.relpath(chosen, addon_dir).replace('\\', '/')
                except ValueError:
                    rel = chosen
            else:
                rel = chosen
            self.custom_output_edit.setText(rel)
            self._mark_dirty()

    def _on_files_dropped(self, paths: List[str]):
        for path in paths:
            if os.path.isdir(path):
                self.file_path = os.path.join(path, f"{os.path.basename(path)}.hbat")
                self.title_changed.emit(os.path.basename(self.file_path))
                self.refresh_matching()
                self._mark_dirty()
                return

    def refresh_matching(self):
        """Scans the target directory and matches assets across all active templates."""
        data = self.template_manager.get_data()
        templates = data.get('templates', [])
        settings = data.get('settings', {})
        slots_map = self.template_manager.get_analyzed_slots_map()

        self.asset_table.set_slots_definition(slots_map)

        target_dir = ""
        if self.file_path:
            target_dir = os.path.splitext(self.file_path)[0]
            if not os.path.isdir(target_dir):
                target_dir = os.path.dirname(self.file_path)

        if not target_dir and get_addon_dir():
            target_dir = get_addon_dir()

        items = match_multi_template_folder_assets(
            directory=target_dir,
            templates=templates,
            settings=settings,
            analyzed_slots_map=slots_map
        )

        self.asset_table.set_items(items)

        # Update status footer
        ready_count = sum(1 for i in items if i.status == "ready")
        warn_count = sum(1 for i in items if i.status == "warning")
        err_count = sum(1 for i in items if i.status == "error")

        self.status_label.setText(
            f"Total: {len(items)} assets | Ready: {ready_count} | Warnings: {warn_count} | Errors: {err_count}"
        )
        self.process_btn.setText(f"Process Batch ({len(items)} Assets)")
        self.process_btn.setEnabled(len(items) > 0)

    def load_file(self, file_path: str):
        """Loads .hbat file (auto-detecting and converting legacy JSON if necessary)."""
        try:
            self.file_path = os.path.normpath(file_path)
            data = load_hbat_file(self.file_path)

            self.template_manager.set_data(data)

            settings = data.get('settings', {})
            custom_out = settings.get('custom_output', '')
            if custom_out.lower() == 'relative_path':
                custom_out = ''
            self.custom_output_edit.setText(custom_out)

            watch_val = settings.get('watch_changes', False)
            self.watch_changes_cb.blockSignals(True)
            self.watch_changes_cb.setChecked(bool(watch_val))
            self.watch_changes_cb.blockSignals(False)

            self._dirty = False
            self.title_changed.emit(os.path.basename(self.file_path))
            self.refresh_matching()
            debug(f"[EditorTab] Loaded file: {self.file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load batch file:\n{e}")

    def save_file(self, path: Optional[str] = None):
        """Saves current state to KeyValues3 .hbat file."""
        target_path = path or self.file_path
        if not target_path:
            addon_dir = get_addon_dir() or ""
            target_path, _ = QFileDialog.getSaveFileName(
                self, "Save Batch Profile", addon_dir, "Hammer Batch (*.hbat)"
            )
            if not target_path:
                return False
            self.file_path = target_path

        data = self.template_manager.get_data()
        data['version'] = 3
        data['settings']['watch_changes'] = self.watch_changes_cb.isChecked()
        data['settings']['custom_output'] = self.custom_output_edit.text().strip() or 'relative_path'

        try:
            success = save_hbat_file(self.file_path, data)
            if success:
                self._dirty = False
                self.dirty_changed.emit(False)
                self.title_changed.emit(os.path.basename(self.file_path))
                debug(f"[EditorTab] Saved KV3 file: {self.file_path}")

                from src.editors.assetgroup_maker.monitor import MonitoringFileWatcher
                for watcher in MonitoringFileWatcher._instances:
                    watcher.update_watch_status(self.file_path, self.watch_changes_cb.isChecked())

                return True
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save KeyValues3 file.")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{e}")
            return False

    def process_all(self):
        """Executes batch creation for all configured templates."""
        if not self.file_path:
            if not self.save_file():
                return

        self.save_file()
        data = self.template_manager.get_data()
        data['settings']['custom_output'] = self.custom_output_edit.text().strip()

        created = perform_batch_processing(
            file_path=self.file_path,
            config_data=data
        )

        if created:
            self.created_files.extend(created)
            self.revert_btn.setEnabled(True)
            self.status_updated.emit(f"Successfully created {len(created)} asset file(s) across templates!")
        else:
            self.status_updated.emit("No assets were created. Check reference templates and source files.")

    def revert_created_files(self):
        """Reverts (deletes) all created files from the last process run."""
        if not self.created_files:
            return

        reply = QMessageBox.question(
            self,
            "Revert Created Files",
            f"Are you sure you want to delete {len(self.created_files)} created asset file(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            deleted_count = 0
            for path in self.created_files:
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                        deleted_count += 1
                    except Exception as e:
                        debug(f"Failed to remove file {path}: {e}")
            self.created_files.clear()
            self.revert_btn.setEnabled(False)
            self.status_updated.emit(f"Reverted {deleted_count} file(s).")
            QMessageBox.information(self, "Revert Complete", f"Reverted {deleted_count} file(s).")

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self.dirty_changed.emit(True)

    def has_unsaved_changes(self) -> bool:
        return self._dirty
