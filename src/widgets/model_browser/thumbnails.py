"""
Thumbnail generation for the model browser.

ValveResourceFormat has no thumbnail API — it decompiles .vmdl_c to glTF and
stops there. So a thumbnail is produced in two stages:

    worker thread   VRF decompile (.vmdl_c -> .glb) + trimesh parse -> MeshData
    GUI thread      render MeshData into an offscreen FBO -> PNG on disk

The render half must run on the thread that owns the GL context, and Qt only
guarantees that for the GUI thread, so renders are drained one-per-tick from a
queue instead of blocking the dialog while a few thousand models bake. Results
are cached as PNGs keyed by resource path + size + source mtime, which makes
every subsequent open of the browser instant.

The shader here is deliberately *not* the viewport's PBR one: a 128px tile does
not benefit from metallic-roughness, and a small self-contained program avoids
coupling thumbnails to the viewport's uniform layout.
"""
import os
import hashlib
from typing import Optional, Dict

import numpy as np
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer, Slot, Qt
from PySide6.QtGui import QImage, QPixmap, QOffscreenSurface, QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat

from src.editors.smartprop_editor.viewport_3d.mesh_cache import load_glb, MeshData


THUMB_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;

uniform mat4 u_mvp;
uniform mat3 u_normal_matrix;

out vec3 v_normal;
out vec2 v_uv;

void main() {
    v_normal = normalize(u_normal_matrix * a_normal);
    v_uv = a_uv;
    gl_Position = u_mvp * vec4(a_position, 1.0);
}
"""

THUMB_FRAGMENT_SHADER = """
#version 330 core
in vec3 v_normal;
in vec2 v_uv;

uniform sampler2D u_base_tex;
uniform bool u_has_base_tex;
uniform vec4 u_base_color;

out vec4 frag_color;

void main() {
    vec4 albedo = u_base_color;
    if (u_has_base_tex) {
        albedo *= texture(u_base_tex, v_uv);
    }
    if (albedo.a < 0.35) {
        discard;
    }

    // Three-quarter key light plus a hemisphere fill, matching the viewport's
    // neutral studio feel closely enough that tiles read as the same scene.
    vec3 normal = normalize(v_normal);
    vec3 key_dir = normalize(vec3(-0.45, 0.75, 0.5));
    float key = max(dot(normal, key_dir), 0.0);
    float fill = 0.5 + 0.5 * normal.y;

    vec3 lit = albedo.rgb * (0.28 * fill + 0.85 * key);
    lit = pow(lit, vec3(1.0 / 2.2));
    frag_color = vec4(lit, 1.0);
}
"""

# Tile background, matching compact.BG so tiles sit flush on the grid.
_CLEAR_COLOR = (0.109, 0.109, 0.109, 1.0)

#: Thumbnails render at exactly this resolution. The grid scales tiles down from
#: it, so the slider never invalidates the cache and never asks for a re-render.
THUMB_SIZE = 128

#: The thumbnail shader samples albedo only, so the loader is told to skip the
#: normal/MR/AO/emissive maps entirely and cap the base one. Dropping four of
#: five maps is where the CPU saving comes from; this cap mainly bounds memory
#: for models that ship 4K albedos.
THUMB_TEXTURE_DIM = 512


def _worker_thread_count() -> int:
    """Loader threads — every core the machine has.

    VRF decompilation is serialised behind dotnet's _decompile_lock, so these
    threads parallelise the *parse* half (trimesh + texture decode) while one
    thread holds the decompile lock. Only the tiles actually on screen are ever
    queued, so a burst is bounded by a screenful of work rather than the whole
    index — there is nothing long-running here to throttle.
    """
    try:
        return max(1, os.cpu_count() or 1)
    except Exception:
        return 1


def thumbnail_cache_path(resource_path: str, size: int) -> str:
    """Disk location for one model's thumbnail at one resolution."""
    from src.widgets.model_browser.cache import thumbnail_dir
    digest = hashlib.sha1(resource_path.lower().encode("utf-8")).hexdigest()[:16]
    return os.path.join(thumbnail_dir(), f"{digest}_{size}.png")


