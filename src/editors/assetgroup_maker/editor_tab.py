import os
import json
from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QMessageBox, QFrame, QCheckBox
)
from PySide6.QtCore import Qt, Signal

from src.settings.main import get_addon_dir, get_cs2_path, get_addon_name, debug
from src.editors.assetgroup_maker.widgets.reference_card import ReferenceCardWidget
from src.editors.assetgroup_maker.widgets.asset_table import AssetTableWidget
from src.editors.assetgroup_maker.matcher import match_folder_assets, AssetGroupItem
from src.editors.assetgroup_maker.process import perform_batch_processing
from src.editors.assetgroup_maker.objects import get_default_file
from src.styles.common import qt_stylesheet_button


class EditorTabWidget(QWidget):
    """
    Self-contained editor widget for a single .hbat batch profile document.
    Includes ReferenceCard, AssetTable, and Action Footer.
    """

    dirty_changed = Signal(bool)
    title_changed = Signal(str)
    status_updated = Signal(str)

    def __init__(self, file_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.file_path: Optional[str] = file_path
        self._dirty: bool = False
        self.created_files: List[str] = []
        self.raw_template_content: str = ""
        self.process_data: Dict = get_default_file()['process'].copy()
        self.replacements_data: Dict = {}

        self._build_ui()
        self._connect_signals()

        if self.file_path and os.path.isfile(self.file_path):
            self.load_file(self.file_path)
        else:
            self._apply_default_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # 1. Top Reference Card
        self.reference_card = ReferenceCardWidget(self)
        root.addWidget(self.reference_card)

        # 2. Center Asset Table
        self.asset_table = AssetTableWidget(self)
        root.addWidget(self.asset_table, 1)

        # 3. Bottom Action Footer
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: #1C1C1C;
                border: 1px solid #363639;
                border-radius: 4px;
            }
        """)
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(8, 6, 8, 6)
        footer_layout.setSpacing(6)

        # Output options row
        opt_row = QHBoxLayout()
        opt_row.setSpacing(8)

        self.same_folder_cb = QCheckBox("Output to same folder as batch")
        self.same_folder_cb.setChecked(True)
        self.same_folder_cb.toggled.connect(self._on_output_toggled)
        opt_row.addWidget(self.same_folder_cb)

        self.custom_output_edit = QLineEdit()
        self.custom_output_edit.setPlaceholderText("Custom output directory relative to addon...")
        self.custom_output_edit.setEnabled(False)
        self.custom_output_edit.textChanged.connect(self._mark_dirty)
        opt_row.addWidget(self.custom_output_edit, 1)

        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.setStyleSheet(qt_stylesheet_button)
        self.browse_output_btn.setEnabled(False)
        self.browse_output_btn.clicked.connect(self._on_browse_output)
        opt_row.addWidget(self.browse_output_btn)

        footer_layout.addLayout(opt_row)

        # Actions and Status row
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.status_label = QLabel("No assets loaded")
        self.status_label.setStyleSheet("color: #9D9D9D; font: 580 9pt 'Segoe UI';")
        action_row.addWidget(self.status_label, 1)

        self.revert_btn = QPushButton("Revert Batch")
        self.revert_btn.setStyleSheet(qt_stylesheet_button)
        self.revert_btn.setEnabled(False)
        self.revert_btn.setToolTip("Delete files created by the last batch process")
        self.revert_btn.clicked.connect(self.revert_created_files)
        action_row.addWidget(self.revert_btn)

        self.process_btn = QPushButton("Process Batch")
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A78C4;
                color: #FFFFFF;
                border: 1px solid #4C8BE2;
                border-radius: 3px;
                padding: 4px 14px;
                font: 600 10pt "Segoe UI";
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #4C8BE2;
            }
            QPushButton:pressed {
                background-color: #2D62A3;
            }
            QPushButton:disabled {
                background-color: #26262B;
                color: #606060;
                border: 1px solid #363639;
            }
        """)
        self.process_btn.clicked.connect(self.process_all)
        action_row.addWidget(self.process_btn)

        footer_layout.addLayout(action_row)
        root.addWidget(footer_frame)

    def _connect_signals(self):
        self.reference_card.reference_changed.connect(self._on_reference_changed)
        self.reference_card.ignore_settings_changed.connect(self._on_ignore_settings_changed)
        self.reference_card.analysis_updated.connect(self._on_analysis_updated)
        self.asset_table.files_dropped.connect(self._on_files_dropped)

    def _apply_default_data(self):
        default = get_default_file()
        self.process_data = default['process'].copy()
        self.reference_card.set_ignore_extensions(self.process_data.get('ignore_extensions', ''))
        self.reference_card.set_ignore_list(self.process_data.get('ignore_list', ''))
        self.refresh_matching()

    def _on_reference_changed(self, text: str):
        self.process_data['reference'] = text
        self._mark_dirty()
        self.refresh_matching()

    def _on_ignore_settings_changed(self):
        self.process_data['ignore_extensions'] = self.reference_card.get_ignore_extensions()
        self.process_data['ignore_list'] = self.reference_card.get_ignore_list()
        self._mark_dirty()
        self.refresh_matching()

    def _on_analysis_updated(self, analysis):
        if analysis:
            self.process_data['extension'] = analysis.asset_type
            self.raw_template_content = analysis.template_content
            self.replacements_data = analysis.replacements
        self.refresh_matching()

    def _on_output_toggled(self, checked: bool):
        self.same_folder_cb.setChecked(checked)
        self.custom_output_edit.setEnabled(not checked)
        self.browse_output_btn.setEnabled(not checked)
        self.process_data['output_to_the_folder'] = checked
        self._mark_dirty()

    def _on_browse_output(self):
        addon_dir = get_addon_dir() or ""
        chosen = QFileDialog.getExistingDirectory(self, "Select Output Directory", addon_dir)
        if chosen:
            if addon_dir:
                try:
                    rel = os.path.relpath(chosen, addon_dir).replace('\\', '/')
                except ValueError:
                    rel = chosen
            else:
                rel = chosen
            self.custom_output_edit.setText(rel)
            self.process_data['custom_output'] = rel
            self._mark_dirty()

    def _on_files_dropped(self, paths: List[str]):
        # Add dropped files/folders to custom files or refresh
        for path in paths:
            if os.path.isdir(path):
                # Set target directory
                self.file_path = os.path.join(path, f"{os.path.basename(path)}.hbat")
                self.title_changed.emit(os.path.basename(self.file_path))
                self.refresh_matching()
                self._mark_dirty()
                return

        # If individual files dropped:
        custom_files = self.process_data.setdefault('custom_files', [])
        for p in paths:
            if os.path.isfile(p) and p not in custom_files:
                custom_files.append(p)
        self.process_data['load_from_the_folder'] = False
        self._mark_dirty()
        self.refresh_matching()

    def refresh_matching(self):
        """Scans the target directory or custom files and updates the asset table."""
        slots_def = {}
        analysis = self.reference_card.current_analysis
        if analysis and analysis.slots:
            slots_def = analysis.slots
        elif 'mesh' not in slots_def:
            slots_def = {'mesh': {'required': True, 'label': 'Render Mesh'}}

        target_dir = ""
        if self.file_path:
            target_dir = os.path.splitext(self.file_path)[0]
            if not os.path.isdir(target_dir):
                target_dir = os.path.dirname(self.file_path)

        if not target_dir and get_addon_dir():
            target_dir = get_addon_dir()

        ext = self.process_data.get('extension', 'vmdl')
        ignore_exts = self.reference_card.get_ignore_extensions()
        ignore_list = self.reference_card.get_ignore_list()

        items = match_folder_assets(
            directory=target_dir,
            slots=slots_def,
            extension=ext,
            ignore_extensions_str=ignore_exts,
            ignore_list_str=ignore_list,
            algorithm=int(self.process_data.get('algorithm', 0))
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
        """Loads .hbat JSON file into this tab."""
        try:
            self.file_path = os.path.normpath(file_path)
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.process_data = data.get('process', {})
            self.replacements_data = data.get('replacements', {})
            self.raw_template_content = data.get('file', {}).get('content', '')

            # Populate reference card
            ref_path = self.process_data.get('reference', '')
            self.reference_card.set_reference_path(ref_path)
            self.reference_card.set_ignore_extensions(
                self.process_data.get('ignore_extensions', get_default_file()['process']['ignore_extensions']))
            self.reference_card.set_ignore_list(self.process_data.get('ignore_list', ''))

            # Output settings
            output_to_folder = self.process_data.get('output_to_the_folder', True)
            self.same_folder_cb.setChecked(output_to_folder)
            self.custom_output_edit.setText(self.process_data.get('custom_output', ''))

            self._dirty = False
            self.title_changed.emit(os.path.basename(self.file_path))
            self.refresh_matching()
            debug(f"[EditorTab] Loaded file: {self.file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load batch file:\n{e}")

    def save_file(self, path: Optional[str] = None):
        """Saves current state to .hbat file."""
        target_path = path or self.file_path
        if not target_path:
            addon_dir = get_addon_dir() or ""
            target_path, _ = QFileDialog.getSaveFileName(
                self, "Save Batch Profile", addon_dir, "Hammer Batch (*.hbat)"
            )
            if not target_path:
                return False
            self.file_path = target_path

        self.process_data['reference'] = self.reference_card.get_reference_path()
        self.process_data['ignore_extensions'] = self.reference_card.get_ignore_extensions()
        self.process_data['ignore_list'] = self.reference_card.get_ignore_list()
        self.process_data['output_to_the_folder'] = self.same_folder_cb.isChecked()
        self.process_data['custom_output'] = self.custom_output_edit.text()

        # If template content is empty, generate it from reference analysis
        if not self.raw_template_content and self.reference_card.current_analysis:
            self.raw_template_content = self.reference_card.current_analysis.template_content
            self.replacements_data = self.reference_card.current_analysis.replacements

        payload = {
            'version': 2,
            'process': self.process_data,
            'replacements': self.replacements_data,
            'file': {'content': self.raw_template_content}
        }

        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4)
            self._dirty = False
            self.dirty_changed.emit(False)
            self.title_changed.emit(os.path.basename(self.file_path))
            debug(f"[EditorTab] Saved file: {self.file_path}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{e}")
            return False

    def process_all(self):
        """Executes batch creation on disk."""
        if not self.file_path:
            if not self.save_file():
                return

        self.save_file()
        created = perform_batch_processing(
            file_path=self.file_path,
            process=self.process_data,
            preview=False,
            replacements=self.replacements_data,
            content_template=self.raw_template_content
        )

        if created:
            self.created_files.extend(created)
            self.revert_btn.setEnabled(True)
            self.status_updated.emit(f"Created {len(created)} assets successfully.")
            QMessageBox.information(
                self, "Batch Complete", f"Successfully created {len(created)} asset file(s)!"
            )
        else:
            QMessageBox.warning(
                self, "Batch Warning", "No assets were created. Check reference template and input files."
            )

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
