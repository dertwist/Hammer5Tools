"""Vmap reading experiments: turning a Core VMAP scene projection into viewport draw data.

Pure data in, pure data out — no Qt and no GL — so the mapping from map nodes to
the SmartProp viewport's draw schema is testable on its own.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Callable, Iterable

import numpy as np

from gui.editors.smartprop_editor.viewport_3d.camera import decompose_trs
from gui.editors.smartprop_editor.viewport_3d.mesh_cache import MaterialData, MeshData, SubMeshData

log = logging.getLogger(__name__)

#: Cache key prefix for brush geometry, which has no resource path of its own.
BRUSH_PATH_PREFIX = "#vmap_brush/"


def draw_info(element_id: int, path: str, transform, label: str = "") -> dict:
    """One entry of the viewport's scene list, in the schema render_area draws.

    ``transform`` is a row-vector 4x4 world matrix. Position/rotation/scale are
    filled in as well because the framing pass reads those rather than the matrix.
    """
    world_matrix = np.asarray(transform, dtype=np.float32).reshape((4, 4))
    position, rotation, scale = decompose_trs(world_matrix)
    return {
        "id": element_id,
        "path": path,
        "label": label,
        "position": position,
        "rotation": rotation,
        "scale": scale,
        "world_matrix": world_matrix,
        "parent_world_matrix": np.eye(4, dtype=np.float32),
        "data": {},
        "is_editor_marker": False,
    }


def brush_mesh(mesh, material_loader: Callable[[str], object | None]) -> MeshData:
    """A brush/displacement mesh as viewport mesh data, with base-color materials."""
    vertices = np.asarray(mesh.vertices, dtype=np.float32).reshape(-1, 3)
    materials: dict[str, MaterialData] = {}

    def material_for(name: str) -> MaterialData:
        cached = materials.get(name)
        if cached is None:
            cached = MaterialData(name=name, base_color_img=material_loader(name))
            materials[name] = cached
        return cached

    bounds_minimum = vertices.min(axis=0) if len(vertices) else np.zeros(3, dtype=np.float32)
    bounds_maximum = vertices.max(axis=0) if len(vertices) else np.zeros(3, dtype=np.float32)
    return MeshData(
        vertices=vertices,
        normals=np.asarray(mesh.normals, dtype=np.float32).reshape(-1, 3),
        indices=np.asarray(mesh.indices, dtype=np.uint32),
        uvs=np.asarray(mesh.uvs, dtype=np.float32).reshape(-1, 2),
        bbox_min=bounds_minimum,
        bbox_max=bounds_maximum,
        submeshes=[SubMeshData(item.index_offset, item.index_count, material_for(item.material))
                   for item in mesh.submeshes],
    )


def build_scene(document, smart_prop_models: Iterable[tuple[int, str, object]],
                material_loader: Callable[[str], object | None]):
    """(draw infos, {cache key: MeshData}) for a whole map.

    ``smart_prop_models`` is the already-evaluated model placements, as
    (SmartProp index, model resource path, world matrix) — evaluation needs Core
    and the addon's files, so it happens in the caller.
    """
    infos: list[dict] = []
    meshes: dict[str, MeshData] = {}
    element_id = 0

    identity = np.eye(4, dtype=np.float32)
    for index, mesh in enumerate(document.meshes):
        key = f"{BRUSH_PATH_PREFIX}{index}"
        meshes[key] = brush_mesh(mesh, material_loader)
        element_id += 1
        infos.append(draw_info(element_id, key, identity, mesh.name or f"mesh {index}"))

    for prop in document.props:
        element_id += 1
        infos.append(draw_info(element_id, prop.resource, prop.transform,
                               f"{prop.class_name} {prop.resource}"))

    smart_props = list(document.smart_props)
    for index, model_name, transform in smart_prop_models:
        element_id += 1
        label = smart_props[index].resource if index < len(smart_props) else model_name
        infos.append(draw_info(element_id, model_name, transform, f"{label} → {model_name}"))

    return infos, meshes


def apply_variable_overrides(document: dict, overrides: dict) -> dict:
    """Return ``document`` with its variable defaults replaced by a placement's overrides.

    Hammer stores per-placement parameter values on the map node, not in the
    .vsmart, so a SmartProp placed twice with different settings only evaluates
    correctly once its overrides are folded into the document Core evaluates.
    """
    if not overrides:
        return document
    for variable in document.get("m_Variables", []) or []:
        name = variable.get("m_VariableName")
        if name in overrides:
            variable["m_DefaultValue"] = overrides[name]
    return document


def resolve_content_path(resource_path: str, addon_content_directory: Callable[[str], str],
                         default_addon: str) -> str | None:
    """The on-disk content file for a map resource reference, or None if it is missing.

    A reference may name its own addon (``.../csgo_addons/<addon>/...``); otherwise
    it resolves against the active one.
    """
    normalized = resource_path.replace("\\", "/").lstrip("/")
    addon = default_addon
    match = re.search(r"(?:^|/)csgo_addons/([^/]+)/(.*)$", normalized, re.IGNORECASE)
    if match:
        addon, normalized = match.group(1), match.group(2)
    if not addon:
        return None
    full_path = os.path.join(addon_content_directory(addon), normalized)
    return full_path if os.path.isfile(full_path) else None
