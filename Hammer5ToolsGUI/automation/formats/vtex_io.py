"""Headless read, write, and edit operations for Source 2 .vtex files."""

from __future__ import annotations

import os
import re
from typing import Any

from keyvalues3 import KV3TextReader
from gui.common import JsonToKv3


def read_vtex(path: str) -> dict[str, Any]:
    """Parse a loose .vtex file (KV3 or DMX format) and return its texture compile configuration."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"VTEX file not found: '{path}'")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    input_textures: list[dict[str, str]] = []
    output_format = "BC7"
    output_type = "2D"
    raw_data: dict[str, Any] = {}

    if "<!-- kv3" in text or "<!-- DMX" not in text:
        try:
            parsed = KV3TextReader().parse(text)
            raw = parsed.value if hasattr(parsed, "value") else parsed
            if isinstance(raw, dict):
                raw_data = raw
                output_format = raw.get("m_outputFormat", output_format)
                output_type = raw.get("m_outputTypeString", output_type)
                for item in raw.get("m_inputTextureArray", []):
                    if isinstance(item, dict):
                        input_textures.append({
                            "name": item.get("m_name", ""),
                            "file_name": item.get("m_fileName", ""),
                            "color_space": item.get("m_colorSpace", "srgb"),
                            "type": item.get("m_typeString", "2D"),
                        })
        except Exception:
            pass

    # Regex fallback for DMX / keyvalues2 format
    if not input_textures:
        matches = re.findall(r'"m_fileName"\s+"string"\s+"([^"]+)"', text)
        for fn in matches:
            input_textures.append({
                "name": "InputTexture_0",
                "file_name": fn.replace("\\", "/"),
                "color_space": "srgb",
                "type": "2D",
            })
        fmt_match = re.search(r'"m_outputFormat"\s+"string"\s+"([^"]+)"', text)
        if fmt_match:
            output_format = fmt_match.group(1)

    return {
        "path": path.replace("\\", "/"),
        "input_textures": input_textures,
        "output_format": output_format,
        "output_type": output_type,
        "raw": raw_data,
    }


def write_vtex(
    path: str,
    input_file: str,
    output_format: str = "BC7",
    color_space: str = "srgb",
    output_type: str = "2D",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a standard KeyValues3 .vtex compile configuration for CS2."""
    norm_input = input_file.replace("\\", "/")

    vtex_data = {
        "m_inputTextureArray": [
            {
                "m_name": "InputTexture_0",
                "m_fileName": norm_input,
                "m_colorSpace": color_space,
                "m_typeString": output_type,
            }
        ],
        "m_outputTypeString": output_type,
        "m_outputFormat": output_format,
        "m_textureOutputChannelPrinters": [],
    }

    content = JsonToKv3(vtex_data)

    if not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "write_vtex",
        "input_file": norm_input,
        "output_format": output_format,
        "color_space": color_space,
        "content_length": len(content),
    }


def edit_vtex(
    path: str,
    updates: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Edit an existing .vtex file, updating input texture references or compile format."""
    current = read_vtex(path)
    raw = current["raw"]

    input_file = updates.get("input_file")
    output_format = updates.get("output_format", current["output_format"])
    color_space = updates.get("color_space", "srgb")

    if not raw or "m_inputTextureArray" not in raw:
        # Re-write with updated settings
        first_input = input_file or (current["input_textures"][0]["file_name"] if current["input_textures"] else "")
        return write_vtex(
            path=path,
            input_file=first_input,
            output_format=output_format,
            color_space=color_space,
            dry_run=dry_run,
        )

    modified_fields: list[str] = []

    if input_file:
        norm_input = input_file.replace("\\", "/")
        for item in raw.get("m_inputTextureArray", []):
            if isinstance(item, dict):
                item["m_fileName"] = norm_input
        modified_fields.append("input_file")

    if "output_format" in updates:
        raw["m_outputFormat"] = updates["output_format"]
        modified_fields.append("output_format")

    if "color_space" in updates:
        for item in raw.get("m_inputTextureArray", []):
            if isinstance(item, dict):
                item["m_colorSpace"] = updates["color_space"]
        modified_fields.append("color_space")

    content = JsonToKv3(raw)

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "edit_vtex",
        "modified_fields": modified_fields,
        "content_length": len(content),
    }
