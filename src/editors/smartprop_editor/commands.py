import copy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget
from PySide6.QtGui import QUndoCommand
from src.widgets import HierarchyItemModel
from src.editors.smartprop_editor._common import get_ElementID_key
class GroupElementsCommand(QUndoCommand):
    def __init__(self, tree: QTreeWidget):
        super().__init__("Group Selected Items")
        self.tree = tree
        self.group_element = None
        self.moved_items_info = []  # (item, old_parent, old_index)
        self._selected_order = [item for item in self.tree.selectedItems()]
        # Keep references to all items to prevent deletion
        self._item_refs = list(self._selected_order)
    def redo(self):
        group_data = {'_class': 'CSmartPropElement_Group', 'm_Modifiers': [], 'm_SelectionCriteria': []}
        group_id = get_ElementID_key(group_data)
        self.group_element = HierarchyItemModel(_data=group_data, _name='Group', _class='Group', _id=group_id)
        invisible_root = self.tree.invisibleRootItem()
        self.moved_items_info = []
        for item in self._selected_order:
            if item is None or item == invisible_root:
                continue
            old_parent = item.parent() or invisible_root
            old_index = old_parent.indexOfChild(item)
            self.moved_items_info.append((item, old_parent, old_index))
        for item, old_parent, old_index in sorted(self.moved_items_info, key=lambda x: (id(x[1]), x[2]), reverse=True):
            old_parent.takeChild(old_index)
        for item, _, _ in self.moved_items_info:
            self.group_element.addChild(item)
        invisible_root.addChild(self.group_element)
        self.tree.clearSelection()
        self.group_element.setSelected(True)
        self.tree.scrollToItem(self.group_element)
    def undo(self):
        if self.group_element is None:
            return
        try:
            invisible_root = self.tree.invisibleRootItem()
            invisible_root.removeChild(self.group_element)
            for item, _, _ in reversed(self.moved_items_info):
                idx = self.group_element.indexOfChild(item)
                if idx != -1:
                    self.group_element.takeChild(idx)
            for item, old_parent, old_index in self.moved_items_info:
                old_parent.insertChild(old_index, item)
            self.tree.clearSelection()
            for item, _, _ in self.moved_items_info:
                item.setSelected(True)
                self.tree.scrollToItem(item)
            self._item_refs = [item for item, _, _ in self.moved_items_info]
        except (RuntimeError, ReferenceError):
            pass
class PasteItemsCommand(QUndoCommand):
    def __init__(self, tree, parent, items):
        super().__init__("Paste Items")
        self.tree = tree
        self.parent = parent
        self.items = items
        self.added = []
    def redo(self):
        for item in self.items:
            self.parent.addChild(item)
            self.parent.setExpanded(True)
            self.added.append(item)
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])
    def undo(self):
        for item in self.added:
            self.parent.removeChild(item)
        self.added.clear()
class BulkModelImportCommand(QUndoCommand):
    def __init__(self, document, parent_item, items):
        super().__init__("Bulk Model Import")
        self.document = document
        self.tree = document.ui.tree_hierarchy_widget
        self.parent_item = parent_item
        self.items = items
        self.added = []
    def redo(self):
        for item in self.items:
            self.parent_item.addChild(item)
            self.parent_item.setExpanded(True)
            self.added.append(item)
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])
    def undo(self):
        for item in self.added:
            self.parent_item.removeChild(item)
        self.added.clear()
class NewFromPresetCommand(QUndoCommand):
    def __init__(self, tree, parent, items):
        super().__init__("New From Preset")
        self.tree = tree
        self.parent = parent
        self.items = items
        self.added = []
    def redo(self):
        for item in self.items:
            self.parent.addChild(item)
            self.parent.setExpanded(True)
            self.added.append(item)
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])
    def undo(self):
        for item in self.added:
            self.parent.removeChild(item)
        self.added.clear()
class PropertiesStateCommand(QUndoCommand):
    def __init__(self, document, item, before, after, description="Edit Properties"):
        super().__init__(description)
        self.document = document
        self.item = item
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        self._first_redo_done = False

    def _item_is_valid(self):
        """Check if self.item is still alive and present in the tree."""
        try:
            # Accessing any property on a deleted C++ object raises RuntimeError
            _ = self.item.treeWidget()
            return _ is not None
        except (RuntimeError, ReferenceError):
            return False

    def _apply(self, state):
        if not self._item_is_valid():
            return
        try:
            # 1. Write restored data into the tree item
            self.item.setData(0, Qt.UserRole, copy.deepcopy(state))
            # 2. Select item, blocking the signal-triggered rebuild
            self.document._restoring_from_undo = True
            try:
                self.document.ui.tree_hierarchy_widget.setCurrentItem(self.item)
            finally:
                self.document._restoring_from_undo = False
            # 3. Explicitly rebuild the Properties UI with the restored data
            self.document._restoring_from_undo = True
            self.document._rebuilding_properties = True
            try:
                self.document.on_tree_current_item_changed(self.item, None)
            finally:
                self.document._rebuilding_properties = False
                self.document._restoring_from_undo = False
            # 4. Sync snapshot so the next user edit has the correct baseline
            self.document._properties_snapshot = copy.deepcopy(state)
        except (RuntimeError, ReferenceError):
            # Item was deleted from C++ side
            pass

    def undo(self):
        self._apply(self.before)

    def redo(self):
        if self._first_redo_done:
            self._apply(self.after)
        self._first_redo_done = True
class ChoicesStateCommand(QUndoCommand):
    def __init__(self, document, before, after, description="Edit Choices"):
        super().__init__(description)
        self.document = document
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        self._first_redo_done = False
    def _apply(self, state):
        self.document._restoring_from_undo = True
        try:
            self.document._rebuild_choices_from_snapshot(state)
        except (RuntimeError, ReferenceError):
            pass
        finally:
            self.document._restoring_from_undo = False
    def undo(self):
        self._apply(self.before)
    def redo(self):
        if self._first_redo_done:
            self._apply(self.after)
        self._first_redo_done = True
class VariablesStateCommand(QUndoCommand):
    def __init__(self, document, before, after, description="Edit Variables"):
        super().__init__(description)
        self.document = document
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        self._first_redo_done = False
    def _apply(self, state):
        self.document._restoring_from_undo = True
        try:
            self.document._rebuild_variables_from_snapshot(state)
        except (RuntimeError, ReferenceError):
            pass
        finally:
            self.document._restoring_from_undo = False
    def undo(self):
        self._apply(self.before)
    def redo(self):
        if self._first_redo_done:
            self._apply(self.after)
        self._first_redo_done = True
