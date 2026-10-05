"""VMAP level operations including reference remapping."""

from __future__ import annotations

import os
from typing import Any

from core.bridge import CoreBridge


def vmap_rewrite_references(
    vmap_path: str,
    replacements: dict[str, str],
    bridge: CoreBridge | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Rewrite asset paths across an uncompiled VMAP level."""
    if not os.path.isfile(vmap_path):
        raise FileNotFoundError(f"VMAP file not found: '{vmap_path}'")

    active_bridge = bridge or CoreBridge.instance()

    # Read existing references to preview what matches
    existing_refs = active_bridge.read_valve_map_asset_references(vmap_path)
    matched_replacements: dict[str, str] = {}

    for ref in existing_refs:
        ref_norm = ref.replace("\\", "/").lower()
        for src, dst in replacements.items():
            src_norm = src.replace("\\", "/").lower()
            if src_norm == ref_norm or ref_norm.startswith(src_norm):
                matched_replacements[ref] = dst.replace("\\", "/")

    if not dry_run and matched_replacements:
        result = active_bridge.rewrite_vmap_references(vmap_path, replacements)
        changed = getattr(result, "changed", True)
        diagnostics = list(getattr(result, "diagnostics", ()))
    else:
        changed = False
        diagnostics = []

    return {
        "vmap_path": vmap_path.replace("\\", "/"),
        "dry_run": dry_run,
        "changed": changed,
        "matched_count": len(matched_replacements),
        "planned_replacements": matched_replacements,
        "diagnostics": diagnostics,
    }
