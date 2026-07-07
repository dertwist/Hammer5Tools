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
    translation_matrix, scale_matrix, rotation_matrix_euler, _normalize, SOURCE2_TO_GL
)


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

# Map Source 2 axes directions to OpenGL space
# S2 is Z-up: S2 X -> GL X [1, 0, 0], S2 Y -> GL -Z [0, 0, -1], S2 Z -> GL Y [0, 1, 0]
AXIS_DIRECTIONS = {
    GizmoAxis.X: np.array([1.0, 0.0, 0.0], dtype=np.float32),
    GizmoAxis.Y: np.array([0.0, 0.0, -1.0], dtype=np.float32),
    GizmoAxis.Z: np.array([0.0, 1.0, 0.0], dtype=np.float32),
}


def project_to_screen(world_pos, view_matrix, proj_matrix, w, h):
    """Project a 3D GL world space point to 2D screen coordinates."""
    pos_h = np.append(world_pos, 1.0)
    clip_pos = proj_matrix @ view_matrix @ pos_h
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
        """Map S2 position to GL space."""
        pos_h = np.append(self.position, 1.0)
        gl_pos = SOURCE2_TO_GL @ pos_h
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

        GL.glDisable(GL.GL_DEPTH_TEST)
        # Force solid fill regardless of the viewport's shading mode (e.g.
        # Wireframe), so the gizmo never inherits a leftover GL_LINE polygon
        # mode from the model render pass.
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

        gl_pos = self._get_gl_position()
        dist = np.linalg.norm(camera_pos - gl_pos)
        gizmo_scale = max(dist * 0.06, 5.0)

        for axis_name in [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]:
            is_active = (axis_name == self.active_axis)
            is_hover = (axis_name == self.hover_axis and not self._dragging)

            color = AXIS_HIGHLIGHT_COLORS[axis_name] if (is_active or is_hover) else AXIS_COLORS[axis_name]

            # Model matrix
            model = translation_matrix(*gl_pos)
            axis_rot = self._axis_rotation_matrix(axis_name)
            model = model @ axis_rot @ scale_matrix(gizmo_scale, gizmo_scale, gizmo_scale)

            GL.glUniformMatrix4fv(
                GL.glGetUniformLocation(shader_program, "uModel"),
                1, GL.GL_FALSE, model
            )
            GL.glUniform3fv(
                GL.glGetUniformLocation(shader_program, "uColor"),
                1, color
            )
            GL.glUniform1f(
                GL.glGetUniformLocation(shader_program, "uAlpha"),
                1.0 if (is_active or is_hover) else 0.85
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
                # Cube at end
                end_model = translation_matrix(*gl_pos) @ axis_rot
                # Rotate maps +Y to axis direction, so offset is along local +Y (which points to axis direction)
                end_offset = np.array([0.0, 1.0, 0.0], dtype=np.float32) * gizmo_scale
                end_model = end_model @ translation_matrix(*end_offset)
                end_model = end_model @ scale_matrix(gizmo_scale * 0.08, gizmo_scale * 0.08, gizmo_scale * 0.08)
                GL.glUniformMatrix4fv(
                    GL.glGetUniformLocation(shader_program, "uModel"),
                    1, GL.GL_FALSE, end_model
                )
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
        threshold = gizmo_scale * 0.15  # Hit radius

        best_axis = GizmoAxis.NONE
        best_dist = float('inf')

        for axis_name in [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]:
            axis_dir = AXIS_DIRECTIONS[axis_name]
            d = self._ray_line_distance(
                ray_origin, ray_dir,
                gl_pos, gl_pos + axis_dir * gizmo_scale
            )
            if d < threshold and d < best_dist:
                best_dist = d
                best_axis = axis_name

        return best_axis

    def begin_drag(self, axis: str, screen_pos: Tuple[float, float]):
        """Start dragging the gizmo along an axis."""
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
            axis_dir_GL = AXIS_DIRECTIONS[self.active_axis]
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

            # S2 translation directly maps to S2 coordinate component
            new_pos = self._drag_start_value.copy()
            axis_idx = [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z].index(self.active_axis)
            new_pos[axis_idx] += gl_delta_val
            return {"position": new_pos.tolist()}

        elif self.mode == GizmoMode.ROTATE:
            # Rotate proportional to drag (1px = 0.5 degrees)
            angle = (dx - dy) * 0.5
            new_rot = self._drag_start_value.copy()
            axis_idx = [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z].index(self.active_axis)
            new_rot[axis_idx] += angle
            # Keep in [0, 360) range
            new_rot[axis_idx] = new_rot[axis_idx] % 360.0
            return {"rotation": new_rot.tolist()}

        elif self.mode == GizmoMode.SCALE:
            # Scale proportional to drag
            factor = 1.0 + (dx - dy) * 0.005
            factor = max(0.01, factor)
            new_scale = self._drag_start_value.copy()
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
            # Rotate -90° around X to point +Y → -Z (S2 Y in GL space)
            m[1, 1], m[1, 2] = 0.0, 1.0
            m[2, 1], m[2, 2] = -1.0, 0.0
        elif axis_name == GizmoAxis.Z:
            # Already pointing +Y (S2 Z in GL space)
            pass
        return m

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
