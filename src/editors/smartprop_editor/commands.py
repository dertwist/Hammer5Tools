import copy
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget
from PySide6.QtGui import QUndoCommand
from src.widgets import HierarchyItemModel
from src.editors.smartprop_editor._common import get_ElementID_key

_log = logging.getLogger(__name__)


def _item_ctx(item):
    """Return a compact string describing a QTreeWidgetItem for debug logs."""
    if item is None:
        return "item=None"
    try:
        name = item.text(0)
    except Exception:
        name = "<unavailable>"
    try:
        data = item.data(0, Qt.UserRole) or {}
    except Exception:
        data = {}
    eid = data.get("m_nElementID", "?") if isinstance(data, dict) else "?"
    cls = data.get("_class", "?") if isinstance(data, dict) else "?"
    return f"'{name}' id={eid} class={cls}"


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
        _log.debug("[Undo/Redo][GroupElements] REDO — grouping %d item(s)", len(self._selected_order))
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
            _log.debug("[Undo/Redo][GroupElements] REDO   moving %s from parent '%s' idx=%d",
                       _item_ctx(item), old_parent.text(0) if old_parent != invisible_root else "<root>", old_index)
        for item, old_parent, old_index in sorted(self.moved_items_info, key=lambda x: (id(x[1]), x[2]), reverse=True):
            old_parent.takeChild(old_index)
        for item, _, _ in self.moved_items_info:
            self.group_element.addChild(item)
        invisible_root.addChild(self.group_element)
        self.tree.clearSelection()
        self.group_element.setSelected(True)
        self.tree.scrollToItem(self.group_element)
        _log.debug("[Undo/Redo][GroupElements] REDO done — created group id=%s",
                   group_data.get("m_nElementID", "?"))

    def undo(self):
        if self.group_element is None:
            return
        _log.debug("[Undo/Redo][GroupElements] UNDO — restoring %d item(s) from group", len(self.moved_items_info))
        try:
            invisible_root = self.tree.invisibleRootItem()
            idx = invisible_root.indexOfChild(self.group_element)
            if idx != -1:
                invisible_root.takeChild(idx)
            # Keep the group node alive while we extract its children
            self._item_refs = [self.group_element]
            for item, _, _ in reversed(self.moved_items_info):
                child_idx = self.group_element.indexOfChild(item)
                if child_idx != -1:
                    self.group_element.takeChild(child_idx)
            for item, old_parent, old_index in self.moved_items_info:
                old_parent.insertChild(old_index, item)
                _log.debug("[Undo/Redo][GroupElements] UNDO   restored %s to parent '%s' idx=%d",
                           _item_ctx(item), old_parent.text(0) if old_parent != invisible_root else "<root>", old_index)
            self.tree.clearSelection()
            for item, _, _ in self.moved_items_info:
                item.setSelected(True)
                self.tree.scrollToItem(item)
            # Keep all children and the group node alive across the undo/redo cycle
            self._item_refs = [item for item, _, _ in self.moved_items_info] + [self.group_element]
            _log.debug("[Undo/Redo][GroupElements] UNDO done")
        except (RuntimeError, ReferenceError) as e:
            import warnings
            _log.exception("[Undo/Redo][GroupElements] UNDO failed: %s", e)
            warnings.warn(f"GroupElementsCommand.undo() failed: {e}")
class PasteItemsCommand(QUndoCommand):
    def __init__(self, tree, parent, items):
        super().__init__("Paste Items")
        self.tree = tree
        self.parent = parent
        self.items = items
        self.added = []
        self._item_refs = []
    def redo(self):
        _log.debug("[Undo/Redo][PasteItems] REDO — pasting %d item(s) under %s",
                   len(self.items), _item_ctx(self.parent))
        self.added = []
        self._item_refs = []
        for item in self.items:
            self.parent.addChild(item)
            self.parent.setExpanded(True)
            self.added.append(item)
            _log.debug("[Undo/Redo][PasteItems] REDO   added %s", _item_ctx(item))
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])
        _log.debug("[Undo/Redo][PasteItems] REDO done")
    def undo(self):
        _log.debug("[Undo/Redo][PasteItems] UNDO — removing %d item(s) from %s",
                   len(self.added), _item_ctx(self.parent))
        for item in self.added:
            idx = self.parent.indexOfChild(item)
            if idx != -1:
                self.parent.takeChild(idx)
                _log.debug("[Undo/Redo][PasteItems] UNDO   removed %s at idx=%d", _item_ctx(item), idx)
        # Keep Python references alive so the C++ objects survive until redo
        self._item_refs = list(self.added)
        self.added.clear()
        _log.debug("[Undo/Redo][PasteItems] UNDO done")
