import logging
import ast
import re
from PySide6.QtWidgets import QTreeWidget
from PySide6.QtCore import Qt

from gui.editors.smartprop_editor.choices import build_choices_tree, read_choices_tree
from gui.editors.smartprop_editor.choices_model import format_choices, parse_choices
from gui.common import editor_info, JsonToKv3, Kv3ToJson
from gui.editors.smartprop_editor._common import (
    disable_line_value_length_limit_keys,
    get_clean_class_name,
    get_clean_class_name_value,
    get_label_id_from_value
)
from gui.widgets.element_id import (
    set_element_id,
    get_element_id_last,
    get_element_id_key,
    update_value_element_id,
    update_child_element_id_value,
)
from gui.widgets import HierarchyItemModel, exception_handler
from gui.editors.smartprop_editor.objects import variable_prefix, element_prefix
from gui.editors.smartprop_editor.document_model import (
    SmartPropDocumentState,
    SmartPropNode,
    format_smartprop,
    parse_smartprop,
    variable_rows_to_kv3,
)

log = logging.getLogger(__name__)

# [Reference handling / merging logic]

def merge_reference_data(reference_data: dict, ref_object_data: dict) -> dict:
    """
    Merge data from 'reference_data' (from the referenced element) into 'ref_object_data'
    (the reference object). The reference object inherits all data from the reference and then
    selectively overrides those values with its own, except for the unique keys.

    Unique keys: m_nElementID, m_sReferenceObjectID, m_nReferenceID.

    For list-type keys containing elements with IDs (like m_Modifiers, m_SelectionCriteria):
    - If an element with the same ID exists in both lists, the reference object's element
      overwrites the reference's element key by key.
    - If an element exists only in the reference object, it's added to the merged list.
    - If an element exists only in the reference, it's included in the merged list.

    For other keys, if the reference object's value is None then the reference's value is used.
    """
    unique_keys = ["m_nElementID", "m_sReferenceObjectID", "m_nReferenceID"]
    list_keys_with_elements = ["m_Modifiers", "m_SelectionCriteria"]

    # Start with a copy of the reference data
    merged_data = dict(reference_data)

    # Apply reference object data with special handling for certain keys
    for k, v in ref_object_data.items():
        # Always use the reference object's values for unique keys
        if k in unique_keys:
            merged_data[k] = v
        # Special handling for list-type keys containing elements with IDs
        elif k in list_keys_with_elements:
            ref_value = reference_data.get(k, [])
            if isinstance(v, list) and isinstance(ref_value, list):
                # Create a dictionary of elements from the reference, keyed by their ID
                ref_elements_by_id = {}
                for elem in ref_value:
                    if isinstance(elem, dict) and "m_nElementID" in elem:
                        ref_elements_by_id[elem["m_nElementID"]] = elem

                # Start with an empty result list
                merged_list = []

                # Process elements from the reference object
                for elem in v:
                    if isinstance(elem, dict) and "m_nElementID" in elem:
                        elem_id = elem["m_nElementID"]
                        # If this element exists in the reference, merge them
                        if elem_id in ref_elements_by_id:
                            # Start with the reference element and update with ref object's values
                            merged_elem = dict(ref_elements_by_id[elem_id])
                            for elem_k, elem_v in elem.items():
                                merged_elem[elem_k] = elem_v
                            merged_list.append(merged_elem)
                            del ref_elements_by_id[elem_id]
                        else:
                            # Element only exists in ref object, add it directly
                            merged_list.append(elem)
                    else:
                        # Element doesn't have an ID, add it directly
                        merged_list.append(elem)

                for elem in ref_elements_by_id.values():
                    merged_list.append(elem)

                merged_data[k] = merged_list
            else:
                # If either value is not a list, use the reference object's value
                merged_data[k] = v
        else:
            # For other keys, if ref object's value is None then inherit reference's value
            ref_value = reference_data.get(k)
            if v is None and ref_value is not None:
                merged_data[k] = ref_value
            else:
                merged_data[k] = v

    return merged_data

