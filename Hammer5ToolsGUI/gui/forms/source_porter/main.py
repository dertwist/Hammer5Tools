"""
PySide6 UI for SourcePorter map converter and asset validator.
Conforms strictly to STYLESHEET.md design principles & color tokens.
Uses exact layout architecture from UnrealPorter (paths, QTabWidget, buttons row, QSplitter, ConsoleWidget).
Automatically handles CS2 installation path via Hammer5Tools environment settings.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QAction
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox, QGroupBox, QPlainTextEdit,
    QFileDialog, QMessageBox, QFrame, QMenuBar, QSplitter, QSpinBox,
    QTabWidget, QSpacerItem, QSizePolicy
)

from gui.common import enable_dark_title_bar
from gui.styles.common import apply_stylesheets
from gui.settings.common import get_cs2_path, get_addon_name
from gui.settings.main import (
    get_settings_value, set_settings_value,
    get_settings_bool, set_settings_bool
)
from gui.widgets.console import ConsoleWidget
from gui.forms.source_porter.porter_client import SourcePorterClient, PorterThread

# Matches a Find Missing issue line, e.g. "  [MissingImport] foo.vmdl -> materials/bar.vmat (material not imported)"
# — the same format Program.cs's PrintReport uses for the CLI subprocess path and
# PorterThread._run_pythonnet uses for the in-process path, so this one parser covers both.
_ISSUE_LINE_RE = re.compile(r"^\s*\[(\w+)]\s+.+?\s+->\s+(.+)$")
_IMPORTABLE_ISSUE_KINDS = {"MissingImport", "MissingPrefab", "MissingSource"}
_ISSUE_DETAIL_SUFFIX_RE = re.compile(
    r"\s+\((?:material not imported|model not imported|texture not imported|prefab map|mesh source)\)$"
)


class AssetImportDialog(QDialog):
    """Dialog for entering (or reviewing a pre-filled) list of Source 1 asset paths to import."""

    def __init__(self, parent: Optional[QWidget] = None, prefill_paths: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Asset Import")
        self.setMinimumSize(640, 420)
        enable_dark_title_bar(self)

        self.paths: List[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        inst_lbl = QLabel(
            "Enter Source 1 asset paths (models, materials, textures) to port into the output addon — one per line.\n"
            "Models import with their materials. .vmdl / .vmat paths are accepted as well."
            if not prefill_paths else
            "Missing assets found by Find Missing — review the list below (edit/remove as needed) before importing."
        )
        inst_lbl.setWordWrap(True)
        inst_lbl.setStyleSheet("color: #a5a5a5; font: 580 9pt 'Segoe UI';")
        layout.addWidget(inst_lbl)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("materials/models/props_junk/wood_crate001a.vmt\nmodels/props_junk/wood_crate001a.mdl")
        if prefill_paths:
            self.editor.setPlainText("\n".join(prefill_paths))
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #272727;
                color: #e5e5e5;
                border: 1px solid #464649;
                border-radius: 4px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 9.5pt;
                padding: 6px;
            }
        """)
        layout.addWidget(self.editor, stretch=1)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_ok = QPushButton("Import Assets")
        btn_ok.clicked.connect(self._on_accept)
        btn_box.addWidget(btn_ok)

        layout.addLayout(btn_box)
        apply_stylesheets(self)

    def _on_accept(self):
        raw_text = self.editor.toPlainText()
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        self.paths = lines
        self.accept()


