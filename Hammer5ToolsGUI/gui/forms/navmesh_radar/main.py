from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from core.bridge import CoreBridge, NavMeshRadarResult
from gui.common import apply_title_bar_theme
from gui.settings.common import (
    addon_content_dir,
    addon_game_dir,
    get_addon_name,
    get_cs2_path,
)

log = logging.getLogger(__name__)


class NavMeshRadarWorker(QThread):
    """Runs the NativeAOT generation call without blocking Qt's GUI thread."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        vpk_path: Path,
        main_vmap_path: Path,
        mode: str,
        offset: float = 16.0,
        add_prefab_reference: bool = True,
        collapse_faces: bool = True,
        collapse_faces_into_ngons: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._vpk_path = vpk_path
        self._main_vmap_path = main_vmap_path
        self._mode = mode
        self._offset = offset
        self._add_prefab_reference = add_prefab_reference
        self._collapse_faces = collapse_faces
        self._collapse_faces_into_ngons = collapse_faces_into_ngons

    def run(self) -> None:
        try:
            result = CoreBridge.instance().generate_navmesh_radar(
                str(self._vpk_path),
                str(self._main_vmap_path),
                self._mode,
                offset=self._offset,
                add_prefab_reference=self._add_prefab_reference,
                collapse_faces=self._collapse_faces,
                collapse_faces_into_ngons=self._collapse_faces_into_ngons,
            )
            if result.generated_vmap_path is None:
                message = "\n".join(result.diagnostics) or "Core did not return a generated map."
                raise RuntimeError(message)
            self.succeeded.emit(result)
        except Exception as error:
            log.exception("NavMesh Radar generation failed")
            self.failed.emit(str(error))


class NavMeshRadarDialog(QDialog):
    """Configures and runs radar-face generation for the active addon map."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("NavMesh Radar")
        self.setMinimumWidth(620)
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)
        apply_title_bar_theme(self)

        self._worker: NavMeshRadarWorker | None = None
        self._vpk_path: Path | None = None
        self._main_vmap_path: Path | None = None
        self._prefab_present = False

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setProperty("h5Component", "legacyCombobox")
        self.mode_combo.addItem("Baked bomb damage", "baked_bomb_damage")
        self.mode_combo.addItem("NavMesh", "navmesh_offset")
        self.mode_combo.currentIndexChanged.connect(self._update_mode_options)
        form.addRow("Source:", self.mode_combo)

        self.vpk_field = QLineEdit()
        self.vpk_field.setReadOnly(True)
        form.addRow("Compiled VPK:", self.vpk_field)

        self.output_field = QLineEdit()
        self.output_field.setReadOnly(True)
        form.addRow("Generated map:", self.output_field)
        layout.addLayout(form)

        options_layout = QHBoxLayout()
        options_layout.setSpacing(6)

        self.add_prefab_checkbox = QCheckBox("Add prefab entity to main map")
        self.add_prefab_checkbox.setProperty("h5Component", "legacyCheckbox")
        self.add_prefab_checkbox.setChecked(True)
        self.add_prefab_checkbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        options_layout.addWidget(self.add_prefab_checkbox, 1)

        self.collapse_faces_checkbox = QCheckBox("Collapse faces")
        self.collapse_faces_checkbox.setProperty("h5Component", "legacyCheckbox")
        self.collapse_faces_checkbox.setChecked(True)
        self.collapse_faces_checkbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.collapse_faces_checkbox.toggled.connect(self._update_collapse_options)
        options_layout.addWidget(self.collapse_faces_checkbox, 1)

        self.collapse_ngons_checkbox = QCheckBox("Collapse faces into N-gons")
        self.collapse_ngons_checkbox.setProperty("h5Component", "legacyCheckbox")
        self.collapse_ngons_checkbox.setChecked(False)
        self.collapse_ngons_checkbox.setToolTip(
            "Dissolve internal edges between nearby collapsed faces on the same height layer."
        )
        self.collapse_ngons_checkbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        options_layout.addWidget(self.collapse_ngons_checkbox, 1)

        self.remove_offset_checkbox = QCheckBox("Remove offset")
        self.remove_offset_checkbox.setProperty("h5Component", "legacyCheckbox")
        self.remove_offset_checkbox.setChecked(False)
        self.remove_offset_checkbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        options_layout.addWidget(self.remove_offset_checkbox, 1)

        layout.addLayout(options_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.close_button = QPushButton("Close")
        self.close_button.setProperty("h5Component", "legacyButton")
        self.close_button.clicked.connect(self.close)
        self.generate_button = QPushButton("Generate")
        self.generate_button.setProperty("h5Component", "legacyButton")
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self._start_generation)
        buttons.addWidget(self.close_button)
        buttons.addWidget(self.generate_button)
        layout.addLayout(buttons)

        self._refresh_paths()
        self._update_mode_options()

    def _update_mode_options(self) -> None:
        is_navmesh = self.mode_combo.currentData() == "navmesh_offset"
        self.remove_offset_checkbox.setVisible(is_navmesh)
        self.collapse_faces_checkbox.setVisible(not is_navmesh)
        self.collapse_ngons_checkbox.setVisible(not is_navmesh)
        self._update_collapse_options(self.collapse_faces_checkbox.isChecked())

    def _update_collapse_options(self, collapse_faces: bool) -> None:
        self.collapse_ngons_checkbox.setEnabled(collapse_faces)
        if not collapse_faces:
            self.collapse_ngons_checkbox.setChecked(False)

    def _refresh_paths(self) -> None:
        addon = get_addon_name()
        content_root = addon_content_dir(addon)
        game_root = addon_game_dir(addon)
        cs2_path_str = get_cs2_path()
        cs2_root = Path(cs2_path_str) if cs2_path_str else None

        self._main_vmap_path = (
            content_root / "maps" / f"{addon}.vmap" if content_root is not None else None
        )
        self._vpk_path = game_root / "maps" / f"{addon}.vpk" if game_root is not None else None
        generated_path = None
        prefab_present = False
        if self._main_vmap_path is not None:
            try:
                status = CoreBridge.instance().navmesh_radar_status(str(self._main_vmap_path))
            except Exception:
                log.exception("Could not read the main map's radar prefab status")
            else:
                if status.generated_vmap_path is not None:
                    generated_path = Path(status.generated_vmap_path)
                prefab_present = status.prefab_present
        self._prefab_present = prefab_present

        if self._vpk_path is not None:
            try:
                vpk_display = (
                    self._vpk_path.relative_to(cs2_root).as_posix()
                    if cs2_root
                    else self._vpk_path.as_posix()
                )
            except ValueError:
                vpk_display = self._vpk_path.as_posix()
            self.vpk_field.setText(vpk_display)
            self.vpk_field.setToolTip(str(self._vpk_path))
        else:
            self.vpk_field.setText("CS2 path is not configured")
            self.vpk_field.setToolTip("")

        if generated_path is not None:
            try:
                output_display = (
                    generated_path.relative_to(cs2_root).as_posix()
                    if cs2_root
                    else generated_path.as_posix()
                )
            except ValueError:
                output_display = generated_path.as_posix()
            self.output_field.setText(output_display)
            self.output_field.setToolTip(str(generated_path))
        elif self._main_vmap_path is None:
            self.output_field.setText("CS2 path is not configured")
            self.output_field.setToolTip("")
        else:
            self.output_field.setText("Main map not found")
            self.output_field.setToolTip(str(self._main_vmap_path))

        self._apply_prefab_state()

    def _apply_prefab_state(self) -> None:
        """A map that already references the sub-map needs no second prefab."""
        if self._prefab_present:
            self.add_prefab_checkbox.setChecked(False)
            self.add_prefab_checkbox.setEnabled(False)
            self.add_prefab_checkbox.setToolTip(
                "The main map already references the generated radar."
            )
            return
        self.add_prefab_checkbox.setEnabled(True)
        self.add_prefab_checkbox.setToolTip("")

    def _start_generation(self) -> None:
        self._refresh_paths()
        if self._vpk_path is None or self._main_vmap_path is None:
            QMessageBox.warning(self, "NavMesh Radar", "Configure the CS2 path and active addon first.")
            return
        if not self._vpk_path.is_file():
            QMessageBox.warning(self, "NavMesh Radar", f"Compiled addon VPK not found:\n{self._vpk_path}")
            return
        if not self._main_vmap_path.is_file():
            QMessageBox.warning(self, "NavMesh Radar", f"Main addon map not found:\n{self._main_vmap_path}")
            return

        self.generate_button.setEnabled(False)
        self.close_button.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.remove_offset_checkbox.setEnabled(False)
        self.collapse_faces_checkbox.setEnabled(False)
        self.collapse_ngons_checkbox.setEnabled(False)
        self.add_prefab_checkbox.setEnabled(False)
        self.progress_bar.setRange(0, 0)

        offset = 16.0 if self.remove_offset_checkbox.isChecked() else 0.0
        collapse_faces = self.collapse_faces_checkbox.isChecked()
        collapse_faces_into_ngons = self.collapse_ngons_checkbox.isChecked()

        self._worker = NavMeshRadarWorker(
            self._vpk_path,
            self._main_vmap_path,
            str(self.mode_combo.currentData()),
            offset=offset,
            add_prefab_reference=self.add_prefab_checkbox.isChecked(),
            collapse_faces=collapse_faces,
            collapse_faces_into_ngons=collapse_faces_into_ngons,
            parent=self,
        )
        self._worker.succeeded.connect(self._generation_succeeded)
        self._worker.failed.connect(self._generation_failed)
        self._worker.finished.connect(self._worker_finished)
        self._worker.start()

    def _generation_succeeded(self, result: NavMeshRadarResult) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        reference_info = "\n\nAdded prefab reference to the main map." if result.reference_added else ""
        QMessageBox.information(
            self,
            "NavMesh Radar complete",
            f"Generated {result.face_count:,} editable faces.{reference_info}\n\n"
            f"Output:\n{result.generated_vmap_path}",
        )

    def _generation_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "NavMesh Radar failed", message)

    def _worker_finished(self) -> None:
        self.generate_button.setEnabled(True)
        self.close_button.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.remove_offset_checkbox.setEnabled(True)
        self.collapse_faces_checkbox.setEnabled(True)
        self._update_mode_options()
        self._refresh_paths()
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def closeEvent(self, event) -> None:
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "NavMesh Radar", "Generation is still running.")
            event.ignore()
            return
        super().closeEvent(event)
