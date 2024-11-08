import ast
import subprocess
import os
from pydoc import importfile


from src.preferences import get_addon_name, get_cs2_path, debug
from src.soudevent_editor.ui_main import Ui_MainWindow
from src.explorer.main import Explorer
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu, QDialog, QTreeWidget, QIntList, QTreeWidgetItem, QMessageBox, QApplication
from PySide6.QtGui import QKeySequence, QUndoStack
from PySide6.QtCore import Qt
from src.widgets import HierarchyItemModel, ErrorInfo
from src.preferences import settings
from src.soudevent_editor.properties_window import SoundEventEditorPropertiesWindow
from src.soudevent_editor.preset_manager import SoundEventEditorPresetManagerWindow
from src.common import JsonToKv3,Kv3ToJson
from src.smartprop_editor.commands import DeleteTreeItemCommand

class CopyDefaultSoundFolders:
    pass


class LoadSoundEvents:
    def __init__(self, tree: QTreeWidget, path: str):
        super().__init__()
        data = open(path, "r")
        data = Kv3ToJson(data.read())
        self.tree = tree
        self.tree.clear()
        self.root = self.tree.invisibleRootItem()
        for key in data:
            new_item = HierarchyItemModel(_data=data[key], _name=key)
            self.root.addChild(new_item)
class SoundEventEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.realtime_save = False
        self.undo_stack = QUndoStack(self)

        # Variables
        self.filepath_vsndevts = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents','soundevents_addon.vsndevts')
        self.filepath_sounds = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'sounds')

        # Variables debug
        debug(f"self.filepath_vsndevts : {self.filepath_vsndevts}")
        debug(f"self.filepath_sounds : {self.filepath_sounds}")

        # Init LoadSoundEvents
        if os.path.exists(self.filepath_vsndevts):
            LoadSoundEvents(tree=self.ui.hierarchy_widget, path=self.filepath_vsndevts)
        else:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(
                "There is no soundevents file. Will you create default? Attention: it would overwrite existing wav files in sounds folder, if it exists.")
            msg_box.setWindowTitle("Warning")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.exec()

        # Init PropertiesWindow
        self.PropertiesWindowInit()

        # Init Hierarchy
        self.ui.hierarchy_widget.header().setSectionHidden(1, True)
        self.ui.hierarchy_widget.currentItemChanged.connect(self.on_changed_hierarchy_item)
        self.ui.hierarchy_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.hierarchy_widget.customContextMenuRequested.connect(self.open_hierarchy_menu)

        # Init Hierarchy filer bar
        self.ui.hierarchy_search_bar_widget.textChanged.connect(lambda text:self.search_hierarchy(text, self.ui.hierarchy_widget.invisibleRootItem()))

        # Connections
        self.ui.open_preset_manager_button.clicked.connect(self.OpenPresetManager)
        self.ui.reload_button.clicked.connect(lambda: LoadSoundEvents(tree=self.ui.hierarchy_widget, path=self.filepath_vsndevts))

        # Explorer
        if os.path.exists(self.filepath_sounds):
            pass
        else:
            os.makedirs(self.filepath_sounds)
        self.mini_explorer = Explorer(tree_directory=self.filepath_sounds, addon=get_addon_name(), editor_name='SoundEvent_Editor', parent=self.ui.explorer_layout_widget)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

    #=======================================================<  Properties Window  >=====================================================

    def PropertiesWindowInit(self):
        self.PropertiesWindow = SoundEventEditorPropertiesWindow()
        self.ui.frame.layout().addWidget(self.PropertiesWindow)
    def UpdatePropertiesWindow(self):
        pass

    #================================================================<  Hierarchy  >=============================================================

    def update_hierarchy_item(self, item: QTreeWidgetItem, _data: dict):
        "Sets Value to data column"
        item.setText(1, str(_data))
    def on_changed_hierarchy_item(self, current_item: QTreeWidgetItem):
        "On changed hierarchy item clear, shows or hide properties placeholder widget"
        if current_item is not None:
            self.PropertiesWindow.properties_groups_show()
            self.PropertiesWindow.properties_clear()
            # Convert column text to dict value
            data = ast.literal_eval(current_item.text(1))
            self.PropertiesWindow.populate_properties(data)
        else:
            self.PropertiesWindow.properties_clear()
            self.PropertiesWindow.properties_groups_hide()


    # ======================================[Tree widget hierarchy filter]========================================
    def search_hierarchy(self, filter_text, parent_item):
        # Reset the root visibility and start the filtering process
        self.filter_tree_item(parent_item, filter_text.lower(), True)

    def filter_tree_item(self, item, filter_text, is_root=False):
        if not isinstance(item, QTreeWidgetItem):
            return False

        # Check if the current item's text matches the filter
        item_text = item.text(0).lower()
        item_visible = filter_text in item_text

        # Always show the root, regardless of filter
        if is_root:
            item.setHidden(False)
        else:
            # Hide the item if it doesn't match the filter
            item.setHidden(not item_visible)

        # Track visibility of any child matching the filter
        any_child_visible = False

        # Recursively filter all children
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_visible = self.filter_tree_item(child_item, filter_text, False)

            if child_visible:
                any_child_visible = True

        # If any child is visible, make sure this item is also visible
        if any_child_visible:
            item.setHidden(False)
            item.setExpanded(True)

        # Return True if this item or any of its children is visible
        return item_visible or any_child_visible

    # ======================================[Tree widget hierarchy context menu]========================================
    def open_hierarchy_menu(self, position):
        menu = QMenu()
        add_new_preset_lat_action = menu.addAction("(Last) - New from")
        menu.addSeparator()
        add_new_preset_action = menu.addAction("New event (Preset)")
        add_new_blank_action = menu.addAction("New event (Blank)")
        # add_new_action.triggered.connect(self.add_an_element)
        add_new_preset_action.setShortcut(QKeySequence(QKeySequence("Ctrl+F")))

        menu.addSeparator()

        move_up_action = menu.addAction("Move Up")
        move_up_action.triggered.connect(lambda: self.move_tree_item(self.ui.hierarchy_widget, -1))
        move_up_action.setShortcut(QKeySequence(QKeySequence("Ctrl+Up")))

        move_down_action = menu.addAction("Move Down")
        move_down_action.triggered.connect(lambda: self.move_tree_item(self.ui.hierarchy_widget, 1))
        move_down_action.setShortcut(QKeySequence(QKeySequence("Ctrl+Down")))
        menu.addSeparator()

        remove_action = menu.addAction("Remove")
        # remove_action.triggered.connect(lambda: self.remove_tree_item(self.ui.hierarchy_widget))
        remove_action.triggered.connect(
            lambda: self.undo_stack.push(DeleteTreeItemCommand(self.ui.hierarchy_widget)))
        remove_action.setShortcut(QKeySequence(QKeySequence("Delete")))

        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self.duplicate_hierarchy_items(self.ui.hierarchy_widget))
        duplicate_action.setShortcut(QKeySequence(QKeySequence("Ctrl+D")))

        menu.addSeparator()

        copy_action = menu.addAction("Copy")
        copy_action.setShortcut(QKeySequence(QKeySequence.Copy))
        copy_action.triggered.connect(lambda: self.copy_item(self.ui.hierarchy_widget))

        paste_action = menu.addAction("Paste")
        paste_action.setShortcut(QKeySequence(QKeySequence.Paste))
        paste_action.triggered.connect(lambda: self.paste_item(self.ui.hierarchy_widget, paste_to_parent=True))

        menu.exec(self.ui.hierarchy_widget.viewport().mapToGlobal(position))

    # ======================================[Tree widget functions]========================================

    def move_tree_item(self, tree, direction):
        """Move selected tree items up or down within their parent."""
        selected_items = tree.selectedItems()
        if not selected_items:
            return  # Exit if no items are selected

        # Group items by parent and sort by current index
        parent_to_items = {}
        for item in selected_items:
            parent = item.parent() or tree.invisibleRootItem()
            if parent not in parent_to_items:
                parent_to_items[parent] = []
            parent_to_items[parent].append(item)

        # Move items for each parent separately
        for parent, items in parent_to_items.items():
            # Sort items by their index in reverse if moving down (to avoid index shifting)
            items.sort(key=lambda item: parent.indexOfChild(item), reverse=(direction > 0))

            for item in items:
                current_index = parent.indexOfChild(item)
                new_index = current_index + direction

                # Check bounds
                if 0 <= new_index < parent.childCount():
                    # Move item
                    parent.takeChild(current_index)
                    parent.insertChild(new_index, item)

        tree.clearSelection()
        for item in selected_items:
            item.setSelected(True)
        tree.scrollToItem(selected_items[-1] if direction > 0 else selected_items[0])

    def copy_item(self, tree, copy_to_clipboard=True):
        """Coping Tree item"""
        # Gathering selected items
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]

        # Remove the same items
        selected_items = list(set(selected_items))

        for tree_item in selected_items:
            item_data = self.serialization_hierarchy_items(item=tree_item)
        # Output
        if copy_to_clipboard:
            clipboard = QApplication.clipboard()
            clipboard.setText(JsonToKv3(item_data))
        else:
            return JsonToKv3(item_data)

    def paste_item(self, tree, data_input=None, paste_to_parent=False):
        """Pasting tree item"""
        if data_input is None:
            data_input = QApplication.clipboard().text()
        try:
            input = Kv3ToJson(data_input)
            if 'm_Children' in input:
                for key in input['m_Children']:
                    tree_item = self.deserialize_hierarchy_item(key)
                    try:
                        if paste_to_parent:
                            tree.currentItem().parent().addChild(tree_item)
                        else:
                            tree.currentItem().addChild(tree_item)
                    except:
                        tree.invisibleRootItem().addChild(tree_item)
            else:
                tree_item = self.deserialize_hierarchy_item(input)
                try:
                    if paste_to_parent:
                        tree.currentItem().parent().addChild(tree_item)
                    else:
                        tree.currentItem().addChild(tree_item)
                except:
                    tree.invisibleRootItem().addChild(tree_item)
        except Exception as error:
            error_message = str(error)
            error_dialog = ErrorInfo(text="Wrong format of the pasting content", details=error_message)
            error_dialog.exec()

    def remove_tree_item(self, tree):
        """Removing Tree item"""
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]
        for item in selected_items:
            if item:
                if item == item.treeWidget().invisibleRootItem():
                    pass
                else:
                    parent = item.parent() or item.treeWidget().invisibleRootItem()
                    index = parent.indexOfChild(item)
                    parent.takeChild(index)

    def duplicate_hierarchy_items(self, tree):
        data = self.copy_item(tree=tree, copy_to_clipboard=False)
        self.paste_item(tree, data, paste_to_parent=True)

    # ======================================[Tree item serialization and deserialization]========================================

    def serialization_hierarchy_items(self, item, data=None):
        """Convert tree structure to json"""
        if data is None:
            data = {'m_Children': []}
        value_row = item.text(1)
        parent_data = ast.literal_eval(value_row)
        # Label form tree element name
        parent_data['m_sLabel'] = item.text(0)
        if item.childCount() > 0:
            parent_data['m_Children'] = []
        data['m_Children'].append(parent_data)
        if item.childCount() > 0:
            for index in range(item.childCount()):
                child = item.child(index)
                key = child.text(0)
                value_row = child.text(1)

                child_data = ast.literal_eval(value_row)
                child_data['m_sLabel'] = key

                if child.childCount() > 0:
                    child_data['m_Children'] = []
                    self.serialization_hierarchy_items(child, child_data)

                parent_data['m_Children'].append(child_data)

        return data

    def deserialize_hierarchy_item(self, m_Children=HierarchyItemModel):
        item_value = {}

        # If there is a dict with child element, copy all expect child key in a new variable, and process it.
        for key in m_Children:
            if key == 'm_Children':
                pass
            else:
                item_value.update({key: m_Children[key]})
        # Get tree item name
        name = item_value.get('m_sLabel', 'None')

        # New element
        tree_item = HierarchyItemModel(_data=item_value, _name=name)
        return tree_item

    #===========================================================<  Preset Manager  >========================================================
    def OpenPresetManager(self):
        self.PresetManager = SoundEventEditorPresetManagerWindow()
        self.PresetManager.show()

    #======================================[Window State]========================================
    def _restore_user_prefs(self):
        """Restore window state"""
        geo = self.settings.value("SoundEventEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SoundEventEditorMainWindow/windowState")
        if state:
            self.restoreState(state)

    def _save_user_prefs(self):
        """Save window state"""
        self.settings.setValue("SoundEventEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SoundEventEditorMainWindow/windowState", self.saveState())
    def closeEvent(self, event):
        self._save_user_prefs()