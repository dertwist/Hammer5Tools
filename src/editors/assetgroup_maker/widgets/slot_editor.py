import os
from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QCheckBox, QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from src.settings.main import get_addon_dir
from src.styles.common import (
    qt_stylesheet_button, qt_stylesheet_combobox, qt_stylesheet_lineedit,
    qt_stylesheet_checkbox, apply_stylesheets
)
from src.editors.assetgroup_maker.analyzer import ReferenceAnalysisResult


class TemplateSlotMappingDialog(QDialog):
    """
    Dialog to configure slot mappings for a Template:
    - View and customize slot tokens
    - Enable / Skip slot mappings (e.g. skip collision mesh or skip roughness map)
    - Configure fallbacks
    """

    def __init__(
        self,
        template_data: Dict[str, Any],
        analysis: Optional[ReferenceAnalysisResult] = None,
        parent=None
    ):
        super().__init__(parent)
        self.template_data = template_data
        self.analysis = analysis
        self.skipped_slots: List[str] = list(template_data.get('skipped_slots', []))
        self.custom_tokens: Dict[str, str] = dict(template_data.get('custom_tokens', {}))
        self.slot_check_boxes: Dict[str, QCheckBox] = {}
        self.token_edits: Dict[str, QLineEdit] = {}

        ext = template_data.get('extension', 'vmdl').upper()
        ref = template_data.get('reference', '')
        ref_name = os.path.basename(ref) if ref else "Untitled"

        self.setWindowTitle(f"Template Slot Mappings — {ref_name} ({ext})")
        self.setMinimumWidth(560)
        self._build_ui()
        apply_stylesheets(self)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # 1. Header Frame: Template Info
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2E2E2E;
                border: 1px solid #464649;
                border-radius: 2px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(4)

        ref_path = self.template_data.get('reference', '')
        ref_lbl = QLabel(f"<b>Template Reference:</b> {ref_path if ref_path else '(None selected)'}")
        ref_lbl.setStyleSheet("font: 600 9.5pt 'Segoe UI'; color: #E5E5E5;")
        header_layout.addWidget(ref_lbl)

        desc_lbl = QLabel("Configure which slots to map or skip during batch asset generation.")
        desc_lbl.setStyleSheet("font: 580 8.5pt 'Segoe UI'; color: #A5A5A5;")
        header_layout.addWidget(desc_lbl)

        root_layout.addWidget(header_frame)

        # 2. Slots Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        fields_container = QWidget()
        fields_layout = QVBoxLayout(fields_container)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(8)

        # Determine active slots definition
        slots_def = {}
        if self.analysis and self.analysis.slots:
            slots_def = self.analysis.slots.copy()
        else:
            ext = self.template_data.get('extension', 'vmdl').lower()
            if ext == 'vmdl':
                slots_def = {
                    'mesh': {'label': 'Render Mesh (LOD0)', 'required': True, 'token': '#$MESH$#'},
                    'collision': {'label': 'Collision Hull (Physics)', 'required': False, 'token': '#$COLLISION$#'},
                    'lod1': {'label': 'LOD 1 Mesh', 'required': False, 'token': '#$LOD1$#'}
                }
            elif ext == 'vmat':
                slots_def = {
                    'color': {'label': 'Color / Albedo Map', 'required': True, 'token': '#$COLOR$#'},
                    'normal': {'label': 'Normal Map', 'required': False, 'token': '#$NORMAL$#'},
                    'roughness': {'label': 'Roughness Map', 'required': False, 'token': '#$ROUGHNESS$#'},
                    'metalness': {'label': 'Metalness Map', 'required': False, 'token': '#$METALNESS$#'},
                    'ao': {'label': 'Ambient Occlusion Map', 'required': False, 'token': '#$AO$#'},
                    'orm': {'label': 'Packed ORM Map', 'required': False, 'token': '#$ORM$#'},
                    'height': {'label': 'Height / Displacement', 'required': False, 'token': '#$HEIGHT$#'},
                    'emissive': {'label': 'Emissive / Self-Illum', 'required': False, 'token': '#$EMISSIVE$#'},
                }
            else:
                slots_def = {
                    'model': {'label': 'Primary Model', 'required': True, 'token': '#$MODEL$#'}
                }

        for slot_key, slot_info in slots_def.items():
            row_frame = self._create_slot_row(slot_key, slot_info)
            fields_layout.addWidget(row_frame)

        fields_layout.addStretch(1)
        scroll.setWidget(fields_container)
        root_layout.addWidget(scroll, 1)

        # 3. Bottom Action Buttons (Cancel / Save Mappings)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(qt_stylesheet_button)
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton("Save Slot Mappings")
        apply_btn.setIcon(QIcon(":/valve_common/icons/tools/common/save.png"))
        apply_btn.setStyleSheet(qt_stylesheet_button)
        apply_btn.setFixedHeight(28)
        apply_btn.clicked.connect(self._apply_and_close)
        btn_row.addWidget(apply_btn)

        root_layout.addLayout(btn_row)

    def _create_slot_row(self, slot_key: str, slot_info: Dict[str, Any]) -> QWidget:
        row_frame = QFrame()
        row_frame.setStyleSheet("""
            QFrame {
                background-color: #272727;
                border: 1px solid #464649;
                border-radius: 2px;
            }
        """)
        row_layout = QVBoxLayout(row_frame)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(6)

        # Header Row: Checkbox + Slot Name + Required/Optional Badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        is_skipped = slot_key in self.skipped_slots
        cb = QCheckBox("Map this slot")
        cb.setStyleSheet(qt_stylesheet_checkbox)
        cb.setChecked(not is_skipped)
        self.slot_check_boxes[slot_key] = cb
        top_row.addWidget(cb)

        slot_label = slot_info.get('label', slot_key)
        is_req = slot_info.get('required', False)
        badge_color = "#4A83C9" if is_req else "#757575"
        badge_text = "REQUIRED" if is_req else "OPTIONAL"

        title_lbl = QLabel(f"<b>{slot_label}</b> ({slot_key})")
        title_lbl.setStyleSheet("font: 600 9.5pt 'Segoe UI'; color: #E5E5E5;")
        top_row.addWidget(title_lbl)

        badge_lbl = QLabel(badge_text)
        badge_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: #2D333F;
                color: {badge_color};
                border: 1px solid {badge_color};
                border-radius: 0px;
                padding: 1px 5px;
                font: 600 7.5pt 'Segoe UI';
            }}
        """)
        top_row.addWidget(badge_lbl)
        top_row.addStretch(1)

        source_filename = slot_info.get('filename', '')
        if source_filename:
            file_lbl = QLabel(f"Reference File: <span style='color:#E0E0E0;'>{source_filename}</span>")
            file_lbl.setStyleSheet("font: 580 8.5pt 'Segoe UI'; color: #A5A5A5;")
            top_row.addWidget(file_lbl)

        row_layout.addLayout(top_row)

        # Token Row
        token_row = QHBoxLayout()
        token_row.setSpacing(6)

        tok_lbl = QLabel("Replacement Token:")
        tok_lbl.setFixedWidth(130)
        tok_lbl.setStyleSheet("color: #A5A5A5; font: 580 8.5pt 'Segoe UI';")
        token_row.addWidget(tok_lbl)

        default_tok = slot_info.get('token', f'#${slot_key.upper()}$#')
        curr_tok = self.custom_tokens.get(slot_key, default_tok)

        tok_edit = QLineEdit(curr_tok)
        tok_edit.setStyleSheet(qt_stylesheet_lineedit)
        tok_edit.setFixedHeight(24)
        self.token_edits[slot_key] = tok_edit
        token_row.addWidget(tok_edit, 1)

        row_layout.addLayout(token_row)

        # Connect checkbox to enable/disable token edit
        cb.toggled.connect(tok_edit.setEnabled)
        tok_edit.setEnabled(cb.isChecked())

        return row_frame

    def _apply_and_close(self):
        self.skipped_slots.clear()
        self.custom_tokens.clear()

        for slot_key, cb in self.slot_check_boxes.items():
            if not cb.isChecked():
                self.skipped_slots.append(slot_key)

        for slot_key, edit in self.token_edits.items():
            tok_text = edit.text().strip()
            if tok_text:
                self.custom_tokens[slot_key] = tok_text

        self.accept()


# Backward compatibility alias
SlotAssignmentDialog = TemplateSlotMappingDialog
