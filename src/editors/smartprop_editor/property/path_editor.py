import copy
import math

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QDialog, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QDoubleSpinBox,
    QSplitter, QComboBox, QMenu, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QMouseEvent, QWheelEvent

from src.styles.common import apply_stylesheets


class InteractiveCurveEditor(QWidget):
    """3D viewport for editing curvatures."""
    points_changed = Signal()
    selection_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.points = []
        self.selected_index = -1
        
        # Camera
        self.yaw = 30.0    # Rotation around Z axis
        self.pitch = -30.0 # Rotation around X axis
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.scale = 1.0
        
        # Interaction state
        self._last_mouse_pos = None
        self._action = None # 'pan', 'orbit', 'drag'
        self._hover_index = -1

    def set_points(self, points):
        self.points = points
        self.update()

    def set_selected_index(self, idx):
        if self.selected_index != idx:
            self.selected_index = idx
            self.update()

    def _project(self, point):
        """Projects a 3D point [x, y, z] to 2D screen coordinates and depth."""
        x, y, z = point
        
        # Yaw (Z axis)
        rad_yaw = math.radians(self.yaw)
        cy, sy = math.cos(rad_yaw), math.sin(rad_yaw)
        x1 = x * cy - y * sy
        y1 = x * sy + y * cy
        z1 = z
        
        # Pitch (X axis)
        rad_pitch = math.radians(self.pitch)
        cp, sp = math.cos(rad_pitch), math.sin(rad_pitch)
        x2 = x1
        y2 = y1 * cp - z1 * sp
        z2 = y1 * sp + z1 * cp
        
        # Screen projection
        w, h = self.width(), self.height()
        sx = x2 * self.scale + w / 2 + self.pan_x
        sy = -z2 * self.scale + h / 2 + self.pan_y
        depth = y2
        
        return sx, sy, depth

    def _unproject_delta(self, dsx, dsy):
        """Converts a screen-space delta (dsx, dsy) to a 3D delta in the camera's parallel plane."""
        # Basically the inverse rotation of the generic X/Y axes of screen to 3D space
        # Screen X moves along rotated X.
        # Screen Y moves along rotated -Z.
        rad_yaw = math.radians(self.yaw)
        rad_pitch = math.radians(self.pitch)
        cy, sy = math.cos(rad_yaw), math.sin(rad_yaw)
        cp, sp = math.cos(rad_pitch), math.sin(rad_pitch)
        
        # Inverse rotate X axis
        # Forward: x1 = dx*cy; y1 = dx*sy; z1 = 0
        # Actually, screen_x = x2 * scale. So x2 = dsx / scale.
        x2 = dsx / self.scale
        z2 = -dsy / self.scale
        y2 = 0 # No depth movement
        
        # Inverse Pitch (X axis)
        # y2 = y1*cp - z1*sp => y1 = y2*cp + z2*sp (inverse of rotation matrix is transpose)
        # z2 = y1*sp + z1*cp => z1 = -y2*sp + z2*cp
        y1 = y2 * cp + z2 * sp
        z1 = -y2 * sp + z2 * cp
        
        # Inverse Yaw (Z axis)
        # x1 = x*cy - y*sy => x = x1*cy + y1*sy
        # y1 = x*sy + y*cy => y = -x1*sy + y1*cy
        x1 = x2
        dx = x1 * cy + y1 * sy
        dy = -x1 * sy + y1 * cy
        dz = z1
        
        return dx, dy, dz

    def min_max_scale(self):
        """Auto fit camera to points."""
        if not self.points:
            return
        min_x = min(p[0] for p in self.points)
        max_x = max(p[0] for p in self.points)
        min_y = min(p[1] for p in self.points)
        max_y = max(p[1] for p in self.points)
        
        dist = max(max_x - min_x, max_y - min_y)
        if dist < 1:
            dist = 500
            
        self.scale = min(self.width(), self.height()) / (dist * 1.5)
        self.pan_x = 0
        self.pan_y = 0
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale *= zoom_factor
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        self._last_mouse_pos = event.position()
        
        if event.button() == Qt.LeftButton:
            # Check if clicked on a point
            closest_idx = -1
            min_dist = 10.0 # Pixel hit radius
            for i, p in enumerate(self.points):
                sx, sy, _ = self._project(p)
                dist = math.hypot(sx - event.position().x(), sy - event.position().y())
                if dist < min_dist:
                    closest_idx = i
                    min_dist = dist
                    
            if closest_idx != -1:
                self.selected_index = closest_idx
                self.selection_changed.emit(closest_idx)
                self._action = 'drag'
            else:
                self._action = 'orbit'
                
        elif event.button() == Qt.RightButton or event.button() == Qt.MiddleButton:
            self._action = 'pan'

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        
        if self._action == 'orbit':
            dx = pos.x() - self._last_mouse_pos.x()
            dy = pos.y() - self._last_mouse_pos.y()
            self.yaw -= dx * 0.5
            self.pitch -= dy * 0.5
            self.update()
            
        elif self._action == 'pan':
            dx = pos.x() - self._last_mouse_pos.x()
            dy = pos.y() - self._last_mouse_pos.y()
            self.pan_x += dx
            self.pan_y += dy
            self.update()
            
        elif self._action == 'drag' and self.selected_index != -1:
            dx = pos.x() - self._last_mouse_pos.x()
            dy = pos.y() - self._last_mouse_pos.y()
            # If shift is pressed, alter depth (move along camera view ray roughly, or just constrained to Z)
            # For simplicity, let's just move in the camera plane.
            dx3, dy3, dz3 = self._unproject_delta(dx, dy)
            self.points[self.selected_index][0] += dx3
            self.points[self.selected_index][1] += dy3
            self.points[self.selected_index][2] += dz3
            self.points_changed.emit()
            self.update()
            
        else:
            # Hover check
            hover = -1
            min_dist = 10.0
            for i, p in enumerate(self.points):
                sx, sy, _ = self._project(p)
                dist = math.hypot(sx - pos.x(), sy - pos.y())
                if dist < min_dist:
                    hover = i
                    min_dist = dist
            if hover != self._hover_index:
                self._hover_index = hover
                self.update()

        self._last_mouse_pos = pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._action = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        # Draw grid
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        grid_size = 500
        step = 100
        for i in range(-grid_size, grid_size + 1, step):
            p1 = self._project((i, -grid_size, 0))
            p2 = self._project((i, grid_size, 0))
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])
            p1 = self._project((-grid_size, i, 0))
            p2 = self._project((grid_size, i, 0))
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])
            
        # Draw axes
        def draw_axis(axis, color):
            p1 = self._project((0, 0, 0))
            p2 = self._project(axis)
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])
            
        draw_axis((100, 0, 0), "#FF5555") # X
        draw_axis((0, 100, 0), "#55FF55") # Y
        draw_axis((0, 0, 100), "#5555FF") # Z

        if not self.points:
            return

        # Draw lines between points
        painter.setPen(QPen(QColor(255, 150, 50), 2))
        path = QPainterPath()
        for i, p in enumerate(self.points):
            sx, sy, _ = self._project(p)
            if i == 0:
                path.moveTo(sx, sy)
            else:
                path.lineTo(sx, sy)
        painter.drawPath(path)

        # Draw points
        for i, p in enumerate(self.points):
            sx, sy, _ = self._project(p)
            
            if i == self.selected_index:
                painter.setBrush(QColor(255, 255, 255))
                painter.setPen(QPen(QColor(255, 100, 0), 2))
                radius = 6
            elif i == self._hover_index:
                painter.setBrush(QColor(255, 200, 100))
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                radius = 5
            else:
                painter.setBrush(QColor(255, 150, 50))
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                radius = 4
                
            painter.drawEllipse(sx - radius, sy - radius, radius*2, radius*2)
            
            # Point index label
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(sx + 8, sy + 4, str(i))

