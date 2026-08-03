"""
Verification for per-property selection, help routing and copy/paste, plus the
chunked row build.

What this guards against:

1. Row descriptions used to be hover tooltips set on every row during the build.
   They now go to the help panel (Section 3) when a row is selected, so the
   selection signal has to carry the field name and its on-screen label.
2. Copy/paste operates on the *selected* row and applies the value to whatever
   row is selected — copying a spacing onto a length is the point — and must
   land on the undo stack like any other edit.
3. PropertyFrame builds its rows a chunk per event-loop tick. A regression here
   is silent: the frame simply stops part-way and the missing fields look like
   fields the element does not have.
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

from src.styles.qt_global_stylesheet import QT_Stylesheet_global

from src.editors.smartprop_editor.property import compact
from src.editors.smartprop_editor.property_frame import PropertyFrame
from src.editors.smartprop_editor.props.legacy_property_list import LegacyPropertyList
from src.editors.smartprop_editor.props.model import ComponentRef
from src.widgets.element_id import ElementIDGenerator


SPHERE = {
    "_class": "CSmartPropElement_PlaceInSphere",
    "m_nElementID": 1,
    "m_bEnabled": True,
    "m_flRandomness": 0.25,
    "m_nCountMin": 1,
    "m_nCountMax": 4,
    "m_flPositionRadiusInner": 8.0,
    "m_flPositionRadiusOuter": 64.0,
    "m_bAlignOrientation": False,
    "m_PlacementMode": "SPHERE",
    "m_DistributionMode": "RANDOM",
    "m_vAlignDirection": [0.0, 0.0, 1.0],
    "m_vPlaneUpDirection": [0.0, 0.0, 1.0],
    "m_Modifiers": [],
    "m_SelectionCriteria": [],
}


class _Emit:
    def emit(self):
        pass


class DummyDocument:
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


def _drain(app, n=40):
    for _ in range(n):
        app.processEvents()


def _row_for(frame, field):
    for widget in frame._property_widgets:
        if getattr(widget, "value_class", None) == field:
            return widget
    return None


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    # main.py applies this to the whole app. Without it these checks do not model
    # the real thing: the sheet carries an unqualified
    # "QWidget { background-color: #151515; }" that paints over anything drawn in
    # a paintEvent, which is exactly how the zebra stripes and the selection
    # highlight shipped invisible while the offscreen checks passed.
    app.setStyleSheet(QT_Stylesheet_global)

    tree = QTreeWidget()
    item = QTreeWidgetItem(tree)
    item.setData(0, Qt.UserRole, dict(SPHERE))

    doc = DummyDocument(tree)
    plist = LegacyPropertyList(document=doc)
    plist.resize(420, 900)
    plist.show()

    ref = ComponentRef(item, "element", -1)

    # ── 1. The chunked build produces every schema field ─────────────────────
    plist.set_components([ref])
    _drain(app)
    frame = plist._frames[0]

    expected = [
        f for f in PropertyFrame._prop_classes_map_cache["PlaceInSphere"]
        if f not in PropertyFrame._SKIP_PROPS
    ]
    built = [getattr(w, "value_class", None) for w in frame._property_widgets]
    missing = [f for f in expected if f not in built]
    assert not missing, f"chunked build stopped early, missing {missing}"
    assert frame._build_offset >= len(expected), "build offset did not reach the end"
    print(f"[PASS] chunked build produced all {len(expected)} rows "
          f"({PropertyFrame._BUILD_CHUNK} per tick)")

    # ── 2. Selecting a row announces field + label for the help panel ────────
    seen = []
    plist.propertySelected.connect(lambda vc, label: seen.append((vc, label)))

    inner = _row_for(frame, "m_flPositionRadiusInner")
    assert inner is not None, "expected a row for m_flPositionRadiusInner"
    frame.select_row(inner)
    _drain(app, 5)
    assert seen, "selecting a row emitted no propertySelected signal"
    field, label = seen[-1]
    assert field == "m_flPositionRadiusInner", field
    assert label, "the help panel needs a non-empty label"
    print(f"[PASS] selection announces ('{field}', '{label}') for the help panel")

    # Descriptions belong to the help panel now, not to a hover tooltip.
    assert not inner.ui.property_class.toolTip(), \
        "row labels must not carry a tooltip any more"
    print("[PASS] row labels no longer set a hover tooltip")

    # ── 3. Focus inside a row's controls selects that row ────────────────────
    outer = _row_for(frame, "m_flPositionRadiusOuter")
    assert frame.row_for_widget(outer.ui.property_class) is outer, \
        "row_for_widget must walk up from a child control to its row"
    print("[PASS] a focused child control resolves to its property row")

    # ── 4. Copy one field, paste it into another ────────────────────────────
    frame.select_row(inner)
    assert frame.copy_property(), "copy_property failed on a selected row"
    assert QApplication.clipboard().text().startswith(PropertyFrame._FIELD_CLIP_TAG)

    undo_before = doc.undo_stack.count()
    frame.select_row(outer)
    assert frame.paste_property(), "paste_property failed on a selected row"
    _drain(app)

    data = item.data(0, Qt.UserRole)
    assert data["m_flPositionRadiusOuter"] == 8.0, \
        f"paste did not apply the copied value: {data['m_flPositionRadiusOuter']}"
    assert data["m_flPositionRadiusInner"] == 8.0, "the source field must be untouched"
    assert doc.undo_stack.count() > undo_before, "paste did not push an undo entry"
    print("[PASS] copy/paste moves a value between rows and is undoable")

    doc.undo_stack.undo()
    assert item.data(0, Qt.UserRole)["m_flPositionRadiusOuter"] == 64.0, \
        "undo did not restore the pasted-over value"
    print("[PASS] undo restores the pasted-over value")

    # ── 5. The selected row is painted with the selection colour ────────────
    frame.select_row(outer)
    _drain(app, 30)
    image = frame.grab().toImage()
    sub = outer._compact_frames[0]
    top_left = sub.mapTo(frame, sub.rect().topLeft())
    got = image.pixelColor(top_left.x() + 4, top_left.y() + 4).name().upper()
    assert got == compact.ROW_BG_SELECTED.upper(), \
        f"selected row painted {got}, expected {compact.ROW_BG_SELECTED.upper()}"
    print(f"[PASS] the selected row is painted {compact.ROW_BG_SELECTED}")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
