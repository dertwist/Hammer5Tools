"""Draggable anchors and tangent handles on the curve canvas.

The canvas keeps one permanent item per anchor and handle and only ever feeds
them new data, so these tests check both the editing maths and that a gesture
never destroys the item holding the mouse grab.
"""

from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.soundevent_editor.property.curve.main import SoundEventEditorPropertyCurve

# distance, volume, slope_left, slope_right, mode_left, mode_right
CURVE = [
    [0.0, 1.0, 0.0, 0.0, 2.0, 3.0],
    [100.0, 0.5, 0.0, 0.0, 2.0, 3.0],
    [200.0, 0.0, 0.0, 0.0, 2.0, 3.0],
]

DISTANCE, VOLUME, SLOPE_LEFT, SLOPE_RIGHT, MODE_LEFT, MODE_RIGHT = range(6)


@pytest.fixture
def curve():
    widget = SoundEventEditorPropertyCurve(
        label_text="distance_volume_mapping_curve",
        value=[list(row) for row in CURVE],
        labels=["Distance", "Volume"],
    )
    yield widget
    widget.deleteLater()


def values(curve, index):
    return curve.datapoint_items[index].get_values()


def set_column(curve, index, column, value):
    curve._suppress_signals = True
    curve.datapoint_items[index].widgets["float_widgets"][column].set_value(value)
    curve._suppress_signals = False


def test_one_item_set_per_curve_point(curve):
    assert len(curve._anchor_items) == len(CURVE)
    assert len(curve._handle_items) == len(CURVE)


def test_anchors_start_on_their_points(curve):
    for index, row in enumerate(CURVE):
        position = curve._anchor_items[index].pos()
        assert (float(position.x()), float(position.y())) == (row[DISTANCE], row[VOLUME])


def test_handles_sit_one_arm_length_from_the_anchor(curve):
    length = curve._handle_length()
    left, right = curve._handle_items[1]
    assert float(left.pos().x()) == pytest.approx(100.0 - length)
    assert float(right.pos().x()) == pytest.approx(100.0 + length)


def test_dragging_an_anchor_writes_both_columns(curve):
    curve._anchor_items[1].setPos((120.0, 0.8))
    assert values(curve, 1)[DISTANCE] == pytest.approx(120.0)
    assert values(curve, 1)[VOLUME] == pytest.approx(0.8)


def test_anchor_x_stays_between_its_neighbours(curve):
    curve._anchor_items[1].setPos((900.0, 0.5))
    assert values(curve, 1)[DISTANCE] < 200.0
    curve._anchor_items[1].setPos((-900.0, 0.5))
    assert values(curve, 1)[DISTANCE] > 0.0


def test_items_survive_a_whole_drag(curve):
    anchor = curve._anchor_items[1]
    for y in (0.6, 0.7, 0.8, 0.9):
        anchor.setPos((110.0, y))
        assert len(curve._anchor_items) == len(CURVE)
        assert anchor is curve._anchor_items[1]
    assert curve._anchor_items[1].scene() is not None


def test_a_drag_is_one_undo_entry(curve):
    edits, pressed, committed = [], [], []
    curve.edited.connect(lambda: edits.append(1))
    curve.slider_pressed.connect(lambda: pressed.append(1))
    curve.committed.connect(lambda: committed.append(1))

    anchor = curve._anchor_items[1]
    for y in (0.6, 0.7, 0.8):
        anchor.setPos((110.0, y))
    assert (len(pressed), len(edits), len(committed)) == (1, 0, 0)

    anchor.sigPositionChangeFinished.emit(anchor)
    assert (len(pressed), len(edits), len(committed)) == (1, 1, 1)


def test_free_handle_sets_its_own_slope(curve):
    set_column(curve, 1, MODE_RIGHT, 2)  # free, not tied
    length = curve._handle_length()
    _left, right = curve._handle_items[1]
    right.setPos((100.0 + length, 0.5 + length * 0.5))
    assert values(curve, 1)[SLOPE_RIGHT] == pytest.approx(0.5)
    assert values(curve, 1)[SLOPE_LEFT] == pytest.approx(0.0)


def test_tied_handle_steers_the_slope_it_mirrors(curve):
    # mode_right 3 means the right slope follows the left one, so dragging the
    # right handle has to write slope_left or nothing would move.
    assert values(curve, 1)[MODE_RIGHT] == 3
    length = curve._handle_length()
    _left, right = curve._handle_items[1]
    right.setPos((100.0 + length, 0.5 + length * 0.25))
    assert values(curve, 1)[SLOPE_LEFT] == pytest.approx(0.25)
    assert values(curve, 1)[MODE_RIGHT] == 3  # tie preserved


def test_dragging_a_derived_handle_switches_it_to_authored(curve):
    set_column(curve, 1, MODE_RIGHT, 1)  # a mode that computes the slope
    length = curve._handle_length()
    _left, right = curve._handle_items[1]
    right.setPos((100.0 + length, 0.5 + length * 0.4))
    assert values(curve, 1)[MODE_RIGHT] == 2
    assert values(curve, 1)[SLOPE_RIGHT] == pytest.approx(0.4)


