import os
import sys
import tempfile
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_dir = os.path.join(repo_root, "src")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.widgets.explorer.main import Explorer


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_resolve_path_relative_forward_slash(qapp):
    with tempfile.TemporaryDirectory() as temp_dir:
        addon_dir = os.path.join(temp_dir, "my_addon")
        target_file = os.path.join(addon_dir, "models", "firewatch", "nature", "rocks", "groupedrock", "grouped_rock_3.vmdl")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w") as f:
            f.write("test")

        explorer = Explorer(tree_directory=addon_dir, addon="my_addon")
        resolved = explorer.resolve_path("models/firewatch/nature/rocks/groupedrock/grouped_rock_3.vmdl")
        assert resolved is not None
        assert os.path.normpath(resolved) == os.path.normpath(target_file)


def test_resolve_path_relative_backward_slash(qapp):
    with tempfile.TemporaryDirectory() as temp_dir:
        addon_dir = os.path.join(temp_dir, "my_addon")
        target_file = os.path.join(addon_dir, "models", "props", "box.vmdl")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w") as f:
            f.write("test")

        explorer = Explorer(tree_directory=addon_dir, addon="my_addon")
        resolved = explorer.resolve_path("models\\props\\box.vmdl")
        assert resolved is not None
        assert os.path.normpath(resolved) == os.path.normpath(target_file)


def test_resolve_path_leading_slash_and_quotes(qapp):
    with tempfile.TemporaryDirectory() as temp_dir:
        addon_dir = os.path.join(temp_dir, "my_addon")
        target_file = os.path.join(addon_dir, "materials", "nature", "grass.vmat")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w") as f:
            f.write("test")

        explorer = Explorer(tree_directory=addon_dir, addon="my_addon")
        resolved = explorer.resolve_path('"/materials/nature/grass.vmat"')
        assert resolved is not None
        assert os.path.normpath(resolved) == os.path.normpath(target_file)

        resolved_single_quote = explorer.resolve_path("'\\materials\\nature\\grass.vmat'")
        assert resolved_single_quote is not None
        assert os.path.normpath(resolved_single_quote) == os.path.normpath(target_file)


def test_resolve_path_compiled_suffix(qapp):
    with tempfile.TemporaryDirectory() as temp_dir:
        addon_dir = os.path.join(temp_dir, "my_addon")
        target_file = os.path.join(addon_dir, "models", "props", "box.vmdl")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w") as f:
            f.write("test")

        explorer = Explorer(tree_directory=addon_dir, addon="my_addon")
        resolved = explorer.resolve_path("models/props/box.vmdl_c")
        assert resolved is not None
        assert os.path.normpath(resolved) == os.path.normpath(target_file)


def test_resolve_path_subfolder_tree_directory(qapp):
    with tempfile.TemporaryDirectory() as temp_dir:
        addon_dir = os.path.join(temp_dir, "my_addon")
        sounds_dir = os.path.join(addon_dir, "sounds")
        target_file = os.path.join(sounds_dir, "ambient", "wind.vsnd")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w") as f:
            f.write("test")

        explorer = Explorer(tree_directory=sounds_dir, addon="my_addon")
        # Relative with sounds/ prefix
        resolved = explorer.resolve_path("sounds/ambient/wind.vsnd")
        assert resolved is not None
        assert os.path.normpath(resolved) == os.path.normpath(target_file)

        # Relative without sounds/ prefix
        resolved2 = explorer.resolve_path("ambient/wind.vsnd")
        assert resolved2 is not None
        assert os.path.normpath(resolved2) == os.path.normpath(target_file)


def test_resolve_path_base_directories(qapp):
    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = os.path.join(temp_dir, "user_content")
        internal_dir = os.path.join(temp_dir, "internal_content")
        target_file = os.path.join(internal_dir, "models", "shared", "tree.vmdl")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w") as f:
            f.write("test")

        explorer = Explorer(
            tree_directory=user_dir,
            base_directories={"User": user_dir, "Internal": internal_dir}
        )
        resolved = explorer.resolve_path("models/shared/tree.vmdl")
        assert resolved is not None
        assert os.path.normpath(resolved) == os.path.normpath(target_file)


def test_goto_clipboard_path_relative(qapp):
    with tempfile.TemporaryDirectory() as temp_dir:
        addon_dir = os.path.join(temp_dir, "my_addon")
        target_file = os.path.join(addon_dir, "models", "firewatch", "nature", "rocks", "groupedrock", "grouped_rock_3.vmdl")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w") as f:
            f.write("test")

        explorer = Explorer(tree_directory=addon_dir, addon="my_addon")
        
        # Put relative path on clipboard
        clipboard = QGuiApplication.clipboard()
        clipboard.setText("models/firewatch/nature/rocks/groupedrock/grouped_rock_3.vmdl")
        
        explorer.goto_clipboard_path()
        selected = explorer.get_selected_files()
        assert len(selected) == 1
        assert os.path.normpath(selected[0]) == os.path.normpath(target_file)
