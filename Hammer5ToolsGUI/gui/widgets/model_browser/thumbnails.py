"""
Thumbnail generation for the model browser.

ValveResourceFormat has no thumbnail API, so a thumbnail is produced in two
stages:

    worker thread   read .vmdl_c blocks directly -> MeshData (see vmdl_reader)
    GUI thread      render MeshData into an offscreen FBO -> PNG on disk

The render half must run on the thread that owns the GL context, and Qt only
guarantees that for the GUI thread, so renders are drained one-per-tick from a
queue instead of blocking the dialog while a few thousand models bake. Results
are cached as PNG blobs in a single sqlite3 database, keyed by resource path +
size + source mtime, which makes every subsequent open of the browser instant.
One file for potentially tens of thousands of thumbnails avoids the per-file
open/close (and antivirus scan) cost that a PNG-per-model directory pays on
every read and on cache clear.

The shader here is deliberately *not* the viewport's PBR one: a 128px tile does
not benefit from metallic-roughness, and a small self-contained program avoids
coupling thumbnails to the viewport's uniform layout.
"""
import logging
import os
import hashlib
import sqlite3
import time
from contextlib import closing
from typing import Optional, Dict

import numpy as np
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer, Slot, Qt, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPixmap, QOffscreenSurface, QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat

from gui.editors.smartprop_editor.viewport_3d.mesh_cache import MeshData


from collections import OrderedDict

log = logging.getLogger(__name__)

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
    // No V-flip: vmdl_reader._decode_texture() already rotates decoded
    // images to standard top-left-origin orientation, matching raw UV.
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
uniform vec3 u_view_dir;
uniform int u_alpha_mode;      // 0 = OPAQUE, 1 = MASK, 2 = BLEND
uniform float u_alpha_cutoff;

out vec4 frag_color;

float pow2(float x) { return x * x; }
vec3 pow2(vec3 x) { return x * x; }
float saturate(float x) { return clamp(x, 0.0, 1.0); }
vec3 saturate(vec3 x) { return clamp(x, 0.0, 1.0); }

vec3 SrgbGammaToLinear(vec3 color)
{
    vec3 vLinearSegment = color / vec3(12.92);
    vec3 vExpSegment = pow((color / vec3(1.055)) + vec3(0.0521327), vec3(2.4));

    const float cap = 0.04045;
    float select = color.r > cap ? vExpSegment.r : vLinearSegment.r;
    float select1 = color.g > cap ? vExpSegment.g : vLinearSegment.g;
    float select2 = color.b > cap ? vExpSegment.b : vLinearSegment.b;

    return vec3(select, select1, select2);
}

vec3 SrgbLinearToGamma(vec3 vLinearColor)
{
    vec3 vLinearSegment = vLinearColor * 12.92;
    vec3 vExpSegment = (1.055 * pow(vLinearColor, vec3(1.0 / 2.4))) - 0.055;

    vec3 vGammaColor = vec3((vLinearColor.r <= 0.0031308) ? vLinearSegment.r : vExpSegment.r,
                            (vLinearColor.g <= 0.0031308) ? vLinearSegment.g : vExpSegment.g,
                            (vLinearColor.b <= 0.0031308) ? vLinearSegment.b : vExpSegment.b);
    return vGammaColor;
}

void main() {
    vec4 base = u_base_color;
    if (u_has_base_tex) {
        vec4 tex = texture(u_base_tex, v_uv);
        base.rgb *= SrgbGammaToLinear(tex.rgb);
        base.a *= tex.a;
    }
    // Base-color textures routinely pack unrelated data (spec/translucency
    // masks) into alpha when the material itself is OPAQUE, so only MASK
    // materials are alpha-tested — matching the SmartProp Editor viewport
    // shader (glsl/model.frag). Discarding on OPAQUE's alpha here made most
    // real (textured) models render as empty tiles once real base-color
    // alpha data started loading.
    if (u_alpha_mode == 1 && base.a < u_alpha_cutoff) {
        discard;
    }

    vec3 norm = normalize(v_normal);
    if (!gl_FrontFacing) norm = -norm;
    vec3 viewDir = normalize(u_view_dir);

    // Fullbright shader calculation matched to SmartProp Editor 3D Viewport
    float flFakeDiffuseLighting = saturate(dot(norm, viewDir)) * 0.7 + 0.3;

    float XtraLight1 = dot(vec3(0.6, 1.0, 0.4), pow2(saturate(norm)));
    float XtraLight2 = dot(vec3(0.6, 0.2, 0.4), pow2(saturate(-norm)));
    float xtraLight = XtraLight1 + XtraLight2;

    vec3 litLinear = xtraLight * base.rgb * flFakeDiffuseLighting;
    vec3 litGamma = SrgbLinearToGamma(litLinear);

    frag_color = vec4(litGamma, 1.0);
}
"""

# Tile background, matching compact.BG so tiles sit flush on the grid.
# RGB comes from the active theme brightness (alpha is 1.0).
def _clear_color():
    from gui.styles import theme
    return (*theme.gl_clear_color(), 1.0)

#: Thumbnails render at exactly this resolution. The grid scales tiles down from
#: it, so the slider never invalidates the cache and never asks for a re-render.
THUMB_SIZE = 128

#: The thumbnail shader samples albedo only, so the loader is told to skip the
#: normal/MR/AO/emissive maps entirely and cap the base one. For a 128px thumbnail,
#: 128px textures provide exact 1:1 density with 16x faster decompression and memory bandwidth.
THUMB_TEXTURE_DIM = 128

#: Mirrors SmartProp3DRenderArea._ALPHA_MODE_CODE (render_area.py) — kept as its
#: own copy since this module renders with an intentionally separate shader.
_ALPHA_MODE_CODE = {"OPAQUE": 0, "MASK": 1, "BLEND": 2}


def _worker_thread_count() -> int:
    """Loader threads — every core the machine has.

    Reads run fully in parallel: each worker keeps its own VRF file loader, so
    unlike the old glTF path there is no global decompile lock to queue behind.
    Only the tiles actually on screen are ever queued, so a burst is bounded by
    a screenful of work rather than the whole index.
    """
    try:
        return max(1, os.cpu_count() or 1)
    except Exception:
        return 1


_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS thumbnails (
    key TEXT PRIMARY KEY,
    written_at REAL NOT NULL,
    data BLOB NOT NULL
)
"""