class BulkModelImportCommand(QUndoCommand):
    def __init__(self, document, parent_item, items):
        super().__init__("Bulk Model Import")
        self.document = document
        self.tree = document.ui.tree_hierarchy_widget
        self.parent_item = parent_item
        self.items = items
        self.added = []
        self._item_refs = []
    def redo(self):
        _log.debug("[Undo/Redo][BulkModelImport] REDO — adding %d model(s) under %s",
                   len(self.items), _item_ctx(self.parent_item))
        self.added = []
        self._item_refs = []
        for item in self.items:
            self.parent_item.addChild(item)
            self.parent_item.setExpanded(True)
            self.added.append(item)
            _log.debug("[Undo/Redo][BulkModelImport] REDO   added %s", _item_ctx(item))
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])
        _log.debug("[Undo/Redo][BulkModelImport] REDO done")
    def undo(self):
        _log.debug("[Undo/Redo][BulkModelImport] UNDO — removing %d model(s) from %s",
                   len(self.added), _item_ctx(self.parent_item))
        for item in self.added:
            idx = self.parent_item.indexOfChild(item)
            if idx != -1:
                self.parent_item.takeChild(idx)
                _log.debug("[Undo/Redo][BulkModelImport] UNDO   removed %s at idx=%d", _item_ctx(item), idx)
        # Keep Python references alive so the C++ objects survive until redo
        self._item_refs = list(self.added)
        self.added.clear()
        _log.debug("[Undo/Redo][BulkModelImport] UNDO done")
class NewFromPresetCommand(QUndoCommand):
    def __init__(self, tree, parent, items):
        super().__init__("New From Preset")
        self.tree = tree
        self.parent = parent
        self.items = items
        self.added = []
        self._item_refs = []
    def redo(self):
        _log.debug("[Undo/Redo][NewFromPreset] REDO — adding %d item(s) under %s",
                   len(self.items), _item_ctx(self.parent))
        self.added = []
        self._item_refs = []
        for item in self.items:
            self.parent.addChild(item)
            self.parent.setExpanded(True)
            self.added.append(item)
            _log.debug("[Undo/Redo][NewFromPreset] REDO   added %s", _item_ctx(item))
        if self.items:
            self.tree.clearSelection()
            self.items[0].setSelected(True)
            self.tree.scrollToItem(self.items[0])
        _log.debug("[Undo/Redo][NewFromPreset] REDO done")
    def undo(self):
        _log.debug("[Undo/Redo][NewFromPreset] UNDO — removing %d item(s) from %s",
                   len(self.added), _item_ctx(self.parent))
        for item in self.added:
            idx = self.parent.indexOfChild(item)
            if idx != -1:
                self.parent.takeChild(idx)
                _log.debug("[Undo/Redo][NewFromPreset] UNDO   removed %s at idx=%d", _item_ctx(item), idx)
        # Keep Python references alive so the C++ objects survive until redo
        self._item_refs = list(self.added)
        self.added.clear()
        _log.debug("[Undo/Redo][NewFromPreset] UNDO done")
class PropertiesStateCommand(QUndoCommand):
    def __init__(self, document, item, before, after, description="Edit Properties"):
        super().__init__(description)
        self.document = document
        self.item = item
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        self._first_redo_done = False
        # Keep a Python reference so the item's C++ object is not garbage-collected
        self._item_ref = item
        _log.debug("[UndoStack][Properties] Pushed '%s' for %s  before_keys=%s  after_keys=%s",
                   description, _item_ctx(item),
                   sorted(before.keys()) if isinstance(before, dict) else type(before).__name__,
                   sorted(after.keys()) if isinstance(after, dict) else type(after).__name__)

    def _item_is_valid(self):
        """Check if self.item is still alive and present in the tree."""
        try:
            _ = self.item.treeWidget()
            return _ is not None
        except (RuntimeError, ReferenceError):
            return False

    def _clear_restoring_flag(self):
        """Called via QTimer.singleShot(0) to clear the undo-restore guard after
        all queued signals from newly-created widgets have been processed."""
        try:
            self.document._restoring_from_undo = False
            self.document._suppress_snapshot_sync = False
            _log.debug("[Undo/Redo][Properties] _restoring_from_undo cleared (deferred)")
        except (RuntimeError, ReferenceError):
            pass

    def _apply(self, state, direction):
        if not self._item_is_valid():
            _log.warning("[Undo/Redo][Properties] %s — item no longer valid, skipping (%s)",
                         direction, _item_ctx(self.item))
            return
        _log.debug("[Undo/Redo][Properties] %s — applying state for %s  keys=%s",
                   direction, _item_ctx(self.item),
                   sorted(state.keys()) if isinstance(state, dict) else type(state).__name__)
        # Set flag BEFORE any widget construction so all signals emitted during
        # rebuild (including deferred/queued ones still in the event queue from
        # the previous state) are suppressed.
        self.document._restoring_from_undo = True
        # Also suppress deferred snapshot sync so it does not overwrite the
        # restored baseline with widget-injected defaults.
        self.document._suppress_snapshot_sync = True
        try:
            tree = self.document.ui.tree_hierarchy_widget
            # 1. Write restored data into the tree item
            self.item.setData(0, Qt.ItemDataRole.UserRole, copy.deepcopy(state))
            # 2. Switch selection without firing currentItemChanged
            tree.blockSignals(True)
            try:
                tree.setCurrentItem(self.item)
            finally:
                tree.blockSignals(False)
            # 3. Rebuild the Properties UI directly (no signal recursion)
            self.document._rebuild_properties_for_item(self.item)
            # 4. Explicitly set the snapshot to the exact restored state so the
            #    next user edit compares against this exact baseline (not a
            #    widget-enriched variant injected by _sync_properties_snapshot_from_widgets).
            self.document._properties_snapshot = copy.deepcopy(state)
            _log.debug("[Undo/Redo][Properties] %s done for %s", direction, _item_ctx(self.item))
        except (RuntimeError, ReferenceError):
            _log.exception("[Undo/Redo][Properties] %s raised RuntimeError/ReferenceError for %s",
                           direction, _item_ctx(self.item))
            # Clear immediately on the error path — no deferred widgets to worry about
            self.document._restoring_from_undo = False
            self.document._suppress_snapshot_sync = False
            return
        # Defer clearing both flags until after the current event-loop cycle so
        # that any signals emitted by newly-created widgets during their first
        # paint/show pass are still suppressed and do NOT push a new command.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._clear_restoring_flag)

    def undo(self):
        _log.debug("[Undo/Redo][Properties] UNDO requested for %s", _item_ctx(self.item))
        self._apply(self.before, "UNDO")

    def redo(self):
        if self._first_redo_done:
            _log.debug("[Undo/Redo][Properties] REDO requested for %s", _item_ctx(self.item))
            self._apply(self.after, "REDO")
        else:
            _log.debug("[Undo/Redo][Properties] REDO skipped (initial push) for %s", _item_ctx(self.item))
        self._first_redo_done = True

    # No id() / mergeWith() — every property edit is a discrete, independent undo step.
    # Merging caused all consecutive edits to collapse into a single command (stack count=1)
    # which made multi-level undo impossible.
