"""Explicit application themes shared by QSS, QPainter, and OpenGL."""

from dataclasses import dataclass, fields

from PySide6.QtGui import QColor

LEVEL_DARK = 1
LEVEL_STANDARD = 2
LEVEL_BRIGHT = 3


@dataclass(frozen=True)
class Theme:
    """Semantic colors, control metrics, and explicit compatibility shades."""

    background: str
    surface: str
    surface_raised: str
    surface_input: str
    text: str
    text_muted: str
    text_disabled: str
    border: str
    border_strong: str
    accent: str
    accent_hover: str
    accent_pressed: str
    selection: str
    selection_text: str
    error: str
    warning: str
    success: str
    control_height: str
    spacing_unit: str
    radius: str
    border_width: str
    icon_size: str
    viewport_clear: tuple[float, float, float]
    palette: tuple[tuple[str, str], ...]
    level: int


_DARK_COLORS = (
    ("#292929", "#161616"), ("#2c2c2c", "#1a1a1a"),
    ("#2e2e2e", "#1c1c1c"), ("#2f2f31", "#1d1d1f"),
    ("#303030", "#1e1e1e"), ("#343434", "#222222"),
    ("#353535", "#232323"), ("#363636", "#242424"),
    ("#363637", "#242426"), ("#373737", "#262626"),
    ("#37373c", "#26262b"), ("#38383a", "#272729"),
    ("#38383b", "#27272a"), ("#3b3a3a", "#2a2929"),
    ("#3b3b3b", "#2a2a2a"), ("#3b3f48", "#2a2e38"),
    ("#3d4d5e", "#2c3e50"), ("#3e3e3e", "#2d2d2d"),
    ("#3e3e41", "#2d2d30"), ("#3e434b", "#2d333b"),
    ("#3f3f42", "#2e2e32"), ("#424242", "#323232"),
    ("#434343", "#333333"), ("#434346", "#333336"),
    ("#43464d", "#33363d"), ("#464649", "#363639"),
    ("#4a4a4a", "#3a3a3a"), ("#4d4d51", "#3d3d42"),
    ("#4d596b", "#3e4b5e"), ("#4f4f4f", "#404040"),
    ("#515965", "#414956"), ("#535353", "#444444"),
    ("#586776", "#4a5a6a"), ("#5d6066", "#4f5259"),
    ("#5e5e5e", "#505050"), ("#636363", "#555555"),
    ("#6d6d6d", "#606060"), ("#727272", "#666666"),
    ("#777777", "#6b6b6b"), ("#787878", "#6c6c6c"),
    ("#797979", "#6d6d6d"), ("#7c7c85", "#71717a"),
    ("#8a8a8a", "#808080"), ("#929292", "#888888"),
    ("#a1a1a1", "#999999"), ("#a2a8b1", "#9aa0aa"),
    ("#a5a5a5", "#9d9d9d"), ("#aaaaaa", "#a3a3a3"),
    ("#b1b1b1", "#aaaaaa"), ("#b2b2b2", "#ababab"),
    ("#b3d096", "#accc8d"), ("#b6b6b6", "#b0b0b0"),
    ("#bebebe", "#b8b8b8"), ("#c0c0c0", "#bababa"),
    ("#cccccc", "#c8c8c8"), ("#d0d0d0", "#cccccc"),
    ("#d4d4d4", "#d0d0d0"), ("#e2e2e2", "#e0e0e0"),
    ("#e5e5e5", "#e3e3e3"),
    ("#1495c0", "#008cba"), ("#252525", "#121212"),
    ("#2a2a2c", "#18181a"), ("#35383e", "#23272d"),
    ("#37373b", "#26262a"), ("#3d3d3d", "#2c2c2c"),
    ("#585858", "#4a4a4a"), ("#5ab55e", "#4caf50"),
    ("#6e727a", "#61666e"), ("#939393", "#8a8a8a"),
    ("#97979c", "#8e8e93"), ("#999999", "#909090"),
    ("#a2a79a", "#9a9f91"), ("#a8a8a8", "#a0a0a0"),
    ("#b3b3b3", "#acacac"), ("#c8c8c8", "#c3c3c3"),
    ("#cfcfcf", "#cbcbcb"),
)

