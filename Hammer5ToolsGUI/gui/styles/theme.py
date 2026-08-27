"""Explicit application themes shared by QSS, QPainter, and OpenGL."""

from dataclasses import dataclass, fields

from PySide6.QtGui import QColor

LEVEL_SYSTEM = 0
LEVEL_STANDARD = 2
LEVEL_BRIGHT = 3
LEVEL_VINTAGE = 4


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
    ("#ff5a5a", "#c84040"), ("#ffd700", "#a87d00"),
    ("#32b8c6", "#167a88"),

    # Feature colours carried over from the QSS fragments. Foregrounds are
    # darkened until they clear 4.5:1 on the Bright background; surfaces and
    # borders mirror their lightness. Hue and saturation are preserved.
    ("#111111", "#eeeeee"),  # bg
    ("#1a1a1c", "#e3e3e5"),  # bg
    ("#1a528a", "#75ade5"),  # bg
    ("#1b5e20", "#a1e4a6"),  # bg
    ("#1d8348", "#7ce2a7"),  # bg
    ("#242424", "#dbdbdb"),  # bg
    ("#2471a3", "#5ca9db"),  # bg
    ("#252527", "#d8d8da"),  # bg
    ("#282828", "#d7d7d7"),  # bg
    ("#2980b9", "#469dd6"),  # bg
    ("#29b6f6", "#055a81"),  # fg
    ("#2d333f", "#c0c6d2"),  # bg
    ("#2e6b9e", "#619ed1"),  # border
    ("#2f2f32", "#cdcdd0"),  # bg
    ("#3498db", "#2488cb"),  # bg
    ("#363639", "#c6c6c9"),  # bg
    ("#383838", "#c7c7c7"),  # bg/border
    ("#3a3a3c", "#c3c3c5"),  # border
    ("#3b3b3e", "#c1c1c4"),  # border
    ("#3e2020", "#dfc1c1"),  # bg
    ("#3e3e42", "#bdbdc1"),  # border
    ("#4ca0ad", "#2d5e66"),  # fg
    ("#555555", "#aaaaaa"),  # border
    ("#666666", "#999999"),  # border
    ("#6a9955", "#415e34"),  # fg
    ("#6c87ff", "#0634ff"),  # fg
    ("#73d1bf", "#206255"),  # fg
    ("#7ac07a", "#2d5f2d"),  # fg
    ("#7dda58", "#2c6416"),  # fg
    ("#7fb800", "#405c00"),  # fg
    ("#8684b8", "#54528e"),  # fg
    ("#8b5e3c", "#c39674"),  # border
    ("#8e44ad", "#9c52bb"),  # bg
    ("#8e8e8e", "#565656"),  # fg
    ("#8fb0ff", "#0045eb"),  # fg
    ("#974533", "#cc7a68"),  # border
    ("#9d9d9d", "#565656"),  # fg
    ("#a0c4ff", "#004cc9"),  # fg
    ("#a375ff", "#5f0fff"),  # fg
    ("#a4b6ef", "#244ccc"),  # fg
    ("#b0a66e", "#91874f"),  # bg
    ("#b5ffef", "#00634e"),  # fg
    ("#b6efa2", "#266211"),  # fg
    ("#c0392b", "#d44d3f"),  # bg
    ("#c1c1c1", "#565656"),  # fg
    ("#c7c7bb", "#595949"),  # fg
    ("#d08a4a", "#7f4e21"),  # fg
    ("#d1494a", "#a82a2b"),  # fg
    ("#d9b34c", "#6b5417"),  # fg
    ("#e53935", "#b21a17"),  # fg
    ("#e5a00d", "#714f06"),  # fg
    ("#e5c07b", "#845f1a"),  # border
    ("#e67e22", "#dd7519"),  # bg
    ("#eca4a0", "#a92922"),  # fg
    ("#ef5350", "#b41410"),  # fg
    ("#f2c94c", "#6a5208"),  # fg
    ("#f44747", "#b60b0b"),  # fg
    ("#f4a9f6", "#96109a"),  # fg
    ("#f6c273", "#774b08"),  # fg
    ("#ff7b7d", "#b80003"),  # fg
    ("#ffb300", "#704f00"),  # fg
    ("#ffbdbe", "#b30003"),  # fg
    ("#ffd199", "#854900"),  # fg

    # Painter, plot and delegate colours resolved via theme.color()/qcolor().
    ("#134f87", "#78b4ec"),  # bg
    ("#1ab8e0", "#1fbde5"),  # bg
    ("#233827", "#c7dccb"),  # bg
    ("#242428", "#c4c4c8"),  # bg - recessed level-meter channel
    ("#2e7d32", "#82d186"),  # border
    ("#32c85a", "#1e8a3f"),  # fg - level meter, safe zone
    ("#3e341b", "#e4dac1"),  # bg
    ("#4ba0f0", "#0d589f"),  # fg
    ("#4b525f", "#a6acb8"),  # fg - unplayed waveform bars
    ("#4ec9b0", "#1d6153"),  # fg
    ("#5aa0e0", "#1b5890"),  # fg
    ("#5fb96a", "#2a5f30"),  # fg
    ("#65666d", "#92939a"),  # border
    ("#81c784", "#2c642f"),  # fg
    ("#c62828", "#d73939"),  # border
    ("#d64545", "#a52424"),  # fg
    ("#dcc832", "#8a7614"),  # fg - level meter, hot zone
    ("#e05656", "#a71f1f"),  # fg
    ("#e0a030", "#704e11"),  # fg
    ("#e57373", "#aa2020"),  # fg
    ("#e63232", "#c01f1f"),  # fg - level meter, clip zone
    ("#e65100", "#9f3800"),  # fg
    ("#f0f0f0", "#c0c0c0"),  # bg - subtle band, stays a band on Bright
    ("#f57f17", "#e8720a"),  # border
    ("#ff5050", "#b60000"),  # fg
    ("#ffc850", "#795300"),  # fg
    ("#ffd54f", "#6e5300"),  # fg
)


