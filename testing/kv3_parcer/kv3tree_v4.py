import sys
from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMainWindow, QMenu,
    QInputDialog, QMessageBox, QToolBar, QPushButton, QFileDialog, QHeaderView
)
from PySide6.QtCore import Qt
import json

import keyvalues3 as kv3

# Sample JSON data

# bt_config = kv3.read(r'E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_ankhor\smartprops\hvac_kit.vsmart')
bt_config = kv3.read('sample.vsmart')

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
print(data)
# data = {
#     'generic_data_type': 'CSmartPropRoot',
#     'm_Variables': [{'_class': 'CSmartPropVariable_Float', 'm_VariableName': 'length', 'm_nElementID': 61}],
#     'm_Children': [{'_class': 'CSmartPropElement_Model',
#                     'm_sModelName': 'models/props/de_nuke/hr_nuke/airduct_hvac_001/airduct_hvac_001_endcap.vmdl',
#                     'm_nElementID': 2}]
# }


square_brackets_group = ['m_Children', 'm_Variables', 'm_Modifiers', 'm_vRandomRotationMin', 'm_vRandomRotationMax', 'm_vPosition']

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

        export_button = QPushButton("Export to Path")
        export_button.clicked.connect(self.export_to_file)
        toolbar.addWidget(export_button)


        quick_export_button = QPushButton("Quick Export")
        quick_export_button.clicked.connect(self.quick_export_to_file())
        toolbar.addWidget(quick_export_button)


        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)


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
            parent = self.tree.invisibleRootItem()
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    item = QTreeWidgetItem([key])
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    parent.addChild(item)
                    for child_data in value:
                        self.populate_tree(child_data, item)
                elif isinstance(value, list):
                    item_class = value[0].get('_class')
                    child = QTreeWidgetItem([key])
                    child.setFlags(child.flags() | Qt.ItemIsEditable)
                    parent.addChild(child)

                    for item in value:
                        item_class = item.get('_class')
                        child_item = QTreeWidgetItem([item_class])
                        child_item.setFlags(child_item.flags() | Qt.ItemIsEditable)
                        child.addChild(child_item)
                        self.populate_tree(item, child_item)
                elif isinstance(value, (str, float, int)):
                    item = QTreeWidgetItem([key, str(value)])
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    parent.addChild(item)
                    self.populate_tree(value, item)

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
        # QMessageBox.information(self, "Export", "Data exported to 'exported_data.json' successfully!")

    def tree_item_to_dict(self, item):
        if item.childCount() == 0:
            return item.text(1)
        data = {}
        for i in range(item.childCount()):
            child = item.child(i)
            key = child.text(0)
            value = self.tree_item_to_dict(child)
            if key in data:
                if isinstance(data[key], list):
                    data[key].append(value)
                else:
                    data[key] = [data[key], value]
            else:
                data[key] = value
        return data


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
