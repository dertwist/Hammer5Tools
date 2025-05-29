import zipfile
import os
import sys
from pythonnet import load
load("coreclr")

import clr

def setup_keyvalues2():
    """Setup the Datamodel.NET library for use with Python."""
    dll_path = os.path.abspath(os.path.join('keyvalues2', "Datamodel.NET.dll"))
    print(f"DLL Path: {dll_path}")
    print(f"DLL Exists: {os.path.exists(dll_path)}")

    if not os.path.exists(dll_path):
        raise FileNotFoundError(f"DLL not found at: {dll_path}")

    dll_dir = os.path.dirname(dll_path)
    if dll_dir not in sys.path:
        sys.path.append(dll_dir)

    try:
        clr.AddReference("Datamodel.NET")
    except:
        try:
            clr.AddReference(dll_path)
        except:
            import System
            assembly = System.Reflection.Assembly.LoadFrom(dll_path)
            clr.AddReference(assembly)

    import Datamodel
    from Datamodel.Codecs import DeferredMode

    return Datamodel.Datamodel, Datamodel.Element, DeferredMode


def find_point_cameras(element, datamodel=None, show_entity_properties=True, _results=None):
    """Find all point_camera entities in the element tree.

    Args:
        element: The root element to search.
        datamodel: The datamodel object (optional).
        show_entity_properties (bool): Whether to print/collect all entity_properties.
        _results (list): Internal accumulator for recursion.

    Returns:
        list of dicts with camera info.
    """
    if _results is None:
        _results = []

    try:
        entity_properties = element["entity_properties"]
        if entity_properties is not None:
            classname = entity_properties["classname"]
            if classname == "point_camera":
                camera_info = {
                    "origin": element["origin"] if "origin" in element else None,
                    "angles": element["angles"] if "angles" in element else None,
                    "targetname": entity_properties["targetname"] if "targetname" in entity_properties else None,
                    "FOV": entity_properties["FOV"] if "FOV" in entity_properties else None,
                }
                if show_entity_properties:
                    camera_info["entity_properties"] = dict(entity_properties)
                _results.append(camera_info)

                print("\nFound point_camera:")
                print(f"  Origin: {camera_info['origin'] if camera_info['origin'] is not None else 'N/A'}")
                print(f"  Angles: {camera_info['angles'] if camera_info['angles'] is not None else 'N/A'}")
                print(f"  TargetName: {camera_info['targetname'] if camera_info['targetname'] is not None else 'N/A'}")
                print(f"  FOV: {camera_info['FOV'] if camera_info['FOV'] is not None else 'N/A'}")
                if show_entity_properties:
                    print("  All entity_properties:")
                    print_element_attributes(entity_properties, "    ")
    except Exception:
        pass

    # Recursively search in child elements
    try:
        children = element["children"]
        if children is not None:
            for child in children:
                find_point_cameras(child, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    try:
        entities = element["entities"]
        if entities is not None:
            for entity in entities:
                find_point_cameras(entity, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    try:
        world = element["world"]
        if world is not None:
            find_point_cameras(world, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    if datamodel is not None and element == datamodel.Root:
        print("\nSearching all elements in datamodel...")
        for el in datamodel.AllElements:
            if el != element:
                try:
                    ep = el["entity_properties"]
                    if ep is not None:
                        cn = ep["classname"]
                        if cn == "point_camera":
                            camera_info = {
                                "origin": el["origin"] if "origin" in el else None,
                                "angles": el["angles"] if "angles" in el else None,
                                "targetname": ep["targetname"] if "targetname" in ep else None,
                                "FOV": ep["FOV"] if "FOV" in ep else None,
                            }
                            if show_entity_properties:
                                camera_info["entity_properties"] = dict(ep)
                            _results.append(camera_info)

                            print("\nFound point_camera in AllElements:")
                            print(f"  Origin: {camera_info['origin'] if camera_info['origin'] is not None else 'N/A'}")
                            print(f"  Angles: {camera_info['angles'] if camera_info['angles'] is not None else 'N/A'}")
                            print(f"  TargetName: {camera_info['targetname'] if camera_info['targetname'] is not None else 'N/A'}")
                            print(f"  FOV: {camera_info['FOV'] if camera_info['FOV'] is not None else 'N/A'}")
                            if show_entity_properties:
                                print("  All entity_properties:")
                                print_element_attributes(ep, "    ")
                except Exception:
                    pass

    return _results


def print_element_attributes(element, indent):
    """Print common attributes of an element."""
    common_attributes = [
        "classname", "targetname", "origin", "angles", "FOV",
        "enabled", "model", "rendercolor", "renderamt",
        "spawnflags", "hammerid", "id"
    ]

    for attr_name in common_attributes:
        try:
            value = element[attr_name]
            if value is not None:
                value_type = type(value).__name__
                print(f"{indent}{attr_name}: {value} ({value_type})")
        except Exception:
            pass


def explore_element(element, depth, brief=False):
    """Recursively explore the structure of an element."""
    if depth > 5:
        return

    indent = "  " * depth
    element_type = type(element).__name__
    print(f"{indent}Element: {element.Name} (Class: {element_type}, ID: {element.ID})")

    if not brief:
        attributes_to_check = [
            "children", "entities", "world", "entity_properties",
            "classname", "targetname", "origin", "angles"
        ]

        for attr_name in attributes_to_check:
            try:
                value = element[attr_name]
                if value is not None:
                    if hasattr(value, 'Name') and hasattr(value, 'ID'):
                        print(f"{indent}  {attr_name}: Element")
                        explore_element(value, depth + 1, brief)
                    elif hasattr(value, '__iter__') and not isinstance(value, str):
                        try:
                            element_list = list(value)
                            if element_list and hasattr(element_list[0], 'Name'):
                                print(f"{indent}  {attr_name}: List<Element> ({len(element_list)} items)")
                                if len(element_list) > 0 and depth < 3:
                                    for i, child in enumerate(element_list[:3]):
                                        explore_element(child, depth + 1, brief)
                                    if len(element_list) > 3:
                                        print(f"{indent}  ... and {len(element_list) - 3} more")
                        except Exception:
                            value_type = type(value).__name__
                            print(f"{indent}  {attr_name}: {value} ({value_type})")
                    else:
                        value_type = type(value).__name__
                        print(f"{indent}  {attr_name}: {value} ({value_type})")
            except Exception:
                pass


def parse(dmx_file_path, show_entity_properties=True):
    """
    Parse the DMX file and return a list of point_camera entities.

    Args:
        dmx_file_path (str): Path to the DMX file.
        show_entity_properties (bool): Whether to print/collect all entity_properties.

    Returns:
        list of dicts with camera info.
    """
    Datamodel, Element, DeferredMode = setup_keyvalues2()
    dmx_model = Datamodel.Load(dmx_file_path, DeferredMode.Automatic)
    root = dmx_model.Root
    if root is None:
        print("Root element is null.")
        return []
    return find_point_cameras(root, dmx_model, show_entity_properties=show_entity_properties)

if __name__ == "__main__":
    dmx_file_path = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_sanctum\maps\de_sanctum.vmap"
    # Example usage: disable entity_properties output
    print(parse(dmx_file_path, show_entity_properties=False))