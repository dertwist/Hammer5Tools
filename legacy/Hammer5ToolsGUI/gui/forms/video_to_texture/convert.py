"""Sprite-sheet packing and .vmat authoring for the Video To Texture utility.

Qt-free on purpose: the packing maths are the part worth testing and need no
running QApplication. Frame decoding lives in decode.py because that half does
need QtMultimedia. The material itself goes through the shared csgo_complex.vfx
schema in unreal_porter rather than a private template, so shader parameter
names and Hammer's formatting stay defined in one place.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageSequence

from gui.forms.unreal_porter.vmat_writer import write_vmat

# Source 2 handles larger, but 4096 is the practical ceiling for a texture that
# is fully resident every frame; cell size is reduced until the sheet fits.
MAX_SHEET_SIZE = 4096
DEFAULT_FPS = 15.0


def read_animation_frames(path: str | Path) -> tuple[list[Image.Image], float]:
    """Frames and average fps of an animated GIF/WebP/APNG, via Pillow.

    A still image yields a single frame, which is a legitimate one-cell sheet.
    """
    frames: list[Image.Image] = []
    durations: list[float] = []
    with Image.open(path) as source:
        for frame in ImageSequence.Iterator(source):
            frames.append(frame.convert("RGBA"))
            # GIFs written by some encoders omit duration or use 0 (= "as fast
            # as possible"); browsers clamp those to 100ms and so do we.
            duration = frame.info.get("duration") or 0
            durations.append(duration if duration >= 10 else 100)
    if not frames:
        raise ValueError("The image contains no frames.")
    average = sum(durations) / len(durations)
    return frames, 1000.0 / average if average else DEFAULT_FPS


def grid_for(count: int) -> tuple[int, int]:
    """Columns and rows for `count` cells, matching the GIF2VMAT layout."""
    columns = max(1, int(math.sqrt(count)))
    return columns, math.ceil(count / columns)


def cell_size_for(frame_size: tuple[int, int], requested_width: int, count: int) -> tuple[int, int]:
    """Per-cell pixel size: aspect preserved, even, and small enough to fit the sheet."""
    width, height = frame_size
    columns, rows = grid_for(count)
    aspect = height / width if width else 1.0
    cell_width = max(2, requested_width)
    while True:
        cell_height = max(2, int(round(cell_width * aspect)) & ~1)
        cell_width = cell_width & ~1
        if cell_width * columns <= MAX_SHEET_SIZE and cell_height * rows <= MAX_SHEET_SIZE:
            return max(2, cell_width), cell_height
        cell_width //= 2
        if cell_width < 2:
            return 2, 2


def build_sheet(frames: list[Image.Image], cell: tuple[int, int]) -> Image.Image:
    """Paste every frame into a left-to-right, top-to-bottom grid."""
    columns, rows = grid_for(len(frames))
    cell_width, cell_height = cell
    sheet = Image.new("RGBA", (cell_width * columns, cell_height * rows), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        resized = frame.convert("RGBA").resize((cell_width, cell_height), Image.LANCZOS)
        sheet.paste(resized, ((index % columns) * cell_width, (index // columns) * cell_height))
    return sheet


def sample_evenly(frames: list, limit: int) -> list:
    """At most `limit` frames, evenly spread across the source."""
    if limit <= 0 or len(frames) <= limit:
        return frames
    step = len(frames) / limit
    return [frames[int(index * step)] for index in range(limit)]


def write_material(vmat_path: Path, color_reference: str, count: int, fps: float,
                   translucent: bool) -> None:
    """Author the animated csgo_complex.vfx material for a `count`-cell sheet."""
    columns, rows = grid_for(count)
    slots = {"color": color_reference}
    flags = {"F_TEXTURE_ANIMATION": "1"}
    if translucent:
        # The sheet's own alpha drives translucency. F_ALPHA_TEST is pinned off
        # because write_vmat otherwise infers it from a bound opacity slot, and
        # csgo_complex forbids alpha test and translucency together.
        slots["opacity"] = color_reference
        flags.update({"F_TRANSLUCENT": "1", "F_ALPHA_TEST": "0"})
    write_vmat(
        str(vmat_path),
        slots,
        shader="csgo_complex.vfx",
        feature_flags=flags,
        extra_params={
            "g_flAnimationTimePerFrame": 1.0 / max(fps, 0.01),
            "g_nNumAnimationCells": count,
            "g_vAnimationGrid": (columns, rows),
        },
    )


def material_reference(texture_path: Path, content_dir: Path | None) -> str:
    """The addon-relative 'materials/...' path a .vmat must reference."""
    if content_dir is not None:
        try:
            return texture_path.resolve().relative_to(content_dir.resolve()).as_posix()
        except ValueError:
            pass
    return texture_path.as_posix()


def convert_frames(
    frames: list[Image.Image],
    fps: float,
    output_dir: Path,
    name: str,
    requested_cell_width: int,
    content_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Write <name>_color.png and <name>.vmat, returning both paths."""
    if not frames:
        raise ValueError("No frames to convert.")
    output_dir.mkdir(parents=True, exist_ok=True)
    cell = cell_size_for(frames[0].size, requested_cell_width, len(frames))
    sheet = build_sheet(frames, cell)

    texture_path = output_dir / f"{name}_color.png"
    sheet.save(texture_path)

    translucent = sheet.getextrema()[3][0] < 255
    vmat_path = output_dir / f"{name}.vmat"
    reference = material_reference(texture_path, content_dir)
    write_material(vmat_path, reference, len(frames), fps, translucent)
    return texture_path, vmat_path
