"""
Transform gizmo system for the 3D viewport.
Supports Translate (W), Rotate (E), and Scale (R) gizmo modes.
Manipulates Source 2 coordinates while rendering and interacting in GL space.
"""
import math
from enum import IntEnum
from typing import Optional, Tuple

import numpy as np

from hammer5tools_gui.editors.smartprop_editor.viewport_3d.camera import (
    translation_matrix, scale_matrix, rotation_matrix_euler, _normalize, SOURCE2_TO_GL, decompose_trs
)


def rotation_matrix_axis_angle(axis, angle_deg):
    angle = math.radians(angle_deg)
    c = math.cos(angle)
    s = math.sin(angle)
    t = 1.0 - c
    x, y, z = axis
    m = np.eye(4, dtype=np.float32)
    m[0, 0] = t*x*x + c
    m[0, 1] = t*x*y + s*z
    m[0, 2] = t*x*z - s*y
    m[1, 0] = t*x*y - s*z
    m[1, 1] = t*y*y + c
    m[1, 2] = t*y*z + s*x
    m[2, 0] = t*x*z + s*y
    m[2, 1] = t*y*z - s*x
    m[2, 2] = t*z*z + c
    return m


class GizmoMode(IntEnum):
    NONE = 0
    TRANSLATE = 1   # W key
    ROTATE = 2      # E key
    SCALE = 3       # R key


class GizmoAxis:
    NONE = ""
    X = "x"
    Y = "y"
    Z = "z"
    XY = "xy"          # Planar translation in XY plane (normal Z, blue)
    XZ = "xz"          # Planar translation in XZ plane (normal Y, green)
    YZ = "yz"          # Planar translation in YZ plane (normal X, red)
    SCREEN = "screen"  # Screen-plane translation (center circle/dot handle in Translate mode)
    CENTER = "center"  # Uniform-scale handle at the axes' origin (Scale mode only)


# Axis colors (Red for X, Green for Y, Blue for Z)
AXIS_COLORS = {
    GizmoAxis.X: np.array([0.9, 0.2, 0.2], dtype=np.float32),
    GizmoAxis.Y: np.array([0.2, 0.8, 0.2], dtype=np.float32),
    GizmoAxis.Z: np.array([0.3, 0.4, 0.9], dtype=np.float32),
    GizmoAxis.XY: np.array([0.3, 0.4, 0.9], dtype=np.float32),  # Normal is Z (Blue)
    GizmoAxis.XZ: np.array([0.2, 0.8, 0.2], dtype=np.float32),  # Normal is Y (Green)
    GizmoAxis.YZ: np.array([0.9, 0.2, 0.2], dtype=np.float32),  # Normal is X (Red)
    GizmoAxis.SCREEN: np.array([0.92, 0.92, 0.92], dtype=np.float32),
}

AXIS_HIGHLIGHT_COLORS = {
    GizmoAxis.X: np.array([1.0, 0.6, 0.2], dtype=np.float32),
    GizmoAxis.Y: np.array([0.6, 1.0, 0.2], dtype=np.float32),
    GizmoAxis.Z: np.array([0.2, 0.6, 1.0], dtype=np.float32),
    GizmoAxis.XY: np.array([0.4, 0.7, 1.0], dtype=np.float32),
    GizmoAxis.XZ: np.array([0.6, 1.0, 0.4], dtype=np.float32),
    GizmoAxis.YZ: np.array([1.0, 0.5, 0.5], dtype=np.float32),
    GizmoAxis.SCREEN: np.array([1.0, 1.0, 1.0], dtype=np.float32),
}

# Hover/active handles use bright yellow across all axes
AXIS_HOVER_COLOR = np.array([1.0, 0.9, 0.2], dtype=np.float32)

# Grayscale color for disabled axes
AXIS_DISABLED_COLOR = np.array([0.42, 0.42, 0.42], dtype=np.float32)

# Uniform-scale center handle (Scale mode only)
CENTER_COLOR = np.array([0.88, 0.88, 0.88], dtype=np.float32)
CENTER_HIGHLIGHT_COLOR = np.array([1.0, 0.85, 0.2], dtype=np.float32)

# Translate arrows length multiplier
TRANSLATE_LENGTH_SCALE = 1.45
# Size of the Scale-mode end cubes
SCALE_CUBE_SIZE = 0.12

# Map Source 2 axes directions to OpenGL space
AXIS_DIRECTIONS = {
    GizmoAxis.X: np.array([1.0, 0.0, 0.0], dtype=np.float32),
    GizmoAxis.Y: np.array([0.0, 0.0, -1.0], dtype=np.float32),
    GizmoAxis.Z: np.array([0.0, 1.0, 0.0], dtype=np.float32),
}


def project_to_screen(world_pos, view_matrix, proj_matrix, w, h):
    """Project a 3D GL world space point to 2D screen coordinates."""
    pos_h = np.append(world_pos, 1.0)
    clip_pos = pos_h @ view_matrix @ proj_matrix
    if abs(clip_pos[3]) > 1e-6:
        ndc = clip_pos[:3] / clip_pos[3]
    else:
        ndc = clip_pos[:3]
    sx = (ndc[0] + 1.0) * 0.5 * w
    sy = (1.0 - ndc[1]) * 0.5 * h
    return np.array([sx, sy], dtype=np.float32)


def screen_to_world_ray(sx, sy, w, h, view_matrix, proj_matrix, camera_pos):
    """Convert screen coordinates to a world ray (origin, direction)."""
    ndc_x = (2.0 * sx / max(w, 1)) - 1.0
    ndc_y = 1.0 - (2.0 * sy / max(h, 1))

    inv_proj = np.linalg.inv(proj_matrix).T
    inv_view = np.linalg.inv(view_matrix).T

    clip = np.array([ndc_x, ndc_y, -1.0, 1.0], dtype=np.float32)
    eye_pos = inv_proj @ clip
    eye_pos = np.array([eye_pos[0], eye_pos[1], -1.0, 0.0], dtype=np.float32)

    world_dir = inv_view @ eye_pos
    direction = _normalize(world_dir[:3])
    return camera_pos.copy(), direction


