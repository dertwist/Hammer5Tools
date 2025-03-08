from PySide6.QtWidgets import (
    QTreeWidget
)
import re
import keyvalues3 as kv3
from src.smartprop_editor.choices import AddChoice, AddOption, AddVariable
from src.common import editor_info, JsonToKv3
from src.smartprop_editor._common import disable_line_value_length_limit_keys
from src.smartprop_editor.element_id import *
from src.smartprop_editor._common import *
from src.settings.main import get_settings_bool
from src.widgets import HierarchyItemModel, exception_handler
from src.smartprop_editor.objects import variable_prefix


# ======================================[Tree item serialization and deserialization]========================================
def serialization_hierarchy_items(item, data=None):
    """Convert tree structure to json."""
    if data is None:
        data = {"m_Children": []}
    value_row = item.text(1)
    parent_data = ast.literal_eval(value_row)
    parent_data["m_sLabel"] = item.text(0)
    if item.childCount() > 0:
        parent_data["m_Children"] = []

    data["m_Children"].append(parent_data)

    if item.childCount() > 0:
        for index in range(item.childCount()):
            child = item.child(index)
            key = child.text(0)
            value_row = child.text(1)
            child_data = ast.literal_eval(value_row)
            child_data["m_sLabel"] = key
            if child.childCount() > 0:
                child_data["m_Children"] = []
                serialization_hierarchy_items(child, child_data)
            parent_data["m_Children"].append(child_data)

    return data


def deserialize_hierarchy_item(m_Children):
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


class VsmartOpen:
    def __init__(self, filename, tree=QTreeWidget, choices_tree=QTreeWidget, variables_scrollArea=None):
        self.filename = filename
        self.variables_scrollArea = variables_scrollArea
        self.tree = tree
        self.choices_tree = choices_tree
        self.open_file()

    def load_file(self, filename):
        with open(filename, 'r') as file:
            out = file.read()
        return out
    def fix_format(self, file_content):
            """Fixing format from Source2Viewr and from null elements, usually it happens in case of Hammer5Tools export, but in valve's smartprops it also could be."""
            pattern = re.compile(r'= resource_name:')
            modified_content = re.sub(pattern, '= ', file_content)
            modified_content = modified_content.replace('null,', '')
            return modified_content
    def open_file(self):
        """Open file data"""
        data = self.load_file(self.filename)
        data = self.fix_format(data)
        data = kv3.textreader.KV3TextReader().parse(data).value

        debug(f'Loaded data \n {data}')

        self.variables = data.get('m_Variables', None)
        #=======================================================<  Clear previous data  >====================================================
        self.tree.clear()
        self.choices_tree.clear()
        reset_ElementID()
        #=========================================================<  Load new data  >======================================================
        self.next_element_id = data.get('editor_info', None)
        if self.next_element_id:
            if isinstance(self.next_element_id, dict):
                self.next_element_id = self.next_element_id.get('m_nElementID', None)
                if self.next_element_id:
                    reset_ElementID(self.next_element_id, [self.next_element_id])
                    debug(f'Last ElementID from file {self.next_element_id}')
        self.populate_tree(data)
        self.populate_choices(data.get('m_Choices', None))
        # self.cleanup_tree(parent_item=self.tree.invisibleRootItem())
        # self.fix_names(parent=self.tree.invisibleRootItem())

    def populate_tree(self, data, parent=None):
        """Populating hierarchy"""
        if parent is None:
            parent = self.tree.invisibleRootItem()
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'm_Children':
                    if isinstance(value, list):
                        for item in value:
                            # Get keys
                            item_class = item.get('_class')
                            value_dict = item.copy()

                            # Delete m_Children key
                            value_dict.pop('m_Children', None)

                            # Assign or get element id
                            if self.next_element_id is None:
                                update_value_ElementID(value_dict)
                                value_dict = update_child_ElementID_value(value_dict)


                            # Add tree item
                            child_item = HierarchyItemModel(_name=value_dict.get('m_sLabel', get_label_id_from_value(value_dict)), _data = str(value_dict), _class=get_clean_class_name(item_class), _id= get_ElementID_key(value_dict))

                            parent.addChild(child_item)
                            self.populate_tree(item, child_item)

    def populate_choices(self, data):
        if data == None:
            print('No choices')
            return False
        else:
            debug(f'Choices {data}')
            for choice in data:
                name = choice['m_Name']
                default = choice.get('m_DefaultOption', None)
                options = choice.get('m_Options', None)
                choice = AddChoice(name=name, tree=self.choices_tree, default=default,variables_scrollArea=self.variables_scrollArea).item
                for option in options:
                    option_item = AddOption(parent=choice, name=option['m_Name']).item
                    variables = option['m_VariableValues']
                    for variable in variables:
                        AddVariable(parent=option_item, variables_scrollArea=self.variables_scrollArea, name=variable['m_TargetName'], type=variable.get('m_DataType', ''), value=variable['m_Value'])



    def fix_names(self, parent):
        """Replace m_child name to class name with m_label, if didn't find m_label set class name with digits suffix"""
        counter = 1

        # Iterate through each child item under the parent
        for index in range(parent.childCount()):
            child_item = parent.child(index)

            # Check if the current name has 'element_prefix'
            if element_prefix in child_item.text(0):
                # Remove 'element_prefix' from the item's name
                element_value = ast.literal_eval(child_item.text(1))
                current_name = child_item.text(0)
                new_name = current_name.replace(element_prefix, '')

                # Set unique naming using 2 digits
                new_name = f"{new_name}_{counter:02d}"
                counter += 1

                child_item.setText(0, new_name)
                if 'm_sLabel' in element_value:
                    label = element_value['m_sLabel']
                    if label != '':
                        child_item.setText(0, label)

                # Recursively fix names for child elements
                self.fix_names(child_item)
            else:
                # If the current name does not have 'element_prefix', pass
                pass


