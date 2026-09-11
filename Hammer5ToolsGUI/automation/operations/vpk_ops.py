"""Official game VPK archive search and extraction operations."""

from __future__ import annotations

import os
from typing import Any

from core.bridge import CoreBridge
from gui.settings.common import get_cs2_path


def vpk_search(
    query: str,
    extension: str | None = None,
    game_dir: str | None = None,
    bridge: CoreBridge | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Search for assets matching a query string inside the CS2 game VPK archive."""
    active_bridge = bridge or CoreBridge.instance()
    root = game_dir or get_cs2_path()
    if not root:
        raise ValueError("CS2 directory must be specified or configured in settings")

    vpk_path = os.path.join(root, "game", "csgo", "pak01_dir.vpk")
    if not os.path.isfile(vpk_path):
        raise FileNotFoundError(f"CS2 VPK archive not found at '{vpk_path}'")

    suffixes = (f".{extension.lstrip('.')}",) if extension else ()
    query_lower = query.lower()

    matches: list[dict[str, Any]] = []

    with active_bridge.create_vpk_index() as index:
        index.mount(vpk_path)
        all_entries = index.entries(suffixes)
        for entry_path, entry_size in all_entries:
            if query_lower in entry_path.lower():
                matches.append({
                    "path": entry_path.replace("\\", "/"),
                    "size_bytes": entry_size,
                })
                if len(matches) >= limit:
                    break

    return {
        "vpk_path": vpk_path.replace("\\", "/"),
        "query": query,
        "extension_filter": extension,
        "match_count": len(matches),
        "matches": matches,
    }


def vpk_extract(
    internal_path: str,
    output_path: str,
    game_dir: str | None = None,
    bridge: CoreBridge | None = None,
) -> dict[str, Any]:
    """Extract a single asset from the CS2 game VPK archive to disk."""
    active_bridge = bridge or CoreBridge.instance()
    root = game_dir or get_cs2_path()
    if not root:
        raise ValueError("CS2 directory must be specified or configured in settings")

    vpk_path = os.path.join(root, "game", "csgo", "pak01_dir.vpk")
    if not os.path.isfile(vpk_path):
        raise FileNotFoundError(f"CS2 VPK archive not found at '{vpk_path}'")

    norm_internal = internal_path.replace("\\", "/").lstrip("/")

    with active_bridge.create_vpk_index() as index:
        index.mount(vpk_path)
        data = index.read_bytes(norm_internal)

    if data is None:
        raise FileNotFoundError(f"Asset '{norm_internal}' not found in '{vpk_path}'")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(data)

    return {
        "internal_path": norm_internal,
        "output_path": output_path.replace("\\", "/"),
        "bytes_written": len(data),
    }
