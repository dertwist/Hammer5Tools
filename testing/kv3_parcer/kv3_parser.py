
import sys
import keyvalues3 as kv3

from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget
from PySide6.QtGui import QStandardItemModel, QStandardItem
data = {'m_Variables': [{'_class': 'CSmartPropVariable_Float', 'm_VariableName': 'length', 'm_nElementID': 61}, {'_class': 'CSmartPropVariable_Int', 'm_VariableName': 'height', 'm_nElementID': 62}], 'generic_data_type': 'CSmartPropRoot', '_editor': {'m_nElementID':'1'}}

data_read = kv3.read('sample.vsmart')
data = data_read
print(type(data), data)
# print(type(data['_editor']))
# print(data['generic_data_type'])
#
#
# print(data['m_Variables'])

def child(data, key_child):
    data_out = {}
    if isinstance(data[key_child], dict):
        print('dict', key_child)
        data_out.update({key_child: data[key_child]})
    if isinstance(data[key_child], str):
        print('str', key_child)
        data_out.update({key_child: data[key_child]})
    if isinstance(data[key_child], list):
        def list_child(data, key):
            # print(data)
            # issue with adding output value to the data
            for item in data:
                print('item', item)
                for key_item in item.keys():
                    print('key_item', key_item)
                    if key_item == key:
                        print('Found child')
                        # data_out.update({key_item: data})
                        list_child(item[key], key)


        if key_child == 'm_Children':
            list_child(data[key_child], key_child)
            data_out.update({key_child: data[key_child]})
        else:
            print('list', key_child, data[key_child])
            data_out.update({key_child: data[key_child]})
    else:
        print('Do not match anyone')
    return data_out

data_kv3 = {}
# for parent in data.keys():
#     data_kv3.update(child(data, parent))


print(data_kv3)

# kv3.write(data_kv3, sys.stdout)
# kv3.write(data_kv3, 'output.vsmart')
import json
# file_path = 'output.vsmart'
# with open(file_path, 'w') as file:
#     file.write(str(data))



def add_items(parent, data):
    for key, value in data.items():
        key_item = QStandardItem(key)
        if isinstance(value, dict):
            value_item = QStandardItem("")
            parent.appendRow([key_item, value_item])
            add_items(key_item, value)
        elif isinstance(value, list):
            def list_child(data, key):
                # print(data)
                # issue with adding output value to the data
                for item in data:
                    print('item', item)
                    for key_item in item.keys():
                        print('key_item', key_item)
                        if key_item == key:
                            print('Found child')
                            print(item, key)

                            list_parent = QStandardItem(key)
                            parent.appendRow(list_parent)
                            value_item = QStandardItem(str(key_item))
                            # parent.appendRow(QStandardItem(str(data)))
                            parent.appendRow(value_item)
                            list_child(item[key], key)

            if key == 'm_Children':
                list_child(data[key], key)
            list_parent = QStandardItem(key)
            parent.appendRow(list_parent)
            # for item in value:
            #     item_key = QStandardItem("")
            #     item_value = QStandardItem(str(item))
            #     list_parent.appendRow([item_key, item_value])
            #     print(value)
            #     add_items(item_value, item)  # Pass item instead of value
        else:
            value_item = QStandardItem(str(value))
            parent.appendRow([key_item, value_item])


app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Data Tree View")

# Create the central widget and layout
central_widget = QWidget()
layout = QVBoxLayout(central_widget)

# Create the tree view and model
tree_view = QTreeView()
model = QStandardItemModel()
model.setHorizontalHeaderLabels(["Key", "Value"])
root_item = model.invisibleRootItem()

# Populate the model with data
add_items(root_item, data)

# Set the model to the tree view
tree_view.setModel(model)
tree_view.expandAll()

# Add the tree view to the layout
layout.addWidget(tree_view)
window.setCentralWidget(central_widget)

# Show the window
window.resize(800, 600)
window.show()

sys.exit(app.exec())
