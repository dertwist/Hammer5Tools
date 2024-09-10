import sys
from time import process_time_ns

from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMainWindow, QMenu,
    QInputDialog, QMessageBox, QToolBar, QPushButton, QFileDialog, QHeaderView
)
from PySide6.QtCore import Qt
import json
import re
import keyvalues3 as kv3
import ast
from smartprop_editor.objects import element_prefix
from preferences import get_cs2_path, get_addon_name, get_config_value
import subprocess
import shutil
import os
class VsmartOpen:
    def __init__(self, filename, tree=None):
        self.filename = filename
        self.tree = tree
        self.open_file()

    def open_file(self):
        if self.check_for_tree():
            print('Hammer5tools vsmart')
            self.tree.clear()
            self.load_state()
        else:
            print("Raw vsmart")
            self.fix_format()
            data = (kv3.read(self.filename)).value
            self.variables = data.get('m_Variables', None)
            self.tree.clear()
            self.populate_tree(data)
            self.cleanup_tree(parent_item=self.tree.invisibleRootItem())
            self.fix_names(parent=self.tree.invisibleRootItem())

    def fix_format(self):
        try:
            pattern = re.compile(r'= resource_name:')
            with open(self.filename, 'r') as file:
                file_content = file.read()

            modified_content = re.sub(pattern, '= ', file_content)
            with open(self.filename, 'w') as file:
                file.write(modified_content)
        except Exception as error:
            print(error)

    def check_for_tree(self):
        with open(self.filename, 'r') as file:
            lines = file.readlines()
            lines_count = len(lines)
            print(lines_count)
            line_vsmartdata_options = (lines[lines_count - 1].strip().split('//Hammer5Tools_vsmartdata_metadata:'))[1]
            print(line_vsmartdata_options)
            return True
        # try:
        #     with open(self.filename, 'r') as file:
        #         lines = file.readlines()
        #         lines_count = len(lines)
        #         line_vsmartdata_options = (lines[lines_count - 1].strip().split('//Hammer5Tools_vsmartdata_metadata:'))[1]
        #         print(line_vsmartdata_options)
        #         return True
        # except:
        #     return False


    def load_state(self):
        with open(self.filename, 'r') as file:
            lines = file.readlines()
            lines_count = len(lines)
            line_vsmartdata_options = (lines[lines_count - 1].strip().split('//Hammer5Tools_vsmartdata_metadata:'))[1]
            line_vsmartdata_tree_structure = (lines[lines_count - 2].strip().split('//Hammer5Tools_vsmartdata_tree_structure:'))[1]
            line_vsmartdata_variables = (lines[lines_count - 3].strip().split('//Hammer5Tools_vsmartdata_variables:'))[1]
            print(f'Loaded h5t structure from vsmart: {self.filename}')
            vsmartdata_tree_structure = ast.literal_eval(line_vsmartdata_tree_structure)
            self.variables = ast.literal_eval(line_vsmartdata_variables)
            self.load_tree_from_file(vsmartdata_tree_structure)
    def load_tree_from_file(self, data, parent=None):
        if parent is None:
            parent = self.tree.invisibleRootItem()

        for key, value in data.items():
            key_split = key.split('%?=!=')
            key_name = key_split[0]

            # Check if key_split has at least two elements before accessing the second element
            if len(key_split) > 1:
                value_row = key_split[1]
            else:
                value_row = ''  # Handle the case when key_split does not have a second element

            item = QTreeWidgetItem([key_name, value_row])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            parent.addChild(item)

            if isinstance(value, dict):
                self.load_tree_from_file(value, item)



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
                            # child = QTreeWidgetItem([key, str(value)])
                            # child.setFlags(child.flags() | Qt.ItemIsEditable)
                            # parent.addChild(child)
                    elif isinstance(value, (str, float, int)):
                        # item = QTreeWidgetItem([key, str(value)])
                        # item.setFlags(item.flags() | Qt.ItemIsEditable)
                        # parent.addChild(item)
                        # self.populate_tree(value, item)
                        pass
                # if key == 'm_Variables':
                #     item_class = value[0].get('_class')
                #     child = QTreeWidgetItem([key])
                #     child.setFlags(child.flags() | Qt.ItemIsEditable)
                #     parent.addChild(child)
                #     for item in value:
                #         item_class = item.get('_class')
                #         value_dict = item.copy()
                #         try:
                #             del value_dict['m_Children']
                #             pass
                #         except:
                #             pass
                #         child_item = QTreeWidgetItem([item_class, str(value_dict)])
                #         child_item.setFlags(child_item.flags() | Qt.ItemIsEditable)
                #         child.addChild(child_item)
                #         self.populate_tree(item, child_item)
                        # elif key == 'm_vEnd':
                        #     print('m_vEnd')

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

    def fix_names(self, parent):
        counter = 1

        # Iterate through each child item under the parent
        for index in range(parent.childCount()):
            child_item = parent.child(index)

            # Check if the current name has 'element_prefix'
            if element_prefix in child_item.text(0):
                # Remove 'element_prefix' from the item's name
                current_name = child_item.text(0)
                new_name = current_name.replace(element_prefix, '')

                # Set unique naming using 2 digits
                new_name = f"{new_name}_{counter:02d}"
                counter += 1

                child_item.setText(0, new_name)

                # Recursively fix names for child elements
                self.fix_names(child_item)
            else:
                # If the current name does not have 'element_prefix', pass
                pass