# --- Main Dialog UI with Splitter ---

class _PathEditorDialog(QDialog):
    def __init__(self, points, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Path Editor")
        self.resize(800, 450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        self._points = copy.deepcopy(points)
        self._block_updates = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(splitter)
        
        # Left side: 3D Viewport
        viewport_container = QWidget()
        vp_layout = QVBoxLayout(viewport_container)
        vp_layout.setContentsMargins(0, 0, 0, 0)
        vp_layout.setSpacing(0)
        
        # Viewport Toolbar
        vp_toolbar = QWidget()
        vp_toolbar.setObjectName('vp_toolbar')
        vp_toolbar.setStyleSheet("background-color: #2D2D2D;")
        vpt_layout = QHBoxLayout(vp_toolbar)
        vpt_layout.setContentsMargins(4, 4, 4, 4)
        
        view_lbl = QLabel("View:")
        view_lbl.setStyleSheet("color: white;")
        vpt_layout.addWidget(view_lbl)
        
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Perspective", "Top (XY)", "Front (XZ)", "Side (YZ)"])
        self.view_combo.currentTextChanged.connect(self._on_view_changed)
        vpt_layout.addWidget(self.view_combo)
        
        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(lambda: self.viewport.min_max_scale())
        vpt_layout.addWidget(fit_btn)
        
        vpt_layout.addStretch()
        vp_layout.addWidget(vp_toolbar)
        
        self.viewport = InteractiveCurveEditor()
        self.viewport.set_points(self._points)
        self.viewport.min_max_scale()
        self.viewport.points_changed.connect(self._on_viewport_modified)
        self.viewport.selection_changed.connect(self._on_viewport_selection)
        vp_layout.addWidget(self.viewport)
        
        splitter.addWidget(viewport_container)
        
        # Right side: Data Table
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 8, 8, 8)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Add Point")
        self.add_btn.clicked.connect(self._add_point)
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self._remove_point)
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.remove_btn)
        toolbar.addStretch()
        right_layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Z"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        right_layout.addWidget(self.table)
        
        splitter.addWidget(right_container)
        
        # Set splitter sizes (60% viewport, 40% table)
        splitter.setSizes([480, 320])
        
        # Footer buttons
        footer = QWidget()
        btn_layout = QHBoxLayout(footer)
        btn_layout.setContentsMargins(8, 0, 8, 8)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addWidget(footer)
        
        self._populate()

    def _on_view_changed(self, text):
        if text == "Perspective":
            self.viewport.yaw = 30.0
            self.viewport.pitch = -30.0
        elif text == "Top (XY)":
            self.viewport.yaw = 0.0
            self.viewport.pitch = -90.0
        elif text == "Front (XZ)":
            self.viewport.yaw = 0.0
            self.viewport.pitch = 0.0
        elif text == "Side (YZ)":
            self.viewport.yaw = 90.0
            self.viewport.pitch = 0.0
        self.viewport.update()

    def _on_viewport_modified(self):
        """When the viewport drags a point, update the table safely without triggering loop."""
        self._block_updates = True
        idx = self.viewport.selected_index
        if 0 <= idx < len(self._points) and idx < self.table.rowCount():
            pt = self._points[idx]
            for i in range(3):
                spin = self.table.cellWidget(idx, i)
                if spin:
                    spin.setValue(pt[i])
        self._block_updates = False

    def _on_viewport_selection(self, idx):
        """When clicking a point in the viewport, select the row in the table."""
        self._block_updates = True
        self.table.clearSelection()
        if 0 <= idx < self.table.rowCount():
            self.table.selectRow(idx)
        self._block_updates = False

    def _on_table_selection(self):
        if self._block_updates:
            return
        rows = list(set(idx.row() for idx in self.table.selectedIndexes()))
        if rows:
            self.viewport.set_selected_index(rows[0])
        else:
            self.viewport.set_selected_index(-1)

    def _on_spinbox_changed(self, row, col, val):
        if self._block_updates:
            return
        if 0 <= row < len(self._points):
            self._points[row][col] = val
            self.viewport.set_points(self._points)

    def _populate(self):
        self._block_updates = True
        self.table.setRowCount(0)
        for idx, pt in enumerate(self._points):
            self._add_row(idx, pt)
        self._block_updates = False
            
    def _add_row(self, idx, pt):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for i in range(3):
            spin = QDoubleSpinBox()
            spin.setRange(-999999.0, 999999.0)
            spin.setDecimals(1)
            # Support flat/incomplete lists gracefully
            val = float(pt[i]) if i < len(pt) else 0.0
            spin.setValue(val)
            spin.valueChanged.connect(lambda v, r=row, c=i: self._on_spinbox_changed(r, c, v))
            self.table.setCellWidget(row, i, spin)

    def _add_point(self):
        # Infer reasonable coordinate for next point
        new_pt = [0.0, 0.0, 0.0]
        if len(self._points) > 0:
            last = self._points[-1]
            new_pt = [last[0] + 100.0, last[1], last[2]] # Simple linear guess across X
        
        self._points.append(new_pt)
        self._block_updates = True
        self._add_row(len(self._points) - 1, new_pt)
        self._block_updates = False
        
        self.viewport.set_points(self._points)
        self.table.selectRow(self.table.rowCount() - 1)

    def _remove_point(self):
        rows = sorted(list(set(idx.row() for idx in self.table.selectedIndexes())), reverse=True)
        if not rows:
            return
            
        self._block_updates = True
        for r in rows:
            self.table.removeRow(r)
            if 0 <= r < len(self._points):
                del self._points[r]
        self._block_updates = False
        
        self.viewport.set_points(self._points)
        self.viewport.set_selected_index(-1)

    def get_points(self):
        return self._points


