"""
Batch-export every StaticMesh / Texture2D under a UE content path — the same
operation as the Content Browser's Asset Actions -> Bulk Export, but for a
whole folder in one call instead of a manual multi-select.

Run inside the Unreal Editor's Python console (Window -> Developer Tools ->
Output Log, "Python" tab):

    import export_assets
    export_assets.run("/Game/FireWatchTower", r"D:/exports/firewatchtower")

Or headlessly via the Editor commandlet (what Hammer5Tools' "Run UE Export"
button does, see ue_export_runner.py) — content_path/output_dir come from the
H5T_UE_CONTENT_PATH / H5T_UE_OUTPUT_DIR env vars instead of call arguments:

    UnrealEditor-Cmd.exe MyProject.uproject -run=pythonscript -script="export_assets.py"

Point Hammer5Tools' Unreal Converter "UE Export cache folder" field at the
same output_dir afterwards (see src/forms/unreal_converter/main.py).

Meshes export with FbxExportOption.force_front_x_axis so the FBX declares +X as
its front axis instead of UE's default -Y, matching Source 2's forward vector.
Nanite meshes have Nanite switched off before export so the real geometry is
written rather than the fallback proxy — see _disable_nanite.

Progress is reported on stdout as "[H5T][level] text" lines; ue_export_runner.py
forwards only those (plus fatal engine errors) to the app console, so the
Editor's own logging never reaches the user.
"""

import os
import time

_EXPORTABLE_CLASSES = ("StaticMesh", "Texture2D")

# Every line meant for the user is printed with this tag. Inside the Editor,
# `print` lands in the engine log as "LogPython: [H5T][info] ...", which is how
# ue_export_runner.py picks our handful of lines out of the tens of thousands
# the Editor emits per run — see its _H5T pattern.
_TAG = "[H5T]"

# Set from the porter's "Nanite" model import option, and off by default. On, a
# Nanite mesh has Nanite switched off before it is exported so the real geometry
# is written; off, it exports as-is, which means Unreal's low-poly fallback
# proxy. Off is the default because the full-geometry path is what a first port
# spends nearly all of its time and disk on — measured on UE 5.7, rebuilding
# twelve meshes at source density cost 320s against 18s to export them, and grew
# the FBX from 7.5MB to 231MB. See _disable_nanite.
IMPORT_NANITE = (os.environ.get("H5T_UE_NANITE") or "0") != "0"

# How many Nanite meshes to switch off before exporting any of them. Clearing
# the flag queues that mesh's rebuild on UE's asset compilation pool, so a whole
# chunk builds in parallel, where flipping one mesh at a time blocks on each
# build in turn. Measured on UE 5.7 over two workload-balanced halves of six
# meshes each, ~4M triangles apiece: 2,496s one at a time against 1,294s
# batched, with the first mesh in the batch absorbing the wait and the other
# five returning already built.
#
# It is bounded because every mesh in a chunk is held at full source density at
# once, which is the memory this trades away. Only used when IMPORT_NANITE is
# on; otherwise nothing is flipped and the chunk is one mesh, exactly as before.
NANITE_BATCH = max(1, int(os.environ.get("H5T_UE_NANITE_BATCH") or 8))



def _say(message: str, level: str = "info") -> None:
    """Emit one user-facing line. Levels: info / warn / error / success.

    Routed through unreal.log_warning because that is the only emitter whose
    output reaches a commandlet's piped stdout. Measured on UE 5.7: a script's
    own `print` and `unreal.log` (Display verbosity) are both swallowed — the
    engine's own Display lines come through, a script's do not — while Warning
    verbosity arrives. The level the user sees is the one in the tag, not UE's,
    so an "info" line still reads as info in the app console.
    """
    line = f"{_TAG}[{level}] {message}"
    try:
        import unreal
    except ImportError:
        print(line, flush=True)     # outside the Editor, e.g. the self-check
        return
    unreal.log_warning(line)


def _human_size(num_bytes) -> str:
    """'45.3 MB'. Deliberately duplicated from gui/forms/cleanup/common.py —
    this module only ever executes inside the Unreal Editor's own Python, which
    has none of the app on its path."""
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.2f} GB"