_local_conn = None
_local_conn_path = None


def _get_db_conn():
    global _local_conn, _local_conn_path
    from gui.widgets.model_browser.cache import thumbnail_db_path
    path = thumbnail_db_path()
    if _local_conn is not None:
        if _local_conn_path == path and os.path.exists(path):
            return _local_conn
        try:
            _local_conn.close()
        except Exception:
            pass
        _local_conn = None
        _local_conn_path = None

    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0)
    conn.execute(_DB_SCHEMA)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    except Exception:
        pass
    _local_conn = conn
    _local_conn_path = path
    return conn


def _close_db_conn():
    global _local_conn, _local_conn_path
    if _local_conn is not None:
        try:
            _local_conn.close()
        except Exception:
            pass
        _local_conn = None
        _local_conn_path = None


def _thumbnail_key(resource_path: str, size: int) -> str:
    digest = hashlib.sha1(resource_path.lower().encode("utf-8")).hexdigest()[:16]
    return f"{digest}_{size}"


def _cached_thumbnail_bytes(entry, size: int) -> Optional[bytes]:
    """Return cached PNG bytes that are still newer than the source, else None."""
    key = _thumbnail_key(entry.path, size)
    try:
        conn = _get_db_conn()
        row = conn.execute(
            "SELECT written_at, data FROM thumbnails WHERE key = ?", (key,)
        ).fetchone()
    except (sqlite3.Error, OSError):
        return None
    if row is None:
        return None
    written_at, data = row
    # VPK-backed models have no cheap mtime to compare against; the pak only
    # changes on a game update, and a stale tile there is harmless.
    if entry.in_vpk:
        return data
    try:
        if written_at > os.path.getmtime(entry.fs_path):
            return data
    except OSError:
        return data
    return None


def _store_thumbnail_bytes(resource_path: str, size: int, data: bytes):
    try:
        conn = _get_db_conn()
        conn.execute(
            "INSERT OR REPLACE INTO thumbnails (key, written_at, data) VALUES (?, ?, ?)",
            (_thumbnail_key(resource_path, size), time.time(), data),
        )
        conn.commit()
    except (sqlite3.Error, OSError):
        pass


class _MeshLoadSignals(QObject):
    loaded = Signal(str, object)    # resource path, MeshData | None


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
            from gui.editors.smartprop_editor.viewport_3d.vmdl_reader import load_model
            mesh = load_model(self.entry.path, context_addon=self.entry.mod,
                              max_texture_dim=THUMB_TEXTURE_DIM, base_color_only=True)
        except Exception as exc:
            msg = str(exc).splitlines()[0] if str(exc) else "Load error"
            log.error(f"[model_browser] thumbnail load skipped for {self.entry.path}: {msg}")
        self.signals.loaded.emit(self.entry.path, mesh)


