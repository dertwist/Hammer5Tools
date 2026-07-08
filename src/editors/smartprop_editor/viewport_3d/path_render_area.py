"""
OpenGL 3D render area for editing a path of control points.

This replaces the old QPainter-based 2D-overlay path viewport.  It reuses the
shared SmartProp 3D viewport infrastructure (Camera, Gizmo, shaders, program
linking) so the path editor and the model viewport share one unified structure:

  * each control point is drawn as a lit 3D sphere,
  * the path between the points is a smooth Catmull-Rom / bezier curve,
  * the grid floor, color-pick selection and the W-translate gizmo all come
    straight from the smartprop viewport modules.

Points are stored/edited in Source 2 coordinates (Z-up, inches) exactly like the
rest of the viewport; SOURCE2_TO_GL converts them to GL space at draw time.
"""
import math
import numpy as np

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from src.editors.smartprop_editor.viewport_3d.camera import (
    Camera, SOURCE2_TO_GL, translation_matrix, scale_matrix,
)
from src.editors.smartprop_editor.viewport_3d.gizmo import Gizmo, GizmoMode, GizmoAxis
from src.editors.smartprop_editor.viewport_3d.render_area import link_program
from src.editors.smartprop_editor.viewport_3d.shaders import (
    MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER,
    PICKING_VERTEX_SHADER, PICKING_FRAGMENT_SHADER,
    GRID_VERTEX_SHADER, GRID_FRAGMENT_SHADER,
    GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER,
    WIREFRAME_VERTEX_SHADER, WIREFRAME_FRAGMENT_SHADER,
)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def _make_sphere(stacks=16, slices=24):
    """Build a unit-radius UV sphere.

    Returns interleaved vertices (pos.xyz, normal.xyz, uv.xy) and a triangle
    index buffer, matching the MODEL shader's attribute layout.
    """
    verts = []
    for i in range(stacks + 1):
        phi = math.pi * i / stacks          # 0 (top) .. pi (bottom)
        y = math.cos(phi)
        r = math.sin(phi)
        for j in range(slices + 1):
            theta = 2.0 * math.pi * j / slices
            x = r * math.cos(theta)
            z = r * math.sin(theta)
            # Unit sphere: the position is also the normal.
            verts.extend([x, y, z, x, y, z, j / slices, i / stacks])

    indices = []
    row = slices + 1
    for i in range(stacks):
        for j in range(slices):
            a = i * row + j
            b = a + row
            indices.extend([a, b, a + 1, a + 1, b, b + 1])

    return np.array(verts, dtype=np.float32), np.array(indices, dtype=np.uint32)


def catmull_rom_spline(points, samples_per_segment=24):
    """Smooth path through `points` (Source 2 coords) via a Catmull-Rom spline.

    Catmull-Rom is a cardinal spline that passes through every control point and
    is directly expressible in cubic-bezier form, so this is the bezier
    curvature interpretation of the path.  Endpoints are clamped (duplicated) so
    the curve starts/ends exactly on the first/last point.
    """
    n = len(points)
    if n < 2:
        return [list(p) for p in points]

    pts = [np.asarray(p, dtype=np.float64) for p in points]
    out = []
    for i in range(n - 1):
        p0 = pts[i - 1] if i - 1 >= 0 else pts[i]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        for s in range(samples_per_segment):
            t = s / samples_per_segment
            t2 = t * t
            t3 = t2 * t
            point = 0.5 * (
                (2.0 * p1)
                + (-p0 + p2) * t
                + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
            )
            out.append(point.tolist())
    out.append(pts[-1].tolist())
    return out