def _human_time(seconds: float) -> str:
    """'3m 12s'."""
    seconds = int(seconds)
    return f"{seconds // 60}m {seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s"

# Maps routinely place engine content that lives outside /Game — the default
# template floor (/Engine/MapTemplates/SM_Template_Map_Floor) is in every map
# made from a UE template, and BasicShapes are common greyboxing props. Without
# these roots the converter writes a vmdl pointing at a mesh nobody exported.
# /Engine as a whole is thousands of assets, so only the roots that actually
DEFAULT_CONTENT_PATHS = "/Game;/Engine/MapTemplates;/Engine/BasicShapes"


def _split_paths(content_path: str) -> list:
    """'/Game;/Engine/MapTemplates' -> ['/Game', '/Engine/MapTemplates'].
    Accepts ';' or ',' so the env var is forgiving about separators."""
    if not content_path:
        return []
    parts = content_path.replace(",", ";").split(";")
    seen, out = set(), []
    for p in parts:
        p = p.strip().rstrip("/")
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out


def _asset_stem(path: str) -> str:
    """'/Game/Meshes/SM_Chair.SM_Chair' or 'Meshes/SM_Chair.uasset' -> 'sm_chair'"""
    filename = os.path.basename(path).replace("\\", "/")
    return filename.split(".", 1)[0].lower()


def _select_export_paths(asset_infos, classes=_EXPORTABLE_CLASSES, asset_filter=None):
    """asset_infos: iterable of (object_path, class_name). Returns the object
    paths whose class is exportable. If asset_filter set is provided, only
    returns paths whose lowercased stem or object path matches the filter.

    The filter comes from the user's port scope, which is a listing of the
    *project* — engine content can never appear in it. So engine roots are
    exempt from it; they are a couple of dozen assets in total, and filtering
    them is indistinguishable from not exporting them at all."""
    if asset_filter:
        allowed = {str(item).replace("\\", "/").lower() for item in asset_filter if item}
        allowed_stems = {_asset_stem(item) for item in allowed}
        res = []
        for path, cls in asset_infos:
            if cls not in classes:
                continue
            path_low = path.replace("\\", "/").lower()
            stem_low = _asset_stem(path)
            if (not path_low.startswith("/game/")
                    or stem_low in allowed_stems or path_low in allowed
                    or any(path_low.endswith(x) for x in allowed)):
                res.append(path)
        return res
    return [path for path, cls in asset_infos if cls in classes]


def _get_asset_class_name(data) -> str:
    """Extract class name string from unreal.AssetData in a way compatible with both UE4 (4.27) and UE5."""
    if hasattr(data, "asset_class_path") and data.asset_class_path is not None:
        asset_name = getattr(data.asset_class_path, "asset_name", None)
        if asset_name is not None:
            return str(asset_name)
    if hasattr(data, "asset_class"):
        return str(data.asset_class)
    return ""


def _get_asset_object_path(data) -> str:
    """Extract object path from unreal.AssetData (e.g. '/Game/Folder/Asset.Asset')."""
    if hasattr(data, "object_path") and data.object_path:
        return str(data.object_path)
    pkg = getattr(data, "package_name", "")
    name = getattr(data, "asset_name", "")
    if pkg and name:
        return f"{pkg}.{name}"
    return str(getattr(data, "package_name", ""))


def _is_valid_asset(unreal, data) -> bool:
    """Check if the asset file exists on disk and is non-empty (at least 32 bytes for valid UE package summary)."""
    disk_path = None
    try:
        if hasattr(unreal, "SystemLibrary") and hasattr(unreal.SystemLibrary, "get_system_path"):
            disk_path = unreal.SystemLibrary.get_system_path(data)
    except Exception:
        disk_path = None

    if not disk_path:
        pkg = str(getattr(data, "package_name", ""))
        if pkg and hasattr(unreal, "Paths"):
            try:
                rel_path = unreal.Paths.convert_relative_path_to_full(pkg + ".uasset")
                if rel_path:
                    disk_path = rel_path
            except Exception:
                pass

    if disk_path and os.path.isfile(disk_path):
        try:
            if os.path.getsize(disk_path) < 32:
                return False
        except OSError:
            return False

    return True


