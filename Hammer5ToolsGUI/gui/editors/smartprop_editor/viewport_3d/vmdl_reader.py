"""Thin viewport adapter over the UI-neutral compiled-resource Core API."""

import functools
import os
from typing import List, Optional

import numpy as np

from core.bridge.core import CoreBridge
from gui.editors.smartprop_editor.viewport_3d.mesh_cache import (
    MaterialData, MeshData, SubMeshData, MAX_TEXTURE_DIM, build_alpha_coverage_mipmaps)


def _game_directory() -> str:
    from gui.common import get_cs2_path
    root = get_cs2_path()
    return os.path.join(root, "game") if root else ""


def _active_addon() -> str:
    from gui.settings.common import get_addon_name
    return get_addon_name() or "addon"


def _texture(value):
    if value is None:
        return None
    return np.frombuffer(value.rgba, dtype=np.uint8).reshape(value.height, value.width, 4).copy()


def _material(value) -> MaterialData:
    textures = tuple(_texture(item) for item in value.textures)
    # Alpha-tested cutouts need a coverage-preserving mip chain or they dissolve with
    # distance; build it here, on the load thread, so the GL upload stays a plain copy.
    mips = None
    if value.alpha_mode == "MASK" and textures[0] is not None:
        mips = build_alpha_coverage_mipmaps(textures[0], value.alpha_cutoff)
    return MaterialData(
        name=value.name, base_color_img=textures[0], normal_img=textures[1], mr_img=textures[2],
        ao_img=textures[3], emissive_img=textures[4], base_color_factor=value.base_color_factor,
        metallic_factor=value.metallic_factor, roughness_factor=value.roughness_factor,
        emissive_factor=value.emissive_factor, alpha_mode=value.alpha_mode, alpha_cutoff=value.alpha_cutoff,
        double_sided=value.double_sided, base_color_mips=mips,
        wrap_u=value.wrap_u, wrap_v=value.wrap_v, uv_set=value.uv_set,
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
    # One MaterialData per distinct CompiledMaterialData. The bridge hands the same
    # object to every submesh sharing a material, and MeshCache._upload_mesh dedupes
    # GPU texture uploads by id(MaterialData) — building a fresh one per submesh
    # defeated that and re-uploaded every texture once per submesh.
    materials: dict = {}

    def material_for(value) -> MaterialData:
        cached = materials.get(id(value))
        if cached is None:
            cached = _material(value)
            materials[id(value)] = cached
        return cached

    return MeshData(
        vertices=vertices, normals=np.asarray(model.normals, dtype=np.float32).reshape(-1, 3),
        indices=np.asarray(model.indices, dtype=np.uint32), uvs=np.asarray(model.uvs, dtype=np.float32).reshape(-1, 2),
        bbox_min=np.asarray(model.bounds_minimum, dtype=np.float32),
        bbox_max=np.asarray(model.bounds_maximum, dtype=np.float32),
        submeshes=[SubMeshData(item.index_offset, item.index_count, material_for(item.material))
                   for item in model.submeshes])


def load_material_base_color(resource_path: str, context_addon: str = None,
                             max_texture_dim: int = None) -> Optional[np.ndarray]:
    """Decode a standalone .vmat's base-color map as an RGBA array, or None."""
    material = CoreBridge.instance().read_compiled_material(
        _game_directory(), _active_addon(), resource_path, context_addon=context_addon,
        maximum_texture_dimension=max_texture_dim or MAX_TEXTURE_DIM)
    return None if material is None else _texture(material.textures[0])


def load_material(resource_path: str, context_addon: str = None,
                  max_texture_dim: int = None) -> Optional[MaterialData]:
    """Decode a standalone .vmat into a full MaterialData, or None.

    Used for CSmartPropOperation_MaterialOverride, which names a replacement material with no
    model to hang it on — unlike load_material_base_color, every PBR map is decoded so the
    substituted surface shades the same way the one it replaced did.
    """
    material = CoreBridge.instance().read_compiled_material(
        _game_directory(), _active_addon(), resource_path, context_addon=context_addon,
        maximum_texture_dimension=max_texture_dim or MAX_TEXTURE_DIM, base_color_only=False)
    return None if material is None else _material(material)


@functools.lru_cache(maxsize=512)
def get_model_material_groups(resource_path: str, context_addon: str = None) -> List[str]:
    if not isinstance(resource_path, str) or not resource_path.strip():
        return []
    return list(CoreBridge.instance().read_compiled_model_material_groups(
        _game_directory(), _active_addon(), resource_path, context_addon))
