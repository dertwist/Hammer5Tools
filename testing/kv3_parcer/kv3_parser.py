
import sys
import keyvalues3 as kv3

from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget, QHeaderView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QAbstractItemView
data = {'m_Variables': [{'_class': 'CSmartPropVariable_Float', 'm_VariableName': 'length', 'm_nElementID': 61}, {'_class': 'CSmartPropVariable_Int', 'm_VariableName': 'height', 'm_nElementID': 62}], 'generic_data_type': 'CSmartPropRoot', '_editor': {'m_nElementID':'1'}}
from PySide6.QtCore import Qt
data_read = kv3.read('sample.vsmart')
data = data_read
print(type(data), data)
# print(type(data['_editor']))
# print(data['generic_data_type'])
#
#
# print(data['m_Variables'])





def add_items(parent, data):

    for key, value in data.items():
        key_item = QStandardItem(key)
        if isinstance(value, dict):
                print(1, value)
                value_item = QStandardItem("")
                parent.appendRow([key_item, value_item])
                if value == '_editor':
                    pass
                else:
                    add_items(key_item, value)
        elif isinstance(value, list):
            list_parent = QStandardItem(key)
            parent.appendRow(list_parent)
            try:
                for item in value:
                    child_item = QStandardItem(item['_class'])
                    # if item.get('_class') == 'CSmartPropElement_Group':
                    # print('CSmartPropElement_Model', item)
                    # keys_except_m_children = [key for key in data.keys() if key != 'm_Children']
                    # child_value = QStandardItem(', '.join(keys_except_m_children))
                    # list_parent.appendRow([child_item, child_value])
                    # else:
                    list_parent.appendRow(child_item)
                    print(item)
                    # if 'm_Children' in item:
                    add_items(child_item, item)
            except:
                pass

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


global data_out_1

def export_tree_data(parent_item, output_dict):
    for row in range(parent_item.rowCount()):
        item = parent_item.child(row, 0)
        key = item.text()  # Get the text of the item as the key
        value_item = parent_item.child(row, 1)
        if value_item:
            value = value_item.text()  # Get the text of the value item
            output_dict[key] = value  # Store key-value pair in the dictionary
            if item.hasChildren():
                child_output_dict = {}  # Create a new dictionary for the nested key-value pairs
                output_dict[key] = child_output_dict
                export_tree_data(item, child_output_dict)

def export_data():
    def print_items(parent_item, indent=""):
        for row in range(parent_item.rowCount()):
            key_item = parent_item.index(row, 0).data()
            value_item = parent_item.index(row, 1).data()
            if value_item is not None:
                print(indent + key_item, value_item)
                if value_item.hasChildren():
                    print_items(value_item, indent + "  ")
            else:
                print(indent + key_item, "None")

    print_items(model)
# Create a QPushButton for exporting data
export_button = QPushButton("Export Data")
export_button.clicked.connect(export_data)
layout.addWidget(export_button)

# Populate the model with data
add_items(root_item, data)

# Set the model to the tree view
tree_view.setModel(model)
tree_view.expandAll()





tree_view.setDragEnabled(True)
tree_view.setAcceptDrops(True)
tree_view.setDragDropMode(QAbstractItemView.InternalMove)  # Adjust the drag-drop mode as needed

# Implement dragEnterEvent to handle when a drag operation enters the tree view
def dragEnterEvent(event):
    if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
        event.accept()
    else:
        event.ignore()

# Implement dropEvent to handle when a drop operation occurs in the tree view
def dropEvent(event):
    data = event.mimeData()
    if data.hasFormat('application/x-qabstractitemmodeldatalist'):
        # Process the dropped data and update the tree view accordingly
        event.accept()
    else:
        event.ignore()

# Connect the dragEnterEvent and dropEvent to the tree view
tree_view.dragEnterEvent = dragEnterEvent
tree_view.dropEvent = dropEvent


# Adjust the column widths to ensure 'Key' header has at least 50% of the width
header = tree_view.header()
header.setSectionResizeMode(0, QHeaderView.Stretch)  # Key column takes 50% of the width
header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Value column adjusts to content

# Add the tree view to the layout
layout.addWidget(tree_view)
window.setCentralWidget(central_widget)

# Show the window
window.resize(1400, 600)
window.show()

sys.exit(app.exec())

sys.exit(app.exec())