def restore_reference_objects(file_data: dict):
    """
    While opening a file, revert each reference object to its non-processed version stored in
    the m_ReferenceObjects dictionary, using the m_sReferenceObjectID key.

    This ensures that any merged reference object is replaced by its original data.
    """
    if "m_ReferenceObjects" not in file_data:
        return

    ref_objs = file_data["m_ReferenceObjects"]

    def revert_item_recursive(item_data: dict):
        s_ref_id = item_data.get("m_sReferenceObjectID")
        if s_ref_id and s_ref_id in ref_objs:
            old_children = item_data.pop("m_Children", None)
            item_data.clear()
            item_data.update(ref_objs[s_ref_id])
            if old_children and "m_Children" not in item_data:
                item_data["m_Children"] = old_children
        if "m_Children" in item_data:
            for child in item_data["m_Children"]:
                revert_item_recursive(child)

    if "m_Children" in file_data:
        for child in file_data["m_Children"]:
            revert_item_recursive(child)

# [Tree item serialization and deserialization]

def serialization_hierarchy_items(item, data=None):
    """Convert tree structure to a JSON-like dict structure."""
    if data is None:
        data = {"m_Children": []}

    try:
        parent_data = item.data(0, Qt.UserRole)
        parent_data = dict(parent_data) if parent_data is not None else {}
        parent_data["m_sLabel"] = item.text(0)

        # Initialize children array if needed
        if item.childCount() > 0:
            parent_data["m_Children"] = []

        data["m_Children"].append(parent_data)

        # Process children
        if item.childCount() > 0:
            for index in range(item.childCount()):
                child = item.child(index)

                child_container = {"m_Children": []}

                # Recursively process the child and its descendants
                serialization_hierarchy_items(child, child_container)

                # (The child is now in child_container["m_Children"][0])
                if child_container["m_Children"]:
                    parent_data["m_Children"].append(child_container["m_Children"][0])
    except Exception as e:
        log.error(f"Error in serialization: {e}")

    return data
def migrate_legacy_comments(data: dict):
    """Migrate legacy m_Comment / Hammer5Tools_Comment into m_sNote."""
    if not isinstance(data, dict):
        return
    # Check if this item has legacy comment keys
    if not data.get("m_sNote"):
        for k in ("m_Comment", "m_sComment", "note", "_comment"):
            val = data.get(k)
            if val and str(val).strip():
                data["m_sNote"] = str(val).strip()
                break

    # Clean legacy comment keys
    for k in ("m_Comment", "m_sComment", "note", "_comment"):
        data.pop(k, None)

    # Clean legacy Hammer5Tools_Comment modifiers / criteria
    for array_key in ("m_Modifiers", "m_SelectionCriteria"):
        arr = data.get(array_key)
        if isinstance(arr, list):
            cleaned = []
            for item in arr:
                if isinstance(item, dict):
                    if item.get("_class") == "Hammer5Tools_Comment":
                        cmt = item.get("m_Comment") or item.get("m_sComment") or item.get("note") or item.get("_comment")
                        if cmt and not data.get("m_sNote"):
                            data["m_sNote"] = str(cmt).strip()
                    else:
                        migrate_legacy_comments(item)
                        cleaned.append(item)
            data[array_key] = cleaned

@exception_handler
def deserialize_hierarchy_item(m_Children, element_id_generator=None):
    """Convert JSON-like hierarchy into tree items recursively."""
    item_value = {}
    for key in m_Children:
        if key != "m_Children":
            item_value.update({key: m_Children[key]})

    migrate_legacy_comments(item_value)
    item_value = element_id_generator.update_child_value(item_value, force=True)
    element_id = element_id_generator.get_key(item_value)
    
    name = item_value.get("m_sLabel", get_clean_class_name_value(item_value))
    tree_item = HierarchyItemModel(
        _data=item_value,
        _name=name,
        _id=element_id,
        _class=get_clean_class_name_value(item_value)
    )
    for child_data in m_Children.get("m_Children", []):
        child_item = deserialize_hierarchy_item(child_data, element_id_generator)
        tree_item.addChild(child_item)
    return tree_item

# [Vsmart File Loading and Saving]

