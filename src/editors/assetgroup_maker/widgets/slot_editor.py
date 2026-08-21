import os
from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QCheckBox, QFrame, QScrollArea, QToolButton, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

from src.settings.main import get_addon_dir, get_addon_name, debug
from src.styles.common import (
    qt_stylesheet_button, qt_stylesheet_combobox, qt_stylesheet_lineedit,
    qt_stylesheet_checkbox, apply_stylesheets
)
from src.editors.assetgroup_maker.analyzer import (
    ReferenceAnalysisResult, extract_fbx_materials, resolve_reference_full_path
)


class TemplateSlotMappingDialog(QDialog):
    """
    Dialog to configure slot mappings and material remap slots for a Template:
    - View and customize slot tokens
    - Enable / Skip slot mappings (e.g. skip collision mesh or skip roughness map)
    - Research embedded FBX materials and swap target .vmat paths with interactive Asset Browser picker
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

        # Load material remaps from template_data or analysis
        self.material_remaps: List[Dict[str, str]] = []
        raw_remaps = template_data.get('material_remaps')
        if raw_remaps is not None:
            self.material_remaps = [dict(r) for r in raw_remaps if isinstance(r, dict)]
        elif analysis and getattr(analysis, 'material_remaps', None):
            self.material_remaps = [dict(r) for r in analysis.material_remaps]

        self.slot_check_boxes: Dict[str, QCheckBox] = {}
        self.token_edits: Dict[str, QLineEdit] = {}
        self.mat_remap_widgets: List[Dict[str, Any]] = []

        ext = template_data.get('extension', 'vmdl').upper()
        ref = template_data.get('reference', '')
        ref_name = os.path.basename(ref) if ref else "Untitled"

        self.setWindowTitle(f"Template Slot Mappings — {ref_name} ({ext})")
        self.setWindowIcon(QIcon(":/icons/appicon.ico"))
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinMaxButtonsHint
            | Qt.WindowCloseButtonHint
        )
        self.setSizeGripEnabled(True)
        self.setMinimumSize(700, 420)
        self.resize(880, 580)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #E5E5E5;
            }
        """)
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
                background-color: #262626;
                border: 1px solid #3E3E42;
                border-radius: 2px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(4)

        ref_path = self.template_data.get('reference', '')
        ref_lbl = QLabel(f"<b>Template Reference:</b> <span style='font-weight: normal; color: #E5E5E5;'>{ref_path if ref_path else '(None selected)'}</span>")
        ref_lbl.setStyleSheet("font: 600 9.5pt 'Segoe UI'; color: #FFFFFF;")
        header_layout.addWidget(ref_lbl)

        root_layout.addWidget(header_frame)

        # 2. Main Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.fields_container = QWidget()
        self.fields_container.setStyleSheet("background: transparent;")
        self.fields_layout = QVBoxLayout(self.fields_container)
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(10)

        # Determine active slots definition (excluding individual material remaps which have their own dedicated section)
        slots_def = {}
        if self.analysis and self.analysis.slots:
            for k, v in self.analysis.slots.items():
                if not v.get('is_material_remap', False):
                    slots_def[k] = v
        else:
            ext = self.template_data.get('extension', 'vmdl').lower()
            if ext == 'vmdl':
                slots_def = {
                    'mesh': {'label': 'Render Mesh (LOD0)', 'required': True, 'token': '#$MESH$#'},
                    'collision': {'label': 'Collision Hull (Physics)', 'required': False, 'token': '#$COLLISION$#'},
                    'lod1': {'label': 'LOD 1 Mesh', 'required': False, 'token': '#$LOD1$#'},
                    'lod2': {'label': 'LOD 2 Mesh', 'required': False, 'token': '#$LOD2$#'},
                    'lod3': {'label': 'LOD 3 Mesh', 'required': False, 'token': '#$LOD3$#'},
                }
            elif ext == 'vmat':
                slots_def = {
                    'color': {'label': 'Color Map', 'required': True, 'token': '#$COLOR$#'},
                    'normal': {'label': 'Normal Map', 'required': False, 'token': '#$NORMAL$#'},
                    'roughness': {'label': 'Roughness Map', 'required': False, 'token': '#$ROUGHNESS$#'},
                    'metalness': {'label': 'Metalness Map', 'required': False, 'token': '#$METALNESS$#'},
                    'ao': {'label': 'Ambient Occlusion Map', 'required': False, 'token': '#$AO$#'},
                    'orm': {'label': 'ORM Map', 'required': False, 'token': '#$ORM$#'},
                    'height': {'label': 'Height Map', 'required': False, 'token': '#$HEIGHT$#'},
                    'emissive': {'label': 'Emissive Map', 'required': False, 'token': '#$EMISSIVE$#'},
                    'tintmask': {'label': 'Tint Mask', 'required': False, 'token': '#$TINTMASK$#'},
                    'opacity': {'label': 'Opacity Map', 'required': False, 'token': '#$OPACITY$#'},
                }
            elif ext == 'vsndevts':
                slots_def = {
                    'sound': {'label': 'Audio File', 'required': True, 'token': '#$SOUND$#'}
                }
            else:
                slots_def = {
                    'model': {'label': 'Primary Model', 'required': True, 'token': '#$MODEL$#'}
                }

        # Standard Slot Rows Section
        slots_header_lbl = QLabel("Companion File Slots & Replacement Tokens:")
        slots_header_lbl.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #A5A5A5;")
        self.fields_layout.addWidget(slots_header_lbl)

        for slot_key, slot_info in slots_def.items():
            row_frame = self._create_slot_row(slot_key, slot_info)
            self.fields_layout.addWidget(row_frame)

        # Material Remap Section (For VMDL or templates with material remaps)
        ext = self.template_data.get('extension', 'vmdl').lower()
        if ext == 'vmdl' or bool(self.material_remaps):
            self._build_material_remaps_section()

        self.fields_layout.addStretch(1)
        scroll.setWidget(self.fields_container)
        root_layout.addWidget(scroll, 1)

        # 3. Bottom Action Buttons (Cancel / Save Mappings)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(qt_stylesheet_button)
        cancel_btn.setFixedHeight(28)
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton("Save Slot Mappings")
        apply_btn.setIcon(QIcon(":/valve_common/icons/tools/common/save.png"))
        apply_btn.setStyleSheet(qt_stylesheet_button)
        apply_btn.setFixedHeight(28)
        apply_btn.setMinimumWidth(140)
        apply_btn.clicked.connect(self._apply_and_close)
        btn_row.addWidget(apply_btn)

        root_layout.addLayout(btn_row)

    def _create_slot_row(self, slot_key: str, slot_info: Dict[str, Any]) -> QWidget:
        row_frame = QFrame()
        row_frame.setStyleSheet("""
            QFrame {
                background-color: #252527;
                border: 1px solid #3E3E42;
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
        badge_bg = "#1F2E40" if is_req else "#2A2A2E"
        badge_border = "#4A83C9" if is_req else "#4E4E52"
        badge_color = "#4A83C9" if is_req else "#8E8E93"
        badge_text = "REQUIRED" if is_req else "OPTIONAL"

        title_lbl = QLabel(f"<b>{slot_label}</b> ({slot_key})")
        title_lbl.setStyleSheet("font: 600 9.5pt 'Segoe UI'; color: #E5E5E5;")
        top_row.addWidget(title_lbl)

        badge_lbl = QLabel(badge_text)
        badge_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: {badge_color};
                border: 1px solid {badge_border};
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

    def _build_material_remaps_section(self):
        mat_section_frame = QFrame()
        mat_section_frame.setStyleSheet("""
            QFrame {
                background-color: #252527;
                border: 1px solid #3E3E42;
                border-radius: 2px;
            }
        """)
        mat_section_layout = QVBoxLayout(mat_section_frame)
        mat_section_layout.setContentsMargins(10, 8, 10, 8)
        mat_section_layout.setSpacing(8)

        # Section Header with Action Buttons
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon(":/valve_common/icons/tools/common/browse.png").pixmap(16, 16))
        header_row.addWidget(icon_lbl)

        title_lbl = QLabel("<b>FBX Materials & Material Slot Remaps (VMDL MaterialGroup):</b>")
        title_lbl.setStyleSheet("font: 600 9.5pt 'Segoe UI'; color: #E5E5E5;")
        header_row.addWidget(title_lbl)

        header_row.addStretch(1)

        research_btn = QPushButton("Research FBX Materials")
        research_btn.setIcon(QIcon(":/valve_common/icons/tools/common/refresh.png"))
        research_btn.setToolTip("Scan FBX mesh files to extract embedded material names")
        research_btn.setStyleSheet(qt_stylesheet_button)
        research_btn.setFixedHeight(26)
        research_btn.clicked.connect(self._research_fbx_materials)
        header_row.addWidget(research_btn)

        add_remap_btn = QPushButton("+ Add Remap")
        add_remap_btn.setIcon(QIcon(":/valve_common/icons/tools/common/new.png"))
        add_remap_btn.setToolTip("Add a new FBX material slot remap")
        add_remap_btn.setStyleSheet(qt_stylesheet_button)
        add_remap_btn.setFixedHeight(26)
        add_remap_btn.clicked.connect(lambda: self._add_material_remap_row("", ""))
        header_row.addWidget(add_remap_btn)

        mat_section_layout.addLayout(header_row)

        desc_lbl = QLabel("Extracts embedded FBX material names and allows swapping the target .vmat material asset path.")
        desc_lbl.setStyleSheet("font: 580 8.5pt 'Segoe UI'; color: #8A8A8A;")
        mat_section_layout.addWidget(desc_lbl)

        # Container for remap rows
        self.remaps_container = QWidget()
        self.remaps_layout = QVBoxLayout(self.remaps_container)
        self.remaps_layout.setContentsMargins(0, 4, 0, 0)
        self.remaps_layout.setSpacing(6)

        mat_section_layout.addWidget(self.remaps_container)

        self.fields_layout.addWidget(mat_section_frame)

        # Populate rows
        if self.material_remaps:
            for remap in self.material_remaps:
                self._add_material_remap_row(remap.get('from', ''), remap.get('to', ''))
        else:
            # Auto research if empty
            self._research_fbx_materials(silent=True)

    def _add_material_remap_row(self, from_mat: str, to_mat: str):
        row_frame = QFrame()
        row_frame.setStyleSheet("""
            QFrame {
                background-color: #2F2F32;
                border: 1px solid #3E3E42;
                border-radius: 2px;
            }
        """)
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(8)

        from_label = QLabel("From (FBX):")
        from_label.setFixedWidth(70)
        from_label.setStyleSheet("color: #A5A5A5; font: 600 8.5pt 'Segoe UI';")
        row_layout.addWidget(from_label)

        from_edit = QLineEdit(from_mat)
        from_edit.setStyleSheet(qt_stylesheet_lineedit)
        from_edit.setFixedHeight(24)
        from_edit.setPlaceholderText("material_name.vmat")
        from_edit.setMinimumWidth(130)
        row_layout.addWidget(from_edit, 1)

        arrow_lbl = QLabel("➔")
        arrow_lbl.setStyleSheet("color: #4A83C9; font: 700 10pt 'Segoe UI';")
        row_layout.addWidget(arrow_lbl)

        to_label = QLabel("To (.vmat):")
        to_label.setFixedWidth(65)
        to_label.setStyleSheet("color: #A5A5A5; font: 600 8.5pt 'Segoe UI';")
        row_layout.addWidget(to_label)

        to_edit = QLineEdit(to_mat)
        to_edit.setStyleSheet(qt_stylesheet_lineedit)
        to_edit.setFixedHeight(24)
        to_edit.setPlaceholderText("materials/.../material.vmat")
        row_layout.addWidget(to_edit, 2)

        # Asset Browser Button (Only .vmat)
        browse_btn = QPushButton()
        browse_btn.setIcon(QIcon(":/valve_common/icons/tools/common/browse.png"))
        browse_btn.setToolTip("Pick .vmat material using Asset Browser")
        browse_btn.setStyleSheet(qt_stylesheet_button)
        browse_btn.setFixedSize(26, 24)
        browse_btn.clicked.connect(lambda: self._on_browse_vmat(to_edit))
        row_layout.addWidget(browse_btn)

        # Delete Remap Button
        del_btn = QToolButton()
        del_btn.setText("✕")
        del_btn.setToolTip("Remove this material remap")
        del_btn.setStyleSheet("""
            QToolButton {
                color: #A5A5A5;
                background: transparent;
                border: none;
                font: 700 9pt 'Segoe UI';
                padding: 2px 4px;
            }
            QToolButton:hover {
                color: #EF5350;
                background-color: #3E2020;
                border-radius: 2px;
            }
        """)
        row_entry = {
            'frame': row_frame,
            'from_edit': from_edit,
            'to_edit': to_edit
        }
        self.mat_remap_widgets.append(row_entry)

        del_btn.clicked.connect(lambda: self._remove_material_remap_row(row_entry))
        row_layout.addWidget(del_btn)

        self.remaps_layout.addWidget(row_frame)

    def _remove_material_remap_row(self, row_entry: Dict[str, Any]):
        if row_entry in self.mat_remap_widgets:
            self.mat_remap_widgets.remove(row_entry)
        frame = row_entry.get('frame')
        if frame:
            self.remaps_layout.removeWidget(frame)
            frame.deleteLater()

    def _on_browse_vmat(self, target_edit: QLineEdit):
        from src.widgets.model_browser import pick_asset
        result = pick_asset(
            self,
            current_path=target_edit.text().strip(),
            addon=get_addon_name(),
            addon_only=False,
            asset_types=[".vmat"],
            title="Select Material (.vmat)"
        )
        if result:
            target_edit.setText(result)

    def _research_fbx_materials(self, silent: bool = False):
        """Scans the template's referenced FBX mesh files and extracts all embedded materials."""
        ref_path = self.template_data.get('reference', '')
        context_folder = None
        main_win = self.window()
        if hasattr(main_win, 'file_path') and main_win.file_path:
            context_folder = os.path.dirname(main_win.file_path)

        # Collect mesh candidates from analysis or slots
        mesh_paths = []
        if self.analysis and self.analysis.slots:
            for s_info in self.analysis.slots.values():
                s_source = s_info.get('source', '')
                if s_source and s_source.lower().endswith('.fbx'):
                    mesh_paths.append(s_source)

        if not mesh_paths and ref_path:
            ref_full = resolve_reference_full_path(ref_path, context_folder=context_folder)
            if ref_full and os.path.isfile(ref_full):
                try:
                    with open(ref_full, 'r', encoding='utf-8', errors='replace') as f:
                        txt = f.read()
                    import re
                    found = re.findall(r'filename\s*=\s*["\']([^"\']+\.fbx)["\']', txt, re.IGNORECASE)
                    mesh_paths.extend(found)
                except Exception:
                    pass

        # If reference itself is an FBX
        if ref_path and ref_path.lower().endswith('.fbx'):
            mesh_paths.append(ref_path)

        existing_froms = {r['from_edit'].text().strip().lower() for r in self.mat_remap_widgets if r.get('from_edit')}
        new_found = 0

        for m_path in mesh_paths:
            m_full = resolve_reference_full_path(m_path, context_folder=context_folder)
            if m_full and os.path.isfile(m_full):
                fbx_mats = extract_fbx_materials(m_full)
                for f_mat in fbx_mats:
                    f_vmat = f_mat if f_mat.lower().endswith('.vmat') else f"{f_mat}.vmat"
                    if f_vmat.lower() not in existing_froms and f_mat.lower() not in existing_froms:
                        existing_froms.add(f_vmat.lower())
                        self._add_material_remap_row(f_vmat, "")
                        new_found += 1

        if not silent:
            if new_found > 0:
                QMessageBox.information(self, "FBX Materials Researched", f"Discovered {new_found} new material slot(s) from FBX mesh files.")
            else:
                QMessageBox.information(self, "FBX Materials Researched", "No new FBX materials found in referenced meshes.")

    def _apply_and_close(self):
        self.skipped_slots.clear()
        self.custom_tokens.clear()
        self.material_remaps.clear()

        for slot_key, cb in self.slot_check_boxes.items():
            if not cb.isChecked():
                self.skipped_slots.append(slot_key)

        for slot_key, edit in self.token_edits.items():
            tok_text = edit.text().strip()
            if tok_text:
                self.custom_tokens[slot_key] = tok_text

        for row in self.mat_remap_widgets:
            from_text = row['from_edit'].text().strip()
            to_text = row['to_edit'].text().strip()
            if from_text:
                self.material_remaps.append({'from': from_text, 'to': to_text})

        self.accept()


# Backward compatibility alias
SlotAssignmentDialog = TemplateSlotMappingDialog
