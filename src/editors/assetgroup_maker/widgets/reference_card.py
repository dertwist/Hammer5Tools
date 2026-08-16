import os
from typing import Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QFrame, QGroupBox, QToolButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont, QDropEvent

from src.settings.main import get_addon_dir, debug
from src.editors.assetgroup_maker.analyzer import analyze_reference_file, ReferenceAnalysisResult
from src.styles.common import qt_stylesheet_button

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
        self.setPlaceholderText("Select or drop a reference file (.vmdl, .vmat, .vsmart)...")

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


class ReferenceCardWidget(QWidget):
    """
    Card at the top of the editor displaying:
    - Reference Template Asset selector with browse & CS2 Tools open action
    - Auto-detected slot pills (Mesh, Collision, Material, Textures)
    - Collapsible Ignore Settings (ignore_extensions & ignore_list)
    """

    reference_changed = Signal(str)
    ignore_settings_changed = Signal()
    analysis_updated = Signal(object)  # ReferenceAnalysisResult

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_analysis: Optional[ReferenceAnalysisResult] = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. Main Card Frame
        card_frame = QFrame()
        card_frame.setStyleSheet("""
            QFrame {
                background-color: #1C1C1C;
                border: 1px solid #363639;
                border-radius: 4px;
            }
        """)
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(6)

        # Title / Header Row
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon(":/valve_common/icons/tools/common/browse.png").pixmap(18, 18))
        header_row.addWidget(icon_label)

        title_label = QLabel("Reference Template Asset")
        title_label.setStyleSheet("font: 700 10pt 'Segoe UI'; color: #FFFFFF;")
        header_row.addWidget(title_label)

        header_row.addStretch(1)

        self.type_badge = QLabel("ModelDoc (.vmdl)")
        self.type_badge.setStyleSheet("""
            QLabel {
                background-color: #2D333F;
                color: #A0C4FF;
                border: 1px solid #3A78C4;
                border-radius: 3px;
                padding: 2px 6px;
                font: 600 8.5pt 'Segoe UI';
            }
        """)
        self.type_badge.hide()
        header_row.addWidget(self.type_badge)

        card_layout.addLayout(header_row)

        # File Input Row
        file_row = QHBoxLayout()
        file_row.setSpacing(4)

        self.ref_edit = DragDropReferenceLineEdit()
        self.ref_edit.file_dropped.connect(self.set_reference_path)
        self.ref_edit.textChanged.connect(self._on_text_changed)
        file_row.addWidget(self.ref_edit, 1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setStyleSheet(qt_stylesheet_button)
        self.browse_btn.setMinimumHeight(24)
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        file_row.addWidget(self.browse_btn)

        self.open_cs2_btn = QPushButton()
        self.open_cs2_btn.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.open_cs2_btn.setToolTip("Open reference asset in CS2 Tools")
        self.open_cs2_btn.setStyleSheet(qt_stylesheet_button)
        self.open_cs2_btn.setFixedSize(24, 24)
        self.open_cs2_btn.clicked.connect(self._open_in_cs2)
        file_row.addWidget(self.open_cs2_btn)

        card_layout.addLayout(file_row)

        # Slot Badges Container
        self.slots_container = QWidget()
        self.slots_layout = QHBoxLayout(self.slots_container)
        self.slots_layout.setContentsMargins(0, 2, 0, 2)
        self.slots_layout.setSpacing(6)

        slots_title = QLabel("Detected Slots:")
        slots_title.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #9D9D9D;")
        self.slots_layout.addWidget(slots_title)

        self.slot_pills_host = QWidget()
        self.slot_pills_layout = QHBoxLayout(self.slot_pills_host)
        self.slot_pills_layout.setContentsMargins(0, 0, 0, 0)
        self.slot_pills_layout.setSpacing(4)
        self.slots_layout.addWidget(self.slot_pills_host)
        self.slots_layout.addStretch(1)

        self.slots_container.hide()
        card_layout.addWidget(self.slots_container)

        # Collapsible Ignore Settings
        self.ignore_toggle_btn = QToolButton()
        self.ignore_toggle_btn.setStyleSheet("QToolButton { border: none; color: #9D9D9D; font: 600 9pt 'Segoe UI'; }")
        self.ignore_toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.ignore_toggle_btn.setArrowType(Qt.RightArrow)
        self.ignore_toggle_btn.setText("Ignore Settings (Extensions & File Exclusions)")
        self.ignore_toggle_btn.setCheckable(True)
        self.ignore_toggle_btn.setChecked(False)
        self.ignore_toggle_btn.toggled.connect(self._toggle_ignore_panel)
        card_layout.addWidget(self.ignore_toggle_btn)

        self.ignore_panel = QWidget()
        ignore_layout = QVBoxLayout(self.ignore_panel)
        ignore_layout.setContentsMargins(6, 4, 6, 4)
        ignore_layout.setSpacing(4)

        # Ignore Extensions Row
        ext_row = QHBoxLayout()
        ext_label = QLabel("Ignore Extensions:")
        ext_label.setFixedWidth(115)
        ext_label.setStyleSheet("color: #C7C7BB; font: 580 9pt 'Segoe UI';")
        self.ignore_ext_edit = QLineEdit()
        self.ignore_ext_edit.setPlaceholderText("mb, ma, max, blend, blend1, tga, png, jpg, exr, hdr")
        self.ignore_ext_edit.textChanged.connect(lambda _: self.ignore_settings_changed.emit())
        ext_row.addWidget(ext_label)
        ext_row.addWidget(self.ignore_ext_edit)
        ignore_layout.addLayout(ext_row)

        # Ignore Files List Row
        file_ignore_row = QHBoxLayout()
        file_ignore_label = QLabel("Ignore Files List:")
        file_ignore_label.setFixedWidth(115)
        file_ignore_label.setStyleSheet("color: #C7C7BB; font: 580 9pt 'Segoe UI';")
        self.ignore_files_edit = QLineEdit()
        self.ignore_files_edit.setPlaceholderText("temp_*, draft_*, *backup*, .git*")
        self.ignore_files_edit.textChanged.connect(lambda _: self.ignore_settings_changed.emit())
        file_ignore_row.addWidget(file_ignore_label)
        file_ignore_row.addWidget(self.ignore_files_edit)
        ignore_layout.addLayout(file_ignore_row)

        self.ignore_panel.hide()
        card_layout.addWidget(self.ignore_panel)

        main_layout.addWidget(card_frame)

    def _toggle_ignore_panel(self, checked: bool):
        self.ignore_toggle_btn.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.ignore_panel.setVisible(checked)

    def _on_browse_clicked(self):
        addon_dir = get_addon_dir() or ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Reference Template Asset",
            addon_dir,
            "Valve Assets (*.vmdl *.vmat *.vsmart *.vsndevts);;All Files (*.*)"
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
        self.reference_changed.emit(text.strip())
        self._analyze_current_reference()

    def _analyze_current_reference(self):
        ref_text = self.ref_edit.text().strip()
        if not ref_text:
            self.type_badge.hide()
            self.slots_container.hide()
            self.current_analysis = None
            self.analysis_updated.emit(None)
            return

        self.current_analysis = analyze_reference_file(ref_text)
        self._update_slot_pills()
        self.analysis_updated.emit(self.current_analysis)

    def _update_slot_pills(self):
        if not self.current_analysis:
            self.slots_container.hide()
            self.type_badge.hide()
            return

        # Update type badge
        type_names = {
            'vmdl': 'ModelDoc (.vmdl)',
            'vmat': 'Material (.vmat)',
            'vsmart': 'SmartProp (.vsmart)',
            'vsndevts': 'SoundEvent (.vsndevts)'
        }
        self.type_badge.setText(type_names.get(self.current_analysis.asset_type, f".{self.current_analysis.asset_type}"))
        self.type_badge.show()

        # Clear existing pills
        while self.slot_pills_layout.count():
            child = self.slot_pills_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if self.current_analysis.slots:
            for slot_key, slot_info in self.current_analysis.slots.items():
                label_text = slot_info.get('label', slot_key)
                filename = slot_info.get('filename', '')

                pill = QLabel(f"<b>{label_text}:</b> {filename}")
                pill.setStyleSheet("""
                    QLabel {
                        background-color: #26262B;
                        color: #E3E3E3;
                        border: 1px solid #363639;
                        border-radius: 3px;
                        padding: 2px 6px;
                        font: 580 8.5pt 'Segoe UI';
                    }
                """)
                self.slot_pills_layout.addWidget(pill)

            self.slots_container.show()
        else:
            self.slots_container.hide()

    def _open_in_cs2(self):
        ref_text = self.ref_edit.text().strip()
        if not ref_text:
            return
        if CS2Netcon:
            clean_path = ref_text.replace('\\', '/').strip('/')
            CS2Netcon.send(f"open_asset {clean_path}")

    # Accessors for state
    def get_reference_path(self) -> str:
        return self.ref_edit.text().strip()

    def get_ignore_extensions(self) -> str:
        return self.ignore_ext_edit.text().strip()

    def set_ignore_extensions(self, val: str):
        self.ignore_ext_edit.setText(val)

    def get_ignore_list(self) -> str:
        return self.ignore_files_edit.text().strip()

    def set_ignore_list(self, val: str):
        self.ignore_files_edit.setText(val)
