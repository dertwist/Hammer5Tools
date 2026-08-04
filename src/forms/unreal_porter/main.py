import os
import pathlib
from datetime import datetime

from PySide6.QtCore import Qt, Slot, QPoint, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QListWidgetItem, QMessageBox, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QListWidget, QProgressBar, QTabWidget, QComboBox,
    QCheckBox, QSplitter, QSpacerItem, QSizePolicy, QMenu, QInputDialog,
)

from src.common import enable_dark_title_bar
from src.styles.common import apply_stylesheets
from src.settings.main import (
    get_addon_dir, get_addon_name,
    get_settings_value, set_settings_value,
    get_settings_bool, set_settings_bool,
)

from src.widgets.console import ConsoleWidget
from .constants import FILE_TYPES, FILE_TYPE_TARGETS, FILE_TYPE_DESCRIPTIONS, scan_unsupported
from .converter import scan_and_group, MaterialConvertWorker
from .transform import UnitScale


class UeExportWorker(QThread):
    """Runs the UE Editor commandlet export off the UI thread — see
    ue_export_runner.run_export. Assumes a local Unreal Engine install."""
    log = Signal(str, str)
    done = Signal(bool)

    def __init__(self, engine_root, project_dir, output_dir, parent=None):
        super().__init__(parent)
        self.engine_root = engine_root
        self.project_dir = project_dir
        self.output_dir = output_dir

    def run(self):
        from .ue_export_runner import run_export, UeExportError

        def _on_line(line: str):
            self.log.emit(line, "info")

        try:
            run_export(self.engine_root, self.project_dir, self.output_dir, on_line=_on_line)
            self.log.emit("UE export finished.", "success")
            self.done.emit(True)
        except UeExportError as e:
            self.log.emit(str(e), "error")
            self.done.emit(False)
        except Exception as e:  # never let the thread die silently
            self.log.emit(f"Unexpected error: {e}", "error")
            self.done.emit(False)


class ScanWorker(QThread):
    """Scans project materials off the UI thread to prevent GUI freezing."""
    log = Signal(str, str)
    progress = Signal(int, int)
    done = Signal(dict)

    def __init__(self, project_dir, bulk_dir, output_dir, parent=None):
        super().__init__(parent)
        self.project_dir = project_dir
        self.bulk_dir = bulk_dir
        self.output_dir = output_dir

    def run(self):
        from .bridge_client import UnrealBridge
        from .converter import scan_master_materials

        bridge = None
        if self.project_dir and os.path.isdir(self.project_dir):
            bridge = UnrealBridge(self.project_dir)

        def _log_cb(msg, level="info"):
            self.log.emit(msg, level)

        def _progress_cb(current, total):
            self.progress.emit(current, total)

        try:
            master_groups = scan_master_materials(
                self.project_dir, self.bulk_dir, bridge,
                output_dir=self.output_dir, log_cb=_log_cb, progress_cb=_progress_cb
            )
            self.done.emit(master_groups)
        except Exception as e:
            self.log.emit(f"Scan failed: {e}", "error")
            self.done.emit({})


