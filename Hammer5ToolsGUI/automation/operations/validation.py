"""Addon validation and orphan asset detection operations."""

from __future__ import annotations

from typing import Any

from automation.formats.shaping import paginate
from core.bridge import CoreBridge
from gui.settings.common import get_addon_dir, get_addon_name, get_cs2_path


def validate_addon(
    addon_name: str | None = None,
    cs2_dir: str | None = None,
    bridge: CoreBridge | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Validate an addon's asset integrity using the Core validator."""
    active_bridge = bridge or CoreBridge.instance()
    active_addon = addon_name or get_addon_name()
    active_cs2 = cs2_dir or get_cs2_path()

    if not active_addon:
        raise ValueError("Addon name must be specified or configured in settings")
    if not active_cs2:
        raise ValueError("CS2 directory must be specified or configured in settings")

    logs: list[str] = []

    def log_handler(msg: str) -> None:
        logs.append(msg)

    status_code = active_bridge.source_porter_validate(active_cs2, active_addon, log=log_handler)

    issues = [line for line in logs if "error" in line.lower() or "missing" in line.lower() or "warning" in line.lower()]

    # The full log of a large addon runs to thousands of lines; the issues are
    # the part worth reading, and even those are paged.
    result = {
        "addon": active_addon,
        "cs2_dir": active_cs2.replace("\\", "/"),
        "status_code": status_code,
        "clean": (status_code == 0),
        "issues_count": len(issues),
        "log_line_count": len(logs),
    }
    result.update(paginate(issues, "issues", limit=limit, offset=offset))
    return result


def find_unused_assets(
    map_path: str,
    addon_dir: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Identify unused (orphan) assets in an addon by comparing disk files against map dependencies."""
    from gui.forms.cleanup.parse import get_vmap_references

    active_addon_dir = addon_dir or get_addon_dir()
    if not active_addon_dir:
        raise ValueError("Addon directory must be specified or configured in settings")

    unused_items = get_vmap_references(addon_dir=active_addon_dir, vmap=map_path)
    # returns list of (file_path, size_bytes)

    total_bytes = sum(size for _, size in unused_items)
    files = [{"path": p.replace("\\", "/"), "size_bytes": size} for p, size in unused_items]

    result = {
        "map_path": map_path.replace("\\", "/"),
        "addon_dir": active_addon_dir.replace("\\", "/"),
        "unused_count": len(files),
        "total_size_bytes": total_bytes,
    }
    result.update(paginate(files, "unused_files", limit=limit, offset=offset))
    return result
