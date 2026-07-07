"""
Interactive 3D viewport container for the SmartProp Editor.
Integrates the OpenGL render area with toolbar controls.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QButtonGroup
)

from src.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea
from src.editors.smartprop_editor.viewport_3d.gizmo import GizmoMode


class SmartProp3DViewport(QWidget):
    elementClicked = Signal(int)

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- toolbar ----
        self.toolbar = QWidget()
        self.toolbar.setObjectName("vp_toolbar_3d")
        self.toolbar.setFixedHeight(20)
        self.toolbar.setStyleSheet(
            "QWidget#vp_toolbar_3d { background-color: #2D2D2D; border-bottom: 1px solid #363639; }"
            " QWidget#vp_toolbar_3d QPushButton,"
            " QWidget#vp_toolbar_3d QComboBox { max-height: 18px; padding: 0px 4px; }"
        )
        tbl = QHBoxLayout(self.toolbar)
        tbl.setContentsMargins(6, 0, 6, 0)
        tbl.setSpacing(6)

        # Shading modes
        shading_lbl = QLabel("Shading:")
        shading_lbl.setStyleSheet("color: #9D9D9D; font: 9pt 'Segoe UI';")
        tbl.addWidget(shading_lbl)

        self._shading_combo = QComboBox()
        self._shading_combo.setFixedWidth(100)
        self._shading_combo.addItems(["Textured", "Solid", "Wireframe"])
        self._shading_combo.currentTextChanged.connect(self._on_shading_mode)
        tbl.addWidget(self._shading_combo)

        tbl.addSpacing(10)

        # Gizmo Transform Modes (W/E/R)
        gizmo_lbl = QLabel("Gizmo:")
        gizmo_lbl.setStyleSheet("color: #9D9D9D; font: 9pt 'Segoe UI';")
        tbl.addWidget(gizmo_lbl)

        self.gizmo_group = QButtonGroup(self)
        self.gizmo_group.setExclusive(True)

        self.btn_translate = QPushButton("Translate (W)")
        self.btn_translate.setCheckable(True)
        self.btn_translate.setChecked(True)
        self.btn_translate.setFixedWidth(90)
        self.btn_translate.clicked.connect(lambda: self._set_gizmo_mode(GizmoMode.TRANSLATE))
        self.gizmo_group.addButton(self.btn_translate)
        tbl.addWidget(self.btn_translate)

        self.btn_rotate = QPushButton("Rotate (E)")
        self.btn_rotate.setCheckable(True)
        self.btn_rotate.setFixedWidth(80)
        self.btn_rotate.clicked.connect(lambda: self._set_gizmo_mode(GizmoMode.ROTATE))
        self.gizmo_group.addButton(self.btn_rotate)
        tbl.addWidget(self.btn_rotate)

        self.btn_scale = QPushButton("Scale (R)")
        self.btn_scale.setCheckable(True)
        self.btn_scale.setFixedWidth(80)
        self.btn_scale.clicked.connect(lambda: self._set_gizmo_mode(GizmoMode.SCALE))
        self.gizmo_group.addButton(self.btn_scale)
        tbl.addWidget(self.btn_scale)

        tbl.addSpacing(10)

        fit_btn = QPushButton("Fit")
        fit_btn.setFixedWidth(40)
        fit_btn.setToolTip("Fit scene into view")
        fit_btn.clicked.connect(self.fit_view)
        tbl.addWidget(fit_btn)

        tbl.addStretch()

        self._info_label = QLabel("No file open.")
        self._info_label.setStyleSheet("color: #6A6A6A; font: 8pt 'Segoe UI';")
        tbl.addWidget(self._info_label)

        layout.addWidget(self.toolbar)

        # ---- render area ----
        self.render_area = SmartProp3DRenderArea(document=document, parent=self)
        self.render_area.elementClicked.connect(self.elementClicked.emit)
        layout.addWidget(self.render_area)

    def _on_shading_mode(self, mode_name):
        self.render_area.shading_mode = mode_name.lower()
        self.render_area.update()

    def _set_gizmo_mode(self, mode: GizmoMode):
        self.render_area.gizmo.set_mode(mode)
        # Sync button checks
        self.btn_translate.setChecked(mode == GizmoMode.TRANSLATE)
        self.btn_rotate.setChecked(mode == GizmoMode.ROTATE)
        self.btn_scale.setChecked(mode == GizmoMode.SCALE)
        self.render_area.update()

    def fit_view(self):
        self.render_area.fit_view()

    def update_viewport(self):
        self.render_area.update_viewport()
        count = len(self.render_area._model_infos)
        self._info_label.setText(f"{count} model{'s' if count != 1 else ''} in scene.")

        # Sync checked button state with gizmo mode
        mode = self.render_area.gizmo.mode
        self.btn_translate.setChecked(mode == GizmoMode.TRANSLATE)
        self.btn_rotate.setChecked(mode == GizmoMode.ROTATE)
        self.btn_scale.setChecked(mode == GizmoMode.SCALE)

    def highlight_element(self, element_id: int):
        self.render_area.highlight_element(element_id)

    def keyPressEvent(self, event):
        # Forward key events (W/E/R) to render area
        if event.key() in (Qt.Key_W, Qt.Key_E, Qt.Key_R):
            self.render_area.keyPressEvent(event)
            self._set_gizmo_mode(self.render_area.gizmo.mode)
        else:
            super().keyPressEvent(event)
