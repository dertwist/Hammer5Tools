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
class MeshData:
    """CPU-side mesh data extracted from a GLB file."""
    vertices: np.ndarray          # (N, 3) float32
    normals: np.ndarray           # (N, 3) float32
    indices: np.ndarray           # (M,) uint32
    uvs: Optional[np.ndarray]     # (N, 2) float32 or None
    bbox_min: np.ndarray          # (3,) float32
    bbox_max: np.ndarray          # (3,) float32
    texture_data: Optional[bytes] = None   # Raw PNG/JPEG bytes for first texture
    texture_width: int = 0
    texture_height: int = 0


@dataclass
class GPUMesh:
    """GPU-uploaded mesh handles (VAO, VBO, EBO, texture)."""
    vao: int = 0
    vbo: int = 0
    ebo: int = 0
    index_count: int = 0
    texture_id: int = 0
    has_texture: bool = False
    bbox_min: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    bbox_max: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))


# ---------------------------------------------------------------------------
# GLB loader (using trimesh)
# ---------------------------------------------------------------------------

def load_glb(path: str) -> Optional[MeshData]:
    """Load a .glb file and return MeshData, or None on failure."""
    try:
        import trimesh

        scene = trimesh.load(path, force='scene', process=False)

        all_vertices = []
        all_normals = []
        all_uvs = []
        all_indices = []
        offset = 0

        # Flatten all meshes in the scene
        for name, geom in scene.geometry.items():
            if not isinstance(geom, trimesh.Trimesh):
                continue

            verts = np.array(geom.vertices, dtype=np.float32)
            faces = np.array(geom.faces, dtype=np.uint32)

            # Apply the geometry's transform if it exists in the scene graph
            try:
                transform = scene.graph.get(name)[0] if name in scene.graph else None
                if transform is not None and not np.allclose(transform, np.eye(4)):
                    ones = np.ones((len(verts), 1), dtype=np.float32)
                    verts_h = np.hstack([verts, ones])
                    verts = (verts_h @ transform.T)[:, :3].astype(np.float32)
            except Exception:
                pass

            norms = np.array(geom.vertex_normals, dtype=np.float32) if geom.vertex_normals is not None and len(geom.vertex_normals) > 0 else np.zeros_like(verts)

            uvs = None
            if geom.visual and hasattr(geom.visual, 'uv') and geom.visual.uv is not None:
                uvs = np.array(geom.visual.uv, dtype=np.float32)

            all_vertices.append(verts)
            all_normals.append(norms)
            if uvs is not None:
                all_uvs.append(uvs)
            else:
                all_uvs.append(np.zeros((len(verts), 2), dtype=np.float32))
            all_indices.append(faces + offset)
            offset += len(verts)

        if not all_vertices:
            return None

        vertices = np.vstack(all_vertices)
        normals = np.vstack(all_normals)
        uvs_arr = np.vstack(all_uvs) if all_uvs else None
        indices = np.vstack(all_indices).flatten().astype(np.uint32)

        bbox_min = vertices.min(axis=0)
        bbox_max = vertices.max(axis=0)

        # Try to extract first texture
        texture_data = None
        tex_w = tex_h = 0
        for name, geom in scene.geometry.items():
            if isinstance(geom, trimesh.Trimesh) and geom.visual:
                try:
                    mat = geom.visual.material
                    if hasattr(mat, 'image') and mat.image is not None:
                        from io import BytesIO
                        buf = BytesIO()
                        mat.image.save(buf, format='PNG')
                        texture_data = buf.getvalue()
                        tex_w, tex_h = mat.image.size
                        break
                except Exception:
                    pass

        return MeshData(
            vertices=vertices,
            normals=normals,
            indices=indices,
            uvs=uvs_arr,
            bbox_min=bbox_min,
            bbox_max=bbox_max,
            texture_data=texture_data,
            texture_width=tex_w,
            texture_height=tex_h,
        )

    except Exception as e:
        print(f"[MeshCache] Failed to load GLB {path}: {e}")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Async decompilation worker
# ---------------------------------------------------------------------------

class _DecompileSignals(QObject):
    finished = Signal(str, str)    # (model_resource_path, glb_cache_path or "")
    error = Signal(str, str)       # (model_resource_path, error_message)