class VsmartOpen:
    def __init__(self, element_id_generator, filename, tree=QTreeWidget, choices_tree=QTreeWidget, variables_scrollArea=None):
        self.element_id_generator = element_id_generator
        self.filename = filename
        self.variables_scrollArea = variables_scrollArea
        self.tree = tree
        self.choices_tree = choices_tree
        self.open_file()

    def load_file(self, filename):
        with open(filename, "r") as file:
            out = file.read()
        return out

    def open_file(self):
        """Open file data, restore references, and populate tree and choices."""
        data = parse_smartprop(self.load_file(self.filename))
        restore_reference_objects(data)
        self.document_state = SmartPropDocumentState.from_mapping(data)
        self.variables = self.document_state.variables
        self.tree.clear()
        self.choices_tree.clear()
        # Set next element ID if available.
        self.next_element_id = self.document_state.metadata.get("editor_info")
        self.content_version = self.document_state.metadata.get("m_nContentVersion", 0)
        if self.next_element_id:
            if isinstance(self.next_element_id, dict):
                self.next_element_id = self.next_element_id.get("m_nElementID", None)
                if self.next_element_id:
                    self.element_id_generator.add_id(self.next_element_id)
        self.raw_choices = self.document_state.choices
        for node in self.document_state.hierarchy:
            self.populate_node(node)
        if self.variables_scrollArea is None:
            self.populate_choices(self.raw_choices)

    def populate_tree(self, data, parent=None):
        """Populate the tree hierarchy with element data."""
        state = SmartPropDocumentState.from_mapping(data)
        for node in state.hierarchy:
            self.populate_node(node, parent)

    def populate_node(self, node: SmartPropNode, parent=None):
        """Render one model-owned hierarchy node and its descendants."""
        parent = parent or self.tree.invisibleRootItem()
        migrate_legacy_comments(node.data)
        if self.next_element_id is None:
            update_value_element_id(node.data)
            node.data = update_child_element_id_value(node.data)
        child_item = HierarchyItemModel(
            _name=node.data.get("m_sLabel", get_label_id_from_value(node.data)),
            _data=node.data,
            _class=get_clean_class_name(node.data.get("_class")),
            _id=get_element_id_key(node.data),
        )
        child_item.smartprop_node = node
        parent.addChild(child_item)
        for child in node.children:
            self.populate_node(child, child_item)

    def populate_choices(self, data):
        if data is None:
            log.info("No choices")
            return False
        build_choices_tree(
            self.choices_tree,
            parse_choices(data),
            variables_scrollArea=self.variables_scrollArea,
            element_id_generator=self.element_id_generator,
        )

    def fix_names(self, parent):
        """Fix tree item names by using m_sLabel or appending a counter suffix."""
        counter = 1
        for index in range(parent.childCount()):
            child_item = parent.child(index)
            if element_prefix in child_item.text(0):
                element_value = ast.literal_eval(child_item.text(1))
                current_name = child_item.text(0)
                new_name = current_name.replace(element_prefix, "")
                new_name = f"{new_name}_{counter:02d}"
                counter += 1
                child_item.setText(0, new_name)
                if "m_sLabel" in element_value and element_value["m_sLabel"]:
                    child_item.setText(0, element_value["m_sLabel"])
                self.fix_names(child_item)