def _cached_thumbnail(entry, size: int) -> Optional[str]:
    """Return a cached PNG that is still newer than its source, else None."""
    png = thumbnail_cache_path(entry.path, size)
    if not os.path.isfile(png):
        return None
    # VPK-backed models have no cheap mtime to compare against; the pak only
    # changes on a game update, and a stale tile there is harmless.
    if entry.in_vpk:
        return png
    try:
        if os.path.getmtime(png) > os.path.getmtime(entry.fs_path):
            return png
    except OSError:
        return png
    return None


class _MeshLoadSignals(QObject):
    loaded = Signal(str, object)    # resource path, MeshData | None


def load_vrf_mesh_direct(entry) -> Optional[MeshData]:
    """Direct in-memory extraction of MeshData from .vmdl_c using VRF.

    Extracts vertex/index buffers directly from VRF without glTF export or disk I/O.
    """
    import os
    import numpy as np
    from src.common import get_cs2_path
    from src.editors.smartprop_editor.viewport_3d.mesh_cache import MeshData, SubMeshData
    from src.dotnet import DotNetInterop

    cs2_path = get_cs2_path()
    if not cs2_path:
        return None

    vmdl_path = entry.path.replace("\\", "/").strip("/")
    if vmdl_path.endswith(".vmdl"):
        vmdl_c_path = vmdl_path + "_c"
    elif not vmdl_path.endswith(".vmdl_c"):
        vmdl_c_path = vmdl_path + ".vmdl_c"
    else:
        vmdl_c_path = vmdl_path

    mod_name = entry.mod.replace("\\", "/").replace("csgo_addons/", "").strip("/")

    data_bytes = None

    # 1. Try loose filesystem file in game/csgo_addons/<addon> or game/csgo
    possible_fs_paths = []
    if getattr(entry, "fs_path", None):
        possible_fs_paths.append(entry.fs_path)
        if entry.fs_path.endswith(".vmdl"):
            possible_fs_paths.append(entry.fs_path + "_c")
            possible_fs_paths.append(entry.fs_path.replace("/content/", "/game/") + "_c")

    if mod_name and mod_name != "csgo":
        possible_fs_paths.append(os.path.join(cs2_path, "game", "csgo_addons", mod_name, vmdl_c_path))
        possible_fs_paths.append(os.path.join(cs2_path, "content", "csgo_addons", mod_name, vmdl_c_path))

    possible_fs_paths.append(os.path.join(cs2_path, "game", "csgo", vmdl_c_path))

    for fs_path in possible_fs_paths:
        if fs_path and os.path.isfile(fs_path):
            try:
                with open(fs_path, "rb") as f:
                    data_bytes = f.read()
                if data_bytes:
                    break
            except Exception:
                pass

    # 2. Try VPK archive if not found on disk
    if data_bytes is None:
        try:
            vpk_path = os.path.join(cs2_path, "game", "csgo", "pak01_dir.vpk")
            if os.path.isfile(vpk_path):
                interop = DotNetInterop()
                Resource, _, _, _, _, Package = interop.setup_vrf()
                import System
                package = System.Activator.CreateInstance(Package)
                package.Read(vpk_path)
                try:
                    pkg_entry = package.FindEntry(vmdl_c_path)
                    if pkg_entry is not None:
                        data_bytes = bytes(package.ReadEntry(pkg_entry))
                finally:
                    if hasattr(package, "Dispose"):
                        package.Dispose()
        except Exception:
            pass

    if data_bytes is None:
        return None

    # Parse .vmdl_c via VRF directly in memory
    try:
        interop = DotNetInterop()
        Resource, _, _, _, _, _ = interop.setup_vrf()
        import System

        ms = System.IO.MemoryStream(data_bytes)
        res = System.Activator.CreateInstance(Resource)
        res.Read(ms)
        if res.ResourceType != res.ResourceType.Model:
            return None

        model = res.DataBlock
        meshes = list(model.GetEmbeddedMeshes())
        if not meshes:
            return None

        all_verts, all_norms, all_uvs, all_indices = [], [], [], []
        vert_offset = 0

        for mesh_tuple in meshes:
            mesh = mesh_tuple.Item1
            vbib = mesh.VBIB
            if vbib is None or vbib.VertexBuffers.Count == 0 or vbib.IndexBuffers.Count == 0:
                continue

            for i in range(min(vbib.VertexBuffers.Count, vbib.IndexBuffers.Count)):
                vb = vbib.VertexBuffers[i]
                ib = vbib.IndexBuffers[i]

                pos_attrs = [a for a in vb.InputLayoutFields if a.SemanticName == 'POSITION']
                if not pos_attrs:
                    continue
                pos_arr = vbib.GetVector3AttributeArray(vb, pos_attrs[0])
                verts = np.array([(v.X, v.Y, v.Z) for v in pos_arr], dtype=np.float32)
                if len(verts) == 0:
                    continue

                norm_attrs = [a for a in vb.InputLayoutFields if a.SemanticName == 'NORMAL']
                if norm_attrs:
                    try:
                        norm_res = vbib.GetNormalTangentArray(vb, norm_attrs[0])
                        norms = np.array([(n.X, n.Y, n.Z) for n in norm_res.Item1], dtype=np.float32)
                    except Exception:
                        norms = np.zeros_like(verts)
                else:
                    norms = np.zeros_like(verts)

                uv_attrs = [a for a in vb.InputLayoutFields if a.SemanticName == 'TEXCOORD']
                if uv_attrs:
                    try:
                        uv_arr = vbib.GetVector2AttributeArray(vb, uv_attrs[0])
                        uvs = np.array([(u.X, u.Y) for u in uv_arr], dtype=np.float32)
                    except Exception:
                        uvs = np.zeros((len(verts), 2), dtype=np.float32)
                else:
                    uvs = np.zeros((len(verts), 2), dtype=np.float32)

                bytes_data = bytes(ib.Data)
                dtype = np.uint16 if ib.ElementSizeInBytes == 2 else np.uint32
                idx = np.frombuffer(bytes_data, dtype=dtype).astype(np.uint32) + vert_offset

                all_verts.append(verts)
                all_norms.append(norms)
                all_uvs.append(uvs)
                all_indices.append(idx)
                vert_offset += len(verts)

        if not all_verts:
            return None

        cat_verts = np.vstack(all_verts)
        cat_norms = np.vstack(all_norms)
        cat_uvs = np.vstack(all_uvs)
        cat_idx = np.concatenate(all_indices)
        bmin = np.min(cat_verts, axis=0)
        bmax = np.max(cat_verts, axis=0)

        submesh = SubMeshData(index_offset=0, index_count=len(cat_idx))
        return MeshData(
            vertices=cat_verts,
            normals=cat_norms,
            indices=cat_idx,
            uvs=cat_uvs,
            bbox_min=bmin,
            bbox_max=bmax,
            submeshes=[submesh]
        )
    except Exception as exc:
        print(f"[model_browser] direct VRF mesh parse failed for {entry.path}: {exc}")
        return None


