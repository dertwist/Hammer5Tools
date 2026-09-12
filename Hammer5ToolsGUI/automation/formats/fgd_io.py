"""Entity definitions read from the game's own FGD files.

CS2 ships the authoritative entity schema on disk, versioned with the build:
every entity class, what it is for, and every keyvalue with its type, default,
and help text. Reading it beats any table written by hand, because it covers
entities added after the table was written and it is never out of date.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

from gui.settings.common import get_cs2_path

# game/ holds the definitions the current build actually uses; bin/ holds legacy
# copies for older tooling.
_FGD_ROOTS = ("game",)

# A declaration starts at "@" in column 0 and runs to the next one. The name may
# sit on the same line as the class keyword or several lines below it, after a
# metadata block, so the chunk is parsed rather than matched in one pass.
_DECLARATION = re.compile(r"^@(\w+)", re.MULTILINE)
_CLASS_NAME = re.compile(r"=\s*(?P<name>[\w.]+)\s*(?::\s*(?P<description>[^\[]*))?", re.DOTALL)
_BASES = re.compile(r"\bbase\s*\(([^)]*)\)", re.IGNORECASE)
_TOOL_TIP = re.compile(r"entity_tool_tip\s*=\s*\"([^\"]*)\"")
_PROPERTY = re.compile(
    r"^\s*(?P<name>\w+)\((?P<type>[\w:]+)\)"
    r"(?P<decorations>(?:\s*\[[^\]]*\]|\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})*)"
    r"\s*:\s*(?P<rest>.*)$",
    re.MULTILINE,
)
_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _strings(text: str) -> list[str]:
    """Return the quoted strings in order, joining FGD's `+` continuations."""
    return [match.group(1).replace('\\"', '"').strip() for match in _QUOTED.finditer(text)]


def _body(text: str, start: int) -> tuple[str, int]:
    """Return the bracketed class body beginning at or after `start`."""
    opening = text.find("[", start)
    if opening < 0:
        return "", start
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index], index
    return text[opening + 1:], len(text)


def _brace_depth(text: str, position: int) -> int:
    return text.count("{", 0, position) - text.count("}", 0, position)


def _body_start(chunk: str) -> int:
    """Index of the class body's opening bracket, ignoring metadata arrays."""
    depth = 0
    for index, character in enumerate(chunk):
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        elif character == "[" and depth == 0:
            return index
    return len(chunk)


