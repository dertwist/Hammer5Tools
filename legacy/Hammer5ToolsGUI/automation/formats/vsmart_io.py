"""Headless read, write, edit, and evaluate operations for Source 2 .vsmart files."""

from __future__ import annotations

import os
from typing import Any

from automation.formats.shaping import outline_children, shape_response, short_class

from core.bridge import CoreBridge
from keyvalues3 import KV3TextReader
from gui.common import JsonToKv3


def read_vsmart_full(path: str) -> dict[str, Any]:
    """Parse a loose .vsmart file and extract root class, variables, choices, and children."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"SmartProp file not found: '{path}'")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    kv3_file = KV3TextReader().parse(text)
    root = kv3_file.value if hasattr(kv3_file, "value") else kv3_file

    if not isinstance(root, dict):
        raise ValueError("Invalid SmartProp: root is not a KeyValues3 object")

    root_class = root.get("_class", "CSmartPropElement_Group")
    variables = root.get("m_Variables", [])
    choices = root.get("m_Choices", [])
    children = root.get("m_Children", [])
    modifiers = root.get("m_Modifiers", [])

    return {
        "path": path.replace("\\", "/"),
        "root_class": root_class,
        "variables": variables,
        "choices": choices,
        "children": children,
        "modifiers": modifiers,
        "raw": root,
    }


def read_vsmart(
    path: str,
    detail: str = "summary",
    select: str | None = None,
) -> dict[str, Any]:
    """Read a .vsmart SmartProp shaped for an agent rather than for a disk round trip."""
    full = read_vsmart_full(path)
    payload = {key: value for key, value in full.items() if key != "raw"}
    return shape_response(
        payload,
        _summarize_vsmart(payload),
        full.get("raw"),
        detail=detail,
        select=select,
        names=_name_vsmart(payload),
    )


def _name_vsmart(payload: dict[str, Any]) -> dict[str, Any]:
    """The smallest useful view: what the prop exposes, and nothing about it.

    A prop with hundreds of exposed parameters summarises large no matter how
    the tree is collapsed, because naming every parameter is the point. This
    level answers "what is there" so `select` can answer "what is it".
    """
    variables = payload.get("variables") or []
    categories: dict[str, list[str]] = {}
    for item in variables:
        if not isinstance(item, dict):
            continue
        name = str(item.get("m_VariableName", ""))
        if name.startswith("hammer5tools_category_"):
            continue
        categories.setdefault(str(item.get("m_Hammer5ToolsCategoryName") or ""), []).append(name)
    return {
        "path": payload.get("path"),
        "root_class": payload.get("root_class"),
        "variable_count": len(variables),
        "parameters_by_category": categories,
    }


def _summarize_vsmart(payload: dict[str, Any]) -> dict[str, Any]:
    """Describe what a SmartProp exposes and how it is structured, not what it contains."""
    variables = payload.get("variables") or []
    return {
        "path": payload.get("path"),
        "root_class": payload.get("root_class"),
        "variable_count": len(variables),
        "choice_count": len(payload.get("choices") or []),
        "modifier_count": len(payload.get("modifiers") or []),
        "variables": [_summarize_variable(item) for item in variables if isinstance(item, dict)],
        "elements": outline_children(payload.get("children")),
    }


_VARIABLE_FIELDS = (
    ("display", "m_DisplayName"),
    ("category", "m_Hammer5ToolsCategoryName"),
    ("hide_when", "m_HideExpression"),
    ("read_only_when", "m_ReadOnlyExpression"),
)


def _summarize_variable(variable: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": variable.get("m_VariableName", ""),
        "class": short_class(variable.get("_class", "")),
        "default": variable.get("m_DefaultValue"),
    }
    for key, field in _VARIABLE_FIELDS:
        value = variable.get(field)
        if value not in (None, ""):
            entry[key] = value
    if variable.get("m_bExposeAsParameter"):
        entry["exposed"] = True
    return entry


def write_vsmart(
    path: str,
    root_class: str = "CSmartPropElement_Group",
    variables: list[dict[str, Any]] | None = None,
    choices: list[dict[str, Any]] | None = None,
    children: list[dict[str, Any]] | None = None,
    modifiers: list[dict[str, Any]] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a standard KeyValues3 .vsmart file."""
    doc: dict[str, Any] = {
        "_class": root_class,
        "m_Variables": list(variables or []),
        "m_Choices": list(choices or []),
        "m_Children": list(children or []),
        "m_Modifiers": list(modifiers or []),
        "editor_info": {
            "m_nElementID": 1,
        },
    }

    # Imported here because the patch module reads documents through this one.
    from automation.formats.vsmart_patch import normalize_variables, reindex_element_ids

    normalize_variables(doc)
    reindex_element_ids(doc)
    content = JsonToKv3(doc)

    if not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "write_vsmart",
        "root_class": root_class,
        "variables_count": len(variables or []),
        "children_count": len(children or []),
        "content_length": len(content),
    }


