"""Official game VPK archive search and extraction operations."""

from __future__ import annotations

import os
from typing import Any

from core.bridge import CoreBridge
from gui.settings.common import get_cs2_path

# CS2 splits stock content across several archives, and the one an asset lives in
# is not guessable from its path: models/dev/dev_cube is in csgo, while
# models/editor/placeholder_box is in core. Searching only csgo makes assets that
# exist look missing, so every mounted archive is searched.
_CONTENT_ARCHIVES = (
    "csgo",
    "csgo_core",
    "csgo_imported",
    "csgo_lv",
    "core",
)


def _archive_paths(root: str) -> list[str]:
    """Return every stock content VPK present in this install, in search order."""
    found = [
        os.path.join(root, "game", name, "pak01_dir.vpk")
        for name in _CONTENT_ARCHIVES
    ]
    present = [path for path in found if os.path.isfile(path)]
    if not present:
        raise FileNotFoundError(f"No CS2 content VPK archives found under '{os.path.join(root, 'game')}'")
    return present


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

    archives = _archive_paths(root)

    suffixes = (f".{extension.lstrip('.')}",) if extension else ()
    query_lower = query.lower()

    matches: list[dict[str, Any]] = []

    with active_bridge.create_vpk_index() as index:
        for archive in archives:
            index.mount(archive)
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
        "archives": [path.replace("\\", "/") for path in archives],
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

    archives = _archive_paths(root)

    norm_internal = internal_path.replace("\\", "/").lstrip("/")

    # vpk_search reports source names ("...vmdl") while the archive stores the
    # compiled ones ("...vmdl_c"), so a path copied straight from a search result
    # would otherwise fail to extract.
    candidates = [norm_internal]
    if norm_internal.endswith("_c"):
        candidates.append(norm_internal[:-2])
    else:
        candidates.append(f"{norm_internal}_c")

    data = None
    with active_bridge.create_vpk_index() as index:
        for archive in archives:
            index.mount(archive)
        for candidate in candidates:
            data = index.read_bytes(candidate)
            if data is not None:
                norm_internal = candidate
                break

    if data is None:
        raise FileNotFoundError(
            f"Asset '{candidates[0]}' not found in any of {len(archives)} CS2 archives "
            f"(also tried '{candidates[1]}')"
        )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(data)

    return {
        "internal_path": norm_internal,
        "output_path": output_path.replace("\\", "/"),
        "bytes_written": len(data),
    }
