import re
from src.common import fast_deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtGui import QUndoCommand

from src.widgets import HierarchyItemModel
from src.editors.smartprop_editor._common import get_clean_class_name_value, get_ElementID_key


class GroupElementsCommand(QUndoCommand):
    def __init__(self, tree: QTreeWidget):
        super().__init__("Group Selected Items")
        self.tree = tree
        self.group_element = None
        self.moved_items_info = []  # (item, old_parent, old_index)
        self._selected_order = [item for item in self.tree.selectedItems()]
        self._item_refs = list(self._selected_order)

    def redo(self):
        print(f"[SPE][GroupSelected] redo: grouping {len(self._selected_order)} item(s)")
        try:
            if self.tree is None:
                print("[SPE][GroupSelected] redo: SKIP — tree is None")
                return
            group_data = {
                '_class': 'CSmartPropElement_Group',
                'm_Modifiers': [],
                'm_SelectionCriteria': []
            }
            group_id = get_ElementID_key(group_data)
            self.group_element = HierarchyItemModel(
                _data=group_data, _name='Group',
                _class='Group', _id=group_id
            )
            invisible_root = self.tree.invisibleRootItem()
            self.moved_items_info = []
            for item in self._selected_order:
                if item is None or item == invisible_root:
                    continue
                old_parent = item.parent() or invisible_root
                old_index = old_parent.indexOfChild(item)
                if old_index == -1:
                    print(f"[SPE][GroupSelected] redo: WARN — item '{item.text(0)}' not found in parent, skipping")
                    continue
                self.moved_items_info.append((item, old_parent, old_index))
            for item, old_parent, old_index in sorted(
                self.moved_items_info, key=lambda x: (id(x[1]), x[2]), reverse=True
            ):
                old_parent.takeChild(old_index)
            for item, _, _ in self.moved_items_info:
                self.group_element.addChild(item)
            invisible_root.addChild(self.group_element)
            self.tree.clearSelection()
            self.group_element.setSelected(True)
            self.tree.scrollToItem(self.group_element)
        except Exception as e:
            print(f"[SPE][GroupSelected] redo: ERROR — {e}")

    def undo(self):
        print(f"[SPE][GroupSelected] undo: restoring {len(self.moved_items_info)} item(s) to original parents")
        try:
            if self.group_element is None or self.tree is None:
                print("[SPE][GroupSelected] undo: SKIP — group_element or tree is None")
                return
            invisible_root = self.tree.invisibleRootItem()
            if invisible_root.indexOfChild(self.group_element) != -1:
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
        except Exception as e:
            print(f"[SPE][GroupSelected] undo: ERROR — {e}")


class PasteItemsCommand(QUndoCommand):
    def __init__(self, tree, parent, items):
        super().__init__("Paste Items")
        self.tree = tree
        self.parent = parent
        self.items = items
        self.added = []

    def redo(self):
        print(f"[SPE][Paste] redo: pasting {len(self.items)} item(s) under '{self.parent.text(0) if self.parent else 'root'}'")
        try:
            if self.parent is None or self.tree is None:
                print("[SPE][Paste] redo: SKIP — parent or tree is None")
                return
            for item in self.items:
                self.parent.addChild(item)
                self.parent.setExpanded(True)
                self.added.append(item)
            if self.items:
                self.tree.clearSelection()
                self.items[0].setSelected(True)
                self.tree.scrollToItem(self.items[0])
        except Exception as e:
            print(f"[SPE][Paste] redo: ERROR — {e}")

    def undo(self):
        print(f"[SPE][Paste] undo: removing {len(self.added)} pasted item(s)")
        try:
            if self.parent is None:
                print("[SPE][Paste] undo: SKIP — parent is None")
                return
            for item in list(self.added):
                if self.parent.indexOfChild(item) != -1:
                    self.parent.removeChild(item)
                else:
                    print(f"[SPE][Paste] undo: WARN — item '{item.text(0)}' not found in parent, skipping")
            self.added.clear()
        except Exception as e:
            print(f"[SPE][Paste] undo: ERROR — {e}")


