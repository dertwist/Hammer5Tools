import sys
from time import process_time_ns

from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMainWindow, QMenu,
    QInputDialog, QMessageBox, QToolBar, QPushButton, QFileDialog, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QObject
import re
import keyvalues3 as kv3
import ast
from smartprop_editor.objects import element_prefix
from smartprop_editor.choices import AddChoice
from preferences import debug
from common import editor_info
class VsmartOpen:
    def __init__(self, filename, tree=None, choices_tree=None):
        self.filename = filename
        self.tree = tree
        self.choices_tree = choices_tree
        self.open_file()

    def load_file(self, filename):
        with open(filename, 'r') as file:
            out = file.read()
        return out
    def fix_format(self, file_content):
            pattern = re.compile(r'= resource_name:')
            modified_content = re.sub(pattern, '= ', file_content)
            modified_content = modified_content.replace('null,', '')
            return modified_content
    def open_file(self):
        data = self.load_file(self.filename)
        data = self.fix_format(data)
        data = kv3.textreader.KV3TextReader().parse(data).value
        debug(f'Loaded data \n {data}')

        self.variables = data.get('m_Variables', None)
        self.tree.clear()
        self.choices_tree.clear()
        self.populate_tree(data)
        self.populate_choices(data.get('m_Choices', None))
        self.cleanup_tree(parent_item=self.tree.invisibleRootItem())
        self.fix_names(parent=self.tree.invisibleRootItem())



    def populate_tree(self, data, parent=None):
        if parent is None:
            parent = self.tree.invisibleRootItem()
            # parent_element = QTreeWidgetItem(['Root'])
            # parent.addChild(parent_element)
            # parent = parent_element
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'm_Children':
                    # print(type(key), key)
                    if isinstance(value, dict):
                        item = QTreeWidgetItem([key])
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                        parent.addChild(item)
                        # for child_data in value:
                        #     self.populate_tree(child_data, item)
                        self.populate_tree(value, item)
                    elif isinstance(value, list):
                        # trying to parse class elements
                        # if key == 'm_SelectionCriteria':
                        #     print(type(key), key)
                        try:
                            item_class = value[0].get('_class')
                            child = QTreeWidgetItem([key])
                            child.setFlags(child.flags() | Qt.ItemIsEditable)
                            parent.addChild(child)
                            for item in value:

                                if key == 'm_Children':
                                    item_class = item.get('_class')
                                    value_dict = item.copy()
                                    try:
                                        del value_dict['m_Children']
                                        pass
                                    except:
                                        pass
                                    child_item = QTreeWidgetItem([item_class,str(value_dict)])
                                    child_item.setFlags(child_item.flags() | Qt.ItemIsEditable)
                                    child.addChild(child_item)
                                    self.populate_tree(item, child_item)
                                # elif key == 'm_vEnd':
                                #     print('m_vEnd')
                        except Exception as error:
                            print(error)
                            pass
                            # if didn't find any class element just set value to key row
                            print(key, value)
                    elif isinstance(value, (str, float, int)):
                        pass

    # Remove m_children items
    def cleanup_tree(self, parent_item):
        def search_recursively_loop(parent_item):
            for index in range(parent_item.childCount()):
                item = parent_item.child(index)
                if item.text(0) == 'm_Children':
                    # move all child from m_children to parent
                    child_item = parent_item.child(index)
                    search_recursively_loop(child_item)
                    for i in range(child_item.childCount()):
                        child = child_item.child(i)
                        parent_item.addChild(child.clone())
                    parent_item.takeChild(index)
                    # check items in parent element
                    for i in range(parent_item.childCount()):
                        child = child_item.child(i)
                        if child:
                            # print(child.text(0))
                            pass

                    self.cleanup_tree(parent_item)
                else:
                    search_recursively_loop(item)

        search_recursively_loop(parent_item)

    def populate_choices(self, data):
        if data == None:
            print('No choices')
            return False
        else:
            debug(f'Choices {data}')

    def fix_names(self, parent):
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
    def __init__(self, filename, tree=None, var_data=None, choices_data=None):
        self.filename = filename
        self.tree = tree
        self.var_data = var_data
        self.choices_data = choices_data
        self.save_file()

        print(f'Saved File: {filename}')

    def save_file(self):
        # data = self.convert_children_to_list(data)
        out_data = {'generic_data_type': "CSmartPropRoot"}
        out_data.update(editor_info)
        if self.var_data is not None:
            out_data.update({'m_Variables': self.var_data})
        if self.choices_data is not None:
            out_data.update({'m_Choices': self.choices_data})
        converted_data = self.tree_to_vsmart((self.tree.invisibleRootItem()), {})
        out_data.update(converted_data)
        kv3.write(out_data, self.filename)

    def tree_to_vsmart(self, item, data):
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
