"""
vsmart writer — turns a normalized UE Blueprint component tree into a Source 2
.vsmart Smart Prop.

Each Blueprint static mesh component becomes a CSmartPropElement_Model whose
relative transform is converted from UE space to Source 2 space via the shared
transform module. Models are leaves in Source 2, so anything that has children —
a scene component, or a mesh component with components parented under it — is
emitted as a CSmartPropElement_Group carrying the transform instead.
"""

import os
from pathlib import Path
from typing import Callable, Iterable, List, Dict, Any, Set, Optional

from src.common import JsonToKv3
from .transform import convert_transform, UETransform, UnitScale
from .vmdl_writer import ue_mesh_to_model_path


class VsmartWriteResult:
    def __init__(self):
        self.placed = 0
        self.skipped = 0
        self.models: Set[str] = set()       # source model paths referenced


def write_vsmart(
    bp_name: str,
    components: Iterable[dict],
    output_path: str,
    model_resolver: Optional[Callable[[str], str]] = None,
    unit_scale: float = UnitScale.ONE_TO_ONE,
    strip_prefix: bool = True,
    variables: Optional[List[dict]] = None,
    choices: Optional[List[dict]] = None,
) -> VsmartWriteResult:
    """
    Write a .vsmart file from normalized UE blueprint components, construction script
    variables, choices, and conditional selection criteria.
    """
    from .vmdl_writer import strip_ue_prefix
    if strip_prefix:
        bp_name = strip_ue_prefix(bp_name)

    def _default_resolver(m: str) -> str:
        return ue_mesh_to_model_path(m, strip_prefix=strip_prefix)

    model_resolver = model_resolver or _default_resolver
    result = VsmartWriteResult()
    element_id_counter = [1]

    comp_list = list(components)
    if not comp_list:
        return result

    # Build lookup table of components by name
    comp_by_name = {c["name"]: c for c in comp_list if "name" in c}

    # Group children by parent name
    children_by_parent: Dict[Optional[str], List[dict]] = {}
    for c in comp_list:
        p = c.get("parent")
        if p not in comp_by_name:
            p = None
        children_by_parent.setdefault(p, []).append(c)

    def new_element_id() -> int:
        elem_id = element_id_counter[0]
        element_id_counter[0] += 1
        return elem_id

    def build_vsmart_element(c: dict, ancestry: frozenset = frozenset()) -> Optional[dict]:
        mesh = c.get("mesh")
        c_name = c.get("name", "Component")

        # Malformed parenting (a component reachable from itself) would recurse
        # forever; the SCS tree should never do this, a hand-edited dump might.
        if c_name in ancestry:
            return None

        child_elements = []
        for child_c in children_by_parent.get(c_name, []):
            child_elem = build_vsmart_element(child_c, ancestry | {c_name})
            if child_elem:
                child_elements.append(child_elem)

        # Transform-only nodes (scene components, mesh-less parents) exist purely
        # to carry an offset for their children — drop them only if empty.
        if not mesh and not child_elements:
            return None

        loc = c.get("location") or {"x": 0.0, "y": 0.0, "z": 0.0}
        rot = c.get("rotation") or {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
        scl = c.get("scale") or {"x": 1.0, "y": 1.0, "z": 1.0}

        st = convert_transform(
            UETransform(
                (loc["x"], loc["y"], loc["z"]),
                (rot["pitch"], rot["yaw"], rot["roll"]),
                (scl["x"], scl["y"], scl["z"]),
            ),
            unit_scale=unit_scale,
        )

        modifiers = []
        if any(abs(v) > 1e-4 for v in st.origin):
            modifiers.append({
                "_class": "CSmartPropOperation_Translate",
                "m_vPosition": {
                    "m_Components": [round(float(v), 4) for v in st.origin]
                }
            })

        if any(abs(v) > 1e-4 for v in st.angles):
            modifiers.append({
                "_class": "CSmartPropOperation_Rotate",
                "m_vRotation": {
                    "m_Components": [round(float(v), 4) for v in st.angles]
                }
            })

        scaled = any(abs(v - 1.0) > 1e-4 for v in st.scales)
        if not mesh and scaled and len(set(st.scales)) == 1:
            modifiers.append({
                "_class": "CSmartPropOperation_Scale",
                "m_flScale": round(float(st.scales[0]), 4)
            })

        selection_criteria = []
        if "choice_name" in c and "choice_value" in c:
            selection_criteria.append({
                "_class": "CSmartPropSelectionCriteria_Choice",
                "m_sChoiceName": c["choice_name"],
                "m_sChoiceValue": c["choice_value"],
            })
        elif "expression" in c:
            selection_criteria.append({
                "_class": "CSmartPropSelectionCriteria_Expression",
                "m_sExpression": c["expression"],
            })
        elif "variable_condition" in c:
            cond = c["variable_condition"]
            if isinstance(cond, dict):
                v_name = cond.get("variable", "Choice")
                v_val = cond.get("value", 0)
                selection_criteria.append({
                    "_class": "CSmartPropSelectionCriteria_Expression",
                    "m_sExpression": f"{v_name} == {v_val}",
                })

        def group(children: list) -> dict:
            return {
                "_class": "CSmartPropElement_Group",
                "m_nElementID": new_element_id(),
                "m_sLabel": c_name,
                "m_Modifiers": modifiers,
                "m_SelectionCriteria": selection_criteria,
                "m_Children": children,
            }

        if not mesh:
            return group(child_elements)

        model_path = model_resolver(mesh)
        result.models.add(model_path)
        result.placed += 1
        label = os.path.splitext(os.path.basename(model_path))[0] or c_name

        elem = {
            "_class": "CSmartPropElement_Model",
            "m_nElementID": new_element_id(),
            "m_sModelName": model_path,
            "m_sLabel": label,
            "m_nLodLevel": 0,
            "m_Modifiers": [] if child_elements else modifiers,
            "m_SelectionCriteria": selection_criteria,
        }

        if scaled:
            elem["m_vModelScale"] = {
                "m_Components": [round(float(v), 4) for v in st.scales]
            }
        if not child_elements:
            return elem

        return group([elem] + child_elements)

    root_elements = []
    for root_c in children_by_parent.get(None, []):
        elem = build_vsmart_element(root_c)
        if elem:
            root_elements.append(elem)

    if not root_elements:
        return result

    vsmart_variables = []
    for var in (variables or []):
        v_name = var.get("name") or var.get("m_VariableName", "selector")
        v_type = str(var.get("type", "int")).lower()
        v_default = var.get("default", var.get("m_DefaultValue", 0))
        min_val = float(var.get("min", var.get("m_flParamaterMinValue", 0)))
        max_val = float(var.get("max", var.get("m_flParamaterMaxValue", 10)))

        if v_type in ("int", "integer"):
            vsmart_variables.append({
                "_class": "CSmartPropVariable_Int",
                "m_VariableName": v_name,
                "m_bExposeAsParameter": True,
                "m_DefaultValue": int(v_default),
                "m_flParamaterMinValue": min_val,
                "m_flParamaterMaxValue": max_val,
                "m_sModelName": "None",
            })
        elif v_type == "float":
            vsmart_variables.append({
                "_class": "CSmartPropVariable_Float",
                "m_VariableName": v_name,
                "m_bExposeAsParameter": True,
                "m_DefaultValue": float(v_default),
                "m_flParamaterMinValue": min_val,
                "m_flParamaterMaxValue": max_val,
                "m_sModelName": "None",
            })
        elif v_type in ("bool", "boolean"):
            vsmart_variables.append({
                "_class": "CSmartPropVariable_Bool",
                "m_VariableName": v_name,
                "m_bExposeAsParameter": True,
                "m_DefaultValue": bool(v_default),
                "m_sModelName": "None",
            })
        elif v_type in ("string", "name"):
            vsmart_variables.append({
                "_class": "CSmartPropVariable_String",
                "m_VariableName": v_name,
                "m_bExposeAsParameter": True,
                "m_DefaultValue": str(v_default),
                "m_sModelName": "None",
            })

    # Detect variant model sets that share a variable condition or can be grouped into PickOne
    var_models: Dict[str, List[dict]] = {}
    other_elements = []

    for elem in root_elements:
        cond_var = None
        if elem.get("_class") == "CSmartPropElement_Model" and elem.get("m_SelectionCriteria"):
            for sc in elem["m_SelectionCriteria"]:
                expr = sc.get("m_sExpression", "")
                if "==" in expr:
                    cond_var = expr.split("==")[0].strip()
                    break

        if cond_var:
            var_models.setdefault(cond_var, []).append(elem)
        else:
            other_elements.append(elem)

    # Also group all top-level model elements into a PickOne if no explicit condition was given but multiple model variants exist
    if not var_models and len(root_elements) > 1 and all(e.get("_class") == "CSmartPropElement_Model" for e in root_elements):
        var_models["selector"] = list(root_elements)
        other_elements = []

    final_root_children = list(other_elements)

    for v_name, models_list in var_models.items():
        if len(models_list) > 1:
            for m_elem in models_list:
                m_elem["m_SelectionCriteria"] = []

            pick_one_id = new_element_id()
            pick_one_node = {
                "_class": "CSmartPropElement_PickOne",
                "m_nElementID": pick_one_id,
                "m_sLabel": f"PickOne_{pick_one_id}",
                "m_SelectionMode": "SPECIFIC",
                "m_SpecificChildIndex": {
                    "m_SourceName": v_name
                },
                "m_bConfigurable": True,
                "m_bEnabled": True,
                "m_Modifiers": [],
                "m_SelectionCriteria": [],
                "m_OutputChoiceVariableName": "",
                "m_Children": models_list
            }
            final_root_children.append(pick_one_node)

            if not any(v.get("m_VariableName") == v_name for v in vsmart_variables):
                vsmart_variables.append({
                    "_class": "CSmartPropVariable_Int",
                    "m_VariableName": v_name,
                    "m_bExposeAsParameter": True,
                    "m_DefaultValue": 0,
                    "m_flParamaterMinValue": 0.0,
                    "m_flParamaterMaxValue": float(max(0, len(models_list) - 1)),
                    "m_sModelName": "None"
                })
        else:
            final_root_children.extend(models_list)

    top_group = {
        "_class": "CSmartPropElement_Group",
        "m_nElementID": new_element_id(),
        "m_sLabel": bp_name,
        "m_Modifiers": [],
        "m_SelectionCriteria": [],
        "m_Children": final_root_children,
    }

    vsmart_choices = []
    for choice in (choices or []):
        c_name = choice.get("name", "Choice")
        options = []
        for opt in choice.get("options", []):
            options.append({
                "_class": "CSmartPropChoiceOption",
                "m_Name": opt.get("name", "Option"),
                "m_VariableValues": [
                    {
                        "m_TargetName": c_name,
                        "m_DataType": "Float",
                        "m_Value": opt.get("value", 0)
                    }
                ]
            })
        if options:
            vsmart_choices.append({
                "_class": "CSmartPropChoice",
                "m_Name": c_name,
                "m_Options": options,
            })

    vsmart_doc = {
        "generic_data_type": "CSmartPropRoot",
        "m_nContentVersion": 1,
        "m_Children": [top_group],
        "m_Variables": vsmart_variables,
        "m_Choices": vsmart_choices,
        "editor_info": {
            "m_nElementID": element_id_counter[0]
        }
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    kv3_str = JsonToKv3(vsmart_doc)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(kv3_str)

    return result
