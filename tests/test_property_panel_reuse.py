"""
Verification for the SmartProp property-panel reuse rework.

Regressions this guards against:

1. Frames were destroyed with ``deleteLater()`` without ``_clear_widgets()``,
   so the PooledPropertyMixin row pools never refilled and every selection paid
   cold widget construction (18-67 ms per row, ~730 ms for a 15-field element).
2. There was no frame cache, so reselecting a component already shown rebuilt
   every widget from scratch.
3. Row backgrounds were applied with one ``setStyleSheet`` per row on every
   rebuild (~180 ms per element). They are now painted once by
   ``PropertyFrame.paintEvent`` via ``compact.paint_zebra``, which only works
   while nothing between the frame and its rows carries an *unqualified*
   ``background-color`` rule — such a rule is inherited by every descendant and
   paints over the stripes.
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
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from src.editors.smartprop_editor.property import compact
from src.editors.smartprop_editor.property.base_pooled import PooledPropertyMixin
from src.editors.smartprop_editor.props.legacy_property_list import LegacyPropertyList
from src.editors.smartprop_editor.props.model import ComponentRef
from src.widgets.element_id import ElementIDGenerator


MODEL = {
    "_class": "CSmartPropElement_Model",
    "m_nElementID": 1,
    "m_sModelName": "models/a.vmdl",
    "m_bForceStatic": False,
    "m_vModelScale": [1.0, 1.0, 1.0],
    "m_MaterialGroupName": "",
    "m_bDetailObject": False,
    "m_bCastShadows": True,
    "m_flUniformModelScale": 1.0,
    "m_Modifiers": [],
    "m_SelectionCriteria": [],
}
COMMENT = {
    "_class": "CSmartPropElement_Comment",
    "m_nElementID": 2,
    "m_bEnabled": True,
    "m_Comment": "hello",
    "m_Modifiers": [],
    "m_SelectionCriteria": [],
}


class _Emit:
    def emit(self):
        pass


class DummyDocument:
    """Minimal stand-in exposing only what LegacyPropertyList touches."""

    def __init__(self, tree):
        self.undo_stack = QUndoStack()
        self._modified = False
        self._property_undo_guard = 0
        self._edited = _Emit()
        self.element_id_generator = ElementIDGenerator()
        self.ui = type("U", (), {"tree_hierarchy_widget": tree})()
        self._var_host = QWidget()
        self.variable_viewport = type(
            "V", (), {"ui": type("VU", (), {"variables_scrollArea": QVBoxLayout(self._var_host)})()}
        )()

    def _on_slider_started(self, *a):
        pass

    def _on_slider_committed(self, *a):
        pass


def _drain(app, n=20):
    for _ in range(n):
        app.processEvents()


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    tree = QTreeWidget()
    items = []
    for data in (MODEL, COMMENT):
        it = QTreeWidgetItem(tree)
        it.setData(0, Qt.UserRole, dict(data))
        items.append(it)

    doc = DummyDocument(tree)
    plist = LegacyPropertyList(document=doc)
    plist.resize(420, 900)
    plist.show()

    ref_a = ComponentRef(items[0], "element", -1)
    ref_b = ComponentRef(items[1], "element", -1)

    # ── 1. Reselecting a cached component reuses the very same frame ─────────
    plist.set_components([ref_a])
    _drain(app)
    frame_a = plist._frames[0]

    plist.set_components([ref_b])
    _drain(app)
    assert plist._frames[0] is not frame_a
    assert not frame_a.isVisible(), "the previous frame must be hidden, not shown"

    plist.set_components([ref_a])
    _drain(app)
    assert plist._frames[0] is frame_a, "cached frame was rebuilt instead of reused"
    assert frame_a.isVisible()
    print("[PASS] reselecting a component reuses its cached frame")

    # ── 2. The ref is rebound on reuse, never captured in the edit closure ───
    assert frame_a._ref is ref_a
    print("[PASS] reused frames commit through a freshly-bound ComponentRef")

    # ── 3. Changed backing data invalidates the cache entry ─────────────────
    changed = dict(items[0].data(0, Qt.UserRole))
    changed["m_sModelName"] = "models/b.vmdl"
    items[0].setData(0, Qt.UserRole, changed)
    plist.set_components([ref_b])
    _drain(app)
    plist.set_components([ref_a])
    _drain(app)
    assert plist._frames[0] is not frame_a, "stale frame reused after backing data changed"
    print("[PASS] a content change invalidates the cached frame")

    # ── 4. Retiring a frame refills the per-class row pools ─────────────────
    for pools in PooledPropertyMixin._pools.values():
        for bucket in pools.values():
            bucket.clear()
    for key in list(plist._cache):
        plist._retire(key)
    plist._frames = []
    _drain(app)
    pooled = sum(
        len(bucket)
        for pools in PooledPropertyMixin._pools.values()
        for bucket in pools.values()
    )
    assert pooled > 0, "dispose() did not return any rows to the pools"
    print(f"[PASS] disposing a frame returned {pooled} rows to the per-class pools")

    # ── 5. Row stripes still alternate ──────────────────────────────────────
    plist.set_components([ref_a])
    _drain(app, 30)
    frame = plist._frames[0]
    image = frame.grab().toImage()

    seen = []
    layout = frame.ui.layout
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget() if item is not None else None
        for sub in getattr(widget, "_compact_frames", None) or ():
            if sub.isHidden():
                continue
            top_left = sub.mapTo(frame, sub.rect().topLeft())
            seen.append(image.pixelColor(top_left.x() + 4, top_left.y() + 4).name().upper())

    even = compact.ROW_BG_EVEN.upper()
    odd = compact.ROW_BG_ODD.upper()
    assert seen, "no compact rows found — the zebra sampling itself is broken"
    expected = [even if i % 2 == 0 else odd for i in range(len(seen))]
    assert seen == expected, f"rows are not alternating: {seen}"
    print(f"[PASS] {len(seen)} rows alternate {even}/{odd}")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