class _MeshLoadWorker(QRunnable):
    """High-performance direct VRF in-memory mesh loader off the GUI thread."""

    def __init__(self, entry, signals: _MeshLoadSignals):
        super().__init__()
        self.entry = entry
        self.signals = signals

    @Slot()
    def run(self):
        mesh = None
        try:
            mesh = load_vrf_mesh_direct(self.entry)
            if mesh is None:
                from src.dotnet import decompile_model_to_glb
                glb = decompile_model_to_glb(self.entry.path, context_addon=self.entry.mod)
                if glb and os.path.isfile(glb):
                    mesh = load_glb(glb, max_texture_dim=THUMB_TEXTURE_DIM,
                                    base_color_only=True)
        except Exception as exc:
            print(f"[model_browser] thumbnail load failed for {self.entry.path}: {exc}")
        self.signals.loaded.emit(self.entry.path, mesh)


class ThumbnailService(QObject):
    """Queues thumbnail work and hands back QPixmaps as they become available."""

    ready = Signal(str, QPixmap)     # resource path, thumbnail
    failed = Signal(str)             # resource path

    #: Renders drained per timer tick. One keeps the dialog fully interactive
    #: while a large index bakes; the queue itself is what provides throughput.
    RENDERS_PER_TICK = 1

    def __init__(self, size: int = THUMB_SIZE, parent=None):
        super().__init__(parent)
        # Fixed render resolution — callers may not raise it. Larger tiles buy
        # nothing at grid scale and cost quadratically in fill and PNG size.
        self.size = min(int(size), THUMB_SIZE)
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(_worker_thread_count())

        self._signals = _MeshLoadSignals()
        self._signals.loaded.connect(self._on_mesh_loaded, Qt.QueuedConnection)

        self._in_flight: set = set()        # resource paths actively being loaded by worker threads
        self._visible_paths: set = set()    # resource paths currently visible
        self._failed: set = set()           # resource paths that failed to load/render
        self._render_queue: list = []       # (resource_path, MeshData)
        self._memory: Dict[str, QPixmap] = {}

        self._surface = None
        self._context = None
        self._program = None
        self._gl_failed = False

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._drain_render_queue)

    # ------------------------------------------------------------------ API

    def request(self, entry) -> Optional[QPixmap]:
        """Return a thumbnail now if one exists, otherwise queue it and return None.

        A queued thumbnail arrives later via the ``ready`` signal.
        """
        self._visible_paths.add(entry.path)

        pixmap = self._memory.get(entry.path)
        if pixmap is not None:
            return pixmap

        png = _cached_thumbnail(entry, self.size)
        if png:
            pixmap = QPixmap(png)
            if not pixmap.isNull():
                self._memory[entry.path] = pixmap
                return pixmap

        if entry.path in self._failed:
            return None

        if entry.path not in self._in_flight:
            self._in_flight.add(entry.path)
            self._pool.start(_MeshLoadWorker(entry, self._signals))

        return None

    def set_visible_paths(self, visible_paths: set):
        """Update visible item paths and cancel queued GL rendering for invisible items."""
        self._visible_paths = set(visible_paths)
        self._render_queue = [
            (path, mesh) for path, mesh in self._render_queue if path in self._visible_paths
        ]

    def is_pending(self, resource_path: str) -> bool:
        return resource_path in self._in_flight or any(p == resource_path for p, _ in self._render_queue)

    def has_pending(self) -> bool:
        return len(self._in_flight) > 0 or len(self._render_queue) > 0

    def cancel_pending(self):
        """Drop queued GL render work when the user scrolls or refilters away from it."""
        self._visible_paths.clear()
        self._render_queue.clear()

    def clear_disk_cache(self):
        from src.widgets.model_browser.cache import clear_cache
        self._memory.clear()
        self._failed.clear()
        clear_cache()

    # -------------------------------------------------------------- internals

    @Slot(str, object)
    def _on_mesh_loaded(self, resource_path: str, mesh):
        self._in_flight.discard(resource_path)
        if resource_path not in self._visible_paths:
            return
        if mesh is None or getattr(mesh, "vertices", None) is None or len(mesh.vertices) == 0:
            self._failed.add(resource_path)
            self.failed.emit(resource_path)
            return
        self._render_queue.append((resource_path, mesh))
        if not self._timer.isActive():
            self._timer.start()

    def _drain_render_queue(self):
        if not self._render_queue:
            self._timer.stop()
            return

        for _ in range(self.RENDERS_PER_TICK):
            if not self._render_queue:
                break
            resource_path, mesh = self._render_queue.pop(0)

            image = self._render_mesh(mesh)
            if image is None or image.isNull():
                self._failed.add(resource_path)
                self.failed.emit(resource_path)
                continue

            pixmap = QPixmap.fromImage(image)
            self._memory[resource_path] = pixmap

            png = thumbnail_cache_path(resource_path, self.size)
            try:
                os.makedirs(os.path.dirname(png), exist_ok=True)
                image.save(png, "PNG")
            except Exception:
                pass

            self.ready.emit(resource_path, pixmap)

    def _ensure_context(self) -> bool:
        """Create the shared offscreen GL context and compile the shader once."""
        if self._gl_failed:
            return False
        if self._program is not None:
            return self._context.makeCurrent(self._surface)

        try:
            from OpenGL import GL
            from PySide6.QtGui import QOpenGLContext

            surface_format = QSurfaceFormat()
            surface_format.setVersion(3, 3)
            surface_format.setProfile(QSurfaceFormat.CoreProfile)
            surface_format.setDepthBufferSize(24)

            self._surface = QOffscreenSurface()
            self._surface.setFormat(surface_format)
            self._surface.create()

            self._context = QOpenGLContext()
            self._context.setFormat(surface_format)
            # Share with the viewport's context so driver-side resources and the
            # 3.3 core profile requirement resolve identically in both places.
            shared = QOpenGLContext.globalShareContext()
            if shared is not None:
                self._context.setShareContext(shared)
            if not self._context.create():
                raise RuntimeError("could not create offscreen GL context")
            if not self._context.makeCurrent(self._surface):
                raise RuntimeError("could not make offscreen GL context current")

            from src.editors.smartprop_editor.viewport_3d.render_area import link_program
            self._program = link_program(THUMB_VERTEX_SHADER, THUMB_FRAGMENT_SHADER)
            GL.glEnable(GL.GL_DEPTH_TEST)
            return True
        except Exception as exc:
            print(f"[model_browser] offscreen GL unavailable, thumbnails disabled: {exc}")
            self._gl_failed = True
            return False

    def _render_mesh(self, mesh: MeshData) -> Optional[QImage]:
        if not self._ensure_context():
            return None

        from OpenGL import GL

        fbo_format = QOpenGLFramebufferObjectFormat()
        fbo_format.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
        # No MSAA: it forces a resolve blit per tile and multiplies fill cost,
        # for edge quality that is invisible once the tile is scaled into the grid.
        fbo_format.setSamples(0)
        fbo = QOpenGLFramebufferObject(self.size, self.size, fbo_format)
        if not fbo.bind():
            return None

        vao = vbo_pos = vbo_nrm = vbo_uv = ebo = None
        textures = []
        try:
            GL.glViewport(0, 0, self.size, self.size)
            GL.glClearColor(*_CLEAR_COLOR)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDisable(GL.GL_CULL_FACE)
            GL.glUseProgram(self._program)

            model, view, projection = _fit_camera(mesh)
            mvp = projection @ view @ model
            normal_matrix = np.linalg.inv(model[:3, :3]).T.astype(np.float32)

            GL.glUniformMatrix4fv(
                GL.glGetUniformLocation(self._program, "u_mvp"),
                1, GL.GL_TRUE, mvp.astype(np.float32))
            GL.glUniformMatrix3fv(
                GL.glGetUniformLocation(self._program, "u_normal_matrix"),
                1, GL.GL_TRUE, normal_matrix)

            vao = GL.glGenVertexArrays(1)
            GL.glBindVertexArray(vao)

            uvs = mesh.uvs
            if uvs is None or len(uvs) != len(mesh.vertices):
                uvs = np.zeros((len(mesh.vertices), 2), dtype=np.float32)

            vbo_pos = _upload_attribute(0, mesh.vertices.astype(np.float32), 3)
            vbo_nrm = _upload_attribute(1, mesh.normals.astype(np.float32), 3)
            vbo_uv = _upload_attribute(2, uvs.astype(np.float32), 2)

            indices = mesh.indices.astype(np.uint32)
            ebo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, ebo)
            GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL.GL_STATIC_DRAW)

            base_tex_loc = GL.glGetUniformLocation(self._program, "u_base_tex")
            has_tex_loc = GL.glGetUniformLocation(self._program, "u_has_base_tex")
            color_loc = GL.glGetUniformLocation(self._program, "u_base_color")
            GL.glUniform1i(base_tex_loc, 0)

            submeshes = mesh.submeshes or []
            if not submeshes:
                GL.glUniform1i(has_tex_loc, 0)
                GL.glUniform4f(color_loc, 0.72, 0.72, 0.72, 1.0)
                GL.glDrawElements(GL.GL_TRIANGLES, len(indices), GL.GL_UNSIGNED_INT, None)
            else:
                for submesh in submeshes:
                    material = submesh.material
                    texture = _upload_texture(getattr(material, "base_color_img", None))
                    if texture:
                        textures.append(texture)
                        GL.glActiveTexture(GL.GL_TEXTURE0)
                        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
                        GL.glUniform1i(has_tex_loc, 1)
                    else:
                        GL.glUniform1i(has_tex_loc, 0)

                    factor = getattr(material, "base_color_factor", (1.0, 1.0, 1.0, 1.0))
                    GL.glUniform4f(color_loc, *[float(c) for c in factor])
                    GL.glDrawElements(
                        GL.GL_TRIANGLES, submesh.index_count, GL.GL_UNSIGNED_INT,
                        GL.ctypes.c_void_p(submesh.index_offset * 4))

            GL.glFinish()
            return fbo.toImage()
        except Exception as exc:
            print(f"[model_browser] thumbnail render failed: {exc}")
            return None
        finally:
            try:
                for texture in textures:
                    GL.glDeleteTextures([texture])
                for buffer in (vbo_pos, vbo_nrm, vbo_uv, ebo):
                    if buffer:
                        GL.glDeleteBuffers(1, [buffer])
                if vao:
                    GL.glBindVertexArray(0)
                    GL.glDeleteVertexArrays(1, [vao])
            except Exception:
                pass
            fbo.release()