class BulkModelImportCommand(QUndoCommand):
    def __init__(self, document, parent_item, items):
        super().__init__("Bulk Model Import")
        self.document = document
        self.tree = document.ui.tree_hierarchy_widget
        self.parent_item = parent_item
        self.items = items
        self.added = []

    def redo(self):
        print(f"[SPE][BulkImport] redo: importing {len(self.items)} model(s) under '{self.parent_item.text(0) if self.parent_item else 'root'}'")
        try:
            if self.parent_item is None or self.tree is None:
                print("[SPE][BulkImport] redo: SKIP — parent_item or tree is None")
                return
            for item in self.items:
                self.parent_item.addChild(item)
                self.parent_item.setExpanded(True)
                self.added.append(item)
            if self.items:
                self.tree.clearSelection()
                self.items[0].setSelected(True)
                self.tree.scrollToItem(self.items[0])
        except Exception as e:
            print(f"[SPE][BulkImport] redo: ERROR — {e}")

    def undo(self):
        print(f"[SPE][BulkImport] undo: removing {len(self.added)} imported model(s)")
        try:
            if self.parent_item is None:
                print("[SPE][BulkImport] undo: SKIP — parent_item is None")
                return
            for item in list(self.added):
                if self.parent_item.indexOfChild(item) != -1:
                    self.parent_item.removeChild(item)
                else:
                    print(f"[SPE][BulkImport] undo: WARN — item '{item.text(0)}' not found in parent, skipping")
            self.added.clear()
        except Exception as e:
            print(f"[SPE][BulkImport] undo: ERROR — {e}")