class ChoicesStateCommand(QUndoCommand):
    def __init__(self, document, before, after, description="Edit Choices"):
        super().__init__(description)
        self.document = document
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        self._first_redo_done = False
        _log.debug("[UndoStack][Choices] Pushed '%s'  before=%d choice(s)  after=%d choice(s)",
                   description, len(before), len(after))

    def _clear_restoring_flag(self):
        try:
            self.document._restoring_from_undo = False
            _log.debug("[Undo/Redo][Choices] _restoring_from_undo cleared (deferred)")
        except (RuntimeError, ReferenceError):
            pass

    def _apply(self, state, direction):
        _log.debug("[Undo/Redo][Choices] %s — rebuilding from %d choice(s)", direction, len(state))
        self.document._restoring_from_undo = True
        try:
            self.document._rebuild_choices_from_snapshot(state)
            _log.debug("[Undo/Redo][Choices] %s done", direction)
        except (RuntimeError, ReferenceError):
            _log.exception("[Undo/Redo][Choices] %s raised RuntimeError/ReferenceError", direction)
            self.document._restoring_from_undo = False
            return
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._clear_restoring_flag)

    def undo(self):
        _log.debug("[Undo/Redo][Choices] UNDO requested")
        self._apply(self.before, "UNDO")

    def redo(self):
        if self._first_redo_done:
            _log.debug("[Undo/Redo][Choices] REDO requested")
            self._apply(self.after, "REDO")
        else:
            _log.debug("[Undo/Redo][Choices] REDO skipped (initial push)")
        self._first_redo_done = True


class VariablesStateCommand(QUndoCommand):
    def __init__(self, document, before, after, description="Edit Variables"):
        super().__init__(description)
        self.document = document
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        self._first_redo_done = False
        _log.debug("[UndoStack][Variables] Pushed '%s'  before=%d var(s)  after=%d var(s)",
                   description, len(before), len(after))

    def _clear_restoring_flag(self):
        try:
            self.document._restoring_from_undo = False
            _log.debug("[Undo/Redo][Variables] _restoring_from_undo cleared (deferred)")
        except (RuntimeError, ReferenceError):
            pass

    def _apply(self, state, direction):
        _log.debug("[Undo/Redo][Variables] %s — rebuilding from %d var(s)", direction, len(state))
        self.document._restoring_from_undo = True
        try:
            self.document._rebuild_variables_from_snapshot(state)
            _log.debug("[Undo/Redo][Variables] %s done", direction)
        except (RuntimeError, ReferenceError):
            _log.exception("[Undo/Redo][Variables] %s raised RuntimeError/ReferenceError", direction)
            self.document._restoring_from_undo = False
            return
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._clear_restoring_flag)

    def undo(self):
        _log.debug("[Undo/Redo][Variables] UNDO requested")
        self._apply(self.before, "UNDO")

    def redo(self):
        if self._first_redo_done:
            _log.debug("[Undo/Redo][Variables] REDO requested")
            self._apply(self.after, "REDO")
        else:
            _log.debug("[Undo/Redo][Variables] REDO skipped (initial push)")
        self._first_redo_done = True
