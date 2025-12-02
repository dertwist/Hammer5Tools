from PIL.ImageChops import invert

from src.forms.mapbuilder.ui_main import Ui_mapbuilder_dialog
from PySide6.QtWidgets import QDialog, QApplication, QToolButton, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, \
    QLabel, QFrame, QSpacerItem, QSizePolicy, QCheckBox
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize
from src.settings.main import get_addon_name, get_settings_value, set_settings_value
from src.common import *
from src.common import enable_dark_title_bar
import dataclasses
from typing import List, Optional


def is_text_file(path: str) -> bool:
    # Mirror IsTextFile(mappath) logic; adjust as needed for your app.
    # Treat .txt or .lst as filelists.
    lower = (path or "").lower()
    return lower.endswith(".txt") or lower.endswith(".lst")


@dataclasses.dataclass
class BuildSettings:
    # Inputs and core switches
    mappath: str = ""
    threads_selected: int = 1  # threadcount.SelectedItem
    entitiesOnly: bool = False
    build_world: bool = True
    build_vis_geometry: bool = True  # maps to -vis if desired

    # Optional toggles mapped from UI
    builddynamicsurfaceeffects: bool = True  # if False -> -skipauxfiles
    settlephys: bool = True  # if False -> -nosettle
    debugVisGeo: bool = False  # -> -debugvisgeo
    onlyBaseTileMesh: bool = False  # -> -tileMeshBaseGeometry
    genLightmaps: bool = False  # -> group of lightmap flags
    compression: bool = True  # affects -lightmapCompressionDisabled
    cpu: bool = False  # -> -lightmapcpu
    noiseremoval: bool = True  # if False -> -lightmapDisableFiltering
    noLightCalc: bool = False  # -> -disableLightingCalculations
    useDeterCharts: bool = False  # -> -lightmapDeterministicCharts
    writeDebugPT: bool = False  # -> -write_debug_path_trace_scene_info
    vrad3LargeSize: bool = False  # -> -vrad3LargeBlockSize
    lightmapres_text: str = "512"  # lightmapres.Text
    lightmapquality_index: int = 0  # lightmapquality.SelectedIndex
    buildPhys: bool = False  # -> -phys
    legacyCompileColMesh: bool = False  # -> -legacycompilecollisionmesh
    buildVis: bool = False  # -> -vis
    buildNav: bool = False  # -> -nav
    navDbg: bool = False  # -> -navdbg
    gridNav: bool = False  # -> -gridnav

    # Audio related
    saReverb: bool = False  # -> -sareverb
    baPaths: bool = False  # -> -sapaths
    bakeCustom: bool = False  # -> -sacustomdata
    audio_threads_selected: Optional[int] = None  # AudioThreadsBox.SelectedItem

    # Logging / diagnostics
    vconPrint: bool = False  # -> -vconsole, -vconport 29000
    vprofPrint: bool = False  # -> -resourcecompiler_log_compile_stats
    logPrint: bool = False  # -> -condebug -consolelog

    # Base switches always present from C# snippet
    fshallow: bool = True
    maxtextureres: int = 256
    dxlevel: int = 110
    quiet: bool = True
    unbuffered_io: bool = True

    # Outroot flags
    include_outroot: bool = True  # control adding -outroot group

    def assemble_commands(self) -> str:
        # Base argument string
        input_flag = "-filelist" if is_text_file(self.mappath) else "-i"
        quoted_map = f"\"{self.mappath}\"" if self.mappath else ""

        base_parts: List[str] = []
        base_parts.append(f"-threads {self.threads_selected}")
        if self.fshallow:
            base_parts.append("-fshallow")
        base_parts.append(f"-maxtextureres {self.maxtextureres}")
        base_parts.append(f"-dxlevel {self.dxlevel}")
        if self.quiet:
            base_parts.append("-quiet")
        if self.unbuffered_io:
            base_parts.append("-unbufferedio")
        base_parts.append(input_flag)
        base_parts.append(quoted_map)
        base_parts.append("-noassert")

        args: List[str] = []

        # World vs entities toggles
        if self.build_world:
            if "-entities" in args:
                args.remove("-entities")
            args.append("-world")
        if self.entitiesOnly:
            args.append("-entities")
            if "-world" in args:
                args.remove("-world")
            if self.audio_threads_selected is not None:
                # Remove the audio thread flags if present in ents only
                self._remove_arg_prefix(args, f"-sareverb_threads {self.audio_threads_selected}")
                self._remove_arg_prefix(args, f"-sacustomdata_threads {self.audio_threads_selected}")

        # Optional toggles
        if not self.builddynamicsurfaceeffects:
            args.append("-skipauxfiles")
        if not self.settlephys:
            args.append("-nosettle")
        if self.debugVisGeo:
            args.append("-debugvisgeo")
        if self.onlyBaseTileMesh:
            args.append("-tileMeshBaseGeometry")

        # Lightmapping block
        if self.genLightmaps:
            args.append("-bakelighting")
            if self.lightmapres_text:
                args.append(f"-lightmapMaxResolution {self.lightmapres_text}")
            args.append("-lightmapDoWeld")
            args.append(f"-lightmapVRadQuality {self.lightmapquality_index}")
            if not self.noiseremoval:
                args.append("-lightmapDisableFiltering")
            if not self.compression:
                args.append("-lightmapCompressionDisabled")
            if self.noLightCalc:
                args.append("-disableLightingCalculations")
            if self.useDeterCharts:
                args.append("-lightmapDeterministicCharts")
            if self.writeDebugPT:
                args.append("-write_debug_path_trace_scene_info")
            if self.vrad3LargeSize:
                args.append("-vrad3LargeBlockSize")
            args.append("-lightmapLocalCompile")
        else:
            # mirror: else if (!genLightmaps.Checked) { args.Add("-nolightmaps"); }
            args.append("-nolightmaps")

        # Physical/vis/nav toggles
        if self.buildPhys:
            args.append("-phys")
        if self.legacyCompileColMesh:
            args.append("-legacycompilecollisionmesh")
        if self.buildVis:
            args.append("-vis")
        if self.buildNav:
            args.append("-nav")
        if self.navDbg:
            args.append("-navdbg")
        if self.gridNav:
            args.append("-gridnav")

        # Audio toggles
        if self.saReverb:
            args.append("-sareverb")
            if self.audio_threads_selected is not None:
                args.append(f"-sareverb_threads {self.audio_threads_selected}")
                if self.oldsource2pre2020:
                    self._safe_remove(args, f"-sareverb_threads {self.audio_threads_selected}")
        if self.baPaths:
            args.append("-sapaths")
            if self.audio_threads_selected is not None:
                args.append(f"-sareverb_threads {self.audio_threads_selected}")
                if self.oldsource2pre2020:
                    self._safe_remove(args, f"-sareverb_threads {self.audio_threads_selected}")
        if self.bakeCustom:
            args.append("-sacustomdata")
            if self.audio_threads_selected is not None:
                args.append(f"-sacustomdata_threads {self.audio_threads_selected}")

        # Logging / diagnostics
        if self.vconPrint:
            args.append("-vconsole")
            args.append("-vconport 29000")
        if self.vprofPrint:
            args.append("-resourcecompiler_log_compile_stats")
        if self.logPrint:
            args.append("-condebug")
            args.append("-consolelog")

        # Outroot and version specifics
        if self.include_outroot:
            combo = "-retail -breakpad -nop4 -outroot "
            args.append(combo)
            if self.oldsource2pre2020:
                self._safe_remove(args, combo)
                args.append("-retail -breakpad -nompi -nop4 -outroot ")

        # Final join: base string + dynamic args
        base = " ".join([p for p in base_parts if p])  # keep order, skip empties
        return f"{base} " + " ".join(args)

    @staticmethod
    def _safe_remove(args: List[str], item: str) -> None:
        try:
            args.remove(item)
        except ValueError:
            pass

    @staticmethod
    def _remove_arg_prefix(args: List[str], starts_with: str) -> None:
        # Convenience for removing exactly matching strings used above.
        BuildSettings._safe_remove(args, starts_with)


