"""
Interactive 3D viewport container for the SmartProp Editor.
Integrates the OpenGL render area with toolbar controls.
"""
import os

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QLabel,
    QToolButton, QSizePolicy,
)

from src.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea
from src.editors.smartprop_editor.viewport_3d.gizmo import GizmoMode
from src.common import get_cs2_path
from src.styles.common import (
    qt_stylesheet_viewport_toolbar,
    qt_stylesheet_combobox,
    qt_stylesheet_checkbox,
)


def _hammer_tool_icon_path(name):
    """Absolute path to a Hammer tool image shipped with the CS2 install."""
    return os.path.join(
        get_cs2_path(), "game", "core", "tools", "images", "hammer", name
    )


# Toggle-button styling for the compact icon toggles in the viewport toolbar.
# Checked state is highlighted so the on/off state reads clearly at a glance.
_VIEWPORT_TOGGLE_STYLE = """
QToolButton {
    border: 1px solid rgba(80, 80, 80, 255);
    border-radius: 2px;
    background-color: #1C1C1C;
    padding: 1px;
}
QToolButton:hover {
    background-color: #414956;
}
QToolButton:checked {
    background-color: #4A5A6A;
    border-color: #accc8d;
}
"""


class SmartProp3DViewport(QWidget):
    elementClicked = Signal(int)

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 3D Toolbar.  Horizontal size policy is Ignored so the toolbar never
        # imposes a minimum width on the viewport dock — the dock can be resized
        # narrower than the toolbar's natural content width (controls clip past
        # the trailing stretch instead of forcing the whole panel wider).
        toolbar = QWidget()
        toolbar.setFixedHeight(28)
        toolbar.setObjectName("SPE_Viewport3D_Toolbar")
        toolbar.setStyleSheet(qt_stylesheet_viewport_toolbar)
        toolbar.setMinimumWidth(0)
        toolbar.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 0, 8, 0)
        tb_layout.setSpacing(8)

        # View dropdown (Textured, Solid, Wireframe)
        tb_layout.addWidget(QLabel("View:"))
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Textured", "Solid", "Wireframe"])
        self.view_combo.setCurrentText("Textured")
        self.view_combo.currentTextChanged.connect(self._on_view_mode_changed)
        tb_layout.addWidget(self.view_combo)

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

        # Push the visibility toggles to the right edge of the toolbar.
        tb_layout.addStretch()

        # Display Groups toggle — single-state Hammer "solids" icon.
        self.groups_check = self._make_toggle_button(
            tooltip="Display Groups",
            icon_off=_hammer_tool_icon_path("selection_mode_solids.png"),
        )
        self.groups_check.setChecked(True)
        self.groups_check.toggled.connect(self._on_display_groups_changed)
        tb_layout.addWidget(self.groups_check)

        # Widgets toggle — locator / rotator / pickone preview widgets.  Uses the
        # activated icon when on and the plain icon when off.
        self.widgets_check = self._make_toggle_button(
            tooltip="Widgets",
            icon_off=_hammer_tool_icon_path("toggle_editor_objects.png"),
            icon_on=_hammer_tool_icon_path("toggle_editor_objects_activated.png"),
        )
        self.widgets_check.setChecked(True)
        self.widgets_check.toggled.connect(self._on_show_widgets_changed)
        tb_layout.addWidget(self.widgets_check)

        # Create smaller styling for the toolbar controls
        qt_stylesheet_viewport_combo = qt_stylesheet_combobox.replace(
            "height:22px;", "height:16px; min-height:16px; max-height:16px; padding-top: 0px; padding-bottom: 0px; font: 580 8pt \"Segoe UI\";"
        )
        qt_stylesheet_viewport_check = qt_stylesheet_checkbox.replace(
            "height:22px;", "height:16px; min-height:16px; max-height:16px; padding-top: 0px; padding-bottom: 0px; font: 580 8pt \"Segoe UI\";"
        )

        # Apply shared app stylesheets to the toolbar controls.
        for combo in (self.space_combo, self.grid_combo, self.rot_combo, self.view_combo):
            combo.setStyleSheet(qt_stylesheet_viewport_combo)
        self.snap_check.setStyleSheet(qt_stylesheet_viewport_check)

        layout.addWidget(toolbar)

        self.render_area = SmartProp3DRenderArea(document=document, parent=self)
        self.render_area.elementClicked.connect(self.elementClicked.emit)
        # Expanding (with no minimum) lets the viewport claim available space by
        # default yet still be dragged arbitrarily narrow.
        self.render_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.render_area)

        # Initialize defaults
        self._on_space_changed("World")
        self._on_snap_changed(Qt.Unchecked)
        self._on_grid_step_changed("8")
        self._on_rot_step_changed("15")
        self._on_display_groups_changed(True)
        self._on_show_widgets_changed(True)
        self._on_view_mode_changed("Textured")

    def _make_toggle_button(self, tooltip, icon_off, icon_on=None):
        """Create a compact checkable icon toggle button for the toolbar.

        If ``icon_on`` is given it is used for the checked state and ``icon_off``
        for the unchecked state; otherwise ``icon_off`` is used for both.
        """
        btn = QToolButton()
        btn.setCheckable(True)
        btn.setToolTip(tooltip)
        btn.setFixedSize(22, 22)
        btn.setIconSize(QSize(16, 16))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(_VIEWPORT_TOGGLE_STYLE)
        icon = QIcon()
        icon.addFile(icon_off, QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon.addFile(icon_on or icon_off, QSize(), QIcon.Mode.Normal, QIcon.State.On)
        btn.setIcon(icon)
        return btn

    def _on_view_mode_changed(self, text):
        self.render_area.shading_mode = text.lower()
        self.render_area.update()

    def _on_space_changed(self, text):
        self.render_area.coordinate_space = text
        self.render_area.update()

    def _on_snap_changed(self, state):
        self.render_area.snapping_enabled = (state == Qt.Checked or state == 2)

    def _on_grid_step_changed(self, text):
        try:
            self.render_area.grid_step = float(text)
            self.render_area.update()
        except ValueError:
            pass

    def _on_rot_step_changed(self, text):
        try:
            self.render_area.rotation_step = float(text)
        except ValueError:
            pass

    def _on_display_groups_changed(self, checked):
        self.render_area.display_groups = bool(checked)
        self.render_area.update_viewport()

    def _on_show_widgets_changed(self, checked):
        self.render_area.show_widgets = bool(checked)
        self.render_area.update()

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
        # Forward transform-mode keys (W/E/R) and the frame-selection key (F) to
        # the render area.
        if event.key() in (Qt.Key_W, Qt.Key_E, Qt.Key_R, Qt.Key_F):
            self.render_area.keyPressEvent(event)
        else:
            super().keyPressEvent(event)
