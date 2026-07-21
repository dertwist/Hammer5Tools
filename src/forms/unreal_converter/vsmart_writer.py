"""
vsmart writer — turns a normalized UE Blueprint component tree into a Source 2
.vsmart Smart Prop.

Each Blueprint static mesh component becomes a CSmartPropElement_Model (or
CSmartPropElement_Group for scene parents) whose relative transform is converted
from UE space to Source 2 space via the shared transform module.
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
    strip_prefix: bool = False,
) -> VsmartWriteResult:
    """
    Write a .vsmart file from normalized UE blueprint components.
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

    def build_vsmart_element(c: dict) -> Optional[dict]:
        mesh = c.get("mesh")
        comp_type = c.get("componentType", "")
        c_name = c.get("name", "Component")

        has_children = bool(children_by_parent.get(c_name))
        if not mesh and not has_children:
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

        elem_id = element_id_counter[0]
        element_id_counter[0] += 1

        child_elements = []
        for child_c in children_by_parent.get(c_name, []):
            child_elem = build_vsmart_element(child_c)
            if child_elem:
                child_elements.append(child_elem)

        if mesh:
            model_path = model_resolver(mesh)
            result.models.add(model_path)
            result.placed += 1
            label = os.path.splitext(os.path.basename(model_path))[0] or c_name

            elem = {
                "_class": "CSmartPropElement_Model",
                "m_nElementID": elem_id,
                "m_sModelName": model_path,
                "m_sLabel": label,
                "m_Modifiers": modifiers,
                "m_SelectionCriteria": [],
            }
            if any(abs(v - 1.0) > 1e-4 for v in st.scales):
                elem["m_vModelScale"] = {
                    "m_Components": [round(float(v), 4) for v in st.scales]
                }
            if child_elements:
                elem["m_Children"] = child_elements
            return elem
        else:
            elem = {
                "_class": "CSmartPropElement_Group",
                "m_nElementID": elem_id,
                "m_sLabel": c_name,
                "m_Modifiers": modifiers,
                "m_SelectionCriteria": [],
                "m_Children": child_elements,
            }
            if any(abs(v - 1.0) > 1e-4 for v in st.scales):
                if len(set(st.scales)) == 1:
                    elem["m_Modifiers"].append({
                        "_class": "CSmartPropOperation_Scale",
                        "m_flScale": round(float(st.scales[0]), 4)
                    })
            return elem

    root_elements = []
    for root_c in children_by_parent.get(None, []):
        elem = build_vsmart_element(root_c)
        if elem:
            root_elements.append(elem)

    if not root_elements:
        return result

    top_id = element_id_counter[0]
    element_id_counter[0] += 1
    top_group = {
        "_class": "CSmartPropElement_Group",
        "m_nElementID": top_id,
        "m_sLabel": bp_name,
        "m_Modifiers": [],
        "m_SelectionCriteria": [],
        "m_Children": root_elements,
    }

    vsmart_doc = {
        "generic_data_type": "CSmartPropRoot",
        "m_nContentVersion": 1,
        "m_Children": [top_group],
        "m_Variables": [],
        "m_Choices": [],
        "editor_info": {
            "m_nElementID": element_id_counter[0]
        }
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    kv3_str = JsonToKv3(vsmart_doc)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(kv3_str)

    return result
