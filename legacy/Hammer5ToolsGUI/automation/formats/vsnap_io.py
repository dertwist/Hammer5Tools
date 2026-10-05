"""Headless read, write, edit, and generate operations for Source 2 .vsnap files."""

from __future__ import annotations

import os
from typing import Any

from core.bridge import CoreBridge, SnapshotDocument, SnapshotStream


def read_vsnap(bridge: CoreBridge, path: str) -> dict[str, Any]:
    """Parse a .vsnap particle snapshot file and summarize its vertex streams."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"VSNAP file not found: '{path}'")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    doc = bridge.read_vsnap(text)

    streams_summary = []
    positions_sample = []

    for s in doc.streams:
        streams_summary.append({
            "name": s.name,
            "type": s.type,
            "count": len(s.values),
        })
        if s.name.lower() == "position":
            for val in s.values[:10]:
                if isinstance(val, (tuple, list)):
                    positions_sample.append([float(x) for x in val])
                else:
                    positions_sample.append(float(val))

    return {
        "path": path.replace("\\", "/"),
        "stream_count": len(doc.streams),
        "point_count": doc.count,
        "streams": streams_summary,
        "sample_positions": positions_sample,
    }


def write_vsnap(
    bridge: CoreBridge,
    path: str,
    positions: list[list[float]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a .vsnap particle snapshot from a list of 3D positions."""
    if not positions:
        raise ValueError("Cannot write .vsnap: positions list is empty")

    stream_values = tuple(tuple(float(c) for c in pt) for pt in positions)
    stream = SnapshotStream("Position", "position", stream_values)
    doc = SnapshotDocument((stream,))

    content = bridge.serialize_vsnap(doc)

    if not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "write_vsnap",
        "point_count": len(positions),
        "content_length": len(content),
    }


def generate_vsnap(
    bridge: CoreBridge,
    path: str,
    primitive: str = "cube",
    count: int = 100,
    size: float = 64.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate a geometric primitive particle snapshot cloud (cube, sphere, cylinder, etc.)."""
    doc = bridge.generate_vsnap(primitive, count, size)
    content = bridge.serialize_vsnap(doc)

    if not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "generate_vsnap",
        "primitive": primitive,
        "point_count": doc.count,
        "size": size,
        "content_length": len(content),
    }


def edit_vsnap(
    bridge: CoreBridge,
    path: str,
    lighting: dict[str, int] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Edit an existing .vsnap file, e.g. applying a two-point lighting gradient."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"VSNAP file not found: '{path}'")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    doc = bridge.read_vsnap(text)

    modified_actions: list[str] = []

    if lighting:
        first_idx = int(lighting.get("first_index", 0))
        second_idx = int(lighting.get("second_index", max(0, doc.count - 1)))
        doc = bridge.apply_vsnap_lighting(doc, first_idx, second_idx)
        modified_actions.append(f"apply_lighting({first_idx}, {second_idx})")

    content = bridge.serialize_vsnap(doc)

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "edit_vsnap",
        "point_count": doc.count,
        "modified_actions": modified_actions,
        "content_length": len(content),
    }
