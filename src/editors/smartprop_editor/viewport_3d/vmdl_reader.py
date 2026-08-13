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
import functools
import os
import re
import threading
from typing import Optional, List

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
        Resource = setup_vrf()[0]

        import System
        self.System = System
        # VRF lives in its own AssemblyLoadContext (dotnet.py VRF_ALC), so
        # Assembly.Load by name — which only searches the default one — misses it.
        asm = Resource.Assembly
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


def _attribute(vbib, vertex_buffer, semantic: str, components: int, semantic_index: int = 0) -> Optional[np.ndarray]:
    """Read one vertex attribute as (N, components) float32, or None if absent.

    Decoding is delegated to VRF, which already handles every DXGI format the
    engine ships (half floats, normalised integers, hemi-octahedral normals),
    so there is no format table to maintain here.
    """
    field = None
    for candidate in vertex_buffer.InputLayoutFields:
        if str(candidate.SemanticName) == semantic and int(candidate.SemanticIndex) == semantic_index:
            field = candidate
            break
    if field is None and semantic_index > 0:
        # A higher semantic index was requested (e.g. TEXCOORD1) but is absent.
        # Fall back to index 0 specifically -- NOT "any field of this semantic"
        # -- so a diffuse request never silently picks up an unrelated channel
        # (e.g. a lightmap stored as TEXCOORD1 while TEXCOORD0 is the diffuse).
        for candidate in vertex_buffer.InputLayoutFields:
            if str(candidate.SemanticName) == semantic and int(candidate.SemanticIndex) == 0:
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


def _transform_uvs(uvs: np.ndarray, scale: tuple, offset: tuple, center: tuple, rotation_deg: float) -> np.ndarray:
    if uvs is None or len(uvs) == 0:
        return uvs
    sx, sy = float(scale[0]), float(scale[1])
    ox, oy = float(offset[0]), float(offset[1])
    cx, cy = float(center[0]), float(center[1])

    if sx == 1.0 and sy == 1.0 and ox == 0.0 and oy == 0.0 and rotation_deg == 0.0:
        return uvs

    res = uvs.copy()
    u = res[:, 0] - cx
    v = res[:, 1] - cy

    if rotation_deg != 0.0:
        rad = np.radians(rotation_deg)
        cos_r, sin_r = np.cos(rad), np.sin(rad)
        u_rot = u * cos_r - v * sin_r
        v_rot = u * sin_r + v * cos_r
        u, v = u_rot, v_rot

    res[:, 0] = u * sx + cx + ox
    res[:, 1] = v * sy + cy + oy
    return res


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
        # GenerateBitmap's row 0 is the image top, the same origin PNG/glTF/VRF
        # all assume, so no row reorientation happens here.  GL's glTexImage2D
        # stores that top row at t=0 (image bottom), so the vertex shader
        # applies the matching ``1.0 - uv.y`` V-flip (see
        # shaders.MODEL_VERTEX_SHADER).  SKBitmap hands back BGRA; GL wants RGBA.
        return np.ascontiguousarray(pixels[:, :, [2, 1, 0, 3]])
    except Exception:
        return None


def _nearest_resize(img: np.ndarray, height: int, width: int) -> np.ndarray:
    rows = (np.arange(height) * (img.shape[0] / height)).astype(np.int32).clip(0, img.shape[0] - 1)
    cols = (np.arange(width) * (img.shape[1] / width)).astype(np.int32).clip(0, img.shape[1] - 1)
    return img[rows][:, cols]


# csgo_environment / csgo_environment_blend
#
# Both compile to the same VRF shader (csgo_environment.frag.slang) and share a
# channel layout that is NOT the generic g_tMetalness/g_tAmbientOcclusion one
# used elsewhere in this file:
#   g_tColor{N}.rgb   sRGB albedo, layer N
#   g_tColor{N}.a     ambient occlusion (or, when F_ALPHA_TEST: the cutout mask
#                     — AO then comes from g_tHeight{N}.b instead)
#   g_tNormal{N}.rg   hemi-octahedron-encoded tangent normal (see
#                     _decode_hemi_oct_normal), .b = roughness
#   g_tHeight{N}.a    metalness (when g_bMetalness{N}, default true)
#   g_tHeight{N}.r    per-pixel height, used to blend layer 2 over layer 1
# A second layer (g_tColor2 present) is height-blended over the first.

