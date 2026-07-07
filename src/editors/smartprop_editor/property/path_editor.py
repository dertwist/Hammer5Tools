from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QDialog, QVBoxLayout,
    QTableWidget, QAbstractItemView, QHeaderView, QLineEdit,
    QSplitter, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDoubleValidator

from src.styles.common import apply_stylesheets
from src.editors.smartprop_editor.viewport_3d.path_render_area import PathEditor3DRenderArea


# --- Main Dialog UI with Splitter ---

class _PathEditorDialog(QDialog):
    """Path editor: an OpenGL 3D viewport (shared with the SmartProp viewport)
    on the left, a coordinate table on the right.

    Control points are shown as 3D spheres and the path between them as a smooth
    bezier/Catmull-Rom curve; there is no 2D overlay layer.
    """

    def __init__(self, points, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Path Editor")
        self.resize(800, 450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        # Normalize to plain float lists so the gizmo can mutate points in place.
        self._points = [[float(c) for c in (list(p) + [0.0, 0.0, 0.0])[:3]] for p in points]
        self._block_updates = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(splitter)

        # ---- Left side: 3D Viewport ----
        viewport_container = QWidget()
        vp_layout = QVBoxLayout(viewport_container)
        vp_layout.setContentsMargins(0, 0, 0, 0)
        vp_layout.setSpacing(0)

        # Viewport toolbar
        vp_toolbar = QWidget()
        vp_toolbar.setObjectName('vp_toolbar')
        vp_toolbar.setStyleSheet("background-color: #2D2D2D;")
        vpt_layout = QHBoxLayout(vp_toolbar)
        vpt_layout.setContentsMargins(6, 3, 6, 3)

        hint = QLabel("MMB: Orbit  |  Shift+MMB: Pan  |  Wheel: Zoom  |  W: Move  F: Frame")
        hint.setStyleSheet("color: #9D9D9D; font: 8pt 'Segoe UI';")
        vpt_layout.addWidget(hint)
        vpt_layout.addStretch()

        self.frame_btn = QPushButton("Frame")
        self.frame_btn.setToolTip("Fit all points into view (F)")
        self.frame_btn.clicked.connect(lambda: self.viewport.frame_objects())
        vpt_layout.addWidget(self.frame_btn)

        vp_layout.addWidget(vp_toolbar)

        self.viewport = PathEditor3DRenderArea(self._points)
        self.viewport.frame_objects()
        self.viewport.points_changed.connect(self._on_viewport_modified)
        self.viewport.selection_changed.connect(self._on_viewport_selection)
        vp_layout.addWidget(self.viewport)

        splitter.addWidget(viewport_container)

        # ---- Right side: Data Table ----
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 8, 8, 8)

        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Add Point")
        self.add_btn.clicked.connect(self._add_point)
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self._remove_point)

        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.remove_btn)
        toolbar.addStretch()
        right_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Z"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        right_layout.addWidget(self.table)

        splitter.addWidget(right_container)
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

    def _on_viewport_modified(self):
        """A gizmo drag moved a point; mirror it into the table without looping."""
        self._block_updates = True
        idx = self.viewport.selected_index
        if 0 <= idx < len(self._points) and idx < self.table.rowCount():
            pt = self._points[idx]
            for i in range(3):
                field = self.table.cellWidget(idx, i)
                if field:
                    field.setText(f"{pt[i]:.1f}")
        self._block_updates = False

    def _on_viewport_selection(self, idx):
        """A sphere was clicked in the viewport; select its row in the table."""
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

    def _on_field_changed(self, row, col, text):
        if self._block_updates:
            return
        if 0 <= row < len(self._points):
            try:
                val = float(text)
            except ValueError:
                return
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
            field = QLineEdit()
            field.setValidator(QDoubleValidator(-999999.0, 999999.0, 3))
            field.setAlignment(Qt.AlignCenter)
            val = float(pt[i]) if i < len(pt) else 0.0
            field.setText(f"{val:.1f}")
            field.textChanged.connect(lambda v, r=row, c=i: self._on_field_changed(r, c, v))
            self.table.setCellWidget(row, i, field)

    def _add_point(self):
        # Infer a reasonable coordinate for the next point.
        new_pt = [0.0, 0.0, 0.0]
        if len(self._points) > 0:
            last = self._points[-1]
            new_pt = [last[0] + 100.0, last[1], last[2]]  # step across X

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

        for r in rows:
            if 0 <= r < len(self._points):
                del self._points[r]

        # Rebuild every row from scratch. Removing rows in place shifts the
        # surviving cell widgets up but leaves their textChanged closures bound
        # to the old row index, so later edits would write to the wrong point.
        # _populate() recreates the rows (and closures) against the new indices.
        self._populate()

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
            QTableWidget { background-color: #151515; color: #E3E3E3; border: none; gridline-color: #2D2D30; }
            QHeaderView::section { background-color: #252526; color: #9D9D9D; border: none; padding: 0px; }
            QPushButton { background-color: #333333; color: #E3E3E3; border: 1px solid #555555; border-radius: 2px; padding: 4px 12px; }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #222222; }
            QTableWidget QLineEdit { background-color: #252526; color: #FFFFFF; border: none; padding: 0px 0px; font-size: 4px; }
        """)

        # apply_stylesheets() sets a QLineEdit-specific stylesheet directly on each field,
        # which overrides the dialog-level "QTableWidget QLineEdit" rule above. Re-apply
        # the path editor's field style directly on each cell so it actually takes effect.
        field_style = "background-color: #151515; color: #FFFFFF; border: none; padding: 0px 0px; font-size: 12px;"
        for row in range(dialog.table.rowCount()):
            for col in range(dialog.table.columnCount()):
                field = dialog.table.cellWidget(row, col)
                if field:
                    field.setStyleSheet(field_style)

        if dialog.exec() == QDialog.Accepted:
            self._path_points = dialog.get_points()
            self.edited.emit()