def _properties(body: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for match in _PROPERTY.finditer(body):
        parts = _strings(match.group("rest"))
        entry: dict[str, Any] = {"name": match.group("name"), "type": match.group("type")}
        if parts:
            entry["display"] = parts[0]
        # The tail is "Display" : default : "Description"; the default may be
        # unquoted, so the description is the last quoted string when there is
        # more than one.
        if len(parts) > 1:
            entry["description"] = parts[-1]
        found.append(entry)
    return found


def _parse(text: str) -> dict[str, dict[str, Any]]:
    classes: dict[str, dict[str, Any]] = {}
    starts = [match.start() for match in _DECLARATION.finditer(text)]

    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(text)
        chunk = text[start:end]
        kind = _DECLARATION.match(chunk).group(1)
        if not kind.endswith("Class"):
            continue

        body_start = _body_start(chunk)
        header = chunk[:body_start]
        # A metadata block holds its own "=" (entity_tool_tip = "...",
        # static_prop = true), so the class name is the last assignment outside
        # the braces.
        name_match = None
        for candidate in _CLASS_NAME.finditer(header):
            if _brace_depth(header, candidate.start()) == 0:
                name_match = candidate
        if name_match is None:
            continue

        described = _strings(name_match.group("description") or "")
        tip = _TOOL_TIP.search(header)
        body, _end = _body(chunk, body_start)
        bases = _BASES.search(header)

        _merge(classes, {
            "classname": name_match.group("name"),
            "kind": kind,
            "description": described[0] if described else (tip.group(1) if tip else ""),
            "bases": [base.strip() for base in (bases.group(1).split(",") if bases else []) if base.strip()],
            "properties": _properties(body),
        })
    return classes


def _merge(classes: dict[str, dict[str, Any]], entry: dict[str, Any]) -> None:
    """Fold one declaration in; csgo.fgd overrides and extends core definitions."""
    existing = classes.get(entry["classname"])
    if existing is None:
        classes[entry["classname"]] = entry
        return
    if not existing["description"] and entry["description"]:
        existing["description"] = entry["description"]
    for base in entry["bases"]:
        if base not in existing["bases"]:
            existing["bases"].append(base)
    known = {item["name"] for item in existing["properties"]}
    existing["properties"].extend(item for item in entry["properties"] if item["name"] not in known)


@lru_cache(maxsize=4)
def load_definitions(cs2_path: str) -> dict[str, dict[str, Any]]:
    """Parse every FGD the build ships. Cached, because it is a few megabytes."""
    classes: dict[str, dict[str, Any]] = {}
    for root_name in _FGD_ROOTS:
        root = os.path.join(cs2_path, root_name)
        if not os.path.isdir(root):
            continue
        for directory, _subdirectories, files in os.walk(root):
            for filename in sorted(files):
                if not filename.lower().endswith(".fgd"):
                    continue
                try:
                    with open(os.path.join(directory, filename), "r", encoding="utf-8", errors="ignore") as handle:
                        parsed = _parse(handle.read())
                except OSError:
                    continue
                for entry in parsed.values():
                    _merge(classes, entry)
    if not classes:
        raise FileNotFoundError(f"No FGD entity definitions found under '{os.path.join(cs2_path, 'game')}'")
    return classes


def _inherited(classes: dict[str, dict[str, Any]], name: str, seen: set[str] | None = None) -> list[dict[str, Any]]:
    """Collect properties from base classes, nearest definition winning."""
    seen = seen if seen is not None else set()
    if name in seen or name not in classes:
        return []
    seen.add(name)
    collected: list[dict[str, Any]] = []
    for base in classes[name]["bases"]:
        collected.extend(_inherited(classes, base, seen))
    collected.extend(classes[name]["properties"])
    return collected


def entity_info(
    classname: str | None = None,
    search: str | None = None,
    include_properties: bool = True,
    cs2_path: str | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    """Describe an entity class, or search for classes by name or description."""
    root = cs2_path or get_cs2_path()
    if not root:
        raise ValueError("CS2 directory must be specified or configured in settings")
    classes = load_definitions(root)

    if classname:
        entry = classes.get(classname) or classes.get(classname.lower())
        if entry is None:
            close = sorted(name for name in classes if classname.lower() in name.lower())[:10]
            raise ValueError(
                f"No entity class '{classname}' is defined." + (f" Did you mean: {', '.join(close)}?" if close else "")
            )
        result: dict[str, Any] = {
            "classname": entry["classname"],
            "kind": entry["kind"],
            "description": entry["description"],
            "bases": entry["bases"],
        }
        if include_properties:
            merged: dict[str, dict[str, Any]] = {}
            for item in _inherited(classes, entry["classname"]):
                merged[item["name"]] = item
            result["properties"] = list(merged.values())
            result["property_count"] = len(merged)
        return result

    if search:
        needle = search.lower()
        matches = [
            {"classname": entry["classname"], "description": entry["description"]}
            for entry in classes.values()
            if needle in entry["classname"].lower() or needle in entry["description"].lower()
        ]
        matches.sort(key=lambda item: item["classname"])
        return {
            "search": search,
            "match_count": len(matches),
            "truncated": len(matches) > limit,
            "matches": matches[:limit],
        }

    return {
        "class_count": len(classes),
        "usage": "Pass classname for one entity's description and keyvalues, or search to find classes.",
    }


def describe(classname: str, cs2_path: str | None = None) -> str:
    """Return just an entity's one-line description, or empty when unknown."""
    root = cs2_path or get_cs2_path()
    if not root:
        return ""
    try:
        entry = load_definitions(root).get(classname)
    except (FileNotFoundError, OSError):
        return ""
    return entry["description"] if entry else ""
