import os
import sys
import math
from typing import List, Dict, Any, Optional

# Add project root to sys.path if not present (for standalone runs or testing)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.dotnet import setup_keyvalues2
from src.common import JsonToKv3, get_cs2_path
from src.settings.common import get_addon_name, get_settings_bool, get_settings_value

def inverse_rotate_point_pyr(x, y, z, pitch, yaw, roll):
    # Reverse Yaw (Z rotation)
    if yaw != 0:
        y_rad = math.radians(-yaw)
        c, s = math.cos(y_rad), math.sin(y_rad)
        x, y = x * c - y * s, x * s + y * c
    # Reverse Pitch (X rotation)
    if pitch != 0:
        p = math.radians(-pitch)
        c, s = math.cos(p), math.sin(p)
        y, z = y * c - z * s, y * s + z * c
    # Reverse Roll (Y rotation)
    if roll != 0:
        r = math.radians(-roll)
        c, s = math.cos(r), math.sin(r)
        x, z = x * c - z * s, x * s + z * c
    return x, y, z

def normalize_angles(angles):
    return [((a + 180) % 360) - 180 for a in angles]

def format_imported_vector(vector):
    should_round = get_settings_bool('SmartPropEditor', 'round_vmap_values', False)
    if should_round:
        try:
            decimals = int(get_settings_value('SmartPropEditor', 'round_vmap_decimals', 4))
        except:
            decimals = 4
        return [round(float(x), decimals) for x in vector]
    else:
        return [{"m_Expression": str(x)} for x in vector]


