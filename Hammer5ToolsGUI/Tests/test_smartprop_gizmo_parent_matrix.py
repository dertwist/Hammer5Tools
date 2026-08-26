import numpy as np

from gui.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea


def test_resolve_parent_world_matrix_walks_up_to_nearest_evaluated_ancestor():
    # Hierarchy: root -> group(1) -> group(2, not evaluated by Core) -> element(3)
    parent_id_by_id = {1: 0, 2: 1, 3: 2}
    group_matrix = np.eye(4, dtype=np.float32)
    group_matrix[3, :3] = [10.0, 0.0, 0.0]
    id_to_world = {1: group_matrix}  # group(2) missing: unevaluated ancestor

    resolved = SmartProp3DRenderArea._resolve_parent_world_matrix(3, parent_id_by_id, id_to_world)

    assert np.array_equal(resolved, group_matrix)


def test_resolve_parent_world_matrix_defaults_to_identity_at_root():
    resolved = SmartProp3DRenderArea._resolve_parent_world_matrix(1, {1: 0}, {})

    assert np.array_equal(resolved, np.eye(4, dtype=np.float32))


if __name__ == "__main__":
    test_resolve_parent_world_matrix_walks_up_to_nearest_evaluated_ancestor()
    test_resolve_parent_world_matrix_defaults_to_identity_at_root()
    print("ok")
