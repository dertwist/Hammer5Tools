"""Tests for the VSnap editor."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMenuBar, QMessageBox, QWidget

from core.bridge import CoreBridge, SnapshotDocument, SnapshotStream
from gui.editors.vsnap_editor.document import (
    DEFAULT_LIGHTNING_END,
    DEFAULT_LIGHTNING_POINT_COUNT,
    DEFAULT_LIGHTNING_START,
    VSnapDocument,
)
from gui.editors.vsnap_editor.main import PointTableModel, VSnapEditorMainWindow
from gui.editors.vsnap_editor.viewport import VSnap3DRenderArea, VSnapViewport


class _Native:
    def read_vsnap(self, text):
        assert "stream_data" in text
        return _payload()

    def serialize_vsnap(self, document):
        assert document["streams"][0]["values"][1] == [4.0, 5.0, 6.0]
        return "serialized"

    def generate_vsnap(self, request):
        assert request["count"] == 2
        return _payload()

    def light_vsnap(self, request):
        assert request["firstIndex"] == 0
        assert request["secondIndex"] == 1
        return _payload()

    def generate_vsnap_lightning(self, request):
        assert len(request["start"]) == 3
        assert len(request["end"]) == 3
        assert request["pointCount"] >= 8
        assert request["seed"] >= 0
        return _payload()

    def vsnap_attributes(self):
        return {
            "attributes": [
                {"name": "position", "type": "position_3d", "attribute": 0, "display": "Position"},
                {"name": "radius", "type": "generic_float", "attribute": 3, "display": "Radius"},
                {"name": "trail_length", "type": "generic_float", "attribute": 10, "display": "Trail Length"},
                {"name": "scratch_vec", "type": "generic_vector_3d", "attribute": 17, "display": "Scratch Vector"},
            ],
            "unnameable": {"Rope Segment Data": 48},
        }


def _payload():
    return {
        "count": 2,
        "streams": [
            {"name": "position", "type": "position_3d", "values": [[1, 2, 3], [4, 5, 6]]},
            {"name": "radius", "type": "generic_float", "values": [2, 3]},
        ],
    }


def test_bridge_adapts_snapshot_contract():
    bridge = CoreBridge(native_client=_Native())

    document = bridge.read_vsnap("stream_data")

    assert document.count == 2
    assert document.streams[0].values[1] == (4.0, 5.0, 6.0)
    assert bridge.serialize_vsnap(document) == "serialized"
    assert bridge.generate_vsnap("sphere", 2, 8.0) == document
    assert bridge.apply_vsnap_lighting(document, 0, 1) == document
    assert bridge.generate_vsnap_lightning(
        document.streams[0].values[0], document.streams[0].values[1],
        64, 28.0, 0.45, 2, 3.5, 1234,
    ) == document


def test_point_table_expands_vector_streams():
    document = SnapshotDocument((
        SnapshotStream("position", "position_3d", ((1.0, 2.0, 3.0),)),
        SnapshotStream("radius", "generic_float", (4.0,)),
    ))
    model = PointTableModel()

    model.set_document(document)

    assert model.rowCount() == 1
    assert model.columnCount() == 4
    assert model.headerData(2, 1) == "position.z"
    assert model.data(model.index(0, 3)) == "4"


def test_viewport_uses_smartprop_toolbar_and_exclusive_tools():
    _ = QApplication.instance() or QApplication([])
    viewport = VSnapViewport()

    assert viewport.render_area is not None
    assert viewport.findChild(QWidget, "SPE_Viewport3D_Toolbar") is not None
    assert viewport.preview_combo.currentText() == "Sprites"
    assert viewport.grid_combo.currentText() == "8"

    viewport.draw_mode = True
    assert viewport.btn_draw.isChecked()
    assert not viewport.pick_mode

    viewport.pick_mode = True
    assert viewport.btn_select.isChecked()
    assert not viewport.draw_mode
    assert viewport.pick_mode

    viewport.set_control_points((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    assert viewport.render_area._control_points["start"].tolist() == [1.0, 3.0, -2.0]
    assert viewport.render_area._control_points["end"].tolist() == [4.0, 6.0, -5.0]

    viewport.close()


def test_translate_gizmo_drives_the_control_points():
    import numpy as np
    from PySide6.QtCore import QPointF, Qt

    from gui.editors.smartprop_editor.viewport_3d.gizmo import GizmoAxis, GizmoMode
    from gui.editors.vsnap_editor.viewport import _gl_to_source

    class _Move:
        def __init__(self, x, y):
            self._pos = QPointF(x, y)

        def position(self):
            return self._pos

        def modifiers(self):
            return Qt.NoModifier

    _ = QApplication.instance() or QApplication([])
    area = VSnap3DRenderArea()
    area.resize(800, 600)
    area.camera.aspect = 800 / 600

    assert area.gizmo.mode == GizmoMode.TRANSLATE
    assert area.gizmo.visible
    assert np.allclose(area.gizmo.position, _gl_to_source(area._control_points["start"]))

    # Clicking the far handle selects it and takes the gizmo with it.
    screen = area._project_points(np.asarray([area._control_points["end"]], np.float32))[0]
    assert area._pick_control_point(QPointF(*screen)) == "end"
    area._selected_control_point = "end"
    area._sync_gizmo()
    assert np.allclose(area.gizmo.position, _gl_to_source(area._control_points["end"]))

    # The X arrow hit-tests, and dragging it moves that handle along X only.
    gl_position = area.gizmo._get_gl_position()
    scale = area.gizmo.get_gizmo_scale(area.camera.position, gl_position)
    direction = (gl_position + np.array([scale * 0.8, 0.0, 0.0], np.float32)) - area.camera.position
    direction /= np.linalg.norm(direction)
    assert area.gizmo.hit_test(area.camera.position, direction, area.camera.position) == GizmoAxis.X

    moved = []
    area.control_point_moved.connect(lambda name, point: moved.append((name, point)))
    handle = area._project_points(np.asarray([gl_position], np.float32))[0]
    before = area._control_points["end"].copy()
    area.gizmo.begin_drag(GizmoAxis.X, (float(handle[0]), float(handle[1])))
    area.mouseMoveEvent(_Move(float(handle[0]) + 120.0, float(handle[1])))
    after = area._control_points["end"]

    assert moved[-1][0] == "end"
    assert not np.isclose(before[0], after[0])
    assert np.allclose(before[1:], after[1:], atol=1e-3)
    assert np.allclose(area.gizmo.position, _gl_to_source(after), atol=1e-4)

    area.close()


def test_brush_drag_stamps_scattered_points_on_the_ground():
    import math

    from PySide6.QtCore import QPointF, Qt

    class _Mouse:
        def __init__(self, x, y):
            self._pos = QPointF(x, y)

        def position(self):
            return self._pos

        def button(self):
            return Qt.LeftButton

        def modifiers(self):
            return Qt.NoModifier

    _ = QApplication.instance() or QApplication([])
    viewport = VSnapViewport()
    viewport.resize(900, 700)
    area = viewport.render_area
    area.resize(900, 600)
    area.camera.aspect = 900 / 600

    # Brush settings live on the viewport toolbar and only appear while drawing.
    assert not viewport.brush_settings.isVisibleTo(viewport)
    viewport.draw_mode = True
    assert viewport.brush_settings.isVisibleTo(viewport)

    for widget, amount in (
        (viewport.brush_size_input, 24.0),
        (viewport.brush_spacing_input, 20.0),
        (viewport.brush_density_input, 4),
    ):
        widget.set_value(amount)
        widget.on_spinbox_updated()
    assert area.brush_size == 24.0 and area.brush_spacing == 20.0 and int(area.brush_density) == 4

    strokes = []
    viewport.points_drawn.connect(strokes.append)

    # Pressing stamps once; nudges shorter than the spacing add nothing.
    area.mousePressEvent(_Mouse(450, 400))
    assert len(strokes) == 1 and len(strokes[0]) == 4
    assert area._painting
    for offset in (1, 2, 3):
        area.mouseMoveEvent(_Mouse(450 + offset, 400))
    assert len(strokes) == 1

    # Dragging across the plane keeps stamping and moves the brush ring.
    for x in range(455, 700, 5):
        area.mouseMoveEvent(_Mouse(x, 400))
    assert len(strokes) > 2
    assert area._hover_ground is not None

    # Each stamp scatters on the ground plane, inside the brush radius.
    for stroke in strokes:
        centre_x = sum(point[0] for point in stroke) / len(stroke)
        centre_y = sum(point[1] for point in stroke) / len(stroke)
        for point in stroke:
            assert point[2] == 0.0
            assert math.hypot(point[0] - centre_x, point[1] - centre_y) <= area.brush_size * 2.01

    area.mouseReleaseEvent(_Mouse(700, 400))
    assert not area._painting

    viewport.draw_mode = False
    assert not viewport.brush_settings.isVisibleTo(viewport)

    viewport.close()


def test_brush_stamps_batch_into_one_rebuild(monkeypatch):
    drawn = []

    class _DrawNative(_Native):
        def generate_vsnap(self, request):
            if "positions" in request:
                drawn.append(list(request["positions"]))
                return _payload()
            return super().generate_vsnap(request)

    bridge = CoreBridge(native_client=_DrawNative())
    monkeypatch.setattr(CoreBridge, "instance", staticmethod(lambda: bridge))
    _ = QApplication.instance() or QApplication([])

    editor = VSnapEditorMainWindow()

    assert not hasattr(editor, "draw_button")

    for index in range(5):
        editor._append_drawn_points([(float(index), 0.0, 0.0), (float(index) + 0.5, 1.0, 0.0)])
    assert not drawn
    assert editor._draw_flush_timer.isActive()

    editor._flush_drawn_points()
    assert len(drawn) == 1 and len(drawn[0]) == 10

    # A second stroke adds to the same cloud instead of starting over.
    editor._append_drawn_points([(9.0, 9.0, 0.0)])
    editor._flush_drawn_points()
    assert len(drawn[-1]) == 11

    # Another generator takes the document over and clears the stroke.
    editor.generate_lightning()
    assert editor._draw_points == []

    editor.close()


def test_viewport_gl_callbacks_are_crash_guarded():
    assert hasattr(VSnap3DRenderArea.initializeGL, "__wrapped__")
    assert hasattr(VSnap3DRenderArea.paintGL, "__wrapped__")
    assert hasattr(VSnap3DRenderArea.mousePressEvent, "__wrapped__")


def test_new_document_uses_default_lightning_preset(monkeypatch):
    calls = []

    class _Bridge:
        def generate_vsnap_lightning(self, *args):
            calls.append(args)
            return CoreBridge(native_client=_Native()).generate_vsnap_lightning(*args)

    monkeypatch.setattr(CoreBridge, "instance", staticmethod(lambda: _Bridge()))

    document = VSnapDocument()
    document.new()

    assert calls[0][0] == DEFAULT_LIGHTNING_START
    assert calls[0][1] == DEFAULT_LIGHTNING_END
    assert not document.dirty


def test_editor_uses_menu_bar_and_default_handle_coordinates(monkeypatch):
    bridge = CoreBridge(native_client=_Native())
    monkeypatch.setattr(CoreBridge, "instance", staticmethod(lambda: bridge))
    _ = QApplication.instance() or QApplication([])

    editor = VSnapEditorMainWindow()

    menu_bar = editor.findChild(QMenuBar)
    assert menu_bar is not None
    assert "Import VMAP…" not in [action.text() for action in editor.file_menu.actions()]
    assert editor.viewport.preview_combo.currentText() == "Sprites"
    assert editor._endpoint_values() == (DEFAULT_LIGHTNING_START, DEFAULT_LIGHTNING_END)
    assert tuple(editor.viewport.render_area._control_points) == ("start", "end")

    editor.close()


def test_numeric_controls_are_sliders_and_drive_the_editor(monkeypatch):
    from PySide6.QtGui import QValidator

    from gui.widgets import FloatWidget

    bridge = CoreBridge(native_client=_Native())
    monkeypatch.setattr(CoreBridge, "instance", staticmethod(lambda: bridge))
    _ = QApplication.instance() or QApplication([])

    editor = VSnapEditorMainWindow()

    sliders = (
        editor.count_spin, editor.size_spin, editor.lightning_points, editor.lightning_roughness,
        editor.lightning_branch_probability, editor.lightning_depth, editor.lightning_radius,
        editor.lightning_seed, *editor.lightning_start_spins, *editor.lightning_end_spins,
    )
    assert all(isinstance(widget, FloatWidget) for widget in sliders)
    assert isinstance(editor.count_spin.value, int) and editor.count_spin.value == 512
    assert editor._endpoint_values() == (DEFAULT_LIGHTNING_START, DEFAULT_LIGHTNING_END)

    # Dragging an endpoint slider moves the viewport handle and arms the debounced regen.
    moved = []
    editor.viewport.set_control_points = lambda start, end: moved.append((start, end))
    editor.lightning_start_spins[0].Slider.setValue(9000)
    assert editor.lightning_start_spins[0].value == 90.0
    assert moved[-1][0][0] == 90.0
    assert editor._lightning_regen_timer.isActive()

    # A gizmo-driven field update must not feed back into that loop.
    editor._lightning_regen_timer.stop()
    moved.clear()
    editor._set_endpoint_fields((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    assert editor._endpoint_values() == ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    assert not moved
    assert not editor._lightning_regen_timer.isActive()

    # Bounded controls reject out-of-range typing.
    probability = editor.lightning_branch_probability.SpinBox.validator()
    assert probability.validate("5", 0)[0] != QValidator.Acceptable
    assert probability.validate("0.5", 0)[0] == QValidator.Acceptable
    trunk_points = editor.lightning_points.SpinBox.validator()
    assert trunk_points.validate("7", 0)[0] != QValidator.Acceptable
    assert trunk_points.validate("8", 0)[0] == QValidator.Acceptable
    assert trunk_points.validate("512", 0)[0] == QValidator.Acceptable
    assert trunk_points.validate("513", 0)[0] != QValidator.Acceptable
    editor.lightning_points.SpinBox.clear()
    editor.lightning_points._on_editing_finished()
    assert editor.lightning_points.value == DEFAULT_LIGHTNING_POINT_COUNT
    assert editor.lightning_points.SpinBox.text() == str(DEFAULT_LIGHTNING_POINT_COUNT)

    editor.close()


def test_editor_activation_contains_default_preset_failure(monkeypatch):
    class _BrokenBridge:
        def generate_vsnap_lightning(self, *args):
            raise RuntimeError("missing NativeAOT lightning entry point")

    failures = []
    monkeypatch.setattr(CoreBridge, "instance", staticmethod(lambda: _BrokenBridge()))
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        staticmethod(lambda _parent, title, message: failures.append((title, message))),
    )
    _ = QApplication.instance() or QApplication([])

    editor = VSnapEditorMainWindow()

    assert failures == [(
        "Could not initialize the lightning preset",
        "missing NativeAOT lightning entry point",
    )]
    assert editor.document.data.count == 0
    editor.close()


def test_bridge_reports_the_engine_loadable_attribute_table():
    bridge = CoreBridge(native_client=_Native())

    attributes = bridge.vsnap_attributes()

    assert [item.name for item in attributes] == ["position", "radius", "trail_length", "scratch_vec"]
    assert [item.width for item in attributes] == [3, 1, 1, 3]
    assert bridge.vsnap_unnameable_attributes() == {"Rope Segment Data": 48}


def test_document_adds_and_removes_attribute_streams(monkeypatch):
    monkeypatch.setattr(CoreBridge, "_instance", CoreBridge(native_client=_Native()), raising=False)
    document = VSnapDocument()
    document.replace(SnapshotDocument((
        SnapshotStream("position", "position_3d", ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))),
    )), dirty=False)

    document.add_stream("trail_length")
    document.add_stream("scratch_vec")

    added = {stream.name: stream for stream in document.data.streams}
    assert added["trail_length"].values == (0.1, 0.1)
    assert added["scratch_vec"].values == ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    document.remove_stream("trail_length")
    assert "trail_length" not in {stream.name for stream in document.data.streams}

    document.remove_stream("position")
    assert "position" in {stream.name for stream in document.data.streams}


def test_table_edits_write_back_into_the_document(monkeypatch):
    monkeypatch.setattr(CoreBridge, "_instance", CoreBridge(native_client=_Native()), raising=False)
    document = VSnapDocument()
    document.replace(SnapshotDocument((
        SnapshotStream("position", "position_3d", ((1.0, 2.0, 3.0),)),
        SnapshotStream("radius", "generic_float", (2.0,)),
    )), dirty=False)

    document.set_value(1, 0, None, 9.5)
    document.set_value(0, 0, 2, -4.0)

    assert document.data.streams[1].values == (9.5,)
    assert document.data.streams[0].values == ((1.0, 2.0, -4.0),)


def test_bridge_reads_vector_streams_from_the_binary_decoder():
    """The binary decoder hands back tuples, not lists; a real Valve vsnap has vector streams."""

    class _TupleNative(_Native):
        def read_vsnap(self, text):
            return {
                "count": 2,
                "streams": [
                    {"name": "scratch_vec", "type": "generic_vector_3d",
                     "values": ((-14.1, 0.0, 98.1), (-11.4, 0.0, 96.3))},
                    {"name": "scratch_float", "type": "generic_float", "values": (2.7, 3.1)},
                ],
            }

    document = CoreBridge(native_client=_TupleNative()).read_vsnap("stream_data")

    assert document.streams[0].values[0] == (-14.1, 0.0, 98.1)
    assert document.streams[1].values == (2.7, 3.1)


def test_viewport_splits_ropes_where_the_segment_id_changes():
    """C_OP_RenderRopes starts a new strip on an id change, so reused ids stay separate ropes."""
    import numpy as np

    area = VSnap3DRenderArea()
    area.set_document(SnapshotDocument((
        SnapshotStream("position", "position_3d", tuple((float(i), 0.0, 0.0) for i in range(6))),
        SnapshotStream("rope_segment_id", "generic_int", (0.0, 0.0, 1.0, 1.0, 0.0, 0.0)),
    )))

    groups = [group.tolist() for group in area._rope_groups]

    assert groups == [[0, 1], [2, 3], [4, 5]]


def test_viewport_draws_one_rope_when_no_segment_stream_exists():
    area = VSnap3DRenderArea()
    area.set_document(SnapshotDocument((
        SnapshotStream("position", "position_3d", tuple((float(i), 0.0, 0.0) for i in range(4))),
    )))

    assert [group.tolist() for group in area._rope_groups] == [[0, 1, 2, 3]]
