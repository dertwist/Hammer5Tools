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
