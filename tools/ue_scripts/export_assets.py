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


def _select_export_paths(asset_infos, classes=_EXPORTABLE_CLASSES):
    """asset_infos: iterable of (object_path, class_name). Returns the object
    paths whose class is exportable — split out so it's testable without the
    `unreal` module, which only exists inside the Editor process."""
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
    Tries EditorAssetLibrary first, falling back to AssetRegistryHelpers."""
    # Method 1: EditorAssetLibrary (requires EditorScriptingUtilities plugin)
    if hasattr(unreal, "EditorAssetLibrary"):
        try:
            for object_path in unreal.EditorAssetLibrary.list_assets(content_path, recursive=True, include_folder=False):
                data = unreal.EditorAssetLibrary.find_asset_data(object_path)
                if data:
                    yield (str(object_path), _get_asset_class_name(data))
            return
        except Exception as e:
            if hasattr(unreal, "log_warning"):
                unreal.log_warning(f"EditorAssetLibrary failed ({e}), falling back to AssetRegistryHelpers")

    # Method 2: AssetRegistryHelpers (built-in to PythonScriptPlugin in UE4/UE5)
    if hasattr(unreal, "AssetRegistryHelpers"):
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        assets = registry.get_assets_by_path(content_path, recursive=True)
        for data in assets:
            obj_path = _get_asset_object_path(data)
            cls_name = _get_asset_class_name(data)
            if obj_path and cls_name:
                yield (obj_path, cls_name)
        return

    raise RuntimeError("Neither EditorAssetLibrary nor AssetRegistryHelpers is available in Unreal Python.")


def run(content_path: str = "/Game", output_dir: str = None):
    if not output_dir:
        raise ValueError("output_dir is required")
    import unreal  # only importable inside the UE Editor process

    infos = list(_list_assets(unreal, content_path))

    export_paths = _select_export_paths(infos)
    if not export_paths:
        unreal.log_warning(f"No StaticMesh/Texture2D assets found under {content_path}")
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
        run(os.environ.get("H5T_UE_CONTENT_PATH", "/Game"), os.environ.get("H5T_UE_OUTPUT_DIR"))
