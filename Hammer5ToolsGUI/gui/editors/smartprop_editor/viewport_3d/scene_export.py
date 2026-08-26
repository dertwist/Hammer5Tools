"""
Debug export: dump the current SmartProp 3D viewport scene to a .glb, with
base color / normal / metallic-roughness / occlusion / emissive textures
embedded, for inspecting the scene in an external glTF viewer.

Each entity's world transform is baked directly into its exported vertices
(one mesh node per entity, identity transform) rather than built as a glTF
TRS/quaternion node hierarchy: this codebase's model matrices use a
"pre-transposed" convention (see camera.py) that would need care to convert
correctly into glTF's standard column-vector quaternion nodes, and a debug
dump doesn't need an editable hierarchy — just correct, inspectable geometry.
"""
import io
import os
import re
from typing import Optional, Tuple

import numpy as np
from PIL import Image as PILImage

from pygltflib import (
    GLTF2, Scene, Node, Mesh, Primitive, Attributes,
    Buffer, BufferView, Accessor,
    Material, PbrMetallicRoughness, TextureInfo, OcclusionTextureInfo, NormalMaterialTexture,
    Texture, Image as GLTFImage, Sampler,
    ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER, FLOAT, UNSIGNED_INT, VEC3, VEC2, SCALAR,
)

from gui.editors.smartprop_editor.viewport_3d.camera import (
    scale_matrix, rotation_matrix_euler, translation_matrix,
)
from gui.editors.smartprop_editor.viewport_3d.render_area import safe_normal_matrix
from gui.editors.smartprop_editor.viewport_3d import vmdl_reader

_INCH_TO_METER = 0.0254


def _world_matrix(position, rotation, scale) -> np.ndarray:
    """Same TRS composition render_area.py uses for its GL uModel, minus the
    Source->GL axis swap (applied once below, after vertices are already in
    world space, instead of per-matrix)."""
    return scale_matrix(*scale) @ rotation_matrix_euler(*rotation) @ translation_matrix(*position)


def _apply(matrix4: np.ndarray, points: np.ndarray, w: float) -> np.ndarray:
    """(N, 3) -> (N, 3) via homogeneous row-vector @ matrix4 (this codebase's convention)."""
    hom = np.empty((len(points), 4), dtype=np.float32)
    hom[:, :3] = points
    hom[:, 3] = w
    return (hom @ matrix4)[:, :3]


def _source_to_gltf_positions(points: np.ndarray) -> np.ndarray:
    """Source world points (Z-up, inches) -> glTF (Y-up, metres): (x, z, -y)."""
    out = np.empty_like(points)
    out[:, 0] = points[:, 0]
    out[:, 1] = points[:, 2]
    out[:, 2] = -points[:, 1]
    return out * _INCH_TO_METER


def _source_to_gltf_dirs(vectors: np.ndarray) -> np.ndarray:
    out = np.empty_like(vectors)
    out[:, 0] = vectors[:, 0]
    out[:, 1] = vectors[:, 2]
    out[:, 2] = -vectors[:, 1]
    lengths = np.linalg.norm(out, axis=1, keepdims=True)
    lengths[lengths < 1e-8] = 1.0
    return out / lengths


def _resolve_context_addon(document) -> Optional[str]:
    opened_path = getattr(document, "opened_file", None) if document else None
    if not opened_path:
        return None
    match = re.search(r'/csgo_addons/([^/]+)/', opened_path.replace('\\', '/'), re.IGNORECASE)
    return match.group(1) if match else None


class _Builder:
    """Accumulates one shared binary blob plus the glTF JSON structures that
    reference it, so every mesh and image can share a single .glb buffer."""

    def __init__(self):
        self.gltf = GLTF2()
        self.gltf.buffers = [Buffer()]
        self.blob = bytearray()

    def _pad(self):
        while len(self.blob) % 4:
            self.blob.append(0)

    def add_bufferview(self, data: bytes, target: Optional[int] = None) -> int:
        self._pad()
        offset = len(self.blob)
        self.blob.extend(data)
        bv = BufferView(buffer=0, byteOffset=offset, byteLength=len(data))
        if target is not None:
            bv.target = target
        idx = len(self.gltf.bufferViews)
        self.gltf.bufferViews.append(bv)
        return idx

    def add_accessor(self, array: np.ndarray, component_type: int, accessor_type: str,
                      target: Optional[int] = None, minmax: bool = False) -> int:
        bv = self.add_bufferview(np.ascontiguousarray(array).tobytes(), target)
        acc = Accessor(bufferView=bv, componentType=component_type, count=len(array), type=accessor_type)
        if minmax:
            acc.min = array.min(axis=0).tolist()
            acc.max = array.max(axis=0).tolist()
        idx = len(self.gltf.accessors)
        self.gltf.accessors.append(acc)
        return idx

    def add_image(self, rgba: np.ndarray) -> int:
        buf = io.BytesIO()
        PILImage.fromarray(rgba, "RGBA").save(buf, format="PNG")
        bv = self.add_bufferview(buf.getvalue())
        idx = len(self.gltf.images)
        self.gltf.images.append(GLTFImage(bufferView=bv, mimeType="image/png"))
        return idx

    def finish(self, path: str):
        self._pad()
        self.gltf.buffers[0].byteLength = len(self.blob)
        self.gltf.set_binary_blob(bytes(self.blob))
        self.gltf.save(path)