class SourcePorterWidget(QDialog):
    """SourcePorter dialog using identical layout architecture to UnrealPorter."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("SourcePorter")
        self.setMinimumSize(1080, 680)
        self.resize(1200, 720)

        enable_dark_title_bar(self)

        self.client = SourcePorterClient()
        self.worker: Optional[PorterThread] = None
        self._restoring_settings = True
        self._pending_missing_paths: List[str] = []

        self._setup_menubar()
        self._setup_ui()
        self._load_defaults()
        self._connect_settings_signals()
        self._restoring_settings = False

        apply_stylesheets(self)

    def _setup_menubar(self):
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #272727;
                color: #e5e5e5;
                font: 580 9pt "Segoe UI";
                border-bottom: 1px solid #464649;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #515965;
                color: #FFFFFF;
            }
            QMenu {
                background-color: #2e2e2e;
                color: #e5e5e5;
                border: 1px solid #464649;
                font: 580 9pt "Segoe UI";
            }
            QMenu::item {
                padding: 6px 24px 6px 10px;
            }
            QMenu::item:selected {
                background-color: #515965;
                color: #FFFFFF;
            }
        """)

        # Tools Menu
        tools_menu = self.menu_bar.addMenu("&Tools")

        act_asset_import = QAction("Asset Import...", self)
        act_asset_import.triggered.connect(self._open_asset_import_dialog)
        tools_menu.addAction(act_asset_import)

        act_import_missing = QAction("Import Missing Assets (Repair)...", self)
        act_import_missing.triggered.connect(self._start_standalone_repair)
        tools_menu.addAction(act_import_missing)

        act_clean_bsp = QAction("Clean BSP Content Cache", self)
        act_clean_bsp.triggered.connect(self._clean_bsp_cache)
        tools_menu.addAction(act_clean_bsp)

        # Help Menu
        help_menu = self.menu_bar.addMenu("&Help")

        act_ref = QAction("SourcePorter Quick Reference", self)
        act_ref.triggered.connect(self._show_reference_dialog)
        help_menu.addAction(act_ref)

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setMenuBar(self.menu_bar)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(6)

        # Baseline dialog stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #2e2e2e;
                color: #e5e5e5;
                font-family: "Segoe UI", sans-serif;
            }
            QGroupBox {
                font: 700 10pt "Segoe UI";
                color: #FFFFFF;
                border: 1px solid #464649;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 10px;
                background-color: #272727;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #4a83c9;
            }
            QLabel {
                color: #e5e5e5;
                font: 600 9pt "Segoe UI";
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #2f2f31;
                color: #e5e5e5;
                border: 1px solid #464649;
                border-radius: 3px;
                padding: 4px 8px;
                font: 580 9pt "Segoe UI";
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #4a83c9;
            }
            QLineEdit:hover, QComboBox:hover, QSpinBox:hover {
                background-color: #38383a;
            }
            QPushButton {
                background-color: #2e2e2e;
                color: #e5e5e5;
                border: 1px solid #464649;
                border-radius: 3px;
                padding: 5px 12px;
                font: 580 9pt "Segoe UI";
            }
            QPushButton:hover {
                background-color: #515965;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #6d7882;
            }
            QPushButton#btn_port {
                background-color: #4a83c9;
                border-color: #2b5f9e;
                color: #FFFFFF;
                font: 700 9.5pt "Segoe UI";
            }
            QPushButton#btn_port:hover {
                background-color: #4a8ad8;
            }
            QPushButton#btn_find_missing {
                background-color: #2E7D32;
                border-color: #1b5e20;
                color: #FFFFFF;
                font: 700 9.5pt "Segoe UI";
            }
            QPushButton#btn_find_missing:hover {
                background-color: #388e3c;
            }
            QPushButton#btn_stop {
                background-color: #C62828;
                border-color: #b71c1c;
                color: #FFFFFF;
            }
            QPushButton#btn_stop:hover {
                background-color: #D32F2F;
            }
            QTabWidget::pane {
                border: 1px solid #464649;
                background-color: #272727;
                border-radius: 2px;
            }
            QTabBar::tab {
                background-color: #272727;
                color: #a5a5a5;
                padding: 6px 16px;
                font: 700 9.5pt "Segoe UI";
                border: 1px solid #464649;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #2f2f31;
                color: #e5e5e5;
                border-color: #4a83c9;
            }
        """)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)

        # --- LEFT PANEL (Paths, Tabs, Actions) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # Paths Group
        left_layout.addWidget(self._build_paths_group())

        # Tabs Widget (General, Dependencies, Advanced)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "General")
        self.tabs.addTab(self._build_dependencies_tab(), "Dependencies")
        self.tabs.addTab(self._build_advanced_tab(), "Advanced")
        left_layout.addWidget(self.tabs, stretch=1)

        # Action bar in Left Panel
        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.btn_port = QPushButton("Start Porting")
        self.btn_port.setObjectName("btn_port")
        self.btn_port.clicked.connect(self._start_porting)

        self.btn_find_missing = QPushButton("Find Missing")
        self.btn_find_missing.setObjectName("btn_find_missing")
        self.btn_find_missing.clicked.connect(self._start_find_missing)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_process)

        actions.addWidget(self.btn_port)
        actions.addWidget(self.btn_find_missing)
        actions.addWidget(self.btn_stop)
        actions.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        left_layout.addLayout(actions)
        splitter.addWidget(left_panel)

        # --- RIGHT PANEL (Console) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Console Widget
        self.console = ConsoleWidget(self)
        self.console.setContextMenuPolicy(Qt.CustomContextMenu)
        self.console.customContextMenuRequested.connect(self._console_context_menu)
        right_layout.addWidget(self.console, stretch=1)

        splitter.addWidget(right_panel)

        # Splitter sizing (Left: ~450px, Right: ~830px)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([450, 830])

        root_layout.addWidget(splitter, stretch=1)

    def _build_paths_group(self) -> QGroupBox:
        box = QGroupBox("Target & Source Configuration")
        grid = QGridLayout(box)
        grid.setContentsMargins(10, 12, 10, 10)
        grid.setVerticalSpacing(6)

        # Row 0: Source Map (Mode + File)
        grid.addWidget(QLabel("Source Map:"), 0, 0)
        map_row = QHBoxLayout()
        map_row.setContentsMargins(0, 0, 0, 0)
        map_row.setSpacing(4)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["VMF", "BSP"])
        self.mode_combo.setFixedWidth(65)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        map_row.addWidget(self.mode_combo)

        self.map_path_edit = QLineEdit()
        self.map_path_edit.setPlaceholderText("Select .vmf or .bsp map file...")
        map_row.addWidget(self.map_path_edit, stretch=1)

        grid.addLayout(map_row, 0, 1)
        btn_map = QPushButton("Browse")
        btn_map.clicked.connect(self._browse_map_file)
        grid.addWidget(btn_map, 0, 2)

        # Row 1: Target Addon
        grid.addWidget(QLabel("Target Addon:"), 1, 0)
        self.addon_combo = QComboBox()
        self.addon_combo.setEditable(True)
        grid.addWidget(self.addon_combo, 1, 1, 1, 2)

        return box

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.cb_use_bsp = QCheckBox("Generate & use BSP for clean geometry (-usebsp)")
        layout.addWidget(self.cb_use_bsp)

        self.cb_nomerge = QCheckBox("Don't merge instances (-usebsp_nomergeinstances)")
        layout.addWidget(self.cb_nomerge)

        self.cb_collapse = QCheckBox("Collapse prefabs & flatten empty group wrappers")
        layout.addWidget(self.cb_collapse)

        layout.addStretch()
        return w

    def _build_dependencies_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.cb_unpack = QCheckBox("Unpack embedded BSP pakfile content")
        layout.addWidget(self.cb_unpack)

        self.cb_compile_assets = QCheckBox("Compile asset dependencies (_c files)")
        layout.addWidget(self.cb_compile_assets)

        self.cb_nodeps = QCheckBox("Skip dependency importing (-nodeps)")
        layout.addWidget(self.cb_nodeps)

        self.cb_use_filelist = QCheckBox("Use KV Filelist import mode (-usefilelist with materials/ & models/ prefixes)")
        layout.addWidget(self.cb_use_filelist)

        self.cb_repair = QCheckBox("Auto-repair missing materials & models (re-import loop)")
        layout.addWidget(self.cb_repair)

        layout.addStretch()
        return w

    def _build_advanced_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.cb_compile_map = QCheckBox("Compile final map (.vmap_c compile)")
        layout.addWidget(self.cb_compile_map)

        self.cb_compact = QCheckBox("Compact toolchain log output")
        layout.addWidget(self.cb_compact)

        threads_layout = QHBoxLayout()
        threads_layout.setSpacing(6)
        threads_layout.addWidget(QLabel("Parallel Tool Threads:"))
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, max(1, os.cpu_count() or 4))
        threads_layout.addWidget(self.spin_threads)
        threads_layout.addStretch()
        layout.addLayout(threads_layout)

        layout.addStretch()
        return w

    def _get_active_cs2_path(self) -> Optional[str]:
        cs2 = get_cs2_path()
        if cs2 and os.path.exists(str(cs2)):
            return str(cs2).replace("\\", "/")
        return None

    def _load_defaults(self):
        # 1. Populate Addons from active CS2 path
        cs2 = self._get_active_cs2_path()
        if cs2:
            self._populate_addons(cs2)

        # 2. Target Addon
        saved_addon = get_settings_value("SourcePorter", "addon", "")
        active_addon = saved_addon or get_addon_name() or ""
        if active_addon:
            idx = self.addon_combo.findText(active_addon)
            if idx >= 0:
                self.addon_combo.setCurrentIndex(idx)
            else:
                self.addon_combo.setEditText(active_addon)

        # 3. Source Map & Mode
        saved_map = get_settings_value("SourcePorter", "map_path", "")
        if saved_map:
            self.map_path_edit.setText(saved_map.replace("\\", "/"))

        saved_mode = get_settings_value("SourcePorter", "mode", "VMF")
        mode_idx = self.mode_combo.findText(saved_mode)
        if mode_idx >= 0:
            self.mode_combo.setCurrentIndex(mode_idx)

        # 4. Checkbox Settings
        self.cb_use_bsp.setChecked(get_settings_bool("SourcePorter", "use_bsp", True))
        self.cb_nomerge.setChecked(get_settings_bool("SourcePorter", "nomerge", False))
        self.cb_collapse.setChecked(get_settings_bool("SourcePorter", "collapse", True))

        self.cb_unpack.setChecked(get_settings_bool("SourcePorter", "unpack", True))
        self.cb_compile_assets.setChecked(get_settings_bool("SourcePorter", "compile_assets", True))
        self.cb_nodeps.setChecked(get_settings_bool("SourcePorter", "nodeps", False))
        self.cb_use_filelist.setChecked(get_settings_bool("SourcePorter", "use_filelist", False))
        self.cb_repair.setChecked(get_settings_bool("SourcePorter", "repair", False))

        self.cb_compile_map.setChecked(get_settings_bool("SourcePorter", "compile_map", False))
        self.cb_compact.setChecked(get_settings_bool("SourcePorter", "compact", True))

        # 5. Threads
        default_threads = max(1, (os.cpu_count() or 4) - 1)
        saved_threads = int(get_settings_value("SourcePorter", "threads", str(default_threads)))
        self.spin_threads.setValue(saved_threads)

        if not self.client.is_available():
            self.console.warn(f"SourcePorter CLI unavailable: {self.client.why_unavailable()}")
        else:
            self.console.info("SourcePorter initialized and ready.")

    def _connect_settings_signals(self):
        """Connect UI controls to persist state changes automatically."""
        self.map_path_edit.textChanged.connect(
            lambda t: not self._restoring_settings and set_settings_value("SourcePorter", "map_path", t.strip())
        )
        self.mode_combo.currentTextChanged.connect(
            lambda t: not self._restoring_settings and set_settings_value("SourcePorter", "mode", t)
        )
        self.addon_combo.currentTextChanged.connect(
            lambda t: not self._restoring_settings and set_settings_value("SourcePorter", "addon", t.strip())
        )

        self.cb_use_bsp.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "use_bsp", s)
        )
        self.cb_nomerge.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "nomerge", s)
        )
        self.cb_collapse.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "collapse", s)
        )

        self.cb_unpack.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "unpack", s)
        )
        self.cb_compile_assets.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "compile_assets", s)
        )
        self.cb_nodeps.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "nodeps", s)
        )
        self.cb_use_filelist.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "use_filelist", s)
        )
        self.cb_repair.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "repair", s)
        )

        self.cb_compile_map.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "compile_map", s)
        )
        self.cb_compact.toggled.connect(
            lambda s: not self._restoring_settings and set_settings_bool("SourcePorter", "compact", s)
        )
        self.spin_threads.valueChanged.connect(
            lambda v: not self._restoring_settings and set_settings_value("SourcePorter", "threads", str(v))
        )

    def _console_context_menu(self, pos):
        menu = self.console.createStandardContextMenu()
        menu.addSeparator()
        clear_act = menu.addAction("Clear Console")
        clear_act.triggered.connect(self.console.clear)
        menu.exec_(self.console.mapToGlobal(pos))

    def _populate_addons(self, cs2_dir: str):
        self.addon_combo.clear()
        addons = set()
        for base in ["content/csgo_addons", "game/csgo_addons"]:
            addon_path = Path(cs2_dir) / base
            if addon_path.exists():
                for item in addon_path.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        addons.add(item.name)

        sorted_addons = sorted(list(addons))
        if sorted_addons:
            self.addon_combo.addItems(sorted_addons)

    def _on_mode_changed(self, mode: str):
        if not self._restoring_settings and mode == "BSP":
            self.cb_nomerge.setChecked(True)
            self.cb_unpack.setChecked(True)
            self.cb_uv_fix.setChecked(True)

    def _browse_map_file(self):
        mode = self.mode_combo.currentText()
        filt = "Source VMF Maps (*.vmf);;All Files (*.*)" if mode == "VMF" else "Source BSP Maps (*.bsp);;All Files (*.*)"
        f, _ = QFileDialog.getOpenFileName(self, f"Select Source 1 {mode} Map", "", f"Source Maps (*.vmf *.bsp);;{filt}")
        if f:
            self.map_path_edit.setText(f.replace("\\", "/"))
            if f.lower().endswith(".bsp"):
                self.mode_combo.setCurrentText("BSP")
            elif f.lower().endswith(".vmf"):
                self.mode_combo.setCurrentText("VMF")

            map_name = Path(f).stem
            if map_name and not self.addon_combo.currentText():
                self.addon_combo.setEditText(f"{map_name}_port")

    def _open_asset_import_dialog(self):
        self._prompt_asset_import()

    def _prompt_asset_import(self, prefill_paths: Optional[List[str]] = None):
        """Open the Asset Import dialog, optionally pre-filled (e.g. with Find Missing's
        results), and run the import if the user confirms the (possibly edited) list."""
        if not self.client.is_available():
            QMessageBox.critical(self, "SourcePorter Unavailable", self.client.why_unavailable())
            return

        cs2 = self._get_active_cs2_path()
        addon = self.addon_combo.currentText().strip()
        if not cs2:
            QMessageBox.warning(self, "CS2 Path Not Set", "CS2 installation directory is not set in Hammer5Tools settings.")
            return
        if not addon:
            QMessageBox.warning(self, "Missing Target Info", "Please specify target addon name.")
            return

        dialog = AssetImportDialog(self, prefill_paths=prefill_paths)
        if dialog.exec() == QDialog.Accepted and dialog.paths:
            args = [cs2, addon, *dialog.paths]
            if not self.cb_compile_assets.isChecked():
                args.append("--no-compile-assets")
            self._run_worker("force-import", args, f"Importing {len(dialog.paths)} asset(s) into {addon}...")

    def _start_standalone_repair(self):
        if not self.client.is_available():
            QMessageBox.critical(self, "SourcePorter Unavailable", self.client.why_unavailable())
            return

        cs2 = self._get_active_cs2_path()
        addon = self.addon_combo.currentText().strip()
        if not cs2:
            QMessageBox.warning(self, "CS2 Path Not Set", "CS2 installation directory is not set in Hammer5Tools settings.")
            return
        if not addon:
            QMessageBox.warning(self, "Missing Target Info", "Please specify target addon name.")
            return

        args = [cs2, addon]
        self._run_worker("repair", args, f"Repairing missing assets in addon {addon}...")

    def _clean_bsp_cache(self):
        map_file = self.map_path_edit.text().strip()
        if map_file:
            stem = Path(map_file).stem
            parent_dir = Path(map_file).parent
            candidate = parent_dir / stem
            if candidate.is_dir():
                try:
                    shutil.rmtree(candidate)
                    self.console.success(f"Removed BSP unpack cache directory: {candidate}")
                    QMessageBox.information(self, "Clean Cache", f"Removed BSP unpack cache directory:\n{candidate}")
                    return
                except Exception as ex:
                    QMessageBox.warning(self, "Error", f"Failed to clean cache: {ex}")
                    return
        QMessageBox.information(self, "Clean Cache", "No active BSP unpack cache directory found.")

    def _show_reference_dialog(self):
        ref_text = (
            "SourcePorter Reference & Features\n\n"
            "• BSP or VMF input (.bsp / .vmf)\n"
            "• Unpacks embedded pakfile content from BSPs automatically\n"
            "• Fixes brush UV scale for decompiled BSP custom materials\n"
            "• Collapses prefabs and flattens redundant single-child CMapGroup wrappers\n"
            "• Find Missing: detects unimported textures/materials/models and missing prefabs\n"
            "• Automated missing-asset repair loops\n\n"
            "SourcePorter is built with Valve import_map_community toolchain and ValveResourceFormat."
        )
        QMessageBox.information(self, "SourcePorter Reference", ref_text)

    def _handle_log_line(self, line: str):
        """Route log output lines into ConsoleWidget with appropriate color level."""
        self._collect_missing_path(line)
        l = line.lower()
        if any(x in line for x in ["===", "---", "===== BATCH"]):
            self.console.header(line)
        elif "error" in l or "failed" in l:
            self.console.error(line)
        elif "warning" in l or "missing" in l:
            self.console.warn(line)
        elif "ported" in l or "imported" in l or "clean" in l or "success" in l:
            self.console.success(line)
        else:
            self.console.info(line)

    def _collect_missing_path(self, line: str):
        """Pull the bare asset path out of a Find Missing issue line, for pre-filling
        the Asset Import dialog once the scan finishes. Ignores kinds with no
        importable path (MissingReference, ReadError) since they carry no such suffix."""
        m = _ISSUE_LINE_RE.match(line)
        if not m or m.group(1) not in _IMPORTABLE_ISSUE_KINDS:
            return
        path = _ISSUE_DETAIL_SUFFIX_RE.sub("", m.group(2)).strip()
        if path and path not in self._pending_missing_paths:
            self._pending_missing_paths.append(path)

    def _start_porting(self):
        if not self.client.is_available():
            QMessageBox.critical(self, "SourcePorter Unavailable", self.client.why_unavailable())
            return

        cs2 = self._get_active_cs2_path()
        map_file = self.map_path_edit.text().strip()
        addon = self.addon_combo.currentText().strip()

        if not cs2:
            QMessageBox.warning(self, "CS2 Path Not Set", "CS2 installation directory is not set in Hammer5Tools settings.")
            return
        if not map_file or not os.path.exists(map_file):
            QMessageBox.warning(self, "Invalid Map File", "Please select an existing .vmf or .bsp map file.")
            return
        if not addon:
            QMessageBox.warning(self, "Invalid Addon Name", "Please specify a target addon name.")
            return

        args = [cs2, map_file, addon]
        if not self.cb_use_bsp.isChecked():
            args.append("--no-bsp")
        if self.cb_nomerge.isChecked():
            args.append("--no-merge")
        if not self.cb_unpack.isChecked():
            args.append("--no-unpack")
        if self.cb_compile_map.isChecked():
            args.append("--compile")
        if not self.cb_compile_assets.isChecked():
            args.append("--no-compile-assets")
        if self.cb_nodeps.isChecked():
            args.append("--nodeps")
        if self.cb_collapse.isChecked():
            args.append("--collapse-prefabs")
        if self.cb_use_filelist.isChecked():
            args.append("--use-filelist")
        if self.cb_repair.isChecked():
            args.append("--repair")
        if not self.cb_compact.isChecked():
            args.append("--verbose")

        threads = self.spin_threads.value()
        args.extend(["--threads", str(threads)])

        self._run_worker("port", args, f"Porting map {Path(map_file).name} -> addon {addon}...")

    def _start_find_missing(self):
        if not self.client.is_available():
            QMessageBox.critical(self, "SourcePorter Unavailable", self.client.why_unavailable())
            return

        cs2 = self._get_active_cs2_path()
        addon = self.addon_combo.currentText().strip()

        if not cs2:
            QMessageBox.warning(self, "CS2 Path Not Set", "CS2 installation directory is not set in Hammer5Tools settings.")
            return
        if not addon:
            QMessageBox.warning(self, "Invalid Addon Name", "Please specify a target addon name.")
            return

        args = [cs2, addon]
        self._run_worker("validate", args, f"Finding missing assets in addon {addon}...")

    def _run_worker(self, sub_cmd: str, args: List[str], status_text: str):
        self.console.clear()
        self.console.header(status_text)
        self._pending_missing_paths = []

        self.btn_port.setEnabled(False)
        self.btn_find_missing.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.worker = PorterThread(self.client, sub_cmd, args)
        self.worker.log_signal.connect(self._handle_log_line)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.start()

    def _stop_process(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.console.warn("Process cancelled by user.")

    def _on_worker_finished(self, return_code: int):
        self.btn_port.setEnabled(True)
        self.btn_find_missing.setEnabled(True)
        self.btn_stop.setEnabled(False)

        # "validate" (Find Missing) uses exit code 1 to mean "scan completed, issues
        # found" — a normal result, not a crash. Only other/negative codes (a real
        # process error, or -1 for user-cancelled) are an actual failure for it.
        if self.worker and self.worker.sub_cmd == "validate":
            if return_code == 0:
                self.console.success("No missing assets found.")
            elif return_code == 1:
                self.console.warn("Missing assets found — see log above.")
                if self._pending_missing_paths:
                    self._prompt_asset_import(self._pending_missing_paths)
            else:
                self.console.error(f"Process finished with exit code {return_code}.")
        elif return_code == 0:
            self.console.success("Process completed successfully.")
        else:
            self.console.error(f"Process finished with exit code {return_code}.")

        # _prompt_asset_import above may have already started a new worker (the
        # chained Asset Import run) — don't clear a reference that's live now.
        if self.worker and not self.worker.isRunning():
            self.worker = None
