"""Frustum culling maths for the 3D viewport."""

import numpy as np

from gui.editors.smartprop_editor.viewport_3d.camera import (
    Camera,
    SOURCE2_TO_GL,
    boxes_visible,
    frustum_planes,
    transformed_box,
)


def _view_projection(camera):
    """The row-vector world->clip matrix, exactly as the shaders receive it."""
    return camera.view_matrix @ camera.projection_matrix


def _camera_at(target, distance, yaw=0.0, pitch=0.0):
    camera = Camera()
    camera.aspect = 16 / 9
    camera.target = np.array(target, dtype=np.float32)
    camera.distance = distance
    camera.yaw, camera.pitch = yaw, pitch
    return camera


def test_a_box_at_the_camera_target_is_visible_and_one_behind_is_not():
    camera = _camera_at([0, 0, 0], 500.0)
    planes = frustum_planes(_view_projection(camera))

    # The camera sits at +Z looking back at the origin, so +Z is behind it.
    centers = np.array([[0, 0, 0], [0, 0, 4000]], dtype=np.float32)
    extents = np.array([[10, 10, 10], [10, 10, 10]], dtype=np.float32)

    assert list(boxes_visible(planes, centers, extents)) == [True, False]


def test_boxes_far_off_to_the_side_are_culled():
    camera = _camera_at([0, 0, 0], 500.0)
    planes = frustum_planes(_view_projection(camera))

    centers = np.array([[0, 0, 0], [20000, 0, 0], [0, 20000, 0]], dtype=np.float32)
    extents = np.full((3, 3), 10.0, dtype=np.float32)

    assert list(boxes_visible(planes, centers, extents)) == [True, False, False]


def test_a_box_straddling_the_edge_is_kept():
    camera = _camera_at([0, 0, 0], 500.0)
    planes = frustum_planes(_view_projection(camera))

    # Centre is far off to the side, but the box is wide enough to reach the view.
    visible = boxes_visible(planes, np.array([[20000, 0, 0]], dtype=np.float32),
                            np.array([[20000, 20000, 20000]], dtype=np.float32))

    assert bool(visible[0])


def test_nothing_is_culled_when_the_camera_frames_the_whole_scene():
    camera = _camera_at([0, 0, 0], 20000.0)
    planes = frustum_planes(_view_projection(camera))

    rng = np.random.default_rng(0)
    centers = rng.uniform(-2000, 2000, size=(200, 3)).astype(np.float32)
    extents = np.full((200, 3), 32.0, dtype=np.float32)

    assert boxes_visible(planes, centers, extents).all()


def test_boxes_visible_handles_an_empty_scene():
    camera = _camera_at([0, 0, 0], 500.0)
    planes = frustum_planes(_view_projection(camera))

    assert len(boxes_visible(planes, np.zeros((0, 3)), np.zeros((0, 3)))) == 0


def test_transformed_box_re_encloses_a_translated_source_space_mesh():
    # A 32-unit cube in Source space, moved 100 along Source +Y.
    model = np.eye(4, dtype=np.float32)
    model[3, :3] = (0.0, 100.0, 0.0)

    center, extent = transformed_box([-16, -16, -16], [16, 16, 16], model @ SOURCE2_TO_GL)

    # Source (x, y, z) becomes GL (x, z, -y), so +Y in Source is -Z in GL.
    assert np.allclose(center, [0.0, 0.0, -100.0], atol=1e-4)
    assert np.allclose(extent, [16.0, 16.0, 16.0], atol=1e-4)


def test_transformed_box_grows_to_cover_a_rotated_mesh():
    from gui.editors.smartprop_editor.viewport_3d.camera import rotation_matrix_euler

    model = rotation_matrix_euler(0.0, 45.0, 0.0) @ SOURCE2_TO_GL
    _, extent = transformed_box([-10, -10, -10], [10, 10, 10], model)

    # Rotating a cube 45 degrees widens its axis-aligned envelope by about sqrt(2).
    assert np.allclose(sorted(extent), [10.0, 14.142, 14.142], atol=1e-2)


def test_culling_a_real_scene_keeps_only_what_is_in_front_of_the_camera():
    # A grid of props spread over the map, viewed from one corner.
    camera = _camera_at([0, 0, 0], 800.0, yaw=0.0, pitch=0.0)
    planes = frustum_planes(_view_projection(camera))

    grid = np.array([[x, 0, z] for x in range(-5000, 5001, 500)
                     for z in range(-5000, 5001, 500)], dtype=np.float32)
    extents = np.full((len(grid), 3), 24.0, dtype=np.float32)

    visible = boxes_visible(planes, grid, extents)
    # A narrow view of a wide grid must discard the bulk of it, but keep something.
    assert 0 < visible.sum() < len(grid) * 0.5