_BRIGHT_COLORS = (
    ("#292929", "#d6d6d6"), ("#2c2c2c", "#d3d3d3"),
    ("#2e2e2e", "#d1d1d1"), ("#2f2f31", "#ceced0"),
    ("#303030", "#cfcfcf"), ("#343434", "#cbcbcb"),
    ("#353535", "#cacaca"), ("#363636", "#c9c9c9"),
    ("#363637", "#c8c8c9"), ("#373737", "#c8c8c8"),
    ("#37373c", "#c3c3c8"), ("#38383a", "#c5c5c7"),
    ("#38383b", "#c4c4c7"), ("#3b3a3a", "#c5c4c4"),
    ("#3b3b3b", "#c4c4c4"), ("#3b3f48", "#b7bbc4"),
    ("#3d4d5e", "#a1b1c2"), ("#3e3e3e", "#c1c1c1"),
    ("#3e3e41", "#bebec1"), ("#3e434b", "#b4b9c1"),
    ("#3f3f42", "#bdbdc0"), ("#424242", "#bdbdbd"),
    ("#434343", "#bcbcbc"), ("#434346", "#b9b9bc"),
    ("#43464d", "#b2b5bc"), ("#464649", "#b6b6b9"),
    ("#4a4a4a", "#b5b5b5"), ("#4d4d51", "#aeaeb2"),
    ("#4d596b", "#94a0b2"), ("#4f4f4f", "#b0b0b0"),
    ("#515965", "#9aa2ae"), ("#535353", "#acacac"),
    ("#586776", "#8998a7"), ("#5d6066", "#999ca2"),
    ("#5e5e5e", "#a1a1a1"), ("#636363", "#9c9c9c"),
    ("#6d6d6d", "#929292"), ("#727272", "#8d8d8d"),
    ("#777777", "#888888"), ("#787878", "#878787"),
    ("#797979", "#868686"), ("#7c7c85", "#7a7a83"),
    ("#8a8a8a", "#757575"), ("#929292", "#6d6d6d"),
    ("#a1a1a1", "#5e5e5e"), ("#a2a8b1", "#4e545d"),
    ("#a5a5a5", "#5a5a5a"), ("#aaaaaa", "#555555"),
    ("#b1b1b1", "#4e4e4e"), ("#b2b2b2", "#4d4d4d"),
    ("#b3d096", "#4c692f"), ("#b6b6b6", "#494949"),
    ("#bebebe", "#414141"), ("#c0c0c0", "#3f3f3f"),
    ("#cccccc", "#333333"), ("#d0d0d0", "#2f2f2f"),
    ("#d4d4d4", "#2b2b2b"), ("#e2e2e2", "#1d1d1d"),
    ("#e5e5e5", "#1a1a1a"), ("#ffffff", "#000000"),
    ("#1495c0", "#3fc0eb"), ("#252525", "#dadada"),
    ("#2a2a2c", "#d3d3d5"), ("#35383e", "#c1c4ca"),
    ("#37373b", "#c4c4c8"), ("#3d3d3d", "#c2c2c2"),
    ("#585858", "#a7a7a7"), ("#5ab55e", "#4aa54e"),
    ("#6e727a", "#858991"), ("#939393", "#6c6c6c"),
    ("#97979c", "#636368"), ("#999999", "#666666"),
    ("#a2a79a", "#606558"), ("#a8a8a8", "#575757"),
    ("#b3b3b3", "#4c4c4c"), ("#c8c8c8", "#373737"),
    ("#cfcfcf", "#303030"),
)


def _make_theme(*, level, palette, viewport_clear, **colors):
    return Theme(
        **colors, control_height="22px", spacing_unit="4px", radius="2px",
        border_width="2px", icon_size="16px", viewport_clear=viewport_clear,
        palette=palette, level=level,
    )


