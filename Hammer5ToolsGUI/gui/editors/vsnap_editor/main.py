"""VSnap experiments: integrated VSnap generation and preview editor.

Experimental project, disabled in dev and stable releases.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.bridge import CoreBridge
from gui.editors.vsnap_editor.document import (
    DEFAULT_LIGHTNING_BRANCH_PROBABILITY,
    DEFAULT_LIGHTNING_END,
    DEFAULT_LIGHTNING_POINT_COUNT,
    DEFAULT_LIGHTNING_RADIUS,
    DEFAULT_LIGHTNING_RECURSION_DEPTH,
    DEFAULT_LIGHTNING_ROUGHNESS,
    DEFAULT_LIGHTNING_SEED,
    DEFAULT_LIGHTNING_START,
    VSnapDocument,
    generate_default_lightning,
)
from gui.editors.vsnap_editor.viewport import VSnapViewport
from gui.widgets import FloatWidget

log = logging.getLogger(__name__)


class PointTableModel(QAbstractTableModel):
    """Virtual read-only view of the Core snapshot streams."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.document = None
        self.columns = []

    def set_document(self, document) -> None:
        self.beginResetModel()
        self.document = document
        self.columns = []
        for stream_index, stream in enumerate(document.streams):
            if stream.type == "generic_float":
                self.columns.append((stream_index, None, stream.name))
            else:
                for component, suffix in enumerate(("x", "y", "z")):
                    self.columns.append((stream_index, component, f"{stream.name}.{suffix}"))
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() or self.document is None else self.document.count

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self.document is None or role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        stream_index, component, _ = self.columns[index.column()]
        value = self.document.streams[stream_index].values[index.row()]
        number = value if component is None else value[component]
        return f"{number:.6g}"

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        return str(section) if orientation == Qt.Vertical else self.columns[section][2]