class ThumbnailService(QObject):
    """Queues thumbnail work and hands back QPixmaps as they become available."""

    ready = Signal(str, QPixmap)     # resource path, thumbnail
    failed = Signal(str)             # resource path

    #: Renders drained per timer tick. Higher throughput drains visible thumbnails
    #: smoothly without stalling GUI frame rate.
    RENDERS_PER_TICK = 4
    MAX_MEMORY_CACHE = 256

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
        self._memory: OrderedDict[str, QPixmap] = OrderedDict()

        self._surface = None
        self._context = None
        self._program = None
        self._gl_failed = False

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._drain_render_queue)

    def _store_memory_pixmap(self, resource_path: str, pixmap: QPixmap):
        self._memory[resource_path] = pixmap
        self._memory.move_to_end(resource_path)
        if len(self._memory) > self.MAX_MEMORY_CACHE:
            self._memory.popitem(last=False)

    # API

    def request(self, entry) -> Optional[QPixmap]:
        """Return a thumbnail now if one exists, otherwise queue it and return None.

        A queued thumbnail arrives later via the ``ready`` signal.
        """
        self._visible_paths.add(entry.path)

        pixmap = self._memory.get(entry.path)
        if pixmap is not None:
            self._memory.move_to_end(entry.path)
            return pixmap

        data = _cached_thumbnail_bytes(entry, self.size)
        if data:
            pixmap = QPixmap()
            pixmap.loadFromData(data, "PNG")
            if not pixmap.isNull():
                self._store_memory_pixmap(entry.path, pixmap)
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

    def is_failed(self, resource_path: str) -> bool:
        return resource_path in self._failed

    def has_pending(self) -> bool:
        return len(self._in_flight) > 0 or len(self._render_queue) > 0

    def cancel_pending(self):
        """Drop queued GL render work when the user scrolls or refilters away from it."""
        self._visible_paths.clear()
        self._render_queue.clear()

    def clear_disk_cache(self):
        from gui.widgets.model_browser.cache import clear_cache
        self._memory.clear()
        self._failed.clear()
        _close_db_conn()
        clear_cache()

    # internals

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
            self._store_memory_pixmap(resource_path, pixmap)

            buffer = QByteArray()
            qbuf = QBuffer(buffer)
            qbuf.open(QIODevice.WriteOnly)
            image.save(qbuf, "PNG")
            qbuf.close()
            _store_thumbnail_bytes(resource_path, self.size, bytes(buffer))

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

            from gui.editors.smartprop_editor.viewport_3d.render_area import link_program
            self._program = link_program(THUMB_VERTEX_SHADER, THUMB_FRAGMENT_SHADER)
            GL.glEnable(GL.GL_DEPTH_TEST)
            return True
        except Exception as exc:
            log.error(f"[model_browser] offscreen GL unavailable, thumbnails disabled: {exc}")
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
            GL.glClearColor(*_clear_color())
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
            GL.glUniform3f(
                GL.glGetUniformLocation(self._program, "u_view_dir"),
                1.05, 0.85, 1.35)

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
            alpha_mode_loc = GL.glGetUniformLocation(self._program, "u_alpha_mode")
            alpha_cutoff_loc = GL.glGetUniformLocation(self._program, "u_alpha_cutoff")
            GL.glUniform1i(base_tex_loc, 0)

            submeshes = mesh.submeshes or []
            if not submeshes:
                GL.glUniform1i(has_tex_loc, 0)
                GL.glUniform4f(color_loc, 0.72, 0.72, 0.72, 1.0)
                GL.glUniform1i(alpha_mode_loc, 0)
                GL.glDrawElements(GL.GL_TRIANGLES, len(indices), GL.GL_UNSIGNED_INT, None)
            else:
                for submesh in submeshes:
                    material = submesh.material
                    texture = _upload_texture(
                        getattr(material, "base_color_img", None),
                        getattr(material, "wrap_u", 0),
                        getattr(material, "wrap_v", 0),
                    )
                    if texture:
                        textures.append(texture)
                        GL.glActiveTexture(GL.GL_TEXTURE0)
                        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
                        GL.glUniform1i(has_tex_loc, 1)
                    else:
                        GL.glUniform1i(has_tex_loc, 0)

                    factor = getattr(material, "base_color_factor", (1.0, 1.0, 1.0, 1.0))
                    GL.glUniform4f(color_loc, *[float(c) for c in factor])
                    GL.glUniform1i(alpha_mode_loc, _ALPHA_MODE_CODE.get(getattr(material, "alpha_mode", "OPAQUE"), 0))
                    GL.glUniform1f(alpha_cutoff_loc, float(getattr(material, "alpha_cutoff", 0.5)))
                    GL.glDrawElements(
                        GL.GL_TRIANGLES, submesh.index_count, GL.GL_UNSIGNED_INT,
                        GL.ctypes.c_void_p(submesh.index_offset * 4))

            GL.glFinish()
            return fbo.toImage()
        except Exception as exc:
            log.error(f"[model_browser] thumbnail render failed: {exc}")
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


# The loader hands back geometry in raw Source space — Z-up, inches — because
# that is the frame the viewport works in (it converts to GL only at draw time).
# Treating those verts as glTF Y-up lays every model on its side, so the swap has
# to happen here too:
# GL_X =  S2_X      GL_Y =  S2_Z      GL_Z = -S2_Y
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


def _upload_texture(image: Optional[np.ndarray], wrap_u: int = 0, wrap_v: int = 0):
    """Upload a GL-oriented RGBA uint8 array from MeshData, or return 0."""
    if image is None or image.size == 0:
        return 0
    from OpenGL import GL
    height, width = image.shape[0], image.shape[1]
    texture = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)

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
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0,
                    GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, np.ascontiguousarray(image))
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