#: Every canonical shade re-cut for Vintage Steam. Neutrals are placed on one
#: olive ramp (the 2003 Steam skin's hue, anchored so #2e2e2e reads as the
#: window green and #e5e5e5 stays the text off-white); chromatic shades keep
#: their hue, lose a fifth of their saturation and, when dark, are lifted so
#: they sit on the olive instead of punching holes in it.
_VINTAGE_COLORS = (
    ("#292929", "#545d49"), ("#2c2c2c", "#56604a"),
    ("#2e2e2e", "#58624c"), ("#2f2f31", "#59644d"),
    ("#303030", "#59644d"), ("#343434", "#5c684f"),
    ("#353535", "#5d6950"), ("#363636", "#5e6a51"),
    ("#363637", "#5e6a51"), ("#373737", "#5f6a51"),
    ("#37373c", "#616d53"), ("#38383a", "#606c53"),
    ("#38383b", "#616d53"), ("#3b3a3a", "#626e53"),
    ("#3b3b3b", "#626e54"), ("#3b3f48", "#677458"),
    ("#3d4d5e", "#71805f"), ("#3e3e3e", "#647156"),
    ("#3e3e41", "#657357"), ("#3e434b", "#69775a"),
    ("#3f3f42", "#667357"), ("#424242", "#677558"),
    ("#434343", "#687659"), ("#434346", "#69775a"),
    ("#43464d", "#6c7b5c"), ("#464649", "#6c7a5b"),
    ("#4a4a4a", "#6e7d5d"), ("#4d4d51", "#728160"),
    ("#4d596b", "#7c8e68"), ("#4f4f4f", "#728160"),
    ("#515965", "#7b8d67"), ("#535353", "#758562"),
    ("#586776", "#859770"), ("#5d6066", "#80936b"),
    ("#5e5e5e", "#7e9069"), ("#636363", "#82946c"),
    ("#6d6d6d", "#899a76"), ("#727272", "#8d9d7b"),
    ("#777777", "#91a07f"), ("#787878", "#92a180"),
    ("#797979", "#92a181"), ("#7c7c85", "#98a689"),
    ("#8a8a8a", "#a0ac92"), ("#929292", "#a6b199"),
    ("#a1a1a1", "#b1baa7"), ("#a2a8b1", "#b8c0af"),
    ("#a5a5a5", "#b4bdab"), ("#aaaaaa", "#b8c0af"),
    ("#b1b1b1", "#bec4b6"), ("#b2b2b2", "#bec5b7"),
    ("#b3d096", "#b5caa0"), ("#b6b6b6", "#c1c8ba"),
    ("#bebebe", "#c8cdc1"), ("#c0c0c0", "#c9cec3"),
    ("#cccccc", "#d2d6ce"), ("#d0d0d0", "#d5d9d1"),
    ("#d4d4d4", "#d9dcd5"), ("#e2e2e2", "#e3e6e1"),
    ("#e5e5e5", "#e6e8e4"), ("#ffffff", "#fafafa"),
    ("#1495c0", "#2e90ac"), ("#252525", "#515a46"),
    ("#2a2a2c", "#555f4a"), ("#35383e", "#616d53"),
    ("#37373b", "#606c53"), ("#3d3d3d", "#637055"),
    ("#585858", "#798a65"), ("#5ab55e", "#6bad6c"),
    ("#6e727a", "#8f9e7d"), ("#939393", "#a6b19a"),
    ("#97979c", "#abb5a0"), ("#999999", "#abb5a0"),
    ("#a2a79a", "#b1baa7"), ("#a8a8a8", "#b7bfad"),
    ("#b3b3b3", "#bfc6b7"), ("#c8c8c8", "#cfd4ca"),
    ("#cfcfcf", "#d5d8d0"), ("#ff5a5a", "#e97573"),
    ("#ffd700", "#ddc327"), ("#32b8c6", "#49aeb4"),
    ("#111111", "#414739"), ("#1a1a1c", "#495040"),
    ("#1a528a", "#336694"), ("#1b5e20", "#317335"),
    ("#1d8348", "#359159"), ("#242424", "#505945"),
    ("#2471a3", "#3e81a7"), ("#252527", "#515b47"),
    ("#282828", "#535c48"), ("#2980b9", "#3f83a9"),
    ("#29b6f6", "#4bafd8"), ("#2d333f", "#5e6a51"),
    ("#2e6b9e", "#407092"), ("#2f2f32", "#5a644d"),
    ("#3498db", "#5098c3"), ("#363639", "#5f6b52"),
    ("#383838", "#606b52"), ("#3a3a3c", "#626e54"),
    ("#3b3b3e", "#637055"), ("#3e2020", "#563634"),
    ("#3e3e42", "#667357"), ("#4ca0ad", "#5c9da2"),
    ("#555555", "#768763"), ("#666666", "#84966f"),
    ("#6a9955", "#71965f"), ("#6c87ff", "#8398ea"),
    ("#73d1bf", "#84c7b7"), ("#7ac07a", "#86b985"),
    ("#7dda58", "#88cb6d"), ("#7fb800", "#8bbd1d"),
    ("#8684b8", "#8f90b1"), ("#8b5e3c", "#957150"),
    ("#8e44ad", "#8c58a1"), ("#8e8e8e", "#a3ae95"),
    ("#8fb0ff", "#a0b9ef"), ("#974533", "#9e5c49"),
    ("#9d9d9d", "#aeb8a3"), ("#a0c4ff", "#afc9f2"),
    ("#a375ff", "#ab8ceb"), ("#a4b6ef", "#b0bee5"),
    ("#b0a66e", "#a9a479"), ("#b5ffef", "#c0f5e9"),
    ("#b6efa2", "#bde6ae"), ("#c0392b", "#b14e3f"),
    ("#c1c1c1", "#cacfc4"), ("#c7c7bb", "#cacfc4"),
    ("#d08a4a", "#bf905f"), ("#d1494a", "#c0625f"),
    ("#d9b34c", "#c7ae62"), ("#e53935", "#ce5750"),
    ("#e5a00d", "#cd9c2a"), ("#e5c07b", "#d7bf8b"),
    ("#e67e22", "#cd8640"), ("#eca4a0", "#e2b0ac"),
    ("#ef5350", "#da6e68"), ("#f2c94c", "#dcc065"),
    ("#f44747", "#dd6562"), ("#f4a9f6", "#ebb5eb"),
    ("#f6c273", "#e5c187"), ("#ff7b7d", "#ed9090"),
    ("#ffb300", "#dda927"), ("#ffbdbe", "#f6c7c7"),
    ("#ffd199", "#f1d1a8"), ("#134f87", "#2c6392"),
    ("#1ab8e0", "#38aec7"), ("#233827", "#57624b"),
    ("#242428", "#515b47"), ("#2e7d32", "#458b47"),
    ("#32c85a", "#4aba64"), ("#3e341b", "#564c30"),
    ("#4ba0f0", "#66a3d9"), ("#4b525f", "#768763"),
    ("#4ec9b0", "#63bca6"), ("#5aa0e0", "#70a3cd"),
    ("#5fb96a", "#6fb175"), ("#65666d", "#869872"),
    ("#81c784", "#8dc08f"), ("#c62828", "#b6423e"),
    ("#d64545", "#c3605c"), ("#dcc832", "#c6ba4c"),
    ("#e05656", "#ce6e6b"), ("#e0a030", "#c99e4b"),
    ("#e57373", "#d78784"), ("#e63232", "#ce524e"),
    ("#e65100", "#cc601f"), ("#f0f0f0", "#eeefed"),
    ("#f57f17", "#d78739"), ("#ff5050", "#e86e6b"),
    ("#ffc850", "#e8c26b"), ("#ffd54f", "#e8cb6a"),
    ("#1e1e1e", "#4b5342"), ("#252528", "#525b47"),
    ("#393939", "#606c53"), ("#505864", "#7a8c66"),
    ("#707070", "#8c9c79"), ("#878787", "#9daa8f"),
    ("#e0d28a", "#d5cc97"), ("#fff8be", "#f6f2c7"),
)

