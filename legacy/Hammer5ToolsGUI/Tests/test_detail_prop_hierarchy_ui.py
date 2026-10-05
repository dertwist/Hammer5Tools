"""Test hierarchy tree styling and configuration in Detail Prop Editor."""
import os
import sys
import pytest
from PySide6.QtWidgets import QApplication, QHeaderView

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
gui_root = os.path.join(repo_root, "Hammer5ToolsGUI")
if gui_root not in sys.path:
    sys.path.insert(0, gui_root)

app = QApplication.instance() or QApplication(sys.argv)

from gui.forms.detail_prop_editor.hierarchy import DetailPropTree, _DropSignalTree
from gui.widgets.tree import HierarchyTreeWidget


def test_detail_prop_tree_inherits_hierarchy_tree_widget():
    tree = _DropSignalTree()
    assert isinstance(tree, HierarchyTreeWidget)
    assert tree.property("h5Component") == "hierarchyTree"
    assert tree.indentation() == 18


def test_detail_prop_tree_widget_setup():
    dp_tree = DetailPropTree()
    assert dp_tree.search_bar.height() == 24 or dp_tree.search_bar.maximumHeight() == 24
    assert dp_tree.search_bar.placeholderText() == "Filter..."
    assert dp_tree.tree.alternatingRowColors() is True
    assert dp_tree.tree.property("h5Component") == "hierarchyTree"
    assert dp_tree.tree.header().sectionResizeMode(0) == QHeaderView.ResizeToContents
    assert dp_tree.tree.header().sectionResizeMode(2) == QHeaderView.ResizeToContents
    dp_tree.deleteLater()
