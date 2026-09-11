"""Headless read, write, and edit operations for Source 2 .vmdl files."""

from __future__ import annotations

import os
import re
from typing import Any

from keyvalues3 import KV3TextReader
from gui.common import JsonToKv3

_MODELDOC41_FORMAT = "format:modeldoc41:version{12fc9d44-453a-4ae4-b4d9-7e2ac0bbd4e0}"


def read_vmdl(path: str) -> dict[str, Any]:
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


def write_vmdl(
    path: str,
    mesh_rel_path: str,
    material_remaps: list[dict[str, str]] | None = None,
    import_scale: float = 1.0,
    physics: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a standard ModelDoc41 .vmdl file from a mesh source and material remaps."""
    norm_mesh = mesh_rel_path.replace("\\", "/")
    base_name = os.path.splitext(os.path.basename(norm_mesh))[0]

    render_mesh = {
        "_class": "RenderMeshFile",
        "name": "mesh0",
        "filename": norm_mesh,
        "import_scale": float(import_scale),
        "import_filter": {"exclude_by_default": False, "exception_list": []},
    }

    children: list[dict[str, Any]] = [
        {
            "_class": "RenderMeshList",
            "children": [render_mesh],
        },
        {
            "_class": "MaterialGroupList",
            "children": [
                {
                    "_class": "DefaultMaterialGroup",
                    "remaps": list(material_remaps or []),
                    "use_global_default": False,
                    "global_default_material": "",
                }
            ],
        },
    ]

    if physics:
        children.append({
            "_class": "PhysicsShapeList",
            "children": [
                {
                    "_class": "PhysicsHullFile",
                    "name": base_name,
                    "filename": norm_mesh,
                    "surface_prop": "default",
                    "collision_prop": "default",
                    "import_scale": float(import_scale),
                    "import_filter": {"exclude_by_default": False, "exception_list": []},
                }
            ],
        })

    vmdl_data = {
        "rootNode": {
            "_class": "RootNode",
            "children": children,
            "model_archetype": "",
            "primary_associated_entity": "",
            "anim_graph_name": "",
        }
    }

    content = JsonToKv3(vmdl_data, format="vmdl")
    content = re.sub(r"format:modeldoc\d+:version\{[0-9a-f-]+\}", _MODELDOC41_FORMAT, content, count=1)

    if not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "write_vmdl",
        "mesh": norm_mesh,
        "import_scale": import_scale,
        "material_remaps_count": len(material_remaps or []),
        "content_length": len(content),
    }


def edit_vmdl(
    path: str,
    updates: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Edit an existing .vmdl file in-place, updating remaps, scale, or mesh paths."""
    read_result = read_vmdl(path)
    root = read_result["raw"]
    root_node = root.get("rootNode", {})
    children = root_node.get("children", [])

    modified_fields: list[str] = []

    # 1. Update import scale
    if "import_scale" in updates:
        new_scale = float(updates["import_scale"])
        for group in children:
            if group.get("_class") in ("RenderMeshList", "PhysicsShapeList"):
                for child in group.get("children", []):
                    if isinstance(child, dict) and "import_scale" in child:
                        child["import_scale"] = new_scale
        modified_fields.append("import_scale")

    # 2. Update mesh filename
    if "mesh_rel_path" in updates:
        new_mesh = str(updates["mesh_rel_path"]).replace("\\", "/")
        for group in children:
            if group.get("_class") in ("RenderMeshList", "PhysicsShapeList"):
                for child in group.get("children", []):
                    if isinstance(child, dict) and "filename" in child:
                        child["filename"] = new_mesh
        modified_fields.append("mesh_rel_path")

    # 3. Update material remaps
    if "material_remaps" in updates:
        new_remaps = list(updates["material_remaps"])
        mat_group_found = False
        for group in children:
            if group.get("_class") == "MaterialGroupList":
                for child in group.get("children", []):
                    if child.get("_class") == "DefaultMaterialGroup":
                        child["remaps"] = new_remaps
                        mat_group_found = True
                        break
        if not mat_group_found:
            children.append({
                "_class": "MaterialGroupList",
                "children": [
                    {
                        "_class": "DefaultMaterialGroup",
                        "remaps": new_remaps,
                        "use_global_default": False,
                        "global_default_material": "",
                    }
                ],
            })
        modified_fields.append("material_remaps")

    content = JsonToKv3(root, format="vmdl")
    content = re.sub(r"format:modeldoc\d+:version\{[0-9a-f-]+\}", _MODELDOC41_FORMAT, content, count=1)

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "edit_vmdl",
        "modified_fields": modified_fields,
        "content_length": len(content),
    }
