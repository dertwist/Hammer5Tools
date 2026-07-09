"""
Mesh loading, GPU buffer management, and asynchronous model decompilation.
Handles GLB → CPU mesh data → GPU upload, with caching at every level.
"""
import os
import traceback
from typing import Optional, Dict
from dataclasses import dataclass, field

import numpy as np

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Slot


# ---------------------------------------------------------------------------
# CPU-side mesh data (loaded from GLB, not yet on GPU)
# ---------------------------------------------------------------------------

@dataclass
class MaterialData:
    """CPU-side PBR material extracted from a glTF/GLB material.

    Textures are kept as ready-to-upload RGBA uint8 arrays (already downscaled
    and vertically flipped for OpenGL) so the GL thread only has to call
    glTexImage2D — no PIL decode on upload, and no wasteful PNG re-encode during
    load.  Channel conventions follow the glTF 2.0 metallic-roughness spec, which
    is what VRF's GltfModelExporter writes:
        base_color_img  — sRGB albedo (may carry alpha for MASK/BLEND)
        normal_img      — tangent-space normal map (linear RGB, +Y up)
        mr_img          — G = roughness, B = metalness (linear)
        ao_img          — R = ambient occlusion (linear)
        emissive_img    — sRGB emissive
    """
    name: str = ""
    base_color_img: Optional[np.ndarray] = None   # (H, W, 4) uint8, GL-oriented
    normal_img: Optional[np.ndarray] = None
    mr_img: Optional[np.ndarray] = None
    ao_img: Optional[np.ndarray] = None
    emissive_img: Optional[np.ndarray] = None
    base_color_factor: tuple = (1.0, 1.0, 1.0, 1.0)
    metallic_factor: float = 1.0
    roughness_factor: float = 1.0
    emissive_factor: tuple = (0.0, 0.0, 0.0)
    alpha_mode: str = "OPAQUE"     # "OPAQUE" | "MASK" | "BLEND"
    alpha_cutoff: float = 0.5
    double_sided: bool = False


@dataclass
class SubMeshData:
    """A contiguous index range within a MeshData that shares one material."""
    index_offset: int              # first index (element count, not bytes)
    index_count: int
    material: MaterialData = field(default_factory=MaterialData)


@dataclass
class MeshData:
    """CPU-side mesh data extracted from a GLB file."""
    vertices: np.ndarray          # (N, 3) float32
    normals: np.ndarray           # (N, 3) float32
    indices: np.ndarray           # (M,) uint32
    uvs: Optional[np.ndarray]     # (N, 2) float32 or None
    bbox_min: np.ndarray          # (3,) float32
    bbox_max: np.ndarray          # (3,) float32
    submeshes: list = field(default_factory=list)   # list[SubMeshData]


@dataclass
class GPUMaterial:
    """GPU-side material: texture handles + scalar factors + alpha state."""
    base_tex: int = 0
    normal_tex: int = 0
    mr_tex: int = 0
    ao_tex: int = 0
    emissive_tex: int = 0
    base_color_factor: tuple = (1.0, 1.0, 1.0, 1.0)
    metallic_factor: float = 1.0
    roughness_factor: float = 1.0
    emissive_factor: tuple = (0.0, 0.0, 0.0)
    alpha_mode: str = "OPAQUE"
    alpha_cutoff: float = 0.5
    double_sided: bool = False

    @property
    def is_transparent(self) -> bool:
        return self.alpha_mode == "BLEND"


@dataclass
class GPUSubMesh:
    """GPU draw range referencing a GPUMaterial."""
    index_offset: int              # in indices
    index_count: int
    material: GPUMaterial = field(default_factory=GPUMaterial)


@dataclass
class GPUMesh:
    """GPU-uploaded mesh handles (VAO, VBO, EBO) plus its material submeshes."""
    vao: int = 0
    vbo: int = 0
    ebo: int = 0
    index_count: int = 0           # total, used for picking / single-draw passes
    submeshes: list = field(default_factory=list)   # list[GPUSubMesh]
    textures: list = field(default_factory=list)    # all owned GL texture ids
    bbox_min: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    bbox_max: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))

    @property
    def has_texture(self) -> bool:
        return any(sm.material.base_tex for sm in self.submeshes)


