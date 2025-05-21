import pytest
from PySide6.QtWidgets import QApplication, QTreeWidgetItem
from PySide6.QtCore import Qt, QPointF
from dev.widgets.tree_widget import CustomTreeWidget, MoveItemCommand

@pytest.fixture(scope="session")
def qapp():
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

def serialize_tree(tree):
    def serialize_item(item):
        return {
            "text": item.text(0),
            "children": [serialize_item(item.child(i)) for i in range(item.childCount())]
        }
    return [
        serialize_item(tree.topLevelItem(i))
        for i in range(tree.topLevelItemCount())
    ]

def setup_tree():
    # Build the tree as described
    tree = CustomTreeWidget(undo_stack=type("DummyStack", (), {"push": lambda self, cmd: cmd.redo()})())
    parent1 = QTreeWidgetItem(["Parent1"])
    child1 = QTreeWidgetItem(["child1"])
    child2 = QTreeWidgetItem(["child2"])
    child3 = QTreeWidgetItem(["child3"])
    parent1.addChildren([child1, child2, child3])
    parent2 = QTreeWidgetItem(["Parent2"])
    child4 = QTreeWidgetItem(["child4"])
    parent2.addChild(child4)
    tree.addTopLevelItems([parent1, parent2])
    return tree, parent1, child1, child2, child3, parent2, child4

def test_drag_and_drop_and_undo(qapp):
    # Use a real QUndoStack for undo/redo
    from PySide6.QtGui import QUndoStack
    tree = CustomTreeWidget(undo_stack=QUndoStack())
    parent1 = QTreeWidgetItem(["Parent1"])
    child1 = QTreeWidgetItem(["child1"])
    child2 = QTreeWidgetItem(["child2"])
    child3 = QTreeWidgetItem(["child3"])
    parent1.addChildren([child1, child2, child3])
    parent2 = QTreeWidgetItem(["Parent2"])
    child4 = QTreeWidgetItem(["child4"])
    parent2.addChild(child4)
    tree.addTopLevelItems([parent1, parent2])

    # Save initial state
    initial_state = serialize_tree(tree)

    # 1. Move child1 under child4
    old_parent = parent1
    old_index = old_parent.indexOfChild(child1)
    new_parent = child4
    new_index = child4.childCount()
    tree.undo_stack.push(MoveItemCommand(tree, child1, old_parent, old_index, new_parent, new_index))

    # 2. Move child2 to root (as first top-level item)
    old_parent = parent1
    old_index = old_parent.indexOfChild(child2)
    new_parent = None
    new_index = 0
    tree.undo_stack.push(MoveItemCommand(tree, child2, old_parent, old_index, new_parent, new_index))

    # 3. Move parent1 under child1
    old_parent = None
    old_index = tree.indexOfTopLevelItem(parent1)
    new_parent = child1
    new_index = child1.childCount()
    tree.undo_stack.push(MoveItemCommand(tree, parent1, old_parent, old_index, new_parent, new_index))

    # 4. Move parent2 under child2
    old_parent = None
    old_index = tree.indexOfTopLevelItem(parent2)
    new_parent = child2
    new_index = child2.childCount()
    tree.undo_stack.push(MoveItemCommand(tree, parent2, old_parent, old_index, new_parent, new_index))

    # Now undo all operations
    for _ in range(tree.undo_stack.count()):
        tree.undo_stack.undo()

    # Compare state after undo to initial state
    final_state = serialize_tree(tree)
    assert final_state == initial_state, f"Tree structure after undo does not match initial structure.\nInitial: {initial_state}\nFinal: {final_state}"
