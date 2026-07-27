"""
PropertyTreeModel — the value layer for the SmartProp property editor (phase P2).

Design notes that differ from a naive reading of the plan:

* **Read-through, not owned copies.** The single source of truth stays the tree item's
  ``Qt.UserRole`` dict. The model reads through to it on every ``data()`` call instead of
  keeping its own copy, so there is no way for the two to desync and no re-seeding step
  after an external change (undo/redo, manual editor, gizmo). Rows are cheap (~20 per
  component) so the extra dict lookups are free.

* **"Default" mode deletes the key.** In the old widget layer a control in Default mode set
  ``self.value = None``, and ``PropertyFrame.on_edited`` rebuilt the element dict by merging
  only non-None widget values — so a Default field ended up *absent* from the saved dict, not
  present-and-null. Writing ``None`` instead would change the ``.vsmart`` output. Callers pass
  the :data:`DEFAULT` sentinel to mean "remove this key".

* **Unknown classes fall back to their own keys.** ``schema.fields_for()`` returns ``[]`` for a
  class it does not know; the old code fell back to iterating the value dict. Preserved here so
  a new/unrecognised element class still shows its fields instead of an empty panel.

Undo: reuses ``PropertySnapshotCommand``. Two contracts of that class matter —
its ``redo()`` deliberately no-ops the first time (the edit is applied *before* the push), and
``mergeWith()`` collapses consecutive edits that share the same diff keys, which gives
keystroke and slider coalescing for free. This model therefore mutates first, then pushes, and
does not implement begin_drag/end_drag.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, Signal

from src.common import fast_deepcopy
from src.editors.smartprop_editor.props import schema


# ---------------------------------------------------------------- sentinels

class _Sentinel:
    __slots__ = ("_name",)

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return self._name

    def __bool__(self):
        return False


#: Selected components disagree on this field.
MIXED = _Sentinel("MIXED")
#: "Default" mode — remove the key from the element dict entirely.
DEFAULT = _Sentinel("DEFAULT")


# ---------------------------------------------------------------- refs

_CONTAINER = {"modifier": "m_Modifiers", "criterion": "m_SelectionCriteria"}

# 'm_Modifiers[2].m_flAmount' / 'm_SelectionCriteria[0]' — same shape document.py parses.
_DIFF_KEY_RE = re.compile(r"^(m_Modifiers|m_SelectionCriteria)\[(\d+)\](?:\.(.+))?$")


@dataclass(frozen=True)
class ComponentRef:
    """Identifies one editable dict: the element itself, or one of its modifiers/criteria."""

    item: Any            # QTreeWidgetItem / HierarchyItemModel
    kind: str            # 'element' | 'modifier' | 'criterion'
    index: int = -1      # -1 for 'element'

    def container(self) -> str | None:
        return _CONTAINER.get(self.kind)

    def target(self, element_data: dict) -> dict | None:
        """The sub-dict this ref points at, inside ``element_data``. None if out of range."""
        if self.kind == "element":
            return element_data
        arr = element_data.get(self.container()) or []
        if 0 <= self.index < len(arr) and isinstance(arr[self.index], dict):
            return arr[self.index]
        return None

    def prop_class(self) -> str:
        data = self.item.data(0, Qt.UserRole)
        target = self.target(data) if isinstance(data, dict) else None
        raw = (target or {}).get("_class", "") or ""
        return raw.split("_", 1)[-1] if raw else ""

    def diff_key(self, field: str) -> str:
        """Discriminator matching PropertySnapshotCommand._changed_keys output."""
        if self.kind == "element":
            return field
        return f"{self.container()}[{self.index}].{field}"


# ---------------------------------------------------------------- model

FieldDefRole = Qt.UserRole + 1
MixedRole = Qt.UserRole + 2
RefRole = Qt.UserRole + 3

COL_NAME = 0
COL_VALUE = 1


class PropertyTreeModel(QAbstractItemModel):
    """Flat 2-column model over one (or several) components' fields.

    Group rows arrive in P5; until then ``parent()`` is always invalid.
    """

    #: Emitted when a write changed m_Modifiers / m_SelectionCriteria as a whole
    #: (add / remove / reorder) so the components list can rebuild itself.
    structureChanged = Signal(object)   # QTreeWidgetItem

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self._document = document
        self._refs: list[ComponentRef] = []
        self._rows: list[schema.FieldDef] = []

    # ---- selection -------------------------------------------------

    def set_components(self, refs) -> None:
        """Point the model at one component (normal) or several (multi-select)."""
        self.beginResetModel()
        self._refs = [r for r in (refs or []) if r.target(self._data_of(r)) is not None]
        self._rows = self._build_rows()
        self.endResetModel()

    def refs(self) -> list[ComponentRef]:
        return list(self._refs)

    def _data_of(self, ref: ComponentRef) -> dict:
        d = ref.item.data(0, Qt.UserRole)
        return d if isinstance(d, dict) else {}

    def _fields_of(self, ref: ComponentRef) -> list[str]:
        """Schema order, or the dict's own keys for a class the schema doesn't know."""
        cls = ref.prop_class()
        fields = schema.fields_for(cls)
        if not fields:
            target = ref.target(self._data_of(ref)) or {}
            fields = [k for k in target.keys() if k not in schema.SKIP]
        return fields

    def _build_rows(self) -> list[schema.FieldDef]:
        if not self._refs:
            return []
        first = self._fields_of(self._refs[0])
        if len(self._refs) > 1:
            # Intersection, preserving the first ref's order.
            common = set(first)
            for r in self._refs[1:]:
                common &= set(self._fields_of(r))
            first = [f for f in first if f in common]

        cls = self._refs[0].prop_class()
        rows = []
        for f in first:
            fd = schema.resolve(cls, f)
            if fd is None:          # SKIP field
                continue
            # One field's control depends on the runtime value; refine it here so the
            # delegate never has to know about this special case.
            if "m_VariableValue" in f:
                val = self._raw(self._refs[0], f)
                if not (isinstance(val, dict) and ("m_TargetName" in val or "m_DataType" in val)) \
                        and not (val is None and cls == "SetVariable"):
                    control = schema.resolve_variable_value(cls, val)
                    kwargs = dict(fd.kwargs)
                    if control == "string":
                        kwargs["expression_bool"] = True
                    elif control == "float" and cls.endswith("Int"):
                        kwargs["int_bool"] = True
                    fd = schema.FieldDef(
                        field=fd.field, control=control, kwargs=kwargs,
                        label=fd.label, icon=fd.icon, group=fd.group,
                    )
            rows.append(fd)
        return rows

    # ---- QAbstractItemModel ----------------------------------------

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() or not (0 <= row < len(self._rows)) or not (0 <= column < 2):
            return QModelIndex()
        return self.createIndex(row, column, None)

    def parent(self, _index=QModelIndex()):
        return QModelIndex()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 2

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ("Name", "Value")[section] if section in (0, 1) else None
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == COL_VALUE:
            f |= Qt.ItemIsEditable
        return f

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        fd = self._rows[index.row()]

        if role == FieldDefRole:
            return fd
        if role == RefRole:
            return self._refs[0] if self._refs else None
        if role == MixedRole:
            return self._value(fd.field) is MIXED

        if index.column() == COL_NAME:
            if role == Qt.DisplayRole:
                return fd.label
            return None

        value = self._value(fd.field)
        if role == Qt.EditRole:
            return value
        if role == Qt.DisplayRole:
            if value is MIXED:
                return "—"          # em dash
            if value is DEFAULT:
                return ""
            return value
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or index.column() != COL_VALUE:
            return False
        return self.set_field(self._rows[index.row()].field, value)

    # ---- reads -----------------------------------------------------

    def _raw(self, ref: ComponentRef, field: str):
        """Raw stored value, or DEFAULT when the key is absent."""
        target = ref.target(self._data_of(ref))
        if target is None or field not in target:
            return DEFAULT
        return target[field]

    def _value(self, field: str):
        """Agreed value across all selected refs, else MIXED."""
        if not self._refs:
            return DEFAULT
        first = self._raw(self._refs[0], field)
        for r in self._refs[1:]:
            if self._raw(r, field) != first:
                return MIXED
        return first

    # ---- writes ----------------------------------------------------

    def set_field(self, field: str, value) -> bool:
        """Write one field across every selected component. Returns True if anything changed.

        ``value is DEFAULT`` removes the key (Default mode). Pushes one
        PropertySnapshotCommand per affected tree item, wrapped in a macro when more than one
        item is touched so a single undo reverts the whole edit.
        """
        if not self._refs:
            return False

        by_item: dict[int, list[ComponentRef]] = {}
        order: list[Any] = []
        for r in self._refs:
            key = id(r.item)
            if key not in by_item:
                by_item[key] = []
                order.append(r.item)
            by_item[key].append(r)

        plans = []
        for item in order:
            refs = by_item[id(item)]
            old_data = fast_deepcopy(item.data(0, Qt.UserRole))
            new_data = fast_deepcopy(old_data)
            touched = False
            for r in refs:
                target = r.target(new_data)
                if target is None:
                    continue
                if value is DEFAULT:
                    if field in target:
                        del target[field]
                        touched = True
                elif target.get(field, DEFAULT) != value:
                    target[field] = value
                    touched = True
            if touched:
                plans.append((item, old_data, new_data))

        if not plans:
            return False

        stack = getattr(self._document, "undo_stack", None)
        macro = stack is not None and len(plans) > 1
        if macro:
            stack.beginMacro(f"Edit {field}")
        try:
            for item, old_data, new_data in plans:
                # Mutate first — PropertySnapshotCommand.redo() skips its first call.
                item.setData(0, Qt.UserRole, new_data)
                self._push_command(item, old_data, new_data)
        finally:
            if macro:
                stack.endMacro()

        self._mark_modified()
        row = next((i for i, fd in enumerate(self._rows) if fd.field == field), None)
        if row is not None:
            self.dataChanged.emit(
                self.index(row, COL_NAME), self.index(row, COL_VALUE),
                [Qt.DisplayRole, Qt.EditRole, MixedRole],
            )
        return True

    def _push_command(self, item, old_data, new_data):
        stack = getattr(self._document, "undo_stack", None)
        if stack is None or old_data == new_data:
            return
        if getattr(self._document, "_property_undo_guard", 0):
            return
        from src.editors.smartprop_editor.commands import PropertySnapshotCommand
        stack.push(PropertySnapshotCommand(self._document, item, old_data, new_data))

    def _mark_modified(self):
        doc = self._document
        if doc is None:
            return
        try:
            doc._modified = True
            doc._edited.emit()
        except Exception:
            pass

    # ---- external changes (undo/redo, manual editor, gizmo) --------

    def apply_external_data(self, item, new_data, changed_keys=()) -> None:
        """Replacement for ``document._incremental_property_update``.

        Writes ``new_data`` onto the tree item and refreshes the affected rows. Because the
        model reads through to the item there is nothing to re-seed — only the views need
        telling. A structural change to either list re-emits ``structureChanged`` so the
        components list can rebuild; if that invalidates our refs, the panel will call
        ``set_components`` again.
        """
        item.setData(0, Qt.UserRole, fast_deepcopy(new_data))

        structural = any(k in ("m_Modifiers", "m_SelectionCriteria") for k in changed_keys)
        if structural:
            self.structureChanged.emit(item)

        if not self._rows or not any(r.item is item for r in self._refs):
            return

        rows = self._rows_for_keys(changed_keys)
        if rows is None:                       # unknown / broad change → refresh everything
            top, bottom = 0, len(self._rows) - 1
        elif not rows:
            return
        else:
            top, bottom = min(rows), max(rows)
        self.dataChanged.emit(
            self.index(top, COL_NAME), self.index(bottom, COL_VALUE),
            [Qt.DisplayRole, Qt.EditRole, MixedRole],
        )

    def _rows_for_keys(self, changed_keys):
        """Row indices touched by a set of diff keys; None means 'cannot tell, refresh all'."""
        if not changed_keys:
            return None
        by_field = {fd.field: i for i, fd in enumerate(self._rows)}
        rows = set()
        for key in changed_keys:
            if key in ("_class", "m_nElementID"):
                continue
            m = _DIFF_KEY_RE.match(key)
            if m:
                container, idx, sub = m.group(1), int(m.group(2)), m.group(3)
                if sub is None:
                    return None                # whole component replaced
                if not any(r.container() == container and r.index == idx for r in self._refs):
                    continue
                field = sub.split(".")[0]
            else:
                field = key.split(".")[0]
            if field in by_field:
                rows.add(by_field[field])
        return rows


# ---------------------------------------------------------------- self-check

if __name__ == "__main__":
    import os, sys
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
    from PySide6.QtGui import QUndoStack

    app = QApplication(sys.argv)

    class Doc:
        """Stand-in for SmartPropDocument: only what PropertySnapshotCommand touches.

        ``apply_property_data`` mirrors the real seam added in document.py, so undo/redo here
        exercises the same path the app will: command -> document hook -> model refresh.
        """
        def __init__(self):
            self.undo_stack = QUndoStack()
            self._modified = False
            self._property_undo_guard = 0
            self.ui = type("U", (), {"tree_hierarchy_widget": None})()
            self.property_panel = None      # set to the model below
            class _E:
                def emit(self_inner): pass
            self._edited = _E()

        def apply_property_data(self, item, new_data, changed_keys):
            self.property_panel.apply_external_data(item, new_data, changed_keys)

    tree = QTreeWidget()
    doc = Doc()
    doc.ui.tree_hierarchy_widget = tree

    def make_item(name="Model"):
        it = QTreeWidgetItem(tree)
        it.setText(0, name)
        it.setData(0, Qt.UserRole, {
            "_class": "CSmartPropElement_Model",
            "m_nElementID": 1,
            "m_sModelName": "models/a.vmdl",
            "m_flUniformModelScale": 1.0,
            "m_Modifiers": [
                {"_class": "CSmartPropOperation_Scale", "m_nElementID": 2,
                 "m_bEnabled": True, "m_flScale": 2.0},
            ],
            "m_SelectionCriteria": [],
        })
        return it

    it1 = make_item()
    m = PropertyTreeModel(doc)
    doc.property_panel = m
    tree.setCurrentItem(it1)      # so PropertySnapshotCommand takes the in-place path

    # --- element component ---
    ref_el = ComponentRef(it1, "element", -1)
    assert ref_el.prop_class() == "Model", ref_el.prop_class()
    m.set_components([ref_el])
    assert m.columnCount() == 2
    assert m.rowCount() == len(m._rows) > 0
    fields = [fd.field for fd in m._rows]
    assert "m_sModelName" in fields and "_class" not in fields and "m_nElementID" not in fields
    # Row order comes straight from the schema, minus SKIP fields.
    assert fields == [f for f in schema.fields_for("Model") if f not in schema.SKIP], fields

    # value read-through
    r = fields.index("m_sModelName")
    assert m.data(m.index(r, COL_VALUE), Qt.EditRole) == "models/a.vmdl"
    assert m.data(m.index(r, COL_NAME), Qt.DisplayRole) == "Model Name"

    # absent key reads as DEFAULT and displays blank
    r_missing = next(i for i, fd in enumerate(m._rows)
                     if fd.field not in it1.data(0, Qt.UserRole))
    assert m.data(m.index(r_missing, COL_VALUE), Qt.EditRole) is DEFAULT
    assert m.data(m.index(r_missing, COL_VALUE), Qt.DisplayRole) == ""

    # --- write + undo ---
    n0 = doc.undo_stack.count()
    assert m.set_field("m_sModelName", "models/b.vmdl") is True
    assert it1.data(0, Qt.UserRole)["m_sModelName"] == "models/b.vmdl"
    assert doc.undo_stack.count() == n0 + 1
    assert doc._modified is True

    # diff-noop: same value pushes nothing
    assert m.set_field("m_sModelName", "models/b.vmdl") is False
    assert doc.undo_stack.count() == n0 + 1

    doc.undo_stack.undo()
    assert it1.data(0, Qt.UserRole)["m_sModelName"] == "models/a.vmdl", \
        it1.data(0, Qt.UserRole)["m_sModelName"]
    doc.undo_stack.redo()
    assert it1.data(0, Qt.UserRole)["m_sModelName"] == "models/b.vmdl"

    # --- DEFAULT deletes the key (must not write None) ---
    assert m.set_field("m_flUniformModelScale", DEFAULT) is True
    assert "m_flUniformModelScale" not in it1.data(0, Qt.UserRole)
    assert m.set_field("m_flUniformModelScale", DEFAULT) is False   # already gone

    # --- modifier component ---
    ref_mod = ComponentRef(it1, "modifier", 0)
    assert ref_mod.prop_class() == "Scale"
    assert ref_mod.diff_key("m_flScale") == "m_Modifiers[0].m_flScale"
    m.set_components([ref_mod])
    mf = [fd.field for fd in m._rows]
    assert "m_flScale" in mf, mf
    rs = mf.index("m_flScale")
    assert m.data(m.index(rs, COL_VALUE), Qt.EditRole) == 2.0
    assert m.setData(m.index(rs, COL_VALUE), 5.0, Qt.EditRole) is True
    assert it1.data(0, Qt.UserRole)["m_Modifiers"][0]["m_flScale"] == 5.0

    # out-of-range ref is dropped by set_components
    m.set_components([ComponentRef(it1, "modifier", 7)])
    assert m.rowCount() == 0 and m.refs() == []

    # --- multi-select: MIXED + fan-out + single undo ---
    it2 = make_item("Model2")
    d2 = it2.data(0, Qt.UserRole); d2["m_sModelName"] = "models/z.vmdl"
    it2.setData(0, Qt.UserRole, d2)
    m.set_components([ComponentRef(it1, "element", -1), ComponentRef(it2, "element", -1)])
    rn = [fd.field for fd in m._rows].index("m_sModelName")
    assert m.data(m.index(rn, COL_VALUE), Qt.EditRole) is MIXED
    assert m.data(m.index(rn, COL_VALUE), Qt.DisplayRole) == "—"
    assert m.data(m.index(rn, COL_VALUE), MixedRole) is True
    before = doc.undo_stack.count()
    assert m.set_field("m_sModelName", "models/same.vmdl") is True
    assert it1.data(0, Qt.UserRole)["m_sModelName"] == "models/same.vmdl"
    assert it2.data(0, Qt.UserRole)["m_sModelName"] == "models/same.vmdl"
    assert m.data(m.index(rn, COL_VALUE), Qt.EditRole) == "models/same.vmdl"
    assert doc.undo_stack.count() == before + 1, "macro should be one undo entry"
    doc.undo_stack.undo()
    assert it1.data(0, Qt.UserRole)["m_sModelName"] == "models/b.vmdl"
    assert it2.data(0, Qt.UserRole)["m_sModelName"] == "models/z.vmdl"

    # --- unknown class falls back to its own keys ---
    it3 = QTreeWidgetItem(tree)
    it3.setData(0, Qt.UserRole, {"_class": "CSmartPropElement_TotallyNew",
                                 "m_nElementID": 9, "m_flWhatever": 3.0})
    m.set_components([ComponentRef(it3, "element", -1)])
    assert [fd.field for fd in m._rows] == ["m_flWhatever"], [fd.field for fd in m._rows]

    # --- apply_external_data: refresh without pushing undo ---
    m.set_components([ComponentRef(it1, "element", -1)])
    n_before = doc.undo_stack.count()
    changed = []
    m.dataChanged.connect(lambda a, b, roles=None: changed.append((a.row(), b.row())))
    nd = fast_deepcopy(it1.data(0, Qt.UserRole)); nd["m_sModelName"] = "models/ext.vmdl"
    m.apply_external_data(it1, nd, frozenset({"m_sModelName"}))
    assert it1.data(0, Qt.UserRole)["m_sModelName"] == "models/ext.vmdl"
    assert doc.undo_stack.count() == n_before, "external apply must not push a command"
    assert changed, "expected a dataChanged for the touched row"

    # structural change notifies the components list
    seen = []
    m.structureChanged.connect(lambda itm: seen.append(itm))
    nd2 = fast_deepcopy(it1.data(0, Qt.UserRole)); nd2["m_Modifiers"] = []
    m.apply_external_data(it1, nd2, frozenset({"m_Modifiers"}))
    assert seen == [it1]

    # _rows_for_keys targeting
    m.set_components([ComponentRef(it1, "element", -1)])
    assert m._rows_for_keys(frozenset({"m_nElementID"})) == set()
    assert m._rows_for_keys(()) is None
    assert m._rows_for_keys(frozenset({"m_Modifiers[0]"})) is None

    print("model.py self-check: ALL ASSERTIONS PASSED (%d rows in last selection)" % m.rowCount())