# ---------------------------------------------------------------------------
# glTF -> Source coordinate conversion
# ---------------------------------------------------------------------------
# VRF's GltfModelExporter writes geometry in glTF space: Y-up and in *metres*
# (1 Source inch = 0.0254 m).  trimesh preserves that frame, and load_glb() bakes
# the node transform into the vertices, so the loaded verts are Y-up metres.  The
# rest of the viewport works in Source space (Z-up, inches) — grid cells, gizmo,
# positions from the document tree — and only converts to GL at draw time via
# SOURCE2_TO_GL.  So undo VRF's conversion here and hand back geometry in raw
# Source space (Z-up, inches).
#
# VRF cyclically permutes the axes on export: glTF = (S_Y, S_Z, S_X), i.e. the
# Source length axis (X) becomes glTF X, width (Y) becomes glTF Z, and up (Z)
# becomes glTF Y.  The inverse (glTF -> Source) is therefore:
#       Source = (glTF_Z, glTF_X, glTF_Y) / 0.0254
# This is a proper rotation (det +1): the model comes back upright (roof up /
# wheels down) and un-mirrored, with its geometry in the same Source frame as the
# per-element positions read from the .vsmart tree.  Verified against
# cargovan_01: the body footprint (Source X ±39, Y [-90,121]) contains all four
# wheel elements (X ±35, Y +99/-56), so the assembly lines up.  Getting the up
# sign wrong flips the model upside down; swapping the horizontal axes rotates
# the body 90° away from the tree-driven wheel positions.
_VRF_GLTF_SCALE = 0.0254  # Source inch -> glTF metre
# Axis-swap (proper rotation), used for direction vectors (normals).
_GLTF_TO_SOURCE_ROT = np.array([
    [ 0.0,  0.0,  1.0],
    [ 1.0,  0.0,  0.0],
    [ 0.0,  1.0,  0.0],
], dtype=np.float32)
# Axis-swap + inch scale, used for positions.
_GLTF_TO_SOURCE = _GLTF_TO_SOURCE_ROT / _VRF_GLTF_SCALE


# ---------------------------------------------------------------------------
# Material extraction helpers
# ---------------------------------------------------------------------------

# Preview textures are capped to this size.  Downscaling on the (background) load
# thread bounds both VRAM and the per-texture CPU cost.
MAX_TEXTURE_DIM = 1024


def _image_to_rgba_array(img) -> Optional[np.ndarray]:
    """Convert a trimesh/PIL image to a GL-ready RGBA uint8 array, or None.

    Downscales to ``MAX_TEXTURE_DIM``, converts to RGBA and flips vertically so
    the GL upload can hand the bytes straight to glTexImage2D.  Runs on the load
    worker thread — deliberately doing all the pixel work here (not a PNG
    round-trip) is the bulk of the loading speed-up.
    """
    if img is None:
        return None
    try:
        from PIL import Image
        im = img
        if im.width > MAX_TEXTURE_DIM or im.height > MAX_TEXTURE_DIM:
            im = im.copy()
            # Bilinear is plenty for a preview and far cheaper than Lanczos.
            im.thumbnail((MAX_TEXTURE_DIM, MAX_TEXTURE_DIM), Image.BILINEAR)
        im = im.convert("RGBA").transpose(Image.FLIP_TOP_BOTTOM)  # GL is bottom-up
        return np.asarray(im, dtype=np.uint8)
    except Exception:
        return None


def _rgba_factor(value, default):
    """Normalise a trimesh color factor to a 0..1 float tuple.

    trimesh stores baseColorFactor as uint8 RGBA (0..255) but emissiveFactor as
    float (0..1); this normalises either form.  ``default`` sets the length.
    """
    if value is None:
        return default
    try:
        arr = np.asarray(value, dtype=np.float64).flatten()
    except Exception:
        return default
    if arr.size == 0:
        return default
    # Heuristic: any component > 1 means the values are 0..255 integers.
    if np.max(arr) > 1.0:
        arr = arr / 255.0
    out = list(default)
    for i in range(min(len(out), arr.size)):
        out[i] = float(arr[i])
    return tuple(out)


