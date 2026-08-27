"""Characterization tests for hierarchy drag/undo model synchronization."""

from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication, QTreeWidgetItem

from gui.widgets.commands import MoveItemsCommand
from gui.widgets.tree import HierarchyTreeWidget


def _app():
    return QApplication.instance() or QApplication([])


def _labels(tree):
    return [tree.topLevelItem(index).text(0) for index in range(tree.topLevelItemCount())]


def test_move_and_undo_notify_model_after_final_tree_order():
    _app()
    stack = QUndoStack()
    tree = HierarchyTreeWidget(stack)
    first = QTreeWidgetItem(["first"])
    second = QTreeWidgetItem(["second"])
    tree.addTopLevelItems([first, second])
    observed = []
    tree.structure_changed = lambda: observed.append(_labels(tree))

    # QTreeWidget has already performed the drop when MoveItemsCommand is pushed.
    tree.takeTopLevelItem(0)
    tree.insertTopLevelItem(1, first)
    stack.push(MoveItemsCommand(tree, [{
        "item": first,
        "old_parent": None,
        "old_index": 0,
        "new_parent": None,
        "new_index": 1,
    }]))

    assert observed[-1] == ["second", "first"]
    stack.undo()
    assert observed[-1] == ["first", "second"]
    stack.redo()
    assert observed[-1] == ["second", "first"]

