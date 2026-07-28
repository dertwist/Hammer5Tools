"""
Offscreen verification script for Phase P4 (PropertyTreeView & PropertyPanel).
"""

import sys
import os
import time

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

from src.editors.smartprop_editor.props.model import PropertyTreeModel, ComponentRef, DEFAULT, MIXED
from src.editors.smartprop_editor.props.view import PropertyPanel
from src.editors.smartprop_editor.props import schema


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

    # 20+ field component data (PlaceInSphere)
    data = {
        "_class": "CSmartPropElement_PlaceInSphere",
        "m_bEnabled": True,
        "m_flRandomness": 0.5,
        "m_nCountMin": 1,
        "m_nCountMax": 10,
        "m_flPositionRadiusInner": 10.0,
        "m_flPositionRadiusOuter": 100.0,
        "m_bAlignOrientation": True,
        "m_PlacementMode": "SPHERE",
        "m_DistributionMode": "RANDOM",
        "m_vAlignDirection": [0.0, 0.0, 1.0],
        "m_vPlaneUpDirection": [0.0, 1.0, 0.0],
    }

    item = QTreeWidgetItem()
    item.setData(0, Qt.UserRole, data)

    doc = DummyDocument(item)
    panel = PropertyPanel(document=doc)

    ref = ComponentRef(item, "element", -1)

    # 1. Performance check: measure render time for 20-field component.
    # Always-visible editors (one full editor widget per row, matching the
    # legacy property panel) cost more than the painted-cell tree view, so the
    # threshold is generous; variable pickers are built lazily on first use.
    render_time_ms = panel.set_components([ref])
    print(f"[PERF] 20-field component render time: {render_time_ms:.2f} ms")
    assert render_time_ms <= 200.0, f"Render time {render_time_ms:.2f} ms exceeded 200ms threshold!"

    # 1b. Always-visible contract: every value cell has a persistent editor open.
    open_count = sum(
        1 for r in range(panel.proxy_model.rowCount())
        if panel.tree_view.isPersistentEditorOpen(panel.proxy_model.index(r, 1))
    )
    assert open_count == panel.proxy_model.rowCount(), \
        f"Expected {panel.proxy_model.rowCount()} open editors, got {open_count}"
    print(f"[PASS] {open_count} always-visible editors opened")

    # 2. Filter test: filter box narrows rows live
    model = panel.tree_model
    proxy = panel.proxy_model
    total_rows = proxy.rowCount()
    assert total_rows > 0

    panel.txt_filter.setText("Radius")
    filtered_rows = proxy.rowCount()
    assert 0 < filtered_rows < total_rows
    print(f"[PASS] Filter narrowed rows from {total_rows} to {filtered_rows}")

    panel.txt_filter.clear()
    assert proxy.rowCount() == total_rows
    print("[PASS] Clear filter restored full row count")

    # 3. Edit through model/view
    original_radius = item.data(0, Qt.UserRole).get("m_flPositionRadiusOuter")
    model.set_field("m_flPositionRadiusOuter", 250.0)
    updated_radius = item.data(0, Qt.UserRole).get("m_flPositionRadiusOuter")
    assert updated_radius == 250.0
    print("[PASS] Edit field written through to tree item data")

    # 4. Undo edit
    doc.undo_stack.undo()
    restored_radius = item.data(0, Qt.UserRole).get("m_flPositionRadiusOuter")
    assert restored_radius == original_radius
    print("[PASS] Undo restored original field value")

    # 5. DEFAULT mode removes key from dict
    model.set_field("m_flRandomness", DEFAULT)
    assert "m_flRandomness" not in item.data(0, Qt.UserRole)
    print("[PASS] DEFAULT sentinel removed key from saved dict")

    doc.undo_stack.undo()
    assert "m_flRandomness" in item.data(0, Qt.UserRole)
    print("[PASS] Undo restored deleted DEFAULT key")

    print("\nALL P4 ASSERTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