def _list_assets(unreal, content_path: str):
    """Yields (object_path, class_name) for assets under content_path.

    The scan is not optional. A commandlet's asset registry comes up holding
    /Game and the handful of engine folders the editor always scans (BasicShapes
    is one, MapTemplates is not), so listing /Engine/MapTemplates without asking
    for it first returns zero assets and the map's template floor silently never
    exports. It is asked for with force_rescan=False so that it really is the
    no-op this comment always claimed for an already-scanned path — forcing it
    made every run re-walk the whole of /Game from disk before exporting a
    single asset.
    """
    if not hasattr(unreal, "AssetRegistryHelpers"):
        raise RuntimeError("AssetRegistryHelpers is not available in Unreal Python.")

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        registry.scan_paths_synchronous([content_path], force_rescan=False)
    except Exception as e:
        unreal.log_warning(f"Error scanning path {content_path}: {e}")

    try:
        assets_data = registry.get_assets_by_path(content_path, recursive=True)
    except Exception as e:
        unreal.log_warning(f"Error listing assets under {content_path}: {e}")
        return

    for data in assets_data:
        try:
            cls_name = _get_asset_class_name(data)
            # Class first: _is_valid_asset stats the package on disk, and a
            # project is overwhelmingly made of things we never export
            # (materials, blueprints, curves, data assets). Checking those was
            # three syscalls each for an answer nobody used.
            if cls_name not in _EXPORTABLE_CLASSES:
                continue
            if not _is_valid_asset(unreal, data):
                obj_path = _get_asset_object_path(data)
                unreal.log_warning(f"Skipping corrupt or empty asset file: {obj_path or data}")
                continue
            obj_path = _get_asset_object_path(data)
            if obj_path:
                yield (obj_path, cls_name)
        except Exception as e:
            unreal.log_warning(f"Skipping asset entry due to error: {e}")
            continue


def _export_filename(object_path: str, output_dir: str, ext: str = ".fbx") -> str:
    """'/Game/Meshes/SM_Chair.SM_Chair' -> '<output_dir>/Game/Meshes/SM_Chair.fbx'.

    Reproduces the layout AssetTools.export_assets writes, which the converter's
    cache scan depends on (ENGINE_EXPORT_ROOTS in src/forms/unreal_porter/main.py
    looks for '<cache>/Engine/BasicShapes' by name)."""
    package = object_path.rsplit(".", 1)[0]
    return os.path.join(output_dir, package.lstrip("/").replace("/", os.sep)) + ext


def _asset_filename(object_path: str, ext: str) -> str:
    """'/Game/Meshes/SM_Chair.SM_Chair' -> 'SM_Chair.fbx' — the file written.

    Mirrors _export_filename's stem, without _asset_stem's lowercasing: this one
    is read by a person looking for the asset in the Content Browser, and Unreal
    asset names are case-sensitive there.
    """
    return os.path.basename(object_path).split(".", 1)[0] + ext


def _nanite_settings(mesh):
    """A StaticMesh's MeshNaniteSettings when Nanite is on, else None."""
    try:
        settings = mesh.get_editor_property("nanite_settings")
    except Exception:
        return None
    try:
        return settings if bool(settings.get_editor_property("enabled")) else None
    except Exception:
        return None


