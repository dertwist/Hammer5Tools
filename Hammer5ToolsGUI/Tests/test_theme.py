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


def test_combobox_alternate_background_present_in_compiled_qss():
    qss = compile_stylesheet(theme.STANDARD_THEME)
    assert "QComboBox QAbstractItemView::item:alternate" in qss
    assert "alternate-background-color" in qss
    assert "qproperty-alternatingRowColors: true;" in qss


def test_legacy_dark_level_falls_back_to_standard():
    theme.set_level(1)
    try:
        assert theme.get_theme() is theme.STANDARD_THEME
        assert theme.selected() == theme.LEVEL_STANDARD
    finally:
        theme.set_level(theme.LEVEL_STANDARD)


def test_system_level_resolves_to_an_explicit_theme():
    theme.set_level(theme.LEVEL_SYSTEM)
    try:
        assert theme.selected() == theme.LEVEL_SYSTEM
        assert theme.level() in (theme.LEVEL_STANDARD, theme.LEVEL_BRIGHT)
        assert theme.level() == theme.system_level()
    finally:
        theme.set_level(theme.LEVEL_STANDARD)


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
    # Anchored on the header components, not on the bare object names: an
    # unscoped QFrame#frame in the one global sheet reaches every .ui that
    # names a frame "frame" and outranks the [h5Component] rules on
    # specificity. See test_smartprop_property_zoo.
    assert 'QFrame[h5Component="smartpropHeaderFrame"] > QLabel#label' in qss
    assert 'QFrame[h5Component="smartpropHeaderFrame"] > QCheckBox#show_child' in qss
    assert 'QFrame[h5Component="smartpropHeaderFrame"] > QLineEdit#variable_name' in qss
    assert 'QFrame[h5Component="smartpropGroupHeaderFrame"] > QPushButton#add_button' in qss
    assert 'h5Component="smartpropPropertyFrame"' in qss
    assert 'h5Component="smartpropGroupHeaderFrame"' in qss
    assert 'h5Component="smartpropVariableBody"' in qss
    assert 'h5Component="smartpropDisplayNameFrame"' in qss
    assert 'h5Component="smartpropFrameLayout"' in qss
    assert "h5VarKind=\"string\"" in qss
    assert "h5VarKind=\"bool\"" in qss
    assert "h5VarKind=\"float\"" in qss


def test_soundevent_property_headers_present_in_compiled_qss():
    qss = compile_stylesheet(theme.STANDARD_THEME)
    assert 'h5Component="soundeventPropertyHeader"' in qss
    assert "QFrame#header QLabel#label_2" in qss
    assert "QFrame#header QCheckBox#show_child" in qss
    assert "QFrame#header QToolButton#gf" in qss
    assert "QFrame#header QLineEdit#property_class" in qss
    assert "QFrame#header QLineEdit#element_id_display" in qss
    assert "QFrame#header QPushButton#delete_button" in qss
    assert "QFrame#header QPushButton#copy_button" in qss


def test_status_line_console_label_present_in_compiled_qss():
    qss = compile_stylesheet(theme.STANDARD_THEME)
    assert "QLabel#console_label" in qss
    assert f"color: {theme.STANDARD_THEME.text_muted};" in qss


def test_mapbuilder_is_styled_through_the_shared_theme():
    """Map Builder used to carry its own hardcoded palette (a teal DesignColors
    class and inline setStyleSheet calls). Its chrome now lives in
    features/mapbuilder.qss like every other feature, so it follows the theme."""
    qss = compile_stylesheet(theme.STANDARD_THEME)
    for component in (
        "mapbuilderOutput",
        "mapbuilderMonitorFrame",
        "mapbuilderGroupHeader",
        "mapbuilderMapList",
        "mapbuilderPreset",
        "systemMonitor",
    ):
        assert f'h5Component="{component}"' in qss
    assert "#32B8C6" not in qss, "the teal DesignColors accent is back"


def test_progress_bar_is_styled_in_compiled_qss():
    """QProgressBar uses the compact Map Builder progress bar style globally."""
    qss = compile_stylesheet(theme.STANDARD_THEME)
    assert "QProgressBar {" in qss
    assert "border: 1px solid" in qss
    assert "font-size: 10px;" in qss
    assert "QProgressBar::chunk {" in qss
    assert "background-color: #1a528a;" in qss


