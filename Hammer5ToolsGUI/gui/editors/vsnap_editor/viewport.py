from __future__ import annotations

import math
import time
from functools import lru_cache

import numpy as np
from PySide6.QtCore import QPointF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.common import gui_assets_dir
from gui.editors.smartprop_editor.viewport_3d.camera import Camera
from gui.editors.smartprop_editor.viewport_3d.crash_guard import gl_guard
from gui.editors.smartprop_editor.viewport_3d.gizmo import Gizmo, GizmoAxis, GizmoMode
from gui.editors.smartprop_editor.viewport_3d.gl_settings import make_viewport_surface_format
from gui.editors.smartprop_editor.viewport_3d.shaders import GIZMO_FRAGMENT_SHADER, GIZMO_VERTEX_SHADER
from gui.editors.vsnap_editor.shaders import (
    COLOR_FRAGMENT_SHADER,
    COLOR_VERTEX_SHADER,
    SPRITE_FRAGMENT_SHADER,
    SPRITE_GEOMETRY_SHADER,
    SPRITE_VERTEX_SHADER,
)
from gui.styles import theme
from gui.widgets import FloatWidget


def _compile_program(vertex_source: str, fragment_source: str, geometry_source: str | None = None) -> int:
    from OpenGL import GL

    shaders = []
    for kind, source in (
        (GL.GL_VERTEX_SHADER, vertex_source),
        (GL.GL_GEOMETRY_SHADER, geometry_source),
        (GL.GL_FRAGMENT_SHADER, fragment_source),
    ):
        if source is None:
            continue
        shader = GL.glCreateShader(kind)
        GL.glShaderSource(shader, source)
        GL.glCompileShader(shader)
        if not GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS):
            raise RuntimeError(GL.glGetShaderInfoLog(shader).decode("utf-8"))
        shaders.append(shader)
    program = GL.glCreateProgram()
    for shader in shaders:
        GL.glAttachShader(program, shader)
    GL.glLinkProgram(program)
    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        raise RuntimeError(GL.glGetProgramInfoLog(program).decode("utf-8"))
    for shader in shaders:
        GL.glDeleteShader(shader)
    return program


def _source_to_gl(points) -> np.ndarray:
    values = np.asarray(points, dtype=np.float32)
    if values.size == 0:
        return np.empty((0, 3), dtype=np.float32)
    return np.column_stack((values[:, 0], values[:, 2], -values[:, 1])).astype(np.float32)


def _gl_to_source(point) -> tuple[float, float, float]:
    return float(point[0]), float(-point[2]), float(point[1])


ROPE_SUBDIVISIONS = 4
_RNG = np.random.default_rng()


@lru_cache(maxsize=1)
def _brush_ring(segments: int = 48) -> np.ndarray:
    """Unit circle on the GL ground plane, as consecutive line segments."""
    angles = np.linspace(0.0, 2.0 * math.pi, segments + 1, dtype=np.float32)
    circle = np.column_stack((np.cos(angles), np.zeros_like(angles), np.sin(angles))).astype(np.float32)
    return np.repeat(circle, 2, axis=0)[1:-1]


@lru_cache(maxsize=32)
def _strip_indices(segments: int) -> tuple[np.ndarray, np.ndarray]:
    """Quad-strip vertex indices for `segments` Catmull-Rom segments."""
    stride = ROPE_SUBDIVISIONS + 1
    start = (np.arange(segments)[:, None] * stride + np.arange(ROPE_SUBDIVISIONS)[None, :]).reshape(-1)
    return start, start + 1


def _theme_gl_color(canonical: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    value = theme.color(canonical).lstrip("#")
    return tuple(int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4)) + (alpha,)


