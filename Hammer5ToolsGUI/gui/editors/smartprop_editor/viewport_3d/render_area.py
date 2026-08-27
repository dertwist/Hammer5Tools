"""
OpenGL-based 3D render area for the SmartProp Editor.
Handles grid rendering, 3D model rendering with textures, click-to-select color picking,
and W/E/R transform gizmo interactions.
"""
import math
import time
import numpy as np

from PySide6.QtCore import Qt, Signal, QPointF, QTimer
from PySide6.QtGui import QColor, QImage, QMouseEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication

from gui.editors.smartprop_editor.viewport_3d.camera import Camera, SOURCE2_TO_GL, translation_matrix, rotation_matrix_euler, scale_matrix, decompose_trs
from gui.editors.smartprop_editor.viewport_3d.gizmo import Gizmo, GizmoMode, GizmoAxis
from gui.editors.smartprop_editor.viewport_3d.mesh_cache import MeshCache
from gui.editors.smartprop_editor.viewport_3d import mesh_deform
from gui.editors.smartprop_editor.viewport_3d.crash_guard import gl_guard
from gui.editors.smartprop_editor.viewport_3d.shaders import (
    MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER,
    PICKING_VERTEX_SHADER, PICKING_FRAGMENT_SHADER,
    GRID_VERTEX_SHADER, GRID_FRAGMENT_SHADER,
    GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER,
    WIREFRAME_VERTEX_SHADER, WIREFRAME_FRAGMENT_SHADER,
    OUTLINE_VERTEX_SHADER, OUTLINE_FRAGMENT_SHADER,
    LOCATOR_VERTEX_SHADER, LOCATOR_FRAGMENT_SHADER,
    GROUP_BILLBOARD_VERTEX_SHADER, GROUP_BILLBOARD_FRAGMENT_SHADER,
)

from core.bridge import CoreBridge
from gui.styles import theme


def compile_shader(shader_type, source):
    from OpenGL import GL
    shader = GL.glCreateShader(shader_type)
    GL.glShaderSource(shader, source)
    GL.glCompileShader(shader)
    status = GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS)
    if not status:
        log = GL.glGetShaderInfoLog(shader).decode('utf-8')
        GL.glDeleteShader(shader)
        raise RuntimeError(f"Shader compilation failed: {log}")
    return shader


def link_program(vertex_source, fragment_source):
    from OpenGL import GL
    vs = compile_shader(GL.GL_VERTEX_SHADER, vertex_source)
    fs = compile_shader(GL.GL_FRAGMENT_SHADER, fragment_source)
    program = GL.glCreateProgram()
    GL.glAttachShader(program, vs)
    GL.glAttachShader(program, fs)
    GL.glLinkProgram(program)
    status = GL.glGetProgramiv(program, GL.GL_LINK_STATUS)
    if not status:
        log = GL.glGetProgramInfoLog(program).decode('utf-8')
        GL.glDeleteProgram(program)
        raise RuntimeError(f"Program linking failed: {log}")
    GL.glDeleteShader(vs)
    GL.glDeleteShader(fs)
    return program


def safe_normal_matrix(model_matrix):
    """Return the normal matrix (inverse-transpose of the 3x3) without ever raising.

    A model whose scale is 0 on an axis produces a singular matrix, and plain
    ``np.linalg.inv`` raises ``LinAlgError`` — which, in the render loop, crashes
    paintGL and makes the whole viewport fail to draw.  Degenerate scales are
    common here: ``m_vModelScale`` is often bound to an expression the viewport
    can't evaluate, so its components fall back to 0.  In that case the geometry
    is flattened/invisible and its normals don't matter, so fall back to identity
    and keep rendering.
    """
    m3 = np.asarray(model_matrix[:3, :3], dtype=np.float32)
    try:
        nm = np.linalg.inv(m3).T
    except np.linalg.LinAlgError:
        return np.eye(3, dtype=np.float32)
    if not np.all(np.isfinite(nm)):
        return np.eye(3, dtype=np.float32)
    return nm.astype(np.float32)


