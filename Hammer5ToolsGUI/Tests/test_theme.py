"""Tests for the explicit per-level application theme."""

import re

from gui.styles import theme
from gui.styles.qss_compiler import compile_stylesheet


def test_bright_theme_uses_off_white_surfaces_and_dark_text():
    bright = theme.get_theme(theme.LEVEL_BRIGHT)

    assert bright.background == "#d1d1d1"
    assert bright.surface == "#d8d8d8"
    assert bright.text == "#1a1a1a"
    assert bright.accent == "#366fb5"


def test_bright_theme_has_matching_viewport_clear_color():
    theme.set_level(theme.LEVEL_BRIGHT)
    try:
        assert theme.gl_clear_color() == (0.82, 0.82, 0.82)
    finally:
        theme.set_level(theme.LEVEL_STANDARD)


def test_all_explicit_themes_compile_without_unresolved_tokens():
    for selected in theme.THEMES.values():
        qss = compile_stylesheet(selected)
        assert not re.search(r"@[A-Za-z_]\w*", qss)


def test_theme_exposes_shared_control_metrics():
    standard = theme.STANDARD_THEME

    assert standard.control_height == "22px"
    assert standard.spacing_unit == "4px"
    assert standard.radius == "2px"
    assert standard.border_width == "2px"
    assert standard.icon_size == "16px"


def test_compiled_qss_does_not_contain_invalid_combobox_item_pseudo_state():
    qss = compile_stylesheet(theme.STANDARD_THEME)
    assert "QComboBox:item" not in qss


def test_dark_theme_matches_pre_brightening_palette():
    dark = theme.get_theme(theme.LEVEL_DARK)
    assert dark.background == "#1c1c1c"
    assert dark.surface == "#151515"
    assert dark.surface_raised == "#1d1d1f"
    assert dark.surface_input == "#242426"
    assert dark.border == "#363639"
    assert dark.border_strong == "#505050"
    assert dark.selection == "#414956"
    assert dark.accent == "#3a78c4"
    assert dark.text == "#e3e3e3"


def test_standard_theme_matches_canonical_palette():
    standard = theme.get_theme(theme.LEVEL_STANDARD)
    assert standard.background == "#2e2e2e"
    assert standard.surface == "#272727"
    assert standard.surface_raised == "#2f2f31"
    assert standard.surface_input == "#363637"
    assert standard.border == "#464649"
    assert standard.border_strong == "#5e5e5e"
    assert standard.selection == "#515965"
    assert standard.accent == "#4a83c9"
    assert standard.accent_hover == "#586776"
    assert standard.accent_pressed == "#6d7882"
    assert standard.text == "#e5e5e5"


def test_smartprop_headers_present_in_compiled_qss():
    qss = compile_stylesheet(theme.STANDARD_THEME)
    assert "QFrame#frame > QLabel#label" in qss
    assert "QFrame#frame > QCheckBox#show_child" in qss
    assert "QFrame#frame > QLineEdit#variable_name" in qss
    assert "QFrame#frame > QPushButton#add_button" in qss
    assert "QFrame#frame_layout" in qss
    assert "h5VarKind=\"string\"" in qss
    assert "h5VarKind=\"bool\"" in qss
    assert "h5VarKind=\"float\"" in qss


def test_mapbuilder_is_styled_through_the_shared_theme():
    """Map Builder used to carry its own hardcoded palette (a teal DesignColors
    class and inline setStyleSheet calls). Its chrome now lives in
    features/mapbuilder.qss like every other feature, so it follows the theme."""
    qss = compile_stylesheet(theme.STANDARD_THEME)
    for component in (
        "mapbuilderProgressBar",
        "mapbuilderOutput",
        "mapbuilderMonitorFrame",
        "mapbuilderGroupHeader",
        "mapbuilderMapList",
        "mapbuilderPreset",
        "systemMonitor",
    ):
        assert f'h5Component="{component}"' in qss
    assert "#32B8C6" not in qss, "the teal DesignColors accent is back"