class VSnap3DRenderArea(QOpenGLWidget):
    """VRF-style spritecard and rope-ribbon particle preview."""

    points_drawn = Signal(list)
    point_picked = Signal(int)
    draw_mode_requested = Signal(bool)
    control_point_moved = Signal(str, tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFormat(make_viewport_surface_format())
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self._gl_disabled = False
        self._gl_crash_count = 0
        self.camera = Camera()
        self.camera.distance = 420.0
        self.preview_mode = "Sprites"
        self.grid_step = 8.0
        self.draw_mode = False
        self.pick_mode = False
        self.brush_size = 16.0
        self.brush_spacing = 16.0
        self.brush_density = 1
        self._painting = False
        self._stroke_last = None
        self._hover_ground = None
        self._document = None
        self._positions = np.empty((0, 3), dtype=np.float32)
        self._colors = np.empty((0, 4), dtype=np.float32)
        self._radii = np.empty((0,), dtype=np.float32)
        self._segment_ids = np.empty((0,), dtype=np.int32)
        self._rope_groups: list[np.ndarray] = []
        self._grid_cache = None
        self._uniform_locations: dict[tuple[int, str], int] = {}
        self._view_matrix = self.camera.view_matrix
        self._projection_matrix = self.camera.projection_matrix
        self._control_points = {
            "start": _source_to_gl(((0.0, 0.0, 160.0),))[0],
            "end": _source_to_gl(((120.0, 30.0, 0.0),))[0],
        }
        self.gizmo = Gizmo()
        self.gizmo.set_mode(GizmoMode.TRANSLATE)
        self.snapping_enabled = False
        self._selected_control_point = "start"
        self._sync_gizmo()
        self._last_mouse = QPointF()
        self._action = None
        self._is_flying = False
        self._pressed_keys = set()
        self._fly_last_time = 0.0
        self.fly_speed = 500.0
        self._fly_timer = QTimer(self)
        self._fly_timer.setInterval(16)
        self._fly_timer.timeout.connect(self._update_fly_movement)
        self._sprite_program = 0
        self._color_program = 0
        self._gizmo_program = 0
        self._sprite_vao = 0
        self._sprite_vbo = 0
        self._color_vao = 0
        self._color_vbo = 0
        self.show_values = False
        self.selected_stream = ""

    @gl_guard("event")
    def set_document(self, document) -> None:
        self._document = document
        streams = {stream.name: stream.values for stream in document.streams}
        positions = streams.get("position", ())
        self._positions = _source_to_gl(positions)
        count = len(self._positions)
        color_values = streams.get("color", ())
        opacity_values = streams.get("opacity", ())
        radius_values = streams.get("radius", ())
        segment_values = streams.get("rope_segment_id", ())
        self._colors = np.ones((count, 4), dtype=np.float32)
        if len(color_values) == count:
            self._colors[:, :3] = np.asarray(color_values, dtype=np.float32)
        else:
            self._colors[:, :3] = np.array([0.3, 0.68, 1.0], dtype=np.float32)
        if len(opacity_values) == count:
            self._colors[:, 3] = np.asarray(opacity_values, dtype=np.float32)
        self._radii = np.asarray(radius_values if len(radius_values) == count else [4.0] * count, dtype=np.float32)
        self._segment_ids = np.asarray(
            segment_values if len(segment_values) == count else [0] * count,
            dtype=np.int32,
        )
        # C_OP_RenderRopes starts a fresh strip wherever Rope Segment ID changes between
        # neighbouring particles, so split on the change rather than gathering every particle
        # sharing an id: a snapshot may legitimately reuse ids for separate ropes.
        breaks = np.flatnonzero(self._segment_ids[1:] != self._segment_ids[:-1]) + 1
        self._rope_groups = [
            group for group in np.split(np.arange(count), breaks) if len(group) >= 2
        ]
        if self.isValid():
            self.makeCurrent()
            self._upload_sprites()
            self.doneCurrent()
        self.update()

    def set_control_points(self, start, end) -> None:
        points = _source_to_gl((start, end))
        self._control_points["start"] = points[0]
        self._control_points["end"] = points[1]
        if not self.gizmo.is_dragging:
            self._sync_gizmo()
        self.update()

    def _sync_gizmo(self) -> None:
        position = _gl_to_source(self._control_points[self._selected_control_point])
        self.gizmo.set_transform(position, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))

    def _sync_gizmo_settings(self, event=None) -> None:
        self.gizmo.camera_right = self.camera.right_vector
        self.gizmo.camera_up = self.camera.up_vector
        self.gizmo.camera_forward = self.camera.target - self.camera.position
        modifiers = event.modifiers() if event is not None else QApplication.keyboardModifiers()
        self.gizmo.snapping_enabled = self.snapping_enabled ^ bool(modifiers & Qt.ControlModifier)
        self.gizmo.grid_step = self.grid_step

    def _gizmo_ray(self, point: QPointF):
        return self.camera.screen_to_ray(point.x(), point.y(), self.width(), self.height())

    def set_preview_mode(self, mode: str) -> None:
        self.preview_mode = mode
        self.update()

    @gl_guard("init")
    def initializeGL(self) -> None:
        from OpenGL import GL

        self._sprite_program = _compile_program(
            SPRITE_VERTEX_SHADER, SPRITE_FRAGMENT_SHADER, SPRITE_GEOMETRY_SHADER,
        )
        self._color_program = _compile_program(COLOR_VERTEX_SHADER, COLOR_FRAGMENT_SHADER)
        self._gizmo_program = _compile_program(GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER)
        self._uniform_locations.clear()
        self.gizmo.init_geometry()
        self._sprite_vao = GL.glGenVertexArrays(1)
        self._sprite_vbo = GL.glGenBuffers(1)
        self._color_vao = GL.glGenVertexArrays(1)
        self._color_vbo = GL.glGenBuffers(1)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        self._upload_sprites()

    def _upload_sprites(self) -> None:
        from OpenGL import GL

        if not self._sprite_vao:
            return
        count = len(self._positions)
        packed = np.empty((count, 8), dtype=np.float32)
        if count:
            packed[:, :3] = self._positions
            packed[:, 3:7] = self._colors
            packed[:, 7] = self._radii
        GL.glBindVertexArray(self._sprite_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._sprite_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, packed.nbytes, packed, GL.GL_DYNAMIC_DRAW)
        stride = packed.strides[0] if count else 32
        for location, width, offset in ((0, 3, 0), (1, 4, 12), (2, 1, 28)):
            GL.glEnableVertexAttribArray(location)
            GL.glVertexAttribPointer(location, width, GL.GL_FLOAT, False, stride, GL.ctypes.c_void_p(offset))
        GL.glBindVertexArray(0)

    @gl_guard("event")
    def resizeGL(self, width: int, height: int) -> None:
        self.camera.aspect = width / max(1, height)

    @gl_guard("paint")
    def paintGL(self) -> None:
        from OpenGL import GL

        self._view_matrix = self.camera.view_matrix
        self._projection_matrix = self.camera.projection_matrix
        clear = theme.gl_clear_color()
        GL.glClearColor(*clear, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self._draw_grid()
        if self.preview_mode == "Rope":
            self._draw_rope()
        else:
            self._draw_sprites()
        self._draw_control_points()
        self._draw_brush_cursor()
        if not self.draw_mode:
            self._sync_gizmo_settings()
            self.gizmo.render(self._gizmo_program, self._view_matrix, self._projection_matrix, self.camera.position)
        if self.show_values and self.selected_stream:
            self._draw_values()

    def _draw_values(self) -> None:
        if not len(self._positions) or not self._document:
            return
        stream = next((s for s in self._document.streams if s.name == self.selected_stream), None)
        if not stream:
            return

        from PySide6.QtGui import QPainter, QColor, QFont
        from OpenGL import GL

        GL.glUseProgram(0)
        GL.glBindVertexArray(0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor(229, 229, 229, 255))

        screen_positions = self._project_points(self._positions)
        values = stream.values
        is_vector = stream.type not in ("generic_float", "generic_int")

        for i in range(len(self._positions)):
            x = screen_positions[i, 0]
            y = screen_positions[i, 1]
            if np.isinf(x):
                continue
            if is_vector:
                v = values[i]
                text = f"{v[0]:.2f}, {v[1]:.2f}, {v[2]:.2f}"
            else:
                text = f"{values[i]:.2f}"
            painter.drawText(int(x) + 4, int(y) - 4, text)
        painter.end()

    def _uniform(self, program: int, name: str) -> int:
        location = self._uniform_locations.get((program, name))
        if location is None:
            from OpenGL import GL

            location = self._uniform_locations[(program, name)] = GL.glGetUniformLocation(program, name)
        return location

    def _set_camera_uniforms(self, program: int) -> None:
        from OpenGL import GL

        GL.glUniformMatrix4fv(self._uniform(program, "view"), 1, GL.GL_FALSE, self._view_matrix)
        GL.glUniformMatrix4fv(self._uniform(program, "projection"), 1, GL.GL_FALSE, self._projection_matrix)

    def _draw_sprites(self) -> None:
        from OpenGL import GL

        if not len(self._positions):
            return
        GL.glUseProgram(self._sprite_program)
        self._set_camera_uniforms(self._sprite_program)
        GL.glUniform3fv(self._uniform(self._sprite_program, "cameraRight"), 1, self.camera.right_vector)
        GL.glUniform3fv(self._uniform(self._sprite_program, "cameraUp"), 1, self.camera.up_vector)
        GL.glBindVertexArray(self._sprite_vao)
        GL.glDrawArrays(GL.GL_POINTS, 0, len(self._positions))

    def _draw_grid(self) -> None:
        step = max(1.0, self.grid_step)
        if self._grid_cache is None or self._grid_cache[0] != step:
            extent = max(256.0, step * 16.0)
            values = np.arange(-extent, extent + step * 0.5, step, dtype=np.float32)
            zeros = np.zeros_like(values)
            edge = np.full_like(values, extent)
            lines = np.stack((
                np.column_stack((values, zeros, -edge)),
                np.column_stack((values, zeros, edge)),
                np.column_stack((-edge, zeros, values)),
                np.column_stack((edge, zeros, values)),
            ), axis=1).reshape(-1, 3)
            colors = np.repeat(np.where(
                (np.abs(values) < step * 0.25)[:, None],
                np.array((0.38, 0.4, 0.43, 0.75), np.float32),
                np.array((0.28, 0.3, 0.33, 0.55), np.float32),
            ), 4, axis=0)
            self._grid_cache = (step, lines, colors)
        self._draw_colored(self._grid_cache[1], self._grid_cache[2], 1)

    def _draw_control_points(self) -> None:
        size = max(4.0, min(18.0, self.camera.distance * 0.025))
        vertices = []
        colors = []
        for name, point in self._control_points.items():
            color = _theme_gl_color("#ff6b4a" if name == "start" else "#00d4ff",
                                    1.0 if name == self._selected_control_point else 0.45)
            x, y, z = point
            vertices.extend((
                (x - size, y, z), (x + size, y, z),
                (x, y - size, z), (x, y + size, z),
                (x, y, z - size), (x, y, z + size),
            ))
            colors.extend((color,) * 6)
        self._draw_colored(np.asarray(vertices, np.float32), np.asarray(colors, np.float32), 1)

    def _draw_brush_cursor(self) -> None:
        if not self.draw_mode or self._hover_ground is None:
            return
        x, y, _ = self._hover_ground
        vertices = _brush_ring() * max(1.0, self.brush_size) + np.array((x, 0.0, -y), np.float32)
        colors = np.tile(_theme_gl_color("#00d4ff", 0.85), (len(vertices), 1)).astype(np.float32)
        self._draw_colored(vertices, colors, 1)

    def _stamp_brush(self, position: QPointF) -> None:
        """Scatter one brush stamp on the ground plane, spacing permitting."""
        point = self._point_on_ground(position)
        if point is None:
            return
        if self._stroke_last is not None:
            step = math.hypot(point[0] - self._stroke_last[0], point[1] - self._stroke_last[1])
            if step < max(0.001, self.brush_spacing):
                return
        self._stroke_last = point
        count = max(1, int(self.brush_density))
        radius = max(0.0, self.brush_size)
        angles = _RNG.uniform(0.0, 2.0 * math.pi, count)
        # sqrt keeps the scatter uniform over the disc instead of clumping at the centre
        distances = radius * np.sqrt(_RNG.random(count))
        self.points_drawn.emit([
            (point[0] + float(distance * math.cos(angle)), point[1] + float(distance * math.sin(angle)), point[2])
            for angle, distance in zip(angles, distances)
        ])

    def _draw_rope(self) -> None:
        if len(self._positions) < 2:
            return
        from OpenGL import GL

        camera_position = self.camera.position
        layers: tuple[list, list, list] = ([], [], [])
        for group in self._rope_groups:
            points, widths, radii, colors = self._rope_samples(
                self._positions[group], self._radii[group], self._colors[group], camera_position,
            )
            aura = colors.copy()
            aura[:, 3] *= 0.18
            corona = colors.copy()
            corona[:, 3] *= 0.72
            core = np.ones_like(colors)
            core[:, 3] = colors[:, 3] * 0.95
            for layer, scale, layer_colors in zip(layers, (2.8, 1.0, 0.3), (aura, corona, core)):
                layer.append(self._rope_triangles(points, widths, radii * scale, layer_colors))
        GL.glDepthMask(False)
        for layer in layers:
            if not layer:
                continue
            self._draw_colored(
                np.concatenate([vertices for vertices, _ in layer]),
                np.concatenate([colors for _, colors in layer]),
                4,
                additive=True,
            )
        GL.glDepthMask(True)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

    def _rope_samples(self, positions, radii, colors, camera_position):
        """Camera-facing Catmull-Rom samples for one rope, shared by every ribbon layer."""
        count = len(positions)
        segments = np.arange(count - 1)
        p0 = positions[np.clip(segments - 1, 0, count - 1)][:, None, :]
        p1 = positions[segments][:, None, :]
        p2 = positions[segments + 1][:, None, :]
        p3 = positions[np.clip(segments + 2, 0, count - 1)][:, None, :]
        amount = np.linspace(0.0, 1.0, ROPE_SUBDIVISIONS + 1, dtype=np.float32)
        t = amount[None, :, None]
        t2 = t * t
        points = (0.5 * ((2 * p1) + (-p0 + p2) * t
                         + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                         + (-p0 + 3 * p1 - 3 * p2 + p3) * (t2 * t))).reshape(-1, 3)
        tangents = (0.5 * ((-p0 + p2) + (4 * p0 - 10 * p1 + 8 * p2 - 2 * p3) * t
                           + (-3 * p0 + 9 * p1 - 9 * p2 + 3 * p3) * t2)).reshape(-1, 3)
        tangents /= np.maximum(1e-8, np.linalg.norm(tangents, axis=1, keepdims=True))
        widths = np.cross(tangents, camera_position - points)
        lengths = np.linalg.norm(widths, axis=1)
        degenerate = lengths < 1e-8
        if degenerate.any():
            axis = np.where(
                np.abs(tangents[degenerate, 1:2]) < 0.999,
                np.array((0.0, 1.0, 0.0), np.float32),
                np.array((1.0, 0.0, 0.0), np.float32),
            )
            widths[degenerate] = np.cross(tangents[degenerate], axis)
            lengths = np.linalg.norm(widths, axis=1)
        widths /= np.maximum(1e-8, lengths)[:, None]
        # Sequential "keep facing the previous sample" flip chain, as a cumulative sign product.
        flips = np.sign(np.einsum("ij,ij->i", widths[1:], widths[:-1]))
        flips[flips == 0.0] = 1.0
        widths *= np.concatenate((np.ones(1, np.float32), np.cumprod(flips)))[:, None]
        sample_radii = (radii[segments][:, None]
                        + (radii[segments + 1] - radii[segments])[:, None] * amount[None, :]).reshape(-1)
        sample_colors = (colors[segments][:, None, :]
                         + (colors[segments + 1] - colors[segments])[:, None, :] * amount[None, :, None]).reshape(-1, 4)
        return points, widths, sample_radii, sample_colors

    def _rope_triangles(self, points, widths, radii, colors) -> tuple[np.ndarray, np.ndarray]:
        offsets = widths * radii[:, None]
        low = points - offsets
        high = points + offsets
        a, b = _strip_indices(len(points) // (ROPE_SUBDIVISIONS + 1))
        return (
            np.stack((low[a], low[b], high[b], low[a], high[b], high[a]), axis=1).reshape(-1, 3),
            np.stack((colors[a], colors[b], colors[b], colors[a], colors[b], colors[a]), axis=1).reshape(-1, 4),
        )

    def _draw_colored(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        primitive: int,
        additive: bool = False,
    ) -> None:
        from OpenGL import GL

        if not len(positions):
            return
        packed = np.column_stack((positions, colors)).astype(np.float32)
        GL.glBindVertexArray(self._color_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._color_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, packed.nbytes, packed, GL.GL_DYNAMIC_DRAW)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, False, 28, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 4, GL.GL_FLOAT, False, 28, GL.ctypes.c_void_p(12))
        GL.glUseProgram(self._color_program)
        self._set_camera_uniforms(self._color_program)
        if additive:
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE)
        mode = GL.GL_LINES if primitive == 1 else GL.GL_TRIANGLES
        GL.glDrawArrays(mode, 0, len(positions))
        if additive:
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

    @gl_guard("event")
    def mousePressEvent(self, event) -> None:
        self.setFocus()
        self._last_mouse = event.position()
        self._sync_gizmo_settings(event)
        if event.button() == Qt.LeftButton and self.gizmo.visible and not self.draw_mode:
            origin, direction = self._gizmo_ray(event.position())
            axis = self.gizmo.hit_test(origin, direction, self.camera.position)
            if axis != GizmoAxis.NONE:
                self.gizmo.begin_drag(axis, (event.position().x(), event.position().y()))
                self.update()
                return
            control_point = self._pick_control_point(event.position())
            if control_point is not None:
                self._selected_control_point = control_point
                self._sync_gizmo()
                self.update()
                return
        if event.button() == Qt.RightButton and not self.gizmo.is_dragging:
            self._is_flying = True
            self._fly_last_time = time.perf_counter()
            self._pressed_keys.clear()
            self._fly_timer.start()
            self.setCursor(Qt.BlankCursor)
            return
        if event.button() == Qt.LeftButton:
            if self.draw_mode:
                self._painting = True
                self._stroke_last = None
                self._stamp_brush(event.position())
                return
            if self.pick_mode:
                picked = self._pick_nearest(event.position())
                if picked is not None:
                    self.point_picked.emit(picked)
        elif event.button() == Qt.MiddleButton:
            if event.modifiers() & Qt.ControlModifier:
                self._action = "zoom"
            elif event.modifiers() & Qt.ShiftModifier:
                self._action = "pan"
            else:
                self._action = "orbit"

    @gl_guard("event")
    def mouseMoveEvent(self, event) -> None:
        delta = event.position() - self._last_mouse
        self._last_mouse = event.position()
        if self.draw_mode and not self._is_flying:
            self._hover_ground = self._point_on_ground(event.position())
            if self._painting:
                self._stamp_brush(event.position())
            self.update()
            return
        self._sync_gizmo_settings(event)
        if self.gizmo.is_dragging:
            moved = self.gizmo.update_drag(
                (event.position().x(), event.position().y()),
                self.camera.view_matrix, self.camera.projection_matrix,
                self.width(), self.height(), self.camera.position,
            )
            if moved and "position" in moved:
                position = tuple(float(value) for value in moved["position"])
                self._control_points[self._selected_control_point] = _source_to_gl((position,))[0]
                self.control_point_moved.emit(self._selected_control_point, position)
            self.update()
            return
        if self._is_flying:
            self.camera.look(delta.x(), delta.y())
            self.update()
        elif self._action == "orbit":
            self.camera.orbit(delta.x(), delta.y())
            self.update()
        elif self._action == "pan":
            self.camera.pan(delta.x(), delta.y())
            self.update()
        elif self._action == "zoom":
            self.camera.zoom(-(delta.x() - delta.y()))
            self.update()
        elif self.gizmo.visible and not self.draw_mode:
            origin, direction = self._gizmo_ray(event.position())
            axis = self.gizmo.hit_test(origin, direction, self.camera.position)
            if axis != self.gizmo.hover_axis:
                self.gizmo.hover_axis = axis
                self.update()

    @gl_guard("event")
    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._painting:
            self._painting = False
            self._stroke_last = None
            return
        if self.gizmo.is_dragging:
            self.gizmo.end_drag()
            self.update()
            return
        if event.button() == Qt.RightButton and self._is_flying:
            self._stop_flying()
        self._action = None

    @gl_guard("event")
    def wheelEvent(self, event) -> None:
        if self._is_flying:
            factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
            self.fly_speed = max(10.0, min(20_000.0, self.fly_speed * factor))
            return
        self.camera.zoom(event.angleDelta().y())
        self.update()

    def keyPressEvent(self, event) -> None:
        if self._is_flying:
            if not event.isAutoRepeat():
                self._pressed_keys.add(event.key())
            event.accept()
            return
        if event.key() == Qt.Key_F:
            self.fit_view()
            event.accept()
            return
        if event.key() == Qt.Key_Q:
            self.draw_mode_requested.emit(False)
            event.accept()
            return
        if event.key() == Qt.Key_W:
            self.draw_mode_requested.emit(True)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if self._is_flying:
            if not event.isAutoRepeat():
                self._pressed_keys.discard(event.key())
            event.accept()
            return
        super().keyReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_ground = None
        self.update()
        super().leaveEvent(event)

    def focusOutEvent(self, event) -> None:
        self._painting = False
        self._stop_flying()
        super().focusOutEvent(event)

    def _stop_flying(self) -> None:
        if not self._is_flying:
            return
        self._is_flying = False
        self._pressed_keys.clear()
        self._fly_timer.stop()
        self.unsetCursor()
        self.update()

    def _update_fly_movement(self) -> None:
        if not self._is_flying:
            self._fly_timer.stop()
            return
        now = time.perf_counter()
        delta_time = max(0.001, min(0.1, now - (self._fly_last_time or now)))
        self._fly_last_time = now
        forward = float(Qt.Key_W in self._pressed_keys) - float(Qt.Key_S in self._pressed_keys)
        right = float(Qt.Key_D in self._pressed_keys) - float(Qt.Key_A in self._pressed_keys)
        up = float(Qt.Key_E in self._pressed_keys or Qt.Key_Space in self._pressed_keys)
        up -= float(Qt.Key_Q in self._pressed_keys or Qt.Key_C in self._pressed_keys)
        length = math.sqrt(forward * forward + right * right + up * up)
        if length == 0.0:
            return
        if length > 1.0:
            forward /= length
            right /= length
            up /= length
        modifiers = QApplication.keyboardModifiers()
        speed_multiplier = 3.0 if modifiers & Qt.ShiftModifier else 1.0
        if modifiers & (Qt.ControlModifier | Qt.AltModifier):
            speed_multiplier = 0.25
        distance = self.fly_speed * speed_multiplier * delta_time
        self.camera.move_fly(forward * distance, right * distance, up * distance)
        self.update()

    def fit_view(self) -> None:
        if not len(self._positions):
            return
        all_points = np.vstack((self._positions, *self._control_points.values()))
        self.camera.fit_to_bounds(all_points.min(axis=0), all_points.max(axis=0))
        self.update()

    def _pick_control_point(self, point: QPointF) -> str | None:
        names = tuple(self._control_points)
        screen = self._project_points(np.asarray([self._control_points[name] for name in names], np.float32))
        distances = np.hypot(screen[:, 0] - point.x(), screen[:, 1] - point.y())
        index = int(np.argmin(distances))
        return names[index] if distances[index] < 18.0 else None

    def _project_points(self, positions: np.ndarray) -> np.ndarray:
        """Projects world points to widget pixels; points behind the camera land infinitely far away."""
        view_projection = self.camera.projection_matrix.T @ self.camera.view_matrix.T
        clip = np.column_stack((positions, np.ones(len(positions), np.float32))) @ view_projection.T
        behind = clip[:, 3] <= 0
        ndc = clip[:, :2] / np.where(behind, 1.0, clip[:, 3])[:, None]
        screen = np.column_stack((
            (ndc[:, 0] + 1.0) * 0.5 * self.width(),
            (1.0 - ndc[:, 1]) * 0.5 * self.height(),
        ))
        screen[behind] = np.inf
        return screen

    def _point_on_ground(self, point: QPointF):
        origin, direction = self.camera.screen_to_ray(point.x(), point.y(), self.width(), self.height())
        if abs(direction[1]) < 1e-8:
            return None
        amount = -origin[1] / direction[1]
        if amount < 0:
            return None
        value = origin + direction * amount
        return float(value[0]), float(-value[2]), float(value[1])

    def _pick_nearest(self, point: QPointF) -> int | None:
        if not len(self._positions):
            return None
        screen = self._project_points(self._positions)
        distances = np.hypot(screen[:, 0] - point.x(), screen[:, 1] - point.y())
        index = int(np.argmin(distances))
        return index if distances[index] < 14.0 else None


