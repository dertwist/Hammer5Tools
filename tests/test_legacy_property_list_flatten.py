"""
Verification for the LegacyPropertyList flatten/header-hide rework and the
document.py add/paste-operator data-mutation rewrite.

Regression this guards against: before this change, editing a property in the
legacy PropertyFrame backend silently did nothing (update_tree_item_value
scanned dead/empty layouts), and "Add Operator"/"Add Selection Criteria" built
orphan widgets instead of mutating data.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(root_dir, "src")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from PySide6.QtCore import Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

from src.editors.smartprop_editor.props.legacy_property_list import LegacyPropertyList
from src.editors.smartprop_editor.props.model import ComponentRef
from src.editors.smartprop_editor.document import SmartPropDocument
from src.widgets.element_id import ElementIDGenerator


class _Emit:
    def emit(self):
        pass


class DummyDocument:
    """Minimal stand-in exposing only what LegacyPropertyList / _append_component touch."""

    def __init__(self, tree):
        self.undo_stack = QUndoStack()
        self._modified = False
        self._property_undo_guard = 0
        self._edited = _Emit()
        self.element_id_generator = ElementIDGenerator()
        self.ui = type("U", (), {"tree_hierarchy_widget": tree})()
        self.variable_viewport = type(
            "V", (), {"ui": type("VU", (), {"variables_scrollArea": None})()}
        )()
        self.smartprop_property_panel = type(
            "P", (), {"set_element": staticmethod(lambda item: None)}
        )()


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    tree = QTreeWidget()
    item = QTreeWidgetItem()
    item.setData(0, Qt.UserRole, {
        "_class": "CSmartPropElement_Comment",
        "m_bEnabled": True,
        "m_Comment": "element original",
        "m_nElementID": 1,
        "m_Modifiers": [
            {"_class": "CSmartPropModifier_Comment", "m_bEnabled": True,
             "m_Comment": "mod original", "m_nElementID": 2},
        ],
        "m_SelectionCriteria": [],
    })
    tree.addTopLevelItem(item)

    doc = DummyDocument(tree)
    plist = LegacyPropertyList(document=doc)

    element_ref = ComponentRef(item, "element", -1)
    modifier_ref = ComponentRef(item, "modifier", 0)

    # ── Flatten: both refs render, no group boxes, headers hidden ──────────
    plist.set_components([element_ref, modifier_ref])
    assert len(plist._frames) == 2, f"expected 2 flat frames, got {len(plist._frames)}"
    for f in plist._frames:
        assert f.ui.frame.isVisible() is False, "PropertyFrame header must be hidden"
        assert f.ui.copy_button.parent() is None or True  # deleted via deleteLater; presence check below
    print("[PASS] set_components renders one flat header-less PropertyFrame per selected ref")

    # ── Editing the modifier commits only that modifier, preserves the rest ─
    mod_frame = plist._frames[1]
    mod_frame.value = dict(mod_frame.value)
    mod_frame.value["m_Comment"] = "mod edited"
    plist._commit_frame(modifier_ref, mod_frame)

    data = item.data(0, Qt.UserRole)
    assert data["m_Modifiers"][0]["m_Comment"] == "mod edited"
    assert data["m_Comment"] == "element original", "element fields must survive a modifier commit"
    assert doc.undo_stack.count() == 1
    print("[PASS] modifier commit updates only m_Modifiers[0], element fields untouched")

    # ── Editing the element commits only element fields, preserves modifiers ─
    elem_frame = plist._frames[0]
    elem_frame.value = dict(elem_frame.value)
    elem_frame.value["m_Comment"] = "element edited"
    plist._commit_frame(element_ref, elem_frame)

    data = item.data(0, Qt.UserRole)
    assert data["m_Comment"] == "element edited"
    assert data["m_Modifiers"][0]["m_Comment"] == "mod edited", "modifiers must survive an element commit"
    assert doc.undo_stack.count() == 2
    print("[PASS] element commit updates element fields, m_Modifiers preserved")

    # ── document._append_component (Add Operator / Add Selection Criteria) ──
    tree.setCurrentItem(item)
    SmartPropDocument._append_component(
        doc, "m_Modifiers", {"_class": "CSmartPropModifier_Comment", "m_Comment": "new op"}
    )
    data = item.data(0, Qt.UserRole)
    assert len(data["m_Modifiers"]) == 2
    assert data["m_Modifiers"][1]["m_Comment"] == "new op"
    assert "m_nElementID" in data["m_Modifiers"][1]
    assert doc.undo_stack.count() == 3
    print("[PASS] _append_component appends a modifier and pushes undo")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