class UnrealPorterWidget(QDialog):
    """
    Unreal Engine -> Source 2 content migration helper.

    An entity/content converter (not a full auto-exporter): it turns already
    exported Unreal data into Source 2 formats — materials -> vmat,
    models -> vmdl, scenes -> vmap, content blueprints -> vsmart, and splits
    packed textures. Assets Source 2 has no equivalent for are surfaced as
    warnings rather than silently dropped.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UnrealPorter (UE → Source 2)")
        self.resize(1280, 850)
        self.setMinimumSize(960, 600)
        enable_dark_title_bar(self)
        self.setStyleSheet("background-color: #151515;")

        self.groups = {}
        self.worker = None
        self.type_checks = {}

        self._build_ui()
        apply_stylesheets(self)
        self._setup_progress_bar_style()
        self.console.info("UnrealPorter ready. Set input/output folders and Scan.")

    def _setup_progress_bar_style(self):
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #505050;
                border-radius: 2px;
                text-align: center;
                color: white;
                font-size: 10px;
                background-color: #1C1C1C;
            }
            QProgressBar::chunk {
                background-color: #1a528a;
                margin: 0px;
                width: 1px;
            }
        """)

    # UI

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Horizontal)

        # Left Container (Paths, Tabs, Actions)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        left_layout.addWidget(self._build_paths_group())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "General")
        self.tabs.addTab(self._build_scenes_tab(), "Scenes")
        self.tabs.addTab(self._build_models_tab(), "Models")
        self.tabs.addTab(self._build_materials_tab(), "Materials")
        self.tabs.addTab(self._build_other_tab(), "Textures")
        left_layout.addWidget(self.tabs, 1)

        # Action bar in Left Panel
        actions = QHBoxLayout()
        self.ue_export_button = QPushButton("Run UE Export")
        self.ue_export_button.setToolTip(
            "Launches UnrealEditor-Cmd.exe / UE4Editor-Cmd.exe to batch-export meshes/textures under the "
            "project into the cache folder (tools/ue_scripts/export_assets.py). "
            "Requires a local Unreal Engine install (UE4.27 or UE5.x)."
        )
        self.ue_export_button.clicked.connect(self.on_run_ue_export)
        self.scan_button = QPushButton("Scan Folder")
        self.scan_button.clicked.connect(self.on_scan)
        self.convert_button = QPushButton("Convert")
        self.convert_button.clicked.connect(self.on_convert)
        self.convert_button.setEnabled(False)
        actions.addWidget(self.ue_export_button)
        actions.addWidget(self.scan_button)
        actions.addWidget(self.convert_button)
        actions.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        left_layout.addLayout(actions)

        splitter.addWidget(left_panel)

        # Right Container (Console, Progress bar)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        self.console = ConsoleWidget()
        self.console.setContextMenuPolicy(Qt.CustomContextMenu)
        self.console.customContextMenuRequested.connect(self._console_context_menu)
        right_layout.addWidget(self.console, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Idle")
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setValue(0)
        right_layout.addWidget(self.progress_bar)

        splitter.addWidget(right_panel)

        # Splitter sizing and stretch factors (Left: ~35-40%, Right: ~60-65%)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([450, 830])

        root.addWidget(splitter, 1)

        # Initial auto-scan of the UE export folder if a saved path exists
        saved_export = self.cache_folder_edit.text().strip()
        if saved_export and os.path.isdir(saved_export):
            self._scan_bulk(saved_export)

    def _build_paths_group(self):
        box = QGroupBox("Conversion settings — paths")
        grid = QGridLayout(box)
        grid.setVerticalSpacing(4)

        # Row 0 — raw UE project Content folder (read via CUE4Parse bridge for
        # scenes / blueprints / material params).
        lbl_proj = QLabel("UE Project Content:")
        lbl_proj.setToolTip("scenes/blueprints/materials")
        grid.addWidget(lbl_proj, 0, 0)
        self.project_folder_edit = QLineEdit()
        self.project_folder_edit.setPlaceholderText("…/YourProject/Content")
        grid.addWidget(self.project_folder_edit, 0, 1)
        proj_btn = QPushButton("Browse")
        proj_btn.clicked.connect(self.browse_project)
        grid.addWidget(proj_btn, 0, 2)

        # Row 1 — output (addon content).
        lbl_out = QLabel("Output folder:")
        lbl_out.setToolTip("addon content")
        grid.addWidget(lbl_out, 1, 0)
        self.output_folder_edit = QLineEdit()
        grid.addWidget(self.output_folder_edit, 1, 1)
        out_btn = QPushButton("Browse")
        out_btn.clicked.connect(self.browse_output)
        grid.addWidget(out_btn, 1, 2)

        # Row 2 — the exported mesh/texture folder. This is both where "Run UE
        # Export" writes and where the converter reads FBX/TGA back from; they
        # were once two separate fields, which only ever created a way to point
        # them at different folders and silently find nothing.
        lbl_cache = QLabel("UE Export folder:")
        lbl_cache.setToolTip(
            "Meshes (.fbx) and textures (.tga/.png) exported out of Unreal — "
            "written by 'Run UE Export', or by a manual Asset Actions → Bulk Export."
        )
        grid.addWidget(lbl_cache, 2, 0)
        self.cache_folder_edit = QLineEdit()
        self.cache_folder_edit.setPlaceholderText("…/UnrealExport  (receives .fbx / .tga from Unreal)")
        grid.addWidget(self.cache_folder_edit, 2, 1)
        cache_btn = QPushButton("Browse")
        cache_btn.clicked.connect(self.browse_cache)
        grid.addWidget(cache_btn, 2, 2)

        # Row 3 — local Unreal Engine install (assumes UE is installed), used
        # to launch UnrealEditor-Cmd.exe / UE4Editor-Cmd.exe for the "Run UE Export" button.
        lbl_engine = QLabel("Unreal Engine install:")
        lbl_engine.setToolTip("Folder containing Engine/Binaries/Win64 (e.g. …/UE_4.27 or …/UE_5.7)")
        grid.addWidget(lbl_engine, 3, 0)
        self.engine_root_edit = QLineEdit()
        self.engine_root_edit.setPlaceholderText("…/UE_4.27 or …/UE_5.7  (contains Engine/Binaries/Win64)")
        grid.addWidget(self.engine_root_edit, 3, 1)
        engine_btn = QPushButton("Browse")
        engine_btn.clicked.connect(self.browse_engine)
        grid.addWidget(engine_btn, 3, 2)

        # The export folder is the single source for exported assets; these two
        # names are what the rest of the form and the material worker read.
        self.bulk_folder_edit = self.cache_folder_edit
        self.input_folder_edit = self.cache_folder_edit

        # Restore previously saved folder paths from userdata settings.
        # The settings section is still "UnrealConverter" after the rename to
        # UnrealPorter — it is an on-disk key, never shown to the user, and
        # renaming it would silently orphan everyone's saved paths.
        saved_project = get_settings_value("UnrealConverter", "project_folder", "")
        saved_bulk = get_settings_value("UnrealConverter", "bulk_folder", "")
        saved_output = get_settings_value("UnrealConverter", "output_folder", "")
        saved_cache = get_settings_value("UnrealConverter", "cache_folder", "")
        saved_engine = get_settings_value("UnrealConverter", "engine_root", "")

        if saved_project:
            self.project_folder_edit.setText(saved_project)
        # The old build had a separate "UE Bulk Export folder"; carry whichever
        # of the two the user had filled in over to the merged field rather than
        # making them re-browse for it.
        if saved_cache or saved_bulk:
            self.cache_folder_edit.setText(saved_cache or saved_bulk)
        if saved_engine:
            self.engine_root_edit.setText(saved_engine)

        addon_dir = get_addon_dir()
        if saved_output:
            self.output_folder_edit.setText(saved_output)
        elif addon_dir:
            # Output is the addon content root; the converter writes into its
            # maps/ models/ materials/ subfolders.
            self.output_folder_edit.setText(str(addon_dir).replace("\\", "/"))

        # Save to userdata whenever fields change
        self.project_folder_edit.textChanged.connect(
            lambda text: set_settings_value("UnrealConverter", "project_folder", text.strip())
        )
        self.output_folder_edit.textChanged.connect(
            lambda text: set_settings_value("UnrealConverter", "output_folder", text.strip())
        )
        self.cache_folder_edit.textChanged.connect(
            lambda text: set_settings_value("UnrealConverter", "cache_folder", text.strip())
        )
        self.engine_root_edit.textChanged.connect(
            lambda text: set_settings_value("UnrealConverter", "engine_root", text.strip())
        )
        return box

    def _build_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        types_box = QGroupBox("Convert file types")
        tv = QVBoxLayout(types_box)
        for t in FILE_TYPES:
            cb = QCheckBox(f"{t}  ->  {FILE_TYPE_TARGETS[t]}")
            cb.setToolTip(FILE_TYPE_DESCRIPTIONS[t])
            cb.setChecked(get_settings_bool("UnrealConverter", f"type_enabled_{t}", True))
            cb.stateChanged.connect(
                lambda state, t=t: set_settings_bool("UnrealConverter", f"type_enabled_{t}", state == Qt.Checked)
            )
            self.type_checks[t] = cb
            tv.addWidget(cb)
        layout.addWidget(types_box)

        settings_box = QGroupBox("General settings")
        sv = QVBoxLayout(settings_box)
        self.strip_prefixes_check = QCheckBox("Remove Unreal's file prefixes")
        self.strip_prefixes_check.setToolTip("Strips prefixes like SM_, BP_, MI_, T_, SK_ from converted asset names (e.g. SM_Chair → chair.vmdl)")
        strip_saved = get_settings_value("UnrealConverter", "strip_ue_prefixes", "false").lower() == "true"
        self.strip_prefixes_check.setChecked(strip_saved)
        self.strip_prefixes_check.stateChanged.connect(
            lambda state: set_settings_value("UnrealConverter", "strip_ue_prefixes", "true" if state == Qt.Checked else "false")
        )
        sv.addWidget(self.strip_prefixes_check)
        layout.addWidget(settings_box)

        layout.addStretch(1)
        return tab

    def _build_scenes_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.scene_entity_combo = QComboBox()
        self.scene_entity_combo.addItems(["prop_static", "prop_dynamic", "prop_physics"])
        saved_entity = get_settings_value("UnrealConverter", "scene_entity_class", "prop_static")
        idx = self.scene_entity_combo.findText(saved_entity)
        if idx != -1:
            self.scene_entity_combo.setCurrentIndex(idx)
        self.scene_entity_combo.currentTextChanged.connect(
            lambda text: set_settings_value("UnrealConverter", "scene_entity_class", text)
        )
        form.addRow("Place actors as:", self.scene_entity_combo)
        note = QLabel(
            "Reads map actors directly from the UE project via the CUE4Parse "
            "bridge (mesh ref + transform) and writes a vmap of entities. Actor "
            "transforms go through the shared UE→Source transform. Instanced "
            "foliage uses per-instance data (handled separately)."
        )
        note.setWordWrap(True)
        form.addRow(note)
        return tab

    def _build_models_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.model_scale_combo = QComboBox()
        self.model_scale_combo.addItem("1 : 1  (keep unit count)", UnitScale.ONE_TO_ONE)
        self.model_scale_combo.addItem("cm → inch  (physically correct)", UnitScale.CM_TO_INCH)
        saved_scale_idx = int(get_settings_value("UnrealConverter", "model_unit_scale_idx", 0))
        if 0 <= saved_scale_idx < self.model_scale_combo.count():
            self.model_scale_combo.setCurrentIndex(saved_scale_idx)
        self.model_scale_combo.currentIndexChanged.connect(
            lambda idx: set_settings_value("UnrealConverter", "model_unit_scale_idx", idx)
        )
        form.addRow("Unit scale:", self.model_scale_combo)
        self.model_vmdl_check = QCheckBox("Generate .vmdl wrapper referencing the mesh")
        self.model_vmdl_check.setChecked(get_settings_bool("UnrealConverter", "model_generate_vmdl", True))
        self.model_vmdl_check.stateChanged.connect(
            lambda state: set_settings_bool("UnrealConverter", "model_generate_vmdl", state == Qt.Checked)
        )
        form.addRow(self.model_vmdl_check)
        self.model_graybox_check = QCheckBox("Use global fallback material with graybox texture")
        self.model_graybox_check.setChecked(get_settings_bool("UnrealConverter", "model_graybox_fallback", False))
        self.model_graybox_check.stateChanged.connect(
            lambda state: set_settings_bool("UnrealConverter", "model_graybox_fallback", state == Qt.Checked)
        )
        form.addRow(self.model_graybox_check)
        note = QLabel(
            "Wraps an exported FBX/glTF mesh in a .vmdl. Pivot/orientation uses "
            "the shared UE→Source transform (Y mirror, Z-up preserved). Nanite "
            "meshes must be exported as regular geometry from Unreal first."
        )
        note.setWordWrap(True)
        form.addRow(note)
        return tab

    def _build_materials_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Master Material CS2 Shader & Texture Slot Swap:"))

        from .master_material_list import MasterMaterialList
        self.master_mat_list = MasterMaterialList()
        self.master_mat_list.map_slots_requested.connect(self._on_map_master_slots)
        layout.addWidget(self.master_mat_list, 1)

        note = QLabel(
            "Groups Material Instances by their parent Master Material. Select the target "
            "CS2 shader and configure texture slot assignments per Master Material. "
            "All Material Instances belonging to a Master Material inherit its shader and slot mappings."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        return tab

    def _populate_master_materials_table(self, master_groups: dict):
        self.master_groups = master_groups
        self.master_mat_list.populate(master_groups)
        self.master_checkboxes = self.master_mat_list.checkboxes()
        self.master_shader_combos = self.master_mat_list.shader_combos()

    def master_shader_selection(self) -> dict:
        """{master material name: chosen CS2 shader} as picked in the Materials
        tab. Empty until a Scan has run, in which case converters fall back to
        their name heuristic."""
        return {name: combo.currentText()
                for name, combo in getattr(self, "master_shader_combos", {}).items()}

    def master_slot_overrides(self) -> dict:
        """{master material name: texture slot overrides} from the Materials tab."""
        return {name: info.get("slot_overrides") or {}
                for name, info in getattr(self, "master_groups", {}).items()}

    @Slot(str)
    def _on_map_master_slots(self, master_name: str):
        if not hasattr(self, "master_groups") or master_name not in self.master_groups:
            return
        info = self.master_groups[master_name]
        textures = info.get("textures", {})
        initial_overrides = info.get("slot_overrides", {})

        from .slot_mapping import SlotMappingDialog
        dlg = SlotMappingDialog(master_name, textures, initial_overrides, parent=self)
        if dlg.exec() == QDialog.Accepted:
            info["slot_overrides"] = dlg.result_overrides
            self.master_mat_list.refresh(master_name, info)
            count = len(dlg.result_overrides)
            self.console.info(f"Updated texture slot mapping for {master_name} ({count} override(s) set).")

    def _build_other_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.tex_split_check = QCheckBox("Split packed textures (ORM / RMA / RMAH)")
        self.tex_split_check.setChecked(get_settings_bool("UnrealConverter", "tex_split_packed", True))
        self.tex_split_check.stateChanged.connect(
            lambda state: set_settings_bool("UnrealConverter", "tex_split_packed", state == Qt.Checked)
        )
        form.addRow(self.tex_split_check)
        self.tex_format_combo = QComboBox()
        self.tex_format_combo.addItems(["tga", "png"])
        saved_format = get_settings_value("UnrealConverter", "tex_output_format", "tga")
        fmt_idx = self.tex_format_combo.findText(saved_format)
        if fmt_idx != -1:
            self.tex_format_combo.setCurrentIndex(fmt_idx)
        self.tex_format_combo.currentTextChanged.connect(
            lambda text: set_settings_value("UnrealConverter", "tex_output_format", text)
        )
        form.addRow("Output texture format:", self.tex_format_combo)
        note = QLabel(
            "Converts textures to a Source-friendly format and splits packed "
            "channel masks into separate maps ready for vtex compilation."
        )
        note.setWordWrap(True)
        form.addRow(note)
        return tab

    # helpers

    def get_unit_scale(self):
        return self.model_scale_combo.currentData()

    def is_enabled(self, type_name):
        cb = self.type_checks.get(type_name)
        return cb.isChecked() if cb else False

    def get_calculated_rel_path(self):
        path = self.output_folder_edit.text().replace("\\", "/")
        parts = path.split("/")
        m_idx = -1
        for i, p in enumerate(parts):
            if p.lower() == "materials":
                m_idx = i
        if m_idx != -1:
            return "/".join(parts[m_idx:])
        return ""

    def browse_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Select UE Project 'Content' Folder")
        if folder:
            self.project_folder_edit.setText(folder)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder_edit.setText(folder)

    def browse_cache(self):
        folder = QFileDialog.getExistingDirectory(self, "Select UE Export Folder")
        if folder:
            self.cache_folder_edit.setText(folder)
            self._scan_bulk(folder)

    def browse_engine(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Unreal Engine Install Folder")
        if folder:
            self.engine_root_edit.setText(folder)

    def _console_context_menu(self, pos: QPoint):
        menu = self.console.createStandardContextMenu()
        menu.addSeparator()

        clear_action = menu.addAction("Clear Console")
        clear_action.triggered.connect(self.console.clear)

        save_action = menu.addAction("Save log...")
        save_action.triggered.connect(self.save_console_log)

        global_pos = self.console.mapToGlobal(pos)
        menu.exec_(global_pos)

    def save_console_log(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            default_name = f"unreal_porter_{timestamp}.txt"
            text = self.console.toPlainText()

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save converter log",
                default_name,
                "Text Files (*.txt);;All Files (*)"
            )

            if not filename:
                return

            log_file = pathlib.Path(filename)
            log_file.write_text(text, encoding="utf-8")
        except Exception as e:
            self.console.error(f"Failed to save log: {e}")

    # UE export

    _WORKER_ATTRS = ("worker", "scan_worker", "scene_worker", "ue_export_worker")

    def closeEvent(self, event):
        """Closing while a worker runs frees the widgets it's still emitting
        into — the same access violation _start_worker guards against.

        ponytail: refuses the close instead of cancelling; give the workers a
        cooperative stop flag if users need to bail out of a long conversion.
        """
        for attr in self._WORKER_ATTRS:
            w = getattr(self, attr, None)
            if w is not None and w.isRunning():
                QMessageBox.warning(self, "Busy", "A job is still running — wait for it to finish before closing.")
                event.ignore()
                return
        super().closeEvent(event)

    def _start_worker(self, attr, worker):
        """Start a QThread, refusing to overwrite one that's still running.

        `self.<attr>` is the only Python reference to the thread; rebinding it
        mid-run lets GC destroy a live QThread, which on Windows shows up as an
        RPC_E_WRONG_THREAD flood and then an access violation.
        """
        running = getattr(self, attr, None)
        if running is not None and running.isRunning():
            self.console.warn("A job is already running — wait for it to finish.")
            return False
        setattr(self, attr, worker)
        worker.start()
        return True

    def on_run_ue_export(self):
        engine_root = self.engine_root_edit.text().strip()
        project_dir = self.project_folder_edit.text().strip()
        output_dir = self.cache_folder_edit.text().strip()
        if not engine_root or not os.path.isdir(engine_root):
            QMessageBox.warning(self, "Error", "Set a valid Unreal Engine install folder first.")
            return
        if not project_dir or not os.path.isdir(project_dir):
            QMessageBox.warning(self, "Error", "Set a valid UE Project Content folder first.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Error", "Set a UE Export cache folder first.")
            return

        worker = UeExportWorker(engine_root, project_dir, output_dir)
        worker.log.connect(self._on_worker_log)
        worker.done.connect(self._on_ue_export_done)
        self.console.header("UE Export")
        self.ue_export_button.setEnabled(False)
        if not self._start_worker("ue_export_worker", worker):
            self.ue_export_button.setEnabled(True)

    @Slot(bool)
    def _on_ue_export_done(self, success):
        if success:
            self.console.info(f"UE export wrote into: {self.cache_folder_edit.text().strip()}")
        self.ue_export_button.setEnabled(True)

    # scan

    def on_scan(self):
        project_dir = self.project_folder_edit.text().strip()
        bulk_dir = self.bulk_folder_edit.text().strip()
        output_dir = self.output_folder_edit.text().strip()
        if not project_dir and not bulk_dir:
            QMessageBox.warning(self, "Error", "Set a UE Project Content folder and/or a UE Export folder.")
            return

        self.console.header("Scanning")
        self.scan_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Scanning…")

        worker = ScanWorker(project_dir, bulk_dir, output_dir)
        worker.log.connect(self._on_worker_log)
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_scan_done)
        if not self._start_worker("scan_worker", worker):
            self.scan_button.setEnabled(True)
            self.convert_button.setEnabled(True)

    @Slot(dict)
    def _on_scan_done(self, master_groups):
        if master_groups:
            self._populate_master_materials_table(master_groups)
        else:
            self.console.warn("No Master Materials or material instances found.")

        project_dir = self.project_folder_edit.text().strip()
        if project_dir and os.path.isdir(project_dir):
            self._scan_project(project_dir)
        bulk_dir = self.bulk_folder_edit.text().strip()
        if bulk_dir and os.path.isdir(bulk_dir):
            self._scan_bulk(bulk_dir)

        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Done")
        self.scan_button.setEnabled(True)
        self.convert_button.setEnabled(bool(master_groups))

    def _scan_project(self, project_dir):
        """Scan the raw UE project via the CUE4Parse bridge (entity data)."""
        if not os.path.isdir(project_dir):
            self.console.error(f"Project Content folder not found: {project_dir}")
            return
        from .bridge_client import UnrealBridge, BridgeError
        bridge = UnrealBridge(project_dir)
        if not bridge.is_available():
            self.console.error("CUE4Parse bridge unavailable — " + bridge.why_unavailable())
            self.console.info("Scenes/blueprints/materials from the raw project need the bridge.")
            return
        try:
            info = bridge.info()
            self.console.success(
                f"Project mounted ({info.get('game')}): {info.get('totalFiles')} files, "
                f"{info.get('umaps')} map(s)."
            )
            names = bridge.list("")  # all file keys
        except BridgeError as e:
            self.console.error(str(e))
            return

        hits = scan_unsupported([os.path.basename(n) for n in names])
        if hits:
            from .constants import get_unsupported
            for key, matched in hits.items():
                cat = get_unsupported(key)
                self.console.warn(f"{cat.label}: {len(matched)} asset(s) will be skipped.")
        else:
            self.console.info("No obviously unsupported assets detected.")

    def _scan_bulk(self, bulk_dir):
        """Scan the UE bulk-export folder for textures/materials."""
        if not os.path.isdir(bulk_dir):
            if hasattr(self, "console"):
                self.console.error(f"Bulk-export folder not found: {bulk_dir}")
            return
        if not hasattr(self, "master_groups") or not self.master_groups:
            from .converter import scan_master_materials
            master_groups = scan_master_materials("", bulk_dir, None)
            if master_groups:
                self._populate_master_materials_table(master_groups)
                if hasattr(self, "console"):
                    self.console.info(f"Bulk-export material groups detected: {len(master_groups)}")

    # convert

    def on_convert(self):
        output_dir = self.output_folder_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "Error", "Set an output folder first.")
            return

        _bad_suffixes = ("models", "materials", "maps", "sounds", "particles", "panorama")
        _out_tail = output_dir.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()
        if _out_tail in _bad_suffixes:
            ans = QMessageBox.warning(
                self, "Output folder looks wrong",
                f"The output folder ends with '{_out_tail}/'.\n\n"
                f"The converter writes {_out_tail}/ subfolders itself — the output "
                f"folder should be the addon content root (e.g. de_firewatch/), not a "
                f"subfolder inside it.\n\n"
                f"This would create duplicated paths like {_out_tail}/{_out_tail}/...\n\n"
                f"Continue anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return

        self.console.header("Converting")
        did_something = False

        if self.is_enabled("Textures") or self.is_enabled("Materials"):
            did_something = self._convert_materials(output_dir) or did_something

        if self.is_enabled("Scenes") or self.is_enabled("Models") or self.is_enabled("Blueprints"):
            did_something = self._convert_scenes_models(output_dir) or did_something

        if not did_something:
            self.console.warn("No file types enabled — nothing to convert.")

    def _convert_scenes_models(self, output_dir):
        project_dir = self.project_folder_edit.text().strip()
        if not project_dir or not os.path.isdir(project_dir):
            self.console.error("Scenes/Models/Blueprints need a valid UE Project Content folder.")
            return False

        from .scene_worker import SceneModelsWorker
        self.scan_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Starting…")

        worker = SceneModelsWorker(
            project_dir=project_dir,
            bulk_dir=self.bulk_folder_edit.text().strip(),
            output_dir=output_dir,
            do_scenes=self.is_enabled("Scenes"),
            do_models=self.is_enabled("Models"),
            do_blueprints=self.is_enabled("Blueprints"),
            do_materials=self.is_enabled("Materials"),
            strip_prefix=self.strip_prefixes_check.isChecked(),
            unit_scale=self.get_unit_scale(),
            use_graybox_fallback=self.model_graybox_check.isChecked(),
            master_shaders=self.master_shader_selection(),
            master_slot_overrides=self.master_slot_overrides(),
        )
        worker.log.connect(self._on_worker_log)
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_scenes_done)
        if not self._start_worker("scene_worker", worker):
            self.scan_button.setEnabled(True)
            self.convert_button.setEnabled(True)
            return False
        return True

    @Slot(str, str)
    def _on_worker_log(self, message, level):
        getattr(self.console, level, self.console.info)(message)

    @Slot()
    def _on_scenes_done(self):
        self.console.info("Scenes/Models conversion finished.")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Done")
        self.scan_button.setEnabled(True)
        self.convert_button.setEnabled(True)

    def _convert_materials(self, output_dir):
        if not hasattr(self, "master_groups") or not self.master_groups:
            self.console.warn("No Master Materials loaded to convert. Run Scan first.")
            return False

        active_master_groups = {}
        for master_name, info in self.master_groups.items():
            chk = getattr(self, "master_checkboxes", {}).get(master_name)
            combo = getattr(self, "master_shader_combos", {}).get(master_name)
            enabled = chk.isChecked() if chk else True
            selected_shader = combo.currentText() if combo else info.get("shader", "csgo_environment.vfx")

            if enabled:
                active_master_groups[master_name] = {
                    "shader": selected_shader,
                    "instances": info.get("instances", []),
                    "enabled": True,
                }

        if not active_master_groups:
            self.console.warn("No Master Material groups selected for conversion.")
            return False

        total_instances = sum(len(g["instances"]) for g in active_master_groups.values())
        self.console.info(f"Converting {total_instances} material instance(s) across {len(active_master_groups)} Master Material swap group(s)…")
        self.scan_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Starting…")

        from .converter import MasterMaterialConvertWorker

        worker = MasterMaterialConvertWorker(
            output_dir, self.bulk_folder_edit.text().strip(), active_master_groups
        )
        worker.progress.connect(self._on_progress)
        worker.file_done.connect(self._on_file_done)
        worker.finished.connect(self._on_mat_finished)
        if not self._start_worker("worker", worker):
            self.scan_button.setEnabled(True)
            self.convert_button.setEnabled(True)
            return False
        return True

    @Slot(int, int)
    def _on_progress(self, current, total):
        max_val = total if total > 0 else 100
        self.progress_bar.setMaximum(max_val)
        self.progress_bar.setValue(current)
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setFormat(f"Converting: {current}/{total} ({pct}%)")
        else:
            self.progress_bar.setFormat("Converting…")

    @Slot(str, bool, str)
    def _on_file_done(self, name, success, message):
        if success:
            self.console.success(f"{name}: {message}")
        else:
            self.console.error(f"{name}: {message}")

    @Slot(list, list)
    def _on_mat_finished(self, created, skipped):
        self.console.info(f"Materials done — created {len(created)}, skipped {len(skipped)}.")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Done")
        self.scan_button.setEnabled(True)
        self.convert_button.setEnabled(True)


# Backward-compatible alias (old name before the UnrealPorter rename).
UE2SourceMaterialsWidget = UnrealPorterWidget