class _DecompileWorker(QRunnable):
    """Background worker that decompiles a .vmdl_c to .glb via VRF."""

    def __init__(self, model_resource_path: str):
        super().__init__()
        self.model_resource_path = model_resource_path
        self.signals = _DecompileSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            from src.dotnet import decompile_model_to_glb
            result = decompile_model_to_glb(self.model_resource_path)
            if result and os.path.exists(result):
                self.signals.finished.emit(self.model_resource_path, result)
            else:
                self.signals.error.emit(self.model_resource_path, "Decompilation returned None")
        except Exception as e:
            self.signals.error.emit(self.model_resource_path, str(e))


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
        self._loading: set = set()                         # Currently decompiling
        self._failed: set = set()                          # Failed decompilations
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(2)             # Limit concurrent decompilations

    def request_model(self, resource_path: str):
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
        # Check if GLB already exists in cache
        glb_path = self._find_cached_glb(resource_path)
        if glb_path:
            mesh_data = load_glb(glb_path)
            if mesh_data:
                self._cpu_cache[resource_path] = mesh_data
                self._pending_upload[resource_path] = mesh_data
                self.model_ready.emit(resource_path)
                return
            else:
                self._failed.add(resource_path)
                return

        # Queue decompilation
        self._loading.add(resource_path)
        worker = _DecompileWorker(resource_path)
        worker.signals.finished.connect(self._on_decompile_finished)
        worker.signals.error.connect(self._on_decompile_error)
        self._thread_pool.start(worker)

    def _find_cached_glb(self, resource_path: str) -> Optional[str]:
        """Check if a GLB file already exists in the cache."""
        from src.common import SmartPropEditor_Path
        from src.settings.common import get_addon_name

        normalized = resource_path.replace("\\", "/").strip("/")
        if not normalized.endswith(".vmdl"):
            if normalized.endswith(".vmdl_c"):
                normalized = normalized[:-2]
            else:
                normalized += ".vmdl"

        glb_subpath = normalized.rsplit(".", 1)[0] + ".glb"

        addon_name = get_addon_name() or "addon"

        # Check addon cache first, then csgo cache
        for subfolder in [addon_name, "csgo"]:
            candidate = os.path.join(str(SmartPropEditor_Path), "cache", subfolder, glb_subpath)
            if os.path.exists(candidate):
                return candidate

        return None

    def _on_decompile_finished(self, resource_path: str, glb_path: str):
        """Called when background decompilation completes."""
        self._loading.discard(resource_path)
        if glb_path and os.path.exists(glb_path):
            mesh_data = load_glb(glb_path)
            if mesh_data:
                self._cpu_cache[resource_path] = mesh_data
                self._pending_upload[resource_path] = mesh_data
                self.model_ready.emit(resource_path)
                return
        self._failed.add(resource_path)

    def _on_decompile_error(self, resource_path: str, error_msg: str):
        """Called when decompilation fails."""
        self._loading.discard(resource_path)
        self._failed.add(resource_path)
        print(f"[MeshCache] Decompilation failed for {resource_path}: {error_msg}")

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

        # Texture upload
        texture_id = 0
        has_texture = False
        if mesh_data.texture_data:
            try:
                from PIL import Image
                from io import BytesIO

                img = Image.open(BytesIO(mesh_data.texture_data))
                # Downscale if too large
                max_dim = 1024
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.LANCZOS)
                img = img.convert("RGBA")
                img = img.transpose(Image.FLIP_TOP_BOTTOM)  # OpenGL expects bottom-up
                img_data = np.array(img, dtype=np.uint8)

                texture_id = GL.glGenTextures(1)
                GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
                GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, img.width, img.height,
                                0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img_data)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
                GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
                GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
                has_texture = True
            except Exception as e:
                print(f"[MeshCache] Texture upload failed: {e}")

        return GPUMesh(
            vao=vao,
            vbo=vbo,
            ebo=ebo,
            index_count=len(mesh_data.indices),
            texture_id=texture_id,
            has_texture=has_texture,
            bbox_min=mesh_data.bbox_min.copy(),
            bbox_max=mesh_data.bbox_max.copy(),
        )

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

        for gpu_mesh in self._gpu_cache.values():
            try:
                GL.glDeleteVertexArrays(1, [gpu_mesh.vao])
                GL.glDeleteBuffers(2, [gpu_mesh.vbo, gpu_mesh.ebo])
                if gpu_mesh.texture_id:
                    GL.glDeleteTextures(1, [gpu_mesh.texture_id])
            except Exception:
                pass

        self._gpu_cache.clear()
        self._cpu_cache.clear()
        self._pending_upload.clear()
        self._loading.clear()
        self._failed.clear()
