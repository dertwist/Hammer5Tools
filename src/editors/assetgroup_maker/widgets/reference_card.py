import os
from typing import Optional, Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QFrame, QToolButton, QScrollArea, QComboBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QDropEvent

from src.settings.main import get_addon_dir, debug
from src.editors.assetgroup_maker.analyzer import analyze_reference_file, ReferenceAnalysisResult
from src.styles.common import (
    qt_stylesheet_button, qt_stylesheet_lineedit, qt_stylesheet_combobox, apply_stylesheets
)

try:
    from src.other.cs2_netcon import CS2Netcon
except Exception:
    CS2Netcon = None


class DragDropReferenceLineEdit(QLineEdit):
    """Line edit for reference asset path supporting drag & drop."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Select or drop a reference file (.vmdl, .vsmart, .vmat, .vtex)...")
        self.setStyleSheet(qt_stylesheet_lineedit)

    def dragEnterEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDropEvent):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if os.path.isfile(path):
                    self.file_dropped.emit(path)
                    event.acceptProposedAction()
                    return
        elif mime.hasText():
            text = mime.text().strip().strip('"').strip("'")
            if os.path.isfile(text):
                self.file_dropped.emit(text)
                event.acceptProposedAction()
                return
        event.ignore()


class TemplateCardWidget(QWidget):
    """
    Card representing a single template configuration in a multi-template batch profile.
    """

    template_changed = Signal()
    delete_requested = Signal(object)  # Emits self
    analysis_updated = Signal(str, object)  # template_id, ReferenceAnalysisResult

    def __init__(self, template_id: str = "template_0", parent=None):
        super().__init__(parent)
        self.template_id = template_id
        self.current_analysis: Optional[ReferenceAnalysisResult] = None
        self.replacements: List[Dict[str, str]] = []
        self.skipped_slots: List[str] = []
        self.custom_tokens: Dict[str, str] = {}
        self.material_remaps: List[Dict[str, str]] = []
        self._build_ui()
        self._update_slot_pills()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Main Card Frame
        card_frame = QFrame()
        card_frame.setStyleSheet("""
            QFrame {
                background-color: #2E2E2E;
                border: 1px solid #464649;
                border-radius: 2px;
            }
        """)
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(6)

        # Header Row: Title, Type Badge, Delete Button
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon(":/valve_common/icons/tools/common/browse.png").pixmap(16, 16))
        header_row.addWidget(icon_label)

        self.title_label = QLabel("Template Asset")
        self.title_label.setStyleSheet("font: 600 9.5pt 'Segoe UI'; color: #E5E5E5;")
        header_row.addWidget(self.title_label)

        header_row.addStretch(1)

        self.type_badge = QLabel("ModelDoc (.vmdl)")
        self.type_badge.setStyleSheet("""
            QLabel {
                background-color: #2D333F;
                color: #A0C4FF;
                border: 1px solid #4A83C9;
                border-radius: 0px;
                padding: 2px 6px;
                font: 600 8.5pt 'Segoe UI';
            }
        """)
        self.type_badge.hide()
        header_row.addWidget(self.type_badge)

        self.del_btn = QToolButton()
        self.del_btn.setText("✕")
        self.del_btn.setToolTip("Remove this template from config")
        self.del_btn.setStyleSheet("""
            QToolButton {
                color: #A5A5A5;
                background: transparent;
                border: none;
                font: 700 9pt 'Segoe UI';
                padding: 2px 6px;
            }
            QToolButton:hover {
                color: #EF5350;
                background-color: #3E2020;
                border-radius: 2px;
            }
        """)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        header_row.addWidget(self.del_btn)

        card_layout.addLayout(header_row)

        # File Input Row
        file_row = QHBoxLayout()
        file_row.setSpacing(4)

        self.ref_edit = DragDropReferenceLineEdit()
        self.ref_edit.setFixedHeight(28)
        self.ref_edit.file_dropped.connect(self.set_reference_path)
        self.ref_edit.textChanged.connect(self._on_text_changed)
        file_row.addWidget(self.ref_edit, 1)

        self.asset_browser_btn = QPushButton("Asset Browser...")
        self.asset_browser_btn.setIcon(QIcon(":/valve_common/icons/tools/common/browse.png"))
        self.asset_browser_btn.setToolTip("Pick template asset using interactive Asset Browser")
        self.asset_browser_btn.setStyleSheet(qt_stylesheet_button)
        self.asset_browser_btn.setFixedHeight(28)
        self.asset_browser_btn.clicked.connect(self._on_asset_browser_clicked)
        file_row.addWidget(self.asset_browser_btn)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setIcon(QIcon(":/valve_common/icons/tools/common/open.png"))
        self.browse_btn.setStyleSheet(qt_stylesheet_button)
        self.browse_btn.setFixedHeight(28)
        self.browse_btn.setToolTip("Browse file system for reference template file")
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        file_row.addWidget(self.browse_btn)

        self.open_cs2_btn = QPushButton()
        self.open_cs2_btn.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.open_cs2_btn.setToolTip("Open reference asset in CS2 Tools")
        self.open_cs2_btn.setStyleSheet(qt_stylesheet_button)
        self.open_cs2_btn.setFixedSize(28, 28)
        self.open_cs2_btn.clicked.connect(self._open_in_cs2)
        file_row.addWidget(self.open_cs2_btn)

        card_layout.addLayout(file_row)

        # Slot Badges Container
        self.slots_container = QWidget()
        self.slots_layout = QHBoxLayout(self.slots_container)
        self.slots_layout.setContentsMargins(0, 2, 0, 2)
        self.slots_layout.setSpacing(6)

        slots_title = QLabel("Detected Slots:")
        slots_title.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #A5A5A5;")
        self.slots_layout.addWidget(slots_title)

        self.slot_pills_host = QWidget()
        self.slot_pills_layout = QHBoxLayout(self.slot_pills_host)
        self.slot_pills_layout.setContentsMargins(0, 0, 0, 0)
        self.slot_pills_layout.setSpacing(4)
        self.slots_layout.addWidget(self.slot_pills_host)
        self.slots_layout.addStretch(1)

        self.edit_slots_btn = QPushButton("Edit Slot Mappings...")
        self.edit_slots_btn.setIcon(QIcon(":/valve_common/icons/tools/common/browse.png"))
        self.edit_slots_btn.setToolTip("Configure slot mappings, custom tokens, and skip options for this template")
        self.edit_slots_btn.setStyleSheet(qt_stylesheet_button)
        self.edit_slots_btn.setFixedHeight(24)
        self.edit_slots_btn.clicked.connect(self._open_slot_mappings_dialog)
        self.slots_layout.addWidget(self.edit_slots_btn)

        card_layout.addWidget(self.slots_container)

        # Collapsible Per-Template Filter / Ignore Settings
        self.ignore_toggle_btn = QToolButton()
        self.ignore_toggle_btn.setIcon(QIcon(":/icons/arrow_drop_right.png"))
        self.ignore_toggle_btn.setIconSize(QSize(10, 10))
        self.ignore_toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.ignore_toggle_btn.setText("Template Filter & Ignore Settings (Extensions & Exclusions)")
        self.ignore_toggle_btn.setCheckable(True)
        self.ignore_toggle_btn.setChecked(False)
        self.ignore_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.ignore_toggle_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                color: #A5A5A5;
                font: 600 8.5pt 'Segoe UI';
                padding: 1px 2px;
                margin: 0px;
                height: 16px;
            }
            QToolButton:hover {
                color: #FFFFFF;
            }
        """)
        self.ignore_toggle_btn.toggled.connect(self._toggle_ignore_panel)
        card_layout.addWidget(self.ignore_toggle_btn)

        self.ignore_panel = QFrame()
        self.ignore_panel.setStyleSheet("""
            QFrame {
                background-color: #242424;
                border: 1px solid #3E3E42;
                border-radius: 2px;
            }
        """)
        ignore_layout = QVBoxLayout(self.ignore_panel)
        ignore_layout.setContentsMargins(6, 4, 6, 4)
        ignore_layout.setSpacing(4)

        mode_row = QHBoxLayout()
        mode_label = QLabel("Filter Mode:")
        mode_label.setFixedWidth(120)
        mode_label.setStyleSheet("color: #A5A5A5; font: 580 8.5pt 'Segoe UI';")
        self.filter_mode_combo = QComboBox()
        self.filter_mode_combo.setStyleSheet(qt_stylesheet_combobox)
        self.filter_mode_combo.setFixedHeight(24)
        self.filter_mode_combo.addItems(["Exclude (Blacklist)", "Include (Whitelist)"])
        self.filter_mode_combo.currentTextChanged.connect(self._on_filter_mode_changed)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.filter_mode_combo)
        mode_row.addStretch(1)
        ignore_layout.addLayout(mode_row)

        ext_row = QHBoxLayout()
        self.ext_label = QLabel("Filter Extensions:")
        self.ext_label.setFixedWidth(120)
        self.ext_label.setStyleSheet("color: #A5A5A5; font: 580 8.5pt 'Segoe UI';")
        self.ignore_ext_edit = QLineEdit()
        self.ignore_ext_edit.setStyleSheet(qt_stylesheet_lineedit)
        self.ignore_ext_edit.setFixedHeight(24)
        self.ignore_ext_edit.setPlaceholderText("e.g. mb, blend, phys_, temp_*, tga (comma separated)")
        self.ignore_ext_edit.textChanged.connect(lambda _: self.template_changed.emit())
        ext_row.addWidget(self.ext_label)
        ext_row.addWidget(self.ignore_ext_edit)
        ignore_layout.addLayout(ext_row)

        file_ignore_row = QHBoxLayout()
        file_ignore_label = QLabel("Ignore Files List:")
        file_ignore_label.setFixedWidth(120)
        file_ignore_label.setStyleSheet("color: #A5A5A5; font: 580 8.5pt 'Segoe UI';")
        self.ignore_files_edit = QLineEdit()
        self.ignore_files_edit.setStyleSheet(qt_stylesheet_lineedit)
        self.ignore_files_edit.setFixedHeight(24)
        self.ignore_files_edit.setPlaceholderText("temp_*, draft_*, *backup*")
        self.ignore_files_edit.textChanged.connect(lambda _: self.template_changed.emit())
        file_ignore_row.addWidget(file_ignore_label)
        file_ignore_row.addWidget(self.ignore_files_edit)
        ignore_layout.addLayout(file_ignore_row)

        self.ignore_panel.hide()
        card_layout.addWidget(self.ignore_panel)

        main_layout.addWidget(card_frame)

    def _on_filter_mode_changed(self, mode_text: str):
        if "Include" in mode_text:
            self.ext_label.setText("Include Extensions:")
            self.ignore_ext_edit.setPlaceholderText("e.g. fbx, obj, dmx (comma separated)")
        else:
            self.ext_label.setText("Exclude Extensions:")
            self.ignore_ext_edit.setPlaceholderText("e.g. mb, blend, phys_, temp_*, tga (comma separated)")
        self.template_changed.emit()

    def _toggle_ignore_panel(self, checked: bool):
        icon_path = ":/icons/arrow_drop_down.png" if checked else ":/icons/arrow_drop_right.png"
        self.ignore_toggle_btn.setIcon(QIcon(icon_path))
        self.ignore_panel.setVisible(checked)

    def set_template_title(self, title: str):
        self.title_label.setText(title)

    def set_can_delete(self, can_delete: bool):
        self.del_btn.setVisible(can_delete)

    def get_global_settings(self) -> Dict[str, Any]:
        """Traverse hierarchy to retrieve the active global settings dictionary."""
        p = self.parent()
        while p is not None:
            if hasattr(p, 'get_data') and callable(p.get_data):
                d = p.get_data()
                if isinstance(d, dict) and 'settings' in d:
                    return dict(d.get('settings', {}))
            p = p.parent()
        return {}

    def get_context_folder(self) -> Optional[str]:
        """Resolves the current working/asset directory from parent widgets or settings."""
        p = self.parent()
        while p is not None:
            if hasattr(p, 'get_target_directory') and callable(p.get_target_directory):
                d = p.get_target_directory()
                if d and os.path.isdir(d):
                    return d
            if hasattr(p, 'file_path') and p.file_path:
                target_dir = os.path.splitext(p.file_path)[0]
                if os.path.isdir(target_dir):
                    return target_dir
                d_name = os.path.dirname(p.file_path)
                if os.path.isdir(d_name):
                    return d_name
            p = p.parent()

        win = self.window()
        if win:
            if hasattr(win, 'file_path') and win.file_path:
                target_dir = os.path.splitext(win.file_path)[0]
                if os.path.isdir(target_dir):
                    return target_dir
                d_name = os.path.dirname(win.file_path)
                if os.path.isdir(d_name):
                    return d_name
            if hasattr(win, 'current_editor_tab') and callable(win.current_editor_tab):
                tab = win.current_editor_tab()
                if tab and hasattr(tab, 'file_path') and tab.file_path:
                    target_dir = os.path.splitext(tab.file_path)[0]
                    if os.path.isdir(target_dir):
                        return target_dir
                    d_name = os.path.dirname(tab.file_path)
                    if os.path.isdir(d_name):
                        return d_name

        return get_addon_dir()

    def _open_slot_mappings_dialog(self):
        from src.editors.assetgroup_maker.widgets.slot_editor import TemplateSlotMappingDialog
        dialog = TemplateSlotMappingDialog(
            template_data=self.get_template_data(),
            analysis=self.current_analysis,
            context_folder=self.get_context_folder(),
            global_settings=self.get_global_settings(),
            parent=self
        )
        if dialog.exec():
            self.skipped_slots = list(dialog.skipped_slots)
            self.custom_tokens = dict(dialog.custom_tokens)
            self.material_remaps = list(dialog.material_remaps)
            self._update_slot_pills()
            self.template_changed.emit()
            self.analysis_updated.emit(self.template_id, self.current_analysis)

    def _on_asset_browser_clicked(self):
        from src.widgets.model_browser import pick_asset
        from src.settings.main import get_addon_name
        result = pick_asset(
            self,
            current_path=self.ref_edit.text().strip(),
            addon=get_addon_name(),
            addon_only=True,
            asset_types=[".vmdl", ".vsmart", ".vmat", ".vtex"],
            title="Select Reference Template Asset"
        )
        if result:
            self.set_reference_path(result)

    def _on_browse_clicked(self):
        addon_dir = get_addon_dir() or ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Reference Template Asset",
            addon_dir,
            "Valve Assets (*.vmdl *.vsmart *.vmat *.vtex);;All Files (*.*)"
        )
        if file_path:
            self.set_reference_path(file_path)

    def set_reference_path(self, path: str):
        addon_dir = get_addon_dir()
        if os.path.isabs(path) and addon_dir:
            try:
                rel_path = os.path.relpath(path, addon_dir).replace('\\', '/')
            except ValueError:
                rel_path = path.replace('\\', '/')
        else:
            rel_path = path.replace('\\', '/')

        self.ref_edit.setText(rel_path)
        self._analyze_current_reference()

    def _on_text_changed(self, text: str):
        self._analyze_current_reference()
        self.template_changed.emit()

    def _analyze_current_reference(self):
        ref_text = self.ref_edit.text().strip()
        if not ref_text:
            self.current_analysis = None
            self._update_slot_pills()
            self.analysis_updated.emit(self.template_id, None)
            return

        context_folder = None
        main_window = self.window()
        if hasattr(main_window, 'file_path') and main_window.file_path:
            context_folder = os.path.dirname(main_window.file_path)

        self.current_analysis = analyze_reference_file(ref_text, context_folder=context_folder)
        if self.current_analysis and self.current_analysis.material_remaps:
            self.material_remaps = list(self.current_analysis.material_remaps)
        self._update_slot_pills()
        self.analysis_updated.emit(self.template_id, self.current_analysis)

    def _update_slot_pills(self):
        type_names = {
            'vmdl': 'ModelDoc (.vmdl)',
            'vmat': 'Material (.vmat)',
            'vsmart': 'SmartProp (.vsmart)',
            'vsndevts': 'SoundEvent (.vsndevts)'
        }

        ext = "vmdl"
        if self.current_analysis and self.current_analysis.asset_type:
            ext = self.current_analysis.asset_type
        else:
            ref = self.ref_edit.text().strip()
            if ref:
                ext = os.path.splitext(ref)[1].lstrip('.').lower() or "vmdl"

        self.type_badge.setText(type_names.get(ext, f".{ext}"))
        self.type_badge.show()

        while self.slot_pills_layout.count():
            child = self.slot_pills_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Get active slots or fallback to standard defaults
        active_slots = {}
        if self.current_analysis and self.current_analysis.slots:
            active_slots = self.current_analysis.slots.copy()
        else:
            if ext == 'vmdl':
                active_slots = {
                    'mesh': {'label': 'Render Mesh (LOD0)', 'required': True, 'token': '#$MESH$#'},
                    'collision': {'label': 'Collision Hull (Physics)', 'required': False, 'token': '#$COLLISION$#'},
                    'lod1': {'label': 'LOD 1 Mesh', 'required': False, 'token': '#$LOD1$#'},
                }
            elif ext == 'vmat':
                active_slots = {
                    'color': {'label': 'Color Map', 'required': True, 'token': '#$COLOR$#'},
                    'normal': {'label': 'Normal Map', 'required': False, 'token': '#$NORMAL$#'},
                    'roughness': {'label': 'Roughness Map', 'required': False, 'token': '#$ROUGHNESS$#'},
                    'metalness': {'label': 'Metalness Map', 'required': False, 'token': '#$METALNESS$#'},
                }
            elif ext == 'vsndevts':
                active_slots = {
                    'sound': {'label': 'Audio File', 'required': True, 'token': '#$SOUND$#'}
                }
            else:
                active_slots = {
                    'model': {'label': 'Primary Model', 'required': True, 'token': '#$MODEL$#'}
                }

        for slot_key, slot_info in active_slots.items():
            label_text = slot_info.get('label', slot_key)
            filename = slot_info.get('filename', '')

            is_skipped = hasattr(self, 'skipped_slots') and slot_key in self.skipped_slots
            if is_skipped:
                pill = QLabel(f"<s>{label_text}</s> <span style='color:#EF5350;'>(Skipped)</span>")
                pill.setStyleSheet("""
                    QLabel {
                        background-color: #242424;
                        color: #777777;
                        border: 1px dashed #555555;
                        border-radius: 0px;
                        padding: 2px 6px;
                        font: 580 8.5pt 'Segoe UI';
                    }
                """)
            else:
                display_txt = f"<b>{label_text}:</b> {filename}" if filename else f"<b>{label_text}</b>"
                pill = QLabel(display_txt)
                pill.setStyleSheet("""
                    QLabel {
                        background-color: #2F2F31;
                        color: #E5E5E5;
                        border: 1px solid #464649;
                        border-radius: 0px;
                        padding: 2px 6px;
                        font: 580 8.5pt 'Segoe UI';
                    }
                """)
            self.slot_pills_layout.addWidget(pill)

        self.slots_container.show()

    def _open_in_cs2(self):
        ref_text = self.ref_edit.text().strip()
        if not ref_text:
            return
        if CS2Netcon:
            clean_path = ref_text.replace('\\', '/').strip('/')
            CS2Netcon.send(f"open_asset {clean_path}")

    def get_template_data(self) -> Dict[str, Any]:
        ref = self.ref_edit.text().strip()
        ext = "vmdl"
        if self.current_analysis:
            ext = self.current_analysis.asset_type
        elif ref:
            ext = os.path.splitext(ref)[1].lstrip('.').lower()

        # Build normalized replacements if analysis available
        reps = []
        existing_froms = set()

        if self.current_analysis and self.current_analysis.replacements:
            for _, rep_info in self.current_analysis.replacements.items():
                pair = rep_info.get('replacement', [])
                if len(pair) >= 2:
                    reps.append({'from': pair[0], 'to': pair[1]})
                    existing_froms.add(pair[0])

        # Preserve any manual replacements the user added in the .hbat config
        for r in getattr(self, 'replacements', []):
            if isinstance(r, dict) and 'from' in r and 'to' in r:
                if r['from'] not in existing_froms:
                    reps.append({'from': r['from'], 'to': r['to']})
                    existing_froms.add(r['from'])

        filter_mode = "include" if "Include" in self.filter_mode_combo.currentText() else "exclude"

        return {
            'id': self.template_id,
            'extension': ext or 'vmdl',
            'reference': ref,
            'filter_mode': filter_mode,
            'ignore_extensions': self.ignore_ext_edit.text().strip(),
            'ignore_list': self.ignore_files_edit.text().strip(),
            'skipped_slots': getattr(self, 'skipped_slots', []),
            'custom_tokens': getattr(self, 'custom_tokens', {}),
            'material_remaps': getattr(self, 'material_remaps', []),
            'replacements': reps
        }

    def set_template_data(self, data: Dict[str, Any]):
        self.template_id = data.get('id', self.template_id)
        self.replacements = list(data.get('replacements', []))
        self.skipped_slots = list(data.get('skipped_slots', []))
        self.custom_tokens = dict(data.get('custom_tokens', {}))
        self.material_remaps = list(data.get('material_remaps', []))
        filter_mode = data.get('filter_mode', 'exclude')
        if filter_mode == 'include':
            self.filter_mode_combo.setCurrentIndex(1)
        else:
            self.filter_mode_combo.setCurrentIndex(0)
        self.ignore_ext_edit.setText(data.get('ignore_extensions', ''))
        self.ignore_files_edit.setText(data.get('ignore_list', ''))
        self.set_reference_path(data.get('reference', ''))


