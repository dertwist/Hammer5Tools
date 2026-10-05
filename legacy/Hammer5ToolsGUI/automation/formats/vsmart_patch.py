"""Targeted edits for .vsmart documents.

Replacing a whole array to change one field forces the entire document through
the caller, which is both expensive and the reason duplicate element IDs and
malformed defaults kept appearing. These operations address one node at a time
and leave the rest of the document untouched.
"""

from __future__ import annotations

import re
from typing import Any

from gui.common import JsonToKv3

from automation.formats.shaping import SelectError, expand_class, iter_element_id_nodes
from automation.formats.vsmart_io import read_vsmart_full

_SEGMENT = re.compile(r"^([^\[\].]+)((?:\[[^\]]*\])*)$")
_SUBSCRIPT = re.compile(r"\[([^\]]*)\]")

# A category is rendered by Hammer5Tools as a collapsible card and by Hammer as
# a pair of inert banner rows, so the markers are always written as a pair.
_CATEGORY_BANNER = "-" * 10
_CATEGORY_BLANK = " " * 45


def _accessors(expression: str) -> list[tuple[str, Any]]:
    """Flatten a select expression into ordered accessor steps."""
    steps: list[tuple[str, Any]] = []
    for segment in expression.split("."):
        match = _SEGMENT.match(segment)
        if match is None:
            raise SelectError(f"Cannot parse target segment '{segment}'")
        steps.append(("key", match.group(1)))
        for subscript in _SUBSCRIPT.findall(match.group(2)):
            if "=" in subscript:
                field, _, wanted = subscript.partition("=")
                steps.append(("match", (field.strip(), wanted.strip())))
            else:
                steps.append(("index", int(subscript)))
    return steps


def _step(node: Any, accessor: tuple[str, Any], expression: str) -> Any:
    kind, value = accessor
    if kind == "key":
        if not isinstance(node, dict) or value not in node:
            raise SelectError(f"'{value}' is not present in '{expression}'")
        return node[value]
    if kind == "index":
        if not isinstance(node, list) or not -len(node) <= value < len(node):
            raise SelectError(f"index {value} is out of range in '{expression}'")
        return node[value]
    field, wanted = value
    if not isinstance(node, list):
        raise SelectError(f"[{field}={wanted}] in '{expression}' does not address a list")
    for item in node:
        if isinstance(item, dict) and str(item.get(field, "")) == wanted:
            return item
    raise SelectError(f"No item has {field} == {wanted} in '{expression}'")


def _resolve_container(root: Any, expression: str) -> tuple[Any, tuple[str, Any]]:
    """Return the container holding the addressed node, and the final accessor."""
    steps = _accessors(expression)
    if not steps:
        raise SelectError("Empty target expression")
    node = root
    for accessor in steps[:-1]:
        node = _step(node, accessor, expression)
    return node, steps[-1]


def _assign(container: Any, accessor: tuple[str, Any], value: Any, expression: str) -> None:
    kind, key = accessor
    if kind == "key":
        if not isinstance(container, dict):
            raise SelectError(f"'{key}' in '{expression}' does not address an object")
        container[key] = value
        return
    if kind == "index":
        _step(container, accessor, expression)
        container[key] = value
        return
    target = _step(container, accessor, expression)
    container[container.index(target)] = value


def _remove(container: Any, accessor: tuple[str, Any], expression: str) -> None:
    kind, key = accessor
    if kind == "key":
        _step(container, accessor, expression)
        del container[key]
        return
    target = _step(container, accessor, expression)
    container.remove(target)


def _category_marker(name: str, slug: str, *, start: bool) -> dict[str, Any]:
    suffix = "start" if start else "end"
    display = f"{_CATEGORY_BANNER} {name} {_CATEGORY_BANNER}" if start else _CATEGORY_BLANK
    return {
        "_class": "CSmartPropVariable_Bool",
        "m_VariableName": f"hammer5tools_category_{slug}_{suffix}",
        "m_bExposeAsParameter": True,
        "m_DefaultValue": "",
        "m_DisplayName": display,
        "m_Hammer5ToolsCategoryName": name,
        "m_ReadOnlyExpression": "true",
    }


def _apply_add_category(root: dict[str, Any], operation: dict[str, Any]) -> str:
    name = operation.get("name")
    if not name:
        raise ValueError("'add_category' requires 'name'")
    contains = list(operation.get("contains") or [])
    if not contains:
        raise ValueError("'add_category' requires 'contains'")

    slug = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    variables = root.setdefault("m_Variables", [])
    by_name = {item.get("m_VariableName"): item for item in variables if isinstance(item, dict)}
    missing = [wanted for wanted in contains if wanted not in by_name]
    if missing:
        raise ValueError(f"'add_category' names variables that do not exist: {', '.join(missing)}")

    grouped = [by_name[wanted] for wanted in contains]
    for item in grouped:
        variables.remove(item)
        item["m_Hammer5ToolsCategoryName"] = name

    insert_at = len(variables)
    block = [_category_marker(name, slug, start=True), *grouped, _category_marker(name, slug, start=False)]
    variables[insert_at:insert_at] = block
    return f"add_category:{name}"


