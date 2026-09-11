"""Headless read, write, edit, and evaluate operations for Source 2 .vsmart files."""

from __future__ import annotations

import os
from typing import Any

from core.bridge import CoreBridge
from keyvalues3 import KV3TextReader
from gui.common import JsonToKv3


def read_vsmart(path: str) -> dict[str, Any]:
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
    current = read_vsmart(path)
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
    vsmart_data = read_vsmart(path)
    root = vsmart_data["raw"]

    opts = options or {}
    max_depth = int(opts.get("maximum_depth", 32))
    max_models = int(opts.get("maximum_models", 10_000))

    evaluation = bridge.evaluate_smartprop(root, maximum_depth=max_depth, maximum_models=max_models)

    models_output = []
    for model in evaluation.models:
        models_output.append({
            "element_id": model.element_id,
            "model_name": model.model_name,
            "transform": list(model.transform),
            "material_group": model.material_group,
            "tint_color": list(model.tint_color) if model.tint_color else None,
        })

    return {
        "path": path.replace("\\", "/"),
        "model_count": len(models_output),
        "widget_count": len(evaluation.widgets),
        "models": models_output,
        "diagnostics": list(evaluation.diagnostics),
    }