@dataclasses.dataclass
class BuildPreset:
    name: str
    default: bool
    settings: BuildSettings


@dataclasses.dataclass
class BuildLog:
    timestamp: str
    log: str
    elapsed_time: float


class BuildSettingsGroup(QWidget):
    def __init__(self, parent=None, group_name: str = "Settings"):
        """Category of settings, used to group settings or buttons together."""
        super().__init__(parent)
        self.collapsed = False
        self.height = 512
        self.setContentsMargins(0, 0, 0, 0)
        self.setMaximumHeight(self.height)
        self.group_header = QHBoxLayout()
        self.group_header_frame = QFrame()
        self.group_header.setContentsMargins(0, 0, 0, 0)
        self.group_header_frame.setContentsMargins(0, 0, 0, 0)
        self.group_header_frame.setLayout(self.group_header)
        self.group_header_frame.setMaximumHeight(32)
        self.group_header_frame.setMinimumHeight(32)
        self.group_collapse_button = QToolButton(self)
        self.group_label = QLabel(group_name, self)
        self.group_content_frame = QFrame()
        self.group_content = QVBoxLayout()

        self.group_collapse_button.setIcon(QIcon(":/icons/arrow_drop_down_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        self.group_collapse_button.setIconSize(QSize(16, 16))

        # Styles
        self.group_content_frame.setStyleSheet("""background-color: red""")
        self.group_header_frame.setStyleSheet("""background-color: blue""")

        # Widgets population
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.group_header_frame)
        self.layout.addWidget(self.group_content_frame)
        self.group_header.addWidget(self.group_label)
        self.group_header.addWidget(self.group_collapse_button)
        self.group_content_frame.setLayout(self.group_content)
        self.group_content_frame.setContentsMargins(0, 0, 0, 0)

        self.spacer_widget = QWidget()
        self.spacer_layout = QVBoxLayout(self.spacer_widget)
        self.spacer_layout.addStretch(1)
        self.spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # self.group_content.addWidget(self.spacer_widget)

        # Connections
        self.group_collapse_button.clicked.connect(self.do_collapse)

    def do_collapse(self):
        if self.collapsed:
            self.collapsed = False
            self.group_content_frame.setMaximumHeight(self.height)
            self.group_collapse_button.setIcon(
                QIcon(":/icons/arrow_drop_down_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
            # self.group_content_frame.setMinimumHeight(self.height)
        else:
            self.collapsed = True
            self.group_collapse_button.setIcon(
                QIcon(":/icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
            self.group_content_frame.setMaximumHeight(0)
            self.group_content_frame.setMinimumHeight(0)

class BuildPresetWidgetBool(QWidget):
    """
    A checkbox widget. Input value is variable, which is caused to create an instance of the button.
    The purpose of giving varialbe is that it can be easily serializated to json format to keep presets on user drive.
    The variable name should be interpretated for UI. For instance varialbe name BuildVis would looks like Build Vis, we separeted one word to 2 by finding big characters and inserting a space between them.
    """
    def __init__(self, parent=None, variable: bool=False):
        super().__init__(parent)
        self.variable = variable
        self.checkbox = QCheckBox()
        self.checkbox.setCheckState(self.variable)
        self.checkbox.setText(self.convert_name())
    def convert_name(self):
        return self.variable.__name__

class BuildPresetButton(QWidget):
    def __init__(self, parent=None):
        """
        A preset of settings to build map, user can add a new preset by clicking the + button. This actions will capture all current settings and save them as a preset
        Default preset cannot be deleted or renamed.
        """
        super().__init__(parent)

    def activate(self):
        """Sets highlighting on the current instance of build preset and loads all the settings from it to the property list"""
        pass

    def deactivate(self):
        """Removes highliting and this means the preset is non-active"""
        pass

    def rename(self):
        pass

    def delete(self):
        pass


class MapBuilderDialog(QDialog):
    """
    A tool to compile VPK map for Counter Strike 2.
    Output tab - raw HTML output of the compilation process.
    Logs tab - compilation logs (saved next to the hammer5tools executable, path:Logs/MapBuilder/addon/timestamp.log).
    Report tab - a beautiful report of the compilation process. This tab will process the raw HTML output and generate a nice looking report.
        Also have a system minotor at the bottom to show how much PC resources is used (self.ui.system_monitor Qframe).
        self.ui.report_widget shows warning, issues and errors item by item, have copy button next to each item.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_mapbuilder_dialog()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)
        self.populate_widgets()
        self.__connections()

    def __connections(self):
        """Adding connections to the buttons and checkboxes"""

    def populate_widgets(self):
        """Set the checkboxes and fill the custom commands line from the settings"""
        self.settings_group = BuildSettingsGroup(self, 'Settings')
        self.world_group = BuildSettingsGroup(self, 'World')
        self.physics_group = BuildSettingsGroup(self, 'Physics')
        self.nav_group = BuildSettingsGroup(self, 'Nav')
        self.ui.build_settings_content.layout().insertWidget(0, self.settings_group)
        # self.ui.build_settings_content.layout().insertWidget(0, self.world_group)
        # self.ui.build_settings_area.widget().layout().insertWidget(0, self.world_group)
        self.settings_group.group_content.layout().addWidget(self.world_group)
        self.settings_group.group_content.layout().addWidget(self.physics_group)
        self.settings_group.group_content.layout().addWidget(self.nav_group)