# load_glb() hands back geometry in raw Source space — Z-up, inches — because
# that is the frame the viewport works in (it converts to GL only at draw time).
# Treating those verts as glTF Y-up lays every model on its side, so the swap has
# to happen here too:
#     GL_X =  S2_X      GL_Y =  S2_Z      GL_Z = -S2_Y
# Unlike camera.SOURCE2_TO_GL this is written in intuitive row-major form, not
# pre-transposed, because the uniform uploads in this module pass GL_TRUE and let
# GL do the transpose. Copying that matrix verbatim would flip Z-up to -Y.
_SOURCE_TO_GL = np.array([
    [1,  0,  0, 0],
    [0,  0,  1, 0],
    [0, -1,  0, 0],
    [0,  0,  0, 1],
], dtype=np.float32)


def _upload_attribute(location: int, data: np.ndarray, components: int):
    from OpenGL import GL
    buffer = GL.glGenBuffers(1)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
    GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_STATIC_DRAW)
    GL.glEnableVertexAttribArray(location)
    GL.glVertexAttribPointer(location, components, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
    return buffer


def _upload_texture(image: Optional[np.ndarray]):
    """Upload a GL-oriented RGBA uint8 array from MeshData, or return 0."""
    if image is None or image.size == 0:
        return 0
    from OpenGL import GL
    height, width = image.shape[0], image.shape[1]
    texture = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0,
                    GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, np.ascontiguousarray(image))
    GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
    return texture