def _extract_material(geom, cache: dict) -> MaterialData:
    """Build a MaterialData for a trimesh geometry, deduped by material identity.

    ``cache`` maps id(trimesh_material) -> MaterialData so instances that share a
    material don't re-process the same textures.  Translucency comes solely from
    the glTF material's own ``alphaMode`` / base alpha as written by VRF — no name
    guessing, which wrongly tagged opaque "window"/"glass"/"blend"-named frame
    materials as see-through.
    """
    mat_obj = getattr(getattr(geom, "visual", None), "material", None)
    key = id(mat_obj)
    if key in cache:
        return cache[key]

    md = MaterialData()
    if mat_obj is not None:
        md.name = str(getattr(mat_obj, "name", "") or "")
        # glTF PBRMaterial exposes the named textures; SimpleMaterial only .image.
        base_img = getattr(mat_obj, "baseColorTexture", None)
        if base_img is None:
            base_img = getattr(mat_obj, "image", None)
        md.base_color_img = _image_to_rgba_array(base_img)
        md.normal_img = _image_to_rgba_array(getattr(mat_obj, "normalTexture", None))
        md.mr_img = _image_to_rgba_array(getattr(mat_obj, "metallicRoughnessTexture", None))
        md.ao_img = _image_to_rgba_array(getattr(mat_obj, "occlusionTexture", None))
        md.emissive_img = _image_to_rgba_array(getattr(mat_obj, "emissiveTexture", None))

        md.base_color_factor = _rgba_factor(getattr(mat_obj, "baseColorFactor", None), [1.0, 1.0, 1.0, 1.0])
        mf = getattr(mat_obj, "metallicFactor", None)
        md.metallic_factor = float(mf) if mf is not None else 1.0
        rf = getattr(mat_obj, "roughnessFactor", None)
        md.roughness_factor = float(rf) if rf is not None else 1.0
        md.emissive_factor = _rgba_factor(getattr(mat_obj, "emissiveFactor", None), [0.0, 0.0, 0.0])

        am = getattr(mat_obj, "alphaMode", None)
        if isinstance(am, bytes):
            am = am.decode("ascii", "ignore")
        md.alpha_mode = str(am).upper() if am else "OPAQUE"
        ac = getattr(mat_obj, "alphaCutoff", None)
        md.alpha_cutoff = float(ac) if ac is not None else 0.5
        ds = getattr(mat_obj, "doubleSided", None)
        md.double_sided = bool(ds) if ds is not None else False

    cache[key] = md
    return md


# ---------------------------------------------------------------------------
# GLB loader (using trimesh)
# ---------------------------------------------------------------------------

