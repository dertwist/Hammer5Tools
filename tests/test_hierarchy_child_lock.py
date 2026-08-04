"""
Soft lock: Model / SmartProp hierarchy items are leaf-only (m_Children must stay empty).

Covers the two pieces added for this: the drop-disabled flag + error-badge/tooltip on
HierarchyItemModel (src/widgets/widgets.py), and the AddItem() parent redirect on
HierarchyTreeWidget (src/widgets/tree.py) that keeps a new element from being parented
onto a selected Model/SmartProp.
"""

import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(root_dir, "src")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QUndoStack
from PySide6.QtCore import Qt

import resources_rc  # noqa: F401 — registers the ":/icons/..." Qt resource paths

from src.widgets.widgets import HierarchyItemModel
from src.widgets.tree import HierarchyTreeWidget


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    # ── flags: Model/SmartProp refuse drops, everything else accepts them ──
    model_item = HierarchyItemModel(_name="a_model", _class="Model")
    assert not (model_item.flags() & Qt.ItemIsDropEnabled)
    smartprop_item = HierarchyItemModel(_name="a_prop", _class="SmartProp")
    assert not (smartprop_item.flags() & Qt.ItemIsDropEnabled)
    group_item = HierarchyItemModel(_name="a_group", _class="Group")
    assert group_item.flags() & Qt.ItemIsDropEnabled
    print("[PASS] Model/SmartProp clear ItemIsDropEnabled; other classes keep it")

    # ── violation flagging: only true once a child actually exists ──
    assert model_item.violates_child_lock() is False
    child = HierarchyItemModel(_name="child", _class="Group")
    model_item.addChild(child)
    assert model_item.violates_child_lock() is True
    assert group_item.violates_child_lock() is False, "non-leaf classes never violate"

    icon = model_item.data(0, Qt.DecorationRole)
    assert icon is not None and not icon.isNull()
    tooltip = model_item.data(0, Qt.ToolTipRole)
    assert tooltip == "Models and Smartprop elements cannot have any child elements."
    print("[PASS] violating item gets a composited icon + explanatory tooltip")

    # ── AddItem redirects onto a Model to beside it instead ──
    undo_stack = QUndoStack()
    tree = HierarchyTreeWidget(undo_stack)
    top_model = HierarchyItemModel(_name="top_model", _class="Model")
    tree.addTopLevelItem(top_model)
    tree.setCurrentItem(top_model)

    new_item = HierarchyItemModel(_name="new_element", _class="Group")
    tree.AddItem(new_item)
    assert new_item.parent() is None, "should land beside the Model, i.e. top-level"
    assert tree.indexOfTopLevelItem(new_item) != -1
    assert top_model.childCount() == 0, "Model must stay childless"
    print("[PASS] AddItem() with a Model selected adds a sibling, not a child")

    # ── AddItem still parents normally under a non-locked item ──
    tree.setCurrentItem(top_model)  # reselect since AddItem() moved current to new_item
    tree.setCurrentItem(new_item)
    another = HierarchyItemModel(_name="nested", _class="Group")
    tree.AddItem(another)
    assert another.parent() is new_item
    print("[PASS] AddItem() still nests under items that allow children")

    print("\nALL hierarchy child-lock ASSERTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
