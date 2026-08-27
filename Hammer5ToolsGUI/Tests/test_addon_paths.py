"""The addon path helpers in gui.settings.common."""
import sys
from pathlib import Path

sys.path.insert(0, "Hammer5ToolsGUI")

from gui.settings import common


def _configure(monkeypatch, cs2="C:/cs2", addon="my_addon"):
    monkeypatch.setattr(common, "get_cs2_path", lambda: cs2)
    monkeypatch.setattr(common, "get_addon_name", lambda: addon)


def test_content_and_game_dirs(monkeypatch):
    _configure(monkeypatch)
    assert common.addon_content_dir() == Path("C:/cs2/content/csgo_addons/my_addon")
    assert common.addon_game_dir() == Path("C:/cs2/game/csgo_addons/my_addon")
    assert common.addon_content_dir("other") == Path("C:/cs2/content/csgo_addons/other")
    assert common.cs2_bin_dir() == Path("C:/cs2/game/bin/win64")


def test_missing_configuration_gives_none(monkeypatch):
    _configure(monkeypatch, cs2=None)
    assert common.addon_content_dir() is None
    assert common.addon_game_dir() is None
    assert common.cs2_bin_dir() is None
    assert common.get_addon_dir() is None

    _configure(monkeypatch, addon=None)
    assert common.addon_content_dir() is None
    # An explicit addon still resolves when only the default is unset.
    assert common.addon_content_dir("other") == Path("C:/cs2/content/csgo_addons/other")


def test_get_addon_dir_is_the_string_form(monkeypatch):
    _configure(monkeypatch)
    assert common.get_addon_dir() == str(Path("C:/cs2/content/csgo_addons/my_addon"))
