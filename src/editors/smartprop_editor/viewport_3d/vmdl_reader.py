"""
Read compiled Source 2 assets (.vmdl_c / .vmat_c / .vtex_c) straight into the
viewport's :class:`MeshData`, with no glTF round-trip and no on-disk cache.

This replaces the old path (VRF ``GltfModelExporter`` -> .glb on disk -> trimesh
-> MeshData).  Everything happens in memory through ValveResourceFormat's block
readers, which is both faster and more faithful:

    * ~2 ms to read all geometry of the largest shipped model (94k verts) versus
      ~2.5 s to export and re-parse it as glTF.
    * No cache directory, so no mtime invalidation and no stale untextured GLBs.
    * The glTF exporter emits every LoD and splits vertices per material, which
      inflated that same model to 376k verts.  Reading draw calls directly keeps
      the real 94k.
    * ``GltfModelExporter`` currently throws on materials (a SharpGLTF/System.
      Runtime version clash), so the old path silently fell back to geometry
      only.  Nothing here touches SharpGLTF.

Geometry comes back in raw Source space (Z-up, inches) because that is how it is
stored in the VBIB — the axis permutation the GLB loader had to undo simply does
not arise.
"""
import ctypes
import os
import re
import threading
from typing import Optional

import numpy as np

from src.editors.smartprop_editor.viewport_3d.mesh_cache import (
    MaterialData, MeshData, SubMeshData, MAX_TEXTURE_DIM,
)


# .NET plumbing

