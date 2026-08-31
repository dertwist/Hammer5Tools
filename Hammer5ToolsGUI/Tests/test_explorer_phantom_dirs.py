"""An Explorer must not invent the addon it was pointed at.

The Audio Editor is constructed before the addon name is resolved, so it can be
handed <cs2>/content/csgo_addons/addon/sounds. Creating that chain made the addon
list treat "addon" as a genuine addon, and the app then stuck to it permanently.
"""
import pytest
from PySide6.QtWidgets import QApplication

from gui.widgets.explorer.main import Explorer


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_addon_that_does_not_exist_is_not_created(qapp, tmp_path):
    ghost = tmp_path / "csgo_addons" / "addon" / "sounds"

    explorer = Explorer(tree_directory=str(ghost), addon="addon", editor_name="test")

    assert not ghost.exists()
    assert not ghost.parent.exists(), "the phantom addon folder itself must not appear"
    # An invalid root index makes QTreeView fall back to listing the drive letters.
    assert explorer.tree.isHidden()


def test_folder_inside_an_existing_addon_is_still_created(qapp, tmp_path):
    addon = tmp_path / "csgo_addons" / "de_swamp"
    addon.mkdir(parents=True)
    sounds = addon / "sounds"

    explorer = Explorer(tree_directory=str(sounds), addon="de_swamp", editor_name="test")

    assert sounds.is_dir()
    assert not explorer.tree.isHidden()


def test_no_directory_browses_nothing(qapp):
    """With no addon selected the path helpers return None, so an editor can hand the
    Explorer nothing at all. That used to root it at the app's working directory."""
    import os

    explorer = Explorer(tree_directory=None, addon="", editor_name="test")

    assert explorer.tree_directory == ""
    assert explorer.tree.isHidden()
    assert not os.path.isdir(os.path.join(os.getcwd(), "csgo_addons"))