def _disable_nanite(unreal, mesh):
    """Switch Nanite off on a mesh so its full geometry can be exported.

    FBX export writes LOD0 *render* data, and on a Nanite mesh that is the
    auto-generated fallback proxy rather than the virtualized geometry. Measured
    on UE 5.7 against a marketplace fence pack, the fallback carried under a
    tenth of the real mesh (6,664 of 69,261 triangles), which is why this tool
    used to tell people to disable Nanite and re-export by hand.

    Setting `enabled` is the whole operation: get_editor_property hands back a
    live reference to the mesh's MeshNaniteSettings, not a copy, so writing to
    it changes the mesh, and the render data is rebuilt from the source mesh on
    the next access — which is the export. StaticMeshEditorSubsystem is NOT used
    for this: get_editor_subsystem returns None in a commandlet, because a
    commandlet has no editor, so anything routed through it silently did nothing.

    Returns a callable that switches Nanite back on, or None if this is not a
    Nanite mesh. The change is in-memory only — the commandlet never saves, so
    the .uasset on disk is untouched either way.
    """
    settings = _nanite_settings(mesh)
    if settings is None:
        return None
    try:
        settings.set_editor_property("enabled", False)
    except Exception as e:
        unreal.log_warning(f"Could not switch Nanite off: {e}")
        return None

    def restore():
        try:
            settings.set_editor_property("enabled", True)
        except Exception:
            pass

    return restore


def _chunks(items, size):
    """Yield successive lists of at most `size` items."""
    items = list(items)
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _begin_nanite_chunk(unreal, paths):
    """Switch Nanite off across a whole chunk so UE builds them in parallel.

    Returns (restores, flipped_paths). The paths are needed because once the
    flag is off _nanite_settings reports the mesh as not-Nanite, so this is the
    only record that it ever was. Loading an asset here is what the export loop
    does moments later and unreal.load_asset is cached, so this costs the flips
    and nothing else.
    """
    restores, flipped = [], set()
    for path in paths:
        try:
            asset = unreal.load_asset(path)
        except Exception:
            continue
        if not isinstance(asset, unreal.StaticMesh):
            continue
        restore = _disable_nanite(unreal, asset)
        if restore is not None:
            restores.append(restore)
            flipped.add(path)
    return restores, flipped


def _export_one(unreal, path, asset, output_dir, options=None, ext=".fbx") -> int:
    """Export one asset; returns the bytes written, or 0 if nothing was written."""
    filename = _export_filename(path, output_dir, ext=ext)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    task = unreal.AssetExportTask()
    task.set_editor_property("object", asset)
    task.set_editor_property("filename", filename)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    if options is not None:
        task.set_editor_property("options", options)
    if not unreal.Exporter.run_asset_export_task(task):
        return 0
    try:
        return os.path.getsize(filename)
    except OSError:
        return 0


def _tally(unreal, path, name, written, counters, sizes):
    """Fold one export result into the running counters dict."""
    if not written:
        counters["failed"] += 1
        unreal.log_warning(f"Export failed for {path}")
        return
    counters["exported"] += 1
    counters["bytes"] += written
    sizes.append((written, name))


# How often the running "Exported n/total - size" line is printed.
_PROGRESS_INTERVAL_SECONDS = 2.0