class _Vrf:
    """Resolved VRF types + bound KeyValues extension methods.

    Built once per process.  ``KVObjectExtensions`` are C# *extension* methods,
    so pythonnet cannot reach them as instance methods on KVObject; they are
    bound here by reflection and invoked statically.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> "_Vrf":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        from src.dotnet import setup_vrf
        setup_vrf()

        import System
        self.System = System
        asm = System.Reflection.Assembly.Load("ValveResourceFormat")
        self.asm = asm
        self.GameFileLoader = asm.GetType("ValveResourceFormat.IO.GameFileLoader")
        self.CubemapFace = asm.GetType("ValveResourceFormat.ResourceTypes.Texture+CubemapFace")
        self.FACE0 = System.Enum.ToObject(self.CubemapFace, 0)

        kvx = asm.GetType("ValveResourceFormat.Serialization.KeyValues.KVObjectExtensions")
        self._kv_methods = {}
        for m in kvx.GetMethods():
            if not m.IsGenericMethodDefinition:
                self._kv_methods.setdefault((m.Name, len(m.GetParameters())), m)

    def kv(self, name, *args):
        """Invoke a KVObjectExtensions method. String arguments only.

        pythonnet cannot box a Python int into the ``object[]`` these are
        invoked with (it stays a PyInt and Invoke rejects it), so the typed
        scalar getters — which all take a numeric default — are unusable from
        here.  Scalars are read via :meth:`kv_scalar` instead.
        """
        method = self._kv_methods.get((name, len(args)))
        if method is None:
            raise KeyError(f"{name}/{len(args)}")
        arr = self.System.Array.CreateInstance(self.System.Object, len(args))
        for i, a in enumerate(args):
            arr[i] = a
        return method.Invoke(None, arr)

    def kv_array(self, obj, name):
        try:
            result = self.kv("GetArray", obj, name)
        except Exception:
            return []
        return result if result is not None else []

    @staticmethod
    def kv_scalar(obj, name):
        """Raw value of a scalar property, or None. KVObject is iterable as pairs."""
        try:
            for pair in obj:
                if str(pair.Key) == name:
                    return pair.Value
        except Exception:
            pass
        return None

    def kv_str(self, obj, name, default=None):
        value = self.kv_scalar(obj, name)
        return default if value is None else str(value)

    def kv_int(self, obj, name, default=0):
        value = self.kv_scalar(obj, name)
        if value is None:
            return default
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return default


# One GameFileLoader per thread.  VRF's loader is not documented as thread-safe
# and the viewport loads models from a QThreadPool, so rather than serialising
# every read behind one lock (which is what the old GLB path had to do) each
# worker keeps its own.  Construction is cheap; VPK mounting happens lazily.
_thread_local = threading.local()


def _resolve(resource_path: str, context_addon: str = None):
    """Split a model reference into (addon_name, game-relative path).

    Accepts absolute paths under ``csgo_addons/<addon>/`` or ``csgo/``, plus
    bare relative paths, matching what the old decompile entry point took.
    """
    from src.settings.common import get_addon_name

    path = resource_path.replace("\\", "/").strip("/")
    if context_addon:
        context_addon = context_addon.replace("\\", "/").replace("csgo_addons/", "").strip("/")

    addon_match = re.search(r'/csgo_addons/([^/]+)/(.*)$', '/' + path, re.IGNORECASE)
    csgo_match = re.search(r'/csgo/(.*)$', '/' + path, re.IGNORECASE)
    if addon_match:
        addon_name, path = addon_match.group(1), addon_match.group(2)
    elif csgo_match:
        addon_name, path = context_addon or get_addon_name() or "addon", csgo_match.group(1)
    else:
        addon_name = context_addon or get_addon_name() or "addon"

    if path.endswith(".vmdl_c"):
        path = path[:-2]
    elif not path.endswith(".vmdl"):
        path += ".vmdl"
    return addon_name, path


def _get_loader(addon_name: str, rel_path: str):
    """Thread-local GameFileLoader anchored so it finds gameinfo.gi + the addon.

    The anchor file need not exist — VRF walks up from it to locate the game
    root and mounts the core search paths and VPKs from there.
    """
    from src.common import get_cs2_path
    from src.dotnet import _suppress_dotnet_console
    from src.settings.common import get_addon_name

    cache = getattr(_thread_local, "loaders", None)
    if cache is None:
        cache = _thread_local.loaders = {}
    if addon_name in cache:
        return cache[addon_name]

    cs2_path = get_cs2_path()
    if not cs2_path:
        return None

    vrf = _Vrf.get()
    addon_candidate = os.path.join(cs2_path, "game", "csgo_addons", addon_name,
                                   rel_path.replace("/", os.sep) + "_c")
    anchor = addon_candidate if os.path.exists(addon_candidate) else os.path.join(
        cs2_path, "game", "csgo", rel_path.replace("/", os.sep) + "_c")

    with _suppress_dotnet_console():
        loader = vrf.System.Activator.CreateInstance(vrf.GameFileLoader, None, anchor)
        # Mount the model's addon and the active addon so addon-local materials
        # and textures resolve the same way Source 2 Viewer resolves them.
        for name in {addon_name, get_addon_name() or "addon"}:
            folder = os.path.join(cs2_path, "game", "csgo_addons", name)
            if os.path.isdir(folder):
                try:
                    loader.AddDiskPathToSearch(folder)
                except Exception:
                    pass

    cache[addon_name] = loader
    return loader


# Buffer marshalling
#
# Never iterate a .NET array elementwise from Python: building a numpy array via
# ``[[v.X, v.Y, v.Z] for v in arr]`` costs ~460 ms on a 94k-vertex buffer.
# Pinning the array and viewing its memory does the same job in ~3.7 ms.

def _pinned_floats(array, components: int) -> Optional[np.ndarray]:
    """Copy a blittable .NET Vector2/3/4[] into an (N, components) float32 array."""
    if array is None or array.Length == 0:
        return None
    from System.Runtime.InteropServices import GCHandle, GCHandleType

    handle = GCHandle.Alloc(array, GCHandleType.Pinned)
    try:
        ptr = handle.AddrOfPinnedObject().ToInt64()
        view = np.ctypeslib.as_array(
            ctypes.cast(ptr, ctypes.POINTER(ctypes.c_float)),
            shape=(array.Length, components),
        )
        return view.copy()
    finally:
        handle.Free()


def _attribute(vbib, vertex_buffer, semantic: str, components: int) -> Optional[np.ndarray]:
    """Read one vertex attribute as (N, components) float32, or None if absent.

    Decoding is delegated to VRF, which already handles every DXGI format the
    engine ships (half floats, normalised integers, hemi-octahedral normals),
    so there is no format table to maintain here.
    """
    field = None
    for candidate in vertex_buffer.InputLayoutFields:
        if str(candidate.SemanticName) == semantic:
            field = candidate
            break
    if field is None:
        return None

    try:
        if semantic == "NORMAL":
            # Handles both compressed and plain float normals.
            return _pinned_floats(vbib.GetNormalTangentArray(vertex_buffer, field).Item1, 3)
        if components == 2:
            return _pinned_floats(vbib.GetVector2AttributeArray(vertex_buffer, field), 2)
        return _pinned_floats(vbib.GetVector3AttributeArray(vertex_buffer, field), 3)
    except Exception:
        return None


def _index_array(index_buffer) -> np.ndarray:
    raw = bytes(index_buffer.Data)
    dtype = np.uint16 if index_buffer.ElementSizeInBytes == 2 else np.uint32
    return np.frombuffer(raw, dtype=dtype).astype(np.uint32)


# Materials

# Source 2 does not use glTF's metallic-roughness layout.  Verified against the
# shipped CS2 materials (csgo_complex / csgo_vertexlitgeneric / csgo_environment /
# csgo_foliage / csgo_glass / csgo_character / csgo_weapon):
#   g_tColor            sRGB albedo
#   g_tNormal           RGB tangent normal (VRF decodes HemiOctRB), A = roughness
#   g_tMetalness        R = metalness
#   g_tAmbientOcclusion R = ambient occlusion
# There is no g_tRoughness — reading roughness out of the normal map's alpha is
# the whole trick.
# The layered shaders (csgo_environment*.vfx, used by most world/prop-detail
# materials) name their first layer "g_tColor1"/"g_tNormal1" instead, so each
# slot is a fallback chain rather than a single key.
_TEX_BASE = ("g_tColor", "g_tColor1", "g_tColor2", "g_tColor3", "g_tColor0", "g_tColorA")
_TEX_NORMAL = ("g_tNormal", "g_tNormal1", "g_tNormal2", "g_tNormal3", "g_tNormal0", "g_tNormalA")
_TEX_METAL = ("g_tMetalness", "g_tMetalness1", "g_tMetalness2", "g_tMetalness3", "g_tMetalness0")
_TEX_AO = ("g_tAmbientOcclusion", "g_tAmbientOcclusion1", "g_tAmbientOcclusion2")
_TEX_EMISSIVE = ("g_tSelfIllumMask", "g_tEmissiveMask", "g_tSelfIllum")


def _texture_path(textures: dict, names):
    for name in names:
        if name in textures:
            return textures[name]
    return None


def _pick_mip(texture, max_dim: Optional[int]) -> int:
    """Smallest mip level that still satisfies ``max_dim``.

    Decoding a mip instead of the full image and downscaling afterwards is a
    large win for thumbnails: a 512x512 BC7 costs ~32 ms at mip 0 but ~1.7 ms at
    mip 2.
    """
    if not max_dim:
        return 0
    # ActualWidth/Height, not Width/Height: block-compressed images are padded up
    # to the block size, so a genuinely 1x1 texture reports 4x4.
    mip, width, height = 0, int(texture.ActualWidth), int(texture.ActualHeight)
    while mip + 1 < int(texture.NumMipLevels) and max(width, height) > max_dim:
        mip += 1
        width //= 2
        height //= 2
    return mip


def _decode_texture(loader, path, max_dim: Optional[int]) -> Optional[np.ndarray]:
    """Decode a .vtex_c to a GL-ready RGBA uint8 array, or None."""
    from src.dotnet import _suppress_dotnet_console

    vrf = _Vrf.get()
    try:
        with _suppress_dotnet_console():
            resource = loader.LoadFileCompiled(path)
        if resource is None:
            return None
        texture = resource.DataBlock
        mip = _pick_mip(texture, max_dim)
        bitmap = texture.GenerateBitmap(
            vrf.System.UInt32(0), vrf.FACE0, vrf.System.UInt32(mip),
            texture.RetrieveCodecFromResourceEditInfo(),
        )
        pixels = np.frombuffer(bytes(bitmap.Bytes), dtype=np.uint8).reshape(
            bitmap.Height, bitmap.Width, 4)
        # SKBitmap hands back BGRA; GL wants RGBA and bottom-up rows.
        return np.ascontiguousarray(pixels[::-1, :, [2, 1, 0, 3]])
    except Exception:
        return None


def _nearest_resize(img: np.ndarray, height: int, width: int) -> np.ndarray:
    rows = (np.arange(height) * (img.shape[0] / height)).astype(np.int32).clip(0, img.shape[0] - 1)
    cols = (np.arange(width) * (img.shape[1] / width)).astype(np.int32).clip(0, img.shape[1] - 1)
    return img[rows][:, cols]


def _vector_param(material, name, default):
    for entry in material.VectorParams:
        if str(entry.Key) == name:
            v = entry.Value
            out = list(default)
            for i, comp in enumerate(("X", "Y", "Z", "W")[:len(out)]):
                try:
                    out[i] = float(getattr(v, comp))
                except Exception:
                    pass
            return tuple(out)
    return tuple(default)


def _float_param(material, name, default):
    for entry in material.FloatParams:
        if str(entry.Key) == name:
            try:
                return float(entry.Value)
            except Exception:
                return default
    return default


def _int_param(material, name, default=0):
    for entry in material.IntParams:
        if str(entry.Key) == name:
            try:
                return int(entry.Value)
            except Exception:
                return default
    return default


def _load_material(loader, material_path: str, max_dim: Optional[int],
                   base_color_only: bool) -> MaterialData:
    from src.dotnet import _suppress_dotnet_console

    md = MaterialData(name=material_path)
    try:
        with _suppress_dotnet_console():
            resource = loader.LoadFileCompiled(material_path)
        if resource is None:
            return md
        material = resource.DataBlock
    except Exception:
        return md

    textures = {str(e.Key): e.Value for e in material.TextureParams}

    base_path = _texture_path(textures, _TEX_BASE)
    if base_path is not None:
        md.base_color_img = _decode_texture(loader, base_path, max_dim)

    if not base_color_only:
        normal_path = _texture_path(textures, _TEX_NORMAL)
        normal_rgba = _decode_texture(loader, normal_path, max_dim) if normal_path else None
        if normal_rgba is not None:
            md.normal_img = normal_rgba

        metal_path = _texture_path(textures, _TEX_METAL)
        metal_img = _decode_texture(loader, metal_path, max_dim) if metal_path else None
        # glTF layout expected by the viewport shader: G = roughness, B = metalness.
        if normal_rgba is not None or metal_img is not None:
            reference = normal_rgba if normal_rgba is not None else metal_img
            h, w = reference.shape[0], reference.shape[1]
            mr = np.zeros((h, w, 4), dtype=np.uint8)
            mr[..., 3] = 255
            if normal_rgba is not None:
                mr[..., 1] = normal_rgba[..., 3]          # roughness from normal alpha
            else:
                mr[..., 1] = int(round(255 * _float_param(material, "g_flRoughness", 1.0)))
            if metal_img is not None:
                metal = metal_img if metal_img.shape[:2] == (h, w) else _nearest_resize(metal_img, h, w)
                mr[..., 2] = metal[..., 0]
            else:
                mr[..., 2] = int(round(255 * _float_param(material, "g_flMetalness", 0.0)))
            md.mr_img = mr

        ao_path = _texture_path(textures, _TEX_AO)
        if ao_path is not None:
            md.ao_img = _decode_texture(loader, ao_path, max_dim)
        emissive_path = _texture_path(textures, _TEX_EMISSIVE)
        if emissive_path is not None:
            md.emissive_img = _decode_texture(loader, emissive_path, max_dim)

    md.base_color_factor = _vector_param(material, "g_vColorTint", [1.0, 1.0, 1.0, 1.0])
    md.metallic_factor = 1.0 if md.mr_img is not None else _float_param(material, "g_flMetalness", 0.0)
    md.roughness_factor = 1.0
    md.emissive_factor = (0.0, 0.0, 0.0)
    md.wrap_u = _int_param(material, "g_nTextureAddressModeU", 0)
    md.wrap_v = _int_param(material, "g_nTextureAddressModeV", 0)

    if _int_param(material, "F_TRANSLUCENT"):
        md.alpha_mode = "BLEND"
    elif _int_param(material, "F_ALPHA_TEST"):
        md.alpha_mode = "MASK"
        md.alpha_cutoff = _float_param(material, "g_flAlphaTestReference", 0.5)
    md.double_sided = bool(_int_param(material, "F_RENDER_BACKFACES"))
    return md


# Model reading

def _draw_call_tint_alpha(vrf, draw_call) -> tuple:
    tint_kv = vrf.kv_scalar(draw_call, "m_vTintColor")
    tint = [1.0, 1.0, 1.0, 1.0]
    if tint_kv is not None:
        try:
            parsed = []
            for item in tint_kv:
                val = getattr(item, "Value", item)
                parsed.append(float(str(val)))
            if len(parsed) >= 3:
                tint[:len(parsed)] = parsed[:4]
        except Exception:
            pass

    alpha_kv = vrf.kv_scalar(draw_call, "m_flAlpha")
    alpha = 1.0
    if alpha_kv is not None:
        try:
            alpha = float(str(alpha_kv))
        except Exception:
            pass

    return tuple(tint), alpha


def _mesh_list(loader, model):
    """Embedded meshes plus any referenced .vmesh_c, LoD0 and active mesh groups only."""
    from src.dotnet import _suppress_dotnet_console
    vrf = _Vrf.get()

    mesh_groups = list(model.GetMeshGroups()) if hasattr(model, "GetMeshGroups") else []
    default_groups = set(model.GetDefaultMeshGroups()) if hasattr(model, "GetDefaultMeshGroups") else set()
    default_mask = 0
    if mesh_groups and default_groups:
        for i, name in enumerate(mesh_groups):
            if name in default_groups:
                default_mask |= (1 << i)

    masks = [int(str(x)) for x in vrf.kv_array(model.Data, "m_refMeshGroupMasks")] if hasattr(model, "Data") else []

    meshes = []
    for idx, entry in enumerate(model.GetEmbeddedMeshesAndLoD()):
        # (Mesh, lodMask, name) — bit 0 is LoD0.
        lod = int(entry.Item2)
        if lod & 1 or lod == 0:
            if default_mask and idx < len(masks):
                mesh_mask = masks[idx]
                if mesh_mask != 0 and not (mesh_mask & default_mask):
                    continue
            meshes.append(entry.Item1)

    for entry in model.GetReferenceMeshNamesAndLoD():
        # Reference meshes are rare for CS2 props, so the tuple shape is handled
        # defensively rather than assumed.
        name = getattr(entry, "Item1", None) or getattr(entry, "MeshName", None)
        lod = getattr(entry, "Item2", 0)
        if name is None:
            continue
        try:
            if int(lod) and not int(lod) & 1:
                continue
        except Exception:
            pass
        try:
            with _suppress_dotnet_console():
                resource = loader.LoadFileCompiled(str(name))
            if resource is not None:
                meshes.append(resource.DataBlock)
        except Exception:
            continue
    return meshes


def load_model(resource_path: str, context_addon: str = None,
               max_texture_dim: int = None, base_color_only: bool = False,
               skin: int = 0) -> Optional[MeshData]:
    """Read a compiled model into :class:`MeshData`, or None on failure.

    Drop-in replacement for ``decompile_model_to_glb`` + ``load_glb``; the same
    ``max_texture_dim`` / ``base_color_only`` knobs bound per-material texture
    work for callers that only shade with albedo.
    """
    import copy
    from src.dotnet import _suppress_dotnet_console

    vrf = _Vrf.get()
    addon_name, rel_path = _resolve(resource_path, context_addon)
    loader = _get_loader(addon_name, rel_path)
    if loader is None:
        return None

    try:
        with _suppress_dotnet_console():
            resource = loader.LoadFileCompiled(rel_path)
    except Exception as exc:
        print(f"[vmdl_reader] Failed to load {rel_path}: {exc}")
        return None
    if resource is None:
        return None

    model = resource.DataBlock
    if max_texture_dim is None:
        max_texture_dim = MAX_TEXTURE_DIM

    # Skin material overrides
    skin_map = {}
    if skin != 0 and hasattr(model, "GetMaterialGroups"):
        try:
            mat_groups = list(model.GetMaterialGroups())
            if len(mat_groups) > skin and skin > 0:
                default_mats = list(mat_groups[0].Item2)
                skin_mats = list(mat_groups[skin].Item2)
                for orig, new_mat in zip(default_mats, skin_mats):
                    skin_map[str(orig)] = str(new_mat)
        except Exception:
            pass

    all_vertices, all_normals, all_uvs, all_indices = [], [], [], []
    submeshes = []
    material_cache = {}
    vertex_total = 0     # running vertex offset across every buffer appended
    index_cursor = 0     # running index (element) offset

    for mesh in _mesh_list(loader, model):
        vbib = mesh.VBIB
        buffer_base = {}          # vertex buffer index -> offset in the flat array
        for buf_index, vertex_buffer in enumerate(vbib.VertexBuffers):
            positions = _attribute(vbib, vertex_buffer, "POSITION", 3)
            if positions is None:
                continue
            count = len(positions)
            normals = _attribute(vbib, vertex_buffer, "NORMAL", 3)
            if normals is None or len(normals) != count:
                normals = np.zeros((count, 3), dtype=np.float32)
            uvs = _attribute(vbib, vertex_buffer, "TEXCOORD", 2)
            if uvs is None or len(uvs) != count:
                uvs = np.zeros((count, 2), dtype=np.float32)

            buffer_base[buf_index] = vertex_total
            all_vertices.append(positions)
            all_normals.append(normals)
            all_uvs.append(uvs)
            vertex_total += count

        if not buffer_base:
            continue

        index_buffers = [_index_array(ib) for ib in vbib.IndexBuffers]

        for scene_object in vrf.kv_array(mesh.Data, "m_sceneObjects"):
            for draw_call in vrf.kv_array(scene_object, "m_drawCalls"):
                start = vrf.kv_int(draw_call, "m_nStartIndex", 0)
                count = vrf.kv_int(draw_call, "m_nIndexCount", 0)
                base_vertex = vrf.kv_int(draw_call, "m_nBaseVertex", 0)
                if count <= 0:
                    continue

                bound = vrf.kv_array(draw_call, "m_vertexBuffers")
                buf_index = vrf.kv_int(bound[0], "m_hBuffer", 0) if len(bound) else 0
                if buf_index not in buffer_base:
                    continue

                ib_handle = 0
                try:
                    ib_kv = vrf.kv("GetSubCollection", draw_call, "m_indexBuffer")
                    if ib_kv is not None:
                        ib_handle = vrf.kv_int(ib_kv, "m_hBuffer", 0)
                except Exception:
                    pass
                if ib_handle >= len(index_buffers):
                    continue

                indices = index_buffers[ib_handle][start:start + count]
                if indices.size == 0:
                    continue
                all_indices.append(indices + (buffer_base[buf_index] + base_vertex))

                material_path = vrf.kv_str(draw_call, "m_material", None)
                material_path = str(material_path) if material_path else ""
                if material_path in skin_map:
                    material_path = skin_map[material_path]

                material = material_cache.get(material_path)
                if material is None:
                    material = (_load_material(loader, material_path, max_texture_dim, base_color_only)
                                if material_path else MaterialData())
                    material_cache[material_path] = material

                tint_vec, draw_alpha = _draw_call_tint_alpha(vrf, draw_call)
                if tint_vec != (1.0, 1.0, 1.0, 1.0) or draw_alpha != 1.0:
                    material = copy.copy(material)
                    r = material.base_color_factor[0] * tint_vec[0]
                    g = material.base_color_factor[1] * tint_vec[1]
                    b = material.base_color_factor[2] * tint_vec[2]
                    a = material.base_color_factor[3] * tint_vec[3] * draw_alpha
                    material.base_color_factor = (r, g, b, a)

                submeshes.append(SubMeshData(index_offset=index_cursor,
                                             index_count=int(indices.size),
                                             material=material))
                index_cursor += int(indices.size)

    if not all_vertices or not all_indices:
        return None

    vertices = np.vstack(all_vertices).astype(np.float32)
    normals = np.vstack(all_normals).astype(np.float32)
    uvs = np.vstack(all_uvs).astype(np.float32)
    indices = np.concatenate(all_indices).astype(np.uint32)

    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths < 1e-8] = 1.0
    normals = (normals / lengths).astype(np.float32)

    return MeshData(
        vertices=vertices,
        normals=normals,
        indices=indices,
        uvs=uvs,
        bbox_min=vertices.min(axis=0),
        bbox_max=vertices.max(axis=0),
        submeshes=submeshes,
    )
