"""
OpenGL-based 3D render area for the SmartProp Editor.
Handles grid rendering, 3D model rendering with textures, click-to-select color picking,
and W/E/R transform gizmo interactions.
"""
import math
import numpy as np

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication

from src.editors.smartprop_editor.viewport_3d.camera import Camera, SOURCE2_TO_GL, translation_matrix, rotation_matrix_euler, scale_matrix, decompose_trs
from src.editors.smartprop_editor.viewport_3d.gizmo import Gizmo, GizmoMode, GizmoAxis
from src.editors.smartprop_editor.viewport_3d.mesh_cache import MeshCache
from src.editors.smartprop_editor.viewport_3d.shaders import (
    MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER,
    PICKING_VERTEX_SHADER, PICKING_FRAGMENT_SHADER,
    GRID_VERTEX_SHADER, GRID_FRAGMENT_SHADER,
    GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER,
    WIREFRAME_VERTEX_SHADER, WIREFRAME_FRAGMENT_SHADER,
    OUTLINE_VERTEX_SHADER, OUTLINE_FRAGMENT_SHADER
)


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


class SmartProp3DRenderArea(QOpenGLWidget):
    elementClicked = Signal(int)

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Request a multisampled (anti-aliased) framebuffer.  This must be set
        # before the widget's GL context is created; glEnable(GL_MULTISAMPLE) in
        # initializeGL is a no-op without a multisampled surface behind it.  The
        # sample count follows the SmartProp Editor's Anti-aliasing setting.
        from src.editors.smartprop_editor.viewport_3d.gl_settings import (
            make_viewport_surface_format, get_viewport_msaa_samples,
        )
        self._msaa_samples = get_viewport_msaa_samples()
        self.setFormat(make_viewport_surface_format(self._msaa_samples))

        # Camera & Interaction
        self.camera = Camera()
        self.gizmo = Gizmo()
        self.mesh_cache = MeshCache(self)
        self.mesh_cache.model_ready.connect(self.update)

        self._last_mouse_pos = QPointF()
        self._action = None  # 'orbit' | 'pan'
        self._selected_id = 0

        # How the currently-selected element's scale is stored, decided when the
        # gizmo's axis availability is computed: "vector" (per-axis m_vModelScale),
        # "uniform" (single m_flUniformModelScale / Scale-op m_flScale), or None
        # (no scale property — scale axes are grayed and not created on drag).
        self._scale_source = None

        # View Settings
        self.shading_mode = "textured"  # "textured" | "solid" | "wireframe"
        self.translucency_enabled = True  # when False, BLEND materials draw opaque
        self.coordinate_space = "World"
        self.snapping_enabled = False
        self.grid_step = 8.0
        self.rotation_step = 15.0
        self.display_groups = True

        # Scene Data (populated from document tree)
        self._model_infos = {}  # id -> info dict

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

        self._grid_vao = 0
        self._grid_vbo = 0
        self._box_vao = 0
        self._box_vbo = 0
        self._dot_vao = 0
        self._dot_vbo = 0
        self._fs_vao = 0  # empty VAO for the fullscreen-triangle outline pass

        # Selection outline appearance.  The selected element's silhouette is
        # traced with a constant-width outline instead of a full-surface fill.
        self.outline_enabled = True
        self.outline_color = (0.15, 0.95, 1.0)  # cyan, matching the app's selection accent
        self.outline_thickness = 3.0            # logical pixels (scaled by device ratio)

        # Offscreen single-sample mask FBO for the selection silhouette.  Kept
        # separate from the picking FBO: this one owns a *texture* colour target
        # (the outline pass samples it), whereas picking reads back from a
        # renderbuffer.
        self._mask_fbo = 0
        self._mask_color_tex = 0
        self._mask_depth_rbo = 0
        self._mask_fbo_w = 0
        self._mask_fbo_h = 0

        # Dedicated single-sample framebuffer for color-ID picking.  The visible
        # surface is multisampled (MSAA), and glReadPixels is invalid on a
        # multisampled buffer — plus MSAA would blend neighbouring IDs at edges
        # and corrupt the lookup.  Picking therefore renders into this private
        # non-multisampled FBO instead.
        self._pick_fbo = 0
        self._pick_color_rbo = 0
        self._pick_depth_rbo = 0
        self._pick_fbo_w = 0
        self._pick_fbo_h = 0

    def initializeGL(self):
        from OpenGL import GL

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

        # Compile Shader Programs
        self._model_program = link_program(MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER)
        self._picking_program = link_program(PICKING_VERTEX_SHADER, PICKING_FRAGMENT_SHADER)
        self._grid_program = link_program(GRID_VERTEX_SHADER, GRID_FRAGMENT_SHADER)
        self._gizmo_program = link_program(GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER)
        self._wireframe_program = link_program(WIREFRAME_VERTEX_SHADER, WIREFRAME_FRAGMENT_SHADER)
        self._outline_program = link_program(OUTLINE_VERTEX_SHADER, OUTLINE_FRAGMENT_SHADER)

        # Empty VAO required by core profile to issue the attribute-less
        # fullscreen-triangle draw in the selection outline pass.
        self._fs_vao = GL.glGenVertexArrays(1)

        # Initialize Grid Geometry
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

        # Initialize Unit Wireframe Box Geometry for fallbacks
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

        # Initialize Solid Dot Geometry for empty elements
        h_dot = 0.5
        dot_verts = np.array([
            [-h_dot, -h_dot,  h_dot], [ h_dot, -h_dot,  h_dot], [ h_dot,  h_dot,  h_dot],
            [-h_dot, -h_dot,  h_dot], [ h_dot,  h_dot,  h_dot], [-h_dot,  h_dot,  h_dot],
            [-h_dot, -h_dot, -h_dot], [-h_dot,  h_dot, -h_dot], [ h_dot,  h_dot, -h_dot],
            [-h_dot, -h_dot, -h_dot], [ h_dot,  h_dot, -h_dot], [ h_dot, -h_dot, -h_dot],
            [-h_dot,  h_dot, -h_dot], [-h_dot,  h_dot,  h_dot], [ h_dot,  h_dot,  h_dot],
            [-h_dot,  h_dot, -h_dot], [ h_dot,  h_dot,  h_dot], [ h_dot,  h_dot, -h_dot],
            [-h_dot, -h_dot, -h_dot], [ h_dot, -h_dot, -h_dot], [ h_dot, -h_dot,  h_dot],
            [-h_dot, -h_dot, -h_dot], [ h_dot, -h_dot,  h_dot], [-h_dot, -h_dot,  h_dot],
            [ h_dot, -h_dot, -h_dot], [ h_dot,  h_dot, -h_dot], [ h_dot,  h_dot,  h_dot],
            [ h_dot, -h_dot, -h_dot], [ h_dot,  h_dot,  h_dot], [ h_dot, -h_dot,  h_dot],
            [-h_dot, -h_dot, -h_dot], [-h_dot, -h_dot,  h_dot], [-h_dot,  h_dot,  h_dot],
            [-h_dot, -h_dot, -h_dot], [-h_dot,  h_dot,  h_dot], [-h_dot,  h_dot, -h_dot]
        ], dtype=np.float32)

        self._dot_vao = GL.glGenVertexArrays(1)
        self._dot_vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self._dot_vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._dot_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, dot_verts.nbytes, dot_verts, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 12, GL.ctypes.c_void_p(0))
        GL.glEnableVertexAttribArray(0)
        GL.glBindVertexArray(0)

        # The two horizontal ground axes (Source X red / Source Y green) are drawn
        # directly by the grid shader as infinite lines that fade with distance,
        # Blender-style.  The vertical Source Z (up) axis is intentionally omitted.

        # Initialize Gizmo Geometry
        self.gizmo.init_geometry()

    def resizeGL(self, w, h):
        from OpenGL import GL
        GL.glViewport(0, 0, w, h)
        self.camera.aspect = w / h if h > 0 else 1.0

    def paintGL(self):
        from OpenGL import GL

        # Perform picking pass first if flagged
        if self._perform_pick_flag:
            self._do_picking_pass()
            self._perform_pick_flag = False

        # Normal Render Pass
        GL.glClearColor(0.11, 0.11, 0.11, 1.0)
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

        # 2. Render Models
        self._render_scene_models(view, proj, cam_pos, picking=False)

        # 2b. Selection outline overlay.  Composited here — after the models but
        # before the gizmo — because the gizmo clears the depth buffer and draws
        # on top; running the outline first keeps it from being wiped or occluded.
        if self.outline_enabled and self._selected_id in self._model_infos:
            self._render_selection_outline(view, proj, cam_pos)

        # 3. Render Gizmo
        self.gizmo.render(self._gizmo_program, view, proj, cam_pos)

    def _render_scene_models(self, view, proj, cam_pos, picking=False, mask_id=None):
        from OpenGL import GL

        # ``mask_id`` renders a selection silhouette: every element is drawn with
        # the flat picking shader, but the element whose id == mask_id is painted
        # solid white and all others black, so the resulting buffer is that one
        # element's depth-occluded silhouette.  It shares the picking shader/geometry
        # path, hence the combined ``use_pick`` flag below.
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

        for eid, info in self._model_infos.items():
            pos = info.get("position", [0.0, 0.0, 0.0])
            rot = info.get("rotation", [0.0, 0.0, 0.0])
            scale = info.get("scale", [1.0, 1.0, 1.0])
            model_path = info.get("path", "")

            # Build the Source-space model matrix, then convert to GL.
            #
            # These helpers store transforms row-vector style (translation in the
            # last row), and matrices are handed to GL untransposed (GL_FALSE), so
            # GL reads each as its transpose.  With the shader computing uModel * v,
            # the effective order applied to a vertex is scale -> rotate -> translate
            # (all in Source Z-up space) -> SOURCE2_TO_GL (Source -> GL Y-up).
            #
            # SOURCE2_TO_GL is already written pre-transposed for exactly this
            # GL_FALSE row-vector chain, so it is used as-is here (NOT .T).  Adding
            # a .T flips Source Z-up to GL -Y, sinking models below the grid and
            # mirroring the scene.
            model_matrix = (
                scale_matrix(*scale)
                @ rotation_matrix_euler(*rot)
                @ translation_matrix(*pos)
                @ SOURCE2_TO_GL
            )

            is_dot = info.get("is_dot", False)
            if is_dot:
                if not self.display_groups:
                    continue
                if use_pick:
                    set_pick_color(eid)
                    dot_size = 12.0
                    dot_matrix = scale_matrix(dot_size, dot_size, dot_size) @ model_matrix
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._picking_program, "uModel"), 1, GL.GL_FALSE, dot_matrix)
                    GL.glBindVertexArray(self._dot_vao)
                    GL.glDrawArrays(GL.GL_TRIANGLES, 0, 36)
                    GL.glBindVertexArray(0)
                else:
                    is_selected = (eid == self._selected_id)
                    GL.glUseProgram(self._wireframe_program)
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._wireframe_program, "uView"), 1, GL.GL_FALSE, view)
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._wireframe_program, "uProjection"), 1, GL.GL_FALSE, proj)
                    
                    dot_size = 12.0
                    dot_matrix = scale_matrix(dot_size, dot_size, dot_size) @ model_matrix
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._wireframe_program, "uModel"), 1, GL.GL_FALSE, dot_matrix)
                    
                    # Color: orange/brown for groups, cyan for selected
                    dot_color = np.array([0.0, 0.85, 0.85] if is_selected else [0.8, 0.4, 0.1], dtype=np.float32)
                    GL.glUniform3fv(GL.glGetUniformLocation(self._wireframe_program, "uColor"), 1, dot_color)
                    
                    GL.glBindVertexArray(self._dot_vao)
                    GL.glDrawArrays(GL.GL_TRIANGLES, 0, 36)
                    
                    if is_selected:
                        highlight_size = 14.0
                        highlight_matrix = scale_matrix(highlight_size, highlight_size, highlight_size) @ model_matrix
                        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._wireframe_program, "uModel"), 1, GL.GL_FALSE, highlight_matrix)
                        GL.glBindVertexArray(self._box_vao)
                        GL.glDrawArrays(GL.GL_LINES, 0, 24)
                        
                    GL.glBindVertexArray(0)
                    GL.glUseProgram(self._model_program)
                continue

            # Query GPU mesh
            gpu_mesh = self.mesh_cache.get_gpu_mesh(model_path)

            if use_pick:
                # Flat id colour (picking) or white/black silhouette (mask mode).
                set_pick_color(eid)

                if gpu_mesh:
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._picking_program, "uModel"), 1, GL.GL_FALSE, model_matrix)
                    GL.glBindVertexArray(gpu_mesh.vao)
                    GL.glDrawElements(GL.GL_TRIANGLES, gpu_mesh.index_count, GL.GL_UNSIGNED_INT, None)
                else:
                    # Draw picking box placeholder
                    self._draw_box_geometry(model_matrix, is_picking=True)
            else:
                is_selected = (eid == self._selected_id)

                if gpu_mesh:
                    # Normal matrix is transpose of inverse of the 3x3 model matrix.
                    norm_mat = np.linalg.inv(model_matrix[:3, :3]).T
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

                    # Box color
                    box_color = np.array([0.0, 0.85, 0.85] if is_selected else [0.4, 0.6, 0.9], dtype=np.float32)
                    GL.glUniform3fv(GL.glGetUniformLocation(self._wireframe_program, "uColor"), 1, box_color)

                    self._draw_box_geometry(model_matrix, is_picking=False)

                    # Restore model program
                    GL.glUseProgram(self._model_program)

        # Second pass: translucent submeshes.  Sorted far-to-near across objects,
        # depth writes off, and each submesh drawn in two culled sub-passes — its
        # far (back) faces, then its near (front) faces over them.  Without the
        # back/front split, unsorted double-sided blending lets a mesh's own
        # interior/back faces punch through the surface, which reads as scrambled,
        # "distorted" geometry.  Flipping the normal on back faces (in the shader)
        # keeps both sides shaded correctly.
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

    # ------------------------------------------------------------------
    # Material binding / submesh drawing
    # ------------------------------------------------------------------
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

        def bind_tex(unit, tex, sampler_name, has_name):
            GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
            GL.glBindTexture(GL.GL_TEXTURE_2D, tex if tex else 0)
            GL.glUniform1i(loc(sampler_name), unit)
            GL.glUniform1i(loc(has_name), 1 if tex else 0)

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

    # ------------------------------------------------------------------
    # Selection outline
    # ------------------------------------------------------------------
    def _ensure_mask_fbo(self, w, h):
        """Create (or resize) the single-sample selection-mask framebuffer.

        Colour is a sampleable texture (the outline pass reads it); depth is a
        renderbuffer so the silhouette is correctly occluded by nearer geometry.
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
        """Draw a silhouette outline around the currently selected mesh.

        Two passes: (1) render the selected element's depth-occluded silhouette as
        white-on-black into the mask FBO; (2) a fullscreen pass dilates that mask
        and paints the ring just outside the silhouette over the visible scene.

        Only loaded meshes are outlined here — group dots and not-yet-loaded model
        placeholders keep their own wireframe-box selection markers.
        """
        from OpenGL import GL

        sel = self._model_infos.get(self._selected_id)
        if not sel or sel.get("is_dot"):
            return
        if self.mesh_cache.get_gpu_mesh(sel.get("path", "")) is None:
            return

        # Work in device pixels so the mask lines up with the HiDPI framebuffer.
        dpr = self.devicePixelRatioF()
        fb_w = max(1, int(round(self.width() * dpr)))
        fb_h = max(1, int(round(self.height() * dpr)))
        self._ensure_mask_fbo(fb_w, fb_h)

        # ---- Pass 1: silhouette mask -----------------------------------------
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._mask_fbo)
        GL.glViewport(0, 0, fb_w, fb_h)
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glDisable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_TRUE)
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

    # ------------------------------------------------------------------
    # Camera fitting
    # ------------------------------------------------------------------
    def _compute_bounds(self, infos):
        """Return the GL-space AABB (min, max, has_bounds) enclosing ``infos``.

        ``infos`` is an iterable of element info dicts (a subset of
        ``self._model_infos.values()``).  Meshes use their transformed AABB;
        dots and not-yet-loaded models fall back to a small box at their origin.
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
            is_dot = info.get("is_dot", False)
            if is_dot:
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

    def fit_view(self):
        """Zoom and position camera to fit all models in scene."""
        if not self._model_infos:
            return
        bbox_min, bbox_max, has_bounds = self._compute_bounds(self._model_infos.values())
        if has_bounds:
            self.camera.fit_to_bounds(bbox_min, bbox_max)
            self.update()

    def frame_selection(self):
        """Frame the camera on the current selection (F key).

        Fits the selected element if one is selected; otherwise frames the whole
        scene, matching the behaviour users expect from Blender/Hammer.
        """
        sel = self._model_infos.get(self._selected_id)
        if sel is not None:
            bbox_min, bbox_max, has_bounds = self._compute_bounds([sel])
            if has_bounds:
                self.camera.fit_to_bounds(bbox_min, bbox_max)
                self.update()
                return
        # Nothing selected (or selection has no bounds) — frame everything.
        self.fit_view()

    def update_viewport(self):
        """Rebuild the scene models list from the current document tree."""
        self._model_infos.clear()

        if not self.document:
            self.update()
            return

        tree_widget = None
        if hasattr(self.document, 'ui') and hasattr(self.document.ui, 'tree_hierarchy_widget'):
            tree_widget = self.document.ui.tree_hierarchy_widget
        if tree_widget is None:
            self.update()
            return

        models_info = []
        self._traverse_tree(tree_widget.invisibleRootItem(), models_info)

        for info in models_info:
            eid = info.get("id", 0)
            self._model_infos[eid] = info

        # Unload any cached models the hierarchy no longer references so the
        # viewport's memory footprint follows the tree (GPU frees happen on the
        # next paint, inside the GL context).
        referenced_paths = {
            info.get("path", "") for info in self._model_infos.values() if info.get("path")
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

    def highlight_element(self, element_id: int):
        """Select/Highlight element and reposition gizmo."""
        self._selected_id = element_id
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

    # ------------------------------------------------------------------
    # Mouse & Keyboard Event Handlers
    # ------------------------------------------------------------------
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
                # Snapshot document data before dragging for undo history
                if self.document and hasattr(self.document, "_gizmo_pre_drag_data"):
                    item = self.document.ui.tree_hierarchy_widget.currentItem()
                    if item:
                        from src.common import fast_deepcopy
                        self.document._gizmo_pre_drag_data = fast_deepcopy(item.data(0, Qt.UserRole))
                self.update()
                return

        # Blender-style navigation: MMB orbits, Shift+MMB pans, LMB selects
        if event.button() == Qt.LeftButton:
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

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        self._sync_gizmo_settings(event)
        dx = pos.x() - self._last_mouse_pos.x()
        dy = pos.y() - self._last_mouse_pos.y()

        # Handle gizmo dragging
        if self.gizmo.is_dragging:
            w, h = self.width(), self.height()
            view = self.camera.view_matrix
            proj = self.camera.projection_matrix
            cam_pos = self.camera.position

            delta = self.gizmo.update_drag(
                (pos.x(), pos.y()), view, proj, w, h, cam_pos
            )

            if delta and self.document:
                # Apply dragging transform immediately to tree item
                item = self.document.ui.tree_hierarchy_widget.currentItem()
                if item and self._selected_id in self._model_infos:
                    from src.common import fast_deepcopy
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

                    # 2. Convert to local space
                    M_parent_inv = np.linalg.inv(parent_world_matrix)
                    M_new_local = M_new_world @ M_parent_inv

                    # 3. Decompose to get target local values
                    target_local_pos, target_local_rot, target_local_scale = decompose_trs(M_new_local)

                    # 4. Apply to modifiers
                    if "position" in delta:
                        mod = self._find_or_create_modifier(data, "CSmartPropOperation_Translate", "m_vPosition")
                        avail = self._vector_axis_availability(mod.get("m_vPosition"))
                        axes = [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]
                        for i, axis in enumerate(axes):
                            if avail.get(axis, True):
                                self._set_vector_component(mod, "m_vPosition", i, target_local_pos[i], target_local_pos)
                    elif "rotation" in delta:
                        mod = self._find_or_create_modifier(data, "CSmartPropOperation_Rotate", "m_vRotation")
                        avail = self._vector_axis_availability(mod.get("m_vRotation"))
                        axes = [GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z]
                        for i, axis in enumerate(axes):
                            if avail.get(axis, True):
                                self._set_vector_component(mod, "m_vRotation", i, target_local_rot[i], target_local_rot)
                    elif "scale" in delta and (axis_idx is not None or is_center):
                        self._apply_scale_delta(data, axis_idx, target_local_scale, uniform=is_center)

                    item.setData(0, Qt.UserRole, data)

                    # 5. Reconstruct the actual world transform from what was written
                    actual_local_pos, actual_local_rot, actual_local_scale = self._get_local_transform(data)
                    M_actual_local = (
                        scale_matrix(*actual_local_scale)
                        @ rotation_matrix_euler(*actual_local_rot)
                        @ translation_matrix(*actual_local_pos)
                    )
                    M_actual_world = M_actual_local @ parent_world_matrix
                    actual_world_pos, actual_world_rot, actual_world_scale = decompose_trs(M_actual_world)

                    info["position"] = actual_world_pos
                    info["rotation"] = actual_world_rot
                    info["scale"] = actual_world_scale

                    # Update all descendant transforms immediately so they follow the group smoothly
                    self._update_subtree_transforms(item, M_actual_world)

                    # Update gizmo position/rotation/scale from the refreshed cache
                    self.gizmo.set_transform(info["position"], info["rotation"], info["scale"])

                    # Refresh Property panel inputs if active
                    if hasattr(self.document, "ui") and hasattr(self.document.ui, "PropertiesFrame"):
                        # Rebuild property view fields to match gizmo
                        self.document.update_property_frame_values(data)

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

        # Handle Camera
        if self._action == 'orbit':
            self.camera.orbit(dx, dy)
        elif self._action == 'pan':
            self.camera.pan(dx, dy)
        elif self._action == 'zoom':
            self.camera.zoom(-(dx - dy))

        self._last_mouse_pos = pos
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.gizmo.is_dragging:
            self.gizmo.end_drag()
            # Push changes to undo stack
            if self.document and hasattr(self.document, "_gizmo_commit_drag"):
                self.document._gizmo_commit_drag()
        self._action = None
        self.update()

    def wheelEvent(self, event):
        self.camera.zoom(event.angleDelta().y())
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_W:
            self.gizmo.set_mode(GizmoMode.TRANSLATE)
            self.update()
        elif event.key() == Qt.Key_E:
            self.gizmo.set_mode(GizmoMode.ROTATE)
            self.update()
        elif event.key() == Qt.Key_R:
            self.gizmo.set_mode(GizmoMode.SCALE)
            self.update()
        elif event.key() == Qt.Key_F:
            # Frame the current selection (or the whole scene if nothing selected).
            self.frame_selection()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Gizmo axis availability
    # ------------------------------------------------------------------
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

        if data.get("_class", "") in self._MODEL_LIKE_CLASSES:
            model_scale = data.get("m_vModelScale")
            if model_scale is not None:
                return with_center(self._vector_axis_availability(model_scale)), "vector"
            if data.get("m_flUniformModelScale") is not None:
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

    # ------------------------------------------------------------------
    # Data modifier helpers
    # ------------------------------------------------------------------
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
        ``axis_idx`` changes.  Returns the resolved [x, y, z] scale to cache.
        """
        source = self._scale_source
        if uniform:
            if source == "vector":
                # Every component is literal (guaranteed by CENTER availability);
                # write each so any non-uniform ratio is preserved.
                for i in range(3):
                    self._set_vector_component(data, "m_vModelScale", i, scale_vec[i], scale_vec)
                return list(scale_vec)
            if source == "uniform":
                self._write_uniform_scale(data, scale_vec[0])
                value = float(scale_vec[0])
                return [value, value, value]
            return list(scale_vec)

        if source == "vector":
            self._set_vector_component(data, "m_vModelScale", axis_idx, scale_vec[axis_idx], scale_vec)
            return list(scale_vec)
        if source == "uniform":
            uniform_val = float(scale_vec[axis_idx])
            self._write_uniform_scale(data, uniform_val)
            # Uniform scale drives all three axes together.
            return [uniform_val, uniform_val, uniform_val]
        # source is None: scale axes are grayed and shouldn't be draggable.
        return list(scale_vec)

    def _write_uniform_scale(self, data, value):
        """Write a single uniform scale value to whichever field the element uses."""
        value = float(value)
        if data.get("m_flUniformModelScale") is not None:
            data["m_flUniformModelScale"] = value
            return
        scale_mod = self._find_modifier(data, "CSmartPropOperation_Scale")
        if scale_mod is not None:
            scale_mod["m_flScale"] = value
        else:
            data["m_flUniformModelScale"] = value

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

    # ------------------------------------------------------------------
    # Tree traversal (extracted from old viewport_3d.py)
    # ------------------------------------------------------------------
    def _get_vector(self, val, default):
        if val is None:
            return default
        if isinstance(val, (list, tuple)):
            val_list = list(val)
            while len(val_list) < 3:
                val_list.append(0.0)
            res = []
            for x in val_list[:3]:
                if isinstance(x, dict) and "m_Expression" in x:
                    try:    res.append(float(x["m_Expression"]))
                    except: res.append(0.0)
                elif isinstance(x, dict) and "m_SourceName" in x:
                    res.append(0.0)
                else:
                    try:    res.append(float(x))
                    except: res.append(0.0)
            return res
        if hasattr(val, "get"):
            comp = val.get("m_Components")
            if comp is not None:
                return self._get_vector(comp, default)
        if hasattr(val, "X") and hasattr(val, "Y") and hasattr(val, "Z"):
            return [float(val.X), float(val.Y), float(val.Z)]
        if hasattr(val, "Pitch") and hasattr(val, "Yaw") and hasattr(val, "Roll"):
            return [float(val.Pitch), float(val.Yaw), float(val.Roll)]
        return default

    def _get_local_transform(self, data):
        """Extract local pos, rot, scale from the element's data dictionary."""
        local_pos   = [0.0, 0.0, 0.0]
        local_rot   = [0.0, 0.0, 0.0]
        local_scale = [1.0, 1.0, 1.0]

        if not isinstance(data, dict):
            return local_pos, local_rot, local_scale

        for mod in data.get("m_Modifiers", []) or []:
            if not isinstance(mod, dict):
                continue
            cls = mod.get("_class", "")
            if cls == "CSmartPropOperation_Translate" and "m_vPosition" in mod:
                comp = self._get_vector(mod["m_vPosition"], [0.0, 0.0, 0.0])
                local_pos = [local_pos[i] + comp[i] for i in range(3)]
            elif cls == "CSmartPropOperation_Rotate" and "m_vRotation" in mod:
                comp = self._get_vector(mod["m_vRotation"], [0.0, 0.0, 0.0])
                local_rot = [local_rot[i] + comp[i] for i in range(3)]
            elif cls == "CSmartPropOperation_Scale" and "m_flScale" in mod:
                try:
                    s = float(mod["m_flScale"])
                    local_scale = [local_scale[i] * s for i in range(3)]
                except Exception:
                    pass

        element_class = data.get("_class", "")
        if element_class == "CSmartPropElement_Model":
            if data.get("m_vModelScale"):
                comp = self._get_vector(data["m_vModelScale"], [1.0, 1.0, 1.0])
                local_scale = [local_scale[i] * comp[i] for i in range(3)]
            elif data.get("m_flUniformModelScale") is not None:
                try:
                    s = float(data["m_flUniformModelScale"])
                    local_scale = [local_scale[i] * s for i in range(3)]
                except Exception:
                    pass
        elif element_class in ("CSmartPropElement_ModelEntity",
                               "CSmartPropElement_PropPhysics",
                               "CSmartPropElement_PropDynamic"):
            if data.get("m_vModelScale"):
                comp = self._get_vector(data["m_vModelScale"], [1.0, 1.0, 1.0])
                local_scale = [local_scale[i] * comp[i] for i in range(3)]

        return local_pos, local_rot, local_scale

    def _load_and_traverse_nested_vsmart(self, smartprop_path, models_list, world_matrix, context_addon=None):
        import os
        import re
        from src.settings.main import get_addon_name, get_cs2_path
        cs2_path = get_cs2_path()
        addon = context_addon or get_addon_name()
        if cs2_path and addon:
            addon_match = re.search(r'/csgo_addons/([^/]+)/(.*)$', '/' + smartprop_path.replace('\\', '/'), re.IGNORECASE)
            if addon_match:
                addon = addon_match.group(1)
                smartprop_path = addon_match.group(2)
            
            full_vsmart_path = os.path.join(cs2_path, 'content', 'csgo_addons', addon, smartprop_path.replace('\\', '/').strip('/'))
            if os.path.exists(full_vsmart_path):
                try:
                    with open(full_vsmart_path, "r") as f:
                        content = f.read()
                    content = re.sub(re.compile(r"= resource_name:"), "= ", content)
                    content = content.replace("null,", "")
                    import keyvalues3 as kv3
                    vsmart_data = kv3.textreader.KV3TextReader().parse(content).value
                    
                    self._traverse_vsmart_dict(vsmart_data, models_list, world_matrix, addon)
                except Exception as e:
                    print(f"[SmartPropEditor] Failed to load/traverse nested smart prop {smartprop_path}: {e}")

    def _traverse_vsmart_dict(self, data, models_list, parent_world_matrix=None, context_addon=None):
        if parent_world_matrix is None:
            parent_world_matrix = np.eye(4, dtype=np.float32)

        # Handle enabling
        is_enabled = data.get("m_bEnabled", True)
        if is_enabled is False or is_enabled == "false":
            return

        local_pos, local_rot, local_scale = self._get_local_transform(data)

        # Build local matrix
        local_matrix = (
            scale_matrix(*local_scale)
            @ rotation_matrix_euler(*local_rot)
            @ translation_matrix(*local_pos)
        )

        # Compose with parent
        world_matrix = local_matrix @ parent_world_matrix

        # Decompose to world TRS
        world_pos, world_rot, world_scale = decompose_trs(world_matrix)

        element_class = data.get("_class", "")
        model_path = ""
        if element_class in ("CSmartPropElement_Model",
                             "CSmartPropElement_ModelEntity",
                             "CSmartPropElement_PropPhysics",
                             "CSmartPropElement_PropDynamic"):
            model_path = data.get("m_sModelName", "")

        # Nested smart prop support inside dict traversal
        if element_class == "CSmartPropElement_SmartProp":
            smartprop_path = data.get("m_sSmartProp", "")
            if smartprop_path:
                self._load_and_traverse_nested_vsmart(smartprop_path, models_list, world_matrix, context_addon)

        eid = data.get("m_nElementID", 0)
        if eid > 0 and model_path:
            models_list.append({
                "id":                  eid,
                "path":                model_path,
                "position":            world_pos,
                "rotation":            world_rot,
                "scale":               world_scale,
                "parent_world_matrix": parent_world_matrix,
                "data":                data,
                "is_dot":              not bool(model_path)
            })

        # Traverse children
        children = data.get("m_Children", [])
        if not isinstance(children, list):
            children = []

        child_indices = list(range(len(children)))
        if element_class == "CSmartPropElement_PickOne":
            selection_mode = data.get("m_SelectionMode", "RANDOM")
            selected_idx = 0
            if selection_mode in ("SPECIFIC", "SPECIFIC_CHILD"):
                specific_idx_val = data.get("m_SpecificChildIndex", 0)
                try:
                    selected_idx = int(float(str(specific_idx_val)))
                except ValueError:
                    selected_idx = 0
            if len(children) > 0:
                selected_idx = max(0, min(selected_idx, len(children) - 1))
                child_indices = [selected_idx]
            else:
                child_indices = []

        for idx in child_indices:
            child_data = children[idx]
            if isinstance(child_data, dict):
                self._traverse_vsmart_dict(child_data, models_list, world_matrix, context_addon)

    def _traverse_tree(self, item, models_list, parent_world_matrix=None):
        if parent_world_matrix is None:
            parent_world_matrix = np.eye(4, dtype=np.float32)

        # Resolve context addon from opened file
        context_addon = None
        if self.document and getattr(self.document, "opened_file", None):
            import re
            opened_path = self.document.opened_file.replace('\\', '/')
            addon_match = re.search(r'/csgo_addons/([^/]+)/', opened_path, re.IGNORECASE)
            if addon_match:
                context_addon = addon_match.group(1)

        # Get parent info to see if we should restrict child traversal (e.g. for PickOne)
        parent_data = item.data(0, Qt.UserRole)
        parent_data = dict(parent_data) if parent_data is not None else {}
        parent_class = parent_data.get("_class", "")

        child_indices = list(range(item.childCount()))

        if parent_class == "CSmartPropElement_PickOne":
            selection_mode = parent_data.get("m_SelectionMode", "RANDOM")
            selected_idx = 0
            if selection_mode == "SPECIFIC" or selection_mode == "SPECIFIC_CHILD":
                specific_idx_val = parent_data.get("m_SpecificChildIndex", 0)
                if isinstance(specific_idx_val, (int, float)):
                    selected_idx = int(specific_idx_val)
                elif isinstance(specific_idx_val, str):
                    try:
                        selected_idx = int(float(specific_idx_val))
                    except ValueError:
                        selected_idx = 0
                elif isinstance(specific_idx_val, dict) and "m_Expression" in specific_idx_val:
                    try:
                        selected_idx = int(float(specific_idx_val["m_Expression"]))
                    except:
                        selected_idx = 0
                else:
                    selected_idx = 0
            else:
                selected_idx = 0

            if item.childCount() > 0:
                selected_idx = max(0, min(selected_idx, item.childCount() - 1))
                child_indices = [selected_idx]
            else:
                child_indices = []

        for idx in child_indices:
            child = item.child(idx)
            data = child.data(0, Qt.UserRole)
            data = dict(data) if data is not None else {}

            # Don't display elements if they are disabled
            is_enabled = data.get("m_bEnabled", True)
            if is_enabled is False or is_enabled == "false":
                continue

            local_pos, local_rot, local_scale = self._get_local_transform(data)

            # Build local matrix in Source 2 space (Scale -> Rotate -> Translate)
            local_matrix = (
                scale_matrix(*local_scale)
                @ rotation_matrix_euler(*local_rot)
                @ translation_matrix(*local_pos)
            )

            # Compose with parent
            world_matrix = local_matrix @ parent_world_matrix

            # Decompose to world TRS
            world_pos, world_rot, world_scale = decompose_trs(world_matrix)

            element_class = data.get("_class", "")
            model_path = ""
            if element_class in ("CSmartPropElement_Model",
                                 "CSmartPropElement_ModelEntity",
                                 "CSmartPropElement_PropPhysics",
                                 "CSmartPropElement_PropDynamic"):
                model_path = data.get("m_sModelName", "")

            # If this is a nested smart prop element, load and traverse it!
            if element_class == "CSmartPropElement_SmartProp":
                smartprop_path = data.get("m_sSmartProp", "")
                if smartprop_path:
                    self._load_and_traverse_nested_vsmart(smartprop_path, models_list, world_matrix, context_addon)

            eid = data.get("m_nElementID", 0)
            if eid > 0:
                models_list.append({
                    "id":                  eid,
                    "path":                model_path,
                    "position":            world_pos,
                    "rotation":            world_rot,
                    "scale":               world_scale,
                    "parent_world_matrix": parent_world_matrix,
                    "data":                data,
                    "is_dot":              not bool(model_path)
                })

            self._traverse_tree(child, models_list, world_matrix)

    def _update_subtree_transforms(self, item, parent_world_matrix):
        """Recursively update the world transforms of all descendants in self._model_infos."""
        parent_data = item.data(0, Qt.UserRole)
        parent_data = dict(parent_data) if parent_data is not None else {}
        parent_class = parent_data.get("_class", "")

        child_indices = list(range(item.childCount()))

        if parent_class == "CSmartPropElement_PickOne":
            selection_mode = parent_data.get("m_SelectionMode", "RANDOM")
            selected_idx = 0
            if selection_mode == "SPECIFIC" or selection_mode == "SPECIFIC_CHILD":
                specific_idx_val = parent_data.get("m_SpecificChildIndex", 0)
                if isinstance(specific_idx_val, (int, float)):
                    selected_idx = int(specific_idx_val)
                elif isinstance(specific_idx_val, str):
                    try:
                        selected_idx = int(float(specific_idx_val))
                    except ValueError:
                        selected_idx = 0
                elif isinstance(specific_idx_val, dict) and "m_Expression" in specific_idx_val:
                    try:
                        selected_idx = int(float(specific_idx_val["m_Expression"]))
                    except:
                        selected_idx = 0
                else:
                    selected_idx = 0
            else:
                selected_idx = 0

            if item.childCount() > 0:
                selected_idx = max(0, min(selected_idx, item.childCount() - 1))
                child_indices = [selected_idx]
            else:
                child_indices = []

        for idx in child_indices:
            child = item.child(idx)
            data = child.data(0, Qt.UserRole)
            data = dict(data) if data is not None else {}

            is_enabled = data.get("m_bEnabled", True)
            if is_enabled is False or is_enabled == "false":
                continue

            local_pos, local_rot, local_scale = self._get_local_transform(data)

            # Build local matrix
            local_matrix = (
                scale_matrix(*local_scale)
                @ rotation_matrix_euler(*local_rot)
                @ translation_matrix(*local_pos)
            )

            # Compose with parent
            world_matrix = local_matrix @ parent_world_matrix

            # Decompose to world TRS
            world_pos, world_rot, world_scale = decompose_trs(world_matrix)

            eid = data.get("m_nElementID", 0)
            if eid > 0 and eid in self._model_infos:
                info = self._model_infos[eid]
                info["position"] = world_pos
                info["rotation"] = world_rot
                info["scale"] = world_scale
                info["parent_world_matrix"] = parent_world_matrix

            self._update_subtree_transforms(child, world_matrix)
