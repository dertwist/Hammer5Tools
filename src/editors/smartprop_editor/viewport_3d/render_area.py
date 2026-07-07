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

from src.editors.smartprop_editor.viewport_3d.camera import Camera, SOURCE2_TO_GL, translation_matrix, rotation_matrix_euler, scale_matrix
from src.editors.smartprop_editor.viewport_3d.gizmo import Gizmo, GizmoMode, GizmoAxis
from src.editors.smartprop_editor.viewport_3d.mesh_cache import MeshCache
from src.editors.smartprop_editor.viewport_3d.shaders import (
    MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER,
    PICKING_VERTEX_SHADER, PICKING_FRAGMENT_SHADER,
    GRID_VERTEX_SHADER, GRID_FRAGMENT_SHADER,
    GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER,
    WIREFRAME_VERTEX_SHADER, WIREFRAME_FRAGMENT_SHADER
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

        # Camera & Interaction
        self.camera = Camera()
        self.gizmo = Gizmo()
        self.mesh_cache = MeshCache(self)
        self.mesh_cache.model_ready.connect(self.update)

        self._last_mouse_pos = QPointF()
        self._action = None  # 'orbit' | 'pan'
        self._selected_id = 0

        # View Settings
        self.shading_mode = "textured"  # "textured" | "solid" | "wireframe"

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

        self._grid_vao = 0
        self._grid_vbo = 0
        self._box_vao = 0
        self._box_vbo = 0

    def initializeGL(self):
        from OpenGL import GL

        # Debug info
        renderer = GL.glGetString(GL.GL_RENDERER).decode('utf-8')
        print(f"[SmartProp3D] OpenGL Context Initialized: {renderer}")

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_MULTISAMPLE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        # Compile Shader Programs
        self._model_program = link_program(MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER)
        self._picking_program = link_program(PICKING_VERTEX_SHADER, PICKING_FRAGMENT_SHADER)
        self._grid_program = link_program(GRID_VERTEX_SHADER, GRID_FRAGMENT_SHADER)
        self._gizmo_program = link_program(GIZMO_VERTEX_SHADER, GIZMO_FRAGMENT_SHADER)
        self._wireframe_program = link_program(WIREFRAME_VERTEX_SHADER, WIREFRAME_FRAGMENT_SHADER)

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

        # Upload meshes ready on CPU
        self.mesh_cache.upload_pending()

        # Matrices
        view = self.camera.view_matrix
        proj = self.camera.projection_matrix
        cam_pos = self.camera.position

        # 1. Render Grid Floor
        GL.glUseProgram(self._grid_program)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._grid_program, "uView"), 1, GL.GL_FALSE, view)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._grid_program, "uProjection"), 1, GL.GL_FALSE, proj)
        GL.glBindVertexArray(self._grid_vao)
        GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, 4)
        GL.glBindVertexArray(0)

        # 2. Render Models
        self._render_scene_models(view, proj, cam_pos, picking=False)

        # 3. Render Gizmo
        self.gizmo.render(self._gizmo_program, view, proj, cam_pos)

    def _render_scene_models(self, view, proj, cam_pos, picking=False):
        from OpenGL import GL

        if picking:
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

        for eid, info in self._model_infos.items():
            pos = info.get("position", [0.0, 0.0, 0.0])
            rot = info.get("rotation", [0.0, 0.0, 0.0])
            scale = info.get("scale", [1.0, 1.0, 1.0])
            model_path = info.get("path", "")

            # Construct S2 -> GL matrix
            model_matrix = SOURCE2_TO_GL @ translation_matrix(*pos) @ rotation_matrix_euler(*rot) @ scale_matrix(*scale)

            # Query GPU mesh
            gpu_mesh = self.mesh_cache.get_gpu_mesh(model_path)

            if picking:
                # Color encoding of the integer ID
                r = (eid & 0xFF) / 255.0
                g = ((eid >> 8) & 0xFF) / 255.0
                b = ((eid >> 16) & 0xFF) / 255.0
                GL.glUniform3f(GL.glGetUniformLocation(self._picking_program, "uPickColor"), r, g, b)

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
                    GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._model_program, "uModel"), 1, GL.GL_FALSE, model_matrix)
                    # Normal matrix is transpose of inverse of 3x3 model matrix
                    norm_mat = np.linalg.inv(model_matrix[:3, :3]).T
                    GL.glUniformMatrix3fv(GL.glGetUniformLocation(self._model_program, "uNormalMatrix"), 1, GL.GL_FALSE, norm_mat)

                    # Highlight selection
                    GL.glUniform1f(GL.glGetUniformLocation(self._model_program, "uHighlight"), 1.0 if is_selected else 0.0)
                    GL.glUniform3fv(GL.glGetUniformLocation(self._model_program, "uBaseColor"), 1, np.array([0.7, 0.7, 0.7], dtype=np.float32))

                    # Texture setup
                    has_tex = 0
                    if self.shading_mode == "textured" and gpu_mesh.has_texture:
                        GL.glActiveTexture(GL.GL_TEXTURE0)
                        GL.glBindTexture(GL.GL_TEXTURE_2D, gpu_mesh.texture_id)
                        GL.glUniform1i(GL.glGetUniformLocation(self._model_program, "uTexture"), 0)
                        has_tex = 1

                    GL.glUniform1i(GL.glGetUniformLocation(self._model_program, "uHasTexture"), has_tex)

                    GL.glBindVertexArray(gpu_mesh.vao)
                    GL.glDrawElements(GL.GL_TRIANGLES, gpu_mesh.index_count, GL.GL_UNSIGNED_INT, None)
                    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
                else:
                    # Queue model decompile / load if not already started
                    self.mesh_cache.request_model(model_path)

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

        # Restore standard polygon fill mode
        if not picking:
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

    def _draw_box_geometry(self, model_matrix, is_picking=False):
        """Draw a box geometry based on S2 scale conversion."""
        from OpenGL import GL

        # Units base: standard 50.0 units
        bx, by, bz = 50.0, 50.0, 50.0
        # Remap Z-up to GL Y-up
        gl_box_matrix = model_matrix @ scale_matrix(bx, bz, by)

        program = self._picking_program if is_picking else self._wireframe_program
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(program, "uModel"), 1, GL.GL_FALSE, gl_box_matrix)

        GL.glBindVertexArray(self._box_vao)
        if is_picking:
            # Render wireframe box corners / outline or lines
            GL.glDrawArrays(GL.GL_LINES, 0, 24)
        else:
            GL.glDrawArrays(GL.GL_LINES, 0, 24)
        GL.glBindVertexArray(0)

    def _do_picking_pass(self):
        """Perform color-coded picking pass on backbuffer."""
        from OpenGL import GL

        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glDisable(GL.GL_BLEND)

        view = self.camera.view_matrix
        proj = self.camera.projection_matrix
        cam_pos = self.camera.position

        self._render_scene_models(view, proj, cam_pos, picking=True)

        # Read color under cursor
        w, h = self.width(), self.height()
        gl_y = h - self._pick_pos.y()
        gl_x = self._pick_pos.x()

        pixel = GL.glReadPixels(int(gl_x), int(gl_y), 1, 1, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
        GL.glEnable(GL.GL_BLEND)

        # Decode ID
        r = pixel[0]
        g = pixel[1]
        b = pixel[2]
        clicked_id = r | (g << 8) | (b << 16)

        if clicked_id != 0 and clicked_id in self._model_infos:
            self.elementClicked.emit(clicked_id)
            self.highlight_element(clicked_id)
        else:
            self.elementClicked.emit(0)
            self.highlight_element(0)

    # ------------------------------------------------------------------
    # Camera fitting
    # ------------------------------------------------------------------
    def fit_view(self):
        """Zoom and position camera to fit all models in scene."""
        if not self._model_infos:
            return

        bbox_min = np.array([float('inf'), float('inf'), float('inf')], dtype=np.float32)
        bbox_max = np.array([float('-inf'), float('-inf'), float('-inf')], dtype=np.float32)

        has_bounds = False
        for eid, info in self._model_infos.items():
            pos = np.array(info.get("position", [0.0, 0.0, 0.0]), dtype=np.float32)
            # Map pos to GL coordinates
            gl_pos = SOURCE2_TO_GL @ np.append(pos, 1.0)
            gl_pos = gl_pos[:3]

            bbox_min = np.minimum(bbox_min, gl_pos - 50.0)
            bbox_max = np.maximum(bbox_max, gl_pos + 50.0)
            has_bounds = True

        if has_bounds:
            self.camera.fit_to_bounds(bbox_min, bbox_max)
            self.update()

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

        # Sync selection gizmo transform if selection exists
        if self._selected_id in self._model_infos:
            sel = self._model_infos[self._selected_id]
            self.gizmo.set_transform(sel["position"], sel["rotation"], sel["scale"])
        else:
            self.gizmo.hide()

        self.update()

    def highlight_element(self, element_id: int):
        """Select/Highlight element and reposition gizmo."""
        self._selected_id = element_id
        if element_id != 0 and element_id in self._model_infos:
            sel = self._model_infos[element_id]
            self.gizmo.set_transform(sel["position"], sel["rotation"], sel["scale"])
        else:
            self.gizmo.hide()
        self.update()

    # ------------------------------------------------------------------
    # Mouse & Keyboard Event Handlers
    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        self._last_mouse_pos = event.position()

        # Hit test transform gizmo first
        if self.gizmo.visible and self.gizmo.mode != GizmoMode.NONE:
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

        # Fallback to camera orbit or pan
        if event.button() == Qt.LeftButton:
            # Trigger color-picking on next paintGL
            self._perform_pick_flag = True
            self._pick_pos = event.position()
            self.update()
        elif event.button() in (Qt.RightButton, Qt.MiddleButton):
            self._action = 'pan'

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
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
                if item:
                    from src.common import fast_deepcopy
                    data = fast_deepcopy(item.data(0, Qt.UserRole))

                    # Apply position, rotation, or scale
                    if "position" in delta:
                        self._set_modifier_value(data, "CSmartPropOperation_Translate", "m_vPosition", delta["position"])
                    elif "rotation" in delta:
                        self._set_modifier_value(data, "CSmartPropOperation_Rotate", "m_vRotation", delta["rotation"])
                    elif "scale" in delta:
                        # Scale mod
                        is_model = data.get("_class", "").startswith("CSmartPropElement_Model")
                        if is_model and "m_vModelScale" in data:
                            data["m_vModelScale"] = delta["scale"]
                        else:
                            self._set_modifier_value(data, "CSmartPropOperation_Scale", "m_flScale", delta["scale"][0])

                    item.setData(0, Qt.UserRole, data)

                    # Update local view caches without full rebuild
                    self._model_infos[self._selected_id]["position"] = delta.get("position", self._model_infos[self._selected_id]["position"])
                    self._model_infos[self._selected_id]["rotation"] = delta.get("rotation", self._model_infos[self._selected_id]["rotation"])
                    self._model_infos[self._selected_id]["scale"] = delta.get("scale", self._model_infos[self._selected_id]["scale"])

                    # Update gizmo position/rotation/scale
                    self.gizmo.set_transform(
                        self._model_infos[self._selected_id]["position"],
                        self._model_infos[self._selected_id]["rotation"],
                        self._model_infos[self._selected_id]["scale"]
                    )

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
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Data modifier helpers
    # ------------------------------------------------------------------
    def _set_modifier_value(self, data, class_name, key, value):
        """Set a property value on a specific modifier or insert a new one if missing."""
        modifiers = data.get("m_Modifiers")
        if modifiers is None:
            modifiers = []
            data["m_Modifiers"] = modifiers

        for mod in modifiers:
            if isinstance(mod, dict) and mod.get("_class") == class_name:
                mod[key] = value
                return

        # Insert new modifier
        new_mod = {
            "_class": class_name,
            key: value,
            "m_bActive": True
        }
        modifiers.append(new_mod)

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

    def _traverse_tree(self, item, models_list, accumulated_transform=None):
        if accumulated_transform is None:
            accumulated_transform = {
                "position": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale":    [1.0, 1.0, 1.0]
            }

        for idx in range(item.childCount()):
            child = item.child(idx)
            data = child.data(0, Qt.UserRole)
            data = dict(data) if data is not None else {}

            local_pos   = [0.0, 0.0, 0.0]
            local_rot   = [0.0, 0.0, 0.0]
            local_scale = [1.0, 1.0, 1.0]

            # Modifiers
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
            model_path = ""
            if element_class == "CSmartPropElement_Model":
                model_path = data.get("m_sModelName", "")
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
                model_path = data.get("m_sModelName", "")
                if data.get("m_vModelScale"):
                    comp = self._get_vector(data["m_vModelScale"], [1.0, 1.0, 1.0])
                    local_scale = [local_scale[i] * comp[i] for i in range(3)]

            new_pos   = [accumulated_transform["position"][i] + local_pos[i]   for i in range(3)]
            new_rot   = [accumulated_transform["rotation"][i] + local_rot[i]   for i in range(3)]
            new_scale = [accumulated_transform["scale"][i]    * local_scale[i] for i in range(3)]
            current_transform = {"position": new_pos, "rotation": new_rot, "scale": new_scale}

            if model_path:
                models_list.append({
                    "id":       data.get("m_nElementID", 0),
                    "path":     model_path,
                    "position": new_pos,
                    "rotation": new_rot,
                    "scale":    new_scale,
                })

            self._traverse_tree(child, models_list, current_transform)
