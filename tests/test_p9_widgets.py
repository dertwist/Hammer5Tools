"""
Phase P9 — verification of the rich property editor widgets.

Covers the scalar field editors (Default / Value / Variable / Expression modes),
the value-contract helpers, and integration with PropertyTreeModel setData +
undo.  List/multi-row editors are exercised in later phases; this file focuses
on the scalar layer added in Phase B.
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

from src.editors.smartprop_editor.props.widgets import (
    EditorContext,
    FloatFieldEditor,
    BoolFieldEditor,
    ComboFieldEditor,
    ColorFieldEditor,
    StringFieldEditor,
    VariableOutputEditor,
    LegacyEditor,
    parse_value_mode,
    build_value_shape,
    MODE_DEFAULT,
    MODE_VALUE,
    MODE_VARIABLE,
    MODE_EXPRESSION,
)
from src.editors.smartprop_editor.props.model import DEFAULT, MIXED


class MockUI:
    tree_hierarchy_widget = None


class DummyDocument:
    """Minimal document stand-in: no variables viewport, so editors degrade."""
    def __init__(self):
        self.undo_stack = QUndoStack()
        self.ui = MockUI()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    ctx = EditorContext()   # no variables source → editors use line-edit fallbacks

    # ── 1. Value-contract helpers ────────────────────────────────────────────
    assert parse_value_mode(None) == (MODE_DEFAULT, None)
    assert parse_value_mode(DEFAULT) == (MODE_DEFAULT, None)
    assert parse_value_mode(5.0) == (MODE_VALUE, 5.0)
    assert parse_value_mode("hi") == (MODE_VALUE, "hi")
    assert parse_value_mode({"m_SourceName": "var1"}) == (MODE_VARIABLE, "var1")
    assert parse_value_mode({"m_Expression": "a + b"}) == (MODE_EXPRESSION, "a + b")
    # Raw-expression field stores the bare string.
    assert parse_value_mode("a + b", field="m_Expression") == (MODE_EXPRESSION, "a + b")
    print("[PASS] parse_value_mode decodes all four shapes (+ raw-expression special case)")

    assert build_value_shape(MODE_DEFAULT, 5.0) is DEFAULT
    assert build_value_shape(MODE_VALUE, 5.0) == 5.0
    assert build_value_shape(MODE_VARIABLE, None, var="vx") == {"m_SourceName": "vx"}
    assert build_value_shape(MODE_EXPRESSION, None, expr="a+b") == {"m_Expression": "a+b"}
    # Raw-expression field writes the bare string back.
    assert build_value_shape(MODE_EXPRESSION, None, expr="a+b", field="m_Expression") == "a+b"
    print("[PASS] build_value_shape builds all four shapes (+ raw-expression special case)")

    # ── 2. FloatFieldEditor: Value mode literal + DEFAULT round-trip ─────────
    fe = FloatFieldEditor("m_flScale", ctx, slider_range=[0, 10])
    fe.set_value(3.5)
    assert fe.value() == 3.5, fe.value()
    fe.set_value(DEFAULT)
    assert fe.value() is DEFAULT, fe.value()
    print("[PASS] FloatFieldEditor Value-mode literal + DEFAULT round-trip")

    # Integer-typed field coerces to int.
    fei = FloatFieldEditor("m_nCount", ctx, int_bool=True)
    fei.set_value(7)
    assert fei.value() == 7 and isinstance(fei.value(), int)
    print("[PASS] FloatFieldEditor int_bool returns int")

    # ── 3. BoolFieldEditor ───────────────────────────────────────────────────
    be = BoolFieldEditor("m_bEnabled", ctx)
    be.set_value(True)
    assert be.value() is True
    be.set_value(DEFAULT)
    assert be.value() is DEFAULT
    print("[PASS] BoolFieldEditor Value-mode + DEFAULT")

    # ── 4. ComboFieldEditor ──────────────────────────────────────────────────
    ce = ComboFieldEditor("m_Mode", ["A", "B", "C"], ctx)
    ce.set_value("B")
    assert ce.value() == "B", ce.value()
    print("[PASS] ComboFieldEditor Value-mode selection")

    # ── 5. ColorFieldEditor ──────────────────────────────────────────────────
    cole = ColorFieldEditor("m_Color", ctx)
    cole.set_value([10, 20, 30, 255])
    v = cole.value()
    assert v[:3] == [10, 20, 30], v
    print("[PASS] ColorFieldEditor Value-mode RGB round-trip")

    # ── 6. StringFieldEditor: placeholder + mode constraints ─────────────────
    se = StringFieldEditor("m_sFoo", ctx, placeholder="hello")
    se.set_value("bar")
    assert se.value() == "bar"
    # expression_bool forces Expression mode (raw-string storage).
    se_expr = StringFieldEditor("m_Expression", ctx, expression_bool=True)
    se_expr.set_value("a ? b : c")
    assert se_expr.value() == "a ? b : c", se_expr.value()
    print("[PASS] StringFieldEditor Value + Expression(raw) modes")

    # ── 7. VariableOutputEditor writes the bare variable name ────────────────
    ve = VariableOutputEditor("m_VariableName", ctx)
    ve.set_value({"m_SourceName": "myVar"})
    assert ve.value() == "myVar", ve.value()
    print("[PASS] VariableOutputEditor reads m_SourceName")

    # ── 8. LegacyEditor literal_eval round-trip ──────────────────────────────
    le = LegacyEditor("m_flWhatever", ctx)
    le.set_value([1, 2, 3])
    assert le.value() == [1, 2, 3], le.value()
    print("[PASS] LegacyEditor literal round-trip")

    # ── 9. Mode switch on a FloatFieldEditor writes the right shape ──────────
    fe2 = FloatFieldEditor("m_flScale", ctx, slider_range=[0, 10])
    # Drive the switch to Variable mode (index 2) and confirm it emits a dict.
    fe2._switch.setCurrentIndex(2)
    # Fallback variable line-edit — type a name then commit.
    fe2._ensure_variable_picker()
    fe2._variable_picker.setText("width_var")
    captured = []
    fe2.commitValue.connect(captured.append)
    fe2._emit()
    assert captured and captured[-1] == {"m_SourceName": "width_var"}, captured
    # Switch back to Value mode.
    fe2._switch.setCurrentIndex(1)
    fe2._set_literal(8.0)
    fe2._emit()
    assert captured[-1] == 8.0, captured
    print("[PASS] FloatFieldEditor mode switch writes Variable/Value shapes")

    # ── 10. Integration: setData writes the shape through the model ──────────
    from src.editors.smartprop_editor.props.model import PropertyTreeModel, ComponentRef

    class MockTreeWidget:
        def __init__(self, item): self._item = item
        def currentItem(self): return self._item
        def setCurrentItem(self, item): self._item = item
        def scrollToItem(self, item): pass

    tree = QTreeWidgetItem()
    tree.setData(0, Qt.UserRole, {
        "_class": "CSmartPropOperation_Scale",
        "m_bEnabled": True,
        "m_flScale": 1.0,
    })

    class Doc:
        def __init__(self, item):
            self.undo_stack = QUndoStack()
            self._modified = False
            self._property_undo_guard = 0
            self.ui = type("U", (), {"tree_hierarchy_widget": MockTreeWidget(item)})()
            self.property_panel = None
            class _E:
                def emit(self_inner): pass
            self._edited = _E()
        def apply_property_data(self, item, new_data, changed_keys):
            item.setData(0, Qt.UserRole, new_data)

    doc = Doc(tree)
    m = PropertyTreeModel(doc)
    doc.property_panel = m
    m.set_components([ComponentRef(tree, "element", -1)])

    # Write a Variable-mode shape directly via the model.
    assert m.set_field("m_flScale", {"m_SourceName": "global_scale"}) is True
    assert tree.data(0, Qt.UserRole)["m_flScale"] == {"m_SourceName": "global_scale"}
    print("[PASS] Model stores Variable-mode dict shape")

    # DEFAULT removes the key.
    assert m.set_field("m_flScale", DEFAULT) is True
    assert "m_flScale" not in tree.data(0, Qt.UserRole)
    print("[PASS] Model DEFAULT removes key (Variable→Default)")

    # Undo reverts the edits.  Consecutive same-field edits coalesce
    # (PropertySnapshotCommand.mergeTo), so one undo restores the very original
    # value — the same coalescing that makes slider scrub one undo step.
    doc.undo_stack.undo()
    restored = tree.data(0, Qt.UserRole).get("m_flScale")
    assert restored == 1.0, f"Expected original value after undo, got {restored!r}"
    print("[PASS] Undo coalesces consecutive edits and restores original value")

    # Redo re-applies the last (DEFAULT) edit.
    doc.undo_stack.redo()
    assert "m_flScale" not in tree.data(0, Qt.UserRole), "Redo should re-remove key"
    print("[PASS] Redo re-applies DEFAULT (key removed)")

    # ── 11. Multi-row editors ────────────────────────────────────────────────
    from src.editors.smartprop_editor.props.widgets import (
        Vector3DFieldEditor,
        ComparisonEditor,
        ColorMatchEditor,
        SurfaceEditor,
        MaterialReplacementsEditor,
        MaterialGroupChoicesEditor,
        SetVariableEditor,
    )

    # Vector3D: components / whole-vector variable / default.
    v = Vector3DFieldEditor("m_vPosition", ctx)
    v.set_value([1.0, 2.0, 3.0])
    assert v.value() == {"m_Components": [1.0, 2.0, 3.0]}, v.value()
    v.set_value({"m_SourceName": "pos_var"})
    assert v.value() == {"m_SourceName": "pos_var"}, v.value()
    print("[PASS] Vector3DFieldEditor components + whole-variable modes")

    # Comparison.
    c = ComparisonEditor("m_VariableComparison", ctx)
    c.set_value({"m_Name": "health", "m_Value": 50, "m_Comparison": ">"})
    assert c.value() == {"m_Name": "health", "m_Value": 50, "m_Comparison": ">"}, c.value()
    print("[PASS] ComparisonEditor round-trips m_Name/Value/Comparison")

    # ColorMatch list.
    cm = ColorMatchEditor("m_ColorChoices", ctx)
    cm.set_value([[255, 0, 0, 255], [0, 255, 0, 255]])
    cmv = cm.value()
    assert isinstance(cmv, list) and len(cmv) == 2 and cmv[0][:3] == [255, 0, 0], cmv
    print("[PASS] ColorMatchEditor preserves color list")

    # Surface list.
    s = SurfaceEditor("m_AllowedSurfaceProperties", ctx)
    s.set_value(["default", "metal"])
    assert s.value() == ["default", "metal"], s.value()
    print("[PASS] SurfaceEditor preserves surface list")

    # MaterialReplacements list of pairs.
    mr = MaterialReplacementsEditor("m_MaterialReplacements", ctx)
    mr.set_value([{"m_OriginalMaterial": "a.vmat", "m_ReplacementMaterial": "b.vmat"}])
    mrv = mr.value()
    assert isinstance(mrv, list) and mrv[0]["m_OriginalMaterial"] == "a.vmat", mrv
    print("[PASS] MaterialReplacementsEditor preserves origin→target pairs")

    # MaterialGroupChoices list of name+weight.
    mg = MaterialGroupChoicesEditor("m_MaterialGroupChoices", ctx)
    mg.set_value([{"m_MaterialGroupName": "grp", "m_flWeight": 0.5}])
    mgv = mg.value()
    assert isinstance(mgv, list) and mgv[0]["m_MaterialGroupName"] == "grp", mgv
    print("[PASS] MaterialGroupChoicesEditor preserves name+weight rows")

    # SetVariable: data type + value.
    sv = SetVariableEditor("m_VariableValue", ctx)
    sv.set_value({"m_TargetName": "out", "m_DataType": "FLOAT", "m_Value": 3.0})
    assert sv.value() == {"m_TargetName": "out", "m_DataType": "FLOAT", "m_Value": 3.0}, sv.value()
    print("[PASS] SetVariableEditor round-trips TargetName/DataType/Value")

    print("\nALL P9 ASSERTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