class VSnapViewport(QWidget):
    """SmartProp-style viewport shell around the VSnap particle renderer."""

    points_drawn = Signal(list)
    point_picked = Signal(int)
    draw_mode_changed = Signal(bool)
    control_point_moved = Signal(str, tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QWidget(self)
        toolbar.setFixedHeight(28)
        toolbar.setObjectName("SPE_Viewport3D_Toolbar")
        toolbar.setProperty("h5Component", "smartpropViewportToolbar")
        toolbar.setMinimumWidth(0)
        toolbar.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 0, 8, 0)
        toolbar_layout.setSpacing(8)

        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.setExclusive(True)
        self.btn_select = self._make_toggle_button(
            "Select particles (Q)",
            gui_assets_dir("icons", "tools", "modeldoc_editor", "manipulation_none.png"),
            gui_assets_dir("icons", "tools", "modeldoc_editor", "manipulation_none_active.png"),
        )
        self.btn_draw = self._make_toggle_button(
            "Draw particles on the ground plane (W)",
            gui_assets_dir("icons", "tools", "hammer", "paint_tool_icon.png"),
            gui_assets_dir("icons", "tools", "hammer", "paint_tool_icon_activated.png"),
        )
        self.mode_button_group.addButton(self.btn_select)
        self.mode_button_group.addButton(self.btn_draw)
        self.btn_select.setChecked(True)
        toolbar_layout.addWidget(self.btn_select)
        toolbar_layout.addWidget(self.btn_draw)

        self.brush_settings = QWidget(toolbar)
        brush_layout = QHBoxLayout(self.brush_settings)
        brush_layout.setContentsMargins(0, 0, 0, 0)
        brush_layout.setSpacing(6)
        self.brush_size_input = self._make_brush_input(
            brush_layout, "Size", "Scatter radius of each brush stamp", [0.0, 256.0], 16.0,
        )
        self.brush_spacing_input = self._make_brush_input(
            brush_layout, "Spacing", "Distance the cursor travels between stamps", [1.0, 256.0], 16.0,
        )
        self.brush_density_input = self._make_brush_input(
            brush_layout, "Density", "Particles dropped per stamp", [1, 32], 1, int_output=True,
        )
        self.brush_settings.hide()
        toolbar_layout.addWidget(self.brush_settings)

        self.btn_frame = self._make_toggle_button(
            "Frame all particles (F)",
            gui_assets_dir("icons", "tools", "sfm", "icon_grapheditor_autoframe.png"),
        )
        self.btn_frame.setCheckable(False)
        self.btn_frame.clicked.connect(self.fit_view)
        toolbar_layout.addWidget(self.btn_frame)

        toolbar_layout.addWidget(QLabel("View:"))
        self.preview_combo = QComboBox(self)
        self.preview_combo.addItems(("Sprites", "Rope"))
        self.preview_combo.setProperty("h5Component", "smartpropViewportCombo")
        toolbar_layout.addWidget(self.preview_combo)

        toolbar_layout.addWidget(QLabel("Grid Step:"))
        self.grid_combo = QComboBox(self)
        self.grid_combo.addItems(("1", "2", "4", "8", "16", "32", "64", "128", "256"))
        self.grid_combo.setCurrentText("8")
        self.grid_combo.setProperty("h5Component", "smartpropViewportCombo")
        toolbar_layout.addWidget(self.grid_combo)

        toolbar_layout.addWidget(QLabel("Stream:"))
        self.stream_combo = QComboBox(self)
        self.stream_combo.setProperty("h5Component", "smartpropViewportCombo")
        toolbar_layout.addWidget(self.stream_combo)

        self.btn_values = self._make_toggle_button(
            "Preview stream values",
            gui_assets_dir("icons", "tools", "modeldoc_editor", "view_controls_streams.png"),
        )
        toolbar_layout.addWidget(self.btn_values)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar)

        self.render_area = VSnap3DRenderArea(self)
        self.render_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.render_area.points_drawn.connect(self.points_drawn.emit)
        self.render_area.point_picked.connect(self.point_picked.emit)
        self.render_area.control_point_moved.connect(self.control_point_moved.emit)
        self.render_area.draw_mode_requested.connect(self._set_draw_mode)
        self.preview_combo.currentTextChanged.connect(self.set_preview_mode)
        self.grid_combo.currentTextChanged.connect(self._set_grid_step)
        self.btn_select.clicked.connect(lambda: self._set_draw_mode(False))
        self.btn_draw.clicked.connect(lambda: self._set_draw_mode(True))
        self.btn_values.clicked.connect(self._toggle_values)
        self.stream_combo.currentIndexChanged.connect(self._set_selected_stream)
        layout.addWidget(self.render_area)

    def _make_brush_input(self, layout, label, tooltip, slider_range, value, int_output=False) -> FloatWidget:
        """One labelled brush setting, wired straight into the render area."""
        caption = QLabel(label, self.brush_settings)
        caption.setToolTip(tooltip)
        widget = FloatWidget(int_output=int_output, slider_range=slider_range, value=value,
                             only_positive=True, spacer_enable=False)
        widget.setToolTip(tooltip)
        widget.setFixedWidth(104)
        attribute = f"brush_{label.lower()}"
        widget.edited.connect(lambda amount: setattr(self.render_area, attribute, amount))
        layout.addWidget(caption)
        layout.addWidget(widget)
        return widget

    def _make_toggle_button(self, tooltip: str, icon_off: str, icon_on: str | None = None) -> QToolButton:
        button = QToolButton(self)
        button.setCheckable(True)
        button.setToolTip(tooltip)
        button.setFixedSize(22, 22)
        button.setIconSize(QSize(16, 16))
        button.setCursor(Qt.PointingHandCursor)
        button.setProperty("h5Component", "smartpropViewportToggle")
        icon = QIcon()
        icon.addFile(icon_off, QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon.addFile(icon_on or icon_off, QSize(), QIcon.Mode.Normal, QIcon.State.On)
        button.setIcon(icon)
        return button

    @property
    def draw_mode(self) -> bool:
        return self.render_area.draw_mode

    @draw_mode.setter
    def draw_mode(self, enabled: bool) -> None:
        self._set_draw_mode(enabled)

    @property
    def pick_mode(self) -> bool:
        return self.render_area.pick_mode

    @pick_mode.setter
    def pick_mode(self, enabled: bool) -> None:
        if enabled:
            self._set_draw_mode(False)
        self.render_area.pick_mode = enabled

    def _set_draw_mode(self, enabled: bool) -> None:
        changed = self.render_area.draw_mode != enabled
        self.render_area.draw_mode = enabled
        if enabled:
            self.render_area.pick_mode = False
        self.btn_draw.setChecked(enabled)
        self.btn_select.setChecked(not enabled)
        self.brush_settings.setVisible(enabled)
        if enabled:
            self.render_area.setCursor(Qt.CrossCursor)
        else:
            self.render_area.unsetCursor()
        if changed:
            self.draw_mode_changed.emit(enabled)

    def _set_grid_step(self, text: str) -> None:
        try:
            self.render_area.grid_step = float(text)
            self.render_area.update()
        except ValueError:
            return

    def _toggle_values(self, checked: bool) -> None:
        self.render_area.show_values = checked
        self.render_area.update()

    def _set_selected_stream(self, index: int) -> None:
        if index == -1:
            self.render_area.selected_stream = ""
        else:
            self.render_area.selected_stream = self.stream_combo.itemData(index)
        self.render_area.update()

    def set_document(self, document) -> None:
        current_stream = self.stream_combo.currentData()
        self.stream_combo.clear()
        for stream in document.streams:
            self.stream_combo.addItem(f"{stream.name}  ·  {stream.type}", stream.name)
        if current_stream:
            index = self.stream_combo.findData(current_stream)
            if index != -1:
                self.stream_combo.setCurrentIndex(index)
        self.render_area.set_document(document)

    def set_control_points(self, start, end) -> None:
        self.render_area.set_control_points(start, end)

    def set_preview_mode(self, mode: str) -> None:
        if self.preview_combo.currentText() != mode:
            self.preview_combo.setCurrentText(mode)
        self.render_area.set_preview_mode(mode)

    def fit_view(self) -> None:
        self.render_area.fit_view()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Q:
            self._set_draw_mode(False)
        elif event.key() == Qt.Key_W:
            self._set_draw_mode(True)
        elif event.key() == Qt.Key_F:
            self.fit_view()
        else:
            super().keyPressEvent(event)
