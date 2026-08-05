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
    registry.scan_paths_synchronous([content_path], force_rescan=True)
    for data in registry.get_assets_by_path(content_path, recursive=True):
        obj_path = _get_asset_object_path(data)
        cls_name = _get_asset_class_name(data)
        if obj_path and cls_name:
            yield (obj_path, cls_name)


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
        unreal.log_warning(f"No StaticMesh/Texture2D assets found matching criteria under {content_path}")
        return

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.export_assets(export_paths, output_dir)
    unreal.log(f"Exported {len(export_paths)} asset(s) to {output_dir}")


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
