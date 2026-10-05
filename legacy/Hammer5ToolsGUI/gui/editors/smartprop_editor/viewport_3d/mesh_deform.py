"""
CPU-side per-vertex mesh warping for models placed under an active, non-rigid
SmartProp deformer (see ``core.bridge.core.SmartPropDeformer``).

Core computes the deformation cage but has no mesh data of its own — the model's
raw vertex positions only exist here, on the GUI side, once loaded from the
compiled .vmdl. So the actual per-vertex warp has to happen here too. This
mirrors Core's ``SmartPropBendDeformerEvaluator.EvaluateCagePosition`` formula
exactly (trilinear blend of 4 cubic-Bezier edges along local X); keep the two in
sync if that formula ever changes.

All matrices here follow the same row-vector convention as the rest of the
viewport (``v_row @ M``, chained left-to-right child-then-parent) — see
``camera.py``'s module docstring.
"""
import numpy as np


def _cubic_bezier(p0, p1, p2, p3, t):
    """Evaluate a cubic Bezier at parameter t: (N,) array; p0..p3: (3,) control points."""
    one_minus_t = 1.0 - t
    return (
        (one_minus_t ** 3)[:, None] * p0
        + (3.0 * one_minus_t ** 2 * t)[:, None] * p1
        + (3.0 * one_minus_t * t ** 2)[:, None] * p2
        + (t ** 3)[:, None] * p3
    )


def evaluate_cage_positions(deformer, points: np.ndarray) -> np.ndarray:
    """Warp (N, 3) points, already in the deformer's volume-local space, through its cage."""
    size = np.asarray(deformer.size, dtype=np.float64)
    control_points = np.asarray(deformer.control_points, dtype=np.float64)  # (8, 3)
    midpoints = np.asarray(deformer.midpoints, dtype=np.float64)  # (8, 3)

    n = len(points)

    def fraction(axis):
        if size[axis] <= 1e-4:
            return np.zeros(n, dtype=np.float64)
        return points[:, axis] / size[axis]

    x_frac, y_frac, z_frac = fraction(0), fraction(1), fraction(2)

    edge00 = _cubic_bezier(control_points[0], midpoints[0], midpoints[1], control_points[4], x_frac)
    edge10 = _cubic_bezier(control_points[1], midpoints[2], midpoints[3], control_points[5], x_frac)
    edge01 = _cubic_bezier(control_points[2], midpoints[4], midpoints[5], control_points[6], x_frac)
    edge11 = _cubic_bezier(control_points[3], midpoints[6], midpoints[7], control_points[7], x_frac)

    lower = edge00 + (edge10 - edge00) * y_frac[:, None]
    upper = edge01 + (edge11 - edge01) * y_frac[:, None]
    return lower + (upper - lower) * z_frac[:, None]


def _to_homogeneous(points: np.ndarray) -> np.ndarray:
    return np.hstack([points, np.ones((len(points), 1), dtype=np.float64)])


def deform_mesh_vertices(vertices: np.ndarray, world_matrix: np.ndarray, deformer) -> np.ndarray | None:
    """Warp a model's own mesh-local vertex positions to follow its deformer.

    ``world_matrix`` is the model's *undeformed* placement (Core leaves it straight
    for a non-rigid model precisely so the mesh can be warped instead). Returns
    None if the deformer's frames are degenerate (zero/mirrored scale) rather than
    raising, matching this viewport's general policy of skipping instead of
    crashing the render loop on bad input.
    """
    try:
        world = np.asarray(world_matrix, dtype=np.float64).reshape(4, 4)
        deformer_frame = np.asarray(deformer.deformer_frame, dtype=np.float64).reshape(4, 4)
        volume_frame = np.asarray(deformer.volume_frame, dtype=np.float64).reshape(4, 4)
        inv_world = np.linalg.inv(world)
        inv_deformer_frame = np.linalg.inv(deformer_frame)
        inv_volume_frame = np.linalg.inv(volume_frame)
    except np.linalg.LinAlgError:
        return None

    to_volume = world @ inv_deformer_frame @ inv_volume_frame
    from_volume = volume_frame @ deformer_frame @ inv_world

    homogeneous = _to_homogeneous(np.asarray(vertices, dtype=np.float64))
    volume_points = (homogeneous @ to_volume)[:, :3]
    deformed_volume_points = evaluate_cage_positions(deformer, volume_points)
    deformed_local = _to_homogeneous(deformed_volume_points) @ from_volume
    return deformed_local[:, :3].astype(np.float32)
