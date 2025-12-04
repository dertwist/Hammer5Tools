"""
Preset management system for build configurations.
Handles saving, loading, and managing compilation presets.
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field, fields
import copy
from src.settings.common import get_settings_value, set_settings_value


@dataclass
class BuildSettings:
    """Complete build settings matching resourcecompiler.exe arguments"""

    # === Core Settings ===
    mappath: str = ""
    threads: int = -1  # -1 = auto-detect

    # === World Building ===
    build_world: bool = True
    entities_only: bool = False
    build_vis_geometry: bool = True

    no_settle: bool = False  # Physics settling

    # === Lightmapping ===
    bake_lighting: bool = True
    lightmap_max_resolution: int = 512
    lightmap_quality: int = 2  # 0=Low, 1=Medium, 2=High, 3=Ultra

    lightmap_compression: bool = True
    lightmap_filtering: bool = True  # Noise removal
    no_light_calculations: bool = False

    # === Physics ===
    build_physics: bool = False
    legacy_compile_collision_mesh: bool = False

    # === Visibility ===
    build_vis: bool = False
    debug_vis_geo: bool = False

    # === Navigation ===
    build_nav: bool = False
    nav_debug: bool = False
    grid_nav: bool = False

    # === Audio ===
    build_reverb: bool = False
    build_paths: bool = False
    bake_custom_audio: bool = False
    audio_threads: int = -1  # -1 = use main threads value

    # === Load Map In Engine ===
    load_in_engine_after_build: bool = True
    build_cubemaps_on_load: bool = True
    build_minimap_on_load: bool = False

    # === Base Arguments (usually fixed) ===
    fshallow: bool = True
    max_texture_res: int = 256
    dxlevel: int = 110
    quiet: bool = True
    unbuffered_io: bool = True
    no_assert: bool = True
    retail: bool = True
    breakpad: bool = True
    nop4: bool = True  # Disable Perforce

    def to_command_line(self, addon_path: str, cs2_path: str) -> str:
        """Convert settings to resourcecompiler.exe command line arguments"""

        # Determine if mappath is a file list
        is_filelist = self.mappath.lower().endswith(('.txt', '.lst'))
        input_flag = "-filelist" if is_filelist else "-i"

        # Build base command
        exe_path = Path(cs2_path) / "game" / "bin" / "win64" / "resourcecompiler.exe"
        quoted_exe = f'"{exe_path}"'
        quoted_map = f'"{self.mappath}"'

        args = []

        # Threads
        threads = self.threads if self.threads > 0 else os.cpu_count()
        args.append(f"-threads {threads}")

        # Base flags
        if self.fshallow:
            args.append("-fshallow")
        args.append(f"-maxtextureres {self.max_texture_res}")
        args.append(f"-dxlevel {self.dxlevel}")
        if self.quiet:
            args.append("-quiet")
        if self.unbuffered_io:
            args.append("-unbufferedio")
        if self.no_assert:
            args.append("-noassert")

        # Input file
        args.append(input_flag)
        args.append(quoted_map)

        # World vs Entities
        if self.entities_only:
            args.append("-entities")
        elif self.build_world:
            args.append("-world")

        # World settings
        if self.no_settle:
            args.append("-nosettle")
        # Lightmapping
        if self.bake_lighting and not self.entities_only:
            args.append("-bakelighting")
            args.append(f"-lightmapMaxResolution {self.lightmap_max_resolution}")

            args.append(f"-lightmapVRadQuality {self.lightmap_quality}")
            if not self.lightmap_filtering:
                args.append("-lightmapDisableFiltering")
            if not self.lightmap_compression:
                args.append("-lightmapCompressionDisabled")
            if self.no_light_calculations:
                args.append("-disableLightingCalculations")

        else:
            args.append("-nolightmaps")

        # Physics
        if self.build_physics:
            args.append("-phys")
            if self.legacy_compile_collision_mesh:
                args.append("-legacycompilecollisionmesh")

        # Visibility
        if self.build_vis:
            args.append("-vis")
        if self.debug_vis_geo:
            args.append("-debugvisgeo")

        # Navigation
        if self.build_nav:
            args.append("-nav")
            if self.nav_debug:
                args.append("-navdbg")
            if self.grid_nav:
                args.append("-gridnav")

        # Audio
        audio_threads = self.audio_threads if self.audio_threads > 0 else threads
        if self.build_reverb:
            args.append("-sareverb")
            args.append(f"-sareverb_threads {audio_threads}")
        if self.build_paths:
            args.append("-sapaths")
            args.append(f"-sapaths_threads {audio_threads}")
        if self.bake_custom_audio:
            args.append("-sacustomdata")
            args.append(f"-sacustomdata_threads {audio_threads}")

        # Logging/Diagnostics (removed deprecated options)

        # Outroot flags
        if self.retail:
            args.append("-retail")
        if self.breakpad:
            args.append("-breakpad")
        if self.nop4:
            args.append("-nop4")

        # Join all arguments
        cmd = f'{quoted_exe} {" ".join(args)}'
        return cmd


@dataclass
class BuildPreset:
    """A named preset containing build settings"""
    name: str
    settings: BuildSettings
    is_default: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "name": self.name,
            "settings": asdict(self.settings),
            "is_default": self.is_default,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BuildPreset':
        """Create from dict with filtering for unknown/removed keys"""
        settings_dict = data.get("settings", {})
        try:
            allowed = {f.name for f in fields(BuildSettings)}
            filtered = {k: v for k, v in settings_dict.items() if k in allowed}
            settings = BuildSettings(**filtered)
        except Exception:
            settings = BuildSettings()
        return cls(
            name=data["name"],
            settings=settings,
            is_default=data.get("is_default", False),
            description=data.get("description", "")
        )


class PresetManager:
    """Manages saving/loading of build presets from main settings"""

    SETTINGS_KEY = "MapBuilder/Presets"

    def __init__(self, presets_file: Path = None):
        """Initialize preset manager. presets_file is kept for backwards compatibility."""
        self.presets_file = presets_file
        self.presets: List[BuildPreset] = []
        self._load_presets()

    def _load_presets(self):
        """Load presets from main settings, with fallback to file if needed"""
        # Try to load from main settings first
        presets_json = get_settings_value("MapBuilder", "Presets", default=None)
        
        if presets_json:
            try:
                data = json.loads(presets_json)
                self.presets = [BuildPreset.from_dict(p) for p in data.get("presets", [])]
                return
            except Exception as e:
                print(f"Error loading presets from settings: {e}")
        
        # Fallback: try to load from old file if it exists
        if self.presets_file and self.presets_file.exists():
            try:
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.presets = [BuildPreset.from_dict(p) for p in data.get("presets", [])]
                    # Save to settings for future use
                    self.save_presets()
                    return
            except Exception as e:
                print(f"Error loading presets from file: {e}")
        
        # Create default presets if nothing found
        self._create_default_presets()

    def _create_default_presets(self):
        """Create default presets"""
        # Fast compile
        fast = BuildPreset(
            name="Fast Compile",
            is_default=True,
            description="Quick compile for testing geometry and gameplay",
            settings=BuildSettings(
                build_world=True,
                bake_lighting=False,
                build_physics=False,
                build_vis=False,
                build_nav=False,
                quiet=True
            )
        )

        # Full compile
        full = BuildPreset(
            name="Full Compile",
            is_default=True,
            description="Complete compile with all features",
            settings=BuildSettings(
                build_world=True,
                bake_lighting=True,
                lightmap_quality=2,
                build_physics=True,
                build_vis=True,
                build_nav=True,
                quiet=False
            )
        )

        # Lighting only
        lighting = BuildPreset(
            name="Lighting Only",
            is_default=True,
            description="Recompile lighting without rebuilding geometry",
            settings=BuildSettings(
                build_world=True,
                bake_lighting=True,
                lightmap_quality=3,
                build_physics=False,
                build_vis=False,
                build_nav=False
            )
        )

        # Entities only
        entities = BuildPreset(
            name="Entities Only",
            is_default=True,
            description="Update entities without recompiling world",
            settings=BuildSettings(
                entities_only=True,
                build_world=False,
                bake_lighting=False,
                build_physics=False,
                build_vis=False,
                build_nav=False
            )
        )

        self.presets = [fast, full, lighting, entities]
        self.save_presets()

    def save_presets(self):
        """Save presets to main settings"""
        try:
            data = {
                "presets": [p.to_dict() for p in self.presets]
            }
            presets_json = json.dumps(data)
            set_settings_value("MapBuilder", "Presets", presets_json)
        except Exception as e:
            print(f"Error saving presets: {e}")

    def add_preset(self, preset: BuildPreset) -> bool:
        """Add a new preset"""
        if any(p.name == preset.name for p in self.presets):
            return False
        self.presets.append(preset)
        self.save_presets()
        return True

    def delete_preset(self, name: str) -> bool:
        """Delete a preset (cannot delete default presets)"""
        preset = self.get_preset(name)
        if not preset or preset.is_default:
            return False
        self.presets = [p for p in self.presets if p.name != name]
        self.save_presets()
        return True

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """Rename a preset (cannot rename default presets)"""
        preset = self.get_preset(old_name)
        if not preset or preset.is_default:
            return False
        if any(p.name == new_name for p in self.presets):
            return False
        preset.name = new_name
        self.save_presets()
        return True

    def update_preset(self, name: str, settings: BuildSettings):
        """Update preset settings"""
        preset = self.get_preset(name)
        if preset:
            preset.settings = copy.deepcopy(settings)
            self.save_presets()

    def get_preset(self, name: str) -> Optional[BuildPreset]:
        """Get preset by name"""
        for p in self.presets:
            if p.name == name:
                return p
        return None

    def get_all_presets(self) -> List[BuildPreset]:
        """Get all presets"""
        return self.presets