def _decode_hemi_oct_normal(rg: np.ndarray) -> np.ndarray:
    """Decode a hemi-octahedron-encoded normal map's RG channels to a standard
    tangent-space RGB normal map, so the existing shader's plain ``* 2 - 1``
    decode reconstructs the same vector.

    Formula: ValveResourceFormat's ``common/utils.slang::DecodeHemiOctahedronNormal``.
    """
    x = rg[..., 0].astype(np.float32) / 255.0
    y = rg[..., 1].astype(np.float32) / 255.0
    tx = x + y - 1.003922
    ty = x - y
    tz = 1.0 - np.abs(tx) - np.abs(ty)
    length = np.sqrt(tx * tx + ty * ty + tz * tz)
    length[length < 1e-8] = 1.0
    out = np.empty(rg.shape[:2] + (3,), dtype=np.uint8)
    out[..., 0] = np.clip((tx / length * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    out[..., 1] = np.clip((-ty / length * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    out[..., 2] = np.clip((tz / length * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    return out


def _height_blend_weight(height1: np.ndarray, height2: np.ndarray,
                          zero1: float, zero2: float, scale1: float, scale2: float,
                          softness: float = 0.5) -> np.ndarray:
    """Per-pixel [0, 1] weight for layer 2, from the two raw (0-255) height maps.

    ponytail: the real shader's weight also comes from a per-vertex painted
    blend value and edge-band shaping we have no data for (no vertex attribute
    carries it, and it isn't a material param) — this is just its base
    crossfade term. Good enough for a preview; not a byte-exact match. Upgrade
    path: read the vertex COLOR/blend attribute if VBIB reading ever needs to
    match CS2 exactly.
    """
    h1 = (height1.astype(np.float32) / 255.0 - zero1) * scale1
    h2 = (height2.astype(np.float32) / 255.0 - zero2) * scale2
    return np.clip(0.5 + (h2 - h1) / (2.0 * max(softness, 1e-4)), 0.0, 1.0)


def _load_environment_layer(loader, textures: dict, suffix: str, max_dim: Optional[int]):
    """Read one numbered layer's raw decoded RGBA color/normal/height textures."""
    color_path = textures.get(f"g_tColor{suffix}")
    normal_path = textures.get(f"g_tNormal{suffix}")
    height_path = textures.get(f"g_tHeight{suffix}")
    color = _decode_texture(loader, color_path, max_dim) if color_path else None
    normal = _decode_texture(loader, normal_path, max_dim) if normal_path else None
    height = _decode_texture(loader, height_path, max_dim) if height_path else None
    return color, normal, height


def _composite_environment_material(loader, material, textures: dict, max_dim: Optional[int],
                                     base_color_only: bool, alpha_tested: bool) -> Optional[dict]:
    """Build base_color/normal/mr/ao images for a csgo_environment[_blend] material.

    Returns None if this isn't an environment-family material (no g_tHeight1),
    so the caller falls back to the generic texture-key reader.
    """
    if "g_tHeight1" not in textures:
        return None

    color1, normal1, height1 = _load_environment_layer(loader, textures, "1", max_dim)
    if color1 is None:
        return None
    h, w = color1.shape[0], color1.shape[1]

    def fit(img):
        if img is None or img.shape[:2] == (h, w):
            return img
        return _nearest_resize(img, h, w)

    color, normal, height = color1, fit(normal1), fit(height1)

    if not base_color_only and "g_tColor2" in textures:
        color2, normal2, height2 = _load_environment_layer(loader, textures, "2", max_dim)
        color2 = fit(color2)
        if color2 is not None:
            zero1 = _float_param(material, "g_flHeightMapZeroPoint1", 0.5)
            zero2 = _float_param(material, "g_flHeightMapZeroPoint2", 0.5)
            scale1 = _float_param(material, "g_flHeightMapScale1", 1.0)
            scale2 = _float_param(material, "g_flHeightMapScale2", 1.0)
            normal2 = fit(normal2)
            height2 = fit(height2)
            h1_src = height[..., 0] if height is not None else np.zeros((h, w), np.uint8)
            h2_src = height2[..., 0] if height2 is not None else np.zeros((h, w), np.uint8)
            weight2 = _height_blend_weight(h1_src, h2_src, zero1, zero2, scale1, scale2)[..., None]

            color = (color.astype(np.float32) * (1 - weight2) + color2.astype(np.float32) * weight2).astype(np.uint8)
            if normal is not None and normal2 is not None:
                normal = (normal.astype(np.float32) * (1 - weight2) + normal2.astype(np.float32) * weight2).astype(np.uint8)
            if height is not None and height2 is not None:
                height = (height.astype(np.float32) * (1 - weight2) + height2.astype(np.float32) * weight2).astype(np.uint8)

    out = {"base_color_img": color}

    if base_color_only:
        return out

    if normal is not None:
        decoded = _decode_hemi_oct_normal(normal[..., :2])
        normal_img = np.full((h, w, 4), 255, dtype=np.uint8)
        normal_img[..., :3] = decoded
        out["normal_img"] = normal_img

    metal_on = bool(_int_param(material, "g_bMetalness1", 1))
    mr = np.zeros((h, w, 4), dtype=np.uint8)
    mr[..., 3] = 255
    if normal is not None:
        mr[..., 1] = normal[..., 2]                          # roughness from normal.b
    if metal_on and height is not None:
        mr[..., 2] = height[..., 3]                           # metalness from height.a
    out["mr_img"] = mr

    if alpha_tested:
        # Alpha-test cutout owns color.a; AO comes from height.b instead.
        if height is not None:
            ao = np.full((h, w, 4), 255, dtype=np.uint8)
            ao[..., 0] = height[..., 2]
            out["ao_img"] = ao
    else:
        ao = np.full((h, w, 4), 255, dtype=np.uint8)
        ao[..., 0] = color[..., 3]
        out["ao_img"] = ao
        out["base_color_img"] = color.copy()
        out["base_color_img"][..., 3] = 255                  # alpha was AO, not opacity

    return out


def _vector_param(material, name, default):
    for entry in material.VectorParams:
        if str(entry.Key) == name:
            v = entry.Value
            out = list(default)
            comps = ("X", "Y", "Z", "W")[:len(out)]
            for i, comp in enumerate(comps):
                try:
                    if hasattr(v, comp):
                        out[i] = float(getattr(v, comp))
                except Exception:
                    pass
            # Vector3s in VRF (e.g. g_vColorTint) are stored as Vector4 with W=0.
            # For 4-element defaults (like RGBA color tints) where W is 0, preserve
            # default alpha so materials don't turn completely transparent.
            if len(default) == 4 and len(comps) == 4 and out[3] == 0.0 and default[3] != 0.0:
                out[3] = default[3]
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

    # F_ALPHA_TEST/F_TRANSLUCENT drive both which channel the environment-shader
    # path reads AO from (see _composite_environment_material) and md.alpha_mode
    # below, so read them once, up front.
    is_translucent = bool(_int_param(material, "F_TRANSLUCENT"))
    is_alpha_test = bool(_int_param(material, "F_ALPHA_TEST"))

    env = _composite_environment_material(
        loader, material, textures, max_dim, base_color_only,
        alpha_tested=is_translucent or is_alpha_test,
    )

    base_tex_name = None
    base_path = None
    for name in _TEX_BASE:
        if name in textures:
            base_tex_name = name
            base_path = textures[name]
            break

    if env is not None:
        md.base_color_img = env.get("base_color_img")
        md.normal_img = env.get("normal_img")
        md.mr_img = env.get("mr_img")
        md.ao_img = env.get("ao_img")
    else:
        if base_path is not None:
            md.base_color_img = _decode_texture(loader, base_path, max_dim)

        if not base_color_only:
            normal_path = _texture_path(textures, _TEX_NORMAL)
            normal_rgba = _decode_texture(loader, normal_path, max_dim) if normal_path else None
            if normal_rgba is not None:
                md.normal_img = normal_rgba

            metal_path = _texture_path(textures, _TEX_METAL)
            metal_img = _decode_texture(loader, metal_path, max_dim) if metal_path else None
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

    if not base_color_only:
        emissive_path = _texture_path(textures, _TEX_EMISSIVE)
        if emissive_path is not None:
            md.emissive_img = _decode_texture(loader, emissive_path, max_dim)

    md.base_color_factor = _vector_param(material, "g_vColorTint", [1.0, 1.0, 1.0, 1.0])
    md.metallic_factor = 1.0 if md.mr_img is not None else _float_param(material, "g_flMetalness", 0.0)
    md.roughness_factor = 1.0
    md.emissive_factor = (0.0, 0.0, 0.0)
    md.wrap_u = _int_param(material, "g_nTextureAddressModeU", 0)
    md.wrap_v = _int_param(material, "g_nTextureAddressModeV", 0)

    # Diffuse/albedo textures always read from TEXCOORD0 in Source 2: the
    # higher TEXCOORD indices (TEXCOORD1+) hold lightmaps or secondary unwraps.
    # g_nUVSet{N}'s trailing digit is a *shader texture-layer* selector (the
    # same N as in g_tColorN), NOT a TEXCOORD semantic index, so its value is
    # never used to pick the vertex channel -- confirmed across shipped CS2
    # models where every diffuse material carries g_nUVSet1=1 yet TEXCOORD0 is
    # the diffuse UV.
    md.uv_set = 0

    # The per-layer UV *transform* params (g_vTexCoordScale{N} etc.) ARE named
    # by the texture-layer suffix, so keep that suffix just for their lookup.
    if base_tex_name and base_tex_name.endswith("1"):
        layer_suffix = "1"
    elif base_tex_name and base_tex_name.endswith("2"):
        layer_suffix = "2"
    elif base_tex_name and base_tex_name.endswith("3"):
        layer_suffix = "3"
    else:
        layer_suffix = ""

    # Read UV transform parameters if specified
    scale_key = f"g_vTexCoordScale{layer_suffix}"
    offset_key = f"g_vTexCoordOffset{layer_suffix}"
    center_key = f"g_vTexCoordCenter{layer_suffix}"
    rot_key = f"g_flTexCoordRotation{layer_suffix}"

    md.uv_scale = _vector_param(material, scale_key, _vector_param(material, "g_vTexCoordScale", [1.0, 1.0]))[:2]
    md.uv_offset = _vector_param(material, offset_key, _vector_param(material, "g_vTexCoordOffset", [0.0, 0.0]))[:2]
    md.uv_center = _vector_param(material, center_key, _vector_param(material, "g_vTexCoordCenter", [0.5, 0.5]))[:2]
    md.uv_rotation = _float_param(material, rot_key, _float_param(material, "g_flTexCoordRotation", 0.0))

    if is_translucent:
        md.alpha_mode = "BLEND"
    elif is_alpha_test:
        md.alpha_mode = "MASK"
        md.alpha_cutoff = _float_param(material, "g_flAlphaTestReference", 0.5)
    md.double_sided = bool(_int_param(material, "F_RENDER_BACKFACES"))

    # When alpha testing/blending is enabled but base_color alpha is empty or missing,
    # check if the normal map holds the alpha cutout mask (common in Source 2 environment shaders).
    if md.alpha_mode in ("MASK", "BLEND") and md.normal_img is not None:
        norm_a = md.normal_img[..., 3]
        if md.base_color_img is None:
            h, w = norm_a.shape[:2]
            bg = np.full((h, w, 4), 255, dtype=np.uint8)
            bg[..., 3] = norm_a
            md.base_color_img = bg
        else:
            base_a = md.base_color_img[..., 3]
            if float(base_a.mean()) < 30.0 and float(norm_a.mean()) > 50.0:
                h, w = md.base_color_img.shape[:2]
                if norm_a.shape[:2] != (h, w):
                    norm_a = _nearest_resize(norm_a[..., None], h, w)[..., 0]
                md.base_color_img = md.base_color_img.copy()
                md.base_color_img[..., 3] = norm_a

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
                if len(parsed) == 3 or (len(parsed) == 4 and tint[3] == 0.0):
                    tint[3] = 1.0
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
        # Tuple: (Mesh mesh, int opt, string name, long lodMask)
        try:
            lod_mask = int(entry.Item4)
        except Exception:
            lod_mask = int(entry.Item2) if hasattr(entry, "Item2") else 1
        if lod_mask & 1:  # Bit 0 is LoD0
            if default_mask and idx < len(masks):
                mesh_mask = masks[idx]
                if mesh_mask != 0 and not (mesh_mask & default_mask):
                    continue
            meshes.append(entry.Item1)

    for entry in model.GetReferenceMeshNamesAndLoD():
        # Tuple: (int groupIndex, string name, long lodMask)
        name = getattr(entry, "Item2", None) or getattr(entry, "Item1", None) or getattr(entry, "MeshName", None)
        lod_mask = getattr(entry, "Item3", getattr(entry, "Item2", 1))
        if name is None or isinstance(name, int):
            continue
        try:
            if int(lod_mask) and not (int(lod_mask) & 1):
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
    vertex_total = 0     # running vertex offset across every draw call appended
    index_cursor = 0     # running index (element) offset

    for mesh in _mesh_list(loader, model):
        vbib = mesh.VBIB
        positions_by_buf = {}
        normals_by_buf = {}
        uv_cache = {}  # (buf_index, uv_set) -> np.ndarray

        for buf_index, vertex_buffer in enumerate(vbib.VertexBuffers):
            positions = _attribute(vbib, vertex_buffer, "POSITION", 3)
            if positions is None:
                continue
            count = len(positions)
            normals = _attribute(vbib, vertex_buffer, "NORMAL", 3)
            if normals is None or len(normals) != count:
                normals = np.zeros((count, 3), dtype=np.float32)

            positions_by_buf[buf_index] = positions
            normals_by_buf[buf_index] = normals

        if not positions_by_buf:
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
                if buf_index not in positions_by_buf:
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

                raw_indices = index_buffers[ib_handle][start:start + count]
                if raw_indices.size == 0:
                    continue

                real_indices = raw_indices + base_vertex
                pos_buf = positions_by_buf[buf_index]
                norm_buf = normals_by_buf[buf_index]
                buf_len = len(pos_buf)

                valid_mask = (real_indices >= 0) & (real_indices < buf_len)
                if not np.all(valid_mask):
                    real_indices = real_indices[valid_mask]
                    if real_indices.size == 0:
                        continue

                material_path = vrf.kv_str(draw_call, "m_material", None)
                material_path = str(material_path) if material_path else ""
                if material_path in skin_map:
                    material_path = skin_map[material_path]

                material = material_cache.get(material_path)
                if material is None:
                    material = (_load_material(loader, material_path, max_texture_dim, base_color_only)
                                if material_path else MaterialData())
                    material_cache[material_path] = material

                uv_set = int(getattr(material, "uv_set", 0))
                cache_key = (buf_index, uv_set)
                if cache_key not in uv_cache:
                    vb = vbib.VertexBuffers[buf_index]
                    uv_data = _attribute(vbib, vb, "TEXCOORD", 2, uv_set)
                    if uv_data is None or len(uv_data) != buf_len:
                        if uv_set != 0:
                            uv_data = _attribute(vbib, vb, "TEXCOORD", 2, 0)
                        if uv_data is None or len(uv_data) != buf_len:
                            uv_data = np.zeros((buf_len, 2), dtype=np.float32)
                    uv_cache[cache_key] = uv_data
                uv_buf = uv_cache[cache_key]

                draw_pos = pos_buf[real_indices]
                draw_norm = norm_buf[real_indices]
                draw_uv = uv_buf[real_indices]

                draw_indices = np.arange(len(real_indices), dtype=np.uint32) + vertex_total
                vertex_total += len(real_indices)

                all_vertices.append(draw_pos)
                all_normals.append(draw_norm)
                all_uvs.append(draw_uv)
                all_indices.append(draw_indices)

                tint_vec, draw_alpha = _draw_call_tint_alpha(vrf, draw_call)
                if tint_vec != (1.0, 1.0, 1.0, 1.0) or draw_alpha != 1.0:
                    material = copy.copy(material)
                    r = material.base_color_factor[0] * tint_vec[0]
                    g = material.base_color_factor[1] * tint_vec[1]
                    b = material.base_color_factor[2] * tint_vec[2]
                    a = material.base_color_factor[3] * tint_vec[3] * draw_alpha
                    material.base_color_factor = (r, g, b, a)

                submeshes.append(SubMeshData(index_offset=index_cursor,
                                             index_count=int(real_indices.size),
                                             material=material))
                index_cursor += int(real_indices.size)

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


@functools.lru_cache(maxsize=512)
def get_model_material_groups(resource_path: str, context_addon: str = None) -> List[str]:
    """
    Return a list of material group (skin) names available on the given model.
    Checks uncompiled source .vmdl on disk (content mounts) and compiled .vmdl_c (VPK / game).
    """
    if not resource_path or not isinstance(resource_path, str):
        return []

    path_clean = resource_path.strip().replace("\\", "/")
    if not path_clean:
        return []

    groups: List[str] = []

    # 1. Try uncompiled source .vmdl on disk
    from src.common import get_cs2_path
    from src.settings.common import get_addon_name, get_addon_dir

    active_addon = context_addon or get_addon_name() or "addon"
    addon_name, rel_path = _resolve(path_clean, active_addon)
    cs2_path = get_cs2_path()

    source_candidates: List[str] = []
    if os.path.isabs(path_clean) and os.path.isfile(path_clean):
        source_candidates.append(path_clean)

    if cs2_path:
        mounts = [os.path.join("csgo_addons", addon_name), "csgo", "csgo_imported", "csgo_core", "core"]
        if context_addon and context_addon != addon_name:
            mounts.insert(0, os.path.join("csgo_addons", context_addon))
        for m in mounts:
            source_candidates.append(os.path.join(cs2_path, "content", m, rel_path.replace("/", os.sep)))

    addon_dir = get_addon_dir()
    if addon_dir:
        source_candidates.append(os.path.join(addon_dir, rel_path.replace("/", os.sep)))

    for candidate in source_candidates:
        if candidate.endswith(".vmdl_c"):
            candidate = candidate[:-2]
        if not candidate.endswith(".vmdl"):
            candidate += ".vmdl"
        if os.path.isfile(candidate):
            try:
                import keyvalues3 as kv3
                kv_data = kv3.read(candidate).value
                root = kv_data.get("rootNode", {})
                for child in root.get("children", []):
                    if child.get("_class") == "MaterialGroupList":
                        for mg in child.get("children", []):
                            cls_name = mg.get("_class", "")
                            name = mg.get("name")
                            if cls_name == "DefaultMaterialGroup" and not name:
                                name = "default"
                            if name and name not in groups:
                                groups.append(str(name))
                if groups:
                    return groups
            except Exception:
                try:
                    with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    if "DefaultMaterialGroup" in text and "default" not in groups:
                        groups.append("default")
                    for m in re.finditer(r'_class\s*=\s*"MaterialGroup"\s*[\s\S]*?name\s*=\s*"([^"]+)"', text):
                        name = m.group(1).strip()
                        if name and name not in groups:
                            groups.append(name)
                    if groups:
                        return groups
                except Exception:
                    pass

    # 2. Try compiled model via VRF
    try:
        from src.dotnet import setup_vrf, _suppress_dotnet_console
        setup_vrf()
        loader = _get_loader(addon_name, rel_path)
        if loader is not None:
            with _suppress_dotnet_console():
                resource = loader.LoadFileCompiled(rel_path)
            if resource is not None:
                model = resource.DataBlock
                if hasattr(model, "GetMaterialGroups"):
                    mat_groups = list(model.GetMaterialGroups())
                    for g in mat_groups:
                        name = getattr(g, "Item1", None) or getattr(g, "Name", None)
                        if name is None and hasattr(g, "Key"):
                            name = g.Key
                        if name is None:
                            name = str(g)
                        name = str(name).strip()
                        if name and name not in groups:
                            groups.append(name)
    except Exception:
        pass

    return groups