class VSnapEditorMainWindow(QWidget):
    """VSnap experiments: integrated VSnap generation and preview editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("h5Component", "vsnapEditor")
        self.document = VSnapDocument(self)
        self._draw_points = []
        self._draw_flush_timer = QTimer(self)
        self._draw_flush_timer.setSingleShot(True)
        self._draw_flush_timer.setInterval(50)
        self._draw_flush_timer.timeout.connect(self._flush_drawn_points)
        self._lightning_regen_timer = QTimer(self)
        self._lightning_regen_timer.setSingleShot(True)
        self._lightning_regen_timer.setInterval(60)
        self._lightning_regen_timer.timeout.connect(self._regenerate_lightning_from_controls)
        self._build_ui()
        self.document.changed.connect(self._refresh)
        self.document.path_changed.connect(self._update_title)
        self.document.dirty_changed.connect(lambda _: self._update_title())
        self._run(
            lambda: self.document.replace(generate_default_lightning(), dirty=False),
            "Could not initialize the lightning preset",
        )
        self._refresh()
        self.viewport.set_control_points(DEFAULT_LIGHTNING_START, DEFAULT_LIGHTNING_END)
        QTimer.singleShot(0, self.viewport.fit_view)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.menu_bar = QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)
        self.file_menu = QMenu("File", self.menu_bar)
        self.menu_bar.addMenu(self.file_menu)
        self.file_menu.addAction(QAction("New", self, triggered=self.new_file))
        self.file_menu.addAction(QAction("Open VSnap…", self, triggered=self.open_file_dialog))
        self.file_menu.addSeparator()
        self.file_menu.addAction(QAction("Save", self, triggered=self.save))
        self.file_menu.addAction(QAction("Save As…", self, triggered=self.save_as))
        self.generate_menu = QMenu("Generate", self.menu_bar)
        self.menu_bar.addMenu(self.generate_menu)
        self.generate_menu.addAction(QAction("Lightning", self, triggered=self.generate_lightning))
        self.generate_menu.addAction(QAction("Primitive", self, triggered=self.generate_primitive))
        outer.setMenuBar(self.menu_bar)

        splitter = QSplitter(Qt.Horizontal, self)
        controls = QWidget(splitter)
        controls.setProperty("h5Component", "vsnapControls")
        controls_layout = QVBoxLayout(controls)

        primitive_group = QGroupBox("Primitive generation", controls)
        primitive_form = QFormLayout(primitive_group)
        self.primitive_combo = QComboBox()
        self.primitive_combo.addItems(("Sphere", "Box", "Plane", "Ring"))
        self.count_spin = FloatWidget(int_output=True, slider_range=[1, 4096], value=512, only_positive=True,
                                      spacer_enable=False)
        self.size_spin = FloatWidget(slider_range=[0.0, 1024.0], value=128.0, only_positive=True, spacer_enable=False)
        generate_button = QPushButton("Generate")
        generate_button.clicked.connect(self.generate_primitive)
        primitive_form.addRow("Shape", self.primitive_combo)
        primitive_form.addRow("Points", self.count_spin)
        primitive_form.addRow("Size", self.size_spin)
        primitive_form.addRow(generate_button)
        controls_layout.addWidget(primitive_group)

        lighting_group = QGroupBox("Procedural lightning", controls)
        lighting_form = QFormLayout(lighting_group)
        start_row, self.lightning_start_spins = self._make_vector_inputs(DEFAULT_LIGHTNING_START)
        end_row, self.lightning_end_spins = self._make_vector_inputs(DEFAULT_LIGHTNING_END)
        self.lightning_points = FloatWidget(
            int_output=True, slider_range=[8, 512], value=DEFAULT_LIGHTNING_POINT_COUNT,
            only_positive=True, lock_range=True, spacer_enable=False,
        )
        self.lightning_roughness = FloatWidget(
            slider_range=[0.0, 256.0], value=DEFAULT_LIGHTNING_ROUGHNESS, only_positive=True, spacer_enable=False,
        )
        self.lightning_branch_probability = FloatWidget(
            slider_range=[0.0, 1.0], value=DEFAULT_LIGHTNING_BRANCH_PROBABILITY,
            lock_range=True, spacer_enable=False,
        )
        self.lightning_depth = FloatWidget(
            int_output=True, slider_range=[0, 4], value=DEFAULT_LIGHTNING_RECURSION_DEPTH,
            lock_range=True, spacer_enable=False,
        )
        self.lightning_radius = FloatWidget(
            slider_range=[0.1, 64.0], value=DEFAULT_LIGHTNING_RADIUS, only_positive=True, spacer_enable=False,
        )
        self.lightning_seed = FloatWidget(
            int_output=True, slider_range=[0, 1_000_000], value=DEFAULT_LIGHTNING_SEED,
            only_positive=True, spacer_enable=False,
        )
        light_button = QPushButton("Generate lightning")
        light_button.clicked.connect(self.generate_lightning)
        lighting_form.addRow("Start XYZ", start_row)
        lighting_form.addRow("End XYZ", end_row)
        lighting_form.addRow("Trunk points", self.lightning_points)
        lighting_form.addRow("Roughness", self.lightning_roughness)
        lighting_form.addRow("Branch chance", self.lightning_branch_probability)
        lighting_form.addRow("Branch depth", self.lightning_depth)
        lighting_form.addRow("Root radius", self.lightning_radius)
        lighting_form.addRow("Seed", self.lightning_seed)
        lighting_form.addRow(light_button)
        controls_layout.addWidget(lighting_group)

        self.status_label = QLabel()
        self.status_label.setProperty("h5Component", "vsnapStatus")
        controls_layout.addWidget(self.status_label)
        controls_layout.addStretch(1)

        center = QSplitter(Qt.Vertical, splitter)
        self.viewport = VSnapViewport(center)
        self.viewport.points_drawn.connect(self._append_drawn_points)
        self.viewport.control_point_moved.connect(self._on_control_point_moved)
        self.table_model = PointTableModel(self)
        self.table = QTableView(center)
        self.table.setModel(self.table_model)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        center.addWidget(self.viewport)
        center.addWidget(self.table)
        center.setSizes((650, 250))
        splitter.addWidget(controls)
        splitter.addWidget(center)
        splitter.setSizes((320, 1000))
        outer.addWidget(splitter, 1)

    def _make_vector_inputs(self, values: tuple[float, float, float]):
        row = QWidget(self)
        row.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        spins = []
        for value in values:
            spin = FloatWidget(slider_range=[-512.0, 512.0], value=float(value), spacer_enable=False)
            spin.setMinimumWidth(0)
            spin.edited.connect(self._on_endpoint_fields_changed)
            layout.addWidget(spin)
            spins.append(spin)
        return row, tuple(spins)

    def _refresh(self) -> None:
        data = self.document.data
        self.viewport.set_document(data)
        self.table_model.set_document(data)
        self.status_label.setText(f"{data.count:,} points · {len(data.streams)} streams")
        self._update_title()

    def _update_title(self, _path: str = "") -> None:
        marker = "*" if self.document.dirty else ""
        self.setWindowTitle(f"{self.document.label()}{marker}")

    def new_file(self) -> None:
        if self._confirm_discard():
            self._draw_points = []
            self._set_endpoint_fields(DEFAULT_LIGHTNING_START, DEFAULT_LIGHTNING_END)
            self._run(self.document.new, "Could not create the lightning preset")
            self.viewport.set_control_points(DEFAULT_LIGHTNING_START, DEFAULT_LIGHTNING_END)
            self.viewport.fit_view()

    def open_file_dialog(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open VSnap", "", "Particle snapshots (*.vsnap)")
        if path:
            self.open_file(path)

    def open_file(self, path: str) -> None:
        self._draw_points = []
        self._run(lambda: self.document.open(path), "Could not open VSnap")

    def save(self) -> None:
        if self.document.path is None:
            self.save_as()
            return
        self._run(self.document.save, "Could not save VSnap")

    def save_as(self) -> None:
        initial = str(self.document.path or Path.cwd() / "snapshot.vsnap")
        path, _ = QFileDialog.getSaveFileName(self, "Save VSnap", initial, "Particle snapshots (*.vsnap)")
        if path:
            if not path.lower().endswith(".vsnap"):
                path += ".vsnap"
            self._run(lambda: self.document.save(path), "Could not save VSnap")

    def generate_primitive(self) -> None:
        self._draw_points = []
        self._run(lambda: self.document.replace(CoreBridge.instance().generate_vsnap(
            self.primitive_combo.currentText(), int(self.count_spin.value), float(self.size_spin.value),
        )), "Could not generate primitive")

    def _append_drawn_points(self, points: list) -> None:
        """Collect brush stamps and rebuild once the stroke pauses."""
        self._draw_points.extend(points)
        self._draw_flush_timer.start()

    def _flush_drawn_points(self) -> None:
        if not self._draw_points:
            return
        self._run(lambda: self.document.replace(
            CoreBridge.instance().generate_drawn_vsnap(self._draw_points),
        ), "Could not add the drawn points")

    def generate_lightning(self) -> None:
        self._draw_points = []
        start, end = self._endpoint_values()
        self._run(lambda: self.document.replace(CoreBridge.instance().generate_vsnap_lightning(
            start,
            end,
            int(self.lightning_points.value),
            float(self.lightning_roughness.value),
            float(self.lightning_branch_probability.value),
            int(self.lightning_depth.value),
            float(self.lightning_radius.value),
            int(self.lightning_seed.value),
        )), "Could not generate lightning")
        self.viewport.set_control_points(start, end)

    def _endpoint_values(self) -> tuple[tuple[float, ...], tuple[float, ...]]:
        return (
            tuple(float(spin.value) for spin in self.lightning_start_spins),
            tuple(float(spin.value) for spin in self.lightning_end_spins),
        )

    def _set_endpoint_fields(self, start, end) -> None:
        for spin, value in zip(self.lightning_start_spins, start):
            spin.set_value(float(value))
        for spin, value in zip(self.lightning_end_spins, end):
            spin.set_value(float(value))

    def _on_endpoint_fields_changed(self) -> None:
        start, end = self._endpoint_values()
        self.viewport.set_control_points(start, end)
        self._lightning_regen_timer.start()

    def _on_control_point_moved(self, name: str, point: tuple) -> None:
        start, end = self._endpoint_values()
        if name == "start":
            start = point
        else:
            end = point
        self._set_endpoint_fields(start, end)
        self._lightning_regen_timer.start()

    def _regenerate_lightning_from_controls(self) -> None:
        self.generate_lightning()

    def unsaved_files(self) -> list[tuple[str, object]]:
        return [(self.document.label(), self.save)] if self.document.dirty else []

    def _confirm_discard(self) -> bool:
        if not self.document.dirty:
            return True
        result = QMessageBox.question(
            self, "Unsaved VSnap", "Discard the unsaved snapshot changes?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        return result == QMessageBox.Yes

    def _run(self, operation, title: str) -> None:
        try:
            operation()
        except Exception as error:
            log.exception(title)
            QMessageBox.critical(self, title, str(error))
