"""
Transform gizmo system for the 3D viewport.
Supports Translate (W), Rotate (E), and Scale (R) gizmo modes.
Manipulates Source 2 coordinates while rendering and interacting in GL space.
"""
import math
from enum import IntEnum
from typing import Optional, Tuple

import numpy as np

from src.editors.smartprop_editor.viewport_3d.camera import (
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
    CENTER = "center"   # uniform-scale handle at the axes' origin (Scale mode only)


# Axis colors (Red for X, Green for Y, Blue for Z)
AXIS_COLORS = {
    GizmoAxis.X: np.array([0.9, 0.2, 0.2], dtype=np.float32),
    GizmoAxis.Y: np.array([0.2, 0.8, 0.2], dtype=np.float32),
    GizmoAxis.Z: np.array([0.3, 0.4, 0.9], dtype=np.float32),
}

AXIS_HIGHLIGHT_COLORS = {
    GizmoAxis.X: np.array([1.0, 0.6, 0.2], dtype=np.float32),
    GizmoAxis.Y: np.array([0.6, 1.0, 0.2], dtype=np.float32),
    GizmoAxis.Z: np.array([0.2, 0.6, 1.0], dtype=np.float32),
}

# Hover/active handles use a single bright yellow across all axes — the standard
# Unity/Blender convention that reads instantly as "this is the handle you'll
# grab", regardless of the axis's own colour.
AXIS_HOVER_COLOR = np.array([1.0, 0.9, 0.2], dtype=np.float32)

# Grayscale color for an axis the gizmo cannot manipulate on the current
# object — i.e. the value is bound to a variable/expression, or the transform
# channel does not exist and can't be created (e.g. scale on an element with no
# model scale).  Such axes render dim/gray and ignore hover + clicks.
AXIS_DISABLED_COLOR = np.array([0.42, 0.42, 0.42], dtype=np.float32)

# Uniform-scale center handle (the small cube where the three scale axes meet).
# Dragging it scales every axis together.  Neutral by default, yellow on hover.
CENTER_COLOR = np.array([0.88, 0.88, 0.88], dtype=np.float32)
CENTER_HIGHLIGHT_COLOR = np.array([1.0, 0.85, 0.2], dtype=np.float32)

# Translate arrows are 1.5x longer than the base gizmo size.
TRANSLATE_LENGTH_SCALE = 1.5
# Size of the Scale-mode end cubes, as a fraction of the gizmo size (1.5x the
# original 0.08).
SCALE_CUBE_SIZE = 0.12

# Map Source 2 axes directions to OpenGL space
# S2 is Z-up: S2 X -> GL X [1, 0, 0], S2 Y -> GL -Z [0, 0, -1], S2 Z -> GL Y [0, 1, 0]
AXIS_DIRECTIONS = {
    GizmoAxis.X: np.array([1.0, 0.0, 0.0], dtype=np.float32),
    GizmoAxis.Y: np.array([0.0, 0.0, -1.0], dtype=np.float32),
    GizmoAxis.Z: np.array([0.0, 1.0, 0.0], dtype=np.float32),
}


def project_to_screen(world_pos, view_matrix, proj_matrix, w, h):
    """Project a 3D GL world space point to 2D screen coordinates.

    view_matrix / proj_matrix are row-vector style (pre-transposed for GL_FALSE
    upload), so the correct clip position is the row-vector chain
    ``pos @ view @ proj`` — not ``proj @ view @ pos``, which would transform by
    the transposes and land the point in the wrong place.
    """
    pos_h = np.append(world_pos, 1.0)
    clip_pos = pos_h @ view_matrix @ proj_matrix
    if abs(clip_pos[3]) > 1e-6:
        ndc = clip_pos[:3] / clip_pos[3]
    else:
        ndc = clip_pos[:3]
    sx = (ndc[0] + 1.0) * 0.5 * w
    sy = (1.0 - ndc[1]) * 0.5 * h
    return np.array([sx, sy], dtype=np.float32)


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
        self._drag_start_value = None

        # Per-mode, per-axis availability.  An axis is unavailable (rendered
        # gray and non-interactive) when its value is bound to a variable or
        # expression, or when the transform channel can't be manipulated for the
        # selected element.  Defaults to fully available.
        self.axis_availability = {
            GizmoMode.TRANSLATE: {GizmoAxis.X: True, GizmoAxis.Y: True, GizmoAxis.Z: True},
            GizmoMode.ROTATE:    {GizmoAxis.X: True, GizmoAxis.Y: True, GizmoAxis.Z: True},
            # Scale also has a CENTER handle for uniform (all-axis) scaling.
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
        self._initialized = False

        # Coordinate Space & Snapping
        self.coordinate_space = "World"  # "World" | "Local" | "Screen"
        self.snapping_enabled = False
        self.grid_step = 8.0
        self.rotation_step = 15.0

        # Camera vectors for Screen space
        self.camera_right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self.camera_forward = np.array([0.0, 0.0, -1.0], dtype=np.float32)

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
        else: # World
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
        else: # World
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
        """Update which axes can be manipulated.

        ``availability`` is keyed by :class:`GizmoMode` then :class:`GizmoAxis`,
        e.g. ``{GizmoMode.TRANSLATE: {"x": True, "y": False, "z": True}}``.
        Modes/axes not present keep their current value.
        """
        for mode, axes in availability.items():
            if mode in self.axis_availability and isinstance(axes, dict):
                for axis, enabled in axes.items():
                    if axis in self.axis_availability[mode]:
                        self.axis_availability[mode][axis] = bool(enabled)

    def is_axis_available(self, axis_name: str, mode: Optional[GizmoMode] = None) -> bool:
        """Return whether the given axis can be dragged in the given mode
        (defaults to the current mode)."""
        m = self.mode if mode is None else mode
        return self.axis_availability.get(m, {}).get(axis_name, True)

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

        # Plain shaft geometry (used by the Scale gizmo, no arrowhead)
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

        # Ring geometry
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

        # Scale cube geometry
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

        self._initialized = True

    def _get_gl_position(self):
        """Map S2 position to GL space.

        SOURCE2_TO_GL is written pre-transposed for GL_FALSE render chains, so a
        direct column-vector point transform must use its transpose to land on
        the same GL location the models are drawn at.
        """
        pos_h = np.append(self.position, 1.0)
        gl_pos = SOURCE2_TO_GL.T @ pos_h
        return gl_pos[:3]

    def render(self, shader_program, view_matrix, proj_matrix, camera_pos):
        """Render the gizmo. Must be called in GL context with gizmo shader active."""
        if not self.visible or not self._initialized or self.mode == GizmoMode.NONE:
            return

        from OpenGL import GL

        # Bind the gizmo program before touching its uniforms — otherwise
        # glGetUniformLocation resolves against the gizmo program while a
        # *different* program is still current, and glUniform* raises
        # GL_INVALID_OPERATION.  Upload view/projection once here.
        GL.glUseProgram(shader_program)
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(shader_program, "uView"), 1, GL.GL_FALSE, view_matrix
        )
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(shader_program, "uProjection"), 1, GL.GL_FALSE, proj_matrix
        )

        # Clear only the depth buffer so the gizmo gets a fresh depth range: it
        # always draws on top of the scene, yet with the depth test still enabled
        # its own parts occlude each other correctly (crossing rings / arrows read
        # as solid 3D instead of a flat draw-order stack).  The gizmo is the last
        # thing rendered each frame, so wiping depth here is safe.  Depth writes
        # must be on for glClear(DEPTH) to take effect, so enable them first.
        GL.glDepthMask(GL.GL_TRUE)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
        GL.glEnable(GL.GL_DEPTH_TEST)
        # Force solid fill regardless of the viewport's shading mode (e.g.
        # Wireframe), so the gizmo never inherits a leftover GL_LINE polygon
        # mode from the model render pass.
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

        gl_pos = self._get_gl_position()
        dist = np.linalg.norm(camera_pos - gl_pos)
        gizmo_scale = max(dist * 0.06, 5.0)

        # Build the space-orientation matrix that carries the gizmo handles from
        # World orientation into the active coordinate space.
        #
        # Each handle is first aimed by ``axis_rot`` at its *World* GL direction
        # (X -> +X, Y -> -Z, Z -> +Y — i.e. the rows of SOURCE2_TO_GL), NOT the
        # GL standard basis.  R_space must therefore map those World directions
        # onto the per-space GL directions returned by ``get_axis_direction`` so
        # every handle is rendered exactly where ``hit_test`` probes for it.
        #
        # With W = SOURCE2_TO_GL's 3x3 (rows = the World axis directions) and T
        # the target frame (rows = this space's GL axis dirs), the row-vector
        # requirement ``W @ R_space == T`` solves to ``R_space = W^-1 @ T``,
        # which is ``W.T @ T`` because W is orthonormal.
        #
        # The previous code filled R_space's rows straight from the space basis
        # (gl_x/gl_y/gl_z), ignoring axis_rot's Y->-Z / Z->+Y remap.  That drew
        # the Local/Screen Y and Z handles along the wrong directions, so they
        # rendered away from where hit_test looked and could never be grabbed.
        R_space = np.eye(4, dtype=np.float32)
        if self.coordinate_space in ("Local", "Screen"):
            T = np.array([
                self.get_axis_direction(GizmoAxis.X),
                self.get_axis_direction(GizmoAxis.Y),
                self.get_axis_direction(GizmoAxis.Z),
            ], dtype=np.float32)
            W = SOURCE2_TO_GL[:3, :3]
            R_space[:3, :3] = W.T @ T

        for axis_name in [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]:
            available = self.is_axis_available(axis_name)
            is_active = available and (axis_name == self.active_axis)
            is_hover = available and (axis_name == self.hover_axis and not self._dragging)

            if not available:
                # Grayscale = this axis can't be manipulated on this object.
                color = AXIS_DISABLED_COLOR
            elif is_active or is_hover:
                color = AXIS_HOVER_COLOR
            else:
                color = AXIS_COLORS[axis_name]

            # Model matrix.  These builders are row-vector style and the matrix is
            # uploaded with GL_FALSE, so the chain must be written scale-first /
            # translate-last (same convention as the model render chain).  Writing
            # it translate-first pushes the translation innermost, which scales and
            # rotates gl_pos itself and flings the gizmo far from the model — making
            # it impossible to click/drag.
            axis_rot = self._axis_rotation_matrix(axis_name)
            # Translate handles are 1.5x longer than the others.  axis_rot aims
            # local +Y at the axis, so stretching local Y lengthens the arrow
            # along its axis without thickening it (X/Z stay at gizmo_scale).
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
                # Shaft
                GL.glBindVertexArray(self._shaft_vao)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._shaft_vertex_count)
                GL.glBindVertexArray(0)
                # Cube at end.  Same scale-first / translate-last convention: shrink
                # the unit cube, push it out along local +Y by gizmo_scale (axis_rot
                # then aims local +Y at the axis direction), rotate, then translate
                # to the gizmo origin — placing it at the shaft tip.
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

        # Uniform-scale center cube at the origin (Scale mode only).  Drawn once,
        # after the axes, so it sits on top where the three shafts meet.
        if self.mode == GizmoMode.SCALE:
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
        """Test if a ray hits any gizmo axis. Returns axis name or GizmoAxis.NONE."""
        if not self.visible or self.mode == GizmoMode.NONE:
            return GizmoAxis.NONE

        gl_pos = self._get_gl_position()
        dist = np.linalg.norm(camera_pos - gl_pos)
        gizmo_scale = max(dist * 0.06, 5.0)

        # Rotate handles are rings perpendicular to their axis, so they need a
        # ring/plane hit test — probing a straight axis line (as Translate/Scale
        # do) would miss the ring everywhere it's actually drawn.
        if self.mode == GizmoMode.ROTATE:
            return self._hit_test_rings(ray_origin, ray_dir, gl_pos, gizmo_scale)

        # In Scale mode the center cube (uniform scale) wins near the origin —
        # tested first because the three axis shafts also start there.
        if self.mode == GizmoMode.SCALE and self.is_axis_available(GizmoAxis.CENTER):
            if self._ray_point_distance(ray_origin, ray_dir, gl_pos) < gizmo_scale * 0.16:
                return GizmoAxis.CENTER

        # Translate arrows are rendered 1.5x longer, so probe that far too.
        axis_len = gizmo_scale * (TRANSLATE_LENGTH_SCALE if self.mode == GizmoMode.TRANSLATE else 1.0)
        threshold = gizmo_scale * 0.15  # Hit radius

        best_axis = GizmoAxis.NONE
        best_dist = float('inf')

        for axis_name in [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]:
            # Unavailable (grayed) axes are inert — they can't be hovered or grabbed.
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

    def _hit_test_rings(self, ray_origin, ray_dir, gl_pos, gizmo_scale) -> str:
        """Hit test the three rotation rings.

        Each ring is the circle of radius ``gizmo_scale`` centred at ``gl_pos``
        lying in the plane whose normal is the axis direction.  For each ring we
        intersect the ray with that plane and measure how far the hit point is
        from the ring circle; the closest ring within tolerance wins.
        """
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
                continue  # ray parallel to the ring's plane — skip (edge-on)
            t = float(np.dot(gl_pos - ray_origin, normal)) / denom
            if t <= 0.0:
                continue  # plane is behind the camera
            hit = ray_origin + ray_dir * t
            ring_dist = abs(float(np.linalg.norm(hit - gl_pos)) - radius)
            if ring_dist < tol and ring_dist < best_dist:
                best_dist = ring_dist
                best_axis = axis_name

        return best_axis

    def begin_drag(self, axis: str, screen_pos: Tuple[float, float]):
        """Start dragging the gizmo along an axis."""
        # Defensive: never start a drag on a grayed-out (unavailable) axis.
        if axis == GizmoAxis.NONE or not self.is_axis_available(axis):
            return
        self.active_axis = axis
        self._dragging = True
        self._drag_start_pos = screen_pos
        self._drag_start_value = {
            GizmoMode.TRANSLATE: self.position.copy(),
            GizmoMode.ROTATE: self.rotation.copy(),
            GizmoMode.SCALE: self.scale_val.copy(),
        }.get(self.mode)

    def update_drag(self, screen_pos: Tuple[float, float], view_matrix, proj_matrix, w, h, camera_pos) -> Optional[dict]:
        """Update the drag and return the new transform delta, or None."""
        if not self._dragging or self.active_axis == GizmoAxis.NONE:
            return None

        dx = screen_pos[0] - self._drag_start_pos[0]
        dy = screen_pos[1] - self._drag_start_pos[1]

        if self.mode == GizmoMode.TRANSLATE:
            gl_pos = self._get_gl_position()
            axis_dir_GL = self.get_axis_direction(self.active_axis)
            dist = np.linalg.norm(camera_pos - gl_pos)
            gizmo_scale = max(dist * 0.06, 5.0)

            # Project endpoints of axis line onto screen
            p0_screen = project_to_screen(gl_pos, view_matrix, proj_matrix, w, h)
            p1_screen = project_to_screen(gl_pos + axis_dir_GL * gizmo_scale, view_matrix, proj_matrix, w, h)

            screen_dir = p1_screen - p0_screen
            screen_dir_len = np.linalg.norm(screen_dir)
            if screen_dir_len < 1.0:
                return None

            screen_dir_norm = screen_dir / screen_dir_len
            mouse_delta = np.array([dx, dy], dtype=np.float32)
            drag_amount = np.dot(mouse_delta, screen_dir_norm)

            # Pixels to GL units
            gl_delta_val = drag_amount * (gizmo_scale / screen_dir_len)

            # Move along the active axis in Source 2 space
            s2_axis_dir = self.get_s2_axis_direction(self.active_axis)
            new_pos = self._drag_start_value + gl_delta_val * s2_axis_dir

            # Snapping
            if self.snapping_enabled and self.grid_step > 0.0:
                new_pos = np.array([round(val / self.grid_step) * self.grid_step for val in new_pos], dtype=np.float32)

            return {"position": new_pos.tolist()}

        elif self.mode == GizmoMode.ROTATE:
            gl_pos = self._get_gl_position()
            center_screen = project_to_screen(gl_pos, view_matrix, proj_matrix, w, h)

            x0 = self._drag_start_pos[0] - center_screen[0]
            y0 = self._drag_start_pos[1] - center_screen[1]
            x1 = screen_pos[0] - center_screen[0]
            y1 = screen_pos[1] - center_screen[1]

            len0 = math.hypot(x0, y0)
            len1 = math.hypot(x1, y1)
            if len0 < 1e-3 or len1 < 1e-3:
                return None

            angle0 = math.atan2(y0, x0)
            angle1 = math.atan2(y1, x1)

            delta_angle = angle1 - angle0
            # Normalize to [-pi, pi] to avoid jump across boundary
            delta_angle = (delta_angle + math.pi) % (2 * math.pi) - math.pi
            angle_deg = math.degrees(delta_angle)

            # Determine rotation sign dynamically from screen-space
            axis_dir_GL = self.get_axis_direction(self.active_axis)
            view_dir = _normalize(gl_pos - camera_pos)
            facing = float(np.dot(axis_dir_GL, view_dir))
            sign = 1.0 if facing > 0 else -1.0

            total_angle_deg = angle_deg * sign

            if self.snapping_enabled and self.rotation_step > 0.0:
                total_angle_deg = round(total_angle_deg / self.rotation_step) * self.rotation_step

            # Build rotation delta in Source 2 space.  ``get_s2_axis_direction``
            # returns the drag axis already expressed in *world* S2 coordinates
            # for every space (Local -> the object's local axis rotated into
            # world; Screen -> the camera axis in world; World -> the world
            # axis), so R_delta is a world-frame rotation in all three cases.
            s2_axis_dir = self.get_s2_axis_direction(self.active_axis)
            R_delta = rotation_matrix_axis_angle(s2_axis_dir, total_angle_deg)

            # Composition.  In this row-vector chain a world-frame rotation is
            # applied *after* the object's current orientation, i.e. the delta
            # is projected onto the existing transform as ``R_start @ R_delta``.
            # This holds for World and Screen too — the earlier
            # ``R_delta @ R_start`` branch rotated about the axis in the
            # object's local frame, so World/Screen rotations drifted off the
            # picked axis as soon as the object already carried a rotation.
            R_start = rotation_matrix_euler(*self._drag_start_value)
            R_new = R_start @ R_delta

            # Decompose back to Euler
            _, new_rot, _ = decompose_trs(R_new)
            return {"rotation": new_rot}

        elif self.mode == GizmoMode.SCALE:
            # Scale proportional to drag
            factor = 1.0 + (dx - dy) * 0.005
            factor = max(0.01, factor)
            new_scale = self._drag_start_value.copy()
            if self.active_axis == GizmoAxis.CENTER:
                new_scale = new_scale * factor
            else:
                axis_idx = [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z].index(self.active_axis)
                new_scale[axis_idx] *= factor
            return {"scale": new_scale.tolist()}

        return None

    def end_drag(self):
        """End the current drag operation."""
        self._dragging = False
        self.active_axis = GizmoAxis.NONE
        self._drag_start_pos = None
        self._drag_start_value = None

    @property
    def is_dragging(self):
        return self._dragging

    @staticmethod
    def _cylinder_side(y0, y1, r0, r1, segments=12):
        """Build a solid tapered cylinder (frustum) side wall between y0 and y1. Rendered as GL_TRIANGLES."""
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
        segments = 12
        shaft_radius = 0.035
        head_radius = 0.09
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
        segments = 10
        radius = 0.035
        return np.array(Gizmo._cylinder_side(0.0, 1.0, radius, radius, segments), dtype=np.float32)

    @staticmethod
    def _build_ring_vertices(segments=48) -> np.ndarray:
        """Build a solid flat ring band on the XZ plane (unit outer radius). Rendered as GL_TRIANGLES."""
        outer_r = 1.0
        inner_r = 0.92
        verts = []
        for i in range(segments):
            a1 = 2.0 * math.pi * i / segments
            a2 = 2.0 * math.pi * (i + 1) / segments
            o1 = [outer_r * math.cos(a1), 0.0, outer_r * math.sin(a1)]
            o2 = [outer_r * math.cos(a2), 0.0, outer_r * math.sin(a2)]
            i1 = [inner_r * math.cos(a1), 0.0, inner_r * math.sin(a1)]
            i2 = [inner_r * math.cos(a2), 0.0, inner_r * math.sin(a2)]
            verts.extend([i1, o1, o2])
            verts.extend([i1, o2, i2])
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
    def _axis_rotation_matrix(axis_name: str) -> np.ndarray:
        """Return a rotation matrix that maps +Y to the given axis direction."""
        m = np.eye(4, dtype=np.float32)
        if axis_name == GizmoAxis.X:
            # Rotate -90° around Z to point +Y → +X
            m[0, 0], m[0, 1] = 0.0, -1.0
            m[1, 0], m[1, 1] = 1.0, 0.0
        elif axis_name == GizmoAxis.Y:
            # Rotate +90° around X to point +Y → -Z (S2 Y in GL space), matching
            # AXIS_DIRECTIONS[Y] = (0, 0, -1).  The opposite sign renders the Y
            # handle on +Z while hit_test probes the -Z segment, so the visible
            # handle can't be grabbed.
            m[1, 1], m[1, 2] = 0.0, -1.0
            m[2, 1], m[2, 2] = 1.0, 0.0
        elif axis_name == GizmoAxis.Z:
            # Already pointing +Y (S2 Z in GL space)
            pass
        return m

    @staticmethod
    def _ray_point_distance(ray_origin, ray_dir, point) -> float:
        """Closest distance between a ray and a point (for the center handle)."""
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