def test_left_handle_slope_sign(curve):
    set_column(curve, 1, MODE_LEFT, 2)
    length = curve._handle_length()
    left, _right = curve._handle_items[1]
    left.setPos((100.0 - length, 0.5 - length * 0.3))
    assert values(curve, 1)[SLOPE_LEFT] == pytest.approx(0.3)


def test_handle_dragged_onto_its_anchor_does_not_divide_by_zero(curve):
    _left, right = curve._handle_items[1]
    right.setPos((100.0, 0.9))
    assert all(value == value for value in values(curve, 1))  # no NaN


def test_item_pool_tracks_added_and_removed_points(curve):
    curve.datapoint_items[1].delete_item()
    assert len(curve._anchor_items) == len(curve.datapoint_items) == 2
    curve.add_datapoint([300.0, 0.2, 0, 0, 2, 3])
    assert len(curve._anchor_items) == len(curve.datapoint_items) == 3


def test_theme_restyle_keeps_the_same_items(curve):
    before = list(curve._anchor_items)
    curve._apply_plot_theme()
    assert curve._anchor_items == before


# --- ranges, measured against pak01_dir.vpk -------------------------------
#
# Across 105130 control points in 41841 shipped curves: x and y are never
# negative (x 0..10000, y 0..1.0084), while slopes are negative at ~20% of
# points and span -10082.46..19.73. So x/y clip at zero and slopes must not
# clip at all.


def test_a_steep_authored_slope_is_not_clamped():
    """The steepest slope shipped in CS2 must survive a load."""
    widget = SoundEventEditorPropertyCurve(
        label_text="distance_unfiltered_stereo_mapping_curve",
        value=[
            [35.109, 0.0, -10082.462, 0.0, 0.0, 0.0],
            [35.208, 1.0, 0.0, -10082.462, 0.0, 0.0],
        ],
        labels=["Distance", "Unfiltered Stereo"],
    )
    assert values(widget, 0)[SLOPE_LEFT] == pytest.approx(-10082.462)
    assert values(widget, 1)[SLOPE_RIGHT] == pytest.approx(-10082.462)
    widget.deleteLater()


def test_a_steep_handle_stays_inside_the_view(curve):
    set_column(curve, 1, MODE_RIGHT, 2)
    set_column(curve, 1, SLOPE_RIGHT, -5000.0)
    curve.plot_graph()
    _left, right = curve._handle_items[1]
    bottom, top = curve.plot_item.viewRange()[1]
    assert bottom <= float(right.pos().y()) <= top


def test_anchor_cannot_be_dragged_to_a_negative_x_or_y(curve):
    curve._anchor_items[0].setPos((-500.0, -2.0))
    assert values(curve, 0)[DISTANCE] >= 0.0
    assert values(curve, 0)[VOLUME] >= 0.0


def test_view_is_clipped_to_the_authored_range_not_the_overshoot(curve):
    # This spline dips below zero between its control points.
    set_column(curve, 0, MODE_LEFT, 2)
    set_column(curve, 0, SLOPE_RIGHT, -0.05)
    curve.plot_graph()
    _distances, volumes = curve.curve_item.getData()
    bottom, _top = curve.plot_item.viewRange()[1]
    assert min(volumes) < bottom or min(volumes) >= 0.0
    assert bottom > -0.5  # the axis does not chase the overshoot


def test_view_x_range_follows_the_points(curve):
    left, right = curve.plot_item.viewRange()[0]
    assert left <= 0.0
    assert right >= 200.0


def arm_segments(curve):
    xs, ys = curve.arms_item.getData()
    points = [(round(float(x), 4), round(float(y), 4)) for x, y in zip(xs, ys)]
    return list(zip(points[0::2], points[1::2]))


def live_pos(item):
    point = item.pos()
    return (round(float(point.x()), 4), round(float(point.y()), 4))


def test_arm_follows_the_handle_while_it_is_dragged(curve):
    set_column(curve, 1, MODE_RIGHT, 2)
    _left, right = curve._handle_items[1]
    right.setPos((160.0, 0.95))
    assert (live_pos(right), (100.0, 0.5)) in arm_segments(curve)


def test_arm_keeps_up_across_a_whole_gesture(curve):
    set_column(curve, 1, MODE_RIGHT, 2)
    _left, right = curve._handle_items[1]
    for y in (0.6, 0.75, 0.9):
        right.setPos((150.0, y))
        assert (live_pos(right), (100.0, 0.5)) in arm_segments(curve)


def test_arm_snaps_back_to_the_slope_on_release(curve):
    set_column(curve, 1, MODE_RIGHT, 2)
    _left, right = curve._handle_items[1]
    right.setPos((160.0, 0.95))
    curve._on_drag_finished()
    length = curve._handle_length()
    slope = values(curve, 1)[SLOPE_RIGHT]
    expected = (round(100.0 + length, 4), round(0.5 + length * slope, 4))
    assert (expected, (100.0, 0.5)) in arm_segments(curve)


def test_arm_vertex_follows_a_dragged_anchor(curve):
    anchor = curve._anchor_items[1]
    anchor.setPos((130.0, 0.85))
    vertex = live_pos(anchor)
    assert any(segment[1] == vertex for segment in arm_segments(curve))
