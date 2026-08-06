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
"""

import os

_EXPORTABLE_CLASSES = ("StaticMesh", "Texture2D")

# Maps routinely place engine content that lives outside /Game — the default
# template floor (/Engine/MapTemplates/SM_Template_Map_Floor) is in every map
# made from a UE template, and BasicShapes are common greyboxing props. Without
# these roots the converter writes a vmdl pointing at a mesh nobody exported.
# /Engine as a whole is thousands of assets, so only the roots that actually
# get placed in levels are included.
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
    exports. scan_paths_synchronous is a no-op for a path already scanned.
    """
    if not hasattr(unreal, "AssetRegistryHelpers"):
        raise RuntimeError("AssetRegistryHelpers is not available in Unreal Python.")

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        registry.scan_paths_synchronous([content_path], force_rescan=True)
    except Exception as e:
        unreal.log_warning(f"Error scanning path {content_path}: {e}")

    try:
        assets_data = registry.get_assets_by_path(content_path, recursive=True)
    except Exception as e:
        unreal.log_warning(f"Error listing assets under {content_path}: {e}")
        return

    for data in assets_data:
        try:
            if not _is_valid_asset(unreal, data):
                obj_path = _get_asset_object_path(data)
                unreal.log_warning(f"Skipping corrupt or empty asset file: {obj_path or data}")
                continue
            obj_path = _get_asset_object_path(data)
            cls_name = _get_asset_class_name(data)
            if obj_path and cls_name:
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


def _export_assets(unreal, export_paths, output_dir) -> int:
    """Export every path, returning how many succeeded.

    StaticMeshes and Texture2Ds go one at a time through AssetExportTask so that
    (1) meshes use FbxExportOption.force_front_x_axis for Source 2 forward alignment, and
    (2) textures export reliably in headless / commandlet mode without requiring GUI interaction.
    """
    meshes, textures, others = [], [], []
    has_tasks = hasattr(unreal, "AssetExportTask")

    for path in export_paths:
        try:
            asset = unreal.load_asset(path) if has_tasks else None
        except Exception as e:
            unreal.log_warning(f"Failed to load asset {path} (skipped): {e}")
            continue

        if asset is not None:
            if isinstance(asset, unreal.StaticMesh):
                meshes.append((path, asset))
                continue
            elif isinstance(asset, unreal.Texture2D):
                textures.append((path, asset))
                continue
            others.append(path)
        else:
            if has_tasks:
                unreal.log_warning(f"Could not load asset {path} (skipped)")
            else:
                others.append(path)

    if has_tasks and not hasattr(unreal, "FbxExportOption"):
        unreal.log_warning(
            "This Unreal build has no FbxExportOption — meshes export with UE's default "
            "-Y front axis and will come into Hammer yawed 90 degrees."
        )

    exported = 0
    if meshes:
        options = unreal.FbxExportOption() if hasattr(unreal, "FbxExportOption") else None
        if options:
            options.set_editor_property("force_front_x_axis", True)
        for path, asset in meshes:
            try:
                filename = _export_filename(path, output_dir, ext=".fbx")
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                task = unreal.AssetExportTask()
                task.set_editor_property("object", asset)
                task.set_editor_property("filename", filename)
                task.set_editor_property("automated", True)
                task.set_editor_property("prompt", False)
                task.set_editor_property("replace_identical", True)
                if options:
                    task.set_editor_property("options", options)
                if unreal.Exporter.run_asset_export_task(task):
                    exported += 1
                else:
                    unreal.log_warning(f"Export failed for mesh {path}")
            except Exception as e:
                unreal.log_warning(f"Error exporting mesh {path}: {e}")

    if textures:
        for path, asset in textures:
            try:
                filename = _export_filename(path, output_dir, ext=".tga")
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                task = unreal.AssetExportTask()
                task.set_editor_property("object", asset)
                task.set_editor_property("filename", filename)
                task.set_editor_property("automated", True)
                task.set_editor_property("prompt", False)
                task.set_editor_property("replace_identical", True)
                if unreal.Exporter.run_asset_export_task(task):
                    exported += 1
                else:
                    unreal.log_warning(f"Export failed for texture {path}")
            except Exception as e:
                unreal.log_warning(f"Error exporting texture {path}: {e}")

    if others:
        try:
            unreal.AssetToolsHelpers.get_asset_tools().export_assets(others, output_dir)
            exported += len(others)
        except Exception as e:
            unreal.log_warning(f"Error exporting assets batch: {e}")
    return exported


def run(content_path: str = DEFAULT_CONTENT_PATHS, output_dir: str = None):
    """content_path may name several roots, ';'-separated — see
    DEFAULT_CONTENT_PATHS. Roots that don't exist in this project are skipped
    with a warning rather than failing the whole export."""
    if not output_dir:
        raise ValueError("output_dir is required")
    import unreal  # only importable inside the UE Editor process

    infos = []
    for root in _split_paths(content_path):
        try:
            found = list(_list_assets(unreal, root))
        except Exception as e:
            unreal.log_warning(f"Skipping content path {root}: {e}")
            continue
        if not found:
            unreal.log_warning(f"No assets found under {root}")
        infos.extend(found)

    asset_list_raw = os.environ.get("H5T_UE_ASSET_LIST")
    asset_filter = set(asset_list_raw.replace(",", ";").split(";")) if asset_list_raw else None

    export_paths = _select_export_paths(infos, asset_filter=asset_filter)
    if not export_paths:
        msg = f"[H5T_EXPORT_COMPLETE] No StaticMesh/Texture2D assets found matching criteria under {content_path}"
        unreal.log_warning(msg)
        print(msg, flush=True)
        return

    ok = _export_assets(unreal, export_paths, output_dir)
    msg = f"[H5T_EXPORT_COMPLETE] Exported {ok}/{len(export_paths)} asset(s) to {output_dir}"
    unreal.log(msg)
    print(msg, flush=True)


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
