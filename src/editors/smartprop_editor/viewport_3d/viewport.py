"""
Interactive 3D viewport container for the SmartProp Editor.
Integrates the OpenGL render area with toolbar controls.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QLabel

from src.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea
from src.editors.smartprop_editor.viewport_3d.gizmo import GizmoMode


class SmartProp3DViewport(QWidget):
    elementClicked = Signal(int)

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 3D Toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(32)
        toolbar.setObjectName("SPE_Viewport3D_Toolbar")
        toolbar.setStyleSheet("""
            QWidget#SPE_Viewport3D_Toolbar {
                background-color: #2D2D2D;
                border-bottom: 1px solid #1E1E1E;
            }
            QComboBox, QCheckBox, QLabel {
                color: #E0E0E0;
                font-family: 'Segoe UI';
                font-size: 11px;
            }
            QComboBox {
                background-color: #3D3D3D;
                border: 1px solid #555555;
                border-radius: 2px;
                padding: 1px 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QCheckBox {
                spacing: 4px;
            }
        """)

        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 0, 8, 0)
        tb_layout.setSpacing(12)

        # Space dropdown
        tb_layout.addWidget(QLabel("Space:"))
        self.space_combo = QComboBox()
        self.space_combo.addItems(["World", "Local", "Screen"])
        self.space_combo.setCurrentText("World")
        self.space_combo.currentTextChanged.connect(self._on_space_changed)
        tb_layout.addWidget(self.space_combo)

        # Snapping Checkbox
        self.snap_check = QCheckBox("Snapping")
        self.snap_check.setChecked(False)
        self.snap_check.stateChanged.connect(self._on_snap_changed)
        tb_layout.addWidget(self.snap_check)

        # Grid Step dropdown
        tb_layout.addWidget(QLabel("Grid Step:"))
        self.grid_combo = QComboBox()
        self.grid_combo.addItems(["1", "2", "4", "8", "16", "32", "64", "128", "256"])
        self.grid_combo.setCurrentText("8")
        self.grid_combo.currentTextChanged.connect(self._on_grid_step_changed)
        tb_layout.addWidget(self.grid_combo)

        # Rotation step dropdown
        tb_layout.addWidget(QLabel("Rotation Step:"))
        self.rot_combo = QComboBox()
        self.rot_combo.addItems(["5", "15", "45"])
        self.rot_combo.setCurrentText("15")
        self.rot_combo.currentTextChanged.connect(self._on_rot_step_changed)
        tb_layout.addWidget(self.rot_combo)

        # Display Groups Checkbox
        self.groups_check = QCheckBox("Display Groups")
        self.groups_check.setChecked(True)
        self.groups_check.stateChanged.connect(self._on_display_groups_changed)
        tb_layout.addWidget(self.groups_check)

        tb_layout.addStretch()
        layout.addWidget(toolbar)

        self.render_area = SmartProp3DRenderArea(document=document, parent=self)
        self.render_area.elementClicked.connect(self.elementClicked.emit)
        layout.addWidget(self.render_area)

        # Initialize defaults
        self._on_space_changed("World")
        self._on_snap_changed(Qt.Unchecked)
        self._on_grid_step_changed("8")
        self._on_rot_step_changed("15")
        self._on_display_groups_changed(Qt.Checked)

    def _on_space_changed(self, text):
        self.render_area.coordinate_space = text
        self.render_area.update()

    def _on_snap_changed(self, state):
        self.render_area.snapping_enabled = (state == Qt.Checked or state == 2)

    def _on_grid_step_changed(self, text):
        try:
            self.render_area.grid_step = float(text)
        except ValueError:
            pass

    def _on_rot_step_changed(self, text):
        try:
            self.render_area.rotation_step = float(text)
        except ValueError:
            pass

    def _on_display_groups_changed(self, state):
        self.render_area.display_groups = (state == Qt.Checked or state == 2)
        self.render_area.update_viewport()

    def _set_gizmo_mode(self, mode: GizmoMode):
        self.render_area.gizmo.set_mode(mode)
        self.render_area.update()

    def fit_view(self):
        self.render_area.fit_view()

    def update_viewport(self):
        self.render_area.update_viewport()

    def highlight_element(self, element_id: int):
        self.render_area.highlight_element(element_id)

    def keyPressEvent(self, event):
        # Forward transform-mode keys (W/E/R) to the render area.
        if event.key() in (Qt.Key_W, Qt.Key_E, Qt.Key_R):
            self.render_area.keyPressEvent(event)
        else:
            super().keyPressEvent(event)
