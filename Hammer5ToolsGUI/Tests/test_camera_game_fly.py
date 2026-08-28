import numpy as np
import pytest

from gui.editors.smartprop_editor.viewport_3d.camera import Camera


def test_camera_forward_vector_orthogonal_to_right():
    cam = Camera()
    cam.yaw = 45.0
    cam.pitch = 30.0

    fwd = cam.forward_vector
    right = cam.right_vector
    up = cam.up_vector

    # Normalized
    assert np.isclose(np.linalg.norm(fwd), 1.0, atol=1e-5)
    assert np.isclose(np.linalg.norm(right), 1.0, atol=1e-5)
    assert np.isclose(np.linalg.norm(up), 1.0, atol=1e-5)

    # Orthogonal
    assert np.isclose(np.dot(fwd, right), 0.0, atol=1e-5)
    assert np.isclose(np.dot(fwd, up), 0.0, atol=1e-5)
    assert np.isclose(np.dot(right, up), 0.0, atol=1e-5)


def test_camera_look_preserves_position():
    cam = Camera()
    cam.target = np.array([10.0, 20.0, 30.0], dtype=np.float32)
    cam.distance = 250.0
    cam.yaw = 15.0
    cam.pitch = 10.0

    initial_pos = cam.position.copy()

    # Look around (mouse delta)
    cam.look(dx=50.0, dy=-30.0, sensitivity=0.2)

    # Position should not have moved
    assert np.allclose(cam.position, initial_pos, atol=1e-4)
    # Yaw and pitch changed
    assert not np.isclose(cam.yaw, 15.0)
    assert not np.isclose(cam.pitch, 10.0)


def test_camera_move_fly_translates_position_and_target():
    cam = Camera()
    cam.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    cam.distance = 100.0
    cam.yaw = 0.0
    cam.pitch = 0.0

    initial_pos = cam.position.copy()
    fwd = cam.forward_vector.copy()

    # Move forward 50 units
    cam.move_fly(forward_amount=50.0, right_amount=0.0, up_amount=0.0)

    expected_pos = initial_pos + fwd * 50.0
    assert np.allclose(cam.position, expected_pos, atol=1e-4)
    assert np.allclose(cam.target, np.array([0.0, 0.0, 0.0], dtype=np.float32) + fwd * 50.0, atol=1e-4)


def test_camera_move_fly_strafe_and_vertical():
    cam = Camera()
    cam.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    cam.distance = 100.0
    cam.yaw = 0.0
    cam.pitch = 0.0

    initial_pos = cam.position.copy()
    right = cam.right_vector.copy()

    # Strafe right 20 units and fly up 30 units
    cam.move_fly(forward_amount=0.0, right_amount=20.0, up_amount=30.0)

    expected_pos = initial_pos + right * 20.0 + np.array([0.0, 30.0, 0.0], dtype=np.float32)
    assert np.allclose(cam.position, expected_pos, atol=1e-4)



class _FakePoint:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self):
        return self._x

    def y(self):
        return self._y


class _FakeEvent:
    def __init__(self, x, y):
        self._pos = _FakePoint(x, y)

    def position(self):
        return self._pos


class _FakeWidget:
    """Just the bits of the viewport widget fly_look_delta touches."""

    def __init__(self):
        self._last_mouse_pos = _FakePoint(400.0, 300.0)

    def width(self):
        return 800

    def height(self):
        return 600

    def mapToGlobal(self, point):
        return point


def test_fly_look_delta_is_raw_motion_away_from_the_edges(monkeypatch):
    """Mid-viewport moves must pass through untouched -- warping there stutters."""
    from gui.editors.smartprop_editor.viewport_3d import render_area

    warped = []
    monkeypatch.setattr(render_area.QCursor, "setPos", staticmethod(warped.append))

    widget = _FakeWidget()
    assert render_area.fly_look_delta(widget, _FakeEvent(430.0, 280.0)) == (30.0, -20.0)
    assert render_area.fly_look_delta(widget, _FakeEvent(425.0, 280.0)) == (-5.0, 0.0)
    assert warped == []


def test_fly_look_delta_recenters_at_the_edge(monkeypatch):
    """Near an edge the hidden pointer is recentered, and the warp adds no look input.

    Without this the pointer keeps travelling, leaves the viewport and clicks
    whatever is under it when the user releases RMB.
    """
    from gui.editors.smartprop_editor.viewport_3d import render_area

    warped = []
    monkeypatch.setattr(render_area.QCursor, "setPos", staticmethod(warped.append))

    widget = _FakeWidget()
    widget._last_mouse_pos = _FakePoint(700.0, 300.0)
    assert render_area.fly_look_delta(widget, _FakeEvent(750.0, 300.0)) == (50.0, 0.0)
    assert [(p.x(), p.y()) for p in warped] == [(400, 300)]

    # Next move is measured from the center the pointer was warped to.
    assert render_area.fly_look_delta(widget, _FakeEvent(410.0, 300.0)) == (10.0, 0.0)


def test_fly_look_delta_drops_moves_queued_before_a_recenter(monkeypatch):
    """Pre-warp events must not register, or the camera spins on its own.

    They arrive after the warp still carrying edge coordinates, so each reads as a
    jump back across the viewport -- always in the same direction, which is what
    made looking left or right spin continuously.
    """
    from gui.editors.smartprop_editor.viewport_3d import render_area

    warped = []
    monkeypatch.setattr(render_area.QCursor, "setPos", staticmethod(warped.append))

    widget = _FakeWidget()
    widget._last_mouse_pos = _FakePoint(700.0, 300.0)
    render_area.fly_look_delta(widget, _FakeEvent(750.0, 300.0))  # triggers recenter
    warped.clear()

    # Stale event from before the warp: dropped, and it must not become the new
    # reference point either, or the next real move would jump back the other way.
    assert render_area.fly_look_delta(widget, _FakeEvent(755.0, 300.0)) == (0.0, 0.0)
    assert warped == []
    assert (widget._last_mouse_pos.x(), widget._last_mouse_pos.y()) == (400, 300)

    # Real motion resumes once the queue drains.
    assert render_area.fly_look_delta(widget, _FakeEvent(390.0, 305.0)) == (-10.0, 5.0)