class MultiTemplateManagerWidget(QWidget):
    """
    Manager container containing multiple template cards and global ignore settings.
    """

    data_changed = Signal()
    analysis_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.template_cards: List[TemplateCardWidget] = []
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # 1. Global Ignore Settings Panel (Collapsible)
        self.ignore_toggle_btn = QToolButton()
        self.ignore_toggle_btn.setIcon(QIcon(":/icons/arrow_drop_right.png"))
        self.ignore_toggle_btn.setIconSize(QSize(10, 10))
        self.ignore_toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.ignore_toggle_btn.setText("Global Ignore Settings (Extensions & File Exclusions)")
        self.ignore_toggle_btn.setCheckable(True)
        self.ignore_toggle_btn.setChecked(False)
        self.ignore_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.ignore_toggle_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                color: #A5A5A5;
                font: 600 8.5pt 'Segoe UI';
                padding: 1px 2px;
                margin: 0px;
                height: 18px;
            }
            QToolButton:hover {
                color: #FFFFFF;
            }
        """)
        self.ignore_toggle_btn.toggled.connect(self._toggle_ignore_panel)
        main_layout.addWidget(self.ignore_toggle_btn)

        self.ignore_panel = QFrame()
        self.ignore_panel.setStyleSheet("""
            QFrame {
                background-color: #282828;
                border: 1px solid #464649;
                border-radius: 2px;
            }
        """)
        ignore_layout = QVBoxLayout(self.ignore_panel)
        ignore_layout.setContentsMargins(8, 6, 8, 6)
        ignore_layout.setSpacing(4)

        mode_row = QHBoxLayout()
        mode_label = QLabel("Filter Mode:")
        mode_label.setFixedWidth(120)
        mode_label.setStyleSheet("color: #A5A5A5; font: 580 8.5pt 'Segoe UI';")
        self.filter_mode_combo = QComboBox()
        self.filter_mode_combo.setStyleSheet(qt_stylesheet_combobox)
        self.filter_mode_combo.setFixedHeight(24)
        self.filter_mode_combo.addItems(["Exclude (Blacklist)", "Include (Whitelist)"])
        self.filter_mode_combo.currentTextChanged.connect(lambda _: self.data_changed.emit())
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.filter_mode_combo)
        mode_row.addStretch(1)
        ignore_layout.addLayout(mode_row)

        ext_row = QHBoxLayout()
        ext_label = QLabel("Filter Extensions:")
        ext_label.setFixedWidth(120)
        ext_label.setStyleSheet("color: #A5A5A5; font: 580 9pt 'Segoe UI';")
        self.ignore_ext_edit = QLineEdit()
        self.ignore_ext_edit.setStyleSheet(qt_stylesheet_lineedit)
        self.ignore_ext_edit.setPlaceholderText("mb, ma, max, blend, blend1, tga, png, jpg, exr, hdr, phys_")
        self.ignore_ext_edit.textChanged.connect(lambda _: self.data_changed.emit())
        ext_row.addWidget(ext_label)
        ext_row.addWidget(self.ignore_ext_edit)
        ignore_layout.addLayout(ext_row)

        file_ignore_row = QHBoxLayout()
        file_ignore_label = QLabel("Ignore Files List:")
        file_ignore_label.setFixedWidth(120)
        file_ignore_label.setStyleSheet("color: #A5A5A5; font: 580 9pt 'Segoe UI';")
        self.ignore_files_edit = QLineEdit()
        self.ignore_files_edit.setStyleSheet(qt_stylesheet_lineedit)
        self.ignore_files_edit.setPlaceholderText("temp_*, draft_*, *backup*, .git*")
        self.ignore_files_edit.textChanged.connect(lambda _: self.data_changed.emit())
        file_ignore_row.addWidget(file_ignore_label)
        file_ignore_row.addWidget(self.ignore_files_edit)
        ignore_layout.addLayout(file_ignore_row)

        self.ignore_panel.hide()
        main_layout.addWidget(self.ignore_panel)

        # 2. Templates Cards Scroll Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        # 3. Add Template Action Button
        add_row = QHBoxLayout()
        add_row.setContentsMargins(0, 0, 0, 0)

        self.add_template_btn = QPushButton("+ Add Template")
        self.add_template_btn.setIcon(QIcon(":/valve_common/icons/tools/common/new.png"))
        self.add_template_btn.setStyleSheet(qt_stylesheet_button)
        self.add_template_btn.setFixedHeight(28)
        self.add_template_btn.setToolTip("Add another template configuration (e.g. for .vmat or .vsmart)")
        self.add_template_btn.clicked.connect(lambda: self.add_template())
        add_row.addWidget(self.add_template_btn)
        add_row.addStretch(1)

        main_layout.addLayout(add_row)

    def _toggle_ignore_panel(self, checked: bool):
        icon_path = ":/icons/arrow_drop_down.png" if checked else ":/icons/arrow_drop_right.png"
        self.ignore_toggle_btn.setIcon(QIcon(icon_path))
        self.ignore_panel.setVisible(checked)

    def add_template(self, template_data: Optional[Dict[str, Any]] = None) -> TemplateCardWidget:
        idx = len(self.template_cards)
        t_id = template_data.get('id', f'template_{idx}') if template_data else f'template_{idx}'

        card = TemplateCardWidget(template_id=t_id, parent=self)
        card.template_changed.connect(self._on_card_changed)
        card.delete_requested.connect(self.remove_template)
        card.analysis_updated.connect(self._on_card_analysis_updated)

        self.template_cards.append(card)
        self.cards_layout.addWidget(card)

        if template_data:
            card.set_template_data(template_data)

        self._update_cards_ui()
        self.data_changed.emit()
        return card

    def remove_template(self, card: TemplateCardWidget):
        if len(self.template_cards) <= 1:
            return  # Always keep at least 1 template

        if card in self.template_cards:
            self.template_cards.remove(card)
            self.cards_layout.removeWidget(card)
            card.deleteLater()
            self._update_cards_ui()
            self.data_changed.emit()
            self.analysis_updated.emit()

    def _update_cards_ui(self):
        count = len(self.template_cards)
        for idx, card in enumerate(self.template_cards, start=1):
            if count == 1:
                card.set_template_title("Reference Template Asset")
                card.set_can_delete(False)
            else:
                card.set_template_title(f"Template {idx}")
                card.set_can_delete(True)

    def _on_card_changed(self):
        self.data_changed.emit()

    def _on_card_analysis_updated(self, template_id: str, analysis: Any):
        self.analysis_updated.emit()

    def set_data(self, data: Dict[str, Any]):
        # Clear existing cards
        for card in list(self.template_cards):
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.template_cards.clear()

        # Settings
        settings = data.get('settings', {})
        filter_mode = settings.get('filter_mode', 'exclude')
        if filter_mode == 'include':
            self.filter_mode_combo.setCurrentIndex(1)
        else:
            self.filter_mode_combo.setCurrentIndex(0)
        self.ignore_ext_edit.setText(settings.get('ignore_extensions', ''))
        self.ignore_files_edit.setText(settings.get('ignore_list', ''))

        # Templates
        templates = data.get('templates', [])
        if not templates:
            templates = [{'id': 'template_0', 'extension': 'vmdl', 'reference': '', 'replacements': []}]

        for t in templates:
            self.add_template(t)

        self._update_cards_ui()

    def get_data(self) -> Dict[str, Any]:
        templates_list = [c.get_template_data() for c in self.template_cards]
        filter_mode = "include" if "Include" in self.filter_mode_combo.currentText() else "exclude"
        return {
            'settings': {
                'filter_mode': filter_mode,
                'ignore_extensions': self.ignore_ext_edit.text().strip(),
                'ignore_list': self.ignore_files_edit.text().strip(),
            },
            'templates': templates_list
        }

    def get_all_templates(self) -> List[Dict[str, Any]]:
        return [c.get_template_data() for c in self.template_cards]

    def get_analyzed_slots_map(self) -> Dict[str, Dict[str, Any]]:
        slots_map = {}
        for card in self.template_cards:
            if card.current_analysis and card.current_analysis.slots:
                slots_map[card.template_id] = card.current_analysis.slots
        return slots_map

    def get_ignore_extensions(self) -> str:
        return self.ignore_ext_edit.text().strip()

    def get_ignore_list(self) -> str:
        return self.ignore_files_edit.text().strip()


# Backward-compatibility alias
ReferenceCardWidget = TemplateCardWidget
