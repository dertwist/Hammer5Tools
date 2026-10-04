"""Transport adapters for Core-owned Valve compilation."""
from __future__ import annotations
from typing import Any
from core.bridge import CoreBridge
from gui.settings.common import get_cs2_path, addon_content_dir


def compile_asset(path: str, cs2_path: str | None = None, force: bool = False,
                  timeout_seconds: int = 120, bridge: CoreBridge | None = None,
                  addon_root: str | None = None, dry_run: bool = False,
                  background: bool = False) -> dict[str, Any]:
    return compile_assets({"path": path, "cs2_path": cs2_path, "force": force,
                           "timeout_seconds": timeout_seconds, "addon_root": addon_root,
                           "dry_run": dry_run, "background": background}, bridge)


def compile_assets(request: dict, bridge: CoreBridge | None = None) -> dict[str, Any]:
    """Forward request-time settings; domain validation and processes stay in Core."""
    payload = dict(request)
    payload["cs2_path"] = payload.get("cs2_path") or get_cs2_path()
    if not payload.get("addon_root"):
        configured = addon_content_dir()
        payload["addon_root"] = str(configured) if configured else None
    if type(payload.get("timeout_seconds", 120)) is not int or payload.get("timeout_seconds", 120) <= 0:
        raise ValueError("timeout_seconds must be a positive integer")
    return (bridge or CoreBridge.instance()).compile_assets(payload)