def _fit_camera(mesh: MeshData):
    """Build model/view/projection placing the mesh in a three-quarter view.

    The model matrix centres the mesh on its bounding box, normalises it to unit
    scale, and rotates Source space into GL space, so one fixed camera frames
    every model regardless of whether it is a doorknob or a hangar.
    """
    bbox_min = np.asarray(mesh.bbox_min, dtype=np.float32)
    bbox_max = np.asarray(mesh.bbox_max, dtype=np.float32)
    center = (bbox_min + bbox_max) * 0.5
    extent = float(np.max(bbox_max - bbox_min))
    if not np.isfinite(extent) or extent <= 1e-6:
        extent = 1.0
    scale = 1.0 / extent

    # Centre and normalise while still in Source space, then convert.
    normalize = np.eye(4, dtype=np.float32)
    normalize[:3, :3] *= scale
    normalize[:3, 3] = -center * scale
    model = _SOURCE_TO_GL @ normalize

    eye = np.array([1.05, 0.85, 1.35], dtype=np.float32)
    view = _look_at(eye, np.zeros(3, dtype=np.float32), np.array([0, 1, 0], dtype=np.float32))
    projection = _perspective(35.0, 1.0, 0.05, 50.0)
    return model, view, projection


def _look_at(eye, target, up):
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, up)
    right /= max(np.linalg.norm(right), 1e-8)
    true_up = np.cross(right, forward)

    matrix = np.eye(4, dtype=np.float32)
    matrix[0, :3] = right
    matrix[1, :3] = true_up
    matrix[2, :3] = -forward
    matrix[:3, 3] = -matrix[:3, :3] @ eye
    return matrix


def _perspective(fov_degrees, aspect, near, far):
    f = 1.0 / np.tan(np.radians(fov_degrees) * 0.5)
    matrix = np.zeros((4, 4), dtype=np.float32)
    matrix[0, 0] = f / aspect
    matrix[1, 1] = f
    matrix[2, 2] = (far + near) / (near - far)
    matrix[2, 3] = (2 * far * near) / (near - far)
    matrix[3, 2] = -1.0
    return matrix