def _export_assets(unreal, export_paths, output_dir):
    """Export every path, returning (exported_count, total_bytes).

    Load and export in the same pass. The old code loaded every asset in the
    project up front and held them all live while exporting, which on a
    Nanite-heavy pack is gigabytes resident and a long collection at the end;
    one at a time lets the Editor drop each asset again, and is what makes a
    running progress line possible at all.

    StaticMeshes and Texture2Ds go one at a time through AssetExportTask so that
    (1) meshes use FbxExportOption.force_front_x_axis for Source 2 forward alignment, and
    (2) textures export reliably in headless / commandlet mode without requiring GUI interaction.
    """
    export_paths = list(export_paths)
    if not hasattr(unreal, "AssetExportTask"):
        try:
            unreal.AssetToolsHelpers.get_asset_tools().export_assets(export_paths, output_dir)
            return len(export_paths), 0
        except Exception as e:
            _say(f"Batch export failed: {e}", "error")
            return 0, 0

    options = None
    if hasattr(unreal, "FbxExportOption"):
        options = unreal.FbxExportOption()
        options.set_editor_property("force_front_x_axis", True)
    else:
        _say("This Unreal build has no FbxExportOption, so meshes export with UE's "
             "default -Y front axis and will come into Hammer yawed 90 degrees.", "warn")

    total = len(export_paths)
    counters = {"exported": 0, "bytes": 0, "failed": 0, "nanite": 0}
    sizes = []          # (bytes, name), for the largest-assets report
    others = []         # exportable class we do not special-case; batched at the end
    last_report = time.time()

    index = 0
    # One mesh per chunk unless Nanite meshes are being brought across at full
    # geometry, in which case the chunk exists so their rebuilds overlap.
    for chunk in _chunks(export_paths, NANITE_BATCH if IMPORT_NANITE else 1):
        restores, flipped = _begin_nanite_chunk(unreal, chunk) if IMPORT_NANITE else ([], set())
        try:
            for path in chunk:
                index += 1
                try:
                    asset = unreal.load_asset(path)
                except Exception as e:
                    unreal.log_warning(f"Failed to load asset {path} (skipped): {e}")
                    asset = None

                name, written = os.path.basename(path), 0
                if asset is None:
                    counters["failed"] += 1
                elif isinstance(asset, unreal.StaticMesh):
                    name = _asset_filename(path, ".fbx")
                    # Nanite was already switched off for this chunk if it was
                    # wanted, which is exactly why _nanite_settings can no
                    # longer tell: `flipped` is the record of what it found.
                    if path in flipped or _nanite_settings(asset) is not None:
                        counters["nanite"] += 1
                    try:
                        written = _export_one(unreal, path, asset, output_dir, options, ".fbx")
                    except Exception as e:
                        unreal.log_warning(f"Error exporting mesh {path}: {e}")
                        written = 0
                    _tally(unreal, path, name, written, counters, sizes)
                elif isinstance(asset, unreal.Texture2D):
                    name = _asset_filename(path, ".tga")
                    try:
                        written = _export_one(unreal, path, asset, output_dir, None, ".tga")
                    except Exception as e:
                        unreal.log_warning(f"Error exporting texture {path}: {e}")
                        written = 0
                    _tally(unreal, path, name, written, counters, sizes)
                else:
                    others.append(path)

                now = time.time()
                if index == total or now - last_report >= _PROGRESS_INTERVAL_SECONDS:
                    last_report = now
                    # The asset is named because the interesting question during
                    # a long export is which one the size jumped on — a total
                    # alone cannot say.
                    _say(f"Exported {index}/{total}  {name}  {_human_size(written)}"
                         f"  (total {_human_size(counters['bytes'])})")
        finally:
            for restore in restores:
                restore()

    if others:
        try:
            unreal.AssetToolsHelpers.get_asset_tools().export_assets(others, output_dir)
            counters["exported"] += len(others)
        except Exception as e:
            _say(f"Batch export of {len(others)} other asset(s) failed: {e}", "warn")

    if counters["nanite"] and IMPORT_NANITE:
        _say(f"{counters['nanite']} Nanite mesh(es) exported at full geometry "
             "(Nanite switched off for the export).")
    elif counters["nanite"]:
        _say(f"{counters['nanite']} Nanite mesh(es) exported as Unreal's low-poly "
             "fallback proxy; tick Models > Nanite for their full geometry.")
    if counters["failed"]:
        _say(f"{counters['failed']} asset(s) produced no file; see the Unreal log.", "warn")
    if sizes:
        sizes.sort(reverse=True)
        _say("Largest: " + ", ".join(f"{name} {_human_size(n)}" for n, name in sizes[:5]))
    return counters["exported"], counters["bytes"]


def run(content_path: str = DEFAULT_CONTENT_PATHS, output_dir: str = None):
    """content_path may name several roots, ';'-separated — see
    DEFAULT_CONTENT_PATHS. Roots that don't exist in this project are skipped
    with a warning rather than failing the whole export."""
    if not output_dir:
        raise ValueError("output_dir is required")
    import unreal  # only importable inside the UE Editor process

    started = time.time()
    infos = []
    for root in _split_paths(content_path):
        try:
            found = list(_list_assets(unreal, root))
        except Exception as e:
            _say(f"Skipping content path {root}: {e}", "warn")
            continue
        if not found:
            unreal.log_warning(f"No assets found under {root}")
        infos.extend(found)

    asset_list_raw = os.environ.get("H5T_UE_ASSET_LIST")
    asset_filter = set(asset_list_raw.replace(",", ";").split(";")) if asset_list_raw else None

    export_paths = _select_export_paths(infos, asset_filter=asset_filter)
    if not export_paths:
        _say(f"No StaticMesh/Texture2D assets matched under {content_path}.", "warn")
        return

    _say(f"{len(export_paths)} asset(s) to export into {output_dir}")
    ok, total_bytes = _export_assets(unreal, export_paths, output_dir)
    _say(f"Exported {ok}/{len(export_paths)} asset(s), {_human_size(total_bytes)}, "
         f"in {_human_time(time.time() - started)}",
         "success" if ok == len(export_paths) else "warn")


