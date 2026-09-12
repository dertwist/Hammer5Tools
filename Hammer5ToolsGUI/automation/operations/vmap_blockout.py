"""Blockout geometry for VMAP levels, built from a real Valve skeleton.

Hand-authored `CDmePolygonMesh` crashes Hammer and the compiler, and a minimal
hand-written `CMapWorld` crashes the deserializer. Both failure modes are
avoidable the same way: start from a map Valve shipped, and add only
`prop_static` entities, which Source 2 accepts at arbitrary non-uniform scale.

This exists so the rule does not have to be remembered. An agent that calls it
cannot produce the crash that the vmap-authoring guide warns about.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import uuid
from typing import Any

from gui.settings.common import get_cs2_path

# models/editor/placeholder_box.vmdl ships in game/core/pak01_dir.vpk. Its base
# form is 10x10x10 with the pivot at the bottom centre, so a box of a requested
# size scales by size/10 and sits on its own origin.
DEFAULT_BOX_MODEL = "models/editor/placeholder_box.vmdl"
_BOX_BASE_SIZE = 10.0

_ENTITY_TEMPLATE = '''			"CMapEntity"
			{{
				"id" "elementid" "{entity_id}"
				"nodeID" "int" "{node_id}"
				"referenceID" "uint64" "0x0"
				"children" "element_array"
				[
				]
				"variableTargetKeys" "string_array"
				[
				]
				"variableNames" "string_array"
				[
				]
				"relayPlugData" "DmePlugList"
				{{
					"id" "elementid" "{plug_id}"
					"names" "string_array"
					[
					]
					"dataTypes" "int_array"
					[
					]
					"plugTypes" "int_array"
					[
					]
					"descriptions" "string_array"
					[
					]
				}}

				"connectionsData" "element_array"
				[
				]
				"entity_properties" "EditGameClassProps"
				{{
					"id" "elementid" "{props_id}"
					"classname" "string" "prop_static"
					"model" "string" "{model}"
					"skin" "string" "{skin}"
					"solid" "string" "6"
					"bakelighting" "string" "-1"
					"disableshadows" "string" "0"
					"lightmapscalebias" "string" "0"
					"lightingorigin" "string" ""
					"bakelightdoublesided" "string" "0"
					"visoccluder" "string" "0"
					"materialoverride" "string" ""
					"lodlevel" "string" "-1"
					"baketoworld" "string" "0"
					"disablemerging" "string" "0"
					"rendertocubemaps" "string" "1"
				}}

				"hitNormal" "vector3" "0 0 1"
				"isProceduralEntity" "bool" "0"
				"origin" "vector3" "{origin}"
				"angles" "qangle" "{angles}"
				"scales" "vector3" "{scales}"
				"transformLocked" "bool" "0"
				"force_hidden" "bool" "0"
				"editorOnly" "bool" "0"
			}}'''


def _dmxconvert(root: str) -> str:
    executable = os.path.join(root, "game", "bin", "win64", "dmxconvert.exe")
    if not os.path.isfile(executable):
        raise FileNotFoundError(f"dmxconvert.exe not found at '{executable}'")
    return executable


def _run(executable: str, source: str, destination: str, encoding: str) -> None:
    result = subprocess.run(
        [executable, "-i", source, "-oe", encoding, "-o", destination],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode != 0 or not os.path.isfile(destination):
        raise RuntimeError(f"dmxconvert failed ({result.returncode}): {result.stderr or result.stdout}")


def _numbers(value: Any, name: str, default: tuple[float, float, float] | None = None) -> list[float]:
    if value is None:
        if default is None:
            raise ValueError(f"'{name}' is required")
        return list(default)
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"'{name}' must be three numbers")
    return [float(component) for component in value]


def _triple(values: list[float]) -> str:
    return " ".join(f"{component:g}" for component in values)


def _find_world_children_end(text: str) -> int:
    """Return the index of the closing bracket of CMapWorld's children array.

    The array mixes GUID references with inline element definitions, so the
    bracket has to be matched by depth rather than found by pattern.
    """
    world = text.find('"world" "CMapWorld"')
    if world < 0:
        raise ValueError("Skeleton has no CMapWorld; it is not a usable .vmap")
    marker = text.find('"children" "element_array"', world)
    if marker < 0:
        raise ValueError("CMapWorld in the skeleton has no children array")
    start = text.find("[", marker)
    depth = 0
    for index in range(start, len(text)):
        character = text[index]
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("CMapWorld children array is unterminated")


def _next_node_id(text: str) -> int:
    found = [int(value) for value in re.findall(r'"nodeID" "int" "(\d+)"', text)]
    return (max(found) + 1) if found else 1


def _add_asset_reference(text: str, model: str) -> str:
    marker = text.find('"map_asset_references" "string_array"')
    if marker < 0:
        return text
    start = text.find("[", marker)
    end = text.find("]", start)
    body = text[start + 1:end]
    if f'"{model}"' in body:
        return text
    separator = "," if body.strip() else ""
    return f'{text[:end]}{separator}\n\t\t"{model}"\n\t{text[end:]}'


def write_blockout(
    path: str,
    boxes: list[dict[str, Any]],
    skeleton: str | None = None,
    cs2_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Write a .vmap of prop_static boxes, based on an existing valid map.

    Each box takes `size` in world units and optional `position`, `angles`,
    `model`, and `skin`. `skeleton` is an existing .vmap to build on; it is
    copied and only its world children and asset references are touched.
    """
    if not boxes:
        raise ValueError("'boxes' must contain at least one box")

    root = cs2_path or get_cs2_path()
    if not root:
        raise RuntimeError("CS2 installation path is not configured")
    if not skeleton:
        skeleton = os.path.join(
            root, "content", "csgo_addons", "addon_template", "maps", "xxx_mapname_xxx.vmap"
        )
    if not os.path.isfile(skeleton):
        raise FileNotFoundError(f"Skeleton .vmap not found: '{skeleton}'")

    executable = _dmxconvert(root)

    with tempfile.TemporaryDirectory(prefix="h5t_blockout_") as workspace:
        text_form = os.path.join(workspace, "skeleton.kv2")
        _run(executable, os.path.abspath(skeleton), text_form, "keyvalues2")
        with open(text_form, "r", encoding="utf-8", errors="surrogateescape") as handle:
            text = handle.read()

        node_id = _next_node_id(text)
        rendered: list[str] = []
        models: set[str] = set()

        for index, box in enumerate(boxes):
            if not isinstance(box, dict):
                raise ValueError("Each box must be an object")
            size = _numbers(box.get("size"), f"boxes[{index}].size")
            if any(component <= 0 for component in size):
                raise ValueError(f"boxes[{index}].size must be positive in every axis")
            position = _numbers(box.get("position"), f"boxes[{index}].position", (0.0, 0.0, 0.0))
            angles = _numbers(box.get("angles"), f"boxes[{index}].angles", (0.0, 0.0, 0.0))
            model = str(box.get("model") or DEFAULT_BOX_MODEL)
            models.add(model)

            rendered.append(_ENTITY_TEMPLATE.format(
                entity_id=uuid.uuid4(),
                node_id=node_id,
                plug_id=uuid.uuid4(),
                props_id=uuid.uuid4(),
                model=model,
                skin=str(box.get("skin") or "default"),
                origin=_triple(position),
                angles=_triple(angles),
                scales=_triple([component / _BOX_BASE_SIZE for component in size]),
            ))
            node_id += 1

        insertion = _find_world_children_end(text)
        prefix = text[:insertion].rstrip()
        separator = "," if not prefix.endswith("[") else ""
        text = f"{prefix}{separator}\n" + ",\n".join(rendered) + "\n\t\t" + text[insertion:]

        for model in sorted(models):
            text = _add_asset_reference(text, model)

        if dry_run:
            return {
                "path": path.replace("\\", "/"),
                "dry_run": True,
                "action": "vmap_write_blockout",
                "skeleton": skeleton.replace("\\", "/"),
                "box_count": len(boxes),
                "models": sorted(models),
            }

        patched = os.path.join(workspace, "patched.kv2")
        with open(patched, "w", encoding="utf-8", errors="surrogateescape") as handle:
            handle.write(text)

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        _run(executable, patched, os.path.abspath(path), "binary")

    return {
        "path": path.replace("\\", "/"),
        "dry_run": False,
        "action": "vmap_write_blockout",
        "skeleton": skeleton.replace("\\", "/"),
        "box_count": len(boxes),
        "models": sorted(models),
        "bytes_written": os.path.getsize(path),
    }