def test_mapbuilder_chart_colours_change_with_the_theme():
    chart_colours = ("#ff5a5a", "#ffd700", "#32b8c6")
    for canonical in chart_colours:
        assert theme.resolve_hex(theme.BRIGHT_THEME, canonical) != canonical




def test_qss_fragments_carry_no_literal_colours():
    """Every colour in QSS must be a @token so it can vary per theme.

    A literal `#rrggbb` or `rgb(...)` is frozen at the Standard palette and
    silently ignores the brightness setting.
    """
    import re
    from pathlib import Path

    qss_root = Path(__file__).resolve().parents[1] / "gui" / "styles" / "qss"
    literal = re.compile(r'#[0-9a-fA-F]{6}\b|\brgb\(\s*\d{1,3}\s*,')
    offenders = []
    for path in sorted(qss_root.rglob("*.qss")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if literal.search(line):
                offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert not offenders, "literal colours in QSS:\n" + "\n".join(offenders)


def test_bright_theme_darkens_foreground_feature_colours():
    """Pale accents designed for a dark background must not survive into Bright."""
    for canonical in ("#ffbdbe", "#b5ffef", "#ffd199", "#81c784", "#4ec9b0"):
        bright = theme.resolve_hex(theme.BRIGHT_THEME, canonical)
        assert bright != canonical, f"{canonical} has no Bright counterpart"
        assert int(bright[1:3], 16) + int(bright[3:5], 16) + int(bright[5:7], 16) < \
               int(canonical[1:3], 16) + int(canonical[3:5], 16) + int(canonical[5:7], 16)


def test_audio_editor_meter_shades_have_bright_counterparts():
    """The level meters paint canonical hexes; each needs a Bright counterpart."""
    for canonical in ("#242428", "#32c85a", "#dcc832", "#e63232",
                      "#4b525f", "#4ba0f0", "#ff5050", "#ffd54f", "#ffc850"):
        assert theme.resolve_hex(theme.BRIGHT_THEME, canonical) != canonical, canonical


def test_audio_editor_painters_carry_no_literal_colours():
    """The VU meters and waveform used raw RGB literals, so they stayed dark on
    Bright while the rest of the editor followed the theme. QPainter and
    pyqtgraph colours must come from theme.color()/qcolor() or a token."""
    from pathlib import Path

    editor = Path(__file__).resolve().parents[1] / "gui" / "editors" / "soundevent_editor"
    literal = re.compile(r"QColor\(\s*(?:\d|0x)|mk(?:Pen|Brush)\(\s*\(")
    offenders = []
    for name in ("audio_player.py", "wave_editor.py"):
        path = editor / name
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if literal.search(line):
                offenders.append(f"{name}:{number}: {line.strip()}")
    assert not offenders, "literal colours in audio painters:\n" + "\n".join(offenders)


def test_vintage_theme_is_registered_and_olive():
    """Vintage Steam recolours the whole chrome; every neutral must land on the
    olive ramp, not stay a grey the palette forgot to map."""
    vintage = theme.get_theme(theme.LEVEL_VINTAGE)

    assert theme.THEMES[theme.LEVEL_VINTAGE] is vintage
    for token in ("background", "surface", "surface_input", "border", "selection"):
        red, green, blue = (int(getattr(vintage, token)[i:i + 2], 16) for i in (1, 3, 5))
        assert green > red > blue, f"{token} is not an olive green"


def test_vintage_theme_covers_every_canonical_shade():
    """A canonical shade with no Vintage counterpart falls through as its dark
    grey and punches a hole in the olive."""
    missing = [canonical for canonical, _ in theme.BRIGHT_THEME.palette
               if theme.resolve_hex(theme.VINTAGE_THEME, canonical) == canonical]
    assert not missing, "no Vintage counterpart for: " + ", ".join(missing)


def test_set_style_property_supports_item_views():
    """QAbstractItemView defines update(QModelIndex), shadowing QWidget.update().
    set_style_property must use QWidget.update(widget) so it works on list/table/tree views."""
    from PySide6.QtWidgets import QApplication, QListWidget, QTableView, QTreeWidget
    from gui.styles.common import set_style_property

    _app = QApplication.instance() or QApplication([])
    for widget in (QListWidget(), QTableView(), QTreeWidget()):
        set_style_property(widget, "h5Component", "testView")
        assert widget.property("h5Component") == "testView"