class DummyAssetDataUE4:
    def __init__(self, cls_name, pkg="/Game/A", name="A"):
        self.asset_class = cls_name
        self.package_name = pkg
        self.asset_name = name


class DummyAssetClassPath:
    def __init__(self, asset_name):
        self.asset_name = asset_name


class DummyAssetDataUE5:
    def __init__(self, asset_name, obj_path="/Game/B.B"):
        self.asset_class_path = DummyAssetClassPath(asset_name)
        self.object_path = obj_path


class DummySettings:
    """Stands in for MeshNaniteSettings, which UE hands back by reference."""

    def __init__(self, props, writable=True):
        self.props = props
        self.writable = writable

    def get_editor_property(self, name):
        if name not in self.props:
            raise Exception(f"no such property {name}")
        return self.props[name]

    def set_editor_property(self, name, value):
        if not self.writable:
            raise Exception("read-only")
        self.props[name] = value


class DummyMesh:
    def __init__(self, enabled=True, writable=True):
        self.settings = DummySettings({"enabled": enabled}, writable)

    def get_editor_property(self, name):
        assert name == "nanite_settings"
        return self.settings


class DummyUnreal:
    """Just enough of the `unreal` module for the Nanite path."""

    @staticmethod
    def log_warning(message):
        pass


def demo():
    data_ue4 = DummyAssetDataUE4("StaticMesh")
    data_ue5 = DummyAssetDataUE5("Texture2D")
    assert _get_asset_class_name(data_ue4) == "StaticMesh"
    assert _get_asset_class_name(data_ue5) == "Texture2D"
    assert _get_asset_object_path(data_ue4) == "/Game/A.A"
    assert _get_asset_object_path(data_ue5) == "/Game/B.B"

    assert _select_export_paths([
        ("/Game/A", "StaticMesh"),
        ("/Game/B", "Texture2D"),
        ("/Game/C", "MaterialInstanceConstant"),
    ]) == ["/Game/A", "/Game/B"]

    # A port scope narrows /Game but must never narrow engine content: the scope
    # is a listing of the project, so no engine asset can ever match it.
    scoped = _select_export_paths([
        ("/Game/Meshes/SM_Chair.SM_Chair", "StaticMesh"),
        ("/Game/Meshes/SM_Table.SM_Table", "StaticMesh"),
        ("/Engine/MapTemplates/SM_Template_Map_Floor.SM_Template_Map_Floor", "StaticMesh"),
        ("/Engine/BasicShapes/Cube.Cube", "StaticMesh"),
        ("/Engine/MapTemplates/M_Thing.M_Thing", "MaterialInstanceConstant"),
    ], asset_filter={"P/Content/Meshes/SM_Chair.uasset"})
    assert scoped == [
        "/Game/Meshes/SM_Chair.SM_Chair",
        "/Engine/MapTemplates/SM_Template_Map_Floor.SM_Template_Map_Floor",
        "/Engine/BasicShapes/Cube.Cube",
    ], scoped

    assert _split_paths("/Game") == ["/Game"]
    assert _split_paths(DEFAULT_CONTENT_PATHS) == [
        "/Game", "/Engine/MapTemplates", "/Engine/BasicShapes"]
    # Engine content must survive: a map built from a UE template places
    # /Engine/MapTemplates/SM_Template_Map_Floor and nothing else exports it.
    assert "/Engine/MapTemplates" in _split_paths(DEFAULT_CONTENT_PATHS)
    assert _split_paths("/Game, /Engine/MapTemplates/") == ["/Game", "/Engine/MapTemplates"]
    assert _split_paths("/Game;/game") == ["/Game"], "duplicate roots collapse"
    assert _split_paths("") == []

    # The export path has to land where the converter's cache scan looks —
    # '<cache>/Engine/BasicShapes' is matched by directory name, not by search.
    out = os.path.join("D:", os.sep, "cache")
    assert _export_filename("/Game/Meshes/SM_Chair.SM_Chair", out) == os.path.join(
        out, "Game", "Meshes", "SM_Chair.fbx")
    assert _export_filename("/Engine/BasicShapes/Cube.Cube", out) == os.path.join(
        out, "Engine", "BasicShapes", "Cube.fbx")

    # Names reach the console with their real case and the extension actually
    # written, so they can be pasted into the Content Browser.
    assert _asset_filename("/Game/Meshes/SM_Chair.SM_Chair", ".fbx") == "SM_Chair.fbx"
    assert _asset_filename("/Game/Fences/SM_Fence_Dune_NN_01i.SM_Fence_Dune_NN_01i",
                           ".fbx") == "SM_Fence_Dune_NN_01i.fbx"
    assert _asset_filename("/Game/Tex/T_Rock_D.T_Rock_D", ".tga") == "T_Rock_D.tga"

    assert list(_chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert list(_chunks([1, 2, 3], 1)) == [[1], [2], [3]], "chunk of 1 is the old loop"
    assert list(_chunks([], 8)) == []

    # A chunk flips every Nanite mesh in it and reports which, because once the
    # flag is off _nanite_settings can no longer say a mesh ever had it.
    class _FakeUnreal(DummyUnreal):
        StaticMesh = DummyMesh

        def __init__(self, assets):
            self._assets = assets

        def load_asset(self, path):
            return self._assets[path]

    nan, plain = DummyMesh(enabled=True), DummyMesh(enabled=False)
    fake = _FakeUnreal({"a": nan, "b": plain})
    restores, flipped = _begin_nanite_chunk(fake, ["a", "b"])
    assert flipped == {"a"}, flipped
    assert nan.settings.props["enabled"] is False
    assert plain.settings.props["enabled"] is False, "a non-Nanite mesh is untouched"
    for r in restores:
        r()
    assert nan.settings.props["enabled"] is True

    assert _human_size(0) == "0 B"
    assert _human_size(1536) == "1.5 KB"
    assert _human_size(47 * 1024 * 1024) == "47.0 MB"
    assert _human_size(3 * 1024 ** 3) == "3.00 GB"
    assert _human_time(9) == "9s"
    assert _human_time(192) == "3m 12s"

    # A Nanite mesh has Nanite switched off for the export and switched back on
    # afterwards; a mesh that never had it is left completely alone.
    plain = DummyMesh(enabled=False)
    assert _disable_nanite(DummyUnreal(), plain) is None
    assert plain.settings.props["enabled"] is False

    mesh = DummyMesh(enabled=True)
    restore = _disable_nanite(DummyUnreal(), mesh)
    assert restore is not None
    assert mesh.settings.props["enabled"] is False, "the export must see Nanite off"
    restore()
    assert mesh.settings.props["enabled"] is True, "the project must be left as found"

    # A mesh that refuses the write is reported as not handled rather than
    # exported as though the switch had worked.
    stubborn = DummyMesh(enabled=True, writable=False)
    assert _disable_nanite(DummyUnreal(), stubborn) is None
    print("ok")


if __name__ == "__main__":
    # `unreal` only importable when this file is executed inside the Editor
    # process (Python console or -run=pythonscript) — everywhere else (a
    # plain `python export_assets.py`, including the self-check above) it
    # isn't installed, which is exactly the signal to run demo() instead.
    try:
        import unreal  # noqa: F401
    except ImportError:
        demo()
    else:
        run(os.environ.get("H5T_UE_CONTENT_PATH") or DEFAULT_CONTENT_PATHS,
            os.environ.get("H5T_UE_OUTPUT_DIR"))
