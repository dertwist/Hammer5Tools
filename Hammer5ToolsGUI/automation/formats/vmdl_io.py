"""Headless read, write, and edit operations for Source 2 .vmdl files."""

from __future__ import annotations

import os
from typing import Any

from automation.formats.shaping import shape_response

from keyvalues3 import KV3TextReader

def read_vmdl_full(path: str) -> dict[str, Any]:
    """Parse a loose .vmdl file and return its structured ModelDoc metadata."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"VMDL file not found: '{path}'")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    kv3_file = KV3TextReader().parse(text)
    root = kv3_file.value if hasattr(kv3_file, "value") else kv3_file
    root_node = root.get("rootNode", {}) if isinstance(root, dict) else {}
    children = root_node.get("children", []) if isinstance(root_node, dict) else []

    meshes = []
    material_remaps = []
    physics_hulls = []
    lod_groups = []

    for group in children:
        if not isinstance(group, dict):
            continue
        cls_name = group.get("_class", "")
        group_children = group.get("children", [])

        if cls_name == "RenderMeshList":
            for child in group_children:
                if isinstance(child, dict) and child.get("_class") == "RenderMeshFile":
                    meshes.append({
                        "name": child.get("name", ""),
                        "filename": child.get("filename", ""),
                        "import_scale": child.get("import_scale", 1.0),
                    })
        elif cls_name == "MaterialGroupList":
            for child in group_children:
                if isinstance(child, dict) and child.get("_class") == "DefaultMaterialGroup":
                    remaps = child.get("remaps", [])
                    if isinstance(remaps, list):
                        material_remaps.extend(remaps)
        elif cls_name == "PhysicsShapeList":
            for child in group_children:
                if isinstance(child, dict) and child.get("_class") == "PhysicsHullFile":
                    physics_hulls.append({
                        "name": child.get("name", ""),
                        "filename": child.get("filename", ""),
                        "surface_prop": child.get("surface_prop", "default"),
                        "import_scale": child.get("import_scale", 1.0),
                    })
        elif cls_name == "LODGroupList":
            for child in group_children:
                if isinstance(child, dict) and child.get("_class") == "LODGroup":
                    lod_groups.append({
                        "switch_threshold": child.get("switch_threshold", 0.0),
                        "mesh_references": child.get("mesh_references", []),
                    })

    format_str = str(getattr(kv3_file, "format", "modeldoc41"))

    return {
        "path": path.replace("\\", "/"),
        "format": format_str,
        "meshes": meshes,
        "material_remaps": material_remaps,
        "physics_hulls": physics_hulls,
        "lod_groups": lod_groups,
        "raw": root,
    }


def read_vmdl(
    path: str,
    detail: str = "summary",
    select: str | None = None,
) -> dict[str, Any]:
    """Read a .vmdl model file.

    The extracted view is already compact, so `summary` and `full` are the same
    here; `select` addresses one node of the parsed document.
    """
    full = read_vmdl_full(path)
    payload = {key: value for key, value in full.items() if key != "raw"}
    return shape_response(payload, payload, full.get("raw"), detail=detail, select=select)


def write_vmdl(path: str, mesh_rel_path: str, material_remaps: list[dict[str, str]] | None = None,
               import_scale: float = 1.0, physics: bool = True, dry_run: bool = False,
               bridge=None) -> dict[str, Any]:
    from core.bridge import CoreBridge
    return (bridge or CoreBridge.instance()).author_source_assets({
        "path": path, "action": "create", "mesh_rel_path": mesh_rel_path,
        "material_remaps": material_remaps, "import_scale": import_scale,
        "physics": physics, "dry_run": dry_run,
    }, "vmdl")


def edit_vmdl(path: str, updates: dict[str, Any], dry_run: bool = False, bridge=None) -> dict[str, Any]:
    from core.bridge import CoreBridge
    return (bridge or CoreBridge.instance()).author_source_assets({
        "path": path, "action": "update", "updates": updates, "dry_run": dry_run,
    }, "vmdl")
