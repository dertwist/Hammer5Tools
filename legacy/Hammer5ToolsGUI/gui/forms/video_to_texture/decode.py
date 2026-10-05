"""Frame extraction from any format QtMultimedia can play.

QMediaPlayer decodes asynchronously and only on a thread with a running event
loop, so this seeks the player from the GUI thread and pumps a nested QEventLoop
per frame -- the same approach the loading editor's MP4 recorder already uses.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink

log = logging.getLogger(__name__)

# Formats Pillow decodes as animations; everything else goes through QMediaPlayer.
IMAGE_SUFFIXES = {".gif", ".webp", ".apng", ".png"}
VIDEO_SUFFIXES = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".m4v", ".mpg", ".mpeg", ".ts")

_LOAD_TIMEOUT_MS = 15000
_FRAME_TIMEOUT_MS = 5000


def input_filter() -> str:
    """QFileDialog filter covering every supported input."""
    videos = " ".join(f"*{suffix}" for suffix in VIDEO_SUFFIXES)
    images = " ".join(f"*{suffix}" for suffix in sorted(IMAGE_SUFFIXES))
    return (
        f"Video and animation ({videos} {images});;"
        f"Video ({videos});;Animation ({images});;All files (*)"
    )


def _spin(predicate, timeout_ms: int) -> bool:
    """Run the event loop until predicate() is true or the timeout expires."""
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: predicate() and loop.quit())
    timer.start()
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    timer.stop()
    return predicate()


def _qimage_to_pil(image: QImage) -> Image.Image:
    """QImage -> Pillow, honouring the row padding QImage may carry."""
    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombuffer(
        "RGBA",
        (converted.width(), converted.height()),
        bytes(converted.constBits()),
        "raw",
        "RGBA",
        converted.bytesPerLine(),
        1,
    ).copy()


def read_video_frames(path: str | Path, max_frames: int, progress=None) -> tuple[list[Image.Image], float]:
    """Up to `max_frames` evenly spaced frames of a video, plus the fps they imply.

    `progress` is called with (done, total) after each frame.
    """
    player = QMediaPlayer()
    sink = QVideoSink()
    player.setVideoSink(sink)

    captured: list[QImage] = []
    sink.videoFrameChanged.connect(
        lambda frame: frame.isValid() and captured.append(frame.toImage().copy())
    )

    try:
        player.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
        ready = _spin(
            lambda: player.mediaStatus() in (
                QMediaPlayer.MediaStatus.LoadedMedia,
                QMediaPlayer.MediaStatus.BufferedMedia,
            ) or player.error() != QMediaPlayer.Error.NoError,
            _LOAD_TIMEOUT_MS,
        )
        if player.error() != QMediaPlayer.Error.NoError:
            raise ValueError(player.errorString() or "The video could not be opened.")
        if not ready:
            raise ValueError("Timed out while opening the video.")

        duration = player.duration()
        if duration <= 0:
            raise ValueError("The video reports no duration, so frames cannot be sampled.")

        # Playing then pausing forces the backend to produce decoded frames;
        # seeking a never-started player emits nothing on some backends.
        player.play()
        player.pause()
        _spin(lambda: bool(captured), _FRAME_TIMEOUT_MS)

        count = max(1, max_frames)
        # The final millisecond often lands past the last decodable frame.
        step = duration / count
        frames: list[Image.Image] = []
        for index in range(count):
            captured.clear()
            player.setPosition(int(index * step))
            if not _spin(lambda: bool(captured), _FRAME_TIMEOUT_MS):
                log.warning("No frame decoded at %d ms; stopping early", int(index * step))
                break
            frames.append(_qimage_to_pil(captured[-1]))
            if progress is not None:
                progress(index + 1, count)
        if not frames:
            raise ValueError("No frames could be decoded from the video.")
        return frames, len(frames) / (duration / 1000.0)
    finally:
        player.stop()
        player.setSource(QUrl())
        player.setVideoSink(None)
