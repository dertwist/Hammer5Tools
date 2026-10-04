"""Tests for automatic Counter-Strike 2 path detection."""

import os
from pathlib import Path

from gui.other.get_cs2_path import (
    is_valid_cs2_path,
    find_counter_strike_path,
    get_steam_library_folders,
)
from gui.settings.common import get_cs2_path


def test_is_valid_cs2_path_falsy():
    assert not is_valid_cs2_path(None)
    assert not is_valid_cs2_path("")
    assert not is_valid_cs2_path("non_existent_directory_12345")


def test_is_valid_cs2_path_requires_game_binary_or_gameinfo(tmp_path):
    # Empty directory
    assert not is_valid_cs2_path(str(tmp_path))

    # Directory with only content
    (tmp_path / "content" / "csgo_addons").mkdir(parents=True)
    assert not is_valid_cs2_path(str(tmp_path))

    # Directory with game/bin/win64/cs2.exe
    cs2_exe = tmp_path / "game" / "bin" / "win64" / "cs2.exe"
    cs2_exe.parent.mkdir(parents=True)
    cs2_exe.write_text("dummy")
    assert is_valid_cs2_path(str(tmp_path))


def test_is_valid_cs2_path_accepts_gameinfo_gi(tmp_path):
    gi = tmp_path / "game" / "csgo" / "gameinfo.gi"
    gi.parent.mkdir(parents=True)
    gi.write_text("dummy")
    assert is_valid_cs2_path(str(tmp_path))


def test_find_counter_strike_path_skips_empty_folder_and_picks_valid_install(tmp_path):
    """
    If an empty or partial CS:GO directory exists in an earlier library (e.g. C: drive),
    find_counter_strike_path must not return it early, but instead continue searching
    and return the library containing the real CS2 install.
    """
    lib1 = tmp_path / "Steam"
    stale_cs2 = lib1 / "steamapps" / "common" / "Counter-Strike Global Offensive"
    stale_cs2.mkdir(parents=True)
    # Stale install only has content, no cs2.exe
    (stale_cs2 / "content").mkdir()

    lib2 = tmp_path / "SteamLibrary"
    valid_cs2 = lib2 / "steamapps" / "common" / "Counter-Strike Global Offensive"
    exe = valid_cs2 / "game" / "bin" / "win64" / "cs2.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("cs2_binary")

    result = find_counter_strike_path([str(lib1), str(lib2)])
    assert result is not None
    assert Path(result).resolve() == valid_cs2.resolve()


def test_find_counter_strike_path_uses_appmanifest_installdir(tmp_path):
    lib = tmp_path / "SteamLibrary"
    steamapps = lib / "steamapps"
    steamapps.mkdir(parents=True)

    manifest = steamapps / "appmanifest_730.acf"
    manifest.write_text(
        '"AppState"\n{\n\t"appid"\t"730"\n\t"installdir"\t"Custom CS2 Folder"\n}\n',
        encoding="utf-8",
    )

    custom_cs2 = steamapps / "common" / "Custom CS2 Folder"
    exe = custom_cs2 / "game" / "bin" / "win64" / "cs2.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("cs2_binary")

    result = find_counter_strike_path([str(lib)])
    assert result is not None
    assert Path(result).resolve() == custom_cs2.resolve()


def test_get_steam_library_folders_parses_vdf_and_prioritizes_cs2(tmp_path):
    steam_root = tmp_path / "Steam"
    steamapps = steam_root / "steamapps"
    steamapps.mkdir(parents=True)

    lib_other = tmp_path / "OtherLibrary"
    lib_other.mkdir(parents=True)

    lib_cs2 = tmp_path / "Cs2Library"
    lib_cs2.mkdir(parents=True)

    vdf = steamapps / "libraryfolders.vdf"
    vdf_content = f'''"libraryfolders"
{{
    "0"
    {{
        "path" "{str(steam_root).replace(chr(92), chr(92)*2)}"
        "apps"
        {{
            "228980" "100"
        }}
    }}
    "1"
    {{
        "path" "{str(lib_other).replace(chr(92), chr(92)*2)}"
        "apps"
        {{
            "400" "200"
        }}
    }}
    "2"
    {{
        "path" "{str(lib_cs2).replace(chr(92), chr(92)*2)}"
        "apps"
        {{
            "730" "300"
        }}
    }}
}}'''
    vdf.write_text(vdf_content, encoding="utf-8")

    folders = get_steam_library_folders(str(steam_root))
    assert len(folders) >= 3
    # The folder with app 730 must be prioritized first
    assert Path(folders[0]).resolve() == lib_cs2.resolve()


def test_get_cs2_path_picks_auto_detected_when_manual_not_set(monkeypatch, tmp_path):
    monkeypatch.setattr("gui.settings.common.get_settings_value", lambda section, key: None)

    fake_cs2 = tmp_path / "cs2_root"
    exe = fake_cs2 / "game" / "bin" / "win64" / "cs2.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("binary")

    monkeypatch.setattr(
        "gui.settings.common.get_counter_strike_path_from_registry",
        lambda: str(fake_cs2),
    )

    detected = get_cs2_path()
    assert detected is not None
    assert Path(detected).resolve() == fake_cs2.resolve()
