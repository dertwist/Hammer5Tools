"""Selection and filtering rules for the Unreal asset picker."""
import sys

sys.path.insert(0, "Hammer5ToolsGUI")

from gui.forms.unreal_porter.asset_tree_model import (
    CHECKED,
    PARTIAL,
    UNCHECKED,
    AssetTreeModel,
)

KEYS = [
    "Game/Meshes/rock.uasset",
    "Game/Meshes/tree.uasset",
    "Game/Textures/rock_d.uasset",
]


def _folder(model, name):
    def walk(nodes):
        for node in nodes:
            if not node.is_leaf and node.name == name:
                return node
            if not node.is_leaf:
                found = walk(node.children)
                if found:
                    return found
        return None
    return walk(model.roots)


def test_tree_groups_by_path():
    model = AssetTreeModel(KEYS)
    assert [root.name for root in model.roots] == ["Game"]
    assert sorted(child.name for child in model.roots[0].children) == ["Meshes", "Textures"]
    assert len(model.leaves) == 3


def test_preselection_is_honoured():
    model = AssetTreeModel(KEYS, preselected={"Game/Meshes/rock.uasset"})
    assert model.checked_keys() == {"Game/Meshes/rock.uasset"}


def test_folder_state_is_derived_from_its_leaves():
    model = AssetTreeModel(KEYS)
    meshes = _folder(model, "Meshes")
    assert model.state_of(meshes) == UNCHECKED

    model.set_checked(meshes, True)
    assert model.state_of(meshes) == CHECKED
    assert model.state_of(model.roots[0]) == PARTIAL

    model.set_checked(_folder(model, "Textures"), True)
    assert model.state_of(model.roots[0]) == CHECKED


def test_partial_state_when_only_some_leaves_are_checked():
    model = AssetTreeModel(KEYS)
    rock = next(leaf for leaf in model.leaves if leaf.name == "rock.uasset")
    model.set_checked(rock, True)
    assert model.state_of(_folder(model, "Meshes")) == PARTIAL


def test_a_folder_tick_skips_rows_the_filter_hides():
    """The user cannot see a filtered-out row and did not mean to include it."""
    model = AssetTreeModel(KEYS)
    model.apply_filter("rock", lambda key: True)
    model.set_checked(_folder(model, "Meshes"), True)
    assert model.checked_keys() == {"Game/Meshes/rock.uasset"}


def test_set_all_skips_hidden_rows_too():
    model = AssetTreeModel(KEYS)
    model.apply_filter("tree", lambda key: True)
    model.set_all(True)
    assert model.checked_keys() == {"Game/Meshes/tree.uasset"}


def test_filter_hides_folders_left_empty():
    model = AssetTreeModel(KEYS)
    model.apply_filter("tree", lambda key: True)   # matches Meshes/tree only
    assert _folder(model, "Meshes").visible
    assert not _folder(model, "Textures").visible
    assert model.roots[0].visible


def test_type_filter_and_name_filter_both_apply():
    model = AssetTreeModel(KEYS)
    model.apply_filter("", lambda key: "Textures" not in key)
    visible = {leaf.key for leaf in model.leaves if leaf.visible}
    assert visible == {"Game/Meshes/rock.uasset", "Game/Meshes/tree.uasset"}


def test_clearing_the_filter_restores_everything():
    model = AssetTreeModel(KEYS)
    model.apply_filter("tree", lambda key: True)
    model.apply_filter("", lambda key: True)
    assert all(leaf.visible for leaf in model.leaves)
    assert _folder(model, "Textures").visible


def test_hidden_rows_keep_their_tick():
    """Filtering is a view concern; it must not silently deselect."""
    model = AssetTreeModel(KEYS, preselected={"Game/Textures/rock_d.uasset"})
    model.apply_filter("tree", lambda key: True)
    assert model.checked_keys() == {"Game/Textures/rock_d.uasset"}


def test_the_model_does_not_import_qt():
    import subprocess

    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, 'Hammer5ToolsGUI');"
         " import gui.forms.unreal_porter.asset_tree_model;"
         " print('PySide6' in sys.modules)"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
