import ast
import re
import uuid
import keyvalues3 as kv3
from PySide6.QtWidgets import QTreeWidget

from src.smartprop_editor.choices import AddChoice, AddOption, AddVariable
from src.common import editor_info, JsonToKv3
from src.settings.main import debug, get_settings_bool
from src.smartprop_editor._common import (
    disable_line_value_length_limit_keys,
    get_clean_class_name,
    get_clean_class_name_value,
    get_label_id_from_value
)
from src.smartprop_editor.element_id import (
    set_ElementID,
    reset_ElementID,
    get_ElementID_last,
    get_ElementID_key,
    update_value_ElementID,
    update_child_ElementID_value
)
from src.widgets import HierarchyItemModel, exception_handler
from src.smartprop_editor.objects import variable_prefix, element_prefix

# =========================================================
# [Reference handling / merging logic]
# =========================================================

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
                            # Remove this element from the reference dictionary
                            del ref_elements_by_id[elem_id]
                        else:
                            # Element only exists in ref object, add it directly
                            merged_list.append(elem)
                    else:
                        # Element doesn't have an ID, add it directly
                        merged_list.append(elem)

                # Add any remaining elements from the reference
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

# ======================================[Tree item serialization and deserialization]========================================

def serialization_hierarchy_items(item, data=None):
    """Convert tree structure to a JSON-like dict structure."""
    if data is None:
        data = {"m_Children": []}

    try:
        value_row = item.text(1)
        parent_data = ast.literal_eval(value_row)
        parent_data["m_sLabel"] = item.text(0)

        # Initialize children array if needed
        if item.childCount() > 0:
            parent_data["m_Children"] = []

        # Add this item to parent's children
        data["m_Children"].append(parent_data)

        # Process children
        if item.childCount() > 0:
            for index in range(item.childCount()):
                child = item.child(index)

                # Create a temporary container for this child
                child_container = {"m_Children": []}

                # Recursively process the child and its descendants
                serialization_hierarchy_items(child, child_container)

                # Add the processed child data to parent's children
                # (The child is now in child_container["m_Children"][0])
                if child_container["m_Children"]:
                    parent_data["m_Children"].append(child_container["m_Children"][0])
    except Exception as e:
        print(f"Error in serialization: {e}")

    return data

def deserialize_hierarchy_item(m_Children):
    """Convert JSON-like hierarchy into tree items recursively."""
    item_value = {}
    for key in m_Children:
        if key != "m_Children":
            item_value.update({key: m_Children[key]})
    item_value = update_child_ElementID_value(item_value, force=True)
    name = item_value.get("m_sLabel", get_clean_class_name_value(item_value))
    tree_item = HierarchyItemModel(
        _data=item_value,
        _name=name,
        _id=get_ElementID_key(item_value),
        _class=get_clean_class_name_value(item_value)
    )
    for child_data in m_Children.get("m_Children", []):
        child_item = deserialize_hierarchy_item(child_data)
        tree_item.addChild(child_item)
    return tree_item

# ======================================[Vsmart File Loading and Saving]========================================

