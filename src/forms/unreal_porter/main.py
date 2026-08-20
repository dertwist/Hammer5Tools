import os
import pathlib
import shutil
import time
from datetime import datetime

from PySide6.QtCore import Qt, Slot, QPoint, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QMessageBox, QProgressDialog, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QProgressBar, QTabWidget, QComboBox,
    QCheckBox, QSplitter, QSpacerItem, QSizePolicy,
)

from src.common import enable_dark_title_bar
from src.styles.common import apply_stylesheets
from src.settings.main import (
    get_addon_name,
    get_settings_value, set_settings_value,
    get_settings_bool, set_settings_bool,
)
from src.settings.common import get_cs2_path

from src.widgets.console import ConsoleWidget
from .constants import scan_unsupported
from ._worker_base import CancellableWorker
from .transform import UnitScale
from .ue_install import find_installs, install_for_project
from .ue_export_runner import DEFAULT_CONTENT_PATHS

# Exports land inside the target addon so everything one port produces lives
# under one folder and "Clean cache" is a single rmtree.
TMP_SUBDIR = "hammer5tools/unrealporter/tmp"

# Where the non-project roots land in the export cache — "/Engine/BasicShapes"
# exports to "<cache>/Engine/BasicShapes". Derived from the export runner's own
# list so adding a root there is enough.
ENGINE_EXPORT_ROOTS = [
    p.strip().strip("/").replace("/", os.sep)
    for p in DEFAULT_CONTENT_PATHS.split(";")
    if p.strip() and not p.strip().lower().startswith("/game")
]


class PrepareWorker(CancellableWorker):
    """Export the analyzed assets, then scan what came out.

    The project survey used to live here; it moved to AnalyzeWorker so its
    result could be cached and so this can only run against a project we have
    already looked at. What is left is the expensive half: booting the Editor.
    """
    log = Signal(str, str)
    progress = Signal(int, int)
    done = Signal(bool)

    def __init__(self, engine_root, project_dir, tmp_dir, output_dir, assets=(), parent=None):
        super().__init__(parent)
        self.engine_root = engine_root
        self.project_dir = project_dir
        self.tmp_dir = tmp_dir
        self.output_dir = output_dir
        self.assets = list(assets)

    def _report_scope(self):
        """Say what is going in before spending minutes on the Editor."""
        from .constants import get_unsupported

        self.log.emit(f"{len(self.assets)} analyzed asset(s) queued for export.", "info")
        for key, matched in scan_unsupported([os.path.basename(n) for n in self.assets]).items():
            self.log.emit(f"{get_unsupported(key).label}: {len(matched)} asset(s) will be skipped.", "warn")

    def run(self):
        from .ue_export_runner import run_export, UeExportError

        try:
            self._report_scope()
            if self.is_cancelled:
                self.log.emit("Asset preparation cancelled.", "warn")
                self.done.emit(False)
                return

            os.makedirs(self.tmp_dir, exist_ok=True)
            self.log.emit(f"Exporting assets into {self.tmp_dir}", "info")
            try:
                run_export(self.engine_root, self.project_dir, self.tmp_dir,
                           on_line=lambda line: self.log.emit(line, "info"),
                           assets=self.assets,
                           is_cancelled=lambda: self._is_cancelled)
            except UeExportError as e:
                # A cancel arrives here as "UE export cancelled." — log it but
                # treat it as a soft stop rather than an export failure.
                level = "warn" if "cancelled" in str(e).lower() else "error"
                self.log.emit(str(e), level)
                self.done.emit(False)
                return
            self.log.emit("UE export finished.", "success")
            self.done.emit(True)
        except Exception as e:  # never let the thread die silently
            self.log.emit(f"Prepare failed: {e}", "error")
            self.done.emit(False)


class AnalyzeWorker(CancellableWorker):
    """Mount the project, list what it holds, and group its materials."""
    log = Signal(str, str)
    progress = Signal(int, int)
    done = Signal(dict)   # the manifest, or {} on failure

    def __init__(self, uproject_path, project_dir, output_dir, parent=None):
        super().__init__(parent)
        self.uproject_path = uproject_path
        self.project_dir = project_dir
        self.output_dir = output_dir

    def run(self):
        from .bridge_client import UnrealBridge, BridgeError
        from . import analysis

        bridge = UnrealBridge(self.project_dir)
        if not bridge.is_available():
            self.log.emit("CUE4Parse bridge unavailable — " + bridge.why_unavailable(), "error")
            self.done.emit({})
            return
        if self.is_cancelled:
            self.log.emit("Analysis cancelled.", "warn")
            self.done.emit({})
            return
        try:
            assets, info, materials = analysis.analyze(
                bridge, self.project_dir,
                log_cb=lambda msg, level="info": self.log.emit(msg, level),
                progress_cb=lambda current, total: self.progress.emit(current, total),
            )
        except BridgeError as e:
            self.log.emit(f"Analysis failed: {e}", "error")
            self.done.emit({})
            return
        except Exception as e:
            self.log.emit(f"Analysis failed: {e}", "error")
            self.done.emit({})
            return

        if not assets:
            self.log.emit("Project mounted but contains no assets.", "warn")
            self.done.emit({})
            return

        # Cooperative cancel after the (potentially long) bridge scan: drop the
        # result without writing the cache, so a cancelled run still re-runs on
        # the next open rather than persisting a partial manifest.
        if self.is_cancelled:
            self.log.emit("Analysis cancelled before persisting the result.", "warn")
            self.done.emit({})
            return

        try:
            manifest = analysis.save(self.uproject_path, self.project_dir, self.output_dir,
                                     assets, info, materials)
        except OSError as e:
            # A cache we cannot persist is a slower next run, not a failure.
            self.log.emit(f"Could not write the analysis cache: {e}", "warn")
            manifest = {"assets": sorted(assets), "info": info or {}, "materials": materials}
        self.done.emit(manifest)


class ExpandRefsWorker(CancellableWorker):
    """Walk the chosen assets' dependencies off the UI thread.

    Assets already in the cached reference graph cost nothing; the rest are
    read from the bridge — one process each — and folded back into the
    manifest so no asset is ever scanned twice for the same project state.
    """
    log = Signal(str, str)
    progress = Signal(int, int)
    done = Signal(set, dict)

    def __init__(self, uproject_path, project_dir, output_dir, chosen, all_keys,
                 refs_map=None, parent=None):
        super().__init__(parent)
        self.uproject_path = uproject_path
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.chosen = chosen
        self.all_keys = all_keys
        self.refs_map = refs_map

    def run(self):
        from .bridge_client import UnrealBridge
        from .asset_selection import expand_references
        from . import analysis

        new_refs = {}
        try:
            selected = expand_references(
                UnrealBridge(self.project_dir), self.chosen, self.all_keys,
                log_cb=lambda msg, level="info": self.log.emit(msg, level),
                progress_cb=lambda current, total: self.progress.emit(current, total),
                refs_map=self.refs_map, new_refs=new_refs,
                is_cancelled=lambda: self._is_cancelled,
            )
        except Exception as e:  # never let the thread die silently
            self.log.emit(f"Reference scan failed: {e}", "error")
            # Fall back to exactly what was ticked rather than losing the picks.
            selected = set(self.chosen)
        # Whatever was read this time is worth keeping even if the walk failed.
        analysis.update_refs(self.output_dir, new_refs)
        self.done.emit(selected, new_refs)


