"""
Mesh data containers, GPU buffer management, and asynchronous model loading.
Handles compiled model → CPU mesh data → GPU upload, with caching at every level.

The CPU half — reading .vmdl_c/.vmat_c/.vtex_c — lives in :mod:`vmdl_reader`.
"""
import os
from typing import Optional, Dict
from dataclasses import dataclass, field

import numpy as np

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Slot


# CPU-side mesh data (read from compiled assets, not yet on GPU)

@dataclass
class MaterialData:
    """CPU-side PBR material built from a Source 2 .vmat_c.

    Textures are kept as ready-to-upload RGBA uint8 arrays (already downscaled
    for OpenGL) so the GL thread only has to call
    glTexImage2D — no PIL decode on upload, and no wasteful PNG re-encode during
    load.  Channel conventions follow the glTF 2.0 metallic-roughness spec, which
    is what the viewport shader expects; :mod:`vmdl_reader` maps Source's own
    layout onto it:
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
    wrap_u: int = 0
    wrap_v: int = 0
    uv_set: int = 0
    uv_scale: tuple = (1.0, 1.0)
    uv_offset: tuple = (0.0, 0.0)
    uv_center: tuple = (0.5, 0.5)
    uv_rotation: float = 0.0



@dataclass
class SubMeshData:
    """A contiguous index range within a MeshData that shares one material."""
    index_offset: int              # first index (element count, not bytes)
    index_count: int
    material: MaterialData = field(default_factory=MaterialData)


@dataclass
class MeshData:
    """CPU-side mesh data, in raw Source space (Z-up, inches)."""
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
    wrap_u: int = 0
    wrap_v: int = 0
    uv_scale: tuple = (1.0, 1.0)
    uv_offset: tuple = (0.0, 0.0)
    uv_center: tuple = (0.5, 0.5)
    uv_rotation: float = 0.0

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


# Preview textures are capped to this size.  Downscaling on the (background)
# load thread bounds both VRAM and the per-texture CPU cost.
MAX_TEXTURE_DIM = 1024


# Async load worker

class _ModelLoadSignals(QObject):
    # (model_resource_path, MeshData or None).  MeshData is a plain Python object
    # carrying numpy arrays; passing it across the queued signal is thread-safe.
    loaded = Signal(str, object)


class _ModelLoadWorker(QRunnable):
    """Background worker: read the compiled model straight into MeshData.

    Doing the whole heavy path — VRF block reads and texture decode/downscale —
    off the UI thread keeps painting smooth.  Only the final GPU upload happens
    on the GL thread.  There is no decompile step and no disk cache to consult;
    see :mod:`vmdl_reader`.
    """

    def __init__(self, model_resource_path: str, context_addon: str = None):
        super().__init__()
        self.model_resource_path = model_resource_path
        self.context_addon = context_addon
        self.signals = _ModelLoadSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        mesh = None
        try:
            from src.editors.smartprop_editor.viewport_3d.vmdl_reader import load_model
            mesh = load_model(self.model_resource_path, self.context_addon)
        except Exception as e:
            print(f"[MeshCache] Model load failed for {self.model_resource_path}: {e}")
            mesh = None
        self.signals.loaded.emit(self.model_resource_path, mesh)


# Mesh Cache

class MeshCache(QObject):
    """
    Manages model loading, GPU upload, and caching.

    Workflow:
        1. request_model(resource_path) → queues a background read
        2. On read complete → MeshData (CPU) is stashed for upload
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
        self._loading: set = set()                         # Currently loading
        self._failed: set = set()                          # Failed loads
        self._thread_pool = QThreadPool()
        # Cap concurrency: reads run fully in parallel (each worker owns its VRF
        # file loader), so a few worker threads speed up multi-model scenes
        # without oversubscribing the CPU.
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
        # Dispatch a background worker that does the whole load (VRF block reads
        # + texture decode) off the UI thread.
        self._loading.add(resource_path)
        worker = _ModelLoadWorker(resource_path, context_addon)
        worker.signals.loaded.connect(self._on_model_loaded)
        self._thread_pool.start(worker)

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
                    base_tex=self._upload_texture(mat.base_color_img, mat.wrap_u, mat.wrap_v),
                    normal_tex=self._upload_texture(mat.normal_img, mat.wrap_u, mat.wrap_v),
                    mr_tex=self._upload_texture(mat.mr_img, mat.wrap_u, mat.wrap_v),
                    ao_tex=self._upload_texture(mat.ao_img, mat.wrap_u, mat.wrap_v),
                    emissive_tex=self._upload_texture(mat.emissive_img, mat.wrap_u, mat.wrap_v),
                    base_color_factor=mat.base_color_factor,
                    metallic_factor=mat.metallic_factor,
                    roughness_factor=mat.roughness_factor,
                    emissive_factor=mat.emissive_factor,
                    alpha_mode=mat.alpha_mode,
                    alpha_cutoff=mat.alpha_cutoff,
                    double_sided=mat.double_sided,
                    wrap_u=mat.wrap_u,
                    wrap_v=mat.wrap_v,
                    uv_scale=mat.uv_scale,
                    uv_offset=mat.uv_offset,
                    uv_center=mat.uv_center,
                    uv_rotation=mat.uv_rotation,
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

    def _upload_texture(self, img_data: Optional[np.ndarray], wrap_u: int = 0, wrap_v: int = 0) -> int:
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

            wrap_modes = {
                0: GL.GL_REPEAT,
                1: GL.GL_MIRRORED_REPEAT,
                2: GL.GL_CLAMP_TO_EDGE,
                3: GL.GL_CLAMP_TO_BORDER,
            }
            gl_wrap_u = wrap_modes.get(wrap_u, GL.GL_REPEAT)
            gl_wrap_v = wrap_modes.get(wrap_v, GL.GL_REPEAT)

            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, gl_wrap_u)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, gl_wrap_v)
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