def _apply_add_variable(root: dict[str, Any], operation: dict[str, Any]) -> str:
    variable = operation.get("variable")
    if not isinstance(variable, dict) or not variable.get("m_VariableName"):
        raise ValueError("'add_variable' requires a 'variable' object with m_VariableName")

    variables = root.setdefault("m_Variables", [])
    name = variable["m_VariableName"]
    if any(isinstance(item, dict) and item.get("m_VariableName") == name for item in variables):
        raise ValueError(f"A variable named '{name}' already exists")

    normalized = normalize_variable(dict(variable))
    after = operation.get("after")
    if after:
        for index, item in enumerate(variables):
            if isinstance(item, dict) and item.get("m_VariableName") == after:
                variables.insert(index + 1, normalized)
                return f"add_variable:{name}"
        raise ValueError(f"Cannot insert after '{after}': no such variable")
    variables.append(normalized)
    return f"add_variable:{name}"


# Writing "" where a number belongs makes a static evaluator read the variable
# as 0, which silently collapses instance counts to nothing.
_TYPED_DEFAULTS: dict[str, Any] = {
    "CSmartPropVariable_Float": 0.0,
    "CSmartPropVariable_Int": 0,
    "CSmartPropVariable_Vector3D": [0.0, 0.0, 0.0],
    "CSmartPropVariable_Angles": [0.0, 0.0, 0.0],
    "CSmartPropVariable_Color": [255, 255, 255, 255],
}


def normalize_variable(variable: dict[str, Any]) -> dict[str, Any]:
    """Give a variable a default of its own type when it has none.

    Bool variables are left alone: the category markers use an empty default
    deliberately, and that convention is load-bearing in Hammer.
    """
    # Summaries print short class names, so accept them back: "Float" is written
    # as CSmartPropVariable_Float rather than rejected.
    if variable.get("_class"):
        variable["_class"] = expand_class(variable["_class"], "Variable")

    fallback = _TYPED_DEFAULTS.get(str(variable.get("_class", "")))
    if fallback is not None and variable.get("m_DefaultValue", "") in ("", None):
        variable["m_DefaultValue"] = list(fallback) if isinstance(fallback, list) else fallback
    return variable


def normalize_variables(root: dict[str, Any]) -> int:
    """Apply typed defaults across a document; returns how many were filled in."""
    filled = 0
    for item in root.get("m_Variables") or []:
        if not isinstance(item, dict):
            continue
        before = item.get("m_DefaultValue", "")
        normalize_variable(item)
        if item.get("m_DefaultValue", "") != before:
            filled += 1
    return filled


def reindex_element_ids(root: Any) -> int:
    """Make every element ID unique, changing as few of them as possible.

    Element IDs seed the pseudo-random operations (RandomOffset, RandomRotation,
    RandomScale), so renumbering a node moves the instances it places. Nodes
    whose IDs are already unique therefore keep them, and only the later
    occurrences of a duplicated ID are reassigned. Returns how many changed.
    """
    containers = list(iter_element_id_nodes(root))
    identifiers = [c.get("m_nElementID") for _path, c in containers]
    next_free = max((i for i in identifiers if isinstance(i, int)), default=0) + 1

    seen: set[int] = set()
    changed = 0
    for _path, container in containers:
        element_id = container.get("m_nElementID")
        if isinstance(element_id, int) and element_id not in seen:
            seen.add(element_id)
            continue
        container["m_nElementID"] = next_free
        seen.add(next_free)
        next_free += 1
        changed += 1
    return changed


_OPERATIONS = {
    "add_category": _apply_add_category,
    "add_variable": _apply_add_variable,
}


def patch_vsmart(
    path: str,
    operations: list[dict[str, Any]],
    dry_run: bool = False,
    reindex: bool = True,
) -> dict[str, Any]:
    """Apply addressed operations to a .vsmart document without rewriting it wholesale."""
    if not operations:
        raise ValueError("'operations' must contain at least one operation")

    root = read_vsmart_full(path)["raw"]
    applied: list[str] = []

    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("Each operation must be an object")
        name = operation.get("op")
        if name in _OPERATIONS:
            applied.append(_OPERATIONS[name](root, operation))
            continue
        if name in ("set", "remove"):
            target = operation.get("target")
            if not target:
                raise ValueError(f"'{name}' requires 'target'")
            container, accessor = _resolve_container(root, target)
            if name == "set":
                if "value" not in operation:
                    raise ValueError("'set' requires 'value'")
                _assign(container, accessor, operation["value"], target)
            else:
                _remove(container, accessor, target)
            applied.append(f"{name}:{target}")
            continue
        raise ValueError(f"Unknown operation '{name}'")

    filled = normalize_variables(root)
    reindexed = reindex_element_ids(root) if reindex else 0

    from automation.formats.vsmart_lint import lint_document

    findings = lint_document(root)
    content = JsonToKv3(root)

    if not dry_run:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "patch_vsmart",
        "applied": applied,
        "defaults_filled": filled,
        "elements_reindexed": reindexed,
        "lint_findings": findings,
        "content_length": len(content),
    }
