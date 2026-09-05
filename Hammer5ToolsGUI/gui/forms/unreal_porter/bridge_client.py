"""
Python client for the Unreal content bridge.

Reads Unreal `.uasset` / `.umap` files (the raw project) through the
Hammer5Tools.Core NativeAOT ABI — no subprocess, no separate .NET runtime
invocation. Used for the "entity" half of the hybrid migration (scenes,
blueprints, material params); meshes/textures come from a UE bulk-export
folder instead.
"""

from __future__ import annotations

import os
from typing import Any


class BridgeError(RuntimeError):
    pass


# Packages that exist only to serve the Editor and hold nothing portable.
# "_BuiltData" is the MapBuildDataRegistry Unreal writes beside every map: it
# carries baked lightmaps and nothing else, so listing it only ever costs a
# reference scan and a slot in the port scope.
_IGNORED_ASSET_SUFFIXES = ("_builtdata",)


def is_ignored_asset(key: str) -> bool:
    """Editor-only packages that must never reach the asset list or a scan."""
    stem = os.path.splitext(os.path.basename(str(key).replace("\\", "/")))[0].lower()
    return stem.endswith(_IGNORED_ASSET_SUFFIXES)


class UnrealBridge:
    """Thin wrapper over CoreBridge's ``unreal_*`` calls."""

    def __init__(self, content_dir: str):
        self.content_dir = content_dir

    def is_available(self) -> bool:
        from core.bridge import CoreBridge

        return CoreBridge.instance().probe().available

    def why_unavailable(self) -> str:
        from core.bridge import CoreBridge

        status = CoreBridge.instance().probe()
        return "" if status.available else (status.diagnostic or "Hammer5Tools Core is unavailable.")

    def _bridge(self):
        if not self.is_available():
            raise BridgeError(self.why_unavailable())
        from core.bridge import CoreBridge

        return CoreBridge.instance()

    def _call(self, method: str, *args):
        """Invoke a Core Unreal API and expose native failures as BridgeError."""
        from core.native import NativeCoreError

        try:
            return getattr(self._bridge(), method)(self.content_dir, *args)
        except NativeCoreError as e:
            raise BridgeError(str(e)) from e

    # commands

    def reset(self) -> None:
        """Drop Core's cached project mount before re-reading the project.

        Core keeps one mounted provider so a scan pays for the content walk once
        instead of once per asset; that mount has to be dropped when the project
        may have changed on disk, or Re-analyze would replay the file set the
        first analysis saw.
        """
        from core.native import NativeCoreError

        try:
            self._bridge().unreal_reset()
        except NativeCoreError as e:
            raise BridgeError(str(e)) from e

    def info(self) -> dict:
        return self._call("unreal_info")

    def list(self, substring: str = "") -> list:
        return self.list_counted(substring)[0]

    def list_counted(self, substring: str = "") -> tuple:
        """(assets, ignored) — the listing plus how many entries were dropped.

        The truncation check compares the listing against the bridge's own
        totalFiles, so anything filtered out here has to be reported or an
        intact project reads as a cut-off one.
        """
        raw = self._call("unreal_list", substring)
        kept = [k for k in raw if not is_ignored_asset(k)]
        return kept, len(raw) - len(kept)

    def list_materials(self) -> list:
        """Find all Material / MaterialInstance .uasset keys under the project,
        regardless of exact subfolder layout (e.g. Materials/ or Environment/...)."""
        all_keys = self.list("")
        mat_keys = []
        for k in all_keys:
            lk = k.lower()
            if not lk.endswith(".uasset") or lk.endswith(".umap"):
                continue
            filename = os.path.basename(lk)
            if (any(x in lk for x in ("/materials/", "/material/", "/material_instances/", "/mi/", "/mastermaterials/", "/inst/", "/m/"))
                or filename.startswith(("mi_", "m_", "mm_", "mat_"))
                or "material" in filename):
                mat_keys.append(k)
        if not mat_keys:
            mat_keys = [k for k in all_keys if k.lower().endswith(".uasset") and not k.lower().endswith(".umap")]
        return mat_keys

    def dump(self, object_path: str) -> Any:
        return self._call("unreal_dump", object_path)

    def iter_refs(self, object_path: str, timeout: int = 600, is_cancelled=None) -> set:
        """Every object reference in an asset.

        The native package walk has no cancellation points, so cancellation
        takes effect between assets rather than during an in-flight call.
        """
        if is_cancelled is not None and is_cancelled():
            raise BridgeError("bridge 'iter_refs' cancelled")
        return set(self._call("unreal_iter_refs", object_path))

    def dump_scene(self, map_path: str) -> dict:
        """Normalized actor list: {map, count, actors:[{actor, componentType,
        mesh, location, rotation, scale}]} — transforms are in UE space."""
        return self._call("unreal_dump_scene", map_path)

    def dump_blueprint(self, bp_path: str) -> dict:
        """Normalized blueprint component tree: {blueprint, count, components:[{name,
        componentType, mesh, parent, location, rotation, scale}]} — transforms in UE space."""
        return self._call("unreal_dump_blueprint", bp_path)

    def export_landscape(self, map_path: str, out_dir: str, flags: str = "mesh") -> dict:
        """Export the map's (first) landscape actor as an OBJ mesh into out_dir.

        flags: "mesh" (just the OBJ — what the Scenes/Models pipeline uses),
        "heightmap", "weightmap", or "all". Returns {ok, components, label,
        saved} where `saved` is the absolute path of the exported OBJ.
        Raises BridgeError (message starts with "NO_LANDSCAPE") if the map has
        no landscape actor with components.
        """
        return self._call("unreal_export_landscape", map_path, out_dir, flags)

    def dump_material(self, mat_path: str) -> dict:
        """Normalized material instance properties: {material, parent, textures,
        scalars, vectors, switches}. `switches` are the MI's static-switch bools
        (e.g. "Use Normal Map") — a signal for whether a param even applies,
        not currently used to gate slot selection but available for it."""
        return self._call("unreal_dump_material", mat_path)