def edit_vsmart(
    path: str,
    updates: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Edit an existing .vsmart file in-place, updating variables, choices, or children."""
    current = read_vsmart_full(path)
    root: dict[str, Any] = dict(current["raw"])

    modified_fields: list[str] = []

    if "variables" in updates:
        root["m_Variables"] = list(updates["variables"])
        modified_fields.append("m_Variables")

    if "set_variable" in updates:
        # updates["set_variable"] = {"name": "foo", "value": 10.0}
        var_spec = updates["set_variable"]
        var_name = var_spec.get("name")
        var_val = var_spec.get("value")
        vars_list = root.setdefault("m_Variables", [])
        found = False
        for item in vars_list:
            if isinstance(item, dict) and item.get("m_VariableName") == var_name:
                item["m_DefaultValue"] = var_val
                found = True
                break
        if not found:
            vars_list.append({
                "_class": "CSmartPropVariable_Float" if isinstance(var_val, (int, float)) else "CSmartPropVariable_String",
                "m_VariableName": var_name,
                "m_DefaultValue": var_val,
            })
        modified_fields.append(f"variable:{var_name}")

    if "choices" in updates:
        root["m_Choices"] = list(updates["choices"])
        modified_fields.append("m_Choices")

    if "children" in updates:
        root["m_Children"] = list(updates["children"])
        modified_fields.append("m_Children")

    if "modifiers" in updates:
        root["m_Modifiers"] = list(updates["modifiers"])
        modified_fields.append("m_Modifiers")

    from automation.formats.vsmart_patch import normalize_variables, reindex_element_ids

    normalize_variables(root)
    reindex_element_ids(root)
    content = JsonToKv3(root)

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "path": path.replace("\\", "/"),
        "dry_run": dry_run,
        "action": "edit_vsmart",
        "modified_fields": modified_fields,
        "content_length": len(content),
    }


def evaluate_vsmart(
    bridge: CoreBridge,
    path: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate an uncompiled SmartProp document using the Hammer5Tools NativeAOT Core."""
    vsmart_data = read_vsmart_full(path)
    root = vsmart_data["raw"]

    opts = options or {}
    max_depth = int(opts.get("maximum_depth", 32))
    max_models = int(opts.get("maximum_models", 10_000))

    evaluation = bridge.evaluate_smartprop(root, maximum_depth=max_depth, maximum_models=max_models)

    # Diagnostics and counts are what an agent reasons about. Ten thousand 4x4
    # transforms are not, so they are only returned when asked for.
    result: dict[str, Any] = {
        "path": path.replace("\\", "/"),
        "model_count": len(evaluation.models),
        "widget_count": len(evaluation.widgets),
        "distinct_models": sorted({model.model_name for model in evaluation.models if model.model_name}),
        "bounds": _model_bounds(evaluation.models),
        "diagnostics": list(evaluation.diagnostics),
    }

    if not bool(opts.get("include_models", False)):
        result["models_hint"] = "Pass include_models=true (with optional offset/limit) for per-instance transforms."
        return result

    offset = max(int(opts.get("offset", 0)), 0)
    limit = max(int(opts.get("limit", 100)), 0)
    window = evaluation.models[offset:offset + limit]
    result["offset"] = offset
    result["returned"] = len(window)
    result["truncated"] = offset + len(window) < len(evaluation.models)
    result["models"] = [
        {
            "element_id": model.element_id,
            "model_name": model.model_name,
            "transform": list(model.transform),
            "material_group": model.material_group,
            "tint_color": list(model.tint_color) if model.tint_color else None,
        }
        for model in window
    ]
    return result


def _model_bounds(models: Any) -> dict[str, list[float]] | None:
    """Return the axis-aligned extent of the placed instances.

    A bounding box answers "did this produce anything, and where" without
    sending one matrix per instance.
    """
    # Core emits row-vector 4x4 matrices, so translation is the last row.
    positions = [
        (model.transform[12], model.transform[13], model.transform[14])
        for model in models
        if model.transform is not None and len(model.transform) >= 16
    ]
    if not positions:
        return None
    return {
        "minimum": [min(axis) for axis in zip(*positions)],
        "maximum": [max(axis) for axis in zip(*positions)],
    }