def scan_vmap_for_props(vmap_path: str) -> List[Dict[str, Any]]:
    """
    Parses a VMAP level file and returns a list of dictionaries,
    each describing a standard prop entity, group, or smartprop found in the map.
    """
    Datamodel, Element, DeferredMode = setup_keyvalues2()
    
    if not os.path.exists(vmap_path):
        return []

    dmx_model = None
    entities = []
    
    try:
        # Load map file
        dmx_model = Datamodel.Load(vmap_path, DeferredMode.Automatic)
        root = dmx_model.Root
        if root is None or not root.ContainsKey("world") or root["world"] is None:
            return []
            
        world = root["world"]
        
        # Traverse the hierarchy recursively starting from world
        def traverse(el, parent=None):
            if el is None:
                return
                
            cn = el.ClassName
            if cn == "CMapGroup":
                origin = [0.0, 0.0, 0.0]
                if el.ContainsKey("origin") and el["origin"] is not None:
                    try:
                        origin = [float(el["origin"].X), float(el["origin"].Y), float(el["origin"].Z)]
                    except:
                        pass
                angles = [0.0, 0.0, 0.0]
                if el.ContainsKey("angles") and el["angles"] is not None:
                    try:
                        angles = [float(el["angles"].Pitch), float(el["angles"].Yaw), float(el["angles"].Roll)]
                    except:
                        pass
                scales = [1.0, 1.0, 1.0]
                if el.ContainsKey("scales") and el["scales"] is not None:
                    try:
                        scales = [float(el["scales"].X), float(el["scales"].Y), float(el["scales"].Z)]
                    except:
                        pass
                        
                child_count = 0
                def count_children(child_el):
                    nonlocal child_count
                    if child_el.ClassName in ["CMapEntity", "CMapSmartProp"]:
                        child_count += 1
                    if child_el.ContainsKey("children") and child_el["children"] is not None:
                        for c in child_el["children"]:
                            count_children(c)
                            
                if el.ContainsKey("children") and el["children"] is not None:
                    for c in el["children"]:
                        count_children(c)
                        
                entities.append({
                    "type": "group",
                    "classname": "CMapGroup",
                    "name": el.Name or f"Group_{el['nodeID']}",
                    "model": f"Group with {child_count} elements",
                    "origin": origin,
                    "angles": angles,
                    "scales": scales,
                    "targetname": el.Name or "",
                    "hammerid": el["nodeID"] if el.ContainsKey("nodeID") else None,
                })
                # Don't scan children separately
                return
                
            elif cn == "CMapSmartProp":
                origin = [0.0, 0.0, 0.0]
                if el.ContainsKey("origin") and el["origin"] is not None:
                    try:
                        origin = [float(el["origin"].X), float(el["origin"].Y), float(el["origin"].Z)]
                    except:
                        pass
                angles = [0.0, 0.0, 0.0]
                if el.ContainsKey("angles") and el["angles"] is not None:
                    try:
                        angles = [float(el["angles"].Pitch), float(el["angles"].Yaw), float(el["angles"].Roll)]
                    except:
                        pass
                scales = [1.0, 1.0, 1.0]
                if el.ContainsKey("scales") and el["scales"] is not None:
                    try:
                        scales = [float(el["scales"].X), float(el["scales"].Y), float(el["scales"].Z)]
                    except:
                        pass
                        
                smartprop_file = el["smartPropFilename"] if el.ContainsKey("smartPropFilename") else ""
                entities.append({
                    "type": "smartprop",
                    "classname": "CMapSmartProp",
                    "name": el.Name or f"SmartProp_{el['nodeID']}",
                    "model": smartprop_file,
                    "origin": origin,
                    "angles": angles,
                    "scales": scales,
                    "targetname": el.Name or "",
                    "hammerid": el["nodeID"] if el.ContainsKey("nodeID") else None,
                })
                return
                
            elif cn == "CMapEntity" and el.ContainsKey("entity_properties"):
                ep = el["entity_properties"]
                if ep is not None:
                    classname = ep["classname"] if ep.ContainsKey("classname") else "None"
                    if classname.startswith("prop_") or "smart" in classname.lower():
                        model = ep["model"] if ep.ContainsKey("model") else None
                        if not model and ep.ContainsKey("model_name"):
                            model = ep["model_name"]
                            
                        origin = [0.0, 0.0, 0.0]
                        if el.ContainsKey("origin") and el["origin"] is not None:
                            try:
                                origin = [float(el["origin"].X), float(el["origin"].Y), float(el["origin"].Z)]
                            except:
                                pass
                                
                        angles = [0.0, 0.0, 0.0]
                        if el.ContainsKey("angles") and el["angles"] is not None:
                            try:
                                angles = [float(el["angles"].Pitch), float(el["angles"].Yaw), float(el["angles"].Roll)]
                            except:
                                pass
                                
                        scales = [1.0, 1.0, 1.0]
                        if el.ContainsKey("scales") and el["scales"] is not None:
                            try:
                                scales = [float(el["scales"].X), float(el["scales"].Y), float(el["scales"].Z)]
                            except:
                                pass
                                
                        entities.append({
                            "type": "prop",
                            "classname": classname,
                            "name": el.Name or f"Prop_{classname}_{el['nodeID']}",
                            "model": model or "",
                            "origin": origin,
                            "angles": angles,
                            "scales": scales,
                            "targetname": ep["targetname"] if ep.ContainsKey("targetname") else "",
                            "hammerid": ep["hammerid"] if ep.ContainsKey("hammerid") else None,
                        })
            
            # Recurse children
            if el.ContainsKey("children") and el["children"] is not None:
                for child in el["children"]:
                    traverse(child, el)
                    
        traverse(world)
        
    except Exception as e:
        print(f"Error scanning VMAP file {vmap_path}: {e}")
    finally:
        if dmx_model is not None and hasattr(dmx_model, 'Dispose'):
            dmx_model.Dispose()
        import gc; gc.collect()
        try:
            import System
            System.GC.Collect()
            System.GC.WaitForPendingFinalizers()
        except:
            pass
            
    return entities