class PropertyPathEditor(QWidget):
    edited = Signal()
    
    def __init__(self, value=None, value_class=None, **kwargs):
        super().__init__()
        self.value_class = value_class
        
        self._path_points = []
        if isinstance(value, list):
            self._path_points = list(value)
        else:
            self._path_points = [[-400.0, 0.0, 0.0], [-200.0, 32.0, 0.0], [200.0, -32.0, 0.0], [400.0, 0.0, 0.0]]
            
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        
        self.label = QLabel("Default Path")
        self.label.setFixedWidth(145)
        self.label.setStyleSheet("color: rgb(255, 209, 153); font: 8pt 'Segoe UI';")
        layout.addWidget(self.label)
        
        self.edit_button = QPushButton("Edit Path...")
        self.edit_button.clicked.connect(self._open_editor)
        layout.addWidget(self.edit_button)
        layout.addStretch()

    @property
    def value(self):
        return {self.value_class: self._path_points}

    def _open_editor(self):
        dialog = _PathEditorDialog(self._path_points, self)
        
        # Apply standard stylesheet to children
        apply_stylesheets(dialog)
        
        # Override specific generic elements to enhance the Path Editor appearance
        dialog.setStyleSheet("""
            QDialog { background-color: #1C1C1C; }
            QWidget#vp_toolbar { background-color: #2D2D2D; border-bottom: 1px solid #363639; }
            QTableWidget { background-color: #151515; color: #E3E3E3; border: 1px solid #363639; gridline-color: #363639; }
            QHeaderView::section { background-color: #252526; color: #9D9D9D; border: 1px solid #363639; padding: 4px; }
            QPushButton { background-color: #333333; color: #E3E3E3; border: 1px solid #555555; border-radius: 2px; padding: 4px 12px; }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #222222; }
            QDoubleSpinBox { background-color: #252526; color: #E3E3E3; border: 1px solid #363639; padding: 2px; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { background-color: #333333; }
        """)
        
        dialog.viewport.setStyleSheet("QWidget { background-color: #151515; border: 1px solid #363639; }")
        
        if dialog.exec() == QDialog.Accepted:
            self._path_points = dialog.get_points()
            self.edited.emit()
