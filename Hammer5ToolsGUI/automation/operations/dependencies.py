"""Recursive dependency resolution for Source 2 assets."""

from __future__ import annotations

import os
from typing import Any

from automation.formats.vmat_io import read_vmat
from automation.formats.vmdl_io import read_vmdl
from automation.formats.vsmart_io import read_vsmart
from automation.formats.vtex_io import read_vtex
from core.bridge import CoreBridge
from gui.settings.common import get_addon_dir


def resolve_dependencies(
    path: str,
    addon_dir: str | None = None,
    visited: set[str] | None = None,
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
                if slot_path:
                    direct_refs.add(slot_path.replace("\\", "/"))
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
            smart_data = read_vsmart(path)

            def walk_smart(node: Any):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if isinstance(v, str) and (v.endswith((".vmdl", ".vmat", ".vsmart", ".vpcf")) or "/" in v):
                            direct_refs.add(v.replace("\\", "/"))
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
            child_res = resolve_dependencies(child_path, addon_dir=active_addon, visited=visited)
            all_refs.update(child_res["all_references"])

    materials = sorted(r for r in all_refs if r.endswith((".vmat", ".vmt")))
    textures = sorted(r for r in all_refs if r.endswith((".png", ".tga", ".jpg", ".vtex", ".hdr", ".exr")))
    models = sorted(r for r in all_refs if r.endswith((".vmdl", ".vmdl_prefab", ".fbx", ".dmx", ".obj")))
    soundevents = sorted(r for r in all_refs if r.endswith((".vsndevts", ".vsnd", ".wav", ".mp3", ".ogg")))
    particles = sorted(r for r in all_refs if r.endswith(".vpcf"))
    smartprops = sorted(r for r in all_refs if r.endswith(".vsmart"))

    return {
        "path": path.replace("\\", "/"),
        "total_references": len(all_refs),
        "materials": materials,
        "textures": textures,
        "models": models,
        "soundevents": soundevents,
        "particles": particles,
        "smartprops": smartprops,
        "all_references": sorted(all_refs),
    }
