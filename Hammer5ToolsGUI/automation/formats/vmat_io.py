"""Headless read, write, and edit operations for Source 2 .vmat files."""

from __future__ import annotations

import os
import re
from typing import Any

from automation.formats.shaping import shape_response

import vdf
from gui.common import app_version


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


def write_vmat(
    path: str,
    shader: str = "csgo_environment.vfx",
    slots: dict[str, str] | None = None,
    parameters: dict[str, Any] | None = None,
    flags: dict[str, Any] | None = None,
    system_attributes: dict[str, str] | None = None,
    attributes: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a new Source 2 .vmat file with the specified shader, slots, and parameters."""
    lines: list[str] = [
        "// THIS FILE IS AUTO-GENERATED",
        f"// Generated with Hammer 5 Tools {app_version}",
        "",
        "Layer0",
        "{",
        f'\tshader "{shader}"',
        "",
    ]

    # Feature flags
    if flags:
        lines.append("\t//---- Feature Flags ----")
        for flag_name, flag_val in sorted(flags.items()):
            lines.append(f"\t{flag_name} {flag_val}")
        lines.append("")

    # Texture slots
    if slots:
        lines.append("\t//---- Textures ----")
        for slot_name, slot_path in sorted(slots.items()):
            norm_slot = slot_path.replace("\\", "/")
            lines.append(f'\t{slot_name} "{norm_slot}"')
        lines.append("")

    # Scalar / vector parameters
    if parameters:
        lines.append("\t//---- Parameters ----")
        for param_name, param_val in sorted(parameters.items()):
            lines.append(f'\t{param_name} "{param_val}"')
        lines.append("")

    # System attributes
    if system_attributes:
        lines.append("\tSystemAttributes")
        lines.append("\t{")
        for attr_k, attr_v in sorted(system_attributes.items()):
            lines.append(f'\t\t{attr_k} "{attr_v}"')
        lines.append("\t}")
        lines.append("")

    # Tool / surface attributes
    if attributes:
        lines.append("\tAttributes")
        lines.append("\t{")
        for attr_k, attr_v in sorted(attributes.items()):
            lines.append(f'\t\t{attr_k} "{attr_v}"')
        lines.append("\t}")
        lines.append("")

    lines.append("}\n")
    content = "\n".join(lines)

    if not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "write_vmat",
        "shader": shader,
        "slots_count": len(slots or {}),
        "parameters_count": len(parameters or {}),
        "flags_count": len(flags or {}),
        "content_length": len(content),
    }


def edit_vmat(
    path: str,
    set_slots: dict[str, str] | None = None,
    set_parameters: dict[str, Any] | None = None,
    set_flags: dict[str, Any] | None = None,
    remove_keys: list[str] | None = None,
    shader: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Edit an existing .vmat file in-place, updating texture slots, parameters, or flags."""
    parsed = read_vmat_full(path)
    layer0: dict[str, Any] = dict(parsed["raw"])

    modified_keys: list[str] = []

    if shader:
        layer0["shader"] = shader
        modified_keys.append("shader")

    if set_slots:
        for slot_k, slot_v in set_slots.items():
            norm_v = slot_v.replace("\\", "/")
            layer0[slot_k] = norm_v
            modified_keys.append(slot_k)

    if set_parameters:
        for param_k, param_v in set_parameters.items():
            layer0[param_k] = str(param_v)
            modified_keys.append(param_k)

    if set_flags:
        for flag_k, flag_v in set_flags.items():
            layer0[flag_k] = flag_v
            modified_keys.append(flag_k)

    if remove_keys:
        for rk in remove_keys:
            if rk in layer0:
                del layer0[rk]
                modified_keys.append(f"-{rk}")

    # Re-serialize via clean format
    slots = {k: v for k, v in layer0.items() if "Texture" in k or k in ("g_tColor", "g_tNormal", "g_tRoughness")}
    flags = {k: v for k, v in layer0.items() if k.startswith("F_")}
    system_attrs = layer0.get("SystemAttributes") if isinstance(layer0.get("SystemAttributes"), dict) else {}
    attrs = layer0.get("Attributes") if isinstance(layer0.get("Attributes"), dict) else {}
    known_keys = set(slots) | set(flags) | {"shader", "SystemAttributes", "Attributes", "VariableState", "MaterialLayers"}
    params = {k: v for k, v in layer0.items() if k not in known_keys}

    out = write_vmat(
        path=path,
        shader=layer0.get("shader", "csgo_environment.vfx"),
        slots=slots,
        parameters=params,
        flags=flags,
        system_attributes=system_attrs,
        attributes=attrs,
        dry_run=dry_run,
    )
    out["action"] = "edit_vmat"
    out["modified_keys"] = modified_keys
    return out
