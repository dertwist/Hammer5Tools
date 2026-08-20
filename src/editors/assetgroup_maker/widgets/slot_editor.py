import os
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFileDialog, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

from src.settings.main import get_addon_dir
from src.styles.common import (
    qt_stylesheet_button, qt_stylesheet_combobox, qt_stylesheet_lineedit, apply_stylesheets
)
from src.editors.assetgroup_maker.matcher import AssetGroupItem


class SlotAssignmentDialog(QDialog):
    """
    Dialog to inspect and customize which companion files (render mesh, physics mesh,
    materials, LODs) are assigned to specific fields for an asset.
    """

    def __init__(self, item: AssetGroupItem, slots_def: Dict[str, Dict], parent=None):
        super().__init__(parent)
        self.item = item
        self.slots_def = slots_def
        self.assigned_slots: Dict[str, str] = item.slots.copy()
        self.combos: Dict[str, QComboBox] = {}

        self.setWindowTitle(f"Edit Slot Mappings — {item.name}")
        self.setMinimumWidth(540)
        self._build_ui()
        apply_stylesheets(self)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # 1. Header Card: Asset details
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2E2E2E;
                border: 1px solid #464649;
                border-radius: 0px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setSpacing(4)

        title_lbl = QLabel(f"<b>Asset:</b> {self.item.name}")
        title_lbl.setStyleSheet("font: 600 10pt 'Segoe UI'; color: #E5E5E5;")
        header_layout.addWidget(title_lbl)

        out_lbl = QLabel(f"<b>Target Output:</b> {self.item.target_output}")
        out_lbl.setStyleSheet("font: 580 9pt 'Segoe UI'; color: #A5A5A5;")
        header_layout.addWidget(out_lbl)

        if self.item.relative_folder:
            folder_lbl = QLabel(f"<b>Directory:</b> {self.item.relative_folder}")
            folder_lbl.setStyleSheet("font: 580 9pt 'Segoe UI'; color: #A5A5A5;")
            header_layout.addWidget(folder_lbl)

        root_layout.addWidget(header_frame)

        # 2. Slot Fields List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        fields_container = QWidget()
        fields_layout = QVBoxLayout(fields_container)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(8)

        # Ensure primary slots exist even if not explicitly analyzed
        active_slots_def = self.slots_def.copy()
        if 'mesh' not in active_slots_def:
            active_slots_def['mesh'] = {'label': 'Render Mesh (LOD0)', 'required': True}
        if 'collision' not in active_slots_def:
            active_slots_def['collision'] = {'label': 'Collision Hull (Physics)', 'required': False}

        for slot_key, slot_info in active_slots_def.items():
            slot_row = self._create_slot_field_row(slot_key, slot_info)
            fields_layout.addWidget(slot_row)

        fields_layout.addStretch(1)
        scroll.setWidget(fields_container)
        root_layout.addWidget(scroll, 1)

        # 3. Bottom Action Buttons (Cancel / Apply)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(qt_stylesheet_button)
        cancel_btn.setFixedHeight(24)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply Mappings")
        apply_btn.setStyleSheet(qt_stylesheet_button)
        apply_btn.setFixedHeight(24)
        apply_btn.clicked.connect(self._apply_and_close)
        btn_row.addWidget(apply_btn)

        root_layout.addLayout(btn_row)

    def _create_slot_field_row(self, slot_key: str, slot_info: Dict) -> QWidget:
        row_frame = QFrame()
        row_frame.setStyleSheet("""
            QFrame {
                background-color: #272727;
                border: 1px solid #464649;
                border-radius: 0px;
            }
        """)
        row_layout = QVBoxLayout(row_frame)
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(4)

        # Label row
        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(6)

        slot_name = slot_info.get('label', slot_key)
        is_req = slot_info.get('required', False)
        title_text = f"{slot_name}" + (" <span style='color: #EF5350;'>(Required)</span>" if is_req else " <span style='color: #81C784;'>(Optional)</span>")
        lbl = QLabel(title_text)
        lbl.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #E5E5E5;")
        lbl_row.addWidget(lbl)
        lbl_row.addStretch(1)
        row_layout.addLayout(lbl_row)

        # Input & browse row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(4)

        combo = QComboBox()
        combo.setStyleSheet(qt_stylesheet_combobox)
        combo.setFixedHeight(24)

        # Populate candidates
        current_val = self.assigned_slots.get(slot_key, "")
        combo.addItem("(None / Clear)", "")

        candidates = self._get_candidates_for_slot(slot_key)
        selected_idx = 0
        for idx, cand_path in enumerate(candidates, start=1):
            fname = os.path.basename(cand_path)
            combo.addItem(fname, cand_path)
            if current_val and os.path.normpath(current_val).lower() == os.path.normpath(cand_path).lower():
                selected_idx = idx

        # If current_val is not in candidates list, add it
        if current_val and selected_idx == 0:
            fname = os.path.basename(current_val)
            combo.addItem(f"{fname} (Custom)", current_val)
            selected_idx = combo.count() - 1

        combo.setCurrentIndex(selected_idx)
        self.combos[slot_key] = combo
        ctrl_row.addWidget(combo, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.setIcon(QIcon(":/valve_common/icons/tools/common/open.png"))
        browse_btn.setStyleSheet(qt_stylesheet_button)
        browse_btn.setFixedHeight(24)
        browse_btn.clicked.connect(lambda _, key=slot_key: self._browse_custom_file(key))
        ctrl_row.addWidget(browse_btn)

        row_layout.addLayout(ctrl_row)
        return row_frame

    def _get_candidates_for_slot(self, slot_key: str) -> List[str]:
        """Gathers suitable candidate files for a slot."""
        candidates = []
        for cand in self.item.available_candidates:
            fname = os.path.basename(cand)
            _, ext = os.path.splitext(fname)
            ext = ext.lower()

            if slot_key in ('mesh', 'collision', 'lod1', 'lod2', 'lod3'):
                if ext in ('.fbx', '.obj', '.dmx'):
                    candidates.append(cand)
            elif slot_key in ('material', 'color', 'normal', 'roughness', 'ao'):
                if ext in ('.vmat', '.tga', '.png', '.jpg', '.exr', '.psd'):
                    candidates.append(cand)
            else:
                candidates.append(cand)

        return candidates

    def _browse_custom_file(self, slot_key: str):
        addon_dir = get_addon_dir() or ""
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            f"Select Companion File for {slot_key}",
            addon_dir,
            "Supported 3D/Material Files (*.fbx *.obj *.dmx *.vmat *.tga *.png);;All Files (*.*)"
        )
        if chosen:
            combo = self.combos.get(slot_key)
            if combo:
                fname = os.path.basename(chosen)
                combo.addItem(f"{fname} (External)", chosen)
                combo.setCurrentIndex(combo.count() - 1)

    def _apply_and_close(self):
        for slot_key, combo in self.combos.items():
            val = combo.currentData()
            if val:
                self.assigned_slots[slot_key] = val
            elif slot_key in self.assigned_slots:
                del self.assigned_slots[slot_key]

        self.accept()
