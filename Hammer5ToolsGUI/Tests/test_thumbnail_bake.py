"""Placement baking for SmartProp thumbnails."""

import numpy as np
import pytest

from gui.editors.smartprop_editor.viewport_3d.mesh_cache import MaterialData, MeshData, SubMeshData
from gui.widgets.model_browser.thumbnails import _bake_placements


def _quad(material_name="mat"):
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
    return MeshData(
        vertices=vertices,
        normals=np.tile(np.array([0, 0, 1], dtype=np.float32), (3, 1)),
        indices=np.array([0, 1, 2], dtype=np.uint32),
        uvs=np.zeros((3, 2), dtype=np.float32),
        bbox_min=vertices.min(axis=0), bbox_max=vertices.max(axis=0),
        submeshes=[SubMeshData(0, 3, MaterialData(name=material_name))])


def _translation(x, y, z):
    matrix = np.eye(4, dtype=np.float32)
    matrix[3, :3] = (x, y, z)      # row-vector style, as Core emits
    return matrix


def test_no_placements_bakes_to_nothing():
    assert _bake_placements([]) is None


def test_placements_are_merged_with_offset_indices_and_world_bounds():
    baked = _bake_placements([
        (_quad("a"), _translation(0, 0, 0)),
        (_quad("b"), _translation(10, 0, 0)),
    ])

    assert len(baked.vertices) == 6
    assert baked.indices.tolist() == [0, 1, 2, 3, 4, 5]
    assert [submesh.index_offset for submesh in baked.submeshes] == [0, 3]
    assert [submesh.material.name for submesh in baked.submeshes] == ["a", "b"]
    assert baked.bbox_min.tolist() == pytest.approx([0.0, 0.0, 0.0])
    assert baked.bbox_max.tolist() == pytest.approx([11.0, 1.0, 0.0])


def test_rotation_carries_into_vertices_and_normals():
    rotate_z = np.eye(4, dtype=np.float32)
    rotate_z[:3, :3] = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]   # +90 deg about Z

    baked = _bake_placements([(_quad(), rotate_z)])

    assert baked.vertices[1].tolist() == pytest.approx([0.0, 1.0, 0.0])
    assert baked.normals[0].tolist() == pytest.approx([0.0, 0.0, 1.0])
