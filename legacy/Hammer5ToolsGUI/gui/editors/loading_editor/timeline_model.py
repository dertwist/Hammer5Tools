"""Qt-free model for camera-history timeline data."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tga"}


@dataclass(frozen=True)
class TimelineFrame:
    timestamp: datetime
    path: str


@dataclass
class CameraTimeline:
    name: str
    frames: list[TimelineFrame] = field(default_factory=list)


def camera_name(filename: str) -> str:
    stem = Path(filename).stem
    match = re.match(r"^(.+?)_(\d+)$", stem)
    if not match:
        return stem
    base, raw_number = match.groups()
    number = int(raw_number)
    return base if number == 0 else f"{base} {number}"


def scan_timeline(history_path: str) -> list[CameraTimeline]:
    root = Path(history_path)
    grouped: dict[str, list[TimelineFrame]] = {}
    if not root.exists():
        return []
    for timestamp_dir in root.iterdir():
        if not timestamp_dir.is_dir():
            continue
        try:
            timestamp = datetime.strptime(timestamp_dir.name, "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            continue
        for image in timestamp_dir.iterdir():
            if image.suffix.lower() not in _IMAGE_SUFFIXES:
                continue
            name = camera_name(image.name)
            grouped.setdefault(name, []).append(TimelineFrame(timestamp, str(image)))
    return [
        CameraTimeline(name, sorted(frames, key=lambda frame: frame.timestamp))
        for name, frames in sorted(grouped.items())
    ]