def convert_vmap_props_to_vsmart(
    vmap_path: str,
    selected_indices: List[int],
    output_vsmart_path: str,
    pivot_strategy: str = "center"
) -> bool:
    """
    Converts a selection of props, groups, or smartprops in a VMAP file into a single SmartProp (.vsmart) file.
    Deletes the original elements from the map and replaces them with a single subclass_prop_smart
    entity at the calculated pivot point.
    """
    Datamodel, Element, DeferredMode = setup_keyvalues2()
    import clr
    import System
    from System.Numerics import Vector3
    import Datamodel as DM

    if not os.path.exists(vmap_path):
        print(f"Error: Map file not found at {vmap_path}")
        return False

    dmx_model = None
    try:
        # 1. Load the map
        dmx_model = Datamodel.Load(vmap_path, DeferredMode.Automatic)
        root = dmx_model.Root
        world = root["world"]
        
        # 2. Rescan to get references and parent relationships inside the active datamodel
        entities = []
        def traverse(el, parent=None):
            if el is None: return
            cn = el.ClassName
            if cn in ["CMapGroup", "CMapSmartProp", "CMapEntity"]:
                if cn in ["CMapGroup", "CMapSmartProp"]:
                    entities.append((el, parent))
                    return
                elif cn == "CMapEntity" and el.ContainsKey("entity_properties"):
                    ep = el["entity_properties"]
                    if ep is not None:
                        classname = ep["classname"] if ep.ContainsKey("classname") else ""
                        if classname.startswith("prop_") or "smart" in classname.lower():
                            entities.append((el, parent))
                            
            if el.ContainsKey("children") and el["children"] is not None:
                for child in el["children"]:
                    traverse(child, el)
                    
        traverse(world)
        
        # Filter to selected ones
        selected_entities = []
        for idx in selected_indices:
            if idx < len(entities):
                selected_entities.append(entities[idx])
                
        if not selected_entities:
            print("Error: No props selected for conversion.")
            return False

        # 3. Calculate the pivot point P
        origins = []
        for el, _ in selected_entities:
            if el.ContainsKey("origin") and el["origin"] is not None:
                try:
                    origins.append([float(el["origin"].X), float(el["origin"].Y), float(el["origin"].Z)])
                except:
                    pass
        if not origins:
            origins = [[0.0, 0.0, 0.0]]
            
        if pivot_strategy == "first":
            pivot = origins[0]
        elif pivot_strategy == "center":
            avg_x = sum(o[0] for o in origins) / len(origins)
            avg_y = sum(o[1] for o in origins) / len(origins)
            avg_z = sum(o[2] for o in origins) / len(origins)
            pivot = [avg_x, avg_y, avg_z]
        else: # "origin"
            pivot = [0.0, 0.0, 0.0]

        # Helper to convert VMAP elements recursively
        element_id_counter = [1]
        
        def convert_element(el, parent_origin, parent_angles=[0.0, 0.0, 0.0], parent_scale=[1.0, 1.0, 1.0]):
            el_cn = el.ClassName
            
            origin = [0.0, 0.0, 0.0]
            if el.ContainsKey("origin") and el["origin"] is not None:
                try:
                    origin = [float(el["origin"].X), float(el["origin"].Y), float(el["origin"].Z)]
                except:
                    pass
            angles = [0.0, 0.0, 0.0]
            if el.ContainsKey("angles") and el["angles"] is not None:
                try:
                    angles = [float(el["angles"].Pitch), float(el["angles"].Yaw), float(el["angles"].Roll)]
                except:
                    pass
            scales = [1.0, 1.0, 1.0]
            if el.ContainsKey("scales") and el["scales"] is not None:
                try:
                    scales = [float(el["scales"].X), float(el["scales"].Y), float(el["scales"].Z)]
                except:
                    pass
                    
            diff_pos = [origin[0] - parent_origin[0], origin[1] - parent_origin[1], origin[2] - parent_origin[2]]
            if parent_angles != [0.0, 0.0, 0.0]:
                rel_pos = list(inverse_rotate_point_pyr(diff_pos[0], diff_pos[1], diff_pos[2], parent_angles[0], parent_angles[1], parent_angles[2]))
            else:
                rel_pos = diff_pos
                
            rel_rot = normalize_angles([angles[0] - parent_angles[0], angles[1] - parent_angles[1], angles[2] - parent_angles[2]])
            rel_scale = [scales[i] / parent_scale[i] for i in range(3)]
            
            modifiers = []
            if rel_pos != [0.0, 0.0, 0.0]:
                modifiers.append({
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": {
                        "m_Components": format_imported_vector(rel_pos)
                    }
                })
            if rel_rot != [0.0, 0.0, 0.0]:
                modifiers.append({
                    "_class": "CSmartPropOperation_Rotate",
                    "m_vRotation": {
                        "m_Components": format_imported_vector(rel_rot)
                    }
                })
                
            element_id = element_id_counter[0]
            element_id_counter[0] += 1
            
            if el_cn == "CMapGroup":
                group_element = {
                    "_class": "CSmartPropElement_Group",
                    "m_nElementID": element_id,
                    "m_sLabel": el.Name or f"Group_{el['nodeID']}",
                    "m_Modifiers": modifiers,
                    "m_SelectionCriteria": [],
                    "m_Children": []
                }
                if rel_scale != [1.0, 1.0, 1.0]:
                    should_round = get_settings_bool('SmartPropEditor', 'round_vmap_values', False)
                    if should_round:
                        try:
                            decimals = int(get_settings_value('SmartPropEditor', 'round_vmap_decimals', 4))
                        except:
                            decimals = 4
                        s_val = round(rel_scale[0], decimals)
                    else:
                        s_val = {"m_Expression": str(rel_scale[0])}
                    modifiers.append({
                        "_class": "CSmartPropOperation_Scale",
                        "m_flScale": s_val
                    })
                    
                if el.ContainsKey("children") and el["children"] is not None:
                    for child in el["children"]:
                        if child.ClassName in ["CMapEntity", "CMapSmartProp", "CMapGroup"]:
                            child_vsmart = convert_element(child, origin, angles, scales)
                            if child_vsmart:
                                group_element["m_Children"].append(child_vsmart)
                return group_element
                
            elif el_cn == "CMapSmartProp":
                smartprop_file = el["smartPropFilename"] if el.ContainsKey("smartPropFilename") else ""
                smartprop_element = {
                    "_class": "CSmartPropElement_SmartProp",
                    "m_sSmartProp": smartprop_file,
                    "m_nElementID": element_id,
                    "m_sLabel": el.Name or f"SmartProp_{el['nodeID']}",
                    "m_Modifiers": modifiers,
                    "m_SelectionCriteria": []
                }
                if rel_scale != [1.0, 1.0, 1.0]:
                    if len(set(rel_scale)) == 1:
                        should_round = get_settings_bool('SmartPropEditor', 'round_vmap_values', False)
                        if should_round:
                            try:
                                decimals = int(get_settings_value('SmartPropEditor', 'round_vmap_decimals', 4))
                            except:
                                decimals = 4
                            s_val = round(rel_scale[0], decimals)
                        else:
                            s_val = {"m_Expression": str(rel_scale[0])}
                        smartprop_element["m_flUniformScale"] = s_val
                    else:
                        modifiers.append({
                            "_class": "CSmartPropOperation_Scale",
                            "m_flScale": format_imported_vector(rel_scale)[0]
                        })
                return smartprop_element
                
            elif el_cn == "CMapEntity":
                ep = el["entity_properties"]
                if ep is not None:
                    classname = ep["classname"] if ep.ContainsKey("classname") else ""
                    model_path = ep["model"] if ep.ContainsKey("model") else ""
                    if not model_path and ep.ContainsKey("model_name"):
                        model_path = ep["model_name"]
                        
                    model_name = os.path.splitext(os.path.basename(model_path))[0] if model_path else f"Prop_{classname}_{el['nodeID']}"
                    model_element = {
                        "_class": "CSmartPropElement_Model",
                        "m_nElementID": element_id,
                        "m_sModelName": model_path,
                        "m_sLabel": model_name,
                        "m_Modifiers": modifiers,
                        "m_SelectionCriteria": []
                    }
                    if rel_scale != [1.0, 1.0, 1.0]:
                        model_element["m_vModelScale"] = {"m_Components": format_imported_vector(rel_scale)}
                    return model_element
            return None

        # 4. Generate the VSMART document data
        vsmart_children = []
        for el, _ in selected_entities:
            converted = convert_element(el, pivot, [0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
            if converted:
                vsmart_children.append(converted)

        # Wrap in a single parent Group element centered at the pivot
        vmap_basename = os.path.splitext(os.path.basename(vmap_path))[0]
        element_id = element_id_counter[0]
        element_id_counter[0] += 1
        
        parent_group_vsmart = {
            "_class": "CSmartPropElement_Group",
            "m_nElementID": element_id,
            "m_sLabel": f"Imported_{vmap_basename}",
            "m_Modifiers": [
                {
                    "_class": "CSmartPropOperation_Translate",
                    "m_vPosition": {
                        "m_Components": format_imported_vector(pivot)
                    }
                }
            ],
            "m_SelectionCriteria": [],
            "m_Children": vsmart_children
        }

        vsmart_doc = {
            "generic_data_type": "CSmartPropRoot",
            "m_nContentVersion": 1,
            "m_Children": [parent_group_vsmart],
            "m_Variables": [],
            "m_Choices": []
        }

        # 5. Write the VSMART file (as KV3)
        print(f"Saving SmartProp configuration to: {output_vsmart_path}...")
        os.makedirs(os.path.dirname(output_vsmart_path), exist_ok=True)
        kv3_content = JsonToKv3(vsmart_doc)
        with open(output_vsmart_path, "w") as f:
            f.write(kv3_content)

        # 6. Delete old entities from VMAP
        print(f"Deleting {len(selected_entities)} old entities from map...")
        for el, parent in selected_entities:
            if parent is not None:
                parent["children"].Remove(el)
            else:
                world["children"].Remove(el)

        # 7. Create and insert replacement subclass_prop_smart entity
        # Formulate relative smartprop path relative to addon content folder
        addon_name = get_addon_name() or "addon"
        cs2_path = get_cs2_path()
        content_addon_root = os.path.normpath(os.path.join(cs2_path, "content", "csgo_addons", addon_name))
        
        # Find relative path of smartprop inside addon content
        try:
            rel_smartprop = os.path.relpath(output_vsmart_path, content_addon_root).replace("\\", "/")
        except ValueError:
            # Fallback if on different drives (e.g. D: and E: during tests)
            parts = output_vsmart_path.replace("\\", "/").split("/smartprops/", 1)
            if len(parts) > 1:
                rel_smartprop = "smartprops/" + parts[1]
            else:
                rel_smartprop = os.path.basename(output_vsmart_path)
        
        print("Creating replacement subclass_prop_smart entity...")
        new_entity = Element(dmx_model, "smartprop_group", None, "CMapEntity")
        
        # Configure entity_properties
        ep = Element(dmx_model, "", None, "CMapEntityProperties")
        ep["classname"] = "subclass_prop_smart"
        ep["smartprop"] = rel_smartprop
        
        new_entity["entity_properties"] = ep
        new_entity["origin"] = Vector3(float(pivot[0]), float(pivot[1]), float(pivot[2]))
        new_entity["angles"] = DM.QAngle(0.0, 0.0, 0.0)
        new_entity["scales"] = Vector3(1.0, 1.0, 1.0)
        
        # Add to top-level world children
        world["children"].Add(new_entity)
        
        # 8. Save the VMAP to a temp file first to avoid read locks from Windows
        temp_vmap_path = vmap_path + ".tmp"
        print(f"Saving map changes to temp file: {temp_vmap_path}...")
        dmx_model.Save(temp_vmap_path, dmx_model.Encoding, dmx_model.EncodingVersion)
        
        # 9. Dispose dmx_model to release the read lock
        if hasattr(dmx_model, 'Dispose'):
            dmx_model.Dispose()
        dmx_model = None
        
        # Force garbage collection to release Windows file handle locks
        import gc; gc.collect()
        try:
            import System
            System.GC.Collect()
            System.GC.WaitForPendingFinalizers()
        except:
            pass
            
        # 10. Replace original file with the modified temp file
        if os.path.exists(vmap_path):
            os.remove(vmap_path)
        os.rename(temp_vmap_path, vmap_path)
        
        print("Map conversion completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error performing map conversion: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if dmx_model is not None and hasattr(dmx_model, 'Dispose'):
            dmx_model.Dispose()
        import gc; gc.collect()
        try:
            import System
            System.GC.Collect()
            System.GC.WaitForPendingFinalizers()
        except:
            pass