class VsmartSave:
    def __init__(self, filename, tree=None, choices_tree=QTreeWidget, variables_layout=None):
        self.filename = filename
        self.tree = tree
        self.variables_layout = variables_layout
        self.var_data = self.save_variables()
        self.choices_tree = choices_tree
        self.choices_data = self.choices(self.choices_tree.invisibleRootItem())
        self.save_file()
    def get_variables(self, layout, only_names=False):
        if only_names:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    item_ = {i: [widget.name, widget.var_class, widget.var_display_name]}
                    data_out.update(item_)
            return data_out
        else:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    item_ = {
                        i: [
                            widget.name,
                            widget.var_class,
                            widget.var_value,
                            widget.var_visible_in_editor,
                            widget.var_display_name
                        ]
                    }
                    data_out.update(item_)
            return data_out

    def save_variables(self):
        variables_ = []
        raw_variables = self.get_variables(self.variables_layout)
        for var_key, var_key_value in raw_variables.items():
            var_default = (var_key_value[2])["default"]
            if var_default is None:
                var_default = ""
            var_min = (var_key_value[2])["min"]
            var_max = (var_key_value[2])["max"]
            var_model = (var_key_value[2])["model"]
            var_class = var_key_value[1]
            var_id = (var_key_value[2])["m_nElementID"]

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
        """Saving file"""
        out_data = {'generic_data_type': "CSmartPropRoot"}
        editor_info['editor_info'].update({'m_nElementID': get_ElementID_last()})
        out_data.update(editor_info)
        if self.var_data is not None:
            out_data.update({'m_Variables': self.var_data})
        if self.choices_data is not None:
            out_data.update({'m_Choices': self.choices_data})
        converted_data = self.tree_to_vsmart((self.tree.invisibleRootItem()), {})
        out_data.update(converted_data)
        if get_settings_bool('SmartPropEditor', 'export_properties_in_one_line', True):
            k3_data = JsonToKv3(out_data, disable_line_value_length_limit_keys=disable_line_value_length_limit_keys)
        else:
            k3_data = JsonToKv3(out_data)
        with open(self.filename, 'w') as file:
            file.write(k3_data)

    def tree_to_vsmart(self, item, data):
        """Convert tree structure to json"""
        if 'm_Children' not in data:
            data['m_Children'] = []

        for index in range(item.childCount()):
            child = item.child(index)
            key = child.text(0)
            value_row = child.text(1)

            child_data = ast.literal_eval(value_row)
            child_data['m_sLabel'] = key
            if child.childCount() > 0:
                child_data['m_Children'] = []
                self.tree_to_vsmart(child, child_data)

            data['m_Children'].append(child_data)

        return data

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
                        out = {'m_TargetName': variable_combobox.combobox.currentText()}
                        out.update(variable_widget.data)
                        variables.append(out)
                options.append({'m_Name': option_child.text(0), 'm_VariableValues': variables})
            choice = {
                '_class': 'CSmartPropChoice',
                'm_Name': child.text(0),
                'm_Options': options,
                'm_DefaultOption': widget.currentText(),
                'm_nElementID': set_ElementID(force=True)
            }
            update_child_ElementID_value(choice, force=True)
            m_Choices.append(choice)
        return m_Choices