class UnrealPorterWidget(QDialog):
    """
    Unreal Engine -> Source 2 content migration helper.

    Two steps. "Prepare Assets" surveys a .uproject, drives the local Editor to
    export its meshes and textures into the target addon's export cache, and
    scans the result. "Convert" turns that into Source 2 formats — materials ->
    vmat, models -> vmdl, scenes -> vmap, content blueprints -> vsmart — with
    the Materials tab in between for shader and texture-slot swapping.

    Assets Source 2 has no equivalent for are surfaced as warnings rather than
    silently dropped.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UnrealPorter")
        self.resize(1280, 850)
        self.setMinimumSize(960, 600)
        enable_dark_title_bar(self)
        self.setStyleSheet("background-color: #272727;")

        self.groups = {}
        self.worker = None
        self._analyzed_uproject = None
        self._project_assets = []
        self._project_refs = {}
        self._selected_assets = set()
        self._installs = find_installs()

        self._build_ui()
        apply_stylesheets(self)
        self._setup_progress_bar_style()
        if self._installs:
            self.console.info("UnrealPorter ready.")
        else:
            self.console.warn(
                "No Unreal Engine install found — exporting new assets requires one. "
                "Converting already-exported assets still works."
            )
        self.console.header("Instructions")
        self.console.info("1. Select Unreal Engine Project")
        self.console.info("2. Analyze project")
        self.console.info("3. Select assets you want to port")
        self.console.info("4. Click Convert")

        self.console.header("Limitations")
        self.console.warn("• Scene override materials (per-actor material overrides on map instances)")
        self.console.warn("• Cables / Splines (CableComponent physics & spline mesh ropes)")
        self.console.warn("• Landscapes / Terrain (heightfield layer blending; must bake to static mesh)")
        self.console.warn("• Master Materials & HLSL graphs (only Material Instance parameters -> vmat)")
        self.console.warn("• Nanite virtual geometry (export regular LOD triangulated mesh first)")
        self.console.warn("• Niagara / Cascade particles (must re-author in CS2 particle editor)")
        self.console.warn("• Virtual Textures / RVT (must bake to standard 2D textures in UE first)")
        self.console.warn("• Gameplay & Logic Blueprints (only static component layout Blueprints -> vsmart)")
        self.console.warn("• Lumen & Baked Lightmaps (lighting bakes must be re-authored in Hammer)")
        self.console.warn("• Skeletal Meshes & Character Rigs (rigged animations / PhAT physics assets)")

        self.console.header("Settings")
        # _build_ui ran before the console existed, so the first report lands here.
        self._log_export_cache()
        # Restores the port picker and re-enables Prepare from cache, without a
        # bridge call when the project has not changed since last time.
        self.ensure_analysis()

    def _setup_progress_bar_style(self):
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #5e5e5e;
                border-radius: 2px;
                text-align: center;
                color: white;
                font-size: 10px;
                background-color: #2e2e2e;
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
        self.tabs.addTab(self._build_materials_tab(), "Materials")
        left_layout.addWidget(self.tabs, 1)

        # Action bar in Left Panel
        actions = QHBoxLayout()
        self.reanalyze_button = QPushButton("Re-analyze")
        self.reanalyze_button.setToolTip(
            "Re-read the project through the CUE4Parse bridge, ignoring the cached "
            "analysis. Only needed if the project changed in a way the file "
            "timestamps did not capture."
        )
        self.reanalyze_button.setEnabled(False)
        self.reanalyze_button.clicked.connect(lambda: self.ensure_analysis(force=True))
        self.convert_button = QPushButton("Convert")
        self.convert_button.setToolTip(
            "Automatically prepares missing asset exports from Unreal Engine "
            "and converts selected materials, models, blueprints, and maps to CS2 formats."
        )
        self.convert_button.clicked.connect(self.on_convert)
        self.convert_button.setEnabled(False)
        self.clean_cache_button = QPushButton("Clean cache")
        self.clean_cache_button.setToolTip("Deletes the addon's export cache folder.")
        self.clean_cache_button.clicked.connect(self.on_clean_cache)
        actions.addWidget(self.reanalyze_button)
        actions.addWidget(self.convert_button)
        actions.addWidget(self.clean_cache_button)
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

        # Pick up an export cache left behind by a previous session so the
        # Materials tab is populated without re-running the whole export.
        self._scan_tmp()

    def _build_paths_group(self):
        box = QGroupBox("Conversion settings — paths")
        grid = QGridLayout(box)
        grid.setVerticalSpacing(4)

        # Row 0 — the .uproject. Everything else is derived from it: the Content
        # folder the bridge reads, and (via EngineAssociation) which engine runs
        # the export.
        lbl_proj = QLabel("UE Project:")
        lbl_proj.setToolTip("The project's .uproject file — scenes, blueprints and materials are read next to it.")
        grid.addWidget(lbl_proj, 0, 0)
        self.uproject_edit = QLineEdit()
        self.uproject_edit.setPlaceholderText("…/YourProject/YourProject.uproject")
        grid.addWidget(self.uproject_edit, 0, 1)
        proj_btn = QPushButton("Browse")
        proj_btn.clicked.connect(self.browse_uproject)
        grid.addWidget(proj_btn, 0, 2)

        # Row 1 — target addon, same source of truth as SourcePorter.
        grid.addWidget(QLabel("Target Addon:"), 1, 0)
        self.addon_combo = QComboBox()
        self.addon_combo.setEditable(True)
        grid.addWidget(self.addon_combo, 1, 1, 1, 2)

        # Row 2 — what got auto-detected. No engine field: if UE is installed we
        # find it, and if it isn't, a path picker would not help.
        grid.addWidget(QLabel("Editor Instance:"), 2, 0)
        self.engine_label = QLabel()
        self.engine_label.setWordWrap(True)
        grid.addWidget(self.engine_label, 2, 1, 1, 2)

        # The settings section is still "UnrealConverter" after the rename to
        # UnrealPorter — it is an on-disk key, never shown to the user, and
        # renaming it would silently orphan everyone's saved paths.
        saved_uproject = get_settings_value("UnrealConverter", "uproject_path", "")
        if not saved_uproject:
            # Carry the old Content-folder setting over rather than making
            # existing users re-browse.
            legacy_content = get_settings_value("UnrealConverter", "project_folder", "")
            if legacy_content:
                saved_uproject = self._uproject_beside(legacy_content)
        if saved_uproject:
            self.uproject_edit.setText(saved_uproject.replace("\\", "/"))

        self._populate_addons()
        active_addon = get_settings_value("UnrealConverter", "addon", "") or get_addon_name() or ""
        if active_addon:
            idx = self.addon_combo.findText(active_addon)
            if idx >= 0:
                self.addon_combo.setCurrentIndex(idx)
            else:
                self.addon_combo.setEditText(active_addon)

        self.uproject_edit.textChanged.connect(self._on_paths_changed)
        self.addon_combo.currentTextChanged.connect(self._on_paths_changed)
        self._refresh_path_labels()
        return box

    @staticmethod
    def _uproject_beside(content_dir: str) -> str:
        """The .uproject next to a project's Content folder, or ""."""
        import glob
        root = os.path.dirname(os.path.normpath(content_dir))
        matches = glob.glob(os.path.join(root, "*.uproject"))
        return matches[0] if matches else ""

    def _populate_addons(self):
        cs2 = get_cs2_path()
        if not cs2:
            return
        addons = set()
        for base in ("content/csgo_addons", "game/csgo_addons"):
            addon_path = pathlib.Path(cs2) / base
            if addon_path.exists():
                addons.update(item.name for item in addon_path.iterdir()
                              if item.is_dir() and not item.name.startswith("."))
        self.addon_combo.addItems(sorted(addons))

    def _on_paths_changed(self, _text=None):
        uproject = self.uproject_edit.text().strip()
        set_settings_value("UnrealConverter", "uproject_path", uproject)
        set_settings_value("UnrealConverter", "addon", self.addon_combo.currentText().strip())
        self._refresh_path_labels()
        if uproject != getattr(self, "_analyzed_uproject", None):
            self.ensure_analysis()

    def _refresh_path_labels(self):
        install = self.engine_install()
        if install:
            self.engine_label.setText(f"Unreal Engine, {install.version}")
            self.engine_label.setStyleSheet("color: #7ac07a;")
        else:
            self.engine_label.setText("None, please install Unreal Engine 4.27 or 5.x")
            self.engine_label.setStyleSheet("color: #d08a4a;")

        self._log_export_cache()

    def _log_export_cache(self):
        """Report the engine instance and export cache to the console when they change."""
        if not hasattr(self, "console"):
            return
        install = self.engine_install()
        install_root = install.root if install else None
        if install_root != getattr(self, "_logged_install_root", None):
            self._logged_install_root = install_root
            if install:
                self.console.info(f"Editor Instance path : {install.root}")
            else:
                self.console.warn(
                    "No Unreal Engine install found. Install Unreal Engine (4.27 or 5.x) to "
                    "export assets — conversion of already-exported files still works."
                )

        tmp = self.tmp_dir()
        if tmp == getattr(self, "_logged_tmp", None):
            return
        self._logged_tmp = tmp
        if tmp:
            self.console.info(f"Export cache: {tmp}")
        else:
            self.console.warn("Export cache: select a target addon to set one.")

    # derived paths — the form has three inputs and computes the rest

    def uproject_path(self) -> str:
        return self.uproject_edit.text().strip()

    def project_dir(self) -> str:
        """The project's Content folder, which is what the bridge mounts."""
        uproject = self.uproject_path()
        return os.path.join(os.path.dirname(uproject), "Content").replace("\\", "/") if uproject else ""

    def output_dir(self) -> str:
        """The addon content root; the converter writes maps/ models/ materials/ under it."""
        addon = self.addon_combo.currentText().strip()
        cs2 = get_cs2_path()
        if not addon or not cs2:
            return ""
        return str(pathlib.Path(cs2) / "content" / "csgo_addons" / addon).replace("\\", "/")

    def tmp_dir(self) -> str:
        """Where UE exports .fbx/.tga, and where the converter reads them back."""
        output = self.output_dir()
        return f"{output}/{TMP_SUBDIR}" if output else ""

    def engine_install(self):
        return install_for_project(self.uproject_path(), self._installs)

    def _build_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        scope_box = QGroupBox("Asset list")
        scope_layout = QVBoxLayout(scope_box)
        self.select_assets_button = QPushButton("Select assets")
        self.select_assets_button.setToolTip(
            "Pick individual assets from the project tree and filter by type. "
            "Anything the selection references — a map's meshes, a mesh's materials, "
            "a material's textures — is added automatically. Available once the "
            "project has been analyzed."
        )
        self.select_assets_button.setEnabled(False)
        self.select_assets_button.clicked.connect(self.on_select_assets)
        scope_layout.addWidget(self.select_assets_button)
        layout.addWidget(scope_box)

        settings_box = QGroupBox("General settings")
        sv = QVBoxLayout(settings_box)
        self.strip_prefixes_check = QCheckBox("Source 2 naming style")
        self.strip_prefixes_check.setToolTip(
            "Rename converted assets the way Source 2 content is named: lowercase, "
            "Unreal's type prefix dropped, PascalCase split into snake_case "
            "(SM_ChairLeg → chair_leg.vmdl). Applies to models, materials, "
            "textures and the mesh names inside the FBX."
        )
        strip_saved = get_settings_bool("UnrealConverter", "strip_ue_prefixes", True)
        self.strip_prefixes_check.setChecked(strip_saved)
        self.strip_prefixes_check.toggled.connect(
            lambda checked: set_settings_bool("UnrealConverter", "strip_ue_prefixes", checked)
        )
        sv.addWidget(self.strip_prefixes_check)
        layout.addWidget(settings_box)

        layout.addWidget(self._build_map_settings_box())
        layout.addWidget(self._build_models_box())
        layout.addWidget(self._build_textures_box())
        layout.addStretch(1)
        return tab

    # Map settings — which non-geometry actors a converted map brings across.
    # (checkbox attribute, label, settings key, default, tooltip)
    _MAP_SETTINGS = (
        ("map_lights_check", "Import light", "map_import_lights", False,
         "Convert Unreal's point, spot, rect and directional lights into their CS2 "
         "equivalents (light_omni2, light_rect, light_environment). Intensities are "
         "converted to lumens; tune a converted light with its Brightness Scale in Hammer."),
        ("map_sky_check", "Import sky", "map_import_sky", False,
         "Place an env_sky named 'sky' where Unreal's Sky Light / Sky Atmosphere sits. "
         "Unreal's sky cubemap is not converted — the entity starts on the default sky material."),
        ("map_cubemaps_check", "Import cubemaps", "map_import_cubemaps", False,
         "Convert Unreal's reflection capture actors into env_combined_light_probe_volume "
         "entities, sized from each capture's influence radius or box extent."),
        ("map_decals_check", "Import decals", "map_import_decals", True,
         "Place Unreal's decal actors as CS2 static overlays using the converted decal material."),
        ("map_mirror_check", "Mirror negative scaled actors", "map_mirror_negative_scale", True,
         "Source 2 renders a negatively scaled prop inside-out. When an actor's scale flips "
         "handedness, write a mirrored copy of its model (name_mirror.vmdl) and place that at "
         "positive scale instead."),
    )

    def _build_map_settings_box(self):
        box = QGroupBox("Map settings")
        v = QVBoxLayout(box)
        for attr, label, key, default, tooltip in self._MAP_SETTINGS:
            check = QCheckBox(label)
            check.setToolTip(tooltip)
            check.setChecked(get_settings_bool("UnrealConverter", key, default))
            check.toggled.connect(
                lambda checked, k=key: set_settings_bool("UnrealConverter", k, checked)
            )
            setattr(self, attr, check)
            v.addWidget(check)
        return box

    def _build_models_box(self):
        box = QGroupBox("Models")
        form = QFormLayout(box)
        self.model_scale_combo = QComboBox()
        # Unreal authors in centimetres: "cm" keeps the unit count as-is, "inch"
        # converts. Order matters — model_unit_scale_idx is saved by index.
        self.model_scale_combo.addItem("cm", UnitScale.ONE_TO_ONE)
        self.model_scale_combo.addItem("inch", UnitScale.CM_TO_INCH)
        self.model_scale_combo.setToolTip(
            "cm keeps Unreal's unit count 1:1. inch converts cm → inch (physically correct)."
        )
        saved_scale_idx = int(get_settings_value("UnrealConverter", "model_unit_scale_idx", 0))
        if 0 <= saved_scale_idx < self.model_scale_combo.count():
            self.model_scale_combo.setCurrentIndex(saved_scale_idx)
        self.model_scale_combo.currentIndexChanged.connect(
            lambda idx: set_settings_value("UnrealConverter", "model_unit_scale_idx", idx)
        )

        self.model_apply_mode_combo = QComboBox()
        self.model_apply_mode_combo.addItems(["FBX", "Vmdl"])
        self.model_apply_mode_combo.setToolTip(
            "FBX: Apply unit scale directly to FBX geometry (VMDL import scale remains 1.0).\n"
            "Vmdl: Keep FBX geometry untouched and set import scale in the VMDL file."
        )
        saved_apply_mode = get_settings_value("UnrealConverter", "model_scale_apply_mode", "FBX")
        apply_mode_idx = self.model_apply_mode_combo.findText(saved_apply_mode)
        if apply_mode_idx != -1:
            self.model_apply_mode_combo.setCurrentIndex(apply_mode_idx)
        self.model_apply_mode_combo.currentTextChanged.connect(
            lambda text: set_settings_value("UnrealConverter", "model_scale_apply_mode", text)
        )

        scale_row = QHBoxLayout()
        scale_row.setContentsMargins(0, 0, 0, 0)
        scale_row.addWidget(self.model_scale_combo, 1)
        scale_row.addWidget(QLabel("Apply Mode:"))
        scale_row.addWidget(self.model_apply_mode_combo, 1)
        form.addRow("Unit Scale:", scale_row)

        self.model_lods_check = QCheckBox("LODs")
        self.model_lods_check.setToolTip(
            "Build an LOD group per _LOD0..N mesh found in the exported FBX. "
            "Off imports only the highest-detail mesh."
        )
        self.model_lods_check.setChecked(get_settings_bool("UnrealConverter", "model_import_lods", True))
        self.model_lods_check.toggled.connect(
            lambda checked: set_settings_bool("UnrealConverter", "model_import_lods", checked)
        )

        self.model_collision_check = QCheckBox("Collision")
        self.model_collision_check.setToolTip(
            "Use the FBX's UCX_/UBX_ collision meshes as the physics hull. "
            "Off generates a hull from the render mesh instead."
        )
        self.model_collision_check.setChecked(get_settings_bool("UnrealConverter", "model_import_collision", True))
        self.model_collision_check.toggled.connect(
            lambda checked: set_settings_bool("UnrealConverter", "model_import_collision", checked)
        )

        mesh_row = QHBoxLayout()
        mesh_row.setContentsMargins(0, 0, 0, 0)
        mesh_row.addWidget(self.model_lods_check)
        mesh_row.addWidget(self.model_collision_check)
        mesh_row.addStretch(1)
        form.addRow("Import:", mesh_row)

        self.model_graybox_check = QCheckBox("Fallback material")
        self.model_graybox_check.setToolTip(
            "Point converted models at the global fallback material with a graybox "
            "texture instead of their own converted material."
        )
        self.model_graybox_check.setChecked(get_settings_bool("UnrealConverter", "model_graybox_fallback", False))
        self.model_graybox_check.toggled.connect(
            lambda checked: set_settings_bool("UnrealConverter", "model_graybox_fallback", checked)
        )

        other_row = QHBoxLayout()
        other_row.setContentsMargins(0, 0, 0, 0)
        other_row.addWidget(self.model_graybox_check)
        other_row.addStretch(1)
        form.addRow("Other:", other_row)
        return box

    def _build_textures_box(self):
        box = QGroupBox("Textures")
        form = QFormLayout(box)

        self.tex_format_combo = QComboBox()
        self.tex_format_combo.addItems(["tga", "png"])
        saved_format = get_settings_value("UnrealConverter", "tex_output_format", "tga")
        fmt_idx = self.tex_format_combo.findText(saved_format)
        if fmt_idx != -1:
            self.tex_format_combo.setCurrentIndex(fmt_idx)
        self.tex_format_combo.currentTextChanged.connect(
            lambda text: set_settings_value("UnrealConverter", "tex_output_format", text)
        )

        self.tex_invert_y_check = QCheckBox("Invert Y-Normal")
        self.tex_invert_y_check.setToolTip(
            "Inverts the Green channel (Y-axis) of normal maps to convert Unreal DirectX normals (Y-) to Source 2 OpenGL format (Y+)."
        )
        self.tex_invert_y_check.setChecked(
            get_settings_bool("UnrealConverter", "tex_invert_y_normal", True)
        )
        self.tex_invert_y_check.toggled.connect(
            lambda checked: set_settings_bool("UnrealConverter", "tex_invert_y_normal", checked)
        )

        tex_row = QHBoxLayout()
        tex_row.setContentsMargins(0, 0, 0, 0)
        tex_row.addWidget(self.tex_format_combo)
        tex_row.addWidget(self.tex_invert_y_check)
        tex_row.addStretch(1)

        form.addRow("Texture format:", tex_row)
        return box

    def _build_materials_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Master Material CS2 Shader & Texture Slot Swap:"))
        top_row.addStretch()

        self.reconvert_mats_button = QPushButton("Re-convert Materials")
        self.reconvert_mats_button.setToolTip(
            "Re-converts only the materials using current shader and slot mappings, "
            "without re-converting models or maps."
        )
        self.reconvert_mats_button.clicked.connect(self.on_reconvert_materials)
        self.reconvert_mats_button.setEnabled(False)
        top_row.addWidget(self.reconvert_mats_button)

        layout.addLayout(top_row)

        from .master_material_list import MasterMaterialList
        self.master_mat_list = MasterMaterialList()
        self.master_mat_list.map_slots_requested.connect(self._on_map_master_slots)
        layout.addWidget(self.master_mat_list, 1)
        return tab

    def _populate_master_materials_table(self, master_groups: dict):
        self.master_groups = master_groups
        self.master_mat_list.populate(master_groups, bulk_dir=self.tmp_dir())

    # The card widgets belong to master_mat_list and are deleteLater()'d on every
    # populate(), so they are read live rather than cached here — a cached dict
    # outlives its widgets the moment anything repopulates the list without going
    # through _populate_master_materials_table (clearing the cache does exactly
    # that), and the next read raises "Internal C++ object already deleted".
    def _master_cards(self):
        return getattr(self, "master_mat_list", None)

    def master_shader_selection(self) -> dict:
        """{master material name: chosen CS2 shader} as picked in the Materials
        tab. Empty until a Scan has run, in which case converters fall back to
        their name heuristic."""
        cards = self._master_cards()
        if cards is None:
            return {}
        return {name: combo.currentText() for name, combo in cards.shader_combos().items()}

    def master_slot_overrides(self) -> dict:
        """{master material name: texture slot overrides} from the Materials tab."""
        return {name: info.get("slot_overrides") or {}
                for name, info in getattr(self, "master_groups", {}).items()}

    def master_param_overrides(self) -> dict:
        """{master material name: scalar/vector/switch -> vmat param overrides}
        from the Materials tab's Params mapping."""
        return {name: info.get("param_overrides") or {}
                for name, info in getattr(self, "master_groups", {}).items()}

    def master_feature_flags(self) -> dict:
        """{master material name: {F_*: "0"/"1"}} from the Materials tab's Feature
        Inspector. Threaded into convert_material so toggled sections actually
        reach the written vmat (previously this output was discarded)."""
        return {name: info.get("feature_flags") or {}
                for name, info in getattr(self, "master_groups", {}).items()}

    def master_blend_modes(self) -> dict:
        """{master material name: int F_BLEND_MODE} from the Materials tab's Blend
        selector (static_overlay only). Threaded into convert_material."""
        return {name: info.get("blend_mode") or 0
                for name, info in getattr(self, "master_groups", {}).items()}

    @Slot(str)
    def _on_map_master_slots(self, master_name: str):
        if not hasattr(self, "master_groups") or master_name not in self.master_groups:
            return
        info = self.master_groups[master_name]
        textures = info.get("textures", {})
        initial_overrides = info.get("slot_overrides", {})
        initial_param_overrides = info.get("param_overrides", {})

        # The Params tab needs one representative value per parameter name. Each
        # instance's mat_data already has the master-chain-merged scalars/
        # vectors/switches; union them across instances so every name the master
        # exposes is editable, with the first non-empty value as a preview.
        scalars, vectors, switches = {}, {}, {}
        for _stem, _path, mat_data in info.get("instances", []):
            for k, v in (mat_data.get("scalars") or {}).items():
                scalars.setdefault(k, v)
            for k, v in (mat_data.get("vectors") or {}).items():
                vectors.setdefault(k, v)
            for k, v in (mat_data.get("switches") or {}).items():
                switches.setdefault(k, v)

        from .slot_mapping import ShaderRemapperDialog
        card_shaders = self.master_shader_selection()
        selected_shader = card_shaders.get(master_name) or info.get("shader") or "csgo_environment.vfx"
        info["shader"] = selected_shader
        initial_feature_flags = info.get("feature_flags", {})
        initial_blend_mode = info.get("blend_mode", 0)

        dlg = ShaderRemapperDialog(
            master_name, textures, initial_overrides,
            shader=selected_shader,
            scalars=scalars, vectors=vectors, switches=switches,
            initial_param_overrides=initial_param_overrides,
            feature_flags=initial_feature_flags,
            blend_mode=initial_blend_mode,
            bulk_dir=self.tmp_dir(), parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            info["slot_overrides"] = dlg.result_overrides
            info["param_overrides"] = dlg.result_param_overrides
            info["feature_flags"] = getattr(dlg, "result_feature_flags", {})
            info["blend_mode"] = getattr(dlg, "result_blend_mode", 0)
            info["shader"] = getattr(dlg, "result_shader", selected_shader)
            cards = self._master_cards()
            if cards and hasattr(cards, "cards") and master_name in cards.cards:
                card = cards.cards[master_name]
                c_idx = card.shader_combo.findText(info["shader"])
                if c_idx >= 0:
                    card.shader_combo.blockSignals(True)
                    card.shader_combo.setCurrentIndex(c_idx)
                    card.shader_combo.blockSignals(False)
            self.master_mat_list.refresh(master_name, info)
            slot_count = len(dlg.result_overrides)
            param_count = len(dlg.result_param_overrides)
            flag_count = len(dlg.result_feature_flags)
            self.console.info(
                f"Updated Shader Remapper for {master_name} "
                f"({info['shader']}, {slot_count} slot(s), {param_count} param(s), {flag_count} feature(s))."
            )

    # helpers

    def get_unit_scale(self):
        return self.model_scale_combo.currentData()

    def get_scale_apply_mode(self):
        return self.model_apply_mode_combo.currentText()

    def is_enabled(self, type_name):
        """Whether a file type converts. The checkboxes live in the Select assets
        dialog now, so the setting is the source of truth rather than a widget."""
        return get_settings_bool("UnrealConverter", f"type_enabled_{type_name}", True)

    def get_calculated_rel_path(self):
        path = self.output_dir()
        parts = path.split("/")
        m_idx = -1
        for i, p in enumerate(parts):
            if p.lower() == "materials":
                m_idx = i
        if m_idx != -1:
            return "/".join(parts[m_idx:])
        return ""

    def browse_uproject(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Unreal Engine Project", "", "Unreal Project (*.uproject);;All Files (*)"
        )
        if path:
            self.uproject_edit.setText(path.replace("\\", "/"))

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
                "Text Files (*.txt);;All Files (*)",
            )

            if not filename:
                return

            log_file = pathlib.Path(filename)
            log_file.write_text(text, encoding="utf-8")
        except Exception as e:
            self.console.error(f"Failed to save log: {e}")

    # prepare assets

    _WORKER_ATTRS = ("worker", "prepare_worker", "scene_worker", "refs_worker", "analyze_worker")

    def closeEvent(self, event):
        """Confirm before closing if a job is running, then stop every worker.

        Cooperative cancel (CancellableWorker.cancel) flips each worker's stop
        flag; the UE Editor subprocess spawned inside PrepareWorker is killed
        by the same flag via run_export's is_cancelled hook. We then wait
        briefly for the threads to drain before letting the close proceed — a
        worker still emitting into freed widgets is the access violation
        _start_worker exists to prevent.
        """
        running = [w for attr in self._WORKER_ATTRS
                   for w in (getattr(self, attr, None),)
                   if w is not None and w.isRunning()]
        if not running:
            super().closeEvent(event)
            return

        if QMessageBox.question(
            self, "Stop jobs?",
            "A conversion or analysis is still running.\n\nStop it and close UnrealPorter?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            event.ignore()
            return

        self._cancel_and_wait(running)
        super().closeEvent(event)

    def _cancel_and_wait(self, workers, deadline_seconds: float = 10.0):
        """Ask every running worker to stop, then pump the UI loop until they
        finish or the deadline passes.

        The UE Editor subprocess is killed by PrepareWorker via its
        is_cancelled hook, so this does not need a process handle at the
        widget level. The dialog is not delete-on-close, so a worker that
        overruns the deadline keeps a live (hidden) widget to emit into — the
        cancel flag just guarantees it won't start the *next* unit of work.
        """
        for w in workers:
            w.cancel()

        progress = QProgressDialog("Stopping jobs…", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()

        deadline = time.monotonic() + deadline_seconds
        while time.monotonic() < deadline:
            if not any(w.isRunning() for w in workers):
                break
            QApplication.processEvents()
            for w in workers:
                w.wait(50)

        progress.close()

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

    # analysis

    def _update_button_states(self):
        uproject = self.uproject_path() if hasattr(self, "uproject_path") else None
        analyzed = bool(getattr(self, "_analyzed_uproject", None)) and bool(getattr(self, "_project_assets", []))
        has_selection = bool(getattr(self, "_selected_assets", set())) or analyzed
        has_masters = bool(getattr(self, "master_groups", None))
        resolving = getattr(self, "_resolving_refs", False)

        if hasattr(self, "select_assets_button"):
            self.select_assets_button.setEnabled(analyzed and not resolving)
        if hasattr(self, "reanalyze_button"):
            self.reanalyze_button.setEnabled(bool(uproject) and os.path.isfile(uproject or "") and not resolving)
        if hasattr(self, "convert_button"):
            self.convert_button.setEnabled(analyzed and has_selection and not resolving)
        if hasattr(self, "reconvert_mats_button"):
            self.reconvert_mats_button.setEnabled(analyzed and has_masters and not resolving)

    # analysis

    def ensure_analysis(self, force=False):
        """Make sure we know what is in the project before anything else runs.

        Cheap path first: if the cached manifest's fingerprint still matches the
        project on disk, nothing runs at all.
        """
        from . import analysis

        uproject = self.uproject_path()
        project_dir = self.project_dir()
        if not uproject or not os.path.isfile(uproject) or not os.path.isdir(project_dir):
            self._set_analysis({}, uproject)
            return

        if not force:
            cached = analysis.load(uproject, project_dir, self.output_dir())
            if cached:
                self.console.info(
                    f"Using cached analysis from {cached.get('analyzed_at')} "
                    f"({len(cached.get('assets', []))} asset(s), "
                    f"{len(cached.get('refs') or {})} reference scan(s) cached) — project unchanged."
                )
                self._set_analysis(cached, uproject)
                return

        self.console.header("Analyzing project")
        self.console.info(f"{os.path.basename(uproject)} — reading assets through the CUE4Parse bridge…")
        self._set_analysis({}, uproject)
        self.progress_bar.setFormat("Analyzing…")

        worker = AnalyzeWorker(uproject, project_dir, self.output_dir())
        worker.log.connect(self._on_worker_log)
        worker.progress.connect(self._on_progress)
        worker.done.connect(lambda manifest, u=uproject: self._on_analysis_done(manifest, u))
        self._start_worker("analyze_worker", worker)

    @Slot(dict, str)
    def _on_analysis_done(self, manifest, uproject):
        if manifest:
            info = manifest.get("info") or {}
            self.console.success(
                f"Analyzed {os.path.basename(uproject)} ({info.get('game')}): "
                f"{len(manifest.get('assets', []))} asset(s), {info.get('umaps')} map(s)."
            )
        else:
            self.console.error("Analysis failed — project cannot be read.")
        self._set_analysis(manifest, uproject)
        self.progress_bar.setFormat("Idle")

    def _set_analysis(self, manifest, uproject):
        """Adopt an analysis result and gate everything that depends on it."""
        from .converter import apply_saved_swaps

        self._analyzed_uproject = uproject if manifest else None
        self._project_assets = list(manifest.get("assets", [])) if manifest else []
        self._selected_assets = set(self._project_assets) if self._project_assets else set()
        # Empty for a manifest written before refs were cached — expansion then
        # falls back to the bridge, exactly as it used to.
        self._project_refs = dict(manifest.get("refs") or {}) if manifest else {}

        groups = dict(manifest.get("materials") or {}) if manifest else {}
        if groups:
            multi_c = sum(1 for g in groups.values() if g.get("count", 0) > 1)
            single_c = sum(1 for g in groups.values() if g.get("count", 0) <= 1)
            self.console.info(f"Loading {len(groups)} Master Material group(s) ({multi_c} multi-instance, {single_c} standalone) and texture thumbnails...")
            self._populate_master_materials_table(apply_saved_swaps(groups, self.output_dir()))
            self.console.success(f"{len(groups)} Master Material group(s) ready with texture bindings and thumbnails.")
        elif manifest:
            self.console.warn("No Master Materials found in the project.")

        self._log_port_scope()
        self._update_button_states()

    def _log_port_scope(self):
        """Counts per type for whatever is actually going to be ported.

        Goes to the console rather than a label so the numbers stay on screen
        next to the run that produced them, instead of being overwritten by the
        next selection.
        """
        from .asset_selection import format_counts

        keys = self._selected_assets or self._project_assets
        if not keys:
            self.console.warn("No assets — analyze a project first.")
            return
        self.console.info("Port scope: " + (format_counts(keys) or f"{len(keys)} asset(s)"))

    def on_select_assets(self):
        if not self._project_assets:
            QMessageBox.information(
                self, "Not analyzed yet",
                "Analyze a project first to choose assets.",
            )
            return

        from .asset_selection import AssetSelectionDialog
        dlg = AssetSelectionDialog(self._project_assets, self._selected_assets, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return

        if not dlg.selected_keys:
            self._selected_assets = set(self._project_assets)
            self.console.info("Nothing ticked — the whole project will be ported.")
            self._log_port_scope()
            self._update_button_states()
            return

        self.console.header("Resolving references")
        self.console.info(f"{len(dlg.selected_keys)} asset(s) picked; following their references…")
        self._resolving_refs = True
        self._update_button_states()
        worker = ExpandRefsWorker(self.uproject_path(), self.project_dir(), self.output_dir(),
                                  dlg.selected_keys, self._project_assets,
                                  refs_map=self._project_refs)
        worker.log.connect(self._on_worker_log)
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_refs_expanded)
        if not self._start_worker("refs_worker", worker):
            self._resolving_refs = False
            self._update_button_states()

    @Slot(set, dict)
    def _on_refs_expanded(self, selected, new_refs):
        self._project_refs.update(new_refs)
        self._selected_assets = selected
        self._resolving_refs = False
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Done")
        self.console.success(f"Port scope: {len(selected)} asset(s) including references.")
        self._log_port_scope()
        self._update_button_states()

    def _scan_tmp(self):
        """Fallback: read material groups out of an export cache.

        Only reached when there is no analysis to take them from — an export
        cache left by a previous session with no project currently selected.
        """
        tmp_dir = self.tmp_dir()
        if not tmp_dir or not os.path.isdir(tmp_dir):
            return
        if getattr(self, "master_groups", None):
            return
        from .converter import scan_master_materials
        master_groups = scan_master_materials("", tmp_dir, None)
        if master_groups:
            self._populate_master_materials_table(master_groups)
            self.console.info(f"Found an existing export cache: {len(master_groups)} material group(s).")
            self._update_button_states()

    def on_clean_cache(self):
        tmp_dir = self.tmp_dir()
        if not tmp_dir or not os.path.isdir(tmp_dir):
            self.console.info("Nothing to clean — no export cache for this addon.")
            return
        if QMessageBox.question(
            self, "Clean cache",
            f"Delete the export cache?\n\n{tmp_dir}\n\n"
            "Missing assets will be re-exported from Unreal Engine on next Convert.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            shutil.rmtree(tmp_dir)
        except OSError as e:
            self.console.error(f"Failed to clean cache: {e}")
            return
        self.console.success(f"Removed {tmp_dir}")
        self.master_groups = {}
        self.master_mat_list.populate({})
        self._update_button_states()

    # convert & stage pipeline

    def _find_missing_tmp_exports(self, scope_assets) -> list:
        tmp_dir = self.tmp_dir()
        if not tmp_dir or not os.path.isdir(tmp_dir):
            return list(scope_assets)

        from .asset_selection import asset_stem, classify
        exported_stems = set()
        for root_path, _, filenames in os.walk(tmp_dir):
            for filename in filenames:
                stem = os.path.splitext(filename)[0].lower()
                exported_stems.add(stem)

        missing = []
        for key in scope_assets:
            cat = classify(key)
            if cat in ("Models", "Textures"):
                stem = asset_stem(key)
                if stem not in exported_stems:
                    missing.append(key)

        # The engine roots are never in scope_assets — the scope is a listing of
        # the project — so nothing above can ask for them. They export whenever
        # the Editor runs at all, but a cache from before they were exported
        # would otherwise satisfy this check and skip the run entirely.
        missing.extend(
            root for root in ENGINE_EXPORT_ROOTS
            if not os.path.isdir(os.path.join(tmp_dir, root))
        )
        return missing

    @Slot()
    def on_convert(self):
        project_dir = self.project_dir()
        output_dir = self.output_dir()
        if not project_dir or not os.path.isdir(project_dir):
            QMessageBox.warning(self, "Error", f"No Content folder next to the project:\n{project_dir}")
            return
        if not output_dir:
            QMessageBox.warning(self, "Error", "Select a target addon first.")
            return
        if not self._project_assets:
            QMessageBox.warning(self, "Project not analyzed", "Analyze project first.")
            return

        # STAGE 1: Resolving port scope and checking export cache
        self.console.header("(1/6) Resolving port scope and checking export cache")
        scope_assets = list(self._selected_assets) if self._selected_assets else list(self._project_assets)
        self.console.info(f"Port scope: {len(scope_assets)} asset(s) queued for conversion.")

        missing = self._find_missing_tmp_exports(scope_assets)
        if missing:
            install = self.engine_install()
            if install is None:
                QMessageBox.warning(
                    self, "No Unreal Engine found",
                    "Some assets are missing from the export cache and require Unreal Engine to export.\n\n"
                    "Please install Unreal Engine (4.27 or 5.x) or point to its install root.",
                )
                return

            # STAGE 2: Preparing assets — Running Unreal Engine
            self.console.header("(2/6) Preparing assets — Running Unreal Engine")
            self.console.info(f"Preparing {len(missing)} missing asset(s) using {install.label}...")
            self.convert_button.setEnabled(False)
            self.reanalyze_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Running Unreal Engine…")

            worker = PrepareWorker(install.root, project_dir, self.tmp_dir(), output_dir, assets=missing)
            worker.log.connect(self._on_worker_log)
            worker.progress.connect(self._on_progress)
            worker.done.connect(self._on_auto_prepare_done)
            if not self._start_worker("prepare_worker", worker):
                self._update_button_states()
                return
        else:
            self.console.header("(2/6) Preparing assets — Export cache up-to-date")
            self.console.info("All required assets are present in the export cache — skipping Unreal Engine export.")
            self._start_conversion_pipeline()

    @Slot(bool)
    def _on_auto_prepare_done(self, success):
        if not success:
            self.console.error("Asset preparation failed — conversion aborted.")
            self._update_button_states()
            return
        from .material_converter import clear_texture_index_cache
        clear_texture_index_cache()
        self.console.success("Asset preparation completed successfully.")
        self._start_conversion_pipeline()

    def _start_conversion_pipeline(self):
        output_dir = self.output_dir()

        # STAGE 3: Converting Master Materials & Material Instances
        self.console.header("(3/6) Converting Master Materials & Material Instances")
        self._log_shader_swaps()
        materials_running = False
        if self.is_enabled("Textures") or self.is_enabled("Materials"):
            materials_running = self._convert_materials(output_dir)
        else:
            self.console.info("Materials/Textures disabled — skipping stage 3.")

        # STAGE 4 & 5 must wait for stage 3. Both stages write the same vmat
        # files — stage 3 from the Materials tab's shader choices, the scene
        # worker from the materials its meshes actually use — so running them on
        # two threads let whichever finished last win per file, which showed up
        # as the shader remapping being ignored for an arbitrary subset.
        if materials_running:
            self._scene_stage_pending = True
            return
        self._start_scene_stage()

    def _start_scene_stage(self):
        self._scene_stage_pending = False
        if not (self.is_enabled("Scenes") or self.is_enabled("Models") or self.is_enabled("Blueprints")):
            self._finish_conversion_pipeline()
            return
        self.console.header("(4/6) & (5/6) Converting Models, Blueprints & Maps")
        if not self._convert_scenes_models(self.output_dir()):
            self._finish_conversion_pipeline()

    def _log_shader_swaps(self):
        """Print clean, minimal Master Material -> CS2 shader remappings."""
        swaps = self.master_shader_selection()
        if not swaps:
            self.console.warn(
                "Shader remapping: no Master Material cards loaded — analyze project first."
            )
            return
        groups = getattr(self, "master_groups", {}) or {}
        self.console.header("(3a/6) Reading Shader Remappings")
        self.console.info(f"Shader Remappings ({len(swaps)} Master Materials):")
        for master, shader in sorted(swaps.items()):
            info = groups.get(master) or {}
            count = len(info.get("instances", []))
            blend_str = ""
            if info.get("blend_mode"):
                bm = info["blend_mode"]
                blend_names = {1: "Translucent", 2: "Alpha Test", 3: "Mod2x", 4: "Additive", 5: "Multiply", 6: "ModThenAdd"}
                blend_str = f" [{blend_names.get(bm, f'Mode {bm}')}]"

            self.console.info(f"  {master} -> {shader}{blend_str} ({count} instances)")

            slot_overrides = info.get("slot_overrides") or {}
            for param, slot in sorted(slot_overrides.items()):
                if isinstance(slot, dict):
                    parts = [f"{s}: {c}" for s, c in slot.items() if s not in ("split_alpha", "split_rgba")]
                    slot_desc = ", ".join(parts) if parts else str(slot)
                else:
                    slot_desc = str(slot)
                self.console.info(f"    slot {param} -> {slot_desc}")

            for param, target in sorted((info.get("param_overrides") or {}).items()):
                self.console.info(f"    param {param} -> {target}")
            for flag, value in sorted((info.get("feature_flags") or {}).items()):
                self.console.info(f"    feature {flag} = {value}")

        import json
        raw_remaps = {
            "shaders": swaps,
            "slots": {m: info.get("slot_overrides") for m, info in groups.items() if info.get("slot_overrides")},
            "params": {m: info.get("param_overrides") for m, info in groups.items() if info.get("param_overrides")},
            "flags": {m: info.get("feature_flags") for m, info in groups.items() if info.get("feature_flags")},
            "blend_modes": {m: info.get("blend_mode") for m, info in groups.items() if info.get("blend_mode")},
        }
        self.console.info("\nRaw Shader Remappings:")
        for line in json.dumps(raw_remaps, indent=2).splitlines():
            self.console.info("  " + line)

    def _finish_conversion_pipeline(self):
        # STAGE 6: Finalizing conversion
        self.console.header("(6/6) Finalizing conversion & writing manifests")
        self.console.success("Conversion finished successfully!")
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Done")
        self._update_button_states()

    def _convert_scenes_models(self, output_dir):
        project_dir = self.project_dir()
        if not project_dir or not os.path.isdir(project_dir):
            self.console.error("Scenes/Models/Blueprints need a valid .uproject with a Content folder.")
            return False

        from .scene_worker import SceneModelsWorker
        self.convert_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Converting Models/Scenes…")

        worker = SceneModelsWorker(
            project_dir=project_dir,
            bulk_dir=self.tmp_dir(),
            output_dir=output_dir,
            do_scenes=self.is_enabled("Scenes"),
            do_models=self.is_enabled("Models"),
            do_blueprints=self.is_enabled("Blueprints"),
            do_materials=self.is_enabled("Materials"),
            strip_prefix=self.strip_prefixes_check.isChecked(),
            unit_scale=self.get_unit_scale(),
            scale_apply_mode=self.get_scale_apply_mode(),
            use_graybox_fallback=self.model_graybox_check.isChecked(),
            master_shaders=self.master_shader_selection(),
            master_slot_overrides=self.master_slot_overrides(),
            master_param_overrides=self.master_param_overrides(),
            master_feature_flags=self.master_feature_flags(),
            master_blend_modes=self.master_blend_modes(),
            selected_assets=self._selected_assets or None,
            import_lods=self.model_lods_check.isChecked(),
            import_collision=self.model_collision_check.isChecked(),
            tex_format=self.tex_format_combo.currentText(),
            invert_y_normal=self.tex_invert_y_check.isChecked(),
            import_lights=self.map_lights_check.isChecked(),
            import_sky=self.map_sky_check.isChecked(),
            import_cubemaps=self.map_cubemaps_check.isChecked(),
            import_decals=self.map_decals_check.isChecked(),
            mirror_negative_scale=self.map_mirror_check.isChecked(),
        )
        worker.log.connect(self._on_worker_log)
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_scenes_done)
        if not self._start_worker("scene_worker", worker):
            self._update_button_states()
            return False
        return True

    @Slot(str, str)
    def _on_worker_log(self, message, level):
        getattr(self.console, level, self.console.info)(message)

    @Slot()
    def _on_scenes_done(self):
        self.console.info("Scenes/Models/Blueprints conversion finished.")
        self._finish_conversion_pipeline()

    def _convert_materials(self, output_dir, ignore_scope=False):
        if not hasattr(self, "master_groups") or not self.master_groups:
            self.console.warn("No Master Materials loaded to convert.")
            return False

        from .asset_selection import asset_stem
        scope = None if (ignore_scope or not self._selected_assets) else {asset_stem(k) for k in self._selected_assets}

        cards = self._master_cards()
        checkboxes = cards.checkboxes() if cards else {}
        combos = cards.shader_combos() if cards else {}

        active_master_groups = {}
        dropped = 0
        for master_name, info in self.master_groups.items():
            chk = checkboxes.get(master_name)
            combo = combos.get(master_name)
            enabled = chk.isChecked() if chk else True
            selected_shader = combo.currentText() if combo else info.get("shader", "csgo_environment.vfx")
            if not enabled:
                continue

            instances = info.get("instances", [])
            if scope is not None:
                kept = [inst for inst in instances if str(inst[0]).lower() in scope]
                dropped += len(instances) - len(kept)
                instances = kept
                if not instances:
                    continue

            active_master_groups[master_name] = {
                "shader": selected_shader,
                "instances": instances,
                "enabled": True,
                # Carry all per-master UI mappings through to the worker; without
                # these the materials-only convert path ignored slot remap, param mapping,
                # feature flags, and blend modes configured in the UI.
                "slot_overrides": info.get("slot_overrides", {}),
                "param_overrides": info.get("param_overrides", {}),
                "feature_flags": info.get("feature_flags", {}),
                "blend_mode": info.get("blend_mode", 0),
            }

        if dropped:
            self.console.info(f"Port scope excluded {dropped} material instance(s).")

        if not active_master_groups:
            self.console.warn("No Master Material groups selected for conversion.")
            return False

        from .converter import MasterMaterialConvertWorker
        self.convert_button.setEnabled(False)
        if hasattr(self, "reconvert_mats_button"):
            self.reconvert_mats_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Converting Materials…")

        worker = MasterMaterialConvertWorker(
            output_dir=output_dir,
            bulk_dir=self.tmp_dir(),
            master_groups=active_master_groups,
            strip_prefix=self.strip_prefixes_check.isChecked(),
            tex_format=self.tex_format_combo.currentText(),
            invert_y_normal=self.tex_invert_y_check.isChecked(),
        )
        worker.file_done.connect(self._on_file_done)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_mat_finished)
        return self._start_worker("mat_worker", worker)

    @Slot(int, int)
    def _on_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setFormat(f"Processing: {current}/{total} ({pct}%)")
        else:
            self.progress_bar.setFormat("Processing…")

    @Slot(str, bool, str)
    def _on_file_done(self, name, success, message):
        if success:
            self.console.success(f"{name}: {message}")
        else:
            self.console.error(f"{name}: {message}")

    @Slot()
    def on_reconvert_materials(self):
        output_dir = self.output_dir()
        if not output_dir:
            QMessageBox.warning(self, "Error", "Select a target addon first.")
            return
        if not getattr(self, "master_groups", None):
            QMessageBox.warning(self, "Error", "No Master Materials loaded to convert.")
            return

        from .material_converter import clear_texture_index_cache
        clear_texture_index_cache()

        scope_assets = list(self._project_assets) if self._project_assets else list(self._selected_assets)
        missing = self._find_missing_tmp_exports(scope_assets)
        project_dir = self.project_dir()
        if missing and project_dir and os.path.isdir(project_dir):
            install = self.engine_install()
            if install:
                self.console.header("Preparing missing assets before Re-converting Materials")
                self.console.info(f"Preparing {len(missing)} missing asset(s) using {install.label}...")
                if hasattr(self, "reconvert_mats_button"):
                    self.reconvert_mats_button.setEnabled(False)
                self.convert_button.setEnabled(False)
                self.progress_bar.setValue(0)
                self.progress_bar.setFormat("Running Unreal Engine…")

                worker = PrepareWorker(install.root, project_dir, self.tmp_dir(), output_dir, assets=missing)
                worker.log.connect(self._on_worker_log)
                worker.progress.connect(self._on_progress)
                worker.done.connect(self._on_reconvert_prepare_done)
                if not self._start_worker("prepare_worker", worker):
                    self._update_button_states()
                return

        self.console.header("Re-converting Materials")
        self._log_shader_swaps()
        if hasattr(self, "reconvert_mats_button"):
            self.reconvert_mats_button.setEnabled(False)
        self.convert_button.setEnabled(False)

        success = self._convert_materials(output_dir, ignore_scope=True)
        if not success:
            self._update_button_states()

    @Slot(bool)
    def _on_reconvert_prepare_done(self, success):
        from .material_converter import clear_texture_index_cache
        clear_texture_index_cache()
        if not success:
            self.console.error("Asset preparation failed — material re-conversion aborted.")
            self._update_button_states()
            return
        self.console.success("Asset preparation completed successfully.")
        output_dir = self.output_dir()
        self.console.header("Re-converting Materials")
        success = self._convert_materials(output_dir, ignore_scope=True)
        if not success:
            self._update_button_states()

    @Slot(list, list)
    def _on_mat_finished(self, created, skipped):
        self.console.info(f"Materials done — created {len(created)}, skipped {len(skipped)}.")
        # Stage 4/5 was deferred until the vmats were written; start it now so
        # the two stages never write the same file at once.
        if getattr(self, "_scene_stage_pending", False):
            self._start_scene_stage()
            return
        scene = getattr(self, "scene_worker", None)
        if scene is not None and scene.isRunning():
            self.progress_bar.setFormat("Converting Models/Scenes…")
            return
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Done")
        self._update_button_states()


# Backward-compatible alias (old name before the UnrealPorter rename).
UE2SourceMaterialsWidget = UnrealPorterWidget
