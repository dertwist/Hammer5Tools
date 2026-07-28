"""
Offscreen verification script for ComponentList (Section 1 of the SmartProp
property editor), now backed by HierarchyTreeWidget(list_mode=True) for the
modifiers/selection-criteria lists instead of a bespoke widget-per-row layout.
"""

import sys
import os

# Ensure repo root and src directory are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(root_dir, "src")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from PySide6.QtWidgets import QApplication, QTreeWidgetItem
from PySide6.QtGui import QUndoStack
from PySide6.QtCore import Qt

from src.editors.smartprop_editor.props.components import ComponentList, CLIPBOARD_PREFIX
from src.editors.smartprop_editor.props.model import ComponentRef
from src.common import fast_deepcopy


class MockUI:
    def __init__(self, current_item):
        self.tree_hierarchy_widget = MockTreeWidget(current_item)

class MockTreeWidget:
    def __init__(self, current_item):
        self._current_item = current_item
    def currentItem(self):
        return self._current_item
    def setCurrentItem(self, item):
        self._current_item = item
    def scrollToItem(self, item):
        pass

class DummyDocument:
    def __init__(self, item=None):
        self.undo_stack = QUndoStack()
        self.ui = MockUI(item)

    def apply_property_data(self, item, new_data, changed_keys):
        item.setData(0, Qt.UserRole, new_data)

    def apply_external_data(self, item, new_data, changed_keys):
        item.setData(0, Qt.UserRole, new_data)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    # Initial data dict with 1 element, 2 modifiers, 1 criterion. Every real
    # component carries m_nElementID (assigned by ElementIDGenerator) — without
    # it, PropertySnapshotCommand's diff can't tell "item moved" from "content
    # replaced" at that index, mislabels reorders, and wrongly merges them with
    # adjacent edits. Match real data shape so undo/redo below behaves as it
    # would in the app.
    initial_data = {
        "_class": "CSmartPropElement_PlaceOnPath",
        "m_bEnabled": True,
        "m_PathName": "test_path",
        "m_nElementID": 1,
        "m_Modifiers": [
            {"_class": "CSmartPropOperation_RandomScale", "m_bEnabled": True, "m_flRandomScaleMin": 0.5, "m_flRandomScaleMax": 1.5, "m_nElementID": 2},
            {"_class": "CSmartPropOperation_Rotate", "m_bEnabled": True, "m_vRotation": [0, 90, 0], "m_nElementID": 3},
        ],
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_ChoiceWeight", "m_bEnabled": True, "m_flWeight": 0.8, "m_nElementID": 4},
        ],
    }

    item = QTreeWidgetItem()
    item.setData(0, Qt.UserRole, initial_data)

    doc = DummyDocument(item)
    widget = ComponentList(document=doc)

    emitted_refs = []
    widget.componentSelected.connect(lambda ref: emitted_refs.append(ref))

    # 1. Test set_element: select element by default
    widget.set_element(item)
    assert len(emitted_refs) >= 1
    assert emitted_refs[-1] == ComponentRef(item, "element", -1)
    assert widget.selected_refs() == [ComponentRef(item, "element", -1)]
    print("[PASS] set_element defaults to element ref (Row 0)")

    # 2. Test selecting a modifier row (native QTreeWidgetItem selection)
    mod0_item = widget.modifiers_tree.topLevelItem(0)
    assert mod0_item.data(0, Qt.UserRole) == ComponentRef(item, "modifier", 0)
    widget.modifiers_tree.setCurrentItem(mod0_item)
    mod0_item.setSelected(True)
    assert emitted_refs[-1] == ComponentRef(item, "modifier", 0)
    assert widget.selected_refs() == [ComponentRef(item, "modifier", 0)]
    print("[PASS] Select modifier ref emits ComponentRef(item, 'modifier', 0)")

    # 3. Test selecting the criterion row
    crit0_item = widget.criteria_tree.topLevelItem(0)
    assert crit0_item.data(0, Qt.UserRole) == ComponentRef(item, "criterion", 0)
    widget.criteria_tree.setCurrentItem(crit0_item)
    crit0_item.setSelected(True)
    assert emitted_refs[-1] == ComponentRef(item, "criterion", 0)
    assert widget.selected_refs() == [ComponentRef(item, "criterion", 0)]
    # Selecting in one tree clears the other selection surfaces.
    assert not widget.elem_row.is_selected()
    assert not widget.modifiers_tree.selectedItems()
    print("[PASS] Select criterion ref emits ComponentRef(item, 'criterion', 0); clears other surfaces")

    # 4. Test the direct single-move reorder API (_reorder_component)
    widget._reorder_component("modifier", 0, 1)
    data = item.data(0, Qt.UserRole)
    assert data["m_Modifiers"][0]["_class"] == "CSmartPropOperation_Rotate"
    assert data["m_Modifiers"][1]["_class"] == "CSmartPropOperation_RandomScale"
    print("[PASS] Reorder modifiers updates list in item data")

    doc.undo_stack.undo()
    data = item.data(0, Qt.UserRole)
    assert data["m_Modifiers"][0]["_class"] == "CSmartPropOperation_RandomScale"
    print("[PASS] Reorder undo restores original modifier list order")

    doc.undo_stack.redo()
    data = item.data(0, Qt.UserRole)
    assert data["m_Modifiers"][0]["_class"] == "CSmartPropOperation_Rotate"
    print("[PASS] Reorder redo re-applies reorder")

    # 4b. Reconciliation path used after a real drag-drop: ComponentTree.reordered
    # fires once HierarchyTreeWidget's own (native, Qt-trusted) InternalMove drop
    # has already reordered the visible QTreeWidgetItems; ComponentList reads that
    # order back via _apply_tree_order and writes it into m_Modifiers. Simulate the
    # "already reordered visually" state directly (real native drag-and-drop isn't
    # simulable headlessly) and confirm the reconciliation is correct.
    tree = widget.modifiers_tree
    assert [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())] == ["Rotate", "Random Scale"]
    moved = tree.takeTopLevelItem(0)
    tree.addTopLevelItem(moved)  # visually: Random Scale, Rotate
    widget._on_modifiers_reordered()
    data = item.data(0, Qt.UserRole)
    assert data["m_Modifiers"][0]["_class"] == "CSmartPropOperation_RandomScale"
    assert data["m_Modifiers"][1]["_class"] == "CSmartPropOperation_Rotate"
    print("[PASS] ComponentTree.reordered -> _apply_tree_order writes the new visual order into m_Modifiers")

    doc.undo_stack.undo()  # restore [Rotate, RandomScale] so step 5 below deletes the expected item
    widget.rebuild()  # sync the tree's visual state — DummyDocument.apply_property_data doesn't, unlike the real app
    data = item.data(0, Qt.UserRole)
    assert data["m_Modifiers"][0]["_class"] == "CSmartPropOperation_Rotate"

    # 4c. Regression: reordering after an unrelated Section-2 property edit must
    # not revert that edit. Section 2 (LegacyPropertyList._commit_frame /
    # PropertyTreeModel.set_field) writes straight to item.data() and does *not*
    # call ComponentList.rebuild() (by design, to avoid rebuilding this tree on
    # every keystroke) — so _apply_tree_order used to read each item's *cached*
    # value snapshot from populate time, which had gone stale the moment the
    # user edited a property, silently discarding that edit on the next reorder.
    live = fast_deepcopy(item.data(0, Qt.UserRole))
    live["m_Modifiers"][1]["m_flRandomScaleMin"] = 9.9  # edit RandomScale (idx1) via "Section 2", no rebuild()
    item.setData(0, Qt.UserRole, live)
    assert widget.modifiers_tree.topLevelItem(1).text(0) == "Random Scale"  # tree item still stale-looking, as expected

    moved = widget.modifiers_tree.takeTopLevelItem(0)  # drag Rotate (idx0) to the end
    widget.modifiers_tree.addTopLevelItem(moved)
    widget._on_modifiers_reordered()

    data = item.data(0, Qt.UserRole)
    assert data["m_Modifiers"][0]["_class"] == "CSmartPropOperation_RandomScale"
    assert data["m_Modifiers"][0]["m_flRandomScaleMin"] == 9.9, "the Section-2 edit must survive a reorder"
    print("[PASS] Reordering after a Section-2 property edit preserves that edit (no silent revert)")

    # Undo only reverts the reorder itself — the direct item.setData() edit above
    # never went through the undo stack (same as a real Section-2 edit mid-drag
    # wouldn't yet), so m_flRandomScaleMin stays 9.9 here; only order is restored.
    doc.undo_stack.undo()  # restore [Rotate, RandomScale] order so step 5 below deletes the expected item
    data = item.data(0, Qt.UserRole)
    assert data["m_Modifiers"][0]["_class"] == "CSmartPropOperation_Rotate"

    # 5. Test deleting component
    widget._on_delete_component(ComponentRef(item, "modifier", 0))
    data = item.data(0, Qt.UserRole)
    assert len(data["m_Modifiers"]) == 1
    print("[PASS] Delete modifier removes item from list")

    doc.undo_stack.undo()
    data = item.data(0, Qt.UserRole)
    assert len(data["m_Modifiers"]) == 2
    print("[PASS] Delete modifier undo restores deleted item")

    # 5b. Batch delete (multi-select Delete key path: ComponentTree.deleteRequested)
    widget.rebuild()
    mod_items = [widget.modifiers_tree.topLevelItem(i) for i in range(widget.modifiers_tree.topLevelItemCount())]
    assert len(mod_items) == 2
    widget._on_modifiers_delete_requested(mod_items)
    data = item.data(0, Qt.UserRole)
    assert len(data["m_Modifiers"]) == 0
    print("[PASS] Multi-select delete (deleteRequested) removes all requested modifiers in one undo step")

    doc.undo_stack.undo()
    data = item.data(0, Qt.UserRole)
    assert len(data["m_Modifiers"]) == 2
    print("[PASS] Batch delete undo restores both deleted items")

    # 6. Test Copy / Paste
    clip_str = f"{CLIPBOARD_PREFIX};;CSmartPropOperation_Scale;;{{'_class': 'CSmartPropOperation_Scale', 'm_flScale': 2.0}};;modifier"
    QApplication.clipboard().setText(clip_str)
    widget._on_paste_modifier()
    data = item.data(0, Qt.UserRole)
    assert len(data["m_Modifiers"]) == 3
    assert data["m_Modifiers"][-1]["_class"] == "CSmartPropOperation_Scale"
    print("[PASS] Paste modifier adds new modifier from clipboard")

    doc.undo_stack.undo()
    data = item.data(0, Qt.UserRole)
    assert len(data["m_Modifiers"]) == 2
    print("[PASS] Paste modifier undo removes pasted item")

    # 7. list_mode disables nesting: HierarchyTreeWidget's own contract.
    assert widget.modifiers_tree.list_mode is True
    assert widget.criteria_tree.list_mode is True
    assert widget.modifiers_tree.rootIsDecorated() is False
    print("[PASS] Modifier/criteria trees are list_mode with no expand decoration (children disabled)")

    # 8. Regression: a real drop delivers the drag-and-drop machinery's cleanup
    # in the same call stack as ComponentTree.dropEvent. ComponentTree used to
    # emit `reordered` synchronously, which triggers ComponentList.rebuild() ->
    # tree.clear(), destroying QTreeWidgetItems mid-cleanup and crashing. It's
    # now deferred via QTimer.singleShot(0, ...) — confirm dropEvent itself
    # doesn't touch the data synchronously, and that the deferred call still
    # lands once the event loop gets a turn.
    widget.rebuild()
    tree = widget.modifiers_tree
    from PySide6.QtCore import QMimeData
    from PySide6.QtGui import QDropEvent
    target_rect = tree.visualItemRect(tree.topLevelItem(1))
    ev = QDropEvent(target_rect.center(), Qt.MoveAction, QMimeData(), Qt.LeftButton, Qt.NoModifier)
    before_reorder_data = item.data(0, Qt.UserRole)
    tree.dropEvent(ev)  # must not raise, must not mutate data synchronously
    assert item.data(0, Qt.UserRole) is before_reorder_data or item.data(0, Qt.UserRole) == before_reorder_data
    for _ in range(5):
        app.processEvents()  # flush the deferred QTimer.singleShot(0, ...)
    print("[PASS] dropEvent's reconciliation is deferred a tick, not synchronous (crash regression)")

    # 9. Regression: wheel events over a (scrollbar-disabled) component tree
    # must reach the outer ComponentList scroll area instead of being eaten —
    # ignore()'ing a QWheelEvent does *not* auto-propagate to the parent the
    # way it does for mouse events, so ComponentTree.wheelEvent forwards it
    # explicitly to the nearest QScrollArea ancestor's viewport.
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent

    many_mods = [
        {"_class": "CSmartPropOperation_Scale", "m_bEnabled": True, "m_flScale": float(i), "m_nElementID": 100 + i}
        for i in range(30)
    ]
    big_item = QTreeWidgetItem()
    big_item.setData(0, Qt.UserRole, {
        "_class": "CSmartPropElement_Group", "m_bEnabled": True, "m_nElementID": 99,
        "m_Modifiers": many_mods, "m_SelectionCriteria": [],
    })
    big_doc = DummyDocument(big_item)
    big_widget = ComponentList(document=big_doc)
    big_widget.resize(400, 250)  # deliberately small: 30 rows overflow the visible area
    big_widget.show()
    big_widget.set_element(big_item)
    app.processEvents()

    sb = big_widget.scroll_area.verticalScrollBar()
    assert sb.maximum() > 0, "test setup sanity: 30 modifiers must overflow the scroll area"
    before_scroll = sb.value()
    pos = big_widget.modifiers_tree.viewport().rect().center()
    wheel_ev = QWheelEvent(
        QPointF(pos), QPointF(big_widget.modifiers_tree.viewport().mapToGlobal(pos)),
        QPoint(0, 0), QPoint(0, -240), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False,
    )
    QApplication.sendEvent(big_widget.modifiers_tree.viewport(), wheel_ev)
    app.processEvents()
    assert sb.value() != before_scroll, "wheel over the component tree should scroll the outer panel"
    print("[PASS] Wheel events over a component tree scroll the outer ComponentList, not eaten by the tree")

    # 11. Regression: the last row sometimes visually vanished after a
    # same-item-count content refresh (e.g. a reorder) because
    # setFixedHeight() computes the *same* value it already had, so it's a
    # no-op — no resize event, no implicit repaint — even though clear() +
    # re-adding items just changed what's actually on screen. Moving or
    # selecting another row happened to force a repaint that fixed it, which
    # is exactly the "disappears until you interact with something else"
    # symptom reported. refresh_height() must force the relayout/repaint
    # itself rather than depending on an incidental later interaction.
    calls = {"layout": 0, "update": 0}
    tree = widget.modifiers_tree
    orig_layout = tree.doItemsLayout
    orig_update = tree.viewport().update
    tree.doItemsLayout = lambda: (calls.__setitem__("layout", calls["layout"] + 1), orig_layout())[-1]
    tree.viewport().update = lambda *a: (calls.__setitem__("update", calls["update"] + 1), orig_update(*a))[-1]
    tree.refresh_height()
    assert calls["layout"] >= 1 and calls["update"] >= 1, \
        "refresh_height() must force doItemsLayout()+viewport().update(), not rely on an implicit resize repaint"
    print("[PASS] refresh_height() forces an explicit relayout + repaint every time, not just on height change")

    # 12. Regression: ComponentList.sizeHint() used to cap out at
    # ComponentTree.ROW_H*16+MARGIN regardless of actual content, and even
    # after that cap was removed it silently summed each ComponentTree's
    # *default* QTreeWidget sizeHint() (unrelated to the fixed height
    # refresh_height() actually sets) instead of its real height — so the
    # reported size barely changed with content at all. It must now grow
    # roughly linearly with modifier count, matching the property panel's own
    # "expand to fit content" treatment instead of being capped or flat.
    from PySide6.QtWidgets import QWidget as _QWidget

    def _sizehint_for(n_mods):
        w_mods = [
            {"_class": "CSmartPropOperation_Scale", "m_bEnabled": True, "m_flScale": float(i), "m_nElementID": i + 2}
            for i in range(n_mods)
        ]
        w_item = QTreeWidgetItem()
        w_item.setData(0, Qt.UserRole, {
            "_class": "CSmartPropElement_Group", "m_bEnabled": True, "m_nElementID": 1,
            "m_Modifiers": w_mods, "m_SelectionCriteria": [],
        })
        w_doc = DummyDocument(w_item)
        w_cl = ComponentList(document=w_doc)
        host = _QWidget()
        from PySide6.QtWidgets import QVBoxLayout as _QVBoxLayout
        _QVBoxLayout(host).addWidget(w_cl)
        host.resize(400, 2000)
        host.show()
        w_cl.set_element(w_item)
        app.processEvents()
        app.processEvents()
        return w_cl.sizeHint().height()

    h_empty = _sizehint_for(0)
    h_16 = _sizehint_for(16)
    h_25 = _sizehint_for(25)
    old_cap = 26 * 16 + 6  # ComponentTree.ROW_H * 16 + old MARGIN cap
    assert h_16 > old_cap, f"sizeHint must exceed the old hard cap ({old_cap}), got {h_16}"
    assert h_25 > h_16 > h_empty, "sizeHint must grow with content, not stay flat"
    print(f"[PASS] ComponentList.sizeHint() scales with content (0={h_empty}, 16={h_16}, 25={h_25}), no longer capped")

    print("\nALL P3 ASSERTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
