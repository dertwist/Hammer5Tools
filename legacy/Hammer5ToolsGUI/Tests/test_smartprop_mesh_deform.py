"""Cross-checks for the CPU-side cage warp in mesh_deform.py against known-shape cages.

mesh_deform.evaluate_cage_positions/deform_mesh_vertices mirror
SmartPropBendDeformerEvaluator's EvaluateCagePosition/EvaluateCage formula in
Hammer5Tools.Core (trilinear blend of 4 cubic-Bezier edges along local X) — Core
computes the cage, but only the GUI has the mesh vertices to warp with it.
"""
import numpy as np

from core.bridge.core import SmartPropDeformer
from gui.editors.smartprop_editor.viewport_3d.mesh_deform import (
    deform_mesh_vertices,
    evaluate_cage_positions,
)

IDENTITY = tuple(
    1.0 if row == column else 0.0
    for row in range(4)
    for column in range(4)
)


def _linear_deformer(start, end, size):
    """A cage whose local-X edges are made exactly linear (Bezier handles at 1/3
    and 2/3 along the straight line), so evaluate_cage_positions reduces to plain
    trilinear interpolation between start and end — a clean check of the lerp
    machinery, independent of the bend-specific curve-fitting math it's normally
    fed with."""
    start = np.array(start, dtype=np.float64)
    end = np.array(end, dtype=np.float64)
    third = start + (end - start) / 3.0
    two_thirds = start + 2.0 * (end - start) / 3.0
    control_points = tuple(tuple(p) for p in (start, start, start, start, end, end, end, end))
    midpoints = tuple(tuple(p) for p in (third, two_thirds) * 4)
    return SmartPropDeformer(size, control_points, midpoints, IDENTITY, IDENTITY)


def test_evaluate_cage_positions_reduces_to_linear_interpolation():
    deformer = _linear_deformer((0.0, 0.0, 0.0), (20.0, 0.0, 0.0), (10.0, 10.0, 10.0))

    points = np.array([[0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [10.0, 0.0, 0.0]], dtype=np.float64)
    deformed = evaluate_cage_positions(deformer, points)

    np.testing.assert_allclose(deformed, [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [20.0, 0.0, 0.0]], atol=1e-6)


def test_deform_mesh_vertices_with_identity_frames_matches_cage_directly():
    deformer = _linear_deformer((0.0, 0.0, 0.0), (20.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    world_matrix = np.array(IDENTITY, dtype=np.float32).reshape(4, 4)
    vertices = np.array([[5.0, 0.0, 0.0], [10.0, 0.0, 0.0]], dtype=np.float32)

    deformed = deform_mesh_vertices(vertices, world_matrix, deformer)

    np.testing.assert_allclose(deformed, [[10.0, 0.0, 0.0], [20.0, 0.0, 0.0]], atol=1e-4)


def test_deform_mesh_vertices_round_trips_through_a_translated_deformer_frame():
    deformer = _linear_deformer((0.0, 0.0, 0.0), (20.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    # deformer_frame translates volume-space by (5, 0, 0) relative to the mesh's
    # own placement; a vertex sitting exactly at that offset should land at the
    # cage's local origin (0,0,0) pre-warp, i.e. undeformed at x=0.
    deformer_frame = tuple(IDENTITY[i] if i not in (12,) else 5.0 for i in range(16))
    deformer = SmartPropDeformer(
        deformer.size, deformer.control_points, deformer.midpoints, deformer_frame, IDENTITY)
    world_matrix = np.array(IDENTITY, dtype=np.float32).reshape(4, 4)
    vertices = np.array([[5.0, 0.0, 0.0]], dtype=np.float32)

    deformed = deform_mesh_vertices(vertices, world_matrix, deformer)

    np.testing.assert_allclose(deformed, [[5.0, 0.0, 0.0]], atol=1e-4)


def test_deform_mesh_vertices_returns_none_for_degenerate_world_matrix():
    deformer = _linear_deformer((0.0, 0.0, 0.0), (20.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    zero_scale_world = np.zeros((4, 4), dtype=np.float32)
    zero_scale_world[3, 3] = 1.0

    assert deform_mesh_vertices(np.array([[1.0, 0.0, 0.0]], dtype=np.float32), zero_scale_world, deformer) is None
