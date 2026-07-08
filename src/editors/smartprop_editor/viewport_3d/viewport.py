"""
Interactive 3D viewport container for the SmartProp Editor.
Integrates the OpenGL render area with toolbar controls.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from src.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea
from src.editors.smartprop_editor.viewport_3d.gizmo import GizmoMode


class SmartProp3DViewport(QWidget):
    elementClicked = Signal(int)

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document

        # The viewport is just the render area — no toolbar/header. Gizmo modes
        # are driven by the W/E/R keys and framing by F (handled in the render
        # area); shading defaults to the render area's own default.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.render_area = SmartProp3DRenderArea(document=document, parent=self)
        self.render_area.elementClicked.connect(self.elementClicked.emit)
        layout.addWidget(self.render_area)

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