def _make_theme(*, level, palette, viewport_clear, **colors):
    return Theme(
        **colors, control_height="22px", spacing_unit="4px", radius="2px",
        border_width="2px", icon_size="16px", viewport_clear=viewport_clear,
        palette=palette, level=level,
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

VINTAGE_THEME = _make_theme(
    level=LEVEL_VINTAGE, palette=_VINTAGE_COLORS, viewport_clear=(0.35, 0.38, 0.30),
    background="#58624c", surface="#525c47", surface_raised="#59644d",
    surface_input="#4b5442", text="#e6e8e4", text_muted="#b4bdab",
    text_disabled="#92a181", border="#6c7a5b", border_strong="#7e9069",
    accent="#c3c87b", accent_hover="#859770", accent_pressed="#91a080",
    selection="#66754f", selection_text="#ffffff", error="#c0625f",
    warning="#cd9c2a", success="#6bad6c",
)

THEMES = {
    LEVEL_STANDARD: STANDARD_THEME,
    LEVEL_BRIGHT: BRIGHT_THEME,
    LEVEL_VINTAGE: VINTAGE_THEME,
}
_PALETTE_MAPS = {level: dict(theme.palette) for level, theme in THEMES.items()}
_ACTIVE_THEME = STANDARD_THEME
_SELECTED_LEVEL = LEVEL_STANDARD
_NON_TOKEN_FIELDS = {"viewport_clear", "palette", "level"}
TOKEN_NAMES = frozenset(f.name for f in fields(Theme) if f.name not in _NON_TOKEN_FIELDS)


def system_level():
    """Bright while the OS reports a light colour scheme, Standard otherwise."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        hints = QGuiApplication.styleHints()
        if hints is not None and hints.colorScheme() == Qt.ColorScheme.Light:
            return LEVEL_BRIGHT
    except Exception:
        pass
    return LEVEL_STANDARD


def set_level(level):
    """Select the active theme (invalid values select Standard).

    LEVEL_SYSTEM resolves to Standard or Bright from the OS colour scheme; the
    selection itself is kept so a later scheme change can re-resolve it.
    """
    global _ACTIVE_THEME, _SELECTED_LEVEL
    try:
        selected = int(level)
    except (TypeError, ValueError):
        selected = LEVEL_STANDARD
    if selected != LEVEL_SYSTEM and selected not in THEMES:
        selected = LEVEL_STANDARD
    _SELECTED_LEVEL = selected
    _ACTIVE_THEME = THEMES[system_level() if selected == LEVEL_SYSTEM else selected]


def selected():
    """The level the user picked, which may be LEVEL_SYSTEM."""
    return _SELECTED_LEVEL


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
