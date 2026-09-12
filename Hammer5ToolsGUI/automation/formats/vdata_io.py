"""Headless read, write, and edit operations for Source 2 .vdata files."""

from __future__ import annotations

import os
from typing import Any

from automation.formats.shaping import shape_response

from keyvalues3 import KV3TextReader
from gui.common import JsonToKv3


def read_vdata_full(path: str) -> dict[str, Any]:
    """Parse a loose .vdata file and extract its named data structures."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"VDATA file not found: '{path}'")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    kv3_file = KV3TextReader().parse(text)
    root = kv3_file.value if hasattr(kv3_file, "value") else kv3_file

    if not isinstance(root, dict):
        raise ValueError("Invalid VDATA: root is not a KeyValues3 object")

    generic_type = root.get("generic_data_type", "")
    entries: dict[str, Any] = {}

    for k, v in root.items():
        if k in ("generic_data_type", "editor_info"):
            continue
        entries[k] = v

    return {
        "path": path.replace("\\", "/"),
        "generic_data_type": generic_type,
        "entry_count": len(entries),
        "entries": entries,
        "raw": root,
    }


def read_vdata(
    path: str,
    detail: str = "summary",
    select: str | None = None,
) -> dict[str, Any]:
    """Read a .vdata gamedata file; the summary lists entry names without their bodies."""
    full = read_vdata_full(path)
    payload = {key: value for key, value in full.items() if key != "raw"}
    return shape_response(payload, _summarize_vdata(payload), full.get("raw"), detail=detail, select=select)


def _summarize_vdata(payload: dict[str, Any]) -> dict[str, Any]:
    entries = payload.get("entries") or {}
    return {
        "path": payload.get("path"),
        "generic_data_type": payload.get("generic_data_type"),
        "entry_count": len(entries),
        "entry_names": sorted(entries),
    }


def write_vdata(
    path: str,
    entries: dict[str, Any],
    generic_data_type: str = "CDetailPropType",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a standard KeyValues3 .vdata file."""
    doc: dict[str, Any] = {
        "generic_data_type": generic_data_type,
    }
    doc.update(entries)

    content = JsonToKv3(doc)

    if not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "write_vdata",
        "generic_data_type": generic_data_type,
        "entries_count": len(entries),
        "content_length": len(content),
    }


def edit_vdata(
    path: str,
    updates: dict[str, Any],
    remove_keys: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Edit an existing .vdata file in-place, adding, updating, or removing entries."""
    current = read_vdata_full(path)
    root: dict[str, Any] = dict(current["raw"])

    modified_keys: list[str] = []

    if "generic_data_type" in updates:
        root["generic_data_type"] = updates["generic_data_type"]
        modified_keys.append("generic_data_type")

    for key, value in updates.items():
        if key == "generic_data_type":
            continue
        root[key] = value
        modified_keys.append(f"set:{key}")

    if remove_keys:
        for rk in remove_keys:
            if rk in root:
                del root[rk]
                modified_keys.append(f"del:{rk}")

    content = JsonToKv3(root)

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "edit_vdata",
        "modified_keys": modified_keys,
        "content_length": len(content),
    }