class VsmartSave:
    def __init__(self, filename, tree=None, choices_tree=QTreeWidget, variables=None,
                 content_version=None, write_file=True, document_state=None):
        self.filename = filename
        self.tree = tree
        self.variables = variables or {}
        self.choices_tree = choices_tree
        self.ref_objects = {}  # To store non-processed reference objects
        self.var_data = self.save_variables()
        self.content_version = content_version
        self.document_state = document_state
        self.choices_data = self.choices(self.choices_tree.invisibleRootItem())
        self.document_data = self.build_document()
        if write_file:
            self.save_file()

    def save_variables(self):
        """The document's ``m_Variables`` list, mapped from the extracted rows."""
        return variable_rows_to_kv3(self.variables)

    def build_document(self):
        """Build a JSON-compatible SmartProp document from the editor state."""
        out_data = {"generic_data_type": "CSmartPropRoot", "m_nContentVersion": self.content_version}
        editor_info["editor_info"].update({"m_nElementID": get_element_id_last()})
        out_data.update(editor_info)
        if self.var_data is not None:
            out_data.update({"m_Variables": self.var_data})
        if self.choices_data is not None:
            out_data.update({"m_Choices": self.choices_data})
        if self.document_state is None:
            converted_data = self.tree_to_vsmart(self.tree.invisibleRootItem(), {})
        else:
            converted_data = {
                "m_Children": [self._model_node_to_vsmart(node) for node in self.document_state.hierarchy]
            }
        out_data.update(converted_data)
        # Store non-processed reference objects into m_ReferenceObjects.
        if self.ref_objects:
            out_data["m_ReferenceObjects"] = {}
            for ref_uuid, ref_obj_data in self.ref_objects.items():
                out_data["m_ReferenceObjects"][ref_uuid] = ref_obj_data
        return out_data

    def _model_node_to_vsmart(self, node):
        """Prepare a model-owned node for serialization, preserving reference behavior."""
        child_data = dict(node.data)
        s_ref_id = child_data.get("m_sReferenceObjectID")
        n_ref_id = child_data.get("m_nReferenceID")
        if s_ref_id:
            self.ref_objects[s_ref_id] = dict(child_data)
            if isinstance(n_ref_id, int):
                reference = self.document_state.find(n_ref_id)
                if reference is not None:
                    child_data = merge_reference_data(reference.data, child_data)
                    child_data["m_sReferenceObjectID"] = s_ref_id
                    child_data["m_nReferenceID"] = n_ref_id
        if node.children:
            child_data["m_Children"] = [
                self._model_node_to_vsmart(child) for child in node.children
            ]
        return child_data

    def save_file(self):
        """Save the current document through the .NET SmartProp serializer."""
        k3_data = format_smartprop(self.document_data)
        with open(self.filename, "w") as file:
            file.write(k3_data)

    def tree_to_vsmart(self, item, data):
        """Convert tree structure to a JSON-like dict structure and handle reference objects."""
        if "m_Children" not in data:
            data["m_Children"] = []
        for index in range(item.childCount()):
            child = item.child(index)
            key = child.text(0)
            child_data = child.data(0, Qt.UserRole)
            child_data = dict(child_data) if child_data is not None else {}
            child_data["m_sLabel"] = key
            # Process reference objects if present.
            s_ref_id = child_data.get("m_sReferenceObjectID", None)
            n_ref_id = child_data.get("m_nReferenceID", None)
            if s_ref_id:
                self.ref_objects[s_ref_id] = dict(child_data)
                # If a valid reference ID is present, find the referenced element and merge.
                if isinstance(n_ref_id, int):
                    reference_str = self.find_element_by_id(n_ref_id, self.tree.invisibleRootItem())
                    if reference_str is not None:
                        reference_parsed = reference_str
                        if isinstance(reference_parsed, str):
                            reference_parsed = ast.literal_eval(reference_parsed)
                        merged = merge_reference_data(reference_parsed, child_data)
                        merged["m_sReferenceObjectID"] = s_ref_id
                        merged["m_nReferenceID"] = n_ref_id
                        child_data = merged
            if child.childCount() > 0:
                child_data["m_Children"] = []
                self.tree_to_vsmart(child, child_data)
            data["m_Children"].append(child_data)
        return data

    def find_element_by_id(self, element_id, item):
        """Traverse the tree to locate an element with m_nElementID; return its text data if found."""
        for i in range(item.childCount()):
            child = item.child(i)
            val_data = child.data(0, Qt.UserRole)
            if val_data is not None and val_data.get("m_nElementID") == element_id:
                return val_data
            if child.childCount() > 0:
                found = self.find_element_by_id(element_id, child)
                if found:
                    return found
        return None

    def choices(self, parent):
        """The KV3 m_Choices list for the tree under `parent`, with element IDs."""
        m_Choices = format_choices(read_choices_tree(parent.treeWidget()))
        for choice in m_Choices:
            choice["m_nElementID"] = set_element_id(force=True)
            update_child_element_id_value(choice, force=True)
        return m_Choices