class VsmartSave:
    def __init__(self, filename, tree=None, var_data=None):
        self.filename = filename
        self.tree = tree
        self.var_data = var_data
        self.save_file()
        print(f'Saved File: {filename}')

    def save_file(self):
        data = self.tree_to_file(self.tree.invisibleRootItem())
        # data = self.convert_children_to_list(data)
        out_data = {'generic_data_type': "CSmartPropRoot"}

        if self.var_data is not None:
            out_data.update({'m_Variables': self.var_data})
        converted_data = self.tree_to_vsmart((self.tree.invisibleRootItem()), {})
        out_data.update(converted_data)
        kv3.write(out_data, self.filename)
        # print(data_raw)
        with open(self.filename, 'a') as file:
            file.write('//Hammer5Tools_vsmartdata_variables:' + str(self.var_data) + '\n')
            file.write('//Hammer5Tools_vsmartdata_tree_structure:' + str(data) + '\n')
            file.write('//Hammer5Tools_vsmartdata_metadata:' + '\n')

    def tree_to_vsmart(self, item, data):
        if 'm_Children' not in data:
            data['m_Children'] = []

        for index in range(item.childCount()):
            child = item.child(index)
            key = child.text(0)
            value_row = child.text(1)

            child_data = ast.literal_eval(value_row)
            if child.childCount() > 0:
                child_data['m_Children'] = []
                self.tree_to_vsmart(child, child_data)

            data['m_Children'].append(child_data)

        return data

    def tree_to_file(self, item):
        data = {}
        for index in range(item.childCount()):
            child = item.child(index)
            key = child.text(0)
            value = child.text(1)if child.childCount() == 0 else self.tree_to_file(child)
            value_row = child.text(1)
            if child.childCount() == 0:
                data[str(key) + '%?=!=' + str(value_row)] = None
            else:
                data[str(key) + '%?=!=' + str(value_row)] = value
        return data

class VsmartCompile:
    def __init__(self, filename):
        self.filename = filename
        self.compile_vsmart()
    def compile_vsmart(self):
        extension = get_config_value('SmartpropEditor', 'Extension')
        source_file = self.filename
        rel_source_file = os.path.relpath(self.filename, (os.path.join(get_cs2_path(), 'content')))
        print(f'Compiling: {rel_source_file}')
        destination_name = os.path.splitext(source_file)[0] + ".vdata"
        if extension == 'vdata':
            pass
        else:
            shutil.copy(source_file, destination_name)


        subprocess_result = subprocess.run(
            '"' + get_cs2_path() + r"\game\bin\win64\resourcecompiler.exe" + '"' + " -i " + '"' + str(
                destination_name) + '"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Print the stdout and stderr to the console
        if subprocess_result.stdout:
            print("Subprocess stdout:")
            print(subprocess_result.stdout.decode('utf-8'))  # Decode the byte output to string and print
        if subprocess_result.stderr:
            print("Subprocess stderr:")
            print(subprocess_result.stderr.decode('utf-8'))
        if extension == 'vdata':
            pass
        else:
            os.remove(destination_name)

        source_name = os.path.join(get_cs2_path(), 'game', os.path.splitext(rel_source_file)[0] + '.vdata_c')
        destination_name = source_name.replace('.vdata_c', '.vsmart_c')
        print(source_name)
        print(destination_name)
        try:
            shutil.move(source_name, destination_name)
        except:
            print(f'ERROR WHILE COMPILING: {os.path.basename(self.filename)}')
        print(f'Compiled: {os.path.basename(self.filename)}')