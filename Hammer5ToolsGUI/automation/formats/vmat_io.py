"""Headless read, write, and edit operations for Source 2 .vmat files."""

from __future__ import annotations

import os
import re
from typing import Any

from automation.formats.shaping import shape_response

import vdf


def read_vmat_full(path: str) -> dict[str, Any]:
    """Parse a loose .vmat file and extract shader, texture slots, parameters, and flags."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"VMAT file not found: '{path}'")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # VMAT files generally start with comments then `Layer0 { ... }`
    parsed = {}
    try:
        parsed = vdf.loads(text)
    except Exception:
        # Fallback if vdf fails: extract Layer0 block
        match = re.search(r"Layer0\s*\{([\s\S]*)\}\s*$", text)
        if match:
            try:
                parsed = vdf.loads(f"Layer0\n{{\n{match.group(1)}\n}}")
            except Exception:
                pass

    layer0 = parsed.get("Layer0", parsed) if isinstance(parsed, dict) else {}
    shader = layer0.get("shader", "")

    slots: dict[str, str] = {}
    flags: dict[str, Any] = {}
    parameters: dict[str, Any] = {}
    system_attributes: dict[str, str] = {}
    attributes: dict[str, str] = {}

    for key, value in layer0.items():
        if key == "shader":
            continue
        if key == "SystemAttributes" and isinstance(value, dict):
            system_attributes.update(value)
        elif key == "Attributes" and isinstance(value, dict):
            attributes.update(value)
        elif key.startswith("F_"):
            flags[key] = value
        elif "Texture" in key or key in ("g_tColor", "g_tNormal", "g_tRoughness"):
            slots[key] = str(value)
        elif isinstance(value, (str, int, float)):
            parameters[key] = value

    return {
        "path": path.replace("\\", "/"),
        "shader": shader,
        "slots": slots,
        "flags": flags,
        "parameters": parameters,
        "system_attributes": system_attributes,
        "attributes": attributes,
        "raw": layer0,
    }


def read_vmat(
    path: str,
    detail: str = "summary",
    select: str | None = None,
) -> dict[str, Any]:
    """Read a .vmat material file.

    The extracted view is already compact, so `summary` and `full` are the same
    here; `select` addresses one node of the parsed document.
    """
    full = read_vmat_full(path)
    payload = {key: value for key, value in full.items() if key != "raw"}
    return shape_response(payload, payload, full.get("raw"), detail=detail, select=select)


def write_vmat(path: str, shader: str = "csgo_environment.vfx", slots: dict[str, str] | None = None,
               parameters: dict[str, Any] | None = None, flags: dict[str, Any] | None = None,
               system_attributes: dict[str, str] | None = None, attributes: dict[str, str] | None = None,
               dry_run: bool = False, bridge=None) -> dict[str, Any]:
    from core.bridge import CoreBridge
    return (bridge or CoreBridge.instance()).author_source_assets({
        "path": path, "action": "create", "shader": shader, "slots": slots,
        "parameters": parameters, "flags": flags, "system_attributes": system_attributes,
        "attributes": attributes, "dry_run": dry_run,
    }, "vmat")


def edit_vmat(path: str, set_slots: dict[str, str] | None = None,
              set_parameters: dict[str, Any] | None = None, set_flags: dict[str, Any] | None = None,
              remove_keys: list[str] | None = None, shader: str | None = None,
              dry_run: bool = False, bridge=None) -> dict[str, Any]:
    from core.bridge import CoreBridge
    return (bridge or CoreBridge.instance()).author_source_assets({
        "path": path, "action": "update", "set_slots": set_slots, "set_parameters": set_parameters,
        "set_flags": set_flags, "remove_keys": remove_keys, "shader": shader, "dry_run": dry_run,
    }, "vmat")