def _add_material(builder: _Builder, material, sampler_idx: int, material_cache: dict) -> int:
    key = id(material)
    if key in material_cache:
        return material_cache[key]

    def tex(img):
        if img is None:
            return None
        tex_idx = len(builder.gltf.textures)
        builder.gltf.textures.append(Texture(source=builder.add_image(img), sampler=sampler_idx))
        return tex_idx

    pbr = PbrMetallicRoughness(
        baseColorFactor=list(material.base_color_factor),
        metallicFactor=float(material.metallic_factor),
        roughnessFactor=float(material.roughness_factor),
    )
    base_tex = tex(material.base_color_img)
    if base_tex is not None:
        pbr.baseColorTexture = TextureInfo(index=base_tex)
    mr_tex = tex(material.mr_img)
    if mr_tex is not None:
        pbr.metallicRoughnessTexture = TextureInfo(index=mr_tex)

    gltf_mat = Material(
        name=material.name or "material",
        pbrMetallicRoughness=pbr,
        doubleSided=bool(material.double_sided),
        emissiveFactor=list(material.emissive_factor),
    )
    normal_tex = tex(material.normal_img)
    if normal_tex is not None:
        gltf_mat.normalTexture = NormalMaterialTexture(index=normal_tex)
    ao_tex = tex(material.ao_img)
    if ao_tex is not None:
        gltf_mat.occlusionTexture = OcclusionTextureInfo(index=ao_tex)
    emissive_tex = tex(material.emissive_img)
    if emissive_tex is not None:
        gltf_mat.emissiveTexture = TextureInfo(index=emissive_tex)

    if material.alpha_mode == "MASK":
        gltf_mat.alphaMode = "MASK"
        gltf_mat.alphaCutoff = float(material.alpha_cutoff)
    elif material.alpha_mode == "BLEND":
        gltf_mat.alphaMode = "BLEND"

    idx = len(builder.gltf.materials)
    builder.gltf.materials.append(gltf_mat)
    material_cache[key] = idx
    return idx


def export_scene_to_glb(render_area, output_path: str) -> Tuple[bool, str]:
    """Write every mesh entity currently in ``render_area``'s hierarchy to a
    single .glb, with textures embedded. Returns (success, message)."""
    model_infos = dict(getattr(render_area, "_model_infos", None) or {})
    if not model_infos:
        return False, "Nothing to export: the viewport has no entities."

    builder = _Builder()
    builder.gltf.samplers = [Sampler()]
    material_cache: dict = {}
    scene_nodes = []
    skipped = []
    context_addon = _resolve_context_addon(getattr(render_area, "document", None))

    for info in model_infos.values():
        if info.get("is_dot"):
            continue
        model_path = info.get("path")
        if not model_path:
            continue

        mesh_data = render_area.mesh_cache._cpu_cache.get(model_path)
        if mesh_data is None:
            try:
                mesh_data = vmdl_reader.load_model(model_path, context_addon)
            except Exception as exc:
                skipped.append(f"{model_path} ({exc})")
                continue
        if mesh_data is None:
            skipped.append(model_path)
            continue

        world = _world_matrix(info.get("position", (0.0, 0.0, 0.0)),
                               info.get("rotation", (0.0, 0.0, 0.0)),
                               info.get("scale", (1.0, 1.0, 1.0)))
        normal_mat = safe_normal_matrix(world)

        positions = _source_to_gltf_positions(_apply(world, mesh_data.vertices, 1.0)).astype(np.float32)
        normals = _source_to_gltf_dirs(mesh_data.normals @ normal_mat[:3, :3]).astype(np.float32)
        # Raw UV is written to TEXCOORD_0 unchanged: glTF viewers apply their
        # own V-flip at texture load, so there is nothing to undo here.
        uvs = mesh_data.uvs.astype(np.float32) if mesh_data.uvs is not None else np.zeros((len(positions), 2), dtype=np.float32)

        pos_acc = builder.add_accessor(positions, FLOAT, VEC3, ARRAY_BUFFER, minmax=True)
        norm_acc = builder.add_accessor(normals, FLOAT, VEC3, ARRAY_BUFFER)
        uv_acc = builder.add_accessor(uvs, FLOAT, VEC2, ARRAY_BUFFER)

        primitives = []
        for sm in mesh_data.submeshes:
            idx_slice = mesh_data.indices[sm.index_offset: sm.index_offset + sm.index_count].astype(np.uint32)
            idx_acc = builder.add_accessor(idx_slice, UNSIGNED_INT, SCALAR, ELEMENT_ARRAY_BUFFER)
            primitives.append(Primitive(
                attributes=Attributes(POSITION=pos_acc, NORMAL=norm_acc, TEXCOORD_0=uv_acc),
                indices=idx_acc,
                material=_add_material(builder, sm.material, 0, material_cache),
            ))
        if not primitives:
            continue

        name = os.path.basename(model_path)
        mesh_idx = len(builder.gltf.meshes)
        builder.gltf.meshes.append(Mesh(primitives=primitives, name=name))
        node_idx = len(builder.gltf.nodes)
        builder.gltf.nodes.append(Node(mesh=mesh_idx, name=name))
        scene_nodes.append(node_idx)

    if not scene_nodes:
        detail = f" Skipped: {', '.join(skipped)}" if skipped else ""
        return False, f"Nothing to export: no entity had a loadable mesh.{detail}"

    builder.gltf.scenes = [Scene(nodes=scene_nodes)]
    builder.gltf.scene = 0
    builder.finish(output_path)

    msg = f"Exported {len(scene_nodes)} mesh(es) to {output_path}."
    if skipped:
        shown = ', '.join(skipped[:5]) + ("..." if len(skipped) > 5 else "")
        msg += f" Skipped {len(skipped)}: {shown}"
    return True, msg
