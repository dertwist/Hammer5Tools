"""Response shaping shared by the automation read tools.

An agent asking "what parameters does this SmartProp expose" should not be sent
the whole document to find out. Every reader returns a summary by default, can
return the full extracted view on request, and can return a single addressed
node through `select`.
"""

from __future__ import annotations

import re
from typing import Any

_SEGMENT = re.compile(r"^([^\[\].]+)((?:\[[^\]]*\])*)$")
_SUBSCRIPT = re.compile(r"\[([^\]]*)\]")


class SelectError(ValueError):
    """Raised when a select expression does not address anything."""


def select_path(root: Any, expression: str) -> Any:
    """Return the node addressed by a dotted select expression.

    Supports `key`, `key[2]`, and `key[field=value]`, e.g.
    `m_Variables[m_VariableName=Length].m_DefaultValue`. The match on
    `field=value` is the first item that compares equal as a string.
    """
    current = root
    for segment in expression.split("."):
        if not segment:
            raise SelectError(f"Empty segment in select expression '{expression}'")
        match = _SEGMENT.match(segment)
        if match is None:
            raise SelectError(f"Cannot parse select segment '{segment}'")
        name, subscripts = match.group(1), match.group(2)
        current = _descend_key(current, name, expression)
        for subscript in _SUBSCRIPT.findall(subscripts):
            current = _descend_subscript(current, subscript, expression)
    return current


def _descend_key(node: Any, name: str, expression: str) -> Any:
    if not isinstance(node, dict) or name not in node:
        raise SelectError(f"'{name}' is not present at that point in '{expression}'")
    return node[name]


def _descend_subscript(node: Any, subscript: str, expression: str) -> Any:
    if not isinstance(node, list):
        raise SelectError(f"'[{subscript}]' in '{expression}' does not address a list")
    if "=" in subscript:
        field, _, wanted = subscript.partition("=")
        for item in node:
            if isinstance(item, dict) and str(item.get(field.strip(), "")) == wanted.strip():
                return item
        raise SelectError(f"No list item has {field.strip()} == {wanted.strip()} in '{expression}'")
    try:
        return node[int(subscript)]
    except (ValueError, IndexError) as error:
        raise SelectError(f"'[{subscript}]' in '{expression}' is out of range") from error


def shape_response(
    payload: dict[str, Any],
    summary: dict[str, Any],
    root: Any,
    *,
    detail: str = "summary",
    select: str | None = None,
    names: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pick the names, the summary, the full view, or one selected node."""
    if select:
        return {
            "path": payload.get("path"),
            "select": select,
            "value": select_path(root, select),
        }
    if detail == "full":
        return payload
    if detail == "names":
        if names is None:
            raise ValueError("This format has no 'names' detail level")
        return names
    if detail != "summary":
        raise ValueError("'detail' must be 'names', 'summary' or 'full'")
    return summary


# Every SmartProp class name carries one of these namespaces. Repeating it on
# each node costs 30% of a summary and says nothing, so summaries print the
# short name. Full reads and writes keep the real class name.
_CLASS_PREFIXES = (
    "CSmartPropSelectionCriteria_",
    "CSmartPropOperation_",
    "CSmartPropElement_",
    "CSmartPropVariable_",
    "CSmartPropFilter_",
)


def short_class(name: Any) -> str:
    """Strip the CSmartProp namespace from a class name for display."""
    text = str(name or "")
    for prefix in _CLASS_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def expand_class(name: str, kind: str) -> str:
    """Expand a short class name back to its real one. `kind` is the namespace."""
    text = str(name or "")
    return text if text.startswith("CSmartProp") else f"CSmartProp{kind}_{text}"


def outline_children(children: Any, depth: int = 2) -> list[dict[str, Any]]:
    """Describe a SmartProp element tree to a bounded depth.

    The shape of the tree is what an agent needs to decide where to patch; the
    contents of every leaf are what makes the document large.
    """
    if not isinstance(children, list):
        return []
    outline: list[dict[str, Any]] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        entry: dict[str, Any] = {
            "class": short_class(child.get("_class", "")),
            "element_id": _element_id(child),
        }
        modifiers = child.get("m_Modifiers")
        if isinstance(modifiers, list) and modifiers:
            entry["modifiers"] = [short_class(m.get("_class", "")) for m in modifiers if isinstance(m, dict)]
        grandchildren = child.get("m_Children")
        if isinstance(grandchildren, list) and grandchildren:
            if depth > 1:
                entry["children"] = outline_children(grandchildren, depth - 1)
            else:
                entry["children_count"] = len(grandchildren)
        outline.append(entry)
    return outline


def _element_id(node: dict[str, Any]) -> Any:
    editor_info = node.get("editor_info")
    if isinstance(editor_info, dict) and "m_nElementID" in editor_info:
        return editor_info["m_nElementID"]
    return node.get("m_nElementID")


def paginate(items: list[Any], key: str, *, limit: int | None = None, offset: int = 0) -> dict[str, Any]:
    """Return one window of `items` under `key`, with the cursor fields beside it.

    `limit=None` returns everything and is for internal callers that need the
    complete list, such as recursive dependency resolution.
    """
    offset = max(offset, 0)
    window = items[offset:] if limit is None else items[offset:offset + max(limit, 0)]
    return {
        key: window,
        "offset": offset,
        "returned": len(window),
        "total": len(items),
        "truncated": offset + len(window) < len(items),
    }


def iter_element_id_nodes(node: Any, path: str = ""):
    """Yield (path, container) for every node that carries an element ID.

    An element's ID lives either in its `editor_info` block or directly on the
    node. The `editor_info` block is never descended into separately, or every
    element would be counted twice.
    """
    if isinstance(node, dict):
        info = node.get("editor_info")
        if isinstance(info, dict) and "m_nElementID" in info:
            yield path or "<root>", info
        elif "m_nElementID" in node:
            yield path or "<root>", node
        for key, value in node.items():
            if key == "editor_info":
                continue
            yield from iter_element_id_nodes(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from iter_element_id_nodes(item, f"{path}[{index}]")
