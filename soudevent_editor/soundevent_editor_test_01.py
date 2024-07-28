import sys
from PySide6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem, QMainWindow, QMenu,
    QInputDialog, QMessageBox, QToolBar, QPushButton, QFileDialog, QTextEdit, QVBoxLayout, QWidget, QHeaderView, QStyledItemDelegate
)
from PySide6.QtCore import Qt
import json
import keyvalues3 as kv3

data = {'ambient_example.outdoors': {'base': 'amb.soundscapeParent.base', 'enable_child_events': 'True', 'soundevent_01': 'ambient_example.outdoors.wind'}, 'ambient_example.outdoors.wind': {'base': 'amb.looping.stereo.base', 'volume': '0.7', 'pitch': '0.8', 'vsnd_files_track_01': 'sounds/ambient/dust2/wind_sand_01.vsnd'}, 'ambient_example.outdoors.airplanes': {'base': 'amb.intermittent.randomAroundPlayer.base', 'volume': '0.7', 'randomize_position_min_radius': '2000.0', 'randomize_position_max_radius': '3000.0', 'retrigger_interval_min': '11.0', 'retrigger_interval_max': '30.0', 'vsnd_files_track_01': 'sounds/ambient/dust2/airplane_03.vsnd'}}

square_brackets_group = ['m_Children', 'm_Variables', 'm_Modifiers', 'm_vRandomRotationMin', 'm_vRandomRotationMax', 'm_vPosition']

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartProp Editor v1")

        # Get screen resolution
        screen = QApplication.primaryScreen().geometry()
        width, height = screen.width(), screen.height()

        # Set window size to 50% of screen resolution
        self.setGeometry(500, 500, width // 2, height // 2)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Key", "Value"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)
        self.tree.itemChanged.connect(self.on_item_changed)

        # Set the delegate for padding
        self.tree.setItemDelegateForColumn(1, QStyledItemDelegate())

        # Set the default width of the columns
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)

        # Set the initial width of the columns
        self.tree.header().resizeSection(0, self.width() * 0.3)
        self.tree.header().resizeSection(1, self.width() * 0.3)

        self.debug_window = QTextEdit(self)
        self.debug_window.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        layout.addWidget(self.debug_window)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.populate_tree(data)

        toolbar = QToolBar()
        self.addToolBar(toolbar)

        export_button = QPushButton("Export to Path")
        export_button.clicked.connect(self.export_to_file)
        toolbar.addWidget(export_button)

        load_button = QPushButton("Load from File")
        load_button.clicked.connect(self.load_file)
        toolbar.addWidget(load_button)

        quick_export_button = QPushButton("Quick Export")
        quick_export_button.clicked.connect(self.quick_export_to_file)
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
        self.update_debug_window()

    def populate_tree(self, data, parent=None):
        if parent is None:
            parent = self.tree.invisibleRootItem()

        if isinstance(data, dict):
            for key, value in data.items():
                if key in square_brackets_group and isinstance(value, list):
                    item = QTreeWidgetItem([key])
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    parent.addChild(item)
                    for child_data in value:
                        self.populate_tree(child_data, item)
                else:
                    item = QTreeWidgetItem([key])
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    parent.addChild(item)
                    self.populate_tree(value, item)
        elif isinstance(data, list):
            for value in data:
                self.populate_tree(value, parent)
        else:
            parent.setText(1, str(data))
            parent.setFlags(parent.flags() | Qt.ItemIsEditable)

    def on_item_changed(self, item, column):
        self.update_debug_window()

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
        self.update_debug_window()

    def add_item(self, item):
        key, ok = QInputDialog.getText(self, "Add Item", "Enter key:")
        if ok and key:
            new_item = QTreeWidgetItem([key])
            new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)
            if item:
                item.addChild(new_item)
            else:
                self.tree.addTopLevelItem(new_item)
        self.update_debug_window()

    def edit_item(self, item):
        if item:
            self.tree.editItem(item, 0)
        self.update_debug_window()

    def remove_item(self, item):
        if item:
            parent = item.parent() or self.tree.invisibleRootItem()
            index = parent.indexOfChild(item)
            parent.takeChild(index)
        self.update_debug_window()

    def convert_children_to_list(self, data):
        if isinstance(data, dict):
            if 'm_Children' in data and isinstance(data['m_Children'], dict):
                data['m_Children'] = [data['m_Children']]

            for key, value in data.items():
                data[key] = self.convert_children_to_list(value)

        elif isinstance(data, list):
            for i in range(len(data)):
                data[i] = self.convert_children_to_list(data[i])

        return data

    def export_to_json(self):
        root = self.tree.invisibleRootItem()
        data = self.tree_item_to_dict(root)
        data = self.convert_children_to_list(data)
        print(data)

        try:
            for key in square_brackets_group:
                if key in data and not isinstance(data[key], list):
                    data[key] = [data[key]]
        except:
            pass

        kvfg = data

        print(kv3.write(kvfg, sys.stdout))

        orig_stdout = sys.stdout
        f = open(r"D:\CG\Projects\Other\Hammer5Tools\soudevent_editor\soundevents_addon_out.vsndevts", 'w')
        sys.stdout = f

        for i in range(1):
            print(kv3.write(kvfg, sys.stdout))
        sys.stdout = orig_stdout
        f.close()

        file_path = r"D:\CG\Projects\Other\Hammer5Tools\soudevent_editor\soundevents_addon_out.vsndevts"

        with open(file_path, 'r') as file:
            content = file.read()

        new_content = content.replace('None', '')

        with open(file_path, 'w') as file:
            file.write(new_content)
        return str(data)

    def export_to_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save JSON File", "", "JSON Files (*.json);;All Files (*)",
                                                   options=options)
        if file_path:
            json_data = self.export_to_json()
            with open(file_path, "w") as file:
                file.write(json_data)
            QMessageBox.information(self, "Export", "Data exported successfully!")
        self.update_debug_window()

    def quick_export_to_file(self):
        json_data = self.export_to_json()
        with open("exported_data.json", "w") as file:
            file.write(json_data)
        QMessageBox.information(self, "Export", "Data exported to 'exported_data.json' successfully!")
        self.update_debug_window()

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

    def load_file(self):
        bt_config = kv3.read(r"D:\CG\Projects\Other\Hammer5Tools\soudevent_editor\soundevents_addon.vsndevts")

        data = bt_config.value
        self.populate_tree(data)
        print(data)
        self.update_debug_window()

    def update_debug_window(self):
        root = self.tree.invisibleRootItem()
        data = self.tree_item_to_dict(root)
        self.debug_window.setPlainText(json.dumps(data, indent=4))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())