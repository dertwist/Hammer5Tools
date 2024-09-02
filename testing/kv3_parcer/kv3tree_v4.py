import sys
from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMainWindow, QMenu,
    QInputDialog, QMessageBox, QToolBar, QPushButton, QFileDialog, QHeaderView
)
from PySide6.QtCore import Qt
import json as vsmart

import keyvalues3 as kv3

bt_config = kv3.read('sample.vsmart')

data = {
    'generic_data_type': 'CSmartPropRoot',
    'm_Variables': [{'_class': 'CSmartPropVariable_Float', 'm_VariableName': 'length', 'm_nElementID': 61, 'm_nElementID1': 61.2}],
    'm_Children': [{'_class': 'CSmartPropElement_Mode55555l',
                    'm_sModelName': 'models/props/de_nuke/hr_nuke/airduct_hvac_001/airduct_hvac_001_endcap.vmdl',
                    'm_nElementID': 2},{'_class': 'CSmartPropElement_Model',
                    'm_sModelName': 'models/props/de_nuke/hr_nuke/airduct_hvac_001/airduct_hvac_001_endcap.vmdl',
                    'm_nElementID': 2}]
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartProp Editor v1")
        self.setGeometry(500, 500, 900, 500)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Key", "Value"])

        header_font = self.tree.headerItem().font(0)
        header_font.setPointSize(12)
        self.tree.headerItem().setFont(0, header_font)

        header = self.tree.header()
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.resizeSection(0, 500)

        self.setCentralWidget(self.tree)

        self.populate_tree(data)

        toolbar = QToolBar()
        self.addToolBar(toolbar)

        export_button = QPushButton("Export to Path")
        export_button.clicked.connect(self.export_to_file)
        toolbar.addWidget(export_button)

        quick_export_button = QPushButton("Quick Export")
        quick_export_button.clicked.connect(self.quick_export_to_file)
        toolbar.addWidget(quick_export_button)

        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())