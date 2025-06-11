import zipfile
import os
import sys
import subprocess
from src.dotnet import setup_keyvalues2


def find_entities_by_classname(element, classname, datamodel=None, show_entity_properties=True, _results=None):
    """Find all entities with a specific classname in the element tree.

    Args:
        element: The root element to search.
        classname (str): The classname to search for (e.g., "point_camera", "info_player_start").
        datamodel: The datamodel object (optional).
        show_entity_properties (bool): Whether to print/collect all entity_properties.
        _results (list): Internal accumulator for recursion.

    Returns:
        list of dicts with entity info.
    """
    if _results is None:
        _results = []

    try:
        entity_properties = element["entity_properties"]
        if entity_properties is not None:
            entity_classname = entity_properties["classname"]
            if entity_classname == classname:
                entity_info = {
                    "classname": entity_classname,
                    "origin": element["origin"] if "origin" in element else None,
                    "angles": element["angles"] if "angles" in element else None,
                    "targetname": entity_properties["targetname"] if "targetname" in entity_properties else None,
                }
                
                # Add common entity properties
                common_props = ["model", "rendercolor", "renderamt", "spawnflags", "hammerid", "id"]
                for prop in common_props:
                    if prop in entity_properties:
                        entity_info[prop] = entity_properties[prop]
                
                # Add classname-specific properties
                if classname == "point_camera":
                    entity_info["FOV"] = entity_properties["FOV"] if "FOV" in entity_properties else None
                elif classname == "light_environment":
                    entity_info["brightness"] = entity_properties["brightness"] if "brightness" in entity_properties else None
                    entity_info["color"] = entity_properties["color"] if "color" in entity_properties else None
                elif classname in ["info_player_start", "info_player_terrorist", "info_player_counterterrorist"]:
                    entity_info["enabled"] = entity_properties["enabled"] if "enabled" in entity_properties else None
                
                if show_entity_properties:
                    entity_info["entity_properties"] = dict(entity_properties)
                _results.append(entity_info)

                print(f"\nFound {classname}:")
                print(f"  Origin: {entity_info['origin'] if entity_info['origin'] is not None else 'N/A'}")
                print(f"  Angles: {entity_info['angles'] if entity_info['angles'] is not None else 'N/A'}")
                print(f"  TargetName: {entity_info['targetname'] if entity_info['targetname'] is not None else 'N/A'}")
                
                # Print classname-specific properties
                if classname == "point_camera" and "FOV" in entity_info:
                    print(f"  FOV: {entity_info['FOV'] if entity_info['FOV'] is not None else 'N/A'}")
                
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
                find_entities_by_classname(child, classname, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    try:
        entities = element["entities"]
        if entities is not None:
            for entity in entities:
                find_entities_by_classname(entity, classname, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    try:
        world = element["world"]
        if world is not None:
            find_entities_by_classname(world, classname, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    if datamodel is not None and element == datamodel.Root:
        print(f"\nSearching all elements in datamodel for {classname}...")
        for el in datamodel.AllElements:
            if el != element:
                try:
                    ep = el["entity_properties"]
                    if ep is not None:
                        cn = ep["classname"]
                        if cn == classname:
                            entity_info = {
                                "classname": cn,
                                "origin": el["origin"] if "origin" in el else None,
                                "angles": el["angles"] if "angles" in el else None,
                                "targetname": ep["targetname"] if "targetname" in ep else None,
                            }
                            
                            # Add common entity properties
                            common_props = ["model", "rendercolor", "renderamt", "spawnflags", "hammerid", "id"]
                            for prop in common_props:
                                if prop in ep:
                                    entity_info[prop] = ep[prop]
                            
                            # Add classname-specific properties
                            if classname == "point_camera":
                                entity_info["FOV"] = ep["FOV"] if "FOV" in ep else None
                            elif classname == "light_environment":
                                entity_info["brightness"] = ep["brightness"] if "brightness" in ep else None
                                entity_info["color"] = ep["color"] if "color" in ep else None
                            elif classname in ["info_player_start", "info_player_terrorist", "info_player_counterterrorist"]:
                                entity_info["enabled"] = ep["enabled"] if "enabled" in ep else None
                            
                            if show_entity_properties:
                                entity_info["entity_properties"] = dict(ep)
                            _results.append(entity_info)

                            print(f"\nFound {classname} in AllElements:")
                            print(f"  Origin: {entity_info['origin'] if entity_info['origin'] is not None else 'N/A'}")
                            print(f"  Angles: {entity_info['angles'] if entity_info['angles'] is not None else 'N/A'}")
                            print(f"  TargetName: {entity_info['targetname'] if entity_info['targetname'] is not None else 'N/A'}")
                            
                            if classname == "point_camera" and "FOV" in entity_info:
                                print(f"  FOV: {entity_info['FOV'] if entity_info['FOV'] is not None else 'N/A'}")
                            
                            if show_entity_properties:
                                print("  All entity_properties:")
                                print_element_attributes(ep, "    ")
                except Exception:
                    pass

    return _results


def find_point_cameras(element, datamodel=None, show_entity_properties=True, _results=None):
    """Find all point_camera entities in the element tree.
    
    This function is kept for backward compatibility.
    """
    return find_entities_by_classname(element, "point_camera", datamodel, show_entity_properties, _results)


def find_all_entities(element, datamodel=None, show_entity_properties=False, _results=None):
    """Find all entities in the element tree and group them by classname.

    Args:
        element: The root element to search.
        datamodel: The datamodel object (optional).
        show_entity_properties (bool): Whether to print/collect all entity_properties.
        _results (dict): Internal accumulator for recursion.

    Returns:
        dict: Dictionary with classnames as keys and lists of entity info as values.
    """
    if _results is None:
        _results = {}

    try:
        entity_properties = element["entity_properties"]
        if entity_properties is not None:
            classname = entity_properties["classname"]
            if classname not in _results:
                _results[classname] = []
            
            entity_info = {
                "classname": classname,
                "origin": element["origin"] if "origin" in element else None,
                "angles": element["angles"] if "angles" in element else None,
                "targetname": entity_properties["targetname"] if "targetname" in entity_properties else None,
            }
            
            # Add common entity properties
            common_props = ["model", "rendercolor", "renderamt", "spawnflags", "hammerid", "id"]
            for prop in common_props:
                if prop in entity_properties:
                    entity_info[prop] = entity_properties[prop]
            
            if show_entity_properties:
                entity_info["entity_properties"] = dict(entity_properties)
            
            _results[classname].append(entity_info)
    except Exception:
        pass

    # Recursively search in child elements
    try:
        children = element["children"]
        if children is not None:
            for child in children:
                find_all_entities(child, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    try:
        entities = element["entities"]
        if entities is not None:
            for entity in entities:
                find_all_entities(entity, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    try:
        world = element["world"]
        if world is not None:
            find_all_entities(world, datamodel, show_entity_properties, _results)
    except Exception:
        pass

    if datamodel is not None and element == datamodel.Root:
        print("\nSearching all elements in datamodel...")
        for el in datamodel.AllElements:
            if el != element:
                try:
                    ep = el["entity_properties"]
                    if ep is not None:
                        classname = ep["classname"]
                        if classname not in _results:
                            _results[classname] = []
                        
                        entity_info = {
                            "classname": classname,
                            "origin": el["origin"] if "origin" in el else None,
                            "angles": el["angles"] if "angles" in el else None,
                            "targetname": ep["targetname"] if "targetname" in ep else None,
                        }
                        
                        # Add common entity properties
                        common_props = ["model", "rendercolor", "renderamt", "spawnflags", "hammerid", "id"]
                        for prop in common_props:
                            if prop in ep:
                                entity_info[prop] = ep[prop]
                        
                        if show_entity_properties:
                            entity_info["entity_properties"] = dict(ep)
                        
                        _results[classname].append(entity_info)
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
    This version ensures the VMAP file is not locked by reading it into memory first.

    Args:
        dmx_file_path (str): Path to the DMX file.
        show_entity_properties (bool): Whether to print/collect all entity_properties.

    Returns:
        list of dicts with camera info.
    """
    Datamodel, Element, DeferredMode = setup_keyvalues2()

    dmx_model = None
    cameras = []

    try:
        # Method 1: Try to read file into memory first
        import tempfile
        import shutil

        # Create a temporary copy of the file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.vmap', delete=False) as temp_file:
            temp_path = temp_file.name
            # Copy the file content
            with open(dmx_file_path, 'rb') as source:
                shutil.copyfileobj(source, temp_file)

        # Load from the temporary file
        try:
            dmx_model = Datamodel.Load(temp_path, DeferredMode.Automatic)
            root = dmx_model.Root

            if root is None:
                print("Root element is null.")
            else:
                # Extract camera data
                cameras = find_point_cameras(root, dmx_model, show_entity_properties=show_entity_properties)
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        print(f"Error using temporary file method: {e}")

        # Method 2: Fallback to direct loading with immediate disposal
        try:
            dmx_model = Datamodel.Load(dmx_file_path, DeferredMode.Automatic)
            root = dmx_model.Root

            if root is None:
                print("Root element is null.")
            else:
                # Extract camera data quickly
                cameras = find_point_cameras(root, dmx_model, show_entity_properties=show_entity_properties)
        except Exception as e2:
            print(f"Error loading VMAP file: {e2}")

    finally:
        # Always dispose of the datamodel to ensure file is not locked
        if dmx_model is not None:
            try:
                if hasattr(dmx_model, 'Dispose'):
                    dmx_model.Dispose()
                elif hasattr(dmx_model, 'Close'):
                    dmx_model.Close()
            except:
                pass

            # Clear reference
            dmx_model = None

        # Force garbage collection to ensure resources are released
        import gc
        gc.collect()

    return cameras

if __name__ == "__main__":
    dmx_file_path = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_sanctum\maps\de_sanctum.vmap"
    # Example usage: disable entity_properties output
    print(parse(dmx_file_path, show_entity_properties=False))