class Gizmo:
    """Transform gizmo that renders axis handles and processes drag interactions."""

    def __init__(self):
        self.mode: GizmoMode = GizmoMode.TRANSLATE
        # Position, rotation, scale in Source 2 coordinates!
        self.position = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.rotation = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.scale_val = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.visible = False

        # Interaction state
        self.hover_axis: str = GizmoAxis.NONE
        self.active_axis: str = GizmoAxis.NONE
        self._dragging = False
        self._drag_start_pos = None
        self._drag_start_gl_pos = None
        self._drag_start_value = None
        self._drag_plane_start_hit = None
        self._accumulated_angle = 0.0
        self._last_angle = None

        # Per-mode, per-axis availability
        self.axis_availability = {
            GizmoMode.TRANSLATE: {GizmoAxis.X: True, GizmoAxis.Y: True, GizmoAxis.Z: True},
            GizmoMode.ROTATE:    {GizmoAxis.X: True, GizmoAxis.Y: True, GizmoAxis.Z: True},
            GizmoMode.SCALE:     {GizmoAxis.X: True, GizmoAxis.Y: True, GizmoAxis.Z: True, GizmoAxis.CENTER: True},
        }

        # GPU resources
        self._arrow_vao = 0
        self._arrow_vbo = 0
        self._arrow_vertex_count = 0
        self._shaft_vao = 0
        self._shaft_vbo = 0
        self._shaft_vertex_count = 0
        self._ring_vao = 0
        self._ring_vbo = 0
        self._ring_vertex_count = 0
        self._cube_vao = 0
        self._cube_vbo = 0
        self._cube_vertex_count = 0
        self._plane_vao = 0
        self._plane_vbo = 0
        self._plane_vertex_count = 0
        self._screen_ring_vao = 0
        self._screen_ring_vbo = 0
        self._screen_ring_vertex_count = 0
        self._initialized = False

        self.coordinate_space = "World"  # "World" | "Local" | "Screen"
        self.snapping_enabled = False
        self.grid_step = 8.0
        self.rotation_step = 15.0

        # Camera vectors for Screen space
        self.camera_right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self.camera_forward = np.array([0.0, 0.0, -1.0], dtype=np.float32)

    def get_gizmo_scale(self, camera_pos: np.ndarray, gl_pos: Optional[np.ndarray] = None) -> float:
        """Calculate gizmo scale in world units to maintain a constant screen-space size."""
        if gl_pos is None:
            gl_pos = self._get_gl_position()
        dist = float(np.linalg.norm(camera_pos - gl_pos))
        return max(dist * (0.08 / 1.5), 1e-4)

    def get_axis_direction(self, axis_name: str) -> np.ndarray:
        """Get the direction of the given axis in GL space."""
        axis_name = axis_name.lower()
        if self.coordinate_space == "Local":
            R = rotation_matrix_euler(*self.rotation)
            s2_dir = R[{"x": 0, "y": 1, "z": 2}[axis_name], :3]
            gl_dir = (SOURCE2_TO_GL.T @ np.append(s2_dir, 0.0))[:3]
            return _normalize(gl_dir)
        elif self.coordinate_space == "Screen":
            gl_dir = {
                "x": self.camera_right,
                "y": self.camera_up,
                "z": self.camera_forward,
            }[axis_name]
            return _normalize(gl_dir)
        else:  # World
            return {
                "x": np.array([1.0, 0.0, 0.0], dtype=np.float32),
                "y": np.array([0.0, 0.0, -1.0], dtype=np.float32),
                "z": np.array([0.0, 1.0, 0.0], dtype=np.float32),
            }[axis_name]

    def get_s2_axis_direction(self, axis_name: str) -> np.ndarray:
        """Get the direction of the given axis in Source 2 space."""
        axis_name = axis_name.lower()
        if self.coordinate_space == "Local":
            R = rotation_matrix_euler(*self.rotation)
            return _normalize(R[{"x": 0, "y": 1, "z": 2}[axis_name], :3])
        elif self.coordinate_space == "Screen":
            gl_dir = {
                "x": self.camera_right,
                "y": self.camera_up,
                "z": self.camera_forward,
            }[axis_name]
            s2_dir = (SOURCE2_TO_GL @ np.append(gl_dir, 0.0))[:3]
            return _normalize(s2_dir)
        else:  # World
            return {
                "x": np.array([1.0, 0.0, 0.0], dtype=np.float32),
                "y": np.array([0.0, 1.0, 0.0], dtype=np.float32),
                "z": np.array([0.0, 0.0, 1.0], dtype=np.float32),
            }[axis_name]

    def set_mode(self, mode: GizmoMode):
        self.mode = mode

    def set_transform(self, position, rotation, scale_val):
        self.position = np.array(position, dtype=np.float32)
        self.rotation = np.array(rotation, dtype=np.float32)
        self.scale_val = np.array(scale_val, dtype=np.float32)
        self.visible = True

    def hide(self):
        self.visible = False
        self.active_axis = GizmoAxis.NONE
        self.hover_axis = GizmoAxis.NONE

    def set_axis_availability(self, availability: dict):
        """Update which axes can be manipulated."""
        for mode, axes in availability.items():
            if mode in self.axis_availability and isinstance(axes, dict):
                for axis, enabled in axes.items():
                    if axis in self.axis_availability[mode]:
                        self.axis_availability[mode][axis] = bool(enabled)

    def is_axis_available(self, axis_name: str, mode: Optional[GizmoMode] = None) -> bool:
        """Return whether the given axis can be dragged in the given mode."""
        m = self.mode if mode is None else mode
        avail_map = self.axis_availability.get(m, {})
        if axis_name == GizmoAxis.XY:
            return avail_map.get(GizmoAxis.X, True) and avail_map.get(GizmoAxis.Y, True)
        elif axis_name == GizmoAxis.XZ:
            return avail_map.get(GizmoAxis.X, True) and avail_map.get(GizmoAxis.Z, True)
        elif axis_name == GizmoAxis.YZ:
            return avail_map.get(GizmoAxis.Y, True) and avail_map.get(GizmoAxis.Z, True)
        elif axis_name == GizmoAxis.SCREEN:
            return (avail_map.get(GizmoAxis.X, True) or
                    avail_map.get(GizmoAxis.Y, True) or
                    avail_map.get(GizmoAxis.Z, True))
        return avail_map.get(axis_name, True)

    def init_geometry(self):
        """Create GPU geometry for gizmo handles. Must be called in GL context."""
        if self._initialized:
            return
        from OpenGL import GL

        # Arrow geometry (shaft + cone tip)
        arrow_verts = self._build_arrow_vertices()
        self._arrow_vao = GL.glGenVertexArrays(1)
        self._arrow_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._arrow_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._arrow_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, arrow_verts.nbytes, arrow_verts, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)
        self._arrow_vertex_count = len(arrow_verts)

        # Plain shaft geometry (Scale mode)
        shaft_verts = self._build_shaft_vertices()
        self._shaft_vao = GL.glGenVertexArrays(1)
        self._shaft_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._shaft_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._shaft_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, shaft_verts.nbytes, shaft_verts, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)
        self._shaft_vertex_count = len(shaft_verts)

        # 3D solid ring band geometry
        ring_verts = self._build_ring_vertices()
        self._ring_vao = GL.glGenVertexArrays(1)
        self._ring_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._ring_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._ring_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, ring_verts.nbytes, ring_verts, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)
        self._ring_vertex_count = len(ring_verts)

        # Cube geometry (Scale ends and center)
        cube_verts = self._build_cube_vertices()
        self._cube_vao = GL.glGenVertexArrays(1)
        self._cube_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._cube_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._cube_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, cube_verts.nbytes, cube_verts, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)
        self._cube_vertex_count = len(cube_verts)

        # Planar quad geometry (Translate dual-axis handles)
        plane_verts = self._build_plane_vertices()
        self._plane_vao = GL.glGenVertexArrays(1)
        self._plane_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._plane_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._plane_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, plane_verts.nbytes, plane_verts, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)
        self._plane_vertex_count = len(plane_verts)

        # Center screen ring geometry (Translate screen-plane handle)
        screen_ring_verts = self._build_screen_ring_vertices()
        self._screen_ring_vao = GL.glGenVertexArrays(1)
        self._screen_ring_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._screen_ring_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._screen_ring_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, screen_ring_verts.nbytes, screen_ring_verts, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)
        self._screen_ring_vertex_count = len(screen_ring_verts)

        self._initialized = True

    def _get_gl_position(self):
        """Map S2 position to GL space."""
        pos_h = np.append(self.position, 1.0)
        gl_pos = SOURCE2_TO_GL.T @ pos_h
        return gl_pos[:3]

    def render(self, shader_program, view_matrix, proj_matrix, camera_pos):
        """Render the gizmo. Must be called in GL context with gizmo shader active."""
        if not self.visible or not self._initialized or self.mode == GizmoMode.NONE:
            return

        from OpenGL import GL

        GL.glUseProgram(shader_program)
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(shader_program, "uView"), 1, GL.GL_FALSE, view_matrix
        )
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(shader_program, "uProjection"), 1, GL.GL_FALSE, proj_matrix
        )

        GL.glDepthMask(GL.GL_TRUE)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

        if self._dragging and self._drag_start_gl_pos is not None and self.mode in (GizmoMode.ROTATE, GizmoMode.SCALE):
            gl_pos = self._drag_start_gl_pos
        else:
            gl_pos = self._get_gl_position()
        gizmo_scale = self.get_gizmo_scale(camera_pos, gl_pos)

        R_space = np.eye(4, dtype=np.float32)
        if self.coordinate_space in ("Local", "Screen"):
            T = np.array([
                self.get_axis_direction(GizmoAxis.X),
                self.get_axis_direction(GizmoAxis.Y),
                self.get_axis_direction(GizmoAxis.Z),
            ], dtype=np.float32)
            W = SOURCE2_TO_GL[:3, :3]
            R_space[:3, :3] = W.T @ T

        # 1. Render single-axis handles (Arrows / Rings / Shafts)
        for axis_name in [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]:
            available = self.is_axis_available(axis_name)
            is_active = available and (axis_name == self.active_axis)
            is_hover = available and (axis_name == self.hover_axis and not self._dragging)

            if not available:
                color = AXIS_DISABLED_COLOR
            elif is_active or is_hover:
                color = AXIS_HOVER_COLOR
            else:
                color = AXIS_COLORS[axis_name]

            axis_rot = self._axis_rotation_matrix(axis_name)
            length_factor = TRANSLATE_LENGTH_SCALE if self.mode == GizmoMode.TRANSLATE else 1.0
            model = (
                scale_matrix(gizmo_scale, gizmo_scale * length_factor, gizmo_scale)
                @ axis_rot
                @ R_space
                @ translation_matrix(*gl_pos)
            )

            GL.glUniformMatrix4fv(
                GL.glGetUniformLocation(shader_program, "uModel"),
                1, GL.GL_FALSE, model
            )
            GL.glUniform3fv(
                GL.glGetUniformLocation(shader_program, "uColor"),
                1, color
            )
            if not available:
                alpha = 0.3
            elif is_active or is_hover:
                alpha = 1.0
            else:
                alpha = 0.95
            GL.glUniform1f(
                GL.glGetUniformLocation(shader_program, "uAlpha"),
                alpha
            )

            if self.mode == GizmoMode.TRANSLATE:
                GL.glBindVertexArray(self._arrow_vao)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._arrow_vertex_count)
                GL.glBindVertexArray(0)
            elif self.mode == GizmoMode.ROTATE:
                GL.glBindVertexArray(self._ring_vao)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._ring_vertex_count)
                GL.glBindVertexArray(0)
            elif self.mode == GizmoMode.SCALE:
                GL.glBindVertexArray(self._shaft_vao)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._shaft_vertex_count)
                GL.glBindVertexArray(0)
                # Scale end cube
                end_model = (
                    scale_matrix(SCALE_CUBE_SIZE * gizmo_scale, SCALE_CUBE_SIZE * gizmo_scale, SCALE_CUBE_SIZE * gizmo_scale)
                    @ translation_matrix(0.0, gizmo_scale, 0.0)
                    @ axis_rot
                    @ R_space
                    @ translation_matrix(*gl_pos)
                )
                GL.glUniformMatrix4fv(
                    GL.glGetUniformLocation(shader_program, "uModel"),
                    1, GL.GL_FALSE, end_model
                )
                GL.glBindVertexArray(self._cube_vao)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._cube_vertex_count)
                GL.glBindVertexArray(0)

        # 2. Render Planar & Screen handles in Translate mode
        if self.mode == GizmoMode.TRANSLATE:
            dir_x = self.get_axis_direction(GizmoAxis.X)
            dir_y = self.get_axis_direction(GizmoAxis.Y)
            dir_z = self.get_axis_direction(GizmoAxis.Z)

            plane_configs = [
                (GizmoAxis.XY, dir_x, dir_y, dir_z, GizmoAxis.XY),  # Blue
                (GizmoAxis.XZ, dir_x, dir_z, dir_y, GizmoAxis.XZ),  # Green
                (GizmoAxis.YZ, dir_y, dir_z, dir_x, GizmoAxis.YZ),  # Red
            ]

            for p_name, u_dir, v_dir, n_dir, c_key in plane_configs:
                p_avail = self.is_axis_available(p_name)
                p_active = p_avail and (self.active_axis == p_name)
                p_hover = p_avail and (self.hover_axis == p_name and not self._dragging)

                if not p_avail:
                    p_color = AXIS_DISABLED_COLOR
                    p_alpha = 0.25
                elif p_active or p_hover:
                    p_color = AXIS_HOVER_COLOR
                    p_alpha = 0.95
                else:
                    p_color = AXIS_COLORS[c_key]
                    p_alpha = 0.55

                M_plane = np.eye(4, dtype=np.float32)
                M_plane[0, :3] = u_dir * gizmo_scale
                M_plane[1, :3] = v_dir * gizmo_scale
                M_plane[2, :3] = n_dir * gizmo_scale
                M_plane[3, :3] = gl_pos

                GL.glUniformMatrix4fv(
                    GL.glGetUniformLocation(shader_program, "uModel"),
                    1, GL.GL_FALSE, M_plane
                )
                GL.glUniform3fv(
                    GL.glGetUniformLocation(shader_program, "uColor"),
                    1, p_color
                )
                GL.glUniform1f(
                    GL.glGetUniformLocation(shader_program, "uAlpha"),
                    p_alpha
                )
                GL.glBindVertexArray(self._plane_vao)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._plane_vertex_count)
                GL.glBindVertexArray(0)

            # Center Screen-Plane Handle (circle/ring facing camera)
            s_avail = self.is_axis_available(GizmoAxis.SCREEN)
            s_active = s_avail and (self.active_axis == GizmoAxis.SCREEN)
            s_hover = s_avail and (self.hover_axis == GizmoAxis.SCREEN and not self._dragging)

            if not s_avail:
                s_color = AXIS_DISABLED_COLOR
                s_alpha = 0.25
            elif s_active or s_hover:
                s_color = AXIS_HOVER_COLOR
                s_alpha = 1.0
            else:
                s_color = AXIS_COLORS[GizmoAxis.SCREEN]
                s_alpha = 0.85

            M_screen = np.eye(4, dtype=np.float32)
            M_screen[0, :3] = self.camera_right * gizmo_scale
            M_screen[1, :3] = self.camera_up * gizmo_scale
            M_screen[2, :3] = self.camera_forward * gizmo_scale
            M_screen[3, :3] = gl_pos

            GL.glUniformMatrix4fv(
                GL.glGetUniformLocation(shader_program, "uModel"),
                1, GL.GL_FALSE, M_screen
            )
            GL.glUniform3fv(
                GL.glGetUniformLocation(shader_program, "uColor"),
                1, s_color
            )
            GL.glUniform1f(
                GL.glGetUniformLocation(shader_program, "uAlpha"),
                s_alpha
            )
            GL.glBindVertexArray(self._screen_ring_vao)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._screen_ring_vertex_count)
            GL.glBindVertexArray(0)

        # 3. Render Uniform-scale center cube (Scale mode only)
        elif self.mode == GizmoMode.SCALE:
            center_available = self.is_axis_available(GizmoAxis.CENTER)
            c_active = center_available and (self.active_axis == GizmoAxis.CENTER)
            c_hover = center_available and (self.hover_axis == GizmoAxis.CENTER and not self._dragging)

            if not center_available:
                c_color = AXIS_DISABLED_COLOR
                c_alpha = 0.3
            elif c_active or c_hover:
                c_color = CENTER_HIGHLIGHT_COLOR
                c_alpha = 1.0
            else:
                c_color = CENTER_COLOR
                c_alpha = 0.9

            center_model = (
                scale_matrix(gizmo_scale * 0.13, gizmo_scale * 0.13, gizmo_scale * 0.13)
                @ translation_matrix(*gl_pos)
            )
            GL.glUniformMatrix4fv(
                GL.glGetUniformLocation(shader_program, "uModel"), 1, GL.GL_FALSE, center_model
            )
            GL.glUniform3fv(GL.glGetUniformLocation(shader_program, "uColor"), 1, c_color)
            GL.glUniform1f(GL.glGetUniformLocation(shader_program, "uAlpha"), c_alpha)
            GL.glBindVertexArray(self._cube_vao)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._cube_vertex_count)
            GL.glBindVertexArray(0)

        GL.glEnable(GL.GL_DEPTH_TEST)

    def hit_test(self, ray_origin, ray_dir, camera_pos) -> str:
        """Test if a ray hits any gizmo axis/handle. Returns axis name or GizmoAxis.NONE."""
        if not self.visible or self.mode == GizmoMode.NONE:
            return GizmoAxis.NONE

        gl_pos = self._get_gl_position()
        gizmo_scale = self.get_gizmo_scale(camera_pos, gl_pos)

        # 1. Rotate mode: ring plane test
        if self.mode == GizmoMode.ROTATE:
            return self._hit_test_rings(ray_origin, ray_dir, gl_pos, gizmo_scale)

        # 2. Scale mode center handle
        if self.mode == GizmoMode.SCALE and self.is_axis_available(GizmoAxis.CENTER):
            if self._ray_point_distance(ray_origin, ray_dir, gl_pos) < gizmo_scale * 0.18:
                return GizmoAxis.CENTER

        # 3. Translate mode: Screen center handle & Planar handles
        if self.mode == GizmoMode.TRANSLATE:
            # Screen handle (center circle)
            if self.is_axis_available(GizmoAxis.SCREEN):
                if self._ray_point_distance(ray_origin, ray_dir, gl_pos) < gizmo_scale * 0.16:
                    return GizmoAxis.SCREEN

            # Planar rectangle handles (XY, XZ, YZ)
            plane_hit = self._hit_test_planes(ray_origin, ray_dir, gl_pos, gizmo_scale)
            if plane_hit != GizmoAxis.NONE:
                return plane_hit

        # 4. Single-axis handles (Arrows / Scale shafts)
        axis_len = gizmo_scale * (TRANSLATE_LENGTH_SCALE if self.mode == GizmoMode.TRANSLATE else 1.0)
        threshold = gizmo_scale * 0.15

        best_axis = GizmoAxis.NONE
        best_dist = float('inf')

        for axis_name in [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]:
            if not self.is_axis_available(axis_name):
                continue
            axis_dir = self.get_axis_direction(axis_name)
            d = self._ray_line_distance(
                ray_origin, ray_dir,
                gl_pos, gl_pos + axis_dir * axis_len
            )
            if d < threshold and d < best_dist:
                best_dist = d
                best_axis = axis_name

        return best_axis

    def _hit_test_planes(self, ray_origin, ray_dir, gl_pos, gizmo_scale) -> str:
        """Hit test the 3 dual-axis planar handles (XY, XZ, YZ)."""
        dir_x = self.get_axis_direction(GizmoAxis.X)
        dir_y = self.get_axis_direction(GizmoAxis.Y)
        dir_z = self.get_axis_direction(GizmoAxis.Z)

        plane_configs = [
            (GizmoAxis.XY, dir_x, dir_y, dir_z),
            (GizmoAxis.XZ, dir_x, dir_z, dir_y),
            (GizmoAxis.YZ, dir_y, dir_z, dir_x),
        ]

        min_u, max_u = 0.22 * gizmo_scale, 0.58 * gizmo_scale
        min_v, max_v = 0.22 * gizmo_scale, 0.58 * gizmo_scale

        best_plane = GizmoAxis.NONE
        best_t = float('inf')

        for p_name, u_dir, v_dir, n_dir in plane_configs:
            if not self.is_axis_available(p_name):
                continue
            denom = float(np.dot(ray_dir, n_dir))
            if abs(denom) < 1e-6:
                continue
            t = float(np.dot(gl_pos - ray_origin, n_dir)) / denom
            if t <= 0.0 or t >= best_t:
                continue

            hit = ray_origin + ray_dir * t
            rel = hit - gl_pos
            du = float(np.dot(rel, u_dir))
            dv = float(np.dot(rel, v_dir))

            if min_u <= du <= max_u and min_v <= dv <= max_v:
                best_t = t
                best_plane = p_name

        return best_plane

    def _hit_test_rings(self, ray_origin, ray_dir, gl_pos, gizmo_scale) -> str:
        """Hit test the three rotation rings."""
        radius = gizmo_scale
        tol = gizmo_scale * 0.18
        best_axis = GizmoAxis.NONE
        best_dist = float('inf')

        for axis_name in [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]:
            if not self.is_axis_available(axis_name):
                continue
            normal = self.get_axis_direction(axis_name)
            denom = float(np.dot(ray_dir, normal))
            if abs(denom) < 1e-6:
                continue
            t = float(np.dot(gl_pos - ray_origin, normal)) / denom
            if t <= 0.0:
                continue
            hit = ray_origin + ray_dir * t
            ring_dist = abs(float(np.linalg.norm(hit - gl_pos)) - radius)
            if ring_dist < tol and ring_dist < best_dist:
                best_dist = ring_dist
                best_axis = axis_name

        return best_axis

    def begin_drag(self, axis: str, screen_pos: Tuple[float, float]):
        """Start dragging the gizmo along an axis or handle."""
        if axis == GizmoAxis.NONE or not self.is_axis_available(axis):
            return
        self.active_axis = axis
        self._dragging = True
        self._drag_start_pos = screen_pos
        self._drag_start_gl_pos = self._get_gl_position().copy()
        self._drag_start_value = {
            GizmoMode.TRANSLATE: self.position.copy(),
            GizmoMode.ROTATE: self.rotation.copy(),
            GizmoMode.SCALE: self.scale_val.copy(),
        }.get(self.mode)
        self._accumulated_angle = 0.0
        self._last_angle = None
        self._drag_plane_start_hit = None

    def update_drag(self, screen_pos: Tuple[float, float], view_matrix, proj_matrix, w, h, camera_pos) -> Optional[dict]:
        """Update the drag and return the new transform delta dict, or None."""
        if not self._dragging or self.active_axis == GizmoAxis.NONE:
            return None

        dx = screen_pos[0] - self._drag_start_pos[0]
        dy = screen_pos[1] - self._drag_start_pos[1]
        gl_pos = self._drag_start_gl_pos if self._drag_start_gl_pos is not None else self._get_gl_position()
        gizmo_scale = self.get_gizmo_scale(camera_pos, gl_pos)

        if self.mode == GizmoMode.TRANSLATE:
            # 1. Screen-plane Translation (Center circle handle)
            if self.active_axis == GizmoAxis.SCREEN:
                p0_screen = project_to_screen(gl_pos, view_matrix, proj_matrix, w, h)
                p_r = project_to_screen(gl_pos + self.camera_right * gizmo_scale, view_matrix, proj_matrix, w, h)
                p_u = project_to_screen(gl_pos + self.camera_up * gizmo_scale, view_matrix, proj_matrix, w, h)

                len_r = np.linalg.norm(p_r - p0_screen)
                len_u = np.linalg.norm(p_u - p0_screen)
                scale_r = gizmo_scale / max(len_r, 1.0)
                scale_u = gizmo_scale / max(len_u, 1.0)

                gl_delta = (dx * scale_r) * self.camera_right - (dy * scale_u) * self.camera_up
                s2_delta = (SOURCE2_TO_GL @ np.append(gl_delta, 0.0))[:3]

                if self.snapping_enabled and self.grid_step > 0.0:
                    s2_delta = np.array([round(val / self.grid_step) * self.grid_step for val in s2_delta], dtype=np.float32)

                new_pos = self._drag_start_value + s2_delta
                return {"position": new_pos.tolist()}

            # 2. Planar Translation (XY, XZ, YZ rectangles)
            elif self.active_axis in (GizmoAxis.XY, GizmoAxis.XZ, GizmoAxis.YZ):
                dir_x = self.get_axis_direction(GizmoAxis.X)
                dir_y = self.get_axis_direction(GizmoAxis.Y)
                dir_z = self.get_axis_direction(GizmoAxis.Z)
                s2_x = self.get_s2_axis_direction(GizmoAxis.X)
                s2_y = self.get_s2_axis_direction(GizmoAxis.Y)
                s2_z = self.get_s2_axis_direction(GizmoAxis.Z)

                configs = {
                    GizmoAxis.XY: (dir_x, dir_y, dir_z, s2_x, s2_y),
                    GizmoAxis.XZ: (dir_x, dir_z, dir_y, s2_x, s2_z),
                    GizmoAxis.YZ: (dir_y, dir_z, dir_x, s2_y, s2_z),
                }
                u_dir, v_dir, n_dir, s2_u, s2_v = configs[self.active_axis]

                # Raycast onto the plane
                r0_org, r0_dir = screen_to_world_ray(self._drag_start_pos[0], self._drag_start_pos[1], w, h, view_matrix, proj_matrix, camera_pos)
                r1_org, r1_dir = screen_to_world_ray(screen_pos[0], screen_pos[1], w, h, view_matrix, proj_matrix, camera_pos)

                denom0 = float(np.dot(r0_dir, n_dir))
                denom1 = float(np.dot(r1_dir, n_dir))

                if abs(denom0) > 1e-5 and abs(denom1) > 1e-5:
                    t0 = float(np.dot(gl_pos - r0_org, n_dir)) / denom0
                    t1 = float(np.dot(gl_pos - r1_org, n_dir)) / denom1
                    hit0 = r0_org + r0_dir * t0
                    hit1 = r1_org + r1_dir * t1
                    gl_delta = hit1 - hit0

                    delta_u = float(np.dot(gl_delta, u_dir))
                    delta_v = float(np.dot(gl_delta, v_dir))
                else:
                    # Fallback to screen projection
                    delta_u = dx * 0.05 * gizmo_scale
                    delta_v = -dy * 0.05 * gizmo_scale

                if self.snapping_enabled and self.grid_step > 0.0:
                    delta_u = round(delta_u / self.grid_step) * self.grid_step
                    delta_v = round(delta_v / self.grid_step) * self.grid_step

                new_pos = self._drag_start_value + delta_u * s2_u + delta_v * s2_v
                return {"position": new_pos.tolist()}

            # 3. Single-axis Translation (X, Y, Z arrows)
            else:
                axis_dir_GL = self.get_axis_direction(self.active_axis)

                p0_screen = project_to_screen(gl_pos, view_matrix, proj_matrix, w, h)
                p1_screen = project_to_screen(gl_pos + axis_dir_GL * gizmo_scale, view_matrix, proj_matrix, w, h)

                screen_dir = p1_screen - p0_screen
                screen_dir_len = np.linalg.norm(screen_dir)
                if screen_dir_len < 1.0:
                    return None

                screen_dir_norm = screen_dir / screen_dir_len
                mouse_delta = np.array([dx, dy], dtype=np.float32)
                drag_amount = float(np.dot(mouse_delta, screen_dir_norm))

                # Pixels to GL units
                gl_delta_val = drag_amount * (gizmo_scale / screen_dir_len)

                if self.snapping_enabled and self.grid_step > 0.0:
                    gl_delta_val = round(gl_delta_val / self.grid_step) * self.grid_step

                s2_axis_dir = self.get_s2_axis_direction(self.active_axis)
                new_pos = self._drag_start_value + gl_delta_val * s2_axis_dir

                return {"position": new_pos.tolist()}

        elif self.mode == GizmoMode.ROTATE:
            center_screen = project_to_screen(gl_pos, view_matrix, proj_matrix, w, h)

            x0 = self._drag_start_pos[0] - center_screen[0]
            y0 = self._drag_start_pos[1] - center_screen[1]
            x_curr = screen_pos[0] - center_screen[0]
            y_curr = screen_pos[1] - center_screen[1]

            len0 = math.hypot(x0, y0)
            len_curr = math.hypot(x_curr, y_curr)
            if len0 < 1e-3 or len_curr < 1e-3:
                return None

            curr_angle = math.atan2(y_curr, x_curr)
            if self._last_angle is None:
                self._last_angle = math.atan2(y0, x0)

            # Continuous multi-turn incremental delta
            step_angle = curr_angle - self._last_angle
            step_angle = (step_angle + math.pi) % (2.0 * math.pi) - math.pi
            self._accumulated_angle += step_angle
            self._last_angle = curr_angle

            # Determine rotation sign dynamically from screen-space
            axis_dir_GL = self.get_axis_direction(self.active_axis)
            view_dir = _normalize(gl_pos - camera_pos)
            facing = float(np.dot(axis_dir_GL, view_dir))
            sign = 1.0 if facing > 0 else -1.0

            total_angle_deg = math.degrees(self._accumulated_angle) * sign

            if self.snapping_enabled and self.rotation_step > 0.0:
                total_angle_deg = round(total_angle_deg / self.rotation_step) * self.rotation_step

            s2_axis_dir = self.get_s2_axis_direction(self.active_axis)
            R_delta = rotation_matrix_axis_angle(s2_axis_dir, total_angle_deg)
            R_start = rotation_matrix_euler(*self._drag_start_value)
            R_new = R_start @ R_delta

            _, new_rot, _ = decompose_trs(R_new)
            return {"rotation": new_rot}

        elif self.mode == GizmoMode.SCALE:
            if self.active_axis == GizmoAxis.CENTER:
                # Uniform scale based on distance from gizmo center
                center_screen = project_to_screen(gl_pos, view_matrix, proj_matrix, w, h)
                d0 = math.hypot(self._drag_start_pos[0] - center_screen[0], self._drag_start_pos[1] - center_screen[1])
                d1 = math.hypot(screen_pos[0] - center_screen[0], screen_pos[1] - center_screen[1])
                if d0 > 10.0:
                    factor = max(0.01, d1 / d0)
                else:
                    factor = max(0.01, 1.0 + (dx - dy) * 0.005)

                if self.snapping_enabled:
                    snap_step = 0.25 if self.grid_step >= 8.0 else 0.1
                    factor = max(snap_step, round(factor / snap_step) * snap_step)

                new_scale = self._drag_start_value * factor
                return {"scale": new_scale.tolist()}
            else:
                # Single-axis scale along screen direction
                axis_dir_GL = self.get_axis_direction(self.active_axis)
                p0_screen = project_to_screen(gl_pos, view_matrix, proj_matrix, w, h)
                p1_screen = project_to_screen(gl_pos + axis_dir_GL * gizmo_scale, view_matrix, proj_matrix, w, h)

                screen_dir = p1_screen - p0_screen
                screen_dir_len = np.linalg.norm(screen_dir)
                if screen_dir_len < 1.0:
                    return None

                screen_dir_norm = screen_dir / screen_dir_len
                mouse_delta = np.array([dx, dy], dtype=np.float32)
                drag_amount = float(np.dot(mouse_delta, screen_dir_norm))

                factor = max(0.01, 1.0 + drag_amount / screen_dir_len)

                axis_idx = [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z].index(self.active_axis)
                new_scale = self._drag_start_value.copy()

                if self.snapping_enabled:
                    snap_step = 0.25 if self.grid_step >= 8.0 else 0.1
                    raw_val = new_scale[axis_idx] * factor
                    new_scale[axis_idx] = max(snap_step, round(raw_val / snap_step) * snap_step)
                else:
                    new_scale[axis_idx] *= factor

                return {"scale": new_scale.tolist()}

        return None

    def end_drag(self):
        """End the current drag operation."""
        self._dragging = False
        self.active_axis = GizmoAxis.NONE
        self._drag_start_pos = None
        self._drag_start_gl_pos = None
        self._drag_start_value = None
        self._drag_plane_start_hit = None
        self._accumulated_angle = 0.0
        self._last_angle = None

    @property
    def is_dragging(self):
        return self._dragging

    @staticmethod
    def _cylinder_side(y0, y1, r0, r1, segments=12):
        """Build a solid tapered cylinder side wall between y0 and y1. Rendered as GL_TRIANGLES."""
        verts = []
        for i in range(segments):
            a1 = 2.0 * math.pi * i / segments
            a2 = 2.0 * math.pi * (i + 1) / segments
            p0a = [r0 * math.cos(a1), y0, r0 * math.sin(a1)]
            p0b = [r0 * math.cos(a2), y0, r0 * math.sin(a2)]
            p1a = [r1 * math.cos(a1), y1, r1 * math.sin(a1)]
            p1b = [r1 * math.cos(a2), y1, r1 * math.sin(a2)]
            if r0 > 1e-6:
                verts.extend([p0a, p0b, p1a])
            if r1 > 1e-6:
                verts.extend([p0b, p1b, p1a])
        return verts

    @staticmethod
    def _disc_cap(y, radius, segments=12):
        """Build a filled disc cap at height y. Rendered as GL_TRIANGLES."""
        verts = []
        center = [0.0, y, 0.0]
        for i in range(segments):
            a1 = 2.0 * math.pi * i / segments
            a2 = 2.0 * math.pi * (i + 1) / segments
            p1 = [radius * math.cos(a1), y, radius * math.sin(a1)]
            p2 = [radius * math.cos(a2), y, radius * math.sin(a2)]
            verts.extend([center, p1, p2])
        return verts

    @staticmethod
    def _build_arrow_vertices() -> np.ndarray:
        """Build a solid arrow (shaft cylinder + cone head) along +Y (unit length). Rendered as GL_TRIANGLES."""
        segments = 14
        shaft_radius = 0.035
        head_radius = 0.095
        shaft_top = 0.75
        tip_y = 1.15

        verts = []
        verts.extend(Gizmo._cylinder_side(0.0, shaft_top, shaft_radius, shaft_radius, segments))
        verts.extend(Gizmo._disc_cap(shaft_top, head_radius, segments))
        verts.extend(Gizmo._cylinder_side(shaft_top, tip_y, head_radius, 0.0, segments))
        return np.array(verts, dtype=np.float32)

    @staticmethod
    def _build_shaft_vertices() -> np.ndarray:
        """Build a solid thin cylinder shaft along +Y (unit length), no head. Rendered as GL_TRIANGLES."""
        segments = 12
        radius = 0.035
        return np.array(Gizmo._cylinder_side(0.0, 1.0, radius, radius, segments), dtype=np.float32)

    @staticmethod
    def _build_ring_vertices(segments=64) -> np.ndarray:
        """Build a solid 3D ring band on the XZ plane. Rendered as GL_TRIANGLES."""
        outer_r = 1.03
        inner_r = 0.95
        half_h = 0.018
        verts = []
        for i in range(segments):
            a1 = 2.0 * math.pi * i / segments
            a2 = 2.0 * math.pi * (i + 1) / segments
            cos1, sin1 = math.cos(a1), math.sin(a1)
            cos2, sin2 = math.cos(a2), math.sin(a2)

            # Top face (+Y)
            verts.extend([
                [inner_r * cos1,  half_h, inner_r * sin1],
                [outer_r * cos1,  half_h, outer_r * sin1],
                [outer_r * cos2,  half_h, outer_r * sin2],
                [inner_r * cos1,  half_h, inner_r * sin1],
                [outer_r * cos2,  half_h, outer_r * sin2],
                [inner_r * cos2,  half_h, inner_r * sin2],
            ])
            # Bottom face (-Y)
            verts.extend([
                [inner_r * cos1, -half_h, inner_r * sin1],
                [outer_r * cos2, -half_h, outer_r * sin2],
                [outer_r * cos1, -half_h, outer_r * sin1],
                [inner_r * cos1, -half_h, inner_r * sin1],
                [inner_r * cos2, -half_h, inner_r * sin2],
                [outer_r * cos2, -half_h, outer_r * sin2],
            ])
            # Outer wall
            verts.extend([
                [outer_r * cos1, -half_h, outer_r * sin1],
                [outer_r * cos2, -half_h, outer_r * sin2],
                [outer_r * cos2,  half_h, outer_r * sin2],
                [outer_r * cos1, -half_h, outer_r * sin1],
                [outer_r * cos2,  half_h, outer_r * sin2],
                [outer_r * cos1,  half_h, outer_r * sin1],
            ])
            # Inner wall
            verts.extend([
                [inner_r * cos1, -half_h, inner_r * sin1],
                [inner_r * cos2,  half_h, inner_r * sin2],
                [inner_r * cos2, -half_h, inner_r * sin2],
                [inner_r * cos1, -half_h, inner_r * sin1],
                [inner_r * cos1,  half_h, inner_r * sin1],
                [inner_r * cos2,  half_h, inner_r * sin2],
            ])
        return np.array(verts, dtype=np.float32)

    @staticmethod
    def _build_cube_vertices() -> np.ndarray:
        """Build unit cube geometry centered at origin. Rendered as GL_TRIANGLES."""
        h = 0.5
        faces = [
            [-h,-h, h], [ h,-h, h], [ h, h, h], [-h,-h, h], [ h, h, h], [-h, h, h],
            [-h,-h,-h], [-h, h,-h], [ h, h,-h], [-h,-h,-h], [ h, h,-h], [ h,-h,-h],
            [-h, h,-h], [-h, h, h], [ h, h, h], [-h, h,-h], [ h, h, h], [ h, h,-h],
            [-h,-h,-h], [ h,-h,-h], [ h,-h, h], [-h,-h,-h], [ h,-h, h], [-h,-h, h],
            [ h,-h,-h], [ h, h,-h], [ h, h, h], [ h,-h,-h], [ h, h, h], [ h,-h, h],
            [-h,-h,-h], [-h,-h, h], [-h, h, h], [-h,-h,-h], [-h, h, h], [-h, h,-h],
        ]
        return np.array(faces, dtype=np.float32)

    @staticmethod
    def _build_plane_vertices() -> np.ndarray:
        """Build a planar quad in local XY plane with double-sided triangles."""
        u0, u1 = 0.28, 0.55
        v0, v1 = 0.28, 0.55
        verts = [
            # Front side
            [u0, v0, 0.0], [u1, v0, 0.0], [u1, v1, 0.0],
            [u0, v0, 0.0], [u1, v1, 0.0], [u0, v1, 0.0],
            # Back side
            [u0, v0, 0.0], [u1, v1, 0.0], [u1, v0, 0.0],
            [u0, v0, 0.0], [u0, v1, 0.0], [u1, v1, 0.0],
        ]
        return np.array(verts, dtype=np.float32)

    @staticmethod
    def _build_screen_ring_vertices(segments=32) -> np.ndarray:
        """Build a flat circular ring facing camera in local XY plane."""
        outer_r = 0.14
        inner_r = 0.08
        verts = []
        for i in range(segments):
            a1 = 2.0 * math.pi * i / segments
            a2 = 2.0 * math.pi * (i + 1) / segments
            cos1, sin1 = math.cos(a1), math.sin(a1)
            cos2, sin2 = math.cos(a2), math.sin(a2)

            # Front side
            verts.extend([
                [inner_r * cos1, inner_r * sin1, 0.0],
                [outer_r * cos1, outer_r * sin1, 0.0],
                [outer_r * cos2, outer_r * sin2, 0.0],
                [inner_r * cos1, inner_r * sin1, 0.0],
                [outer_r * cos2, outer_r * sin2, 0.0],
                [inner_r * cos2, inner_r * sin2, 0.0],
            ])
            # Back side
            verts.extend([
                [inner_r * cos1, inner_r * sin1, 0.0],
                [outer_r * cos2, outer_r * sin2, 0.0],
                [outer_r * cos1, outer_r * sin1, 0.0],
                [inner_r * cos1, inner_r * sin1, 0.0],
                [inner_r * cos2, inner_r * sin2, 0.0],
                [outer_r * cos2, outer_r * sin2, 0.0],
            ])
        return np.array(verts, dtype=np.float32)

    @staticmethod
    def _axis_rotation_matrix(axis_name: str) -> np.ndarray:
        """Return a rotation matrix that maps +Y to the given axis direction."""
        m = np.eye(4, dtype=np.float32)
        if axis_name == GizmoAxis.X:
            # Rotate -90° around Z to point +Y → +X
            m[0, 0], m[0, 1] = 0.0, -1.0
            m[1, 0], m[1, 1] = 1.0, 0.0
        elif axis_name == GizmoAxis.Y:
            # Rotate +90° around X to point +Y → -Z (S2 Y in GL space)
            m[1, 1], m[1, 2] = 0.0, -1.0
            m[2, 1], m[2, 2] = 1.0, 0.0
        elif axis_name == GizmoAxis.Z:
            # Already pointing +Y (S2 Z in GL space)
            pass
        return m

    @staticmethod
    def _ray_point_distance(ray_origin, ray_dir, point) -> float:
        """Closest distance between a ray and a point."""
        denom = float(np.dot(ray_dir, ray_dir))
        if denom < 1e-10:
            return float('inf')
        t = max(0.0, float(np.dot(point - ray_origin, ray_dir)) / denom)
        closest = ray_origin + ray_dir * t
        return float(np.linalg.norm(closest - point))

    @staticmethod
    def _ray_line_distance(ray_origin, ray_dir, line_start, line_end) -> float:
        """Compute closest distance between a ray and a line segment."""
        u = ray_dir
        v = line_end - line_start
        w = ray_origin - line_start

        a = float(np.dot(u, u))
        b = float(np.dot(u, v))
        c = float(np.dot(v, v))
        d = float(np.dot(u, w))
        e = float(np.dot(v, w))

        denom = a * c - b * b
        if abs(denom) < 1e-10:
            return float('inf')

        s = (b * e - c * d) / denom
        t = (a * e - b * d) / denom
        t = max(0.0, min(1.0, t))
        s = max(0.0, s)

        closest_ray = ray_origin + u * s
        closest_line = line_start + v * t

        return float(np.linalg.norm(closest_ray - closest_line))


