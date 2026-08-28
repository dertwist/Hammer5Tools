"""GUI safety tests: the application must survive missing CS2, missing addons,
and every gui/ module must import without errors.

All tests are pure-Python with monkeypatch.  No QApplication is needed.
"""

import importlib
import os
from pathlib import Path

import pytest

from gui.settings import common as settings_common
from gui.shell.addon_selector import list_addons
from gui.shell.editors import EditorSlot, register_builders


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GUI_ROOT = Path(__file__).resolve().parents[1] / "gui"

# Modules that trigger app lifecycle, compile resources, or rely on a running
# QApplication when imported at the top level.
_SKIP_MODULES = frozenset({
    "gui.main",
    "gui.resources_rc",
})


def _gui_module_names():
    """Yield dotted module names for every .py file under gui/."""
    for dirpath, _dirnames, filenames in os.walk(_GUI_ROOT):
        rel = Path(dirpath).relative_to(_GUI_ROOT.parent)
        package = ".".join(rel.parts)
        for filename in filenames:
            if not filename.endswith(".py") or filename == "__init__.py":
                continue
            module = f"{package}.{filename[:-3]}"
            yield module


# ---------------------------------------------------------------------------
# 1. Import safety
# ---------------------------------------------------------------------------

import subprocess
import sys

_ALL_MODULES = sorted(_gui_module_names())

def test_gui_modules_importable():
    """Every gui/ module must import without ImportError or SyntaxError.
    
    Runs in a subprocess to avoid polluting PySide6 global state in the pytest process.
    """
    to_check = []
    for module_name in _ALL_MODULES:
        if module_name in _SKIP_MODULES:
            continue
        basename = module_name.rsplit(".", 1)[-1]
        if basename.startswith("ui_"):
            continue
        to_check.append(module_name)
        
    code = "import sys, os\nsys.path.insert(0, os.path.abspath('Hammer5ToolsGUI'))\n"
    code += "\n".join(f"import {m}" for m in to_check)
    result = subprocess.run(
        [sys.executable, "-c", code], 
        capture_output=True, 
        text=True
    )
    assert result.returncode == 0, f"Import failed:\\n{result.stderr}"


# ---------------------------------------------------------------------------
# 2. No CS2 path
# ---------------------------------------------------------------------------

def test_cs2_path_helpers_return_none_without_cs2(monkeypatch):
    """When CS2 is not installed, every derived path helper returns None."""
    monkeypatch.setattr(settings_common, "get_cs2_path", lambda: None)
    assert settings_common.addon_content_dir() is None
    assert settings_common.addon_game_dir() is None
    assert settings_common.cs2_bin_dir() is None
    assert settings_common.cs2_addons_dir() is None
    assert settings_common.get_addon_dir() is None


def test_list_addons_returns_empty_without_cs2(monkeypatch):
    """list_addons must return [] when CS2 is not installed."""
    monkeypatch.setattr(settings_common, "get_cs2_path", lambda: None)
    assert list_addons(None) == []


def test_editor_slots_gate_cs2_editors():
    """CS2-gated editor slots must not be registered when CS2 is unavailable."""

    class _Page:
        pass

    slots = (
        EditorSlot("always", "Always", _Page(), lambda: None),
        EditorSlot("gated", "Gated", _Page(), lambda: None, requires_cs2=True),
    )

    builders_without = {}
    register_builders(slots, builders_without, cs2_available=False)
    assert list(builders_without) == [slots[0].page]

    builders_with = {}
    register_builders(slots, builders_with, cs2_available=True)
    assert list(builders_with) == [slots[0].page, slots[1].page]


# ---------------------------------------------------------------------------
# 3. No available addons
# ---------------------------------------------------------------------------

def test_list_addons_returns_empty_for_nonexistent_dir():
    """A CS2 path that does not exist on disk must produce an empty addon list."""
    assert list_addons("Z:/nonexistent/path/to/cs2") == []


def test_addon_helpers_return_none_without_addon_name(monkeypatch):
    """When no addon is selected, addon_content_dir and addon_game_dir return None."""
    monkeypatch.setattr(settings_common, "get_cs2_path", lambda: "C:/cs2")
    monkeypatch.setattr(settings_common, "get_addon_name", lambda: None)
    assert settings_common.addon_content_dir() is None
    assert settings_common.addon_game_dir() is None
