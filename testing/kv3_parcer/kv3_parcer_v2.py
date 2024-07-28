import keyvalues3 as kv3
import sys
import ast


import sys
import keyvalues3 as kv3
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget
from PySide6.QtGui import QStandardItemModel, QStandardItem

data = {'ambient_example.indoors.rockfalls': {'base': 'amb.intermittent.randomAroundPlayer.base', 'volume': 0.7, 'randomize_position_min_radius': 500.0, 'randomize_position_max_radius': 1000.0, 'randomize_position_hemisphere': False, 'retrigger_interval_min': 5.0, 'retrigger_interval_max': 15.0, 'retrigger_radius': 1000.0, 'vsnd_files_track_01': ['sounds/ambient/dust2/rockfall_01.vsnd', 'sounds/ambient/dust2/rockfall_02.vsnd', 'sounds/ambient/dust2/rockfall_03.vsnd', 'sounds/ambient/dust2/rockfall_04.vsnd', 'sounds/ambient/dust2/rockfall_05.vsnd', 'sounds/ambient/dust2/rockfall_06.vsnd', 'sounds/ambient/dust2/rockfall_07.vsnd', 'sounds/ambient/dust2/rockfall_08.vsnd']}, 'ambient_example.indoors.vent': {'base': 'amb.looping.atXYZ.base', 'volume': 0.2, 'position': [1136.0, 1392.0, 64.0], 'vsnd_files_track_01': 'sounds/vent_01.vsnd', 'distance_volume_mapping_curve': [[0.0, 1.0, 0.0, 0.0, 2.0, 3.0], [500.0, 1.0, 0.0, 0.0, 2.0, 3.0]]}}

data_read = kv3.read('see_test.txt')
data_read = kv3.read('see_test1.txt')
# data_read = kv3.read('soundevents_addon.vsndevts')
# data_read = kv3.read('hvac_kit.txt')
data.keys()
data = data_read
# data = data_read.keys()
# print(data)





def child_merge(block_1, block_2):
    merged_data = {}

    # Iterate through the keys of both dictionaries
    for key in set(block_1.keys()).union(block_2.keys()):
        if key in block_1 and key in block_2:
            # If both dictionaries have the same key, merge their values
            merged_data[key] = {**block_1[key], **block_2[key]}
        elif key in block_1:
            # If the key is only in block_1
            merged_data[key] = block_1[key]
        else:
            # If the key is only in block_2
            merged_data[key] = block_2[key]

    return merged_data
def child_key (data, key_child):
    data_out = {}
    if isinstance(data[key_child], dict):
        for key in data[key_child]:
            data_out = child_merge(data_out, {key_child: {key: data[key_child][key]}})
            if key == 'volume':
                try:
                    data_out = child_merge(data_out, {key_child: {key: data[key_child][key]}})
                except:
                    pass
                print(data_out)
            if key == 'position':
                try:
                    data_out = child_merge(data_out, {key_child: {key: data[key_child][key]}})
                except:
                    pass
            child_key(data[key_child], key)
    elif isinstance(data[key_child], list):
        try:
            if key_child == 'distance_volume_mapping_curve':
                for key in data[key_child]:
                    block_new = {key_child: key}
                    data_out = child_merge(data_out, block_new)
                    print(key,data[key_child])
                    print(data_out)
        except:
            pass
        for key in data[key_child]:
            try:
                if key_child == 'distance_volume_mapping_curve':
                    block_new = {key_child: {key: data[key_child][key]}}
                    data_out = child_merge(data_out, block_new)
                    print(block_new)
                else:
                    block_new = {key_child: {key: data[key_child][key]}}
                    data_out = child_merge(data_out, block_new)
                    print(block_new)
            except:
                pass
    elif isinstance(data[key_child], int):
        pass
        # print(key_child,'int ', data[key_child])
    elif isinstance(data[key_child], float):
        try:
            for key in data[key_child]:
                print(key_child, key, data[key_child][key])
        except:
            pass

    elif isinstance(data[key_child], str):
        try:
            for key in data[key_child]:
                print(key_child, key, data[key_child][key])
        except:
            pass
    else:
        print('Do not match')
    return data_out

# Merge childs in new var
data_kv3 = {}

# print(data_kv3)
# kv3.write(data_kv3, sys.stdout)

for parent in data.keys():
    data_out = child_key(data, parent)
    data_kv3 = child_merge(data_kv3,data_out)


data = {'ambient_example.indoors.vent': {'base': 'amb.looping.atXYZ.base', 'volume': 0.2}}

def add_items(parent, data):
    for key, value in data.items():
        key_item = QStandardItem(key)
        if isinstance(value, dict):
            value_item = QStandardItem("")
            parent.appendRow([key_item, value_item])
            add_items(key_item, value)
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


# for key, value in data.items():
#     for key in data[key]:
#         print(f"{key} = {value}")