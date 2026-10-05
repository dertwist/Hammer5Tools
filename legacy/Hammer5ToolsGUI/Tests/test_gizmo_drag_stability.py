"""Gizmo drags must not be perturbed by the scene rebuilds they trigger.

Every mouse-move of a drag rewrites the document and re-evaluates it through
Core, which used to push the round-tripped transform straight back into the
gizmo.  For a child element that round-trip is lossy (restricted axes, a parent
matrix Core reports for a different repeat of the same element), so the handles
crawled away from the cursor.  The drag now owns the transform outright.
"""
import numpy as np
import pytest

from gui.editors.smartprop_editor.viewport_3d.gizmo import Gizmo, GizmoAxis, GizmoMode

# Looking down -Z at the origin, y up: a plain orthographic-ish setup is enough
# for project_to_screen, which is all the translate path needs.
VIEW = np.array([
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, -400.0, 1.0],
], dtype=np.float32)
PROJ = np.array([
    [1.5, 0.0, 0.0, 0.0],
    [0.0, 2.0, 0.0, 0.0],
    [0.0, 0.0, -1.0, -1.0],
    [0.0, 0.0, -2.0, 0.0],
], dtype=np.float32)
CAM = np.array([0.0, 0.0, 400.0], dtype=np.float32)
W, H = 1280, 720


def _gizmo():
    g = Gizmo()
    g.mode = GizmoMode.TRANSLATE
    g.set_transform([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
    return g


def _drag_to(g, x, y):
    return g.update_drag((x, y), VIEW, PROJ, W, H, CAM)


def test_drag_result_is_absolute_from_the_press_point():
    g = _gizmo()
    g.begin_drag(GizmoAxis.X, (640.0, 360.0))

    half = _drag_to(g, 700.0, 360.0)["position"]
    full = _drag_to(g, 760.0, 360.0)["position"]

    assert full[0] == pytest.approx(2.0 * half[0], rel=1e-4)
    # Untouched axes stay put.
    assert full[1] == pytest.approx(0.0) and full[2] == pytest.approx(0.0)


def test_rebuild_pushing_back_a_lossy_transform_cannot_move_the_drag():
    """set_transform mid-drag is what update_viewport used to do every event."""
    g = _gizmo()
    g.begin_drag(GizmoAxis.X, (640.0, 360.0))
    clean = _drag_to(g, 740.0, 360.0)["position"]

    g2 = _gizmo()
    g2.begin_drag(GizmoAxis.X, (640.0, 360.0))
    _drag_to(g2, 690.0, 360.0)
    # A rebuild reports a wildly different world transform (wrong repeat of a
    # FitOnLine child) and re-seeds the gizmo with it.
    g2.set_transform([999.0, -50.0, 7.0], [0.0, 90.0, 0.0], [3.0, 3.0, 3.0])
    polluted = _drag_to(g2, 740.0, 360.0)["position"]

    assert polluted == pytest.approx(clean, abs=1e-4)


def test_gizmo_adopts_its_own_drag_result():
    g = _gizmo()
    g.begin_drag(GizmoAxis.X, (640.0, 360.0))
    result = _drag_to(g, 740.0, 360.0)["position"]

    assert g.position.tolist() == pytest.approx(result, abs=1e-5)


def test_local_space_axis_is_frozen_for_the_whole_rotate_drag():
    g = _gizmo()
    g.mode = GizmoMode.ROTATE
    g.coordinate_space = "Local"
    g.set_transform([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
    g.begin_drag(GizmoAxis.Z, (740.0, 360.0))
    # X is a bystander here -- it swings when the Local basis follows a changing
    # rotation, and holds still when the basis is pinned to the press.
    x_at_start = g.get_s2_axis_direction(GizmoAxis.X).copy()

    _drag_to(g, 740.0, 300.0)
    assert g.rotation.tolist() != [0.0, 0.0, 0.0]  # the drag did rotate it
    assert g.get_s2_axis_direction(GizmoAxis.X) == pytest.approx(x_at_start, abs=1e-6)

    g.end_drag()
    assert g.get_s2_axis_direction(GizmoAxis.X) != pytest.approx(x_at_start, abs=1e-6)
