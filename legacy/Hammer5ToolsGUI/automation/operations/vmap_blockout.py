"""Core-backed structured map insertion; no text splicing or external conversion."""
from __future__ import annotations
from typing import Any
from core.bridge import CoreBridge
from gui.settings.common import get_cs2_path, addon_content_dir

DEFAULT_BOX_MODEL = "models/editor/placeholder_box.vmdl"


def write_blockout(path: str, boxes: list[dict[str, Any]] | None = None, skeleton: str | None = None,
                   cs2_path: str | None = None, dry_run: bool = False, bridge=None,
                   items_file: str | None = None, addon_root: str | None = None) -> dict[str, Any]:
    request = {"path": path, "cs2_path": cs2_path or get_cs2_path(), "dry_run": dry_run}
    if skeleton is not None:
        request["skeleton"] = skeleton
    if boxes is not None:
        request["boxes"] = boxes
    if items_file is not None:
        request["items_file"] = items_file
    configured = addon_content_dir() if addon_root is None else None
    request["addon_root"] = addon_root or (str(configured) if configured else None)
    return (bridge or CoreBridge.instance()).author_map(request, "insert")