def load_glb(path: str) -> Optional[MeshData]:
    """Load a .glb file and return MeshData, or None on failure."""
    try:
        import trimesh

        scene = trimesh.load(path, force='scene', process=False)

        material_cache: dict = {}

        all_vertices = []
        all_normals = []
        all_uvs = []
        all_indices = []
        submeshes = []       # SubMeshData per instance (index range + material)
        offset = 0           # running vertex offset
        index_cursor = 0     # running index (element) offset

        # Pair every geometry *instance* with its world transform via the scene
        # graph.  Iterating scene.geometry directly and looking transforms up by
        # geometry key is unreliable — trimesh's node names don't always match
        # geometry keys (e.g. a mesh split by material yields '.foo' and
        # '.foo_1', but the graph nodes are '.foo_ab12' / '.foo_cd34').  Any
        # instance that misses its transform stays in a different coordinate
        # space/scale from its siblings, so half the model ends up 39x too big.
        instances = []
        try:
            node_names = list(scene.graph.nodes_geometry)
        except Exception:
            node_names = []
        if node_names:
            for node_name in node_names:
                try:
                    transform, geom_name = scene.graph[node_name]
                except Exception:
                    continue
                geom = scene.geometry.get(geom_name)
                if isinstance(geom, trimesh.Trimesh):
                    instances.append((geom, np.array(transform, dtype=np.float32)))
        else:
            # No usable scene graph — take geometries as-is (identity transform).
            for geom in scene.geometry.values():
                if isinstance(geom, trimesh.Trimesh):
                    instances.append((geom, np.eye(4, dtype=np.float32)))

        # Flatten all instances into one buffer, baking each world transform so
        # every instance shares the same glTF world space (Y-up, metres).
        for geom, transform in instances:
            verts = np.array(geom.vertices, dtype=np.float32)
            faces = np.array(geom.faces, dtype=np.uint32)
            norms = (np.array(geom.vertex_normals, dtype=np.float32)
                     if geom.vertex_normals is not None and len(geom.vertex_normals) > 0
                     else np.zeros_like(verts))

            if not np.allclose(transform, np.eye(4)):
                ones = np.ones((len(verts), 1), dtype=np.float32)
                verts = (np.hstack([verts, ones]) @ transform.T)[:, :3].astype(np.float32)
                # Rotate normals by the transform's linear part (uniform scale +
                # rotation); magnitude is fixed up by the final normalize.
                norms = (norms @ transform[:3, :3].T).astype(np.float32)

            uvs = None
            if geom.visual and hasattr(geom.visual, 'uv') and geom.visual.uv is not None:
                uvs = np.array(geom.visual.uv, dtype=np.float32)

            all_vertices.append(verts)
            all_normals.append(norms)
            if uvs is not None and len(uvs) == len(verts):
                all_uvs.append(uvs)
            else:
                all_uvs.append(np.zeros((len(verts), 2), dtype=np.float32))
            all_indices.append(faces + offset)

            # Record this instance as a submesh (index range + its material) so
            # every material renders with its own textures / blend mode.
            n_idx = int(faces.size)   # (F, 3) -> F*3 indices
            material = _extract_material(geom, material_cache)
            submeshes.append(SubMeshData(index_offset=index_cursor,
                                         index_count=n_idx,
                                         material=material))
            index_cursor += n_idx
            offset += len(verts)

        if not all_vertices:
            return None

        vertices = np.vstack(all_vertices)
        normals = np.vstack(all_normals)
        uvs_arr = np.vstack(all_uvs) if all_uvs else None
        indices = np.vstack(all_indices).flatten().astype(np.uint32)

        # Undo VRF's glTF (Y-up, metres) frame -> raw Source (Z-up, inches),
        # so downstream transforms and the grid share one coordinate system.
        vertices = (vertices @ _GLTF_TO_SOURCE.T).astype(np.float32)
        normals = (normals @ _GLTF_TO_SOURCE_ROT.T).astype(np.float32)
        # Renormalize: baking a scaled node transform changed normal lengths.
        n_len = np.linalg.norm(normals, axis=1, keepdims=True)
        n_len[n_len < 1e-8] = 1.0
        normals = (normals / n_len).astype(np.float32)

        bbox_min = vertices.min(axis=0)
        bbox_max = vertices.max(axis=0)

        return MeshData(
            vertices=vertices,
            normals=normals,
            indices=indices,
            uvs=uvs_arr,
            bbox_min=bbox_min,
            bbox_max=bbox_max,
            submeshes=submeshes,
        )

    except Exception as e:
        print(f"[MeshCache] Failed to load GLB {path}: {e}")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Async load worker
# ---------------------------------------------------------------------------

class _ModelLoadSignals(QObject):
    # (model_resource_path, MeshData or None).  MeshData is a plain Python object
    # carrying numpy arrays; passing it across the queued signal is thread-safe.
    loaded = Signal(str, object)


class _ModelLoadWorker(QRunnable):
    """Background worker: decompile (if needed) then parse+process the GLB.

    Doing the whole heavy path — VRF decompile, trimesh parse, and texture
    decode/downscale — off the UI thread keeps painting smooth.  Only the final
    GPU upload happens on the GL thread.  When ``glb_path`` is already known
    (cache hit) the decompile step is skipped entirely.
    """

    def __init__(self, model_resource_path: str, context_addon: str = None, glb_path: str = None):
        super().__init__()
        self.model_resource_path = model_resource_path
        self.context_addon = context_addon
        self.glb_path = glb_path
        self.signals = _ModelLoadSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        mesh = None
        try:
            glb = self.glb_path
            if not glb:
                from src.dotnet import decompile_model_to_glb
                glb = decompile_model_to_glb(self.model_resource_path, self.context_addon)
            if glb and os.path.exists(glb):
                mesh = load_glb(glb)   # trimesh parse + texture processing (heavy)
                if mesh is None:
                    # Empty/invalid GLB — remove so a later request re-decompiles.
                    try:
                        os.remove(glb)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[MeshCache] Model load failed for {self.model_resource_path}: {e}")
            mesh = None
        self.signals.loaded.emit(self.model_resource_path, mesh)