class PathEditor3DRenderArea(QOpenGLWidget):
    """OpenGL viewport that edits a list of 3D control points.

    Public interface mirrors the old InteractiveCurveEditor so the path dialog
    can drive it unchanged:
        set_points(points), set_selected_index(idx), selected_index,
        frame_objects(), signals points_changed / selection_changed(int).
    """
    points_changed = Signal()
    selection_changed = Signal(int)

    # Sphere size follows the camera distance so it keeps a roughly constant
    # on-screen size; clamped so it never vanishes or swallows the scene.
    SPHERE_SCREEN_FACTOR = 0.018
    SPHERE_MIN_RADIUS = 3.0

    def __init__(self, points=None, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.points = points if points is not None else []
        self.selected_index = -1
        self._hover_index = -1

        self.camera = Camera()
        self.gizmo = Gizmo()
        self.gizmo.set_mode(GizmoMode.TRANSLATE)

        # Grid and Snapping Settings
        self.grid_step = 64.0
        self.snapping_enabled = False

        # Interaction state
        self._last_mouse_pos = QPointF()
        self._action = None            # 'orbit' | 'pan' | 'zoom'
        self._perform_pick_flag = False
        self._pick_pos = None

        # Shader programs
        self._model_program = 0
        self._picking_program = 0
        self._grid_program = 0
        self._gizmo_program = 0
        self._line_program = 0

        # GPU buffers
        self._grid_vao = 0
        self._sphere_vao = 0
        self._sphere_index_count = 0
        self._curve_vao = 0
        self._curve_vbo = 0
        self._curve_vertex_count = 0

        # Curve is rebuilt on the GL thread from these CPU samples; compute the
        # initial curve now so the path is drawn on the very first paint.
        self._curve_samples = []
        self._curve_dirty = True
        self._mark_curve_dirty()

    # ------------------------------------------------------------------
    # Public API (matches the old InteractiveCurveEditor)
    # ------------------------------------------------------------------
    def set_points(self, points):
        self.points = points
        if self.selected_index >= len(self.points):
            self.selected_index = -1
        self._hover_index = -1
        self._sync_gizmo()
        self._mark_curve_dirty()
        self.update()

    def set_selected_index(self, idx):
        if self.selected_index != idx:
            self.selected_index = idx
            self._sync_gizmo()
            self.update()

    def frame_objects(self):
        """Fit the camera to the current points."""
        if not self.points:
            return
        gl_pts = np.array([self._to_gl(p) for p in self.points], dtype=np.float32)
        bbox_min = gl_pts.min(axis=0) - 30.0
        bbox_max = gl_pts.max(axis=0) + 30.0
        self.camera.fit_to_bounds(bbox_min, bbox_max)
        self.update()

    # Alias so callers used to the smartprop viewport can use fit_view too.
    fit_view = frame_objects

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _to_gl(point):
        """Source 2 point -> GL world position (xyz)."""
        p = [float(point[i]) if i < len(point) else 0.0 for i in range(3)]
        # Direct column-vector point transform -> use the transpose (SOURCE2_TO_GL
        # is written pre-transposed for GL_FALSE render chains, not for this form).
        gl = SOURCE2_TO_GL.T @ np.array([p[0], p[1], p[2], 1.0], dtype=np.float32)
        return gl[:3]

    def _sphere_radius(self):
        return max(self.camera.distance * self.SPHERE_SCREEN_FACTOR, self.SPHERE_MIN_RADIUS)

    def _mark_curve_dirty(self):
        self._curve_samples = catmull_rom_spline(self.points) if len(self.points) >= 2 else []
        self._curve_dirty = True

    def _sync_gizmo(self):
        if 0 <= self.selected_index < len(self.points):
            pt = self.points[self.selected_index]
            self.gizmo.set_transform(
                [float(pt[0]), float(pt[1]), float(pt[2])], [0.0, 0.0, 0.0], [1.0, 1.0, 1.0]
            )
        else:
            self.gizmo.hide()

    def _sync_gizmo_settings(self, event=None):
        self.gizmo.camera_right = self.camera.right_vector
        self.gizmo.camera_up = self.camera.up_vector
        self.gizmo.camera_forward = self.camera.target - self.camera.position

        # Snapping toggling with Ctrl key
        ctrl_held = False
        if event is not None:
            ctrl_held = bool(event.modifiers() & Qt.ControlModifier)
        else:
            from PySide6.QtWidgets import QApplication
            if QApplication.keyboardModifiers() & Qt.ControlModifier:
                ctrl_held = True

        self.gizmo.snapping_enabled = self.snapping_enabled ^ ctrl_held
        self.gizmo.grid_step = self.grid_step

    # ------------------------------------------------------------------
    # GL lifecycle
    # ------------------------------------------------------------------
    def initializeGL(self):
        from OpenGL import GL

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_MULTISAMPLE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        self._model_program = link_program(MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER)
        self._picking_program = link_program(PICKING_VERTEX_SHADER, PICKING_FRAGMENT_SHADER)
        self._grid_program = link_program(GRID_VERTEX_SHADER, GRID_FRAGMENT_SHADER)
        self._gizmo_program = link_program(GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER)
        self._line_program = link_program(WIREFRAME_VERTEX_SHADER, WIREFRAME_FRAGMENT_SHADER)

        # Grid floor (large quad, procedurally shaded in the grid fragment shader)
        size = 25000.0
        grid_vertices = np.array([
            [-size, 0.0, -size],
            [ size, 0.0, -size],
            [ size, 0.0,  size],
            [-size, 0.0,  size],
        ], dtype=np.float32)
        self._grid_vao = GL.glGenVertexArrays(1)
        grid_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._grid_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, grid_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, grid_vertices.nbytes, grid_vertices, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)

        # Unit sphere (pos.xyz, normal.xyz, uv.xy) + index buffer
        sphere_verts, sphere_indices = _make_sphere()
        self._sphere_index_count = len(sphere_indices)
        self._sphere_vao = GL.glGenVertexArrays(1)
        sphere_vbo = GL.glGenBuffers(1)
        sphere_ebo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._sphere_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, sphere_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, sphere_verts.nbytes, sphere_verts, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, sphere_ebo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, sphere_indices.nbytes, sphere_indices, GL.GL_STATIC_DRAW)
        stride = 32  # 8 floats
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, GL.ctypes.c_void_p(12))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(2, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, GL.ctypes.c_void_p(24))
        GL.glEnableVertexAttribArray(2)
        GL.glBindVertexArray(0)

        # Curve polyline (pos only, streamed — rebuilt whenever points change)
        self._curve_vao = GL.glGenVertexArrays(1)
        self._curve_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._curve_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._curve_vbo)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)

        self.gizmo.init_geometry()
        self._sync_gizmo()

    def resizeGL(self, w, h):
        from OpenGL import GL
        GL.glViewport(0, 0, w, h)
        self.camera.aspect = w / h if h > 0 else 1.0

    def _upload_curve_if_needed(self):
        from OpenGL import GL
        if not self._curve_dirty:
            return
        self._curve_dirty = False
        if len(self._curve_samples) < 2:
            self._curve_vertex_count = 0
            return
        arr = np.array(self._curve_samples, dtype=np.float32)
        self._curve_vertex_count = len(arr)
        GL.glBindVertexArray(self._curve_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._curve_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, arr.nbytes, arr, GL.GL_DYNAMIC_DRAW)
        GL.glBindVertexArray(0)

    def paintGL(self):
        from OpenGL import GL

        if self._perform_pick_flag:
            self._do_picking_pass()
            self._perform_pick_flag = False

        GL.glClearColor(0.11, 0.11, 0.11, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        self._upload_curve_if_needed()
        self._sync_gizmo_settings()

        view = self.camera.view_matrix
        proj = self.camera.projection_matrix
        cam_pos = self.camera.position

        # 1. Grid floor (depth writes off so its transparent areas never occlude)
        GL.glDepthMask(GL.GL_FALSE)
        GL.glUseProgram(self._grid_program)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._grid_program, "uView"), 1, GL.GL_FALSE, view)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._grid_program, "uProjection"), 1, GL.GL_FALSE, proj)
        GL.glUniform1f(GL.glGetUniformLocation(self._grid_program, "uGridStep"), float(self.grid_step))
        GL.glBindVertexArray(self._grid_vao)
        GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, 4)
        GL.glBindVertexArray(0)
        GL.glDepthMask(GL.GL_TRUE)

        # 2. Bezier/Catmull-Rom path curve
        self._draw_curve(view, proj)

        # 3. Control-point spheres
        self._draw_spheres(view, proj, cam_pos, picking=False)

        # 4. Transform gizmo (on top)
        self.gizmo.render(self._gizmo_program, view, proj, cam_pos)

    def _draw_curve(self, view, proj):
        from OpenGL import GL
        if self._curve_vertex_count < 2:
            return
        GL.glUseProgram(self._line_program)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._line_program, "uView"), 1, GL.GL_FALSE, view)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._line_program, "uProjection"), 1, GL.GL_FALSE, proj)
        # Curve verts are Source 2 coords; uModel converts them to GL space.
        # SOURCE2_TO_GL is used as-is (NOT .T) for GL_FALSE upload — see render_area.
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._line_program, "uModel"), 1, GL.GL_FALSE, SOURCE2_TO_GL)
        GL.glUniform3fv(GL.glGetUniformLocation(self._line_program, "uColor"), 1,
                        np.array([0.95, 0.6, 0.2], dtype=np.float32))
        try:
            GL.glLineWidth(2.5)
        except Exception:
            pass
        GL.glBindVertexArray(self._curve_vao)
        GL.glDrawArrays(GL.GL_LINE_STRIP, 0, self._curve_vertex_count)
        GL.glBindVertexArray(0)

    def _sphere_model_matrix(self, point, radius):
        # Row-vector chain (see render_area): scale, translate (Source 2), then
        # convert to GL.  Uploaded untransposed so GL applies it correctly.
        p = [float(point[i]) if i < len(point) else 0.0 for i in range(3)]
        return (
            scale_matrix(radius, radius, radius)
            @ translation_matrix(p[0], p[1], p[2])
            @ SOURCE2_TO_GL
        )

    def _draw_spheres(self, view, proj, cam_pos, picking=False):
        from OpenGL import GL
        if not self.points:
            return

        radius = self._sphere_radius()

        if picking:
            prog = self._picking_program
            GL.glUseProgram(prog)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uView"), 1, GL.GL_FALSE, view)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uProjection"), 1, GL.GL_FALSE, proj)
        else:
            prog = self._model_program
            GL.glUseProgram(prog)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uView"), 1, GL.GL_FALSE, view)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uProjection"), 1, GL.GL_FALSE, proj)
            GL.glUniform3fv(GL.glGetUniformLocation(prog, "uCameraPos"), 1, cam_pos)
            GL.glUniform1i(GL.glGetUniformLocation(prog, "uHasTexture"), 0)

        GL.glBindVertexArray(self._sphere_vao)
        for i, pt in enumerate(self.points):
            model = self._sphere_model_matrix(pt, radius)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uModel"), 1, GL.GL_FALSE, model)

            if picking:
                pid = i + 1  # 0 is reserved for "nothing"
                r = (pid & 0xFF) / 255.0
                g = ((pid >> 8) & 0xFF) / 255.0
                b = ((pid >> 16) & 0xFF) / 255.0
                GL.glUniform3f(GL.glGetUniformLocation(prog, "uPickColor"), r, g, b)
            else:
                if i == self.selected_index:
                    base = np.array([1.0, 0.9, 0.35], dtype=np.float32)
                    highlight = 1.0
                elif i == self._hover_index:
                    base = np.array([1.0, 0.78, 0.35], dtype=np.float32)
                    highlight = 0.0
                else:
                    base = np.array([0.9, 0.55, 0.2], dtype=np.float32)
                    highlight = 0.0
                norm_mat = np.linalg.inv(model[:3, :3]).T
                GL.glUniformMatrix3fv(GL.glGetUniformLocation(prog, "uNormalMatrix"), 1, GL.GL_FALSE, norm_mat)
                GL.glUniform3fv(GL.glGetUniformLocation(prog, "uBaseColor"), 1, base)
                GL.glUniform1f(GL.glGetUniformLocation(prog, "uHighlight"), highlight)

            GL.glDrawElements(GL.GL_TRIANGLES, self._sphere_index_count, GL.GL_UNSIGNED_INT, None)
        GL.glBindVertexArray(0)

    def _do_picking_pass(self):
        from OpenGL import GL
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glDisable(GL.GL_BLEND)

        view = self.camera.view_matrix
        proj = self.camera.projection_matrix
        cam_pos = self.camera.position
        self._draw_spheres(view, proj, cam_pos, picking=True)

        w, h = self.width(), self.height()
        gl_y = h - self._pick_pos.y()
        gl_x = self._pick_pos.x()
        pixel = GL.glReadPixels(int(gl_x), int(gl_y), 1, 1, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
        GL.glEnable(GL.GL_BLEND)

        pid = pixel[0] | (pixel[1] << 8) | (pixel[2] << 16)
        idx = pid - 1
        if 0 <= idx < len(self.points):
            if idx != self.selected_index:
                self.selected_index = idx
                self._sync_gizmo()
                self.selection_changed.emit(idx)
        else:
            if self.selected_index != -1:
                self.selected_index = -1
                self._sync_gizmo()
                self.selection_changed.emit(-1)

    # ------------------------------------------------------------------
    # Mouse & keyboard
    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        self._last_mouse_pos = event.position()
        self._sync_gizmo_settings(event)

        # Gizmo handle first (left click)
        if event.button() == Qt.LeftButton and self.gizmo.visible and self.gizmo.mode != GizmoMode.NONE:
            w, h = self.width(), self.height()
            ray_org, ray_dir = self.camera.screen_to_ray(event.position().x(), event.position().y(), w, h)
            axis = self.gizmo.hit_test(ray_org, ray_dir, self.camera.position)
            if axis != GizmoAxis.NONE:
                self.gizmo.begin_drag(axis, (event.position().x(), event.position().y()))
                self.update()
                return

        if event.button() == Qt.LeftButton:
            # Color-pick a control point on the next paint.
            self._perform_pick_flag = True
            self._pick_pos = event.position()
            self.update()
        elif event.button() == Qt.MiddleButton:
            if event.modifiers() & Qt.ControlModifier:
                self._action = 'zoom'
            elif event.modifiers() & Qt.ShiftModifier:
                self._action = 'pan'
            else:
                self._action = 'orbit'
        elif event.button() == Qt.RightButton:
            self._action = 'pan'

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        dx = pos.x() - self._last_mouse_pos.x()
        dy = pos.y() - self._last_mouse_pos.y()

        self._sync_gizmo_settings(event)

        # Gizmo drag -> move the selected control point.
        if self.gizmo.is_dragging:
            w, h = self.width(), self.height()
            delta = self.gizmo.update_drag(
                (pos.x(), pos.y()), self.camera.view_matrix, self.camera.projection_matrix,
                w, h, self.camera.position
            )
            if delta and "position" in delta and 0 <= self.selected_index < len(self.points):
                new_pos = delta["position"]
                pt = self.points[self.selected_index]
                for i in range(3):
                    pt[i] = new_pos[i]
                self.gizmo.set_transform(new_pos, [0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
                self._mark_curve_dirty()
                self.points_changed.emit()
            self._last_mouse_pos = pos
            self.update()
            return

        # Gizmo hover feedback
        if self.gizmo.visible:
            w, h = self.width(), self.height()
            ray_org, ray_dir = self.camera.screen_to_ray(pos.x(), pos.y(), w, h)
            axis = self.gizmo.hit_test(ray_org, ray_dir, self.camera.position)
            if axis != self.gizmo.hover_axis:
                self.gizmo.hover_axis = axis
                self.update()

        # Camera navigation
        if self._action == 'orbit':
            self.camera.orbit(dx, dy)
            self.update()
        elif self._action == 'pan':
            self.camera.pan(dx, dy)
            self.update()
        elif self._action == 'zoom':
            self.camera.zoom(-(dx - dy))
            self.update()

        self._last_mouse_pos = pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.gizmo.is_dragging:
            self.gizmo.end_drag()
        self._action = None
        self.update()

    def wheelEvent(self, event):
        self.camera.zoom(event.angleDelta().y())
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F:
            self.frame_objects()
        elif event.key() == Qt.Key_W:
            self.gizmo.set_mode(GizmoMode.TRANSLATE)
            self.update()
        else:
            super().keyPressEvent(event)
