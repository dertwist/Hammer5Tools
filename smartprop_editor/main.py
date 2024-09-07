import os.path
from distutils.util import strtobool

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QTreeWidgetItem, QVBoxLayout, QSpacerItem, QSizePolicy, QInputDialog
from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtGui import QCursor, QDrag, QAction
from PySide6.QtCore import Qt

from smartprop_editor.ui_main import Ui_MainWindow
from preferences import get_config_value, get_addon_name, get_cs2_path

from smartprop_editor.variable_frame import VariableFrame
from smartprop_editor.objects import variables_list, variable_prefix
from smartprop_editor.vsmart import VsmartOpen, VsmartSave

from explorer.main import Explorer
from preferences import settings

global opened_file


# Get cs2_path
cs2_path = get_cs2_path()

class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, version="v0.0.2", parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.version_label.setText(version)
        self.settings = settings

        # Hierarchy setup
        self.ui.tree_hierarchy_widget.hideColumn(1)
        self.ui.tree_hierarchy_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tree_hierarchy_widget.customContextMenuRequested.connect(self.open_hierarchy_menu)

        # adding var classes to combobox
        for item in variables_list:
            self.ui.add_new_variable_combobox.addItem(item)

        # restore_prefs
        self._restore_user_prefs()

        tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name(), 'smartprops')
        self.mini_explorer = Explorer(tree_directory=tree_directory, addon=get_addon_name(), editor_name='SmartProp_editor', parent=self.ui.explorer_layout_widget)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

        self.buttons()


    def buttons(self):
        self.ui.add_new_variable_button.clicked.connect(self.add_new_variable)
        self.ui.open_file_button.clicked.connect(self.open_file)
        self.ui.save_file_button.clicked.connect(self.save_file)

    def open_file(self):
        index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
        filename = self.mini_explorer.model.filePath(index)
        global opened_file
        opened_file = filename
        VsmartOpen(filename=filename, tree=self.ui.tree_hierarchy_widget)
    def save_file(self):
        index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
        filename = opened_file
        print(filename)
        VsmartSave(filename=filename, tree=self.ui.tree_hierarchy_widget)
    # variables
    def add_new_variable(self):
        name = 'new_var'
        existing_variables = []
        variables = self.get_variables(self.ui.variables_scrollArea)
        for key, value in variables.items():
            existing_variables.append(value[0])

        # Check if the name already exists
        if name in existing_variables:
            suffix = 1
            while f"{name}_{suffix}" in existing_variables:
                suffix += 1
            name = f"{name}_{suffix}"
        self.add_variable(name=name, var_value='', var_visible_in_editor=False, var_class=self.ui.add_new_variable_combobox.currentText())

    def add_variable(self, name, var_class, var_value, var_visible_in_editor):
        variable = VariableFrame(name=name, widget_list=self.ui.variables_scrollArea, var_value=var_value, var_class=var_class, var_visible_in_editor=var_visible_in_editor)
        index = (self.ui.variables_scrollArea.count()) - 1
        self.ui.variables_scrollArea.insertWidget(index, variable)

    def get_variables(self, layout):
        data_out = {}
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                item = {i: [widget.name, widget.var_class, widget.var_value, widget.var_visible_in_editor]}
                data_out.update(item)
        return data_out

    # ContextMenu
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        if self.ui.variables_QscrollArea is QApplication.focusWidget():
            paste_action = QAction("Paste Variable", self)
            paste_action.triggered.connect(self.paste_variable)
            context_menu.addAction(paste_action)
        else:
            pass

        context_menu.exec_(event.globalPos())

    def paste_variable(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(';;')

        if clipboard_data[0] == "hammer5tools:smartprop_editor_var":
            visible_in_editor = bool(strtobool(clipboard_data[4]))
            self.add_variable(clipboard_data[1], clipboard_data[2], clipboard_data[3], visible_in_editor)
        else:
            print("Clipboard data format is not valid.")


    def open_hierarchy_menu(self, position):
        menu = QMenu()
        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")
        add_action = menu.addAction("Add")
        edit_action = menu.addAction("Edit")
        remove_action = menu.addAction("Remove")

        move_up_action.triggered.connect(lambda: self.move_item(self.ui.tree_hierarchy_widget.itemAt(position), -1))
        move_down_action.triggered.connect(lambda: self.move_item(self.ui.tree_hierarchy_widget.itemAt(position), 1))
        add_action.triggered.connect(lambda: self.add_item(self.ui.tree_hierarchy_widget.itemAt(position)))
        edit_action.triggered.connect(lambda: self.edit_item(self.ui.tree_hierarchy_widget.itemAt(position)))
        remove_action.triggered.connect(lambda: self.remove_item(self.ui.tree_hierarchy_widget.itemAt(position)))

        menu.exec(self.ui.tree_hierarchy_widget.viewport().mapToGlobal(position))

    def move_item(self, item, direction):
        if not item:
            return
        parent = item.parent() or self.ui.tree_hierarchy_widget.invisibleRootItem()
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
                self.ui.tree_hierarchy_widget.addTopLevelItem(new_item)

    def edit_item(self, item):
        if item:
            self.ui.tree_hierarchy_widget.editItem(item, 0)

    def remove_item(self, item):
        if item:
            parent = item.parent() or self.ui.tree_hierarchy_widget.invisibleRootItem()
            index = parent.indexOfChild(item)
            parent.takeChild(index)

    # Prefs
    def _restore_user_prefs(self):
        geo = self.settings.value("SmartPropEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SmartPropEditorMainWindow/windowState")
        if state:
            self.restoreState(state)

        saved_index = self.settings.value("SmartPropEditorMainWindow/currentComboBoxIndex")
        if saved_index is not None:
            self.ui.add_new_variable_combobox.setCurrentIndex(int(saved_index))

    def _save_user_prefs(self):
        current_index = self.ui.add_new_variable_combobox.currentIndex()
        self.settings.setValue("SmartPropEditorMainWindow/currentComboBoxIndex", current_index)
        self.settings.setValue("SmartPropEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SmartPropEditorMainWindow/windowState", self.saveState())
    def closeEvent(self, event):
        self._save_user_prefs()
