"""
Verification script for Phases P5-P8.
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

from src.editors.smartprop_editor.props.panel import SmartPropPropertyPanel
from src.editors.smartprop_editor.props.model import ComponentRef, MIXED, DEFAULT
from src.editors.smartprop_editor.props.help import HelpPanel
from src.editors.smartprop_editor.props.view import is_field_visible_for_layout2dgrid


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

    # 1. P5: Test Layout2DGrid visibility predicate
    grid_segment = {"_class": "CSmartPropElement_Layout2DGrid", "m_GridArrangement": "SEGMENT", "m_bAlternateShift": False}
    assert is_field_visible_for_layout2dgrid("m_nCountW", grid_segment) is True
    assert is_field_visible_for_layout2dgrid("m_flSpacingWidth", grid_segment) is False
    assert is_field_visible_for_layout2dgrid("m_flAlternateShiftWidth", grid_segment) is False

    grid_segment_alt = {"_class": "CSmartPropElement_Layout2DGrid", "m_GridArrangement": "SEGMENT", "m_bAlternateShift": True}
    assert is_field_visible_for_layout2dgrid("m_flAlternateShiftWidth", grid_segment_alt) is True

    grid_fill = {"_class": "CSmartPropElement_Layout2DGrid", "m_GridArrangement": "FILL"}
    assert is_field_visible_for_layout2dgrid("m_flSpacingWidth", grid_fill) is True
    assert is_field_visible_for_layout2dgrid("m_nCountW", grid_fill) is False
    print("[PASS] P5: Layout2DGrid visibility predicate verified")

    # 2. P5: Test HelpPanel updating
    help_panel = HelpPanel()
    help_panel.set_component_help(ComponentRef(None, "element", -1))
    # Browser should have some HTML content after set_component_help (title in span)
    assert len(help_panel.browser.toHtml()) > 200
    print("[PASS] P5: HelpPanel component help text verified")

    # 3. P6: Test SmartPropPropertyPanel integration
    elem_data = {
        "_class": "CSmartPropElement_Group",
        "m_bEnabled": True,
        "m_Modifiers": [
            {"_class": "CSmartPropOperation_Scale", "m_bEnabled": True, "m_flScale": 1.0},
            {"_class": "CSmartPropOperation_Scale", "m_bEnabled": True, "m_flScale": 2.0},
            {"_class": "CSmartPropOperation_Scale", "m_bEnabled": True, "m_flScale": 3.0},
        ],
        "m_SelectionCriteria": [],
    }

    item = QTreeWidgetItem()
    item.setData(0, Qt.UserRole, elem_data)

    doc = DummyDocument(item)
    panel = SmartPropPropertyPanel(document=doc)
    panel.set_element(item)

    cl = panel.components_list
    assert cl.elem_row.ref.kind == "element"
    assert cl.modifiers_tree.topLevelItemCount() == 3
    assert cl.criteria_tree.topLevelItemCount() == 0
    print("[PASS] P6: SmartPropPropertyPanel section 1 populated")

    # 4. P8: Multi-selection test across 3 same-class modifiers
    refs = [
        ComponentRef(item, "modifier", 0),
        ComponentRef(item, "modifier", 1),
        ComponentRef(item, "modifier", 2),
    ]

    panel.components_list._selected_refs = list(refs)
    panel.property_panel.set_components(refs)

    model = panel.property_panel.tree_model
    scale_idx = model.index(1, 1)  # m_flScale column
    assert model.data(scale_idx, Qt.EditRole) is MIXED
    assert model.data(scale_idx, Qt.DisplayRole) == "—"
    print("[PASS] P8: Multi-selection differing values render as MIXED ('—')")

    # Perform single edit across all 3 selected components
    model.set_field("m_flScale", 5.0)
    data_after = item.data(0, Qt.UserRole)
    assert data_after["m_Modifiers"][0]["m_flScale"] == 5.0
    assert data_after["m_Modifiers"][1]["m_flScale"] == 5.0
    assert data_after["m_Modifiers"][2]["m_flScale"] == 5.0
    print("[PASS] P8: Multi-selection edit writes concrete value to all selected components")

    # Single undo reverts all 3 selected components
    doc.undo_stack.undo()
    data_reverted = item.data(0, Qt.UserRole)
    assert data_reverted["m_Modifiers"][0]["m_flScale"] == 1.0
    assert data_reverted["m_Modifiers"][1]["m_flScale"] == 2.0
    assert data_reverted["m_Modifiers"][2]["m_flScale"] == 3.0
    print("[PASS] P8: Single undo reverts multi-component edit across all selected components")

    # 6. Test properties_groups_show / properties_groups_hide toggle properties_spacer
    class MockWidget:
        def __init__(self): self.visible = False
        def show(self): self.visible = True
        def hide(self): self.visible = False
        def isVisible(self): return self.visible

    class MockUIWithSpacer:
        def __init__(self):
            self.properties_placeholder = MockWidget()
            self.properties_spacer = MockWidget()

    doc.ui = MockUIWithSpacer()
    # Import document class properties_groups_show / hide functions
    from src.editors.smartprop_editor.document import SmartPropDocument
    SmartPropDocument.properties_groups_show(doc)
    assert not doc.ui.properties_placeholder.isVisible()
    assert not doc.ui.properties_spacer.isVisible()
    SmartPropDocument.properties_groups_hide(doc)
    assert doc.ui.properties_placeholder.isVisible()
    assert not doc.ui.properties_spacer.isVisible()
    # 7. Test update_property_frame_values / _incremental_property_update without PropertyFrame NameError
    doc.ui.tree_hierarchy_widget = MockTreeWidget(item)
    doc.property_panel = panel
    SmartPropDocument.update_property_frame_values(doc, elem_data, ("m_bEnabled",))
    SmartPropDocument._incremental_property_update(doc, item, elem_data, ("m_bEnabled",))
    print("[PASS] update_property_frame_values / _incremental_property_update executed without error")

    print("\nALL P5-P8 ASSERTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
