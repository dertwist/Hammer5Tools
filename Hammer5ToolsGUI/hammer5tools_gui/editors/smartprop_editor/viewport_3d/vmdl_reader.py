"""Thin viewport adapter over the UI-neutral compiled-resource Core API."""

import functools
import os
from typing import List, Optional

import numpy as np

from hammer5tools_core.bridge.core import CoreBridge
from hammer5tools_gui.editors.smartprop_editor.viewport_3d.mesh_cache import MaterialData, MeshData, SubMeshData, MAX_TEXTURE_DIM


def _game_directory() -> str:
    from hammer5tools_gui.common import get_cs2_path
    root = get_cs2_path()
    return os.path.join(root, "game") if root else ""


def _active_addon() -> str:
    from hammer5tools_gui.settings.common import get_addon_name
    return get_addon_name() or "addon"


def _texture(value):
    if value is None:
        return None
    return np.frombuffer(value.rgba, dtype=np.uint8).reshape(value.height, value.width, 4).copy()


def _material(value) -> MaterialData:
    textures = tuple(_texture(item) for item in value.textures)
    return MaterialData(
        name=value.name, base_color_img=textures[0], normal_img=textures[1], mr_img=textures[2],
        ao_img=textures[3], emissive_img=textures[4], base_color_factor=value.base_color_factor,
        metallic_factor=value.metallic_factor, roughness_factor=value.roughness_factor,
        emissive_factor=value.emissive_factor, alpha_mode=value.alpha_mode, alpha_cutoff=value.alpha_cutoff,
        double_sided=value.double_sided, wrap_u=value.wrap_u, wrap_v=value.wrap_v, uv_set=value.uv_set,
        uv_scale=value.uv_scale, uv_offset=value.uv_offset, uv_center=value.uv_center,
        uv_rotation=value.uv_rotation)


def load_model(resource_path: str, context_addon: str = None, max_texture_dim: int = None,
               base_color_only: bool = False, skin: int = 0) -> Optional[MeshData]:
    model = CoreBridge.instance().read_compiled_model(
        _game_directory(), _active_addon(), resource_path, context_addon=context_addon,
        maximum_texture_dimension=max_texture_dim or MAX_TEXTURE_DIM, base_color_only=base_color_only, skin=skin)
    if model is None:
        return None
    vertices = np.asarray(model.vertices, dtype=np.float32).reshape(-1, 3)
    return MeshData(
        vertices=vertices, normals=np.asarray(model.normals, dtype=np.float32).reshape(-1, 3),
        indices=np.asarray(model.indices, dtype=np.uint32), uvs=np.asarray(model.uvs, dtype=np.float32).reshape(-1, 2),
        bbox_min=np.asarray(model.bounds_minimum, dtype=np.float32),
        bbox_max=np.asarray(model.bounds_maximum, dtype=np.float32),
        submeshes=[SubMeshData(item.index_offset, item.index_count, _material(item.material)) for item in model.submeshes])


@functools.lru_cache(maxsize=512)
def get_model_material_groups(resource_path: str, context_addon: str = None) -> List[str]:
    if not isinstance(resource_path, str) or not resource_path.strip():
        return []
    return list(CoreBridge.instance().read_compiled_model_material_groups(
        _game_directory(), _active_addon(), resource_path, context_addon))