class NewFromPresetCommand(QUndoCommand):
    def __init__(self, tree, parent, items):
        super().__init__("New From Preset")
        self.tree = tree
        self.parent = parent
        self.items = items
        self.added = []

    def redo(self):
        print(f"[SPE][NewFromPreset] redo: adding {len(self.items)} preset item(s)")
        try:
            if self.parent is None or self.tree is None:
                print("[SPE][NewFromPreset] redo: SKIP — parent or tree is None")
                return
            for item in self.items:
                self.parent.addChild(item)
                self.parent.setExpanded(True)
                self.added.append(item)
            if self.items:
                self.tree.clearSelection()
                self.items[0].setSelected(True)
                self.tree.scrollToItem(self.items[0])
        except Exception as e:
            print(f"[SPE][NewFromPreset] redo: ERROR — {e}")

    def undo(self):
        print(f"[SPE][NewFromPreset] undo: removing {len(self.added)} preset item(s)")
        try:
            if self.parent is None:
                print("[SPE][NewFromPreset] undo: SKIP — parent is None")
                return
            for item in list(self.added):
                if self.parent.indexOfChild(item) != -1:
                    self.parent.removeChild(item)
                else:
                    print(f"[SPE][NewFromPreset] undo: WARN — item '{item.text(0)}' not found in parent, skipping")
            self.added.clear()
        except Exception as e:
            print(f"[SPE][NewFromPreset] undo: ERROR — {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Properties Panel — snapshot-based undo (actions 11-20)
# ──────────────────────────────────────────────────────────────────────────────

class PropertySnapshotCommand(QUndoCommand):
    """Snapshot the full data of one hierarchy tree item before/after a property edit.

    Consecutive edits on the *same property* of the *same item* are merged so
    rapid keystrokes produce a single undo entry.  Editing a *different* property
    always starts a fresh history entry, giving the user one entry per property.
    The first redo() call is intentionally skipped because the change was already
    applied before the command was pushed.
    """
    _MERGE_ID = 1001

    @staticmethod
    def _changed_keys(old, new):
        """Return a frozenset of change-discriminator strings.

        For scalar values the discriminator is the dict key itself (e.g. 'm_flScale').
        For list values we identify which index changed.  If that index holds a dict
        we recurse into it so that two edits to different sub-properties of the same
        modifier produce distinct discriminators:
            m_Modifiers[0].m_flAmount  vs  m_Modifiers[0].m_bEnabled
        This prevents mergeWith from collapsing them into a single history entry.
        """
        all_keys = set((old or {}).keys()) | set((new or {}).keys())
        result = set()
        for k in all_keys:
            v_old = (old or {}).get(k)
            v_new = (new or {}).get(k)
            if v_old == v_new:
                continue
            if isinstance(v_old, list) and isinstance(v_new, list):
                old_ids = [item.get('m_nElementID') for item in v_old if isinstance(item, dict) and 'm_nElementID' in item]
                new_ids = [item.get('m_nElementID') for item in v_new if isinstance(item, dict) and 'm_nElementID' in item]
                if len(v_old) != len(v_new):
                    result.add(k)
                elif old_ids and new_ids and old_ids != new_ids:
                    result.add(k)
                else:
                    for i in range(len(v_old)):
                        if v_old[i] != v_new[i]:
                            if isinstance(v_old[i], dict) and isinstance(v_new[i], dict):
                                sub = PropertySnapshotCommand._changed_keys(v_old[i], v_new[i])
                                for sk in sub:
                                    result.add(f'{k}[{i}].{sk}')
                            else:
                                result.add(f'{k}[{i}]')
            elif isinstance(v_old, dict) and isinstance(v_new, dict):
                sub = PropertySnapshotCommand._changed_keys(v_old, v_new)
                for sk in sub:
                    result.add(f'{k}.{sk}')
            else:
                result.add(k)
        return frozenset(result)

    @staticmethod
    def _label_for_keys(keys, old_data=None, new_data=None):
        """Build a human-readable history label from the set of change discriminators."""
        content = keys - {'_class', 'm_nElementID'}
        
        # Check if this is a modifier/criteria list change (add, remove, reorder)
        list_keys = set()
        for k in content:
            base = k.split('[')[0]
            if base in ('m_Modifiers', 'm_SelectionCriteria'):
                list_keys.add(base)
        
        if len(list_keys) == 1 and all(k.startswith(list(list_keys)[0]) for k in content):
            base = list(list_keys)[0]
            friendly_base = "Modifier" if base == "m_Modifiers" else "Selection Criteria"
            
            old_list = (old_data or {}).get(base, [])
            new_list = (new_data or {}).get(base, [])
            
            def get_specific_name(item):
                if isinstance(item, dict) and '_class' in item:
                    cls_name = item['_class']
                    name = cls_name.split('_', 1)[-1]
                    name = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
                    return name
                return ""

            if len(old_list) < len(new_list):
                old_ids = {i.get('m_nElementID') for i in old_list if isinstance(i, dict)}
                added = [i for i in new_list if isinstance(i, dict) and i.get('m_nElementID') not in old_ids]
                spec = get_specific_name(added[0]) + " " if added else ""
                return f"Add {spec}{friendly_base}"
            elif len(old_list) > len(new_list):
                new_ids = {i.get('m_nElementID') for i in new_list if isinstance(i, dict)}
                removed = [i for i in old_list if isinstance(i, dict) and i.get('m_nElementID') not in new_ids]
                spec = get_specific_name(removed[0]) + " " if removed else ""
                return f"Delete {spec}{friendly_base}"
            else:
                # Same length but changed: could be reorder or edit of multiple items
                if content == {base} or (len(content) >= 2 and all('.' not in k for k in content)):
                    # try to find one that moved
                    spec = ""
                    for o, n in zip(old_list, new_list):
                        if isinstance(o, dict) and isinstance(n, dict):
                            if o.get('m_nElementID') != n.get('m_nElementID'):
                                spec = get_specific_name(n) + " "
                                break
                    # Fallback to "Reorder Modifiers" if spec logic missed it or the user prefers
                    return f"Reorder {spec}{friendly_base}"

        if len(content) == 1:
            key = next(iter(content))
            
            # Check for vector components
            if '.m_Components[' in key:
                base, comp = key.split('.m_Components[')
                axis_idx = comp.split(']')[0]
                axis_map = {'0': 'X', '1': 'Y', '2': 'Z'}
                axis = axis_map.get(axis_idx, '')
                
                base_clean = base.split('.')[-1]
                base_clean = re.sub(r'^m_(?:fl|[nbsv])?', '', base_clean)
                base_clean = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', base_clean)
                
                return f"Edit {base_clean} - {axis} value"
                
            # For compound discriminators use the leaf key for a clean label
            if '.' in key:
                key = key.rsplit('.', 1)[1]
            key = re.sub(r'\[\d+\]$', '', key)
            label = re.sub(r'^m_(?:fl|[nbsv])?', '', key)
            label = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', label)
            return f"Edit {label}"
        return "Edit Properties"

    def __init__(self, document, item, old_data, new_data):
        self._diff_keys = self._changed_keys(old_data, new_data)
        super().__init__(self._label_for_keys(self._diff_keys, old_data, new_data))
        self.document = document
        self.item = item
        self.old_data = old_data
        self.new_data = new_data
        self._item_id = id(item)
        self._first_redo = True

    # QUndoCommand virtual — non-negative id enables merging
    def id(self):
        return self._MERGE_ID

    def mergeWith(self, other):
        if not isinstance(other, PropertySnapshotCommand):
            return False
        # Different item → never merge
        if self._item_id != other._item_id:
            return False
        # Do not merge structural changes (Add, Delete, Reorder, Move Up, Move Down)
        _NO_MERGE = ("Add ", "Delete ", "Reorder ", "Move Up ", "Move Down ")
        if any(self.text().startswith(p) for p in _NO_MERGE):
            return False
        if any(other.text().startswith(p) for p in _NO_MERGE):
            return False
        # Different property (or property set) → start a new history entry
        if self._diff_keys != other._diff_keys:
            return False
        self.new_data = other.new_data
        return True

    def redo(self):
        if self._first_redo:
            self._first_redo = False
            print(f"[SPE][PropertyEdit] redo: (initial apply) '{self.item.text(0)}' — {self.text()}")
            return
        print(f"[SPE][PropertyEdit] redo: '{self.item.text(0)}' — {self.text()}")
        try:
            tree = self.document.ui.tree_hierarchy_widget
            if tree.currentItem() is self.item:
                self.document._incremental_property_update(
                    self.item, self.new_data, self._diff_keys
                )
            else:
                self.item.setData(0, Qt.UserRole, fast_deepcopy(self.new_data))
                tree.setCurrentItem(self.item)
            tree.scrollToItem(self.item)
            self.document._inject_virtual_children(self.item)
        except Exception as e:
            print(f"[SPE][PropertyEdit] redo: ERROR — {e}")

    def undo(self):
        print(f"[SPE][PropertyEdit] undo: '{self.item.text(0)}' — {self.text()}")
        try:
            tree = self.document.ui.tree_hierarchy_widget
            if tree.currentItem() is self.item:
                self.document._incremental_property_update(
                    self.item, self.old_data, self._diff_keys
                )
            else:
                self.item.setData(0, Qt.UserRole, fast_deepcopy(self.old_data))
                tree.setCurrentItem(self.item)
            tree.scrollToItem(self.item)
            self.document._inject_virtual_children(self.item)
        except Exception as e:
            print(f"[SPE][PropertyEdit] undo: ERROR — {e}")

class VirtualItemSnapshotCommand(PropertySnapshotCommand):
    """PropertySnapshotCommand that re-selects the virtual row after undo/redo."""

    def __init__(self, document, item, old_data, new_data, list_key, virtual_idx):
        super().__init__(document, item, old_data, new_data)
        self._virtual_list_key = list_key
        self._virtual_idx      = virtual_idx

    def _reselect(self, target_idx):
        self.document._reselect_virtual_item(
            self.item, self._virtual_list_key, target_idx
        )

    def redo(self):
        super().redo()
        self._reselect(self._virtual_idx)

    def undo(self):
        # After undo, the index in the old_data is what matters.
        # For a Delete the old idx is still valid; for Duplicate it's original idx.
        super().undo()
        self._reselect(self._virtual_idx)


# ──────────────────────────────────────────────────────────────────────────────
# Variables Panel — full-snapshot undo (actions 21-31)
# ──────────────────────────────────────────────────────────────────────────────

class VariablesSnapshotCommand(QUndoCommand):
    """Store a serialised snapshot of all variables before and after an edit.

    On undo/redo the entire variable list is cleared and rebuilt from the stored
    snapshot, which keeps the command implementation simple and reliable.
    The first redo() is skipped because the change was already applied.

    Consecutive "Edit Variable" commands that touch the *same field* of the *same
    variable* are merged (via mergeWith) so rapid spinbox increments produce a
    single undo entry, while editing a different field always starts a new entry.
    """
    _MERGE_ID = 1002

    @staticmethod
    def _discriminator(old_state, new_state):
        """Return a frozenset identifying which variable/field changed.

        Returns None when the lists differ in length (structural change — never merge).
        """
        if len(old_state) != len(new_state):
            return None
        result = set()
        for i, (old_var, new_var) in enumerate(zip(old_state, new_state)):
            for key in set(old_var.keys()) | set(new_var.keys()):
                if old_var.get(key) != new_var.get(key):
                    if key == 'var_value':
                        ov = old_var.get('var_value') or {}
                        nv = new_var.get('var_value') or {}
                        for vk in set(ov.keys()) | set(nv.keys()):
                            if ov.get(vk) != nv.get(vk):
                                result.add(f'var_{i}.{vk}')
                    else:
                        result.add(f'var_{i}.{key}')
        return frozenset(result)

    def __init__(self, document, old_state, new_state, description="Edit Variables"):
        super().__init__(description)
        self.document = document
        self.old_state = fast_deepcopy(old_state)
        self.new_state = fast_deepcopy(new_state)
        self._disc = self._discriminator(old_state, new_state)
        self._first_redo = True

    def id(self):
        return self._MERGE_ID

    def mergeWith(self, other):
        if not isinstance(other, VariablesSnapshotCommand):
            return False
        # Only merge plain field-edits, not structural operations
        if self.text() != "Edit Variable" or other.text() != "Edit Variable":
            return False
        if self._disc is None or other._disc is None:
            return False
        if self._disc != other._disc:
            return False
        self.new_state = other.new_state
        return True

    def redo(self):
        if self._first_redo:
            self._first_redo = False
            print(f"[SPE][Variables] redo: (initial apply) {self.text()}")
            return
        print(f"[SPE][Variables] redo: {self.text()}")
        try:
            self.document._restore_variables(self.new_state)
        except Exception as e:
            print(f"[SPE][Variables] redo: ERROR — {e}")

    def undo(self):
        print(f"[SPE][Variables] undo: {self.text()}")
        try:
            self.document._restore_variables(self.old_state)
        except Exception as e:
            print(f"[SPE][Variables] undo: ERROR — {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Choices Panel — full-snapshot undo (actions 32-40)
# ──────────────────────────────────────────────────────────────────────────────

class ChoicesSnapshotCommand(QUndoCommand):
    """Store a serialised snapshot of the entire choices tree before/after an edit.

    On undo/redo the choices tree is cleared and rebuilt from the stored snapshot.
    The first redo() is skipped because the change was already applied.
    """

    def __init__(self, document, old_state, new_state, description="Edit Choices"):
        super().__init__(description)
        self.document = document
        self.old_state = fast_deepcopy(old_state)
        self.new_state = fast_deepcopy(new_state)
        self._first_redo = True

    def redo(self):
        if self._first_redo:
            self._first_redo = False
            print(f"[SPE][Choices] redo: (initial apply) {self.text()}")
            return
        print(f"[SPE][Choices] redo: {self.text()}")
        try:
            self.document._restore_choices(self.new_state)
        except Exception as e:
            print(f"[SPE][Choices] redo: ERROR — {e}")

    def undo(self):
        print(f"[SPE][Choices] undo: {self.text()}")
        try:
            self.document._restore_choices(self.old_state)
        except Exception as e:
            print(f"[SPE][Choices] undo: ERROR — {e}")
