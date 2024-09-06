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

vsmart_path = 'bicycle_rack.vsmart'


pattern = re.compile(r'= resource_name:')
with open(vsmart_path, 'r') as file:
    file_content = file.read()

modified_content = re.sub(pattern, '= ', file_content)
with open(vsmart_path, 'w') as file:
    file.write(modified_content)


bt_config = kv3.read(vsmart_path)
data = bt_config.value



data = {
    'generic_data_type': 'CSmartPropRoot',
    'm_Variables': [{'_class': 'CSmartPropVariable_Float', 'm_VariableName': 'length', 'm_nElementID': 61, 'm_nElementID1': 61.2}],
    'm_Children': [{'_class': 'CSmartPropElement_Mode55555l',
                    'm_sModelName': 'models/props/de_nuke/hr_nuke/airduct_hvac_001/airduct_hvac_001_endcap.vmdl',
                    'm_nElementID': 2},{'_class': 'CSmartPropElement_Model',
                    'm_sModelName': 'models/props/de_nuke/hr_nuke/airduct_hvac_001/airduct_hvac_001_endcap.vmdl',
                    'm_nElementID': 2}]
}

data_raw = data
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartProp Editor v1")
        self.setGeometry(500, 500, 900, 500)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Key", "Value"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.setCentralWidget(self.tree)
        self.populate_tree(data)


        header = self.tree.header()
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.resizeSection(0, 500)
        toolbar = QToolBar()
        self.addToolBar(toolbar)


        load_file_button = QPushButton("Load file")
        load_file_button.clicked.connect(self.load_file)
        toolbar.addWidget(load_file_button)


        export_button = QPushButton("Export to Path")
        export_button.clicked.connect(self.export_to_file)
        toolbar.addWidget(export_button)


        quick_export_button = QPushButton("Quick Export")
        quick_export_button.clicked.connect(self.quick_export_to_file)
        toolbar.addWidget(quick_export_button)

        remove_child_button = QPushButton("Remove children")
        remove_child_button.clicked.connect(self.remove_child)
        toolbar.addWidget(remove_child_button)

        save_tree_button = QPushButton("Save tree structure as h5t format")
        save_tree_button.clicked.connect(self.save_tree)
        toolbar.addWidget(save_tree_button)

        load_tree_button = QPushButton("Load h5t format")
        load_tree_button.clicked.connect(self.load_tree)
        toolbar.addWidget(load_tree_button)


        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)


    def load_tree(self):
        with open('treestructure.vsmart', 'r') as file:
            lines = file.readlines()
            lines_count = len(lines)

            line_vsmartdata_tree_structure = (lines[lines_count - 1].strip().split('//Hammer5Tools_vsmartdata_tree_structure:'))[1]
            line_vsmartdata_options = (lines[lines_count - 2].strip().split('//Hammer5Tools_vsmartdata_options:'))[1]
            line_vsmartdata_variables = (lines[lines_count - 3].strip().split('//Hammer5Tools_vsmartdata_variables:'))[1]
            print(line_vsmartdata_tree_structure)
            print(line_vsmartdata_options)
            print(line_vsmartdata_variables)

            self.tree.clear()
            vsmartdata_tree_structure = ast.literal_eval(line_vsmartdata_tree_structure)
            self.load_json_tree(vsmartdata_tree_structure)

    def load_json_tree(self, data, parent=None):
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
                self.load_json_tree(value, item)


    def save_tree(self):
        data = self.tree_item_to_dict(self.tree.invisibleRootItem())
        # data = self.convert_children_to_list(data)
        # converted_data = self.convert_to_kv3(data)
        kv3.write(data, 'treestructure.vsmart')
        # kv3.write(converted_data, 'treestructure.vsmart')
        # print(data_raw)

        # kv3.write(data_raw, 'treestructure.vsmart')
        with open('treestructure.vsmart', 'a') as file:
            file.write('//Hammer5Tools_vsmartdata_variables:' + '\n')
            file.write('//Hammer5Tools_vsmartdata_options:' + '\n')
            file.write('//Hammer5Tools_vsmartdata_tree_structure:' + str(data))

    def convert_to_kv3(self, data):
        new_data = {}
        for item, value in data.items():
            if isinstance(value, dict):
                new_data[item] = self.convert_to_kv3(value)  # Update new_data with converted dict
            elif isinstance(value, str):
                print('str', value)
                new_data[item] = ast.literal_eval(value)  # Convert string values to dictionary
                print(type(ast.literal_eval(value)))
            elif isinstance(value, list):
                new_list = []
                for val in value:
                    new_list.append(self.convert_to_kv3(val))  # Recursively convert list elements
                new_data[item] = new_list  # Update new_data with converted list
            else:
                new_data[item] = value  # For other types, keep the value as is
        return new_data

    def tree_item_to_dict(self, item):
        data = {}
        for index in range(item.childCount()):
            child = item.child(index)
            child_data = self.tree_item_to_dict(child)  # Recursively get child data
            key = child.text(0)
            value = child.text(1) if child.childCount() == 0 else self.tree_item_to_dict(child)
            value_row = child.text(1)
            if key in data:
                if not isinstance(data[key], list):
                    data[str(key) + '%?=!=' + str(value_row)] = value = [data[key]]
                data[str(key) + '%?=!=' + str(value_row)] = value.append(value)
            else:
                data[str(key) + '%?=!=' + str(value_row)] = value

        return data



    def load_file(self):
        options = QFileDialog.Options()
        file_url, _ = QFileDialog.getOpenFileUrl(self, "Save VSmart File", "", "VSmart Files (*.vsmart);;All Files (*)", options=options)
        if file_url:
            file_path = file_url.toLocalFile()
            self.tree.clear()
            data = (kv3.read(file_path)).value
            def search(data):
                if isinstance(data, dict):
                    for item in data.items():
                        print(item)
                        if item.items():
                            search(item)
                elif isinstance(data, list):
                    for item in data:

                        print(item)
                        if item.items():
                            search(item)
            self.populate_tree(data)

    def dropEvent(self, event):
        item = self.tree.currentItem()
        if not item:
            return

        parent = item.parent() or self.tree.invisibleRootItem()
        dropped_item = event.source().currentItem()
        if not dropped_item:
            return

        new_item = QTreeWidgetItem(dropped_item.text(0))
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)

        index = self.tree.indexOfTopLevelItem(item)
        if index >= 0:
            parent.insertChild(index, new_item)
        else:
            parent.addChild(new_item)

        event.accept()

    def populate_tree(self, data, parent=None):
        if parent is None:
            print('None')
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
                if key == 'm_Variables':
                    item_class = value[0].get('_class')
                    child = QTreeWidgetItem([key])
                    child.setFlags(child.flags() | Qt.ItemIsEditable)
                    parent.addChild(child)
                    for item in value:
                        item_class = item.get('_class')
                        value_dict = item.copy()
                        try:
                            del value_dict['m_Children']
                            pass
                        except:
                            pass
                        child_item = QTreeWidgetItem([item_class, str(value_dict)])
                        child_item.setFlags(child_item.flags() | Qt.ItemIsEditable)
                        child.addChild(child_item)
                        self.populate_tree(item, child_item)
                        # elif key == 'm_vEnd':
                        #     print('m_vEnd')


    def search_recursively(self, parent_item):
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
                            print(child.text(0))

                    self.search_recursively(parent_item)
                else:
                    search_recursively_loop(item)

        search_recursively_loop(parent_item)


    def remove_child(self):
        root_item = self.tree.invisibleRootItem()
        self.search_recursively(root_item)

    def on_item_changed(self, item, column):
        # Handle item changes if necessary
        pass

    def open_menu(self, position):
        menu = QMenu()
        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")
        add_action = menu.addAction("Add")
        edit_action = menu.addAction("Edit")
        remove_action = menu.addAction("Remove")

        move_up_action.triggered.connect(lambda: self.move_item(self.tree.itemAt(position), -1))
        move_down_action.triggered.connect(lambda: self.move_item(self.tree.itemAt(position), 1))
        add_action.triggered.connect(lambda: self.add_item(self.tree.itemAt(position)))
        edit_action.triggered.connect(lambda: self.edit_item(self.tree.itemAt(position)))
        remove_action.triggered.connect(lambda: self.remove_item(self.tree.itemAt(position)))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def move_item(self, item, direction):
        if not item:
            return
        parent = item.parent() or self.tree.invisibleRootItem()
        index = parent.indexOfChild(item)
        new_index = index + direction

        if 0 <= new_index < parent.childCount():
            parent.takeChild(index)
            parent.insertChild(new_index, item)

    def add_item(self, item):
        key, ok = QInputDialog.getText(self, "Add Item", "Enter key:")
        if ok and key:
            new_item = QTreeWidgetItem([key])
            new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)
            if item:
                item.addChild(new_item)
            else:
                self.tree.addTopLevelItem(new_item)

    def edit_item(self, item):
        if item:
            self.tree.editItem(item, 0)

    def remove_item(self, item):
        if item:
            parent = item.parent() or self.tree.invisibleRootItem()
            index = parent.indexOfChild(item)
            parent.takeChild(index)

    def convert_children_to_list(self, data):
        if isinstance(data, dict):
            # Check if 'm_Children' key exists and is a dictionary
            if 'm_Children' in data and isinstance(data['m_Children'], dict):
                data['m_Children'] = [data['m_Children']]  # Convert to list

            # Recursively convert m_Children in nested dictionaries
            for key, value in data.items():
                data[key] = self.convert_children_to_list(value)

        elif isinstance(data, list):
            # Recursively convert m_Children in nested lists
            for i in range(len(data)):
                data[i] = self.convert_children_to_list(data[i])

        return data

    # Convert m_Children to list format



    def export_to_vsmart(self, path):
        root = self.tree.invisibleRootItem()
        data = self.tree_item_to_dict(root)
        data = self.convert_children_to_list(data)
        kv3.write(data, path)

    def export_to_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save VSmart File", "", "VSmart Files (*.vsmart);;All Files (*)",
                                                   options=options)
        if file_path:
            self.export_to_vsmart(file_path)
            # QMessageBox.information(self, "Export", "Data exported successfully!")

    def quick_export_to_file(self):
        self.export_to_vsmart('exported_data.vsmart')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