class VsmartOpen:
    def __init__(self, filename, tree=QTreeWidget, choices_tree=QTreeWidget, variables_scrollArea=None):
        self.filename = filename
        self.variables_scrollArea = variables_scrollArea
        self.tree = tree
        self.choices_tree = choices_tree
        self.open_file()

    def load_file(self, filename):
        with open(filename, "r") as file:
            out = file.read()
        return out

    def fix_format(self, file_content):
        """Fix formatting issues from various exports."""
        pattern = re.compile(r"= resource_name:")
        modified_content = re.sub(pattern, "= ", file_content)
        modified_content = modified_content.replace("null,", "")
        return modified_content

    def open_file(self):
        """Open file data, restore references, and populate tree and choices."""
        data = self.load_file(self.filename)
        data = self.fix_format(data)
        data = kv3.textreader.KV3TextReader().parse(data).value
        debug(f"Loaded data:\n{data}")
        # Restore non-processed reference objects.
        restore_reference_objects(data)
        self.variables = data.get("m_Variables", None)
        # Clear previous tree data.
        self.tree.clear()
        self.choices_tree.clear()
        reset_ElementID()
        # Set next element ID if available.
        self.next_element_id = data.get("editor_info", None)
        if self.next_element_id:
            if isinstance(self.next_element_id, dict):
                self.next_element_id = self.next_element_id.get("m_nElementID", None)
                if self.next_element_id:
                    reset_ElementID(self.next_element_id, [self.next_element_id])
                    debug(f"Last ElementID from file: {self.next_element_id}")
        self.populate_tree(data)
        self.populate_choices(data.get("m_Choices", None))

    def populate_tree(self, data, parent=None):
        """Populate the tree hierarchy with element data."""
        if parent is None:
            parent = self.tree.invisibleRootItem()
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "m_Children" and isinstance(value, list):
                    for item in value:
                        item_class = item.get("_class")
                        value_dict = item.copy()
                        value_dict.pop("m_Children", None)
                        if self.next_element_id is None:
                            update_value_ElementID(value_dict)
                            value_dict = update_child_ElementID_value(value_dict)
                        child_item = HierarchyItemModel(
                            _name=value_dict.get("m_sLabel", get_label_id_from_value(value_dict)),
                            _data=str(value_dict),
                            _class=get_clean_class_name(item_class),
                            _id=get_ElementID_key(value_dict)
                        )
                        parent.addChild(child_item)
                        self.populate_tree(item, child_item)

    def populate_choices(self, data):
        """Populate choices based on provided data."""
        if data is None:
            print("No choices")
            return False
        else:
            debug(f"Choices: {data}")
            for choice in data:
                name = choice["m_Name"]
                default = choice.get("m_DefaultOption", None)
                options = choice.get("m_Options", None)
                choice_item = AddChoice(
                    name=name,
                    tree=self.choices_tree,
                    default=default,
                    variables_scrollArea=self.variables_scrollArea
                ).item
                for option in options:
                    option_item = AddOption(parent=choice_item, name=option["m_Name"]).item
                    variables = option["m_VariableValues"]
                    for variable in variables:
                        AddVariable(
                            parent=option_item,
                            variables_scrollArea=self.variables_scrollArea,
                            name=variable["m_TargetName"],
                            type=variable.get("m_DataType", ""),
                            value=variable["m_Value"]
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
    def __init__(self, filename, tree=None, choices_tree=QTreeWidget, variables_layout=None):
        self.filename = filename
        self.tree = tree
        self.variables_layout = variables_layout
        self.choices_tree = choices_tree
        self.ref_objects = {}  # To store non-processed reference objects
        self.var_data = self.save_variables()
        self.choices_data = self.choices(self.choices_tree.invisibleRootItem())
        self.save_file()

    def get_variables(self, layout, only_names=False):
        if layout is None:
            return {}
        if only_names:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    data_out[i] = [widget.name, widget.var_class, widget.var_display_name]
            return data_out
        else:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    data_out[i] = [
                        widget.name,
                        widget.var_class,
                        widget.var_value,
                        widget.var_visible_in_editor,
                        widget.var_display_name
                    ]
            return data_out

    def save_variables(self):
        variables_ = []
        raw_variables = self.get_variables(self.variables_layout)
        for var_key, var_key_value in raw_variables.items():
            var_default = var_key_value[2]["default"]
            if var_default is None:
                var_default = ""
            var_min = var_key_value[2]["min"]
            var_max = var_key_value[2]["max"]
            var_model = var_key_value[2]["model"]
            var_class = var_key_value[1]
            var_id = var_key_value[2]["m_nElementID"]

            var_dict = {
                "_class": variable_prefix + var_class,
                "m_VariableName": var_key_value[0],
                "m_bExposeAsParameter": var_key_value[3],
                "m_DefaultValue": var_default,
                "m_nElementID": var_id
            }
            if var_key_value[4] in (None, ""):
                var_dict.pop("m_ParameterName", None)
            else:
                var_dict.update({"m_ParameterName": var_key_value[4]})
            if var_min is not None:
                if var_class == "Float":
                    var_dict.update({"m_flParamaterMinValue": var_min})
                elif var_class == "Int":
                    var_dict.update({"m_nParamaterMinValue": var_min})
            if var_max is not None:
                if var_class == "Float":
                    var_dict.update({"m_flParamaterMaxValue": var_max})
                elif var_class == "Int":
                    var_dict.update({"m_nParamaterMaxValue": var_max})
            if var_model is not None:
                var_dict.update({"m_sModelName": var_model})
            variables_.append(var_dict)
        return variables_

    @exception_handler
    def save_file(self):
        """Save file while processing references and merging reference objects."""
        out_data = {"generic_data_type": "CSmartPropRoot"}
        editor_info["editor_info"].update({"m_nElementID": get_ElementID_last()})
        out_data.update(editor_info)
        if self.var_data is not None:
            out_data.update({"m_Variables": self.var_data})
        if self.choices_data is not None:
            out_data.update({"m_Choices": self.choices_data})
        converted_data = self.tree_to_vsmart(self.tree.invisibleRootItem(), {})
        out_data.update(converted_data)
        # Store non-processed reference objects into m_ReferenceObjects.
        if self.ref_objects:
            out_data["m_ReferenceObjects"] = {}
            for ref_uuid, ref_obj_data in self.ref_objects.items():
                out_data["m_ReferenceObjects"][ref_uuid] = ref_obj_data
        if get_settings_bool("SmartPropEditor", "export_properties_in_one_line", True):
            k3_data = JsonToKv3(out_data, disable_line_value_length_limit_keys=disable_line_value_length_limit_keys)
        else:
            k3_data = JsonToKv3(out_data)
        with open(self.filename, "w") as file:
            file.write(k3_data)

    def tree_to_vsmart(self, item, data):
        """Convert tree structure to a JSON-like dict structure and handle reference objects."""
        if "m_Children" not in data:
            data["m_Children"] = []
        for index in range(item.childCount()):
            child = item.child(index)
            key = child.text(0)
            value_row = child.text(1)
            child_data = ast.literal_eval(value_row)
            child_data["m_sLabel"] = key
            # Process reference objects if present.
            s_ref_id = child_data.get("m_sReferenceObjectID", None)
            n_ref_id = child_data.get("m_nReferenceID", None)
            if s_ref_id:
                # Store the non-processed version.
                self.ref_objects[s_ref_id] = dict(child_data)
                # If a valid reference ID is present, find the referenced element and merge.
                if isinstance(n_ref_id, int):
                    reference_str = self.find_element_by_id(n_ref_id, self.tree.invisibleRootItem())
                    if reference_str is not None:
                        reference_parsed = ast.literal_eval(reference_str)
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
            val_str = child.text(1)
            parsed_data = ast.literal_eval(val_str)
            if parsed_data.get("m_nElementID") == element_id:
                return val_str
            if child.childCount() > 0:
                found = self.find_element_by_id(element_id, child)
                if found:
                    return found
        return None

    def choices(self, parent):
        m_Choices = []
        for choice_index in range(parent.childCount()):
            child = parent.child(choice_index)
            widget = parent.treeWidget().itemWidget(child, 1)
            options = []
            for option_index in range(child.childCount()):
                option_child = child.child(option_index)
                variables = []
                for variable_index in range(option_child.childCount()):
                    variable_child = option_child.child(variable_index)
                    variable_widget = parent.treeWidget().itemWidget(variable_child, 1)
                    variable_combobox = parent.treeWidget().itemWidget(variable_child, 0)
                    if variable_widget is None:
                        variables.append({})
                    else:
                        out = {"m_TargetName": variable_combobox.combobox.currentText()}
                        out.update(variable_widget.data)
                        variables.append(out)
                options.append({"m_Name": option_child.text(0), "m_VariableValues": variables})
            choice = {
                "_class": "CSmartPropChoice",
                "m_Name": child.text(0),
                "m_Options": options,
                "m_DefaultOption": widget.currentText() if widget else None,
                "m_nElementID": set_ElementID(force=True)
            }
            update_child_ElementID_value(choice, force=True)
            m_Choices.append(choice)
        return m_Choices