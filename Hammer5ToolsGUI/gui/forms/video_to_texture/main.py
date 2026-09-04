"""The 'Video To Texture' utility dialog.

Packs a video or animated image into a Source 2 sprite sheet plus a
csgo_complex.vfx material with texture animation enabled.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from gui.common import apply_title_bar_theme
from gui.forms.video_to_texture.convert import (
    convert_frames,
    material_reference,
    read_animation_frames,
    sample_evenly,
)
from gui.forms.video_to_texture.decode import IMAGE_SUFFIXES, input_filter, read_video_frames
from gui.settings.common import addon_content_dir, get_addon_name

log = logging.getLogger(__name__)

TITLE = "Video To Texture"
CELL_SIZES = (64, 128, 256, 512, 1024)


class VideoToTextureDialog(QDialog):
    """Turns a video or GIF into an animated .vmat for the active addon."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(620)
        self.setAttribute(Qt.WA_DeleteOnClose)
        apply_title_bar_theme(self)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        source_row = QHBoxLayout()
        self.source_field = QLineEdit()
        self.source_field.setReadOnly(True)
        self.source_field.setPlaceholderText("Video (mp4, mov, mkv, webm, ...) or animated GIF")
        source_button = QPushButton("Browse")
        source_button.setProperty("h5Component", "legacyButton")
        source_button.clicked.connect(self._browse_source)
        source_row.addWidget(self.source_field, 1)
        source_row.addWidget(source_button)
        form.addRow("Source:", source_row)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Material name")
        form.addRow("Material name:", self.name_field)

        output_row = QHBoxLayout()
        self.output_field = QLineEdit()
        self.output_field.setReadOnly(True)
        output_button = QPushButton("Browse")
        output_button.setProperty("h5Component", "legacyButton")
        output_button.clicked.connect(self._browse_output)
        output_row.addWidget(self.output_field, 1)
        output_row.addWidget(output_button)
        form.addRow("Output folder:", output_row)

        self.cell_combo = QComboBox()
        self.cell_combo.setProperty("h5Component", "legacyCombobox")
        for size in CELL_SIZES:
            self.cell_combo.addItem(f"{size} px", size)
        self.cell_combo.setCurrentIndex(CELL_SIZES.index(256))
        self.cell_combo.setToolTip("Width of one animation cell. Height follows the source aspect.")
        form.addRow("Frame size:", self.cell_combo)

        self.frames_spin = QSpinBox()
        self.frames_spin.setRange(1, 256)
        self.frames_spin.setValue(64)
        self.frames_spin.setToolTip("Frames sampled evenly across the source.")
        form.addRow("Max frames:", self.frames_spin)

        self.fps_spin = QDoubleSpinBox()
        self.fps_spin.setRange(0.0, 240.0)
        self.fps_spin.setDecimals(2)
        self.fps_spin.setValue(0.0)
        self.fps_spin.setSpecialValueText("Source")
        self.fps_spin.setToolTip("Playback rate written into the material. 0 keeps the source rate.")
        form.addRow("Frame rate:", self.fps_spin)

        layout.addLayout(form)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        layout.addWidget(self.progress_bar)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_button = QPushButton("Close")
        close_button.setProperty("h5Component", "legacyButton")
        close_button.clicked.connect(self.close)
        self.convert_button = QPushButton("Convert")
        self.convert_button.setProperty("h5Component", "legacyButton")
        self.convert_button.setDefault(True)
        self.convert_button.clicked.connect(self._convert)
        buttons.addWidget(close_button)
        buttons.addWidget(self.convert_button)
        layout.addLayout(buttons)

        self._output_dir: Path | None = None
        self._set_output_dir(self._default_output_dir())

    @staticmethod
    def _default_output_dir() -> Path | None:
        content = addon_content_dir(get_addon_name())
        return content / "materials" if content is not None else None

    def _set_output_dir(self, path: Path | None) -> None:
        """Keep the real path, show it addon-relative so the field reads like a vmat reference."""
        self._output_dir = path
        if path is None:
            self.output_field.setText("")
            self.output_field.setToolTip("No addon selected")
            return
        self.output_field.setText(material_reference(path, addon_content_dir(get_addon_name())))
        self.output_field.setToolTip(str(path))

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select a video or animation", "", input_filter())
        if not path:
            return
        self.source_field.setText(path)
        if not self.name_field.text().strip():
            self.name_field.setText(Path(path).stem.lower().replace(" ", "_"))

    def _browse_output(self) -> None:
        start = str(self._output_dir) if self._output_dir is not None else ""
        path = QFileDialog.getExistingDirectory(self, "Select the output folder", start)
        if path:
            self._set_output_dir(Path(path))

    def _set_progress(self, value: int, message: str, detail: str = "") -> None:
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(message)
        self.progress_bar.setToolTip(detail)

    def _read_frames(self, source: Path):
        """Frames and fps, from Pillow for animated images and QtMultimedia otherwise."""
        limit = self.frames_spin.value()
        if source.suffix.lower() in IMAGE_SUFFIXES:
            self._set_progress(10, "Reading frames...")
            frames, fps = read_animation_frames(source)
            trimmed = sample_evenly(frames, limit)
            # Dropping frames shortens the clip unless the rate drops with it.
            return trimmed, fps * len(trimmed) / len(frames)
        return read_video_frames(
            source,
            limit,
            progress=lambda done, total: self._set_progress(
                int(done / total * 80), f"Decoding frame {done}/{total}..."
            ),
        )

    def _convert(self) -> None:
        source_text = self.source_field.text().strip()
        name = self.name_field.text().strip()
        if not source_text or not Path(source_text).is_file():
            self._set_progress(0, "Select a source video or animation first.")
            return
        if not name:
            self._set_progress(0, "Enter a material name.")
            return
        if self._output_dir is None:
            self._set_progress(0, "Select an output folder.")
            return

        self.convert_button.setEnabled(False)
        try:
            frames, fps = self._read_frames(Path(source_text))
            self._set_progress(90, "Packing sprite sheet...")
            texture_path, vmat_path = convert_frames(
                frames,
                self.fps_spin.value() or fps,
                self._output_dir,
                name,
                self.cell_combo.currentData(),
                content_dir=addon_content_dir(get_addon_name()),
            )
        except Exception as error:
            log.exception("Video To Texture conversion failed")
            self._set_progress(0, f"Failed: {error}")
            return
        finally:
            self.convert_button.setEnabled(True)

        content = addon_content_dir(get_addon_name())
        self._set_progress(
            100,
            f"Done - {material_reference(vmat_path, content)} ({len(frames)} frames)",
            f"{vmat_path}\n{texture_path}",
        )
