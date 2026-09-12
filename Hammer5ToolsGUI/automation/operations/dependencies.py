"""Recursive dependency resolution for Source 2 assets."""

from __future__ import annotations

import os
from typing import Any

from automation.formats.vmat_io import read_vmat
from automation.formats.vmdl_io import read_vmdl
from automation.formats.vsmart_io import read_vsmart_full
from automation.formats.vtex_io import read_vtex
from automation.formats.shaping import paginate

# A reference is recognised by its extension. Treating "any string containing a
# slash" as a path turns SmartProp division expressions such as
# "(sizer_x+32)/32" into asset dependencies.
_REFERENCE_SUFFIXES = (
    ".vmat", ".vmt",
    ".png", ".tga", ".jpg", ".jpeg", ".vtex", ".hdr", ".exr", ".psd",
    ".vmdl", ".vmdl_prefab", ".fbx", ".dmx", ".obj",
    ".vsndevts", ".vsnd", ".wav", ".mp3", ".ogg",
    ".vpcf", ".vsmart", ".vanim", ".vphys",
)
from core.bridge import CoreBridge
from gui.settings.common import get_addon_dir


def resolve_dependencies(
    path: str,
    addon_dir: str | None = None,
    visited: set[str] | None = None,
    limit: int | None = 200,
    offset: int = 0,
    include_all: bool = False,
) -> dict[str, Any]:
    """Recursively resolve all external asset dependencies for any Source 2 file."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Target asset file not found: '{path}'")

    if visited is None:
        visited = set()

    norm_path = os.path.normpath(path).lower()
    if norm_path in visited:
        return {
            "path": path.replace("\\", "/"),
            "total_references": 0,
            "materials": [],
            "textures": [],
            "models": [],
            "soundevents": [],
            "particles": [],
            "smartprops": [],
            "other": [],
            "all_references": [],
        }
    visited.add(norm_path)

    active_addon = addon_dir or get_addon_dir() or os.path.dirname(os.path.abspath(path))
    ext = os.path.splitext(path)[1].lower()

    direct_refs: set[str] = set()

    if ext == ".vmat":
        try:
            mat_data = read_vmat(path)
            for slot_path in mat_data.get("slots", {}).values():
                # A slot key containing "Texture" can hold a scalar or a vector
                # (g_vTextureScale), so the value still has to look like a file.
                if slot_path and slot_path.strip().lower().endswith(_REFERENCE_SUFFIXES):
                    direct_refs.add(slot_path.strip().replace("\\", "/"))
        except Exception:
            pass
    elif ext in (".vmdl", ".vmdl_prefab"):
        try:
            model_data = read_vmdl(path)
            for mesh in model_data.get("meshes", []):
                fn = mesh.get("filename")
                if fn:
                    direct_refs.add(fn.replace("\\", "/"))
            for remap in model_data.get("material_remaps", []):
                to_mat = remap.get("to")
                if to_mat and not to_mat.startswith("materials/dev/"):
                    direct_refs.add(to_mat.replace("\\", "/"))
        except Exception:
            pass
    elif ext == ".vtex":
        try:
            tex_data = read_vtex(path)
            for item in tex_data.get("input_textures", []):
                fn = item.get("file_name")
                if fn:
                    direct_refs.add(fn.replace("\\", "/"))
        except Exception:
            pass
    elif ext == ".vsmart":
        try:
            smart_data = read_vsmart_full(path)

            def walk_smart(node: Any):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if isinstance(v, str) and v.strip().lower().endswith(_REFERENCE_SUFFIXES):
                            direct_refs.add(v.strip().replace("\\", "/"))
                        elif isinstance(v, (dict, list)):
                            walk_smart(v)
                elif isinstance(node, list):
                    for item in node:
                        walk_smart(item)

            walk_smart(smart_data.get("raw", {}))
        except Exception:
            pass
    elif ext == ".vmap":
        try:
            direct_refs.update(CoreBridge.instance().read_valve_map_asset_references(path))
        except Exception:
            pass

    all_refs = set(direct_refs)

    # Recurse into child references if they exist on disk inside active_addon
    for ref in direct_refs:
        child_path = os.path.join(active_addon, ref) if not os.path.isabs(ref) else ref
        if os.path.isfile(child_path):
            child_res = resolve_dependencies(
                child_path, addon_dir=active_addon, visited=visited, limit=None, include_all=True
            )
            all_refs.update(child_res["all_references"])

    materials = sorted(r for r in all_refs if r.endswith((".vmat", ".vmt")))
    textures = sorted(r for r in all_refs if r.endswith((".png", ".tga", ".jpg", ".vtex", ".hdr", ".exr")))
    models = sorted(r for r in all_refs if r.endswith((".vmdl", ".vmdl_prefab", ".fbx", ".dmx", ".obj")))
    soundevents = sorted(r for r in all_refs if r.endswith((".vsndevts", ".vsnd", ".wav", ".mp3", ".ogg")))
    particles = sorted(r for r in all_refs if r.endswith(".vpcf"))
    smartprops = sorted(r for r in all_refs if r.endswith(".vsmart"))

    result = {
        "path": path.replace("\\", "/"),
        "total_references": len(all_refs),
        "materials": materials,
        "textures": textures,
        "models": models,
        "soundevents": soundevents,
        "particles": particles,
        "smartprops": smartprops,
    }
    # The category lists above already name every reference by kind, so the flat
    # list is pure duplication and is returned only when asked for. Anything a
    # category did not claim is always reported, since that is the part the
    # categories do not tell you.
    categorised = set(materials) | set(textures) | set(models) | set(soundevents) | set(particles) | set(smartprops)
    result["other"] = sorted(all_refs - categorised)
    if include_all:
        result.update(paginate(sorted(all_refs), "all_references", limit=limit, offset=offset))
    return result