class SmartProp3DRenderArea(QOpenGLWidget):
    elementClicked = Signal(int)
    gizmoModeChanged = Signal(object)

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # MSAA format must be set before Qt creates the GL context.
        from gui.editors.smartprop_editor.viewport_3d.gl_settings import (
            make_viewport_surface_format, get_viewport_msaa_samples,
        )
        self._msaa_samples = get_viewport_msaa_samples()
        self.setFormat(make_viewport_surface_format(self._msaa_samples))

        # Camera & Interaction
        self.camera = Camera()
        self.gizmo = Gizmo()
        self.mesh_cache = MeshCache(self)
        self.mesh_cache.model_ready.connect(self.update)

        # Fly Camera State (Engine Game Camera on RMB hold)
        self.fly_speed = 500.0
        self._is_flying = False
        self._pressed_keys = set()
        self._fly_timer = QTimer(self)
        self._fly_timer.setInterval(16)
        self._fly_timer.timeout.connect(self._update_fly_movement)
        self._fly_last_time = None

        # Prevent GL callback failures from unwinding into Qt's paint loop.
        self._gl_disabled = False
        self._gl_crash_count = 0

        self._last_mouse_pos = QPointF()
        self._action = None  # 'orbit' | 'pan'
        self._selected_id = 0

        # Gizmo scale source: per-axis, uniform, or unavailable.
        self._scale_source = None

        self.shading_mode = "textured"  # "textured" | "solid" | "wireframe"
        self.translucency_enabled = True  # when False, BLEND materials draw opaque
        self.coordinate_space = "World"
        self.snapping_enabled = False
        self.grid_step = 8.0
        self.rotation_step = 15.0
        self.display_groups = True
        self.show_widgets = True
        self.isolated_element_id = None
        self.isolated_element_name = ""
        # Follow selection instead of the Ctrl+H isolation target.
        self.dynamic_isolation = False
        self.current_transform_text = None

        self._model_infos = {}  # id -> info dict (primary entry per element id)
        self._model_instances = []  # list of all individual model instances to render
        self._path_infos = []  # list of PlaceOnPath curve and control point data

        # Evaluated preview widgets, rebuilt from document variable defaults.
        self._widget_infos = []  # list of resolved widget dicts to draw

        self._warn_unsupported = set()     # unsupported element class short-names

        # Prevent recursive .vsmart expansion and repeated cycle logs.
        self._nested_vsmart_stack = []
        self._warned_cyclic_smartprops = set()

        # Picking state
        self._perform_pick_flag = False
        self._pick_pos = None

        # Shader Programs & GPU Buffers
        self._model_program = 0
        self._picking_program = 0
        self._grid_program = 0
        self._gizmo_program = 0
        self._wireframe_program = 0
        self._outline_program = 0
        self._locator_program = 0
        self._billboard_program = 0

        self._grid_vao = 0
        self._grid_vbo = 0
        self._box_vao = 0
        self._box_vbo = 0
        self._billboard_vao = 0
        self._billboard_vbo = 0
        self._group_texture = 0
        self._element_texture = 0
        self._fs_vao = 0  # empty VAO for the fullscreen-triangle outline pass

        # Preview-widget GPU resources
        self._locator_vao = 0
        self._locator_vbo = 0
        self._locator_vertex_count = 0

        self._rotator_ring_vao = 0
        self._rotator_ring_vbo = 0
        self._rotator_ring_vertex_count = 0
        self._rotator_needle_vao = 0
        self._rotator_tab_vao = 0

        self._sizer_arrow_vao = 0
        self._sizer_arrow_vbo = 0
        self._sizer_arrow_vertex_count = 0

        self._pickone_sq_frame_vao = 0
        self._pickone_sq_fill_vao = 0
        self._pickone_dia_frame_vao = 0
        self._pickone_dia_fill_vao = 0

        self._circle_vao = 0
        self._circle_count = 0
        self._circle_fill_vao = 0
        self._circle_fill_count = 0

        self._dynamic_vao = 0
        self._dynamic_vbo = 0

        self.outline_enabled = True
        self.outline_color = (0.15, 0.95, 1.0)  # cyan, matching the app's selection accent
        self.outline_thickness = 3.0            # logical pixels (scaled by device ratio)

        # Outline mask uses a texture target; picking uses a renderbuffer.
        self._mask_fbo = 0
        self._mask_color_tex = 0
        self._mask_depth_rbo = 0
        self._mask_fbo_w = 0
        self._mask_fbo_h = 0

        # Picking uses a non-MSAA FBO because antialiasing corrupts color IDs.
        self._pick_fbo = 0
        self._pick_color_rbo = 0
        self._pick_depth_rbo = 0
        self._pick_fbo_w = 0
        self._pick_fbo_h = 0

    @gl_guard("init")
    def initializeGL(self):
        from OpenGL import GL

        # Reset FBO and picking handles on context recreation
        self._mask_fbo = 0
        self._mask_color_tex = 0
        self._mask_depth_rbo = 0
        self._mask_fbo_w = 0
        self._mask_fbo_h = 0

        self._pick_fbo = 0
        self._pick_color_rbo = 0
        self._pick_depth_rbo = 0
        self._pick_fbo_w = 0
        self._pick_fbo_h = 0

        # Invalidate mesh cache so stale GPU handles from previous context are re-uploaded
        if hasattr(self, "mesh_cache") and self.mesh_cache is not None:
            self.mesh_cache.invalidate_gpu_cache()

        # Debug info
        renderer = GL.glGetString(GL.GL_RENDERER).decode('utf-8')
        samples = GL.glGetIntegerv(GL.GL_SAMPLES)
        print(f"[SmartProp3D] OpenGL Context Initialized: {renderer} (MSAA x{samples})")

        GL.glEnable(GL.GL_DEPTH_TEST)
        # Only enable multisampling when the surface actually provides samples;
        # this keeps the state honest on drivers that report a 0-sample buffer.
        if samples and samples > 1:
            GL.glEnable(GL.GL_MULTISAMPLE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        self._model_program = link_program(MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER)
        self._picking_program = link_program(PICKING_VERTEX_SHADER, PICKING_FRAGMENT_SHADER)
        self._grid_program = link_program(GRID_VERTEX_SHADER, GRID_FRAGMENT_SHADER)
        self._gizmo_program = link_program(GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER)
        self._wireframe_program = link_program(WIREFRAME_VERTEX_SHADER, WIREFRAME_FRAGMENT_SHADER)
        self._outline_program = link_program(OUTLINE_VERTEX_SHADER, OUTLINE_FRAGMENT_SHADER)
        self._locator_program = link_program(LOCATOR_VERTEX_SHADER, LOCATOR_FRAGMENT_SHADER)
        self._billboard_program = link_program(
            GROUP_BILLBOARD_VERTEX_SHADER,
            GROUP_BILLBOARD_FRAGMENT_SHADER,
        )

        # Empty VAO required by core profile to issue the attribute-less
        # fullscreen-triangle draw in the selection outline pass.
        self._fs_vao = GL.glGenVertexArrays(1)

        # Dynamic reusable VAO/VBO for immediate streaming lines/polygons
        self._dynamic_vao = GL.glGenVertexArrays(1)
        self._dynamic_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._dynamic_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._dynamic_vbo)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)

        self._init_editor_billboard_geometry()

        size = 25000.0
        grid_vertices = np.array([
            [-size, 0.0, -size],
            [ size, 0.0, -size],
            [ size, 0.0,  size],
            [-size, 0.0,  size],
        ], dtype=np.float32)

        self._grid_vao = GL.glGenVertexArrays(1)
        self._grid_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._grid_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._grid_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, grid_vertices.nbytes, grid_vertices, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)

        h = 0.5
        box_lines = np.array([
            [-h, -h, -h], [ h, -h, -h],
            [ h, -h, -h], [ h, -h,  h],
            [ h, -h,  h], [-h, -h,  h],
            [-h, -h,  h], [-h, -h, -h],
            [-h,  h, -h], [ h,  h, -h],
            [ h,  h, -h], [ h,  h,  h],
            [ h,  h,  h], [-h,  h,  h],
            [-h,  h,  h], [-h,  h, -h],
            [-h, -h, -h], [-h,  h, -h],
            [ h, -h, -h], [ h,  h, -h],
            [ h, -h,  h], [ h,  h,  h],
            [-h, -h,  h], [-h,  h,  h],
        ], dtype=np.float32)

        self._box_vao = GL.glGenVertexArrays(1)
        self._box_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._box_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._box_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, box_lines.nbytes, box_lines, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)

        # The two horizontal ground axes (Source X red / Source Y green) are drawn
        # directly by the grid shader as infinite lines that fade with distance,
        # Blender-style.  The vertical Source Z (up) axis is intentionally omitted.

        self.gizmo.init_geometry()

        # Initialize preview-widget geometry (locators / rotators / pickone).
        self._init_widget_geometry()

    @gl_guard("event")
    def resizeGL(self, w, h):
        if w <= 0 or h <= 0:
            return
        from OpenGL import GL
        GL.glViewport(0, 0, w, h)
        self.camera.aspect = w / h if h > 0 else 1.0

    @gl_guard("paint")
    def paintGL(self):
        if self.width() <= 0 or self.height() <= 0:
            return
        from OpenGL import GL

        # Explicitly restore expected OpenGL states that QPainter might have left dirty:
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glDepthFunc(GL.GL_LESS)

        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        
        # Reset bindings to avoid any QPainter leftovers interfering
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)

        # Perform picking pass first if flagged
        if self._perform_pick_flag:
            self._do_picking_pass()
            self._perform_pick_flag = False

        # Normal Render Pass
        from gui.styles import theme as _theme
        GL.glClearColor(*_theme.gl_clear_color(), 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Upload meshes ready on CPU and free ones the hierarchy dropped
        self.mesh_cache.upload_pending()
        self.mesh_cache.release_unloaded()

        # Matrices
        view = self.camera.view_matrix
        proj = self.camera.projection_matrix
        cam_pos = self.camera.position
        self._sync_gizmo_settings()

        # 1. Render Grid Floor (depth writes disabled so the transparent
        # areas of the floor never occlude models/gizmo drawn afterward)
        GL.glDepthMask(GL.GL_FALSE)
        # Force solid fill — otherwise a leftover GL_LINE polygon mode from
        # the previous frame's Wireframe-shaded model pass would turn the
        # grid quad into an outline instead of the shader-drawn overlay.
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        GL.glUseProgram(self._grid_program)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._grid_program, "uView"), 1, GL.GL_FALSE, view)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._grid_program, "uProjection"), 1, GL.GL_FALSE, proj)
        GL.glUniform1f(GL.glGetUniformLocation(self._grid_program, "uGridStep"), float(self.grid_step))
        GL.glBindVertexArray(self._grid_vao)
        GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, 4)
        GL.glBindVertexArray(0)
        GL.glDepthMask(GL.GL_TRUE)

        self._render_scene_models(view, proj, cam_pos, picking=False)

        # 2b. Selection outline overlay.  Composited here — after the models but
        # before the gizmo — because the gizmo clears the depth buffer and draws
        # on top; running the outline first keeps it from being wiped or occluded.
        if self.outline_enabled and self._selected_id in self._model_infos:
            self._render_selection_outline(view, proj, cam_pos)

        # 2c. Render preview widgets (locators / rotators / pickone handles).
        # Drawn after models/outline and before the gizmo (which clears depth).
        if self.show_widgets and self._widget_infos:
            self._render_widgets(view, proj)

        # 2d. Render path curves and control point markers for PlaceOnPath elements.
        if self._path_infos:
            self._render_paths(view, proj)

        self.gizmo.render(self._gizmo_program, view, proj, cam_pos)

        # 4. Draw 2D HUD/Overlay
        self._render_2d_overlay()

    def _render_2d_overlay(self):
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return
        from PySide6.QtGui import QPainter, QPen, QColor, QFont
        from PySide6.QtCore import Qt
        
        painter = QPainter()
        if not painter.begin(self):
            return
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 1. Rectangle highlight around the viewport if in isolate mode (slighter, 2px)
            if self.isolated_element_id is not None:
                pen = QPen(theme.qcolor("#b3d096"), 2) # isolated view highlight color
                painter.setPen(pen)
                painter.drawRect(1, 1, w - 2, h - 2)
                
            # 2. Build the HUD text lines in the left bottom corner
            hud_lines = []
            
            # Line: Isolate Mode details
            if self.isolated_element_id is not None:
                isolated_name = getattr(self, "isolated_element_name", None) or "Unknown Object"
                hud_lines.append(f"Isolate Mode: {isolated_name}")
                
            # Line: Object count
            rendered_pool = self._model_instances if self._model_instances else list(self._model_infos.values())
            num_models = sum(1 for info in rendered_pool if not info.get("is_editor_marker"))
            hud_lines.append(f"Objects: {num_models}")
            
            # Line: Active transformation details
            transform_text = getattr(self, "current_transform_text", None)
            if transform_text:
                hud_lines.append(transform_text)

            # Lines: preview-accuracy warnings (amber).  Marked with a leading "⚠" so
            # the text-colour pass below can style them.
            unsupported = getattr(self, "_warn_unsupported", None)
            if unsupported:
                names = ", ".join(sorted(unsupported))
                hud_lines.append(f"⚠ Not fully previewed: {names}")

            # 3. Paint the HUD text lines in the bottom-left corner with sharp stylesheet style
            if hud_lines:
                font = QFont("Segoe UI", 9)
                painter.setFont(font)
                
                margin_left = 15
                margin_bottom = 15
                line_height = 20
                box_padding = 10
                
                longest_line_width = 0
                for line in hud_lines:
                    metrics = painter.fontMetrics()
                    longest_line_width = max(longest_line_width, metrics.horizontalAdvance(line))
                    
                box_width = longest_line_width + (box_padding * 2) + 10
                box_height = (len(hud_lines) * line_height) + (box_padding * 2) - 5
                
                box_x = margin_left
                box_y = h - margin_bottom - box_height
                
                # Sharp stylesheet box styling:
                # - Draw sharp background box (dark gray, #303030 with 220 alpha)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(48, 48, 48, 220))
                painter.drawRect(box_x, box_y, box_width, box_height)
                
                # - Draw sharp 1px border (#535353)
                painter.setPen(QPen(QColor(83, 83, 83), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(box_x, box_y, box_width, box_height)
                
                # - Draw a clean 3px left accent line
                accent_color = theme.qcolor("#b3d096") if self.isolated_element_id is not None else QColor(0, 120, 215)
                painter.setPen(Qt.NoPen)
                painter.setBrush(accent_color)
                painter.drawRect(box_x, box_y, 3, box_height)
                
                for i, line in enumerate(hud_lines):
                    if line.startswith("⚠"):
                        painter.setPen(QColor(255, 196, 61)) # amber for preview warnings
                    elif line.startswith("Isolate Mode:"):
                        painter.setPen(theme.qcolor("#b3d096")) # isolated view color
                    elif line.startswith("Translate:") or line.startswith("Rotate:") or line.startswith("Scale:") or line.startswith("Scaling"):
                        painter.setPen(QColor(255, 165, 0)) # orange for active transforms
                    else:
                        painter.setPen(QColor(240, 240, 240)) # default white
                        
                    text_y = box_y + box_padding + (i * line_height) + painter.fontMetrics().ascent()
                    painter.drawText(box_x + box_padding + 6, text_y, line)
        finally:
            painter.end()

    def _init_editor_billboard_geometry(self):
        """Upload hierarchy marker icons and their camera-facing unit quad."""
        from OpenGL import GL
        from gui.common import gui_assets_dir

        vertices = np.array([
            [-0.5, -0.5, 0.0, 0.0],
            [ 0.5, -0.5, 1.0, 0.0],
            [ 0.5,  0.5, 1.0, 1.0],
            [-0.5, -0.5, 0.0, 0.0],
            [ 0.5,  0.5, 1.0, 1.0],
            [-0.5,  0.5, 0.0, 1.0],
        ], dtype=np.float32)

        self._billboard_vao = GL.glGenVertexArrays(1)
        self._billboard_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._billboard_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._billboard_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, 16, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, GL.GL_FALSE, 16, GL.ctypes.c_void_p(8))
        GL.glEnableVertexAttribArray(1)
        GL.glBindVertexArray(0)

        self._group_texture = self._upload_billboard_texture(
            gui_assets_dir("icons", "tools", "hammer", "selection_mode_groups.png")
        )
        self._element_texture = self._upload_billboard_texture(
            gui_assets_dir("icons", "tools", "hammer", "entity_tool_icon_activated.png")
        )

    @staticmethod
    def _upload_billboard_texture(icon_path):
        """Upload one bundled RGBA editor icon and return its texture id."""
        from OpenGL import GL

        image = QImage(icon_path).convertToFormat(QImage.Format_RGBA8888).mirrored(False, True)
        if image.isNull():
            raise RuntimeError(f"Unable to load SmartProp hierarchy icon: {icon_path}")
        pixels = np.frombuffer(image.constBits(), dtype=np.uint8, count=image.sizeInBytes())

        texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, image.width(), image.height(), 0,
            GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, pixels,
        )
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        return texture

    def _draw_editor_billboard(self, view, proj, source_position, texture, pick_color=None):
        """Draw a camera-facing hierarchy icon."""
        from OpenGL import GL

        source = np.array([*source_position, 1.0], dtype=np.float32)
        center = (SOURCE2_TO_GL.T @ source)[:3]
        distance = float(np.linalg.norm(self.camera.position - center))
        size = max(distance * 0.035, 8.0)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        GL.glUseProgram(self._billboard_program)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._billboard_program, "uView"), 1, GL.GL_FALSE, view)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._billboard_program, "uProjection"), 1, GL.GL_FALSE, proj)
        GL.glUniform3fv(GL.glGetUniformLocation(self._billboard_program, "uCenter"), 1, center)
        GL.glUniform3fv(
            GL.glGetUniformLocation(self._billboard_program, "uCameraRight"),
            1,
            np.asarray(self.camera.right_vector, dtype=np.float32),
        )
        GL.glUniform3fv(
            GL.glGetUniformLocation(self._billboard_program, "uCameraUp"),
            1,
            np.asarray(self.camera.up_vector, dtype=np.float32),
        )
        GL.glUniform1f(GL.glGetUniformLocation(self._billboard_program, "uSize"), size)
        GL.glUniform1i(GL.glGetUniformLocation(self._billboard_program, "uPicking"), pick_color is not None)
        GL.glUniform3f(
            GL.glGetUniformLocation(self._billboard_program, "uPickColor"),
            *(pick_color or (0.0, 0.0, 0.0)),
        )
        GL.glActiveTexture(GL.GL_TEXTURE0)
        bound = False
        if texture:
            try:
                if GL.glIsTexture(texture):
                    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
                    bound = True
            except Exception:
                pass
        if not bound:
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glUniform1i(GL.glGetUniformLocation(self._billboard_program, "uIcon"), 0)
        GL.glBindVertexArray(self._billboard_vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)
        GL.glBindVertexArray(0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    def _render_scene_models(self, view, proj, cam_pos, picking=False, mask_id=None):
        from OpenGL import GL

        # The mask renders only the selected element for an x-ray outline.
        use_pick = picking or (mask_id is not None)

        # Resolve context addon from opened file
        context_addon = None
        if self.document and getattr(self.document, "opened_file", None):
            import re
            opened_path = self.document.opened_file.replace('\\', '/')
            addon_match = re.search(r'/csgo_addons/([^/]+)/', opened_path, re.IGNORECASE)
            if addon_match:
                context_addon = addon_match.group(1)

        if use_pick:
            GL.glUseProgram(self._picking_program)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._picking_program, "uView"), 1, GL.GL_FALSE, view)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._picking_program, "uProjection"), 1, GL.GL_FALSE, proj)
        else:
            # Configure polygon mode based on shading style
            if self.shading_mode == "wireframe":
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
            else:
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

            GL.glUseProgram(self._model_program)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._model_program, "uView"), 1, GL.GL_FALSE, view)
            GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._model_program, "uProjection"), 1, GL.GL_FALSE, proj)
            GL.glUniform3fv(GL.glGetUniformLocation(self._model_program, "uCameraPos"), 1, cam_pos)

        def set_pick_color(eid):
            """Upload the flat colour for the picking/mask shader.

            Mask mode: white for the outlined element, black otherwise.
            Picking mode: the element id encoded across the RGB channels.
            """
            if mask_id is not None:
                c = 1.0 if eid == mask_id else 0.0
                GL.glUniform3f(GL.glGetUniformLocation(self._picking_program, "uPickColor"), c, c, c)
            else:
                r = (eid & 0xFF) / 255.0
                g = ((eid >> 8) & 0xFF) / 255.0
                b = ((eid >> 16) & 0xFF) / 255.0
                GL.glUniform3f(GL.glGetUniformLocation(self._picking_program, "uPickColor"), r, g, b)

        # Translucent (BLEND) submeshes are collected here and drawn in a second
        # pass after all opaque geometry, sorted back-to-front with depth writes
        # off so they composite correctly.
        transparent_items = []
        marker_items = []

        rendered_pool = self._model_instances if self._model_instances else list(self._model_infos.values())
        for info in rendered_pool:
            eid = info.get("id", 0)
            if mask_id is not None and eid != mask_id:
                continue

            pos = info.get("position", [0.0, 0.0, 0.0])
            rot = info.get("rotation", [0.0, 0.0, 0.0])
            scale = info.get("scale", [1.0, 1.0, 1.0])
            model_path = info.get("path", "")

            # Matrices are pre-transposed for GL_FALSE; do not transpose SOURCE2_TO_GL.
            if "world_matrix" in info:
                model_matrix = info["world_matrix"] @ SOURCE2_TO_GL
            else:
                model_matrix = (
                    scale_matrix(*scale)
                    @ rotation_matrix_euler(*rot)
                    @ translation_matrix(*pos)
                    @ SOURCE2_TO_GL
                )

            is_editor_marker = info.get("is_editor_marker", False)
            if is_editor_marker:
                marker_type = info.get("marker_type", "element")
                if marker_type == "group" and not self.display_groups:
                    continue
                # Draw hierarchy markers together after every model pass. This makes
                # them true editor overlays: meshes never occlude the icon, and
                # the picking pass resolves the visible icon before geometry.
                marker_items.append((eid, pos, marker_type))
                continue

            deformer = info.get("deformer")
            if deformer is not None and "world_matrix" in info:
                # Bend deformers are reported as unsupported and use the plain mesh.
                self._warn_unsupported.add("BendDeformer")
                gpu_mesh = self.mesh_cache.get_gpu_mesh(model_path)
            else:
                gpu_mesh = self.mesh_cache.get_gpu_mesh(model_path)

            if use_pick:
                # Flat id colour (picking) or white/black silhouette (mask mode).
                set_pick_color(eid)

                if gpu_mesh:
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._picking_program, "uModel"), 1, GL.GL_FALSE, model_matrix)
                    GL.glBindVertexArray(gpu_mesh.vao)
                    GL.glDrawElements(GL.GL_TRIANGLES, gpu_mesh.index_count, GL.GL_UNSIGNED_INT, None)
                else:
                    self._draw_box_geometry(model_matrix, is_picking=True)
            else:
                is_selected = (eid == self._selected_id)

                if gpu_mesh:
                    # Normal matrix is transpose of inverse of the 3x3 model matrix
                    # (crash-safe: degenerate/zero scales fall back to identity).
                    norm_mat = safe_normal_matrix(model_matrix)
                    textured = (self.shading_mode == "textured")

                    for sm in gpu_mesh.submeshes:
                        if textured and sm.material.is_transparent and self.translucency_enabled:
                            # Defer translucent submeshes to the sorted second pass.
                            dist = float(np.linalg.norm(cam_pos - model_matrix[3, :3]))
                            transparent_items.append(
                                (dist, gpu_mesh, sm, model_matrix, norm_mat, is_selected)
                            )
                        else:
                            # Translucency off (or non-textured shading): draw BLEND
                            # materials as solid so they don't render see-through.
                            force_opaque = sm.material.is_transparent and not self.translucency_enabled
                            self._draw_material_submesh(
                                gpu_mesh, sm, model_matrix, norm_mat, is_selected, textured,
                                force_opaque=force_opaque,
                            )
                else:
                    # Queue model decompile / load if not already started
                    self.mesh_cache.request_model(model_path, context_addon)

                    # Draw fallback wireframe bounding box placeholder
                    GL.glUseProgram(self._wireframe_program)
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._wireframe_program, "uView"), 1, GL.GL_FALSE, view)
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._wireframe_program, "uProjection"), 1, GL.GL_FALSE, proj)

                    box_color = np.array([0.0, 0.85, 0.85] if is_selected else [0.4, 0.6, 0.9], dtype=np.float32)
                    GL.glUniform3fv(GL.glGetUniformLocation(self._wireframe_program, "uColor"), 1, box_color)

                    self._draw_box_geometry(model_matrix, is_picking=False)

                    GL.glUseProgram(self._model_program)

        # Blend translucent submeshes far-to-near, rendering back faces first.
        if not use_pick and transparent_items:
            transparent_items.sort(key=lambda t: t[0], reverse=True)
            GL.glUseProgram(self._model_program)
            GL.glEnable(GL.GL_CULL_FACE)
            GL.glFrontFace(GL.GL_CCW)
            GL.glDepthMask(GL.GL_FALSE)
            for _dist, gm, sm, mm, nm, sel in transparent_items:
                GL.glCullFace(GL.GL_FRONT)   # keep back faces (far side) first
                self._draw_material_submesh(gm, sm, mm, nm, sel, True)
                GL.glCullFace(GL.GL_BACK)    # then front faces (near side) over them
                self._draw_material_submesh(gm, sm, mm, nm, sel, True)
            GL.glDepthMask(GL.GL_TRUE)
            GL.glDisable(GL.GL_CULL_FACE)

        # Hierarchy icons ignore scene depth without writing it.
        if marker_items:
            depth_test_was_enabled = bool(GL.glIsEnabled(GL.GL_DEPTH_TEST))
            depth_writes_were_enabled = bool(GL.glGetBooleanv(GL.GL_DEPTH_WRITEMASK))
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glDepthMask(GL.GL_FALSE)
            for eid, pos, marker_type in marker_items:
                if mask_id is not None:
                    pick_color = (1.0, 1.0, 1.0)
                elif picking:
                    pick_color = (
                        (eid & 0xFF) / 255.0,
                        ((eid >> 8) & 0xFF) / 255.0,
                        ((eid >> 16) & 0xFF) / 255.0,
                    )
                else:
                    pick_color = None
                texture = self._group_texture if marker_type == "group" else self._element_texture
                self._draw_editor_billboard(view, proj, pos, texture, pick_color)

            GL.glDepthMask(GL.GL_TRUE if depth_writes_were_enabled else GL.GL_FALSE)
            if depth_test_was_enabled:
                GL.glEnable(GL.GL_DEPTH_TEST)
            else:
                GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glUseProgram(self._picking_program if use_pick else self._model_program)

        # Restore standard polygon fill mode
        if not use_pick:
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

    def _draw_box_geometry(self, model_matrix, is_picking=False):
        """Draw a ~50-unit placeholder box at the model's transform."""
        from OpenGL import GL

        # The unit box geometry spans [-0.5, 0.5]; scale it to a 50-inch cube in
        # the model's local Source space.  In this row-vector chain, local scale
        # is pre-multiplied so it is applied before the model transform.
        box_size = 50.0
        gl_box_matrix = scale_matrix(box_size, box_size, box_size) @ model_matrix

        program = self._picking_program if is_picking else self._wireframe_program
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(program, "uModel"), 1, GL.GL_FALSE, gl_box_matrix)

        GL.glBindVertexArray(self._box_vao)
        if is_picking:
            # Render wireframe box corners / outline or lines
            GL.glDrawArrays(GL.GL_LINES, 0, 24)
        else:
            GL.glDrawArrays(GL.GL_LINES, 0, 24)
        GL.glBindVertexArray(0)

    # Material binding / submesh drawing
    _ALPHA_MODE_CODE = {"OPAQUE": 0, "MASK": 1, "BLEND": 2}

    def _bind_material(self, program, material, textured, force_opaque=False):
        """Upload one GPUMaterial's uniforms and bind its textures (units 0-4).

        In non-textured (solid / wireframe) shading the maps are ignored and the
        surface renders as a neutral, opaque grey so geometry stays readable.
        ``force_opaque`` renders a BLEND material as OPAQUE (used when the viewport
        translucency toggle is off).
        """
        from OpenGL import GL

        def loc(name):
            return GL.glGetUniformLocation(program, name)

        # Flat fallback colour used when no base texture is bound.
        GL.glUniform3f(loc("uBaseColor"), 0.7, 0.7, 0.7)

        if not textured:
            GL.glUniform4f(loc("uBaseColorFactor"), 1.0, 1.0, 1.0, 1.0)
            GL.glUniform1f(loc("uRoughness"), 0.6)
            GL.glUniform1f(loc("uMetallic"), 0.0)
            GL.glUniform3f(loc("uEmissiveFactor"), 0.0, 0.0, 0.0)
            GL.glUniform1i(loc("uAlphaMode"), 0)
            GL.glUniform1f(loc("uAlphaCutoff"), 0.5)
            GL.glUniform2f(loc("uUvScale"), 1.0, 1.0)
            GL.glUniform2f(loc("uUvOffset"), 0.0, 0.0)
            GL.glUniform2f(loc("uUvCenter"), 0.5, 0.5)
            GL.glUniform1f(loc("uUvRotation"), 0.0)
            for name in ("uHasBaseTex", "uHasNormalTex", "uHasMRTex", "uHasAO", "uHasEmissive"):
                GL.glUniform1i(loc(name), 0)
            return

        bcf = material.base_color_factor
        GL.glUniform4f(loc("uBaseColorFactor"), bcf[0], bcf[1], bcf[2], bcf[3])
        GL.glUniform1f(loc("uRoughness"), float(material.roughness_factor))
        GL.glUniform1f(loc("uMetallic"), float(material.metallic_factor))
        ef = material.emissive_factor
        GL.glUniform3f(loc("uEmissiveFactor"), ef[0], ef[1], ef[2])
        alpha_mode = 0 if force_opaque else self._ALPHA_MODE_CODE.get(material.alpha_mode, 0)
        GL.glUniform1i(loc("uAlphaMode"), alpha_mode)
        GL.glUniform1f(loc("uAlphaCutoff"), float(material.alpha_cutoff))

        uv_scale = getattr(material, "uv_scale", (1.0, 1.0))
        uv_offset = getattr(material, "uv_offset", (0.0, 0.0))
        uv_center = getattr(material, "uv_center", (0.5, 0.5))
        uv_rot = float(getattr(material, "uv_rotation", 0.0))
        GL.glUniform2f(loc("uUvScale"), float(uv_scale[0]), float(uv_scale[1]))
        GL.glUniform2f(loc("uUvOffset"), float(uv_offset[0]), float(uv_offset[1]))
        GL.glUniform2f(loc("uUvCenter"), float(uv_center[0]), float(uv_center[1]))
        GL.glUniform1f(loc("uUvRotation"), uv_rot)

        def bind_tex(unit, tex, sampler_name, has_name):
            GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
            bound = False
            if tex and textured:
                try:
                    if GL.glIsTexture(tex):
                        GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
                        bound = True
                except Exception:
                    pass
            if not bound:
                GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            GL.glUniform1i(loc(sampler_name), unit)
            GL.glUniform1i(loc(has_name), 1 if bound else 0)

        bind_tex(0, material.base_tex, "uBaseTex", "uHasBaseTex")
        bind_tex(1, material.normal_tex, "uNormalTex", "uHasNormalTex")
        bind_tex(2, material.mr_tex, "uMRTex", "uHasMRTex")
        bind_tex(3, material.ao_tex, "uAOTex", "uHasAO")
        bind_tex(4, material.emissive_tex, "uEmissiveTex", "uHasEmissive")
        GL.glActiveTexture(GL.GL_TEXTURE0)

    def _draw_material_submesh(self, gpu_mesh, submesh, model_matrix, norm_mat, is_selected, textured, force_opaque=False):
        """Draw one material submesh with the model shader."""
        from OpenGL import GL
        prog = self._model_program

        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uModel"), 1, GL.GL_FALSE, model_matrix)
        GL.glUniformMatrix3fv(GL.glGetUniformLocation(prog, "uNormalMatrix"), 1, GL.GL_FALSE, norm_mat)
        # Selection feedback is a post-process outline (see _render_selection_outline),
        # not a per-fragment fill, so ``is_selected`` no longer feeds the model shader.

        self._bind_material(prog, submesh.material, textured, force_opaque=force_opaque)

        GL.glBindVertexArray(gpu_mesh.vao)
        # index_offset is an element count; glDrawElements wants a byte offset
        # into the element buffer (uint32 indices -> 4 bytes each).
        GL.glDrawElements(
            GL.GL_TRIANGLES, submesh.index_count, GL.GL_UNSIGNED_INT,
            GL.ctypes.c_void_p(submesh.index_offset * 4),
        )
        GL.glBindVertexArray(0)

    def _ensure_pick_fbo(self, w, h):
        """Create (or resize) the single-sample picking framebuffer to w x h."""
        from OpenGL import GL

        if self._pick_fbo and self._pick_fbo_w == w and self._pick_fbo_h == h:
            return

        # Drop the old attachments/FBO before making new ones.
        if self._pick_fbo:
            GL.glDeleteFramebuffers(1, [self._pick_fbo])
            GL.glDeleteRenderbuffers(2, [self._pick_color_rbo, self._pick_depth_rbo])

        self._pick_color_rbo = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self._pick_color_rbo)
        GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_RGBA8, w, h)

        self._pick_depth_rbo = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self._pick_depth_rbo)
        GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_DEPTH_COMPONENT24, w, h)

        self._pick_fbo = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._pick_fbo)
        GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                     GL.GL_RENDERBUFFER, self._pick_color_rbo)
        GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT,
                                     GL.GL_RENDERBUFFER, self._pick_depth_rbo)

        self._pick_fbo_w = w
        self._pick_fbo_h = h
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.defaultFramebufferObject())

    def _do_picking_pass(self):
        """Render color-coded IDs into the private single-sample FBO and read
        the pixel under the cursor.  Keeping picking off the multisampled default
        framebuffer avoids the glReadPixels GL_INVALID_OPERATION and stops MSAA
        from blending neighbouring IDs at silhouette edges."""
        from OpenGL import GL

        if self._pick_pos is None:
            return

        # Work in device pixels so picking lines up with the HiDPI framebuffer.
        dpr = self.devicePixelRatioF()
        fb_w = max(1, int(round(self.width() * dpr)))
        fb_h = max(1, int(round(self.height() * dpr)))
        self._ensure_pick_fbo(fb_w, fb_h)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._pick_fbo)
        GL.glViewport(0, 0, fb_w, fb_h)
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glDisable(GL.GL_BLEND)

        view = self.camera.view_matrix
        proj = self.camera.projection_matrix
        cam_pos = self.camera.position

        self._render_scene_models(view, proj, cam_pos, picking=True)

        # Read color under cursor (device pixels, origin bottom-left).
        gl_x = int(self._pick_pos.x() * dpr)
        gl_y = int(fb_h - self._pick_pos.y() * dpr)
        gl_x = min(max(gl_x, 0), fb_w - 1)
        gl_y = min(max(gl_y, 0), fb_h - 1)

        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
        pixel = GL.glReadPixels(gl_x, gl_y, 1, 1, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)

        # Restore the default (visible) framebuffer + blending for the main pass.
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.defaultFramebufferObject())
        GL.glViewport(0, 0, fb_w, fb_h)
        GL.glEnable(GL.GL_BLEND)

        # Decode ID.  PyOpenGL may hand back the single pixel as (1,1,4), (4,) or
        # raw bytes depending on version — flatten so the RGB bytes are stable.
        flat = np.frombuffer(bytes(pixel), dtype=np.uint8) if isinstance(pixel, (bytes, bytearray)) \
            else np.asarray(pixel, dtype=np.uint8).reshape(-1)
        r, g, b = int(flat[0]), int(flat[1]), int(flat[2])
        clicked_id = r | (g << 8) | (b << 16)

        if clicked_id != 0 and clicked_id in self._model_infos:
            self.elementClicked.emit(clicked_id)
            self.highlight_element(clicked_id)
        else:
            self.elementClicked.emit(0)
            self.highlight_element(0)

    # Selection outline
    def _ensure_mask_fbo(self, w, h):
        """Create (or resize) the single-sample selection-mask framebuffer.

        Colour is a sampleable texture (the outline pass reads it); depth is a
        renderbuffer required for FBO completeness (the mask pass renders with
        depth testing off, for the x-ray silhouette -- see _render_selection_outline).
        """
        from OpenGL import GL

        if self._mask_fbo and self._mask_fbo_w == w and self._mask_fbo_h == h:
            return

        if self._mask_fbo:
            GL.glDeleteFramebuffers(1, [self._mask_fbo])
            GL.glDeleteTextures(1, [self._mask_color_tex])
            GL.glDeleteRenderbuffers(1, [self._mask_depth_rbo])

        self._mask_color_tex = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._mask_color_tex)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, w, h, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        # Linear filtering softens the outline's edge when the pass samples between
        # texels; clamp keeps the border ring from wrapping across the screen.
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

        self._mask_depth_rbo = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self._mask_depth_rbo)
        GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_DEPTH_COMPONENT24, w, h)

        self._mask_fbo = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._mask_fbo)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                  GL.GL_TEXTURE_2D, self._mask_color_tex, 0)
        GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT,
                                     GL.GL_RENDERBUFFER, self._mask_depth_rbo)

        self._mask_fbo_w = w
        self._mask_fbo_h = h
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.defaultFramebufferObject())

    def _render_selection_outline(self, view, proj, cam_pos):
        """Draw an x-ray silhouette outline around the currently selected mesh.

        Two passes: (1) render the selected element's full silhouette (depth test
        off, so nearer geometry can't hide any of it) as white-on-black into the
        mask FBO; (2) a fullscreen pass dilates that mask and paints the ring just
        outside the silhouette over the visible scene -- visible through occluders.

        Loaded meshes and group billboards are outlined here. Not-yet-loaded model
        placeholders keep their own wireframe-box selection markers.
        """
        from OpenGL import GL

        sel = self._model_infos.get(self._selected_id)
        if not sel:
            return
        if not sel.get("is_editor_marker") and self.mesh_cache.get_gpu_mesh(sel.get("path", "")) is None:
            return

        # Work in device pixels so the mask lines up with the HiDPI framebuffer.
        dpr = self.devicePixelRatioF()
        fb_w = max(1, int(round(self.width() * dpr)))
        fb_h = max(1, int(round(self.height() * dpr)))
        self._ensure_mask_fbo(fb_w, fb_h)

        # Pass 1: silhouette mask
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._mask_fbo)
        GL.glViewport(0, 0, fb_w, fb_h)
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glDisable(GL.GL_BLEND)
        # Depth test off: the mask should capture the selected mesh's full
        # silhouette, not just the parts visible past whatever else is in front
        # of it -- that's what makes the outline read as x-ray.
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_FALSE)
        self._render_scene_models(view, proj, cam_pos, mask_id=self._selected_id)

        # ---- Pass 2: composite outline over the visible framebuffer ----------
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.defaultFramebufferObject())
        GL.glViewport(0, 0, fb_w, fb_h)
        GL.glEnable(GL.GL_BLEND)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_FALSE)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

        prog = self._outline_program
        GL.glUseProgram(prog)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._mask_color_tex)
        GL.glUniform1i(GL.glGetUniformLocation(prog, "uMask"), 0)
        GL.glUniform2f(GL.glGetUniformLocation(prog, "uTexel"), 1.0 / fb_w, 1.0 / fb_h)
        GL.glUniform1f(GL.glGetUniformLocation(prog, "uThickness"),
                       max(1.0, float(self.outline_thickness) * dpr))
        oc = self.outline_color
        GL.glUniform3f(GL.glGetUniformLocation(prog, "uOutlineColor"), oc[0], oc[1], oc[2])

        GL.glBindVertexArray(self._fs_vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)
        GL.glBindVertexArray(0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        # Restore depth writes/testing for the gizmo pass that follows.
        GL.glDepthMask(GL.GL_TRUE)
        GL.glEnable(GL.GL_DEPTH_TEST)

    # Camera fitting
    def _compute_bounds(self, infos):
        """Return the GL-space AABB (min, max, has_bounds) enclosing ``infos``.

        ``infos`` is an iterable of element info dicts (a subset of
        ``self._model_infos.values()``).  Meshes use their transformed AABB;
        groups and not-yet-loaded models fall back to a small box at their origin.
        """
        bbox_min = np.array([float('inf'), float('inf'), float('inf')], dtype=np.float32)
        bbox_max = np.array([float('-inf'), float('-inf'), float('-inf')], dtype=np.float32)

        has_bounds = False
        for info in infos:
            pos = info.get("position", [0.0, 0.0, 0.0])
            rot = info.get("rotation", [0.0, 0.0, 0.0])
            scale = info.get("scale", [1.0, 1.0, 1.0])

            model_matrix = (
                scale_matrix(*scale)
                @ rotation_matrix_euler(*rot)
                @ translation_matrix(*pos)
                @ SOURCE2_TO_GL
            )
            is_editor_marker = info.get("is_editor_marker", False)
            if is_editor_marker:
                gl_pos = (SOURCE2_TO_GL.T @ np.append(np.array(pos, dtype=np.float32), 1.0))[:3]
                bbox_min = np.minimum(bbox_min, gl_pos - 10.0)
                bbox_max = np.maximum(bbox_max, gl_pos + 10.0)
            else:
                gpu_mesh = self.mesh_cache.get_gpu_mesh(info.get("path", ""))
                if gpu_mesh is not None:
                    # Transform the mesh's Source-space AABB corners into GL space.
                    lo, hi = gpu_mesh.bbox_min, gpu_mesh.bbox_max
                    corners = np.array([[x, y, z, 1.0]
                                        for x in (lo[0], hi[0])
                                        for y in (lo[1], hi[1])
                                        for z in (lo[2], hi[2])], dtype=np.float32)
                    gl_corners = (corners @ model_matrix)[:, :3]
                    bbox_min = np.minimum(bbox_min, gl_corners.min(axis=0))
                    bbox_max = np.maximum(bbox_max, gl_corners.max(axis=0))
                else:
                    # Mesh not loaded yet — frame the placeholder box at the origin.
                    # This is a direct column-vector point transform, so the conversion
                    # matrix must be transposed here (opposite of the GL_FALSE render
                    # chain above, which uses SOURCE2_TO_GL as-is).
                    gl_pos = (SOURCE2_TO_GL.T @ np.append(np.array(pos, dtype=np.float32), 1.0))[:3]
                    bbox_min = np.minimum(bbox_min, gl_pos - 50.0)
                    bbox_max = np.maximum(bbox_max, gl_pos + 50.0)
            has_bounds = True

        return bbox_min, bbox_max, has_bounds

    @gl_guard("event")
    def fit_view(self):
        """Zoom and position camera to fit all models in scene."""
        pool = self._model_instances if self._model_instances else list(self._model_infos.values())
        if not pool:
            return
        bbox_min, bbox_max, has_bounds = self._compute_bounds(pool)
        if has_bounds:
            self.camera.fit_to_bounds(bbox_min, bbox_max)
            self.update()

    def frame_selection(self):
        """Frame the camera on the current selection (F key).

        Fits the selected element if one is selected; otherwise frames the whole
        scene, matching the behaviour users expect from Blender/Hammer.
        """
        pool = self._model_instances if self._model_instances else list(self._model_infos.values())
        matching = [inst for inst in pool if inst.get("id") == self._selected_id]
        if not matching and self._selected_id in self._model_infos:
            matching = [self._model_infos[self._selected_id]]
        if matching:
            bbox_min, bbox_max, has_bounds = self._compute_bounds(matching)
            if has_bounds:
                self.camera.fit_to_bounds(bbox_min, bbox_max)
                self.update()
                return
        # Nothing selected (or selection has no bounds) — frame everything.
        self.fit_view()

    def _find_tree_item(self, parent_item, eid):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            data = child.data(0, Qt.UserRole)
            if isinstance(data, dict) and data.get("m_nElementID") == eid:
                return child
            found = self._find_tree_item(child, eid)
            if found is not None:
                return found
        return None

    def _collect_subtree_ids(self, item):
        """IDs of ``item`` and every descendant — the set a viewport isolation
        should keep visible."""
        ids = set()
        data = item.data(0, Qt.UserRole)
        if isinstance(data, dict) and data.get("m_nElementID"):
            ids.add(data["m_nElementID"])
        for i in range(item.childCount()):
            ids.update(self._collect_subtree_ids(item.child(i)))
        return ids

    # Element classes the viewport can place/preview.  Anything else that carries
    # geometry or replicates it (PlaceMultiple, BendDeformer, ModifyState, …) is
    # only partially previewed, so it's surfaced as a HUD warning.
    _SUPPORTED_ELEMENT_CLASSES = frozenset({
        "CSmartPropElement_Model",
        "CSmartPropElement_ModelEntity",
        "CSmartPropElement_PropPhysics",
        "CSmartPropElement_PropDynamic",
        "CSmartPropElement_Group",
        "CSmartPropElement_PickOne",
        "CSmartPropElement_SmartProp",
        "CSmartPropElement_FitOnLine",
        "CSmartPropElement_PlaceOnPath",
        "CSmartPropElement_ModifyState",
    })

    @gl_guard("event")
    def update_viewport(self):
        """Rebuild the scene models list from the current document tree."""
        self._model_infos.clear()
        self._model_instances = []
        self._path_infos = []
        self._widget_infos = []
        self._warn_unsupported = set()

        if not self.document:
            self.update()
            return

        tree_widget = None
        if hasattr(self.document, 'ui') and hasattr(self.document.ui, 'tree_hierarchy_widget'):
            tree_widget = self.document.ui.tree_hierarchy_widget
        if tree_widget is None:
            self.update()
            return

        if self.isolated_element_id is not None:
            isolated_item = self._find_tree_item(tree_widget.invisibleRootItem(), self.isolated_element_id)
            if isolated_item is None:
                self.isolated_element_id = None
                self.isolated_element_name = ""
            else:
                self.isolated_element_name = isolated_item.text(0)

        models_info = self._apply_core_evaluation(tree_widget.invisibleRootItem())

        if self.isolated_element_id is not None:
            subtree_ids = self._collect_subtree_ids(isolated_item)
            models_info = [info for info in models_info if info.get("id") in subtree_ids]

        self._model_instances = list(models_info)
        for info in models_info:
            eid = info.get("id", 0)
            if eid > 0 and eid not in self._model_infos:
                self._model_infos[eid] = info

        # Unload any cached models the hierarchy no longer references so the
        # viewport's memory footprint follows the tree (GPU frees happen on the
        # next paint, inside the GL context).
        #
        # Not while isolated: the visible set is then a small slice of the
        # hierarchy, not a truthful "what the document still uses", so pruning
        # against it would free every hidden model and force a full reload the
        # moment the isolation moves to another element or clears — which is
        # every selection change in dynamic isolation mode.  Whatever really was
        # removed from the tree is reclaimed by the next unisolated rebuild.
        if self.isolated_element_id is None:
            referenced_paths = {
                info.get("path", "") for info in self._model_instances if info.get("path")
            }
            self.mesh_cache.prune(referenced_paths)

        # Sync selection gizmo transform if selection exists
        if self._selected_id in self._model_infos:
            sel = self._model_infos[self._selected_id]
            self.gizmo.set_transform(sel["position"], sel["rotation"], sel["scale"])
            self._apply_gizmo_availability(sel.get("data"))
        else:
            self.gizmo.hide()

        self.update()

    def _apply_core_evaluation(self, root_item):
        """Build the scene exclusively from authoritative Core placements."""
        if not hasattr(self.document, "build_smartprop_document"):
            self._warn_unsupported.add("Hammer5Tools Core document snapshot unavailable")
            return []

        try:
            document = self.document.build_smartprop_document()
            result = CoreBridge.instance().evaluate_smartprop(
                document,
                nested_documents=self._collect_nested_smartprops(document),
            )
        except Exception as error:
            self._warn_unsupported.add(f"Core evaluation unavailable: {error}")
            return []

        if result.diagnostics:
            self._warn_unsupported.update(result.diagnostics)
            return []

        data_by_id = {}
        parent_id_by_id = {}

        def collect_data(item, ancestor_id=0):
            for index in range(item.childCount()):
                child = item.child(index)
                data = child.data(0, Qt.UserRole)
                child_id = data.get("m_nElementID", 0) if isinstance(data, dict) else 0
                if isinstance(data, dict):
                    data_by_id[child_id] = data
                if child_id:
                    parent_id_by_id[child_id] = ancestor_id
                collect_data(child, child_id or ancestor_id)

        collect_data(root_item)

        evaluated = []
        for model in result.models:
            world_matrix = np.asarray(model.transform, dtype=np.float32).reshape((4, 4))
            world_pos, world_rot, world_scale = decompose_trs(world_matrix)
            evaluated.append({
                "id": model.element_id,
                "path": model.model_name,
                "position": world_pos,
                "rotation": world_rot,
                "scale": world_scale,
                "world_matrix": world_matrix,
                "data": data_by_id.get(model.element_id, {}),
                "is_editor_marker": False,
                "material_group": model.material_group,
                "tint_color": model.tint_color,
                "deformer": model.deformer,
            })

        for widget in result.widgets:
            if widget.type in ("group", "element"):
                evaluated.append(self._marker_draw_info(widget, data_by_id.get(widget.element_id, {})))
            else:
                self._widget_infos.append(self._widget_draw_info(widget))

        # Core flattens every element to a world matrix and doesn't hand back
        # parent linkage, so recover each element's actual parent world matrix
        # from the tree hierarchy (skipping ancestors Core didn't evaluate,
        # e.g. unsupported/hidden nodes) instead of assuming no parent exists.
        id_to_world = {entry["id"]: entry["world_matrix"] for entry in evaluated}
        for entry in evaluated:
            entry["parent_world_matrix"] = self._resolve_parent_world_matrix(
                entry["id"], parent_id_by_id, id_to_world
            )

        return evaluated

    @staticmethod
    def _resolve_parent_world_matrix(element_id, parent_id_by_id, id_to_world):
        """Walk up the tree hierarchy to the nearest ancestor Core evaluated."""
        ancestor_id = parent_id_by_id.get(element_id, 0)
        while ancestor_id and ancestor_id not in id_to_world:
            ancestor_id = parent_id_by_id.get(ancestor_id, 0)
        return id_to_world.get(ancestor_id, np.eye(4, dtype=np.float32))

    @staticmethod
    def _marker_draw_info(widget, data):
        """Adapt a Core hierarchy marker to the selectable scene-object schema."""
        world_matrix = np.asarray(widget.transform, dtype=np.float32).reshape((4, 4))
        world_position, world_rotation, world_scale = decompose_trs(world_matrix)
        return {
            "id": widget.element_id,
            "path": "",
            "position": world_position,
            "rotation": world_rotation,
            "scale": world_scale,
            "world_matrix": world_matrix,
            "data": data,
            "is_editor_marker": True,
            "marker_type": widget.type,
        }

    @staticmethod
    def _widget_draw_info(widget):
        """Adapt a Core widget placement to the existing OpenGL draw schema."""
        world_matrix = np.asarray(widget.transform, dtype=np.float32).reshape((4, 4))
        world_position, world_rotation, _ = decompose_trs(world_matrix)
        offset = np.asarray(widget.offset, dtype=np.float32)
        positioned = (np.array([*offset, 1.0], dtype=np.float32) @ world_matrix)[:3]
        return {
            "type": widget.type,
            "element_id": widget.element_id,
            "world_matrix": world_matrix,
            "position": list(world_position) if widget.type == "sizer" else positioned.tolist(),
            "rotation": list(world_rotation),
            "offset": list(widget.offset),
            "min_bounds": list(widget.minimum_bounds),
            "max_bounds": list(widget.maximum_bounds),
            "axis": list(widget.axis),
            "color": list(widget.color),
            "handles": dict(zip(
                ("min_x", "max_x", "min_y", "max_y", "min_z", "max_z"),
                widget.handles,
            )),
            "active_axes": dict(zip(("x", "y", "z"), widget.active_axes)),
            "scale": widget.scale,
            "radius": widget.radius,
            "angle": widget.angle,
            "size": widget.size,
            "shape": widget.shape,
            "name": widget.name,
        }

    def _collect_nested_smartprops(self, document):
        """Load the nested SmartProp graph for the Core resolver payload."""
        import os
        import re

        from gui.editors.smartprop_editor.document_model import parse_smartprop
        from gui.settings.common import addon_content_dir, get_addon_name, get_cs2_path

        cs2_path = get_cs2_path()
        default_addon = get_addon_name()
        if not (cs2_path and default_addon):
            return {}

        documents = {}
        visited = set()

        def load(resource_path, context_addon):
            addon = context_addon or default_addon
            normalized_path = resource_path.replace("\\", "/").lstrip("/")
            addon_match = re.search(
                r"(?:^|/)csgo_addons/([^/]+)/(.*)$",
                normalized_path,
                re.IGNORECASE,
            )
            if addon_match:
                addon = addon_match.group(1)
                normalized_path = addon_match.group(2)

            full_path = os.path.join(addon_content_dir(addon), normalized_path)
            visit_key = os.path.normcase(os.path.normpath(full_path))
            if visit_key in visited or not os.path.isfile(full_path):
                return
            visited.add(visit_key)

            with open(full_path, "r", encoding="utf-8") as nested_file:
                nested_document = parse_smartprop(nested_file.read())
            documents[resource_path] = nested_document
            scan(nested_document, addon)

        def scan(value, context_addon=default_addon):
            if isinstance(value, dict):
                for child_value in value.values():
                    scan(child_value, context_addon)
            elif isinstance(value, list):
                for child_value in value:
                    scan(child_value, context_addon)
            elif isinstance(value, str) and value.lower().endswith(".vsmart"):
                load(value, context_addon)

        scan(document)
        return documents

    def _follow_selection_isolation(self):
        """Point the isolation at the current selection while dynamic mode is on.

        Returns True when the scene was rebuilt (the caller can skip its own
        gizmo sync — update_viewport() already did it).
        """
        if not self.dynamic_isolation:
            return False
        target = self._selected_id if self._selected_id else None
        if target == self.isolated_element_id:
            return False
        self.isolated_element_id = target
        self.isolated_element_name = ""
        self.update_viewport()
        return True

    @gl_guard("event")
    def set_dynamic_isolation(self, enabled: bool):
        """Enable/disable selection-following isolation (clears it when off)."""
        self.dynamic_isolation = bool(enabled)
        if not self.dynamic_isolation:
            self.isolated_element_id = None
            self.isolated_element_name = ""
            self.update_viewport()
        else:
            self._follow_selection_isolation()

    @gl_guard("event")
    def highlight_element(self, element_id: int):
        """Select/Highlight element and reposition gizmo."""
        self._selected_id = element_id
        if self._follow_selection_isolation():
            return
        if element_id != 0 and element_id in self._model_infos:
            sel = self._model_infos[element_id]
            self.gizmo.set_transform(sel["position"], sel["rotation"], sel["scale"])
            self._apply_gizmo_availability(sel.get("data"))
        else:
            self.gizmo.hide()
        self.update()

    def _sync_gizmo_settings(self, event=None):
        self.gizmo.coordinate_space = self.coordinate_space
        self.gizmo.camera_right = self.camera.right_vector
        self.gizmo.camera_up = self.camera.up_vector
        self.gizmo.camera_forward = self.camera.target - self.camera.position

        # Snapping toggling with Ctrl key
        ctrl_held = False
        if event is not None:
            ctrl_held = bool(event.modifiers() & Qt.ControlModifier)
        elif QApplication.keyboardModifiers() & Qt.ControlModifier:
            ctrl_held = True

        self.gizmo.snapping_enabled = self.snapping_enabled ^ ctrl_held
        self.gizmo.grid_step = self.grid_step
        self.gizmo.rotation_step = self.rotation_step

    # Mouse & Keyboard Event Handlers
    @gl_guard("event")
    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        self._last_mouse_pos = event.position()
        self._sync_gizmo_settings(event)

        # Hit test transform gizmo first (left click only, matches selection)
        if event.button() == Qt.LeftButton and self.gizmo.visible and self.gizmo.mode != GizmoMode.NONE:
            # Build ray
            w, h = self.width(), self.height()
            ray_org, ray_dir = self.camera.screen_to_ray(event.position().x(), event.position().y(), w, h)
            axis = self.gizmo.hit_test(ray_org, ray_dir, self.camera.position)

            if axis != GizmoAxis.NONE:
                self.gizmo.begin_drag(axis, (event.position().x(), event.position().y()))
                # Arm the one-shot panel-rebuild guard for this drag (used when a
                # transform modifier is created on the first move).
                if self.document is not None:
                    self.document._gizmo_live_rebuilt = False
                # Snapshot document data before dragging for undo history
                if self.document and hasattr(self.document, "_gizmo_pre_drag_data"):
                    item = self.document.ui.tree_hierarchy_widget.currentItem()
                    if item:
                        from gui.common import fast_deepcopy
                        self.document._gizmo_pre_drag_data = fast_deepcopy(item.data(0, Qt.UserRole))
                self.update()
                return

        # Blender-style navigation: MMB orbits, Shift+MMB pans, LMB selects
        # Right click: Engine Game Camera (Fly Mode)
        if event.button() == Qt.RightButton and not self.gizmo.is_dragging:
            self._is_flying = True
            self._fly_last_time = time.perf_counter()
            self._pressed_keys.clear()
            if not self._fly_timer.isActive():
                self._fly_timer.start()
            self.setCursor(Qt.BlankCursor)
            self.update()
            return
        elif event.button() == Qt.LeftButton:
            # Trigger color-picking on next paintGL
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

    @gl_guard("event")
    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        self._sync_gizmo_settings(event)
        dx = pos.x() - self._last_mouse_pos.x()
        dy = pos.y() - self._last_mouse_pos.y()

        if self._is_flying:
            self.camera.look(dx, dy)
            self._last_mouse_pos = pos
            self.update()
            return

        if self.gizmo.is_dragging:
            w, h = self.width(), self.height()
            view = self.camera.view_matrix
            proj = self.camera.projection_matrix
            cam_pos = self.camera.position

            delta = self.gizmo.update_drag(
                (pos.x(), pos.y()), view, proj, w, h, cam_pos
            )

            if delta and self.document:
                item = self.document.ui.tree_hierarchy_widget.currentItem()
                if item and self._selected_id in self._model_infos:
                    from gui.common import fast_deepcopy
                    data = fast_deepcopy(item.data(0, Qt.UserRole))

                    # Only the dragged axis changes.  Writing a single component
                    # (instead of the whole vector) preserves any variable /
                    # expression bindings on the other two axes.
                    axis_idx = self._active_axis_index()
                    is_center = self.gizmo.active_axis == GizmoAxis.CENTER
                    info = self._model_infos[self._selected_id]
                    parent_world_matrix = info.get("parent_world_matrix", np.eye(4, dtype=np.float32))

                    # 1. Build the updated world matrix based on the delta
                    world_pos = delta.get("position", info.get("position", [0.0, 0.0, 0.0]))
                    world_rot = delta.get("rotation", info.get("rotation", [0.0, 0.0, 0.0]))
                    world_scale = delta.get("scale", info.get("scale", [1.0, 1.0, 1.0]))

                    M_new_world = (
                        scale_matrix(*world_scale)
                        @ rotation_matrix_euler(*world_rot)
                        @ translation_matrix(*world_pos)
                    )

                    # 2. Convert to local space (guard a degenerate/zero-scale
                    # ancestor so a drag can't crash on a singular parent matrix).
                    try:
                        M_parent_inv = np.linalg.inv(parent_world_matrix)
                    except np.linalg.LinAlgError:
                        M_parent_inv = np.eye(4, dtype=np.float32)
                    M_new_local = M_new_world @ M_parent_inv

                    target_local_pos, target_local_rot, target_local_scale = decompose_trs(M_new_local)

                    # 4. Apply to modifiers.  Collect the property keys touched so
                    # the Property panel can live-update just those value widgets.
                    changed_keys = []
                    if "position" in delta:
                        mod = self._find_or_create_modifier(data, "CSmartPropOperation_Translate", "m_vPosition")
                        M_prior = self._evaluate_modifiers_prior_to(data, mod, parent_world_matrix)
                        space = str(mod.get("m_CoordinateSpace") or "ELEMENT").upper()

                        if space in ("WORLD", "PARENT"):
                            M_prior_pos, _, _ = decompose_trs(M_prior)
                            target_mod_pos = [
                                float(target_local_pos[0] - M_prior_pos[0]),
                                float(target_local_pos[1] - M_prior_pos[1]),
                                float(target_local_pos[2] - M_prior_pos[2]),
                            ]
                        else:
                            try:
                                M_prior_inv = np.linalg.inv(M_prior)
                            except np.linalg.LinAlgError:
                                M_prior_inv = np.eye(4, dtype=np.float32)
                            p_homo = np.array([target_local_pos[0], target_local_pos[1], target_local_pos[2], 1.0], dtype=np.float32)
                            target_mod_pos = [float(x) for x in (p_homo @ M_prior_inv)[:3]]

                        avail = self._vector_axis_availability(mod.get("m_vPosition"))
                        axes = [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]
                        for i, axis in enumerate(axes):
                            if avail.get(axis, True):
                                self._set_vector_component(mod, "m_vPosition", i, target_mod_pos[i], target_mod_pos)
                        changed_keys.append(f"m_Modifiers[{data['m_Modifiers'].index(mod)}].m_vPosition")
                        self.current_transform_text = f"Translate: X: {target_mod_pos[0]:.2f}, Y: {target_mod_pos[1]:.2f}, Z: {target_mod_pos[2]:.2f}"
                    elif "rotation" in delta:
                        mod = self._find_or_create_modifier(data, "CSmartPropOperation_Rotate", "m_vRotation")
                        M_prior = self._evaluate_modifiers_prior_to(data, mod, parent_world_matrix)
                        space = str(mod.get("m_CoordinateSpace") or "ELEMENT").upper()

                        _, rot_prior, _ = decompose_trs(M_prior)
                        R_prior = rotation_matrix_euler(*rot_prior)
                        R_target = rotation_matrix_euler(*target_local_rot)

                        if space in ("WORLD", "PARENT"):
                            R_mod = R_prior.T @ R_target
                        else:
                            R_mod = R_target @ R_prior.T

                        _, target_mod_rot, _ = decompose_trs(R_mod)

                        avail = self._vector_axis_availability(mod.get("m_vRotation"))
                        axes = [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]
                        for i, axis in enumerate(axes):
                            if avail.get(axis, True):
                                self._set_vector_component(mod, "m_vRotation", i, target_mod_rot[i], target_mod_rot)
                        changed_keys.append(f"m_Modifiers[{data['m_Modifiers'].index(mod)}].m_vRotation")
                        self.current_transform_text = f"Rotate: Pitch: {target_mod_rot[0]:.2f}, Yaw: {target_mod_rot[1]:.2f}, Roll: {target_mod_rot[2]:.2f}"
                    elif "scale" in delta and (axis_idx is not None or is_center):
                        changed_keys.extend(self._apply_scale_delta(data, axis_idx, target_local_scale, uniform=is_center))
                        if is_center:
                            self.current_transform_text = f"Scaling {target_local_scale[0]:.2f}"
                        else:
                            self.current_transform_text = f"Scale: X: {target_local_scale[0]:.2f}, Y: {target_local_scale[1]:.2f}, Z: {target_local_scale[2]:.2f}"

                    item.setData(0, Qt.UserRole, data)

                    # Live-refresh the touched Property panel value widgets so the
                    # fields track the gizmo drag smoothly (not just on release).
                    if changed_keys and hasattr(self.document, "ui") and hasattr(self.document.ui, "PropertiesFrame"):
                        self.document.update_property_frame_values(data, changed_keys)

                    # Core is the only transform evaluator. Rebuild from its
                    # primitive placements after writing the editor values.
                    self.update_viewport()

            self._last_mouse_pos = pos
            self.update()
            return

        # Hover test gizmo
        if self.gizmo.visible and not self.gizmo.is_dragging:
            w, h = self.width(), self.height()
            ray_org, ray_dir = self.camera.screen_to_ray(pos.x(), pos.y(), w, h)
            axis = self.gizmo.hit_test(ray_org, ray_dir, self.camera.position)
            if axis != self.gizmo.hover_axis:
                self.gizmo.hover_axis = axis
                self.update()

        if self._action == 'orbit':
            self.camera.orbit(dx, dy)
        elif self._action == 'pan':
            self.camera.pan(dx, dy)
        elif self._action == 'zoom':
            self.camera.zoom(-(dx - dy))

        self._last_mouse_pos = pos
        self.update()

    @gl_guard("event")
    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.gizmo.is_dragging:
            self.gizmo.end_drag()
            # Push changes to undo stack
            if self.document and hasattr(self.document, "_gizmo_commit_drag"):
                self.document._gizmo_commit_drag()
            self.update_viewport()
        if event.button() == Qt.RightButton and self._is_flying:
            self._is_flying = False
            self._pressed_keys.clear()
            if self._fly_timer.isActive():
                self._fly_timer.stop()
            self.unsetCursor()
            self.current_transform_text = None
            self.update()
            return
        self._action = None
        self.current_transform_text = None
        self.update()

    @gl_guard("event")
    def wheelEvent(self, event):
        if self._is_flying:
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1.0 / 1.15
            self.fly_speed = max(10.0, min(20000.0, self.fly_speed * factor))
            self.current_transform_text = f"Camera Speed: {self.fly_speed:.0f}"
            self.update()
            return
        self.camera.zoom(event.angleDelta().y())
        self.update()

    @gl_guard("event")
    def keyPressEvent(self, event):
        if self._is_flying:
            if not event.isAutoRepeat():
                self._pressed_keys.add(event.key())
            event.accept()
            return

        if event.key() == Qt.Key_Q:
            self.gizmo.set_mode(GizmoMode.NONE)
            self.gizmoModeChanged.emit(GizmoMode.NONE)
            self.update()
        elif event.key() == Qt.Key_W:
            self.gizmo.set_mode(GizmoMode.TRANSLATE)
            self.gizmoModeChanged.emit(GizmoMode.TRANSLATE)
            self.update()
        elif event.key() == Qt.Key_E:
            self.gizmo.set_mode(GizmoMode.ROTATE)
            self.gizmoModeChanged.emit(GizmoMode.ROTATE)
            self.update()
        elif event.key() == Qt.Key_R:
            self.gizmo.set_mode(GizmoMode.SCALE)
            self.gizmoModeChanged.emit(GizmoMode.SCALE)
            self.update()
        elif event.key() == Qt.Key_F:
            # Frame the current selection (or the whole scene if nothing selected).
            self.frame_selection()
        else:
            super().keyPressEvent(event)

    @gl_guard("event")
    def keyReleaseEvent(self, event):
        if self._is_flying:
            if not event.isAutoRepeat():
                self._pressed_keys.discard(event.key())
            event.accept()
            return
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        if self._is_flying:
            self._is_flying = False
            self._pressed_keys.clear()
            if self._fly_timer.isActive():
                self._fly_timer.stop()
            self.unsetCursor()
            self.current_transform_text = None
            self.update()
        super().focusOutEvent(event)

    def _update_fly_movement(self):
        if not self._is_flying:
            self._fly_timer.stop()
            return

        now = time.perf_counter()
        dt = max(0.001, min(0.1, now - (self._fly_last_time or now)))
        self._fly_last_time = now

        forward = 0.0
        right = 0.0
        up = 0.0

        if Qt.Key_W in self._pressed_keys:
            forward += 1.0
        if Qt.Key_S in self._pressed_keys:
            forward -= 1.0
        if Qt.Key_D in self._pressed_keys:
            right += 1.0
        if Qt.Key_A in self._pressed_keys:
            right -= 1.0
        if Qt.Key_E in self._pressed_keys or Qt.Key_Space in self._pressed_keys:
            up += 1.0
        if Qt.Key_Q in self._pressed_keys or Qt.Key_C in self._pressed_keys:
            up -= 1.0

        if forward != 0.0 or right != 0.0 or up != 0.0:
            length = math.sqrt(forward * forward + right * right + up * up)
            if length > 1.0:
                forward /= length
                right /= length
                up /= length

            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ShiftModifier:
                speed_multiplier = 3.0
            elif modifiers & (Qt.ControlModifier | Qt.AltModifier):
                speed_multiplier = 0.25
            else:
                speed_multiplier = 1.0

            dist = self.fly_speed * speed_multiplier * dt
            self.camera.move_fly(forward * dist, right * dist, up * dist)
            self.update()

    # Gizmo axis availability
    # Element classes that carry a model (and therefore a model scale).
    _MODEL_LIKE_CLASSES = (
        "CSmartPropElement_Model",
        "CSmartPropElement_ModelEntity",
        "CSmartPropElement_PropPhysics",
        "CSmartPropElement_PropDynamic",
    )

    def _active_axis_index(self):
        """Return 0/1/2 for the axis currently being dragged, else None."""
        return {GizmoAxis.X: 0, GizmoAxis.Y: 1, GizmoAxis.Z: 2}.get(self.gizmo.active_axis)

    def _apply_gizmo_availability(self, data):
        """Compute per-axis availability for ``data`` and push it to the gizmo."""
        availability, scale_source = self._compute_axis_availability(data)
        self._scale_source = scale_source
        self.gizmo.set_axis_availability(availability)

    def _compute_axis_availability(self, data):
        """Work out which gizmo axes can be manipulated for an element.

        Returns ``(availability, scale_source)`` where ``availability`` is
        ``{GizmoMode: {axis: bool}}``.  An axis is unavailable when its value is
        bound to a variable/expression, when the whole vector is variable-bound,
        or (for scale) when the element has no scale property at all.

        Translate/Rotate default to fully available even when the modifier is
        absent — dragging creates it.  Scale is never auto-created.
        """
        all_on = {GizmoAxis.X: True, GizmoAxis.Y: True, GizmoAxis.Z: True}
        availability = {
            GizmoMode.TRANSLATE: dict(all_on),
            GizmoMode.ROTATE:    dict(all_on),
            GizmoMode.SCALE:     {GizmoAxis.X: False, GizmoAxis.Y: False,
                                  GizmoAxis.Z: False, GizmoAxis.CENTER: False},
        }
        if not isinstance(data, dict):
            return availability, None

        translate = self._find_modifier(data, "CSmartPropOperation_Translate")
        if translate is not None:
            availability[GizmoMode.TRANSLATE] = self._vector_axis_availability(translate.get("m_vPosition"))

        rotate = self._find_modifier(data, "CSmartPropOperation_Rotate")
        if rotate is not None:
            availability[GizmoMode.ROTATE] = self._vector_axis_availability(rotate.get("m_vRotation"))

        scale_avail, scale_source = self._scale_axis_availability(data)
        availability[GizmoMode.SCALE] = scale_avail
        return availability, scale_source

    def _scale_axis_availability(self, data):
        """Return ``(availability, source)`` for the Scale gizmo.

        ``source`` is ``"vector"`` (per-axis m_vModelScale), ``"uniform"``
        (single value), or ``None`` (no scale property → all axes grayed).
        """
        all_on = {GizmoAxis.X: True, GizmoAxis.Y: True, GizmoAxis.Z: True}
        all_off = {GizmoAxis.X: False, GizmoAxis.Y: False, GizmoAxis.Z: False}

        # The center (uniform) handle needs every axis editable, since it scales
        # them all at once — a variable/expression on any component disables it.
        def with_center(avail):
            avail = dict(avail)
            avail[GizmoAxis.CENTER] = (
                avail[GizmoAxis.X] and avail[GizmoAxis.Y] and avail[GizmoAxis.Z]
            )
            return avail

        has_model_scale = (
            data.get("_class", "") in self._MODEL_LIKE_CLASSES
            or "m_vModelScale" in data
            or "m_flUniformModelScale" in data
        )
        if has_model_scale:
            model_scale = data.get("m_vModelScale")
            if model_scale is not None:
                return with_center(self._vector_axis_availability(model_scale)), "vector"
            return with_center(all_on), "uniform"

        scale_mod = self._find_modifier(data, "CSmartPropOperation_Scale")
        if scale_mod is not None:
            # A variable/expression-bound uniform scale can't be dragged.
            if isinstance(scale_mod.get("m_flScale"), dict):
                return with_center(all_off), "uniform"
            return with_center(all_on), "uniform"

        return with_center(all_off), None

    def _vector_axis_availability(self, vec):
        """Per-axis availability for a vector value (position/rotation/scale)."""
        # Whole vector bound to a single variable → no per-axis editing.
        if isinstance(vec, dict) and "m_SourceName" in vec and "m_Components" not in vec:
            return {GizmoAxis.X: False, GizmoAxis.Y: False, GizmoAxis.Z: False}
        comps = self._vector_components(vec)
        if comps is None:
            # Unset / None — treated as [0, 0, 0], all directly editable.
            return {GizmoAxis.X: True, GizmoAxis.Y: True, GizmoAxis.Z: True}
        axes = (GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z)
        return {
            axes[i]: (self._component_is_literal(comps[i]) if i < len(comps) else True)
            for i in range(3)
        }

    # Data modifier helpers
    def _evaluate_modifiers_prior_to(self, data, target_mod, parent_world_matrix):
        """Return the UI editing basis without evaluating domain modifiers."""
        return np.eye(4, dtype=np.float32)

    @staticmethod
    def _find_modifier(data, class_name):
        """Return the first modifier dict of the given class, or None."""
        for mod in data.get("m_Modifiers") or []:
            if isinstance(mod, dict) and mod.get("_class") == class_name:
                return mod
        return None

    def _find_or_create_modifier(self, data, class_name, vector_key=None):
        """Return the modifier of ``class_name``, creating an enabled one if absent.

        When created for a transform (``vector_key`` given) the vector is
        initialised to a zeroed ``m_Components`` list, matching the editor's own
        Translate/Rotate defaults.
        """
        mod = self._find_modifier(data, class_name)
        if mod is not None:
            return mod
        modifiers = data.get("m_Modifiers")
        if modifiers is None:
            modifiers = []
            data["m_Modifiers"] = modifiers
        mod = {"_class": class_name, "m_bEnabled": True}
        if vector_key is not None:
            mod[vector_key] = {"m_Components": [0.0, 0.0, 0.0]}

        # Maintain canonical TRS (Translate -> Rotate -> Scale) modifier order
        if class_name in ("CSmartPropOperation_Translate", "Translate"):
            insert_idx = len(modifiers)
            for idx, m in enumerate(modifiers):
                if isinstance(m, dict) and m.get("_class") in (
                    "CSmartPropOperation_Rotate", "Rotate",
                    "CSmartPropOperation_Scale", "Scale"
                ):
                    insert_idx = idx
                    break
            modifiers.insert(insert_idx, mod)
        elif class_name in ("CSmartPropOperation_Rotate", "Rotate"):
            insert_idx = len(modifiers)
            for idx, m in enumerate(modifiers):
                if isinstance(m, dict) and m.get("_class") in (
                    "CSmartPropOperation_Scale", "Scale"
                ):
                    insert_idx = idx
                    break
            modifiers.insert(insert_idx, mod)
        else:
            modifiers.append(mod)

        return mod

    def _set_vector_component(self, container, key, axis_idx, value, full_vector):
        """Write one numeric component of a vector field, preserving the other
        components (including variable/expression bindings) and the container
        format (``m_Components`` dict vs plain list)."""
        vec = container.get(key)
        value = float(value)
        if isinstance(vec, dict) and "m_Components" in vec:
            comps = list(vec["m_Components"])
            while len(comps) < 3:
                comps.append(0.0)
            comps[axis_idx] = value
            new_vec = dict(vec)
            new_vec["m_Components"] = comps
            container[key] = new_vec
        elif isinstance(vec, (list, tuple)):
            comps = list(vec)
            while len(comps) < 3:
                comps.append(0.0)
            comps[axis_idx] = value
            container[key] = comps
        else:
            # None / unmergeable — build a fresh literal vector.
            container[key] = [float(full_vector[0]), float(full_vector[1]), float(full_vector[2])]

    def _apply_scale_delta(self, data, axis_idx, scale_vec, uniform=False):
        """Apply a scale drag to ``data`` according to the element's scale source.

        ``uniform`` (the center handle) scales every axis at once; otherwise only
        ``axis_idx`` changes.  Returns the list of property keys written (e.g.
        ``["m_vModelScale"]``) so the Property panel can live-update just those.
        """
        source = self._scale_source
        if uniform:
            if source == "vector":
                # Every component is literal (guaranteed by CENTER availability);
                for i in range(3):
                    self._set_vector_component(data, "m_vModelScale", i, scale_vec[i], scale_vec)
                return ["m_vModelScale"]
            if source == "uniform":
                return [self._write_uniform_scale(data, scale_vec[0])]
            return []

        if source == "vector":
            self._set_vector_component(data, "m_vModelScale", axis_idx, scale_vec[axis_idx], scale_vec)
            return ["m_vModelScale"]
        if source == "uniform":
            return [self._write_uniform_scale(data, scale_vec[axis_idx])]
        # source is None: scale axes are grayed and shouldn't be draggable.
        return []

    def _write_uniform_scale(self, data, value):
        """Write a single uniform scale value to whichever field the element uses.

        Returns the property key that was written, for the Property panel's
        live drag update.
        """
        value = float(value)
        has_model_scale = (
            data.get("_class", "") in self._MODEL_LIKE_CLASSES
            or "m_vModelScale" in data
            or "m_flUniformModelScale" in data
        )
        if has_model_scale:
            data["m_flUniformModelScale"] = value
            return "m_flUniformModelScale"
        if data.get("m_flUniformModelScale") is not None:
            data["m_flUniformModelScale"] = value
            return "m_flUniformModelScale"
        scale_mod = self._find_modifier(data, "CSmartPropOperation_Scale")
        if scale_mod is not None:
            scale_mod["m_flScale"] = value
            return f"m_Modifiers[{data['m_Modifiers'].index(scale_mod)}].m_flScale"
        data["m_flUniformModelScale"] = value
        return "m_flUniformModelScale"

    @staticmethod
    def _vector_components(vec):
        """Return the list of raw components of a vector value, or None if the
        value has no per-component form (None, or a whole-vector variable)."""
        if isinstance(vec, dict):
            if "m_Components" in vec:
                return list(vec["m_Components"])
            return None
        if isinstance(vec, (list, tuple)):
            return list(vec)
        return None

    @staticmethod
    def _component_is_literal(comp):
        """True when a vector component is a plain number the gizmo can edit
        (i.e. not a variable ``m_SourceName`` or ``m_Expression`` binding)."""
        if isinstance(comp, bool):
            return False
        if isinstance(comp, (int, float)):
            return True
        if isinstance(comp, str):
            try:
                float(comp)
                return True
            except ValueError:
                return False
        return False

    def _update_element_widgets(self, eid, world_pos, world_rot, world_matrix):
        """Update the world transform of all visual widgets belonging to element `eid`."""
        if not eid or not self._widget_infos:
            return
        for w in self._widget_infos:
            if w.get("element_id") == eid:
                wtype = w.get("type")
                if wtype == "sizer":
                    w["world_matrix"] = np.array(world_matrix, dtype=np.float32)
                    w["position"] = [float(world_pos[0]), float(world_pos[1]), float(world_pos[2])]
                    w["rotation"] = [float(world_rot[0]), float(world_rot[1]), float(world_rot[2])]
                else:
                    offset = w.get("offset", [0.0, 0.0, 0.0])
                    p = np.array([offset[0], offset[1], offset[2], 1.0], dtype=np.float32)
                    world_offset = (p @ world_matrix)[:3]
                    w["position"] = [float(world_offset[0]), float(world_offset[1]), float(world_offset[2])]
                    w["rotation"] = [float(world_rot[0]), float(world_rot[1]), float(world_rot[2])]

    @staticmethod
    def _build_locator_vertices():
        """Build 3D faceted locator geometry for the 6 axes (+/- X Red, +/- Y Green, +/- Z Blue).
        Returns a float32 numpy array with [x, y, z, nx, ny, nz, r, g, b] per vertex.
        """
        def build_axis_arm(D, U, V, color, L_pos=1.0, d_shoulder=0.60, r_pos=0.22, L_neg=0.70, r_neg=0.20):
            origin = np.array([0.0, 0.0, 0.0], dtype=np.float32)
            s0 = d_shoulder * D + r_pos * U
            s1 = d_shoulder * D + r_pos * V
            s2 = d_shoulder * D - r_pos * U
            s3 = d_shoulder * D - r_pos * V
            tip = L_pos * D

            # Positive pointed arrowhead arm (8 triangles)
            pos_faces = [
                (origin, s1, s0),
                (origin, s2, s1),
                (origin, s3, s2),
                (origin, s0, s3),
                (tip, s0, s1),
                (tip, s1, s2),
                (tip, s2, s3),
                (tip, s3, s0),
            ]

            # Negative flat-capped prism arm (6 triangles: 4 sides + 2 end cap)
            e0 = -L_neg * D + r_neg * U
            e1 = -L_neg * D + r_neg * V
            e2 = -L_neg * D - r_neg * U
            e3 = -L_neg * D - r_neg * V

            neg_faces = [
                # 4 long side facets from origin to end cap
                (origin, e0, e1),
                (origin, e1, e2),
                (origin, e2, e3),
                (origin, e3, e0),
                # Flat diamond end cap
                (e0, e2, e1),
                (e0, e3, e2),
            ]

            verts = []
            for tri in pos_faces + neg_faces:
                v0, v1, v2 = tri
                e_1 = v1 - v0
                e_2 = v2 - v0
                n = np.cross(e_1, e_2)
                norm_len = np.linalg.norm(n)
                if norm_len > 1e-6:
                    n = n / norm_len
                else:
                    n = np.array([0.0, 1.0, 0.0], dtype=np.float32)
                for v in (v0, v1, v2):
                    verts.extend([v[0], v[1], v[2], n[0], n[1], n[2], color[0], color[1], color[2]])
            return verts

        X_D = np.array([1, 0, 0], dtype=np.float32)
        X_U = np.array([0, 1, 0], dtype=np.float32)
        X_V = np.array([0, 0, 1], dtype=np.float32)
        red = [0.85, 0.12, 0.12]

        Y_D = np.array([0, 1, 0], dtype=np.float32)
        Y_U = np.array([0, 0, 1], dtype=np.float32)
        Y_V = np.array([1, 0, 0], dtype=np.float32)
        green = [0.0, 0.85, 0.0]

        Z_D = np.array([0, 0, 1], dtype=np.float32)
        Z_U = np.array([1, 0, 0], dtype=np.float32)
        Z_V = np.array([0, 1, 0], dtype=np.float32)
        blue = [0.0, 0.16, 0.78]

        all_verts = []
        all_verts.extend(build_axis_arm(X_D, X_U, X_V, red))
        all_verts.extend(build_axis_arm(Y_D, Y_U, Y_V, green))
        all_verts.extend(build_axis_arm(Z_D, Z_U, Z_V, blue))
        return np.array(all_verts, dtype=np.float32)

    @staticmethod
    def _build_sizer_arrow_vertices(length=14.0, shaft_r=0.7, head_len=7.0, head_r=2.5, segments=12):
        """Build an arrow pointing along +Z (Source 2 up) with shaft and cone head."""
        verts = []
        shaft_len = max(0.0, length - head_len)
        for i in range(segments):
            a1 = 2.0 * math.pi * i / segments
            a2 = 2.0 * math.pi * (i + 1) / segments
            p0a = [shaft_r * math.cos(a1), shaft_r * math.sin(a1), 0.0]
            p0b = [shaft_r * math.cos(a2), shaft_r * math.sin(a2), 0.0]
            p1a = [shaft_r * math.cos(a1), shaft_r * math.sin(a1), shaft_len]
            p1b = [shaft_r * math.cos(a2), shaft_r * math.sin(a2), shaft_len]
            verts.extend([p0a, p0b, p1a])
            verts.extend([p0b, p1b, p1a])
        cone_base_z = shaft_len
        cone_tip = [0.0, 0.0, length]
        for i in range(segments):
            a1 = 2.0 * math.pi * i / segments
            a2 = 2.0 * math.pi * (i + 1) / segments
            c1 = [head_r * math.cos(a1), head_r * math.sin(a1), cone_base_z]
            c2 = [head_r * math.cos(a2), head_r * math.sin(a2), cone_base_z]
            verts.extend([[0.0, 0.0, cone_base_z], c2, c1])
            verts.extend([cone_tip, c1, c2])
        return np.array(verts, dtype=np.float32)

    @staticmethod
    def _build_rotator_ring_vertices(segments=64, inner_r=0.90, outer_r=1.0, height=0.04):
        """Build a 3D extruded circular ring band with top, bottom, outer, and inner cylindrical walls."""
        verts = []
        hz = height * 0.5
        for i in range(segments):
            a1 = 2.0 * math.pi * i / segments
            a2 = 2.0 * math.pi * (i + 1) / segments
            c1, s1 = math.cos(a1), math.sin(a1)
            c2, s2 = math.cos(a2), math.sin(a2)

            # Top ring (z = +hz)
            it1 = [inner_r * c1, inner_r * s1, hz]
            it2 = [inner_r * c2, inner_r * s2, hz]
            ot1 = [outer_r * c1, outer_r * s1, hz]
            ot2 = [outer_r * c2, outer_r * s2, hz]
            verts.extend([it1, ot1, ot2, it1, ot2, it2])

            # Bottom ring (z = -hz)
            ib1 = [inner_r * c1, inner_r * s1, -hz]
            ib2 = [inner_r * c2, inner_r * s2, -hz]
            ob1 = [outer_r * c1, outer_r * s1, -hz]
            ob2 = [outer_r * c2, outer_r * s2, -hz]
            verts.extend([ib1, ob2, ob1, ib1, ib2, ob2])

            # Outer cylindrical wall (r = outer_r)
            verts.extend([ot1, ob1, ob2, ot1, ob2, ot2])

            # Inner cylindrical wall (r = inner_r)
            verts.extend([it1, it2, ib2, it1, ib2, ib1])

        return np.array(verts, dtype=np.float32)

    @staticmethod
    def _build_rotator_tab_vertices(cx=0.95, w=0.09, h=0.07, depth=0.06):
        """Build a 3D box tab on the ring centered around (cx, 0, 0)."""
        x0, x1 = cx - w * 0.5, cx + w * 0.5
        y0, y1 = -h * 0.5, h * 0.5
        z0, z1 = -depth * 0.5, depth * 0.5

        c000 = [x0, y0, z0]
        c100 = [x1, y0, z0]
        c110 = [x1, y1, z0]
        c010 = [x0, y1, z0]
        c001 = [x0, y0, z1]
        c101 = [x1, y0, z1]
        c111 = [x1, y1, z1]
        c011 = [x0, y1, z1]

        faces = [
            # Top (+Z)
            c001, c101, c111, c001, c111, c011,
            # Bottom (-Z)
            c000, c110, c100, c000, c010, c110,
            # Outer (+X)
            c100, c110, c111, c100, c111, c101,
            # Inner (-X)
            c000, c011, c010, c000, c001, c011,
            # Side (+Y)
            c010, c110, c111, c010, c111, c011,
            # Side (-Y)
            c000, c101, c100, c000, c001, c101,
        ]
        return np.array(faces, dtype=np.float32)

    def _draw_dynamic_verts(self, arr, mode):
        """Draw dynamic vertex array using reusable GL buffers."""
        from OpenGL import GL
        if len(arr) == 0:
            return
        GL.glBindVertexArray(self._dynamic_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._dynamic_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, arr.nbytes, arr, GL.GL_DYNAMIC_DRAW)
        GL.glDrawArrays(mode, 0, len(arr))
        GL.glBindVertexArray(0)

    def _init_widget_geometry(self):
        """Build the static GPU geometry for the preview widgets."""
        from OpenGL import GL

        def make_vao(verts):
            arr = np.asarray(verts, dtype=np.float32)
            vao = GL.glGenVertexArrays(1)
            vbo = GL.glGenBuffers(1)
            GL.glBindVertexArray(vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, arr.nbytes, arr, GL.GL_STATIC_DRAW)
            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
            GL.glEnableVertexAttribArray(0)
            GL.glBindVertexArray(0)
            return vao

        # 1. 3D Faceted Locator (198 vertices with pos, normal, color)
        locator_verts = self._build_locator_vertices()
        self._locator_vao = GL.glGenVertexArrays(1)
        self._locator_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._locator_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._locator_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, locator_verts.nbytes, locator_verts, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 36, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 36, GL.ctypes.c_void_p(12))
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(2, 3, GL.GL_FLOAT, GL.GL_FALSE, 36, GL.ctypes.c_void_p(24))
        GL.glEnableVertexAttribArray(2)
        GL.glBindVertexArray(0)
        self._locator_vertex_count = len(locator_verts) // 9

        # 2. Rotator Widget Geometry (3D ring band + radial needle + 3D box tab)
        ring_verts = self._build_rotator_ring_vertices(segments=64, inner_r=0.90, outer_r=1.0, height=0.04)
        self._rotator_ring_vao = make_vao(ring_verts)
        self._rotator_ring_vertex_count = len(ring_verts)

        self._rotator_needle_vao = make_vao([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        self._rotator_tab_vao = make_vao(self._build_rotator_tab_vertices(cx=0.95, w=0.09, h=0.07, depth=0.06))

        # 3. Sizer Widget Arrow Geometry (along +Z)
        sizer_arrow_verts = self._build_sizer_arrow_vertices(length=14.0, shaft_r=0.7, head_len=7.0, head_r=2.5, segments=12)
        self._sizer_arrow_vao = make_vao(sizer_arrow_verts)
        self._sizer_arrow_vertex_count = len(sizer_arrow_verts)

        # 4. PickOne Handles
        # SQUARE: Outer frame + inset filled square
        self._pickone_sq_frame_vao = make_vao([
            [-0.5, -0.5, 0.0], [0.5, -0.5, 0.0], [0.5, 0.5, 0.0], [-0.5, 0.5, 0.0],
        ])
        self._pickone_sq_fill_vao = make_vao([
            [-0.26, -0.26, 0.0], [0.26, -0.26, 0.0], [0.26, 0.26, 0.0],
            [-0.26, -0.26, 0.0], [0.26, 0.26, 0.0], [-0.26, 0.26, 0.0],
        ])

        # DIAMOND: Elongated diamond rhombus shape
        self._pickone_dia_frame_vao = make_vao([
            [0.0, 0.55, 0.0], [0.28, 0.0, 0.0], [0.0, -0.55, 0.0], [-0.28, 0.0, 0.0],
        ])
        self._pickone_dia_fill_vao = make_vao([
            [0.0, 0.55, 0.0], [0.28, 0.0, 0.0], [0.0, -0.55, 0.0],
            [0.0, 0.55, 0.0], [0.0, -0.55, 0.0], [-0.28, 0.0, 0.0],
        ])

        # CIRCLE: Outer ring (radius 0.5) + concentric inner disc (radius 0.3)
        segments = 48
        circle = [[0.5 * math.cos(2.0 * math.pi * i / segments), 0.5 * math.sin(2.0 * math.pi * i / segments), 0.0] for i in range(segments)]
        self._circle_vao = make_vao(circle)
        self._circle_count = segments

        circle_inner = [[0.0, 0.0, 0.0]] + [
            [0.30 * math.cos(2.0 * math.pi * i / segments), 0.30 * math.sin(2.0 * math.pi * i / segments), 0.0]
            for i in range(segments + 1)
        ]
        self._circle_fill_vao = make_vao(circle_inner)
        self._circle_fill_count = len(circle_inner)

    def _render_widgets(self, view, proj):
        """Draw all collected preview widgets."""
        from OpenGL import GL
        if not self._gizmo_program:
            return
        prog = self._gizmo_program
        GL.glUseProgram(prog)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uView"), 1, GL.GL_FALSE, view)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uProjection"), 1, GL.GL_FALSE, proj)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        try:
            GL.glLineWidth(2.0)
        except Exception:
            pass
        for w in self._widget_infos:
            try:
                wtype = w.get("type")
                if wtype == "locator":
                    self._draw_locator_widget(view, proj, w)
                    GL.glUseProgram(prog)
                    GL.glDisable(GL.GL_DEPTH_TEST)
                elif wtype == "sizer":
                    self._draw_sizer_widget(prog, w)
                elif wtype == "rotator":
                    self._draw_rotator_widget(prog, w)
                elif wtype == "pickone":
                    self._draw_pickone_widget(prog, w)
            except Exception:
                pass
        GL.glBindVertexArray(0)
        GL.glEnable(GL.GL_DEPTH_TEST)

    def _render_paths(self, view, proj):
        """Draw PlaceOnPath spline curves and control points in the viewport."""
        from OpenGL import GL
        if not self._path_infos or not self._wireframe_program:
            return

        prog = self._wireframe_program
        GL.glUseProgram(prog)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uView"), 1, GL.GL_FALSE, view)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uProjection"), 1, GL.GL_FALSE, proj)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uModel"), 1, GL.GL_FALSE, SOURCE2_TO_GL)

        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        for path_info in self._path_infos:
            path_id = path_info.get("id", 0)
            is_selected = (self._selected_id == path_id)
            curve = path_info.get("curve", [])

            # 1. Spline Curve Line
            if len(curve) >= 2:
                color = np.array([0.15, 0.95, 1.0] if is_selected else [0.95, 0.60, 0.20], dtype=np.float32)
                GL.glUniform3fv(GL.glGetUniformLocation(prog, "uColor"), 1, color)
                try:
                    GL.glLineWidth(3.0 if is_selected else 2.0)
                except Exception:
                    pass
                curve_arr = np.array(curve, dtype=np.float32)
                self._draw_dynamic_verts(curve_arr, GL.GL_LINE_STRIP)

            # 2. Control Point Markers (small 3D cross / diamond at each control point)
            ctrl_pts = path_info.get("control_points", [])
            if ctrl_pts:
                marker_color = np.array([0.25, 1.0, 1.0] if is_selected else [1.0, 0.75, 0.30], dtype=np.float32)
                GL.glUniform3fv(GL.glGetUniformLocation(prog, "uColor"), 1, marker_color)
                cross_lines = []
                s = 4.0
                for pt in ctrl_pts:
                    px, py, pz = float(pt[0]), float(pt[1]), float(pt[2])
                    cross_lines.extend([
                        [px - s, py, pz], [px + s, py, pz],
                        [px, py - s, pz], [px, py + s, pz],
                        [px, py, pz - s], [px, py, pz + s],
                    ])
                if cross_lines:
                    self._draw_dynamic_verts(np.array(cross_lines, dtype=np.float32), GL.GL_LINES)

        GL.glBindVertexArray(0)

    def _set_widget_uniforms(self, prog, model_matrix, color, alpha=1.0):
        from OpenGL import GL
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uModel"), 1, GL.GL_FALSE, model_matrix)
        GL.glUniform3fv(GL.glGetUniformLocation(prog, "uColor"), 1, np.asarray(color, dtype=np.float32))
        GL.glUniform1f(GL.glGetUniformLocation(prog, "uAlpha"), float(alpha))

    def _draw_locator_widget(self, view, proj, w):
        """Draw 3D faceted locator matching Hammer 5 reference visuals."""
        from OpenGL import GL
        if not self._locator_program or not self._locator_vao:
            return
        pos = w.get("position", [0.0, 0.0, 0.0])
        rot = w.get("rotation", [0.0, 0.0, 0.0])
        size = float(w.get("scale", 1.0)) * 8.0
        model = (
            scale_matrix(size, size, size)
            @ rotation_matrix_euler(*rot)
            @ translation_matrix(*pos)
            @ SOURCE2_TO_GL
        )
        norm_mat = safe_normal_matrix(model)

        prog = self._locator_program
        GL.glUseProgram(prog)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uModel"), 1, GL.GL_FALSE, model)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uView"), 1, GL.GL_FALSE, view)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog, "uProjection"), 1, GL.GL_FALSE, proj)
        GL.glUniformMatrix3fv(GL.glGetUniformLocation(prog, "uNormalMatrix"), 1, GL.GL_FALSE, norm_mat)
        GL.glUniform3fv(GL.glGetUniformLocation(prog, "uCameraPos"), 1, self.camera.position)
        GL.glUniform1f(GL.glGetUniformLocation(prog, "uAlpha"), 1.0)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glBindVertexArray(self._locator_vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._locator_vertex_count)
        GL.glBindVertexArray(0)

    def _draw_sizer_widget(self, prog, w):
        """Draw adaptive sizer (3D volume box, 2D plane, or 1D line) with face handle arrows."""
        from OpenGL import GL
        min_b = w.get("min_bounds", [0.0, 0.0, 0.0])
        max_b = w.get("max_bounds", [0.0, 0.0, 0.0])
        handles = w.get("handles", {})
        active_axes = w.get("active_axes", {"x": True, "y": True, "z": True})
        world_matrix = w.get("world_matrix", np.eye(4, dtype=np.float32))

        min_x, min_y, min_z = float(min_b[0]), float(min_b[1]), float(min_b[2])
        max_x, max_y, max_z = float(max_b[0]), float(max_b[1]), float(max_b[2])

        active_count = sum(1 for a in ("x", "y", "z") if active_axes.get(a))
        if active_count == 0:
            return

        model = world_matrix @ SOURCE2_TO_GL

        fill_color = [0.22, 0.65, 0.95]
        outline_color = [0.35, 0.85, 1.0]

        # 1. Geometry rendering
        if active_count == 3:
            c000 = [min_x, min_y, min_z]
            c100 = [max_x, min_y, min_z]
            c110 = [max_x, max_y, min_z]
            c010 = [min_x, max_y, min_z]
            c001 = [min_x, min_y, max_z]
            c101 = [max_x, min_y, max_z]
            c111 = [max_x, max_y, max_z]
            c011 = [min_x, max_y, max_z]

            faces = [
                c000, c100, c110, c000, c110, c010,
                c001, c011, c111, c001, c111, c101,
                c000, c001, c101, c000, c101, c100,
                c010, c110, c111, c010, c111, c011,
                c000, c010, c011, c000, c011, c001,
                c100, c101, c111, c100, c111, c110,
            ]
            face_arr = np.array(faces, dtype=np.float32)

            lines = [
                c000, c100, c100, c110, c110, c010, c010, c000,
                c001, c101, c101, c111, c111, c011, c011, c001,
                c000, c001, c100, c101, c110, c111, c010, c011,
            ]
            line_arr = np.array(lines, dtype=np.float32)

            self._set_widget_uniforms(prog, model, fill_color, alpha=0.30)
            self._draw_dynamic_verts(face_arr, GL.GL_TRIANGLES)

            self._set_widget_uniforms(prog, model, outline_color, alpha=0.95)
            self._draw_dynamic_verts(line_arr, GL.GL_LINES)

        elif active_count == 2:
            if not active_axes.get("x"):
                p0, p1, p2, p3 = [min_x, min_y, min_z], [min_x, max_y, min_z], [min_x, max_y, max_z], [min_x, min_y, max_z]
            elif not active_axes.get("y"):
                p0, p1, p2, p3 = [min_x, min_y, min_z], [max_x, min_y, min_z], [max_x, min_y, max_z], [min_x, min_y, max_z]
            else:
                p0, p1, p2, p3 = [min_x, min_y, min_z], [max_x, min_y, min_z], [max_x, max_y, min_z], [min_x, max_y, min_z]

            faces = [p0, p1, p2, p0, p2, p3]
            lines = [p0, p1, p1, p2, p2, p3, p3, p0]
            self._set_widget_uniforms(prog, model, fill_color, alpha=0.35)
            self._draw_dynamic_verts(np.array(faces, dtype=np.float32), GL.GL_TRIANGLES)
            self._set_widget_uniforms(prog, model, outline_color, alpha=0.95)
            self._draw_dynamic_verts(np.array(lines, dtype=np.float32), GL.GL_LINES)

        elif active_count == 1:
            if active_axes.get("x"):
                p0, p1 = [min_x, 0.0, 0.0], [max_x, 0.0, 0.0]
            elif active_axes.get("y"):
                p0, p1 = [0.0, min_y, 0.0], [0.0, max_y, 0.0]
            else:
                p0, p1 = [0.0, 0.0, min_z], [0.0, 0.0, max_z]
            lines = [p0, p1]
            self._set_widget_uniforms(prog, model, outline_color, alpha=1.0)
            self._draw_dynamic_verts(np.array(lines, dtype=np.float32), GL.GL_LINES)

        # 2. Draw Handle Arrows on configured faces
        mid_x = (min_x + max_x) * 0.5
        mid_y = (min_y + max_y) * 0.5
        mid_z = (min_z + max_z) * 0.5

        arrow_defs = [
            ("max_x", [max_x, mid_y, mid_z], rotation_matrix_euler(90.0, 0.0, 0.0), [0.90, 0.15, 0.15]),
            ("min_x", [min_x, mid_y, mid_z], rotation_matrix_euler(-90.0, 0.0, 0.0), [0.90, 0.15, 0.15]),
            ("max_y", [mid_x, max_y, mid_z], rotation_matrix_euler(0.0, 0.0, -90.0), [0.15, 0.85, 0.20]),
            ("min_y", [mid_x, min_y, mid_z], rotation_matrix_euler(0.0, 0.0, 90.0), [0.15, 0.85, 0.20]),
            ("max_z", [mid_x, mid_y, max_z], np.eye(4, dtype=np.float32), [0.15, 0.35, 0.95]),
            ("min_z", [mid_x, mid_y, min_z], rotation_matrix_euler(180.0, 0.0, 0.0), [0.15, 0.35, 0.95]),
        ]

        for hkey, hpos, hrot, hcolor in arrow_defs:
            if handles.get(hkey):
                arrow_model = (
                    hrot
                    @ translation_matrix(*hpos)
                    @ world_matrix
                    @ SOURCE2_TO_GL
                )
                self._set_widget_uniforms(prog, arrow_model, hcolor, alpha=1.0)
                GL.glBindVertexArray(self._sizer_arrow_vao)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._sizer_arrow_vertex_count)

    def _draw_rotator_widget(self, prog, w):
        """Draw 3D rotator with wide ring band, initial angle spoke needle, and handle tab."""
        from OpenGL import GL
        pos = w.get("position", [0.0, 0.0, 0.0])
        radius = float(w.get("radius", 16.0))
        axis = w.get("axis", [0.0, 0.0, 1.0])
        angle_deg = float(w.get("angle", 0.0))
        color = w.get("color", [0.72, 0.74, 0.48])

        align = self._rotation_align_z_to(axis)
        base_model = (
            scale_matrix(radius, radius, radius)
            @ align
            @ translation_matrix(*pos)
            @ SOURCE2_TO_GL
        )

        # 1. Draw solid 3D ring band
        self._set_widget_uniforms(prog, base_model, color, alpha=0.88)
        GL.glBindVertexArray(self._rotator_ring_vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._rotator_ring_vertex_count)

        # 2. Needle spoke line at initial angle
        needle_rot = rotation_matrix_euler(0.0, 0.0, angle_deg)
        needle_model = needle_rot @ base_model
        yellow = [0.95, 0.90, 0.10]
        self._set_widget_uniforms(prog, needle_model, yellow, alpha=1.0)
        GL.glBindVertexArray(self._rotator_needle_vao)
        GL.glDrawArrays(GL.GL_LINES, 0, 2)

        # 3. Handle marker tab at the ring edge (3D box, 12 triangles = 36 verts)
        self._set_widget_uniforms(prog, needle_model, yellow, alpha=0.95)
        GL.glBindVertexArray(self._rotator_tab_vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 36)

    def _draw_pickone_widget(self, prog, w):
        """Draw PickOne billboard handle with camera-distance adaptive scaling."""
        from OpenGL import GL
        pos = w.get("position", [0.0, 0.0, 0.0])
        size = float(w.get("size", 8.0))
        color = w.get("color", [0.6, 0.6, 0.6])
        shape = str(w.get("shape", "SQUARE")).upper()

        gl_pos = (SOURCE2_TO_GL.T @ np.array([pos[0], pos[1], pos[2], 1.0], dtype=np.float32))[:3]
        dist = float(np.linalg.norm(self.camera.position - gl_pos))
        screen_scale = max(dist * 0.013, 1.6) * (size / 8.0)

        R = np.asarray(self.camera.right_vector, dtype=np.float32)
        U = np.asarray(self.camera.up_vector, dtype=np.float32)
        F = np.cross(R, U)
        model = np.eye(4, dtype=np.float32)
        model[0, :3] = R * screen_scale
        model[1, :3] = U * screen_scale
        model[2, :3] = F * screen_scale
        model[3, :3] = gl_pos

        if shape == "CIRCLE":
            fill_vao, fill_mode, fill_count = self._circle_fill_vao, GL.GL_TRIANGLE_FAN, self._circle_fill_count
            line_vao, line_count = self._circle_vao, self._circle_count
        elif shape == "DIAMOND":
            fill_vao, fill_mode, fill_count = self._pickone_dia_fill_vao, GL.GL_TRIANGLES, 6
            line_vao, line_count = self._pickone_dia_frame_vao, 4
        else:  # SQUARE (default)
            fill_vao, fill_mode, fill_count = self._pickone_sq_fill_vao, GL.GL_TRIANGLES, 6
            line_vao, line_count = self._pickone_sq_frame_vao, 4

        # Inset solid fill + crisp outline frame
        self._set_widget_uniforms(prog, model, color, alpha=0.55)
        GL.glBindVertexArray(fill_vao)
        GL.glDrawArrays(fill_mode, 0, fill_count)
        self._set_widget_uniforms(prog, model, color, alpha=1.0)
        GL.glBindVertexArray(line_vao)
        GL.glDrawArrays(GL.GL_LINE_LOOP, 0, line_count)

    @staticmethod
    def _rotation_align_z_to(axis):
        """Row-vector 4x4 rotating Source 2 +Z onto ``axis`` (orients rotator rings)."""
        a = np.array([float(axis[0]), float(axis[1]), float(axis[2])], dtype=np.float64)
        n = np.linalg.norm(a)
        M = np.eye(4, dtype=np.float32)
        if n < 1e-8:
            return M
        a = a / n
        z = np.array([0.0, 0.0, 1.0])
        v = np.cross(z, a)
        c = float(np.dot(z, a))
        s = float(np.linalg.norm(v))
        if s < 1e-8:
            if c < 0.0:  # antiparallel: flip 180 degrees about X
                M[:3, :3] = np.diag([1.0, -1.0, -1.0]).astype(np.float32)
            return M
        vx = np.array([[0.0, -v[2], v[1]],
                       [v[2], 0.0, -v[0]],
                       [-v[1], v[0], 0.0]])
        R = np.eye(3) + vx + vx @ vx * ((1.0 - c) / (s * s))
        M[:3, :3] = R.T.astype(np.float32)  # transpose for the row-vector chain
        return M