# ---------------------------------------------------------------------------
# Mesh Cache
# ---------------------------------------------------------------------------

class MeshCache(QObject):
    """
    Manages model decompilation, GLB loading, GPU upload, and caching.

    Workflow:
        1. request_model(resource_path) → queues decompilation if needed
        2. On decompilation complete → loads GLB into MeshData (CPU)
        3. On next paint → upload_pending() pushes to GPU (must be in GL context)
        4. get_gpu_mesh(resource_path) → returns GPUMesh or None
    """

    model_ready = Signal(str)     # Emitted when a model's GPU mesh is ready for rendering

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cpu_cache: Dict[str, MeshData] = {}
        self._gpu_cache: Dict[str, GPUMesh] = {}
        self._pending_upload: Dict[str, MeshData] = {}    # Waiting for GL context
        self._pending_unload: Dict[str, GPUMesh] = {}     # Waiting to be freed in GL context
        self._loading: set = set()                         # Currently decompiling/loading
        self._failed: set = set()                          # Failed decompilations
        self._thread_pool = QThreadPool()
        # Cap concurrency: first-time decompiles serialise on VRF's global lock,
        # but already-cached GLBs are parsed/textured in parallel, so a few worker
        # threads speed up multi-model scenes without oversubscribing the CPU.
        cpu = os.cpu_count() or 4
        self._thread_pool.setMaxThreadCount(max(2, min(4, cpu - 1)))

    def request_model(self, resource_path: str, context_addon: str = None):
        """Request a model to be loaded. Non-blocking; emits model_ready when done."""
        if not resource_path:
            return

        # Already loaded
        if resource_path in self._gpu_cache or resource_path in self._pending_upload:
            return
        # Already loading
        if resource_path in self._loading:
            return
        # Previously failed
        if resource_path in self._failed:
            return
        # Dispatch a background worker that does the whole load (decompile if the
        # GLB isn't cached, then parse + process textures) off the UI thread.  The
        # cheap cache lookup happens here so the worker can skip decompilation on a
        # hit; everything expensive runs in run().
        glb_path = self._find_cached_glb(resource_path, context_addon)
        self._loading.add(resource_path)
        worker = _ModelLoadWorker(resource_path, context_addon, glb_path)
        worker.signals.loaded.connect(self._on_model_loaded)
        self._thread_pool.start(worker)

    def _find_cached_glb(self, resource_path: str, context_addon: str = None) -> Optional[str]:
        """Check if a GLB file already exists in the cache."""
        from src.common import SmartPropEditor_Path
        from src.settings.common import get_addon_name

        import re

        normalized = resource_path.replace("\\", "/").strip("/")
        
        # Try to extract the addon name and convert to a relative path
        addon_match = re.search(r'/csgo_addons/([^/]+)/(.*)$', '/' + normalized, re.IGNORECASE)
        csgo_match = re.search(r'/csgo/(.*)$', '/' + normalized, re.IGNORECASE)
        
        addon_name = context_addon or get_addon_name() or "addon"
        if addon_match:
            addon_name = addon_match.group(1)
            normalized = addon_match.group(2)
        elif csgo_match:
            normalized = csgo_match.group(1)

        if not normalized.endswith(".vmdl"):
            if normalized.endswith(".vmdl_c"):
                normalized = normalized[:-2]
            else:
                normalized += ".vmdl"

        glb_subpath = normalized.rsplit(".", 1)[0] + ".glb"

        # Check addon cache first, then csgo cache
        for subfolder in [addon_name, "csgo"]:
            candidate = os.path.join(str(SmartPropEditor_Path), "cache", subfolder, glb_subpath)
            if os.path.exists(candidate):
                return candidate

        return None

    def _on_model_loaded(self, resource_path: str, mesh_data):
        """Runs on the UI thread when a load worker finishes (queued signal).

        The worker already did all the heavy CPU work, so this just stashes the
        MeshData for the next paint's GPU upload, or marks the model failed.
        """
        self._loading.discard(resource_path)
        # The model may have been pruned from the hierarchy while it loaded.
        if mesh_data is not None:
            self._cpu_cache[resource_path] = mesh_data
            self._pending_upload[resource_path] = mesh_data
            self.model_ready.emit(resource_path)
        else:
            self._failed.add(resource_path)

    def upload_pending(self):
        """
        Upload pending MeshData to GPU. MUST be called from within a valid GL context
        (e.g. inside paintGL or after makeCurrent).
        """
        from OpenGL import GL

        for resource_path, mesh_data in list(self._pending_upload.items()):
            try:
                gpu_mesh = self._upload_mesh(mesh_data)
                self._gpu_cache[resource_path] = gpu_mesh
            except Exception as e:
                print(f"[MeshCache] GPU upload failed for {resource_path}: {e}")
                self._failed.add(resource_path)
            finally:
                del self._pending_upload[resource_path]

    def prune(self, referenced_paths):
        """
        Drop every cached model not in ``referenced_paths`` so the cache mirrors
        what the hierarchy still uses.  GPU handles can't be freed here (this is
        called from the tree-edit path, outside a GL context), so they are queued
        in ``_pending_unload`` and released by ``release_unloaded`` on the next
        paint.  CPU/pending/failed entries — cheap Python objects — are dropped
        immediately so a later re-add reloads the model cleanly.
        """
        referenced = set(referenced_paths)

        # Rescue any mesh that was queued for unload but is referenced again
        # (rapid remove -> re-add within the debounce window) so it isn't freed
        # and needlessly reloaded.
        for path in list(self._pending_unload.keys()):
            if path in referenced:
                self._gpu_cache[path] = self._pending_unload.pop(path)

        for path in list(self._gpu_cache.keys()):
            if path not in referenced:
                self._pending_unload[path] = self._gpu_cache.pop(path)

        for path in list(self._pending_upload.keys()):
            if path not in referenced:
                del self._pending_upload[path]

        for path in list(self._cpu_cache.keys()):
            if path not in referenced:
                del self._cpu_cache[path]

        self._failed.difference_update(
            {path for path in self._failed if path not in referenced}
        )

    def release_unloaded(self):
        """
        Free GPU resources queued by ``prune``. MUST be called from within a valid
        GL context (e.g. inside paintGL).
        """
        if not self._pending_unload:
            return

        from OpenGL import GL

        for path, gpu_mesh in list(self._pending_unload.items()):
            try:
                GL.glDeleteVertexArrays(1, [gpu_mesh.vao])
                GL.glDeleteBuffers(2, [gpu_mesh.vbo, gpu_mesh.ebo])
                if gpu_mesh.textures:
                    GL.glDeleteTextures(len(gpu_mesh.textures), gpu_mesh.textures)
            except Exception as e:
                print(f"[MeshCache] GPU unload failed for {path}: {e}")
            finally:
                del self._pending_unload[path]

    def _upload_mesh(self, mesh_data: MeshData) -> GPUMesh:
        """Upload a MeshData to GPU buffers. Must be called in GL context."""
        from OpenGL import GL

        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)

        # Interleave vertex data: pos(3) + normal(3) + uv(2) = 8 floats per vertex
        n_verts = len(mesh_data.vertices)
        uvs = mesh_data.uvs if mesh_data.uvs is not None else np.zeros((n_verts, 2), dtype=np.float32)
        interleaved = np.hstack([mesh_data.vertices, mesh_data.normals, uvs]).astype(np.float32)

        vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, interleaved.nbytes, interleaved, GL.GL_STATIC_DRAW)

        stride = 8 * 4  # 8 floats × 4 bytes

        # Position — location 0
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)

        # Normal — location 1
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, GL.ctypes.c_void_p(12))
        GL.glEnableVertexAttribArray(1)

        # UV — location 2
        GL.glVertexAttribPointer(2, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, GL.ctypes.c_void_p(24))
        GL.glEnableVertexAttribArray(2)

        ebo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, ebo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, mesh_data.indices.nbytes, mesh_data.indices, GL.GL_STATIC_DRAW)

        GL.glBindVertexArray(0)

        # Upload each material's textures once (deduped by MaterialData identity),
        # then build a GPUSubMesh per index range.
        owned_textures = []
        gpu_material_cache = {}   # id(MaterialData) -> GPUMaterial
        gpu_submeshes = []

        for sm in (mesh_data.submeshes or []):
            mat = sm.material
            key = id(mat)
            gpu_mat = gpu_material_cache.get(key)
            if gpu_mat is None:
                gpu_mat = GPUMaterial(
                    base_tex=self._upload_texture(mat.base_color_img),
                    normal_tex=self._upload_texture(mat.normal_img),
                    mr_tex=self._upload_texture(mat.mr_img),
                    ao_tex=self._upload_texture(mat.ao_img),
                    emissive_tex=self._upload_texture(mat.emissive_img),
                    base_color_factor=mat.base_color_factor,
                    metallic_factor=mat.metallic_factor,
                    roughness_factor=mat.roughness_factor,
                    emissive_factor=mat.emissive_factor,
                    alpha_mode=mat.alpha_mode,
                    alpha_cutoff=mat.alpha_cutoff,
                    double_sided=mat.double_sided,
                )
                for tex in (gpu_mat.base_tex, gpu_mat.normal_tex, gpu_mat.mr_tex,
                            gpu_mat.ao_tex, gpu_mat.emissive_tex):
                    if tex:
                        owned_textures.append(tex)
                gpu_material_cache[key] = gpu_mat
            gpu_submeshes.append(GPUSubMesh(index_offset=sm.index_offset,
                                            index_count=sm.index_count,
                                            material=gpu_mat))

        # Fallback: a mesh with no material data still draws as one plain submesh.
        if not gpu_submeshes:
            gpu_submeshes.append(GPUSubMesh(index_offset=0,
                                            index_count=len(mesh_data.indices),
                                            material=GPUMaterial()))

        return GPUMesh(
            vao=vao,
            vbo=vbo,
            ebo=ebo,
            index_count=len(mesh_data.indices),
            submeshes=gpu_submeshes,
            textures=owned_textures,
            bbox_min=mesh_data.bbox_min.copy(),
            bbox_max=mesh_data.bbox_max.copy(),
        )

    def _upload_texture(self, img_data: Optional[np.ndarray]) -> int:
        """Upload a pre-decoded RGBA uint8 array as a 2D texture; 0 if absent.

        All the expensive pixel work (decode, downscale, flip) already happened on
        the load worker thread, so here we only touch GL — glTexImage2D + mipmaps.
        """
        if img_data is None or getattr(img_data, "size", 0) == 0:
            return 0
        from OpenGL import GL
        try:
            h, w = img_data.shape[0], img_data.shape[1]
            texture_id = GL.glGenTextures(1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w, h,
                            0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img_data)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
            GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            return int(texture_id)
        except Exception as e:
            print(f"[MeshCache] Texture upload failed: {e}")
            return 0

    def get_gpu_mesh(self, resource_path: str) -> Optional[GPUMesh]:
        """Get the GPU mesh for a model, or None if not yet loaded."""
        return self._gpu_cache.get(resource_path)

    def is_loading(self, resource_path: str) -> bool:
        """Check if a model is currently being decompiled/loaded."""
        return resource_path in self._loading or resource_path in self._pending_upload

    def is_failed(self, resource_path: str) -> bool:
        """Check if a model failed to load."""
        return resource_path in self._failed

    def clear(self):
        """Release all GPU resources and clear caches."""
        from OpenGL import GL

        for gpu_mesh in list(self._gpu_cache.values()) + list(self._pending_unload.values()):
            try:
                GL.glDeleteVertexArrays(1, [gpu_mesh.vao])
                GL.glDeleteBuffers(2, [gpu_mesh.vbo, gpu_mesh.ebo])
                if gpu_mesh.textures:
                    GL.glDeleteTextures(len(gpu_mesh.textures), gpu_mesh.textures)
            except Exception:
                pass

        self._gpu_cache.clear()
        self._cpu_cache.clear()
        self._pending_upload.clear()
        self._pending_unload.clear()
        self._loading.clear()
        self._failed.clear()