DARK_THEME = _make_theme(
    level=LEVEL_DARK, palette=_DARK_COLORS, viewport_clear=(0.11, 0.11, 0.11),
    background="#1c1c1c", surface="#151515", surface_raised="#1d1d1f",
    surface_input="#242426", text="#e3e3e3", text_muted="#9d9d9d",
    text_disabled="#6d6d6d", border="#363639", border_strong="#505050",
    accent="#3a78c4", accent_hover="#4a5a6a", accent_pressed="#606c77",
    selection="#414956", selection_text="#ffffff", error="#d1494a",
    warning="#e5a00d", success="#4caf50",
)
STANDARD_THEME = _make_theme(
    level=LEVEL_STANDARD, palette=(), viewport_clear=(0.18, 0.18, 0.18),
    background="#2e2e2e", surface="#272727", surface_raised="#2f2f31",
    surface_input="#363637", text="#e5e5e5", text_muted="#a5a5a5",
    text_disabled="#797979", border="#464649", border_strong="#5e5e5e",
    accent="#4a83c9", accent_hover="#586776", accent_pressed="#6d7882",
    selection="#515965", selection_text="#ffffff", error="#d1494a",
    warning="#e5a00d", success="#5ab55e",
)
BRIGHT_THEME = _make_theme(
    level=LEVEL_BRIGHT, palette=_BRIGHT_COLORS, viewport_clear=(0.82, 0.82, 0.82),
    background="#d1d1d1", surface="#d8d8d8", surface_raised="#ceced0",
    surface_input="#c8c8c9", text="#1a1a1a", text_muted="#5a5a5a",
    text_disabled="#868686", border="#b6b6b9", border_strong="#a1a1a1",
    accent="#366fb5", accent_hover="#8998a7", accent_pressed="#7d8892",
    selection="#9aa2ae", selection_text="#000000", error="#d1494a",
    warning="#e5a00d", success="#4aa54e",
)

THEMES = {LEVEL_DARK: DARK_THEME, LEVEL_STANDARD: STANDARD_THEME, LEVEL_BRIGHT: BRIGHT_THEME}
_PALETTE_MAPS = {level: dict(theme.palette) for level, theme in THEMES.items()}
_ACTIVE_THEME = STANDARD_THEME
_NON_TOKEN_FIELDS = {"viewport_clear", "palette", "level"}
TOKEN_NAMES = frozenset(f.name for f in fields(Theme) if f.name not in _NON_TOKEN_FIELDS)


def set_level(level):
    """Select the active explicit theme (invalid values select Standard)."""
    global _ACTIVE_THEME
    try:
        selected = int(level)
    except (TypeError, ValueError):
        selected = LEVEL_STANDARD
    _ACTIVE_THEME = THEMES.get(selected, STANDARD_THEME)


def level():
    return _ACTIVE_THEME.level


def get_theme(level: int | None = None) -> Theme:
    return THEMES.get(level, STANDARD_THEME) if level is not None else _ACTIVE_THEME


def resolve_hex(theme: Theme, canonical: str) -> str:
    palette = _PALETTE_MAPS.get(theme.level)
    if palette is None:
        palette = dict(theme.palette)
    return palette.get(canonical.lower(), canonical)


_RGB_BY_LEVEL = {
    LEVEL_DARK: {
        (135, 135, 135): (125, 125, 125), (112, 112, 112): (100, 100, 100),
        (80, 88, 100): (65, 73, 86), (193, 193, 193): (188, 188, 188),
        (57, 57, 57): (40, 40, 40),
    },
    LEVEL_BRIGHT: {
        (135, 135, 135): (120, 120, 120), (112, 112, 112): (143, 143, 143),
        (80, 88, 100): (155, 163, 175), (193, 193, 193): (62, 62, 62),
        (57, 57, 57): (198, 198, 198),
    },
}


def resolve_rgb(theme: Theme, canonical: tuple[int, int, int]) -> tuple[int, int, int]:
    hex_value = "#%02x%02x%02x" % canonical
    resolved = resolve_hex(theme, hex_value)
    if resolved != hex_value:
        return tuple(int(resolved[index:index + 2], 16) for index in (1, 3, 5))
    return _RGB_BY_LEVEL.get(theme.level, {}).get(canonical, canonical)


def color(canonical: str) -> str:
    return resolve_hex(_ACTIVE_THEME, canonical)


def qcolor(canonical: str) -> QColor:
    return QColor(color(canonical))


def gl_clear_color():
    return _ACTIVE_THEME.viewport_clear
