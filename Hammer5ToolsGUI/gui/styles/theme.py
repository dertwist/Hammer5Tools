"""Runtime theme selection for the application palette.

The interface brightness setting (Preferences -> General, stored as
APP/brightness_level in settings.ini) has three levels:

    1 - Dark    : the original pre-brightening palette
    2 - Standard: the current source palette (default; identity map,
                  stylesheets pass through untouched)
    3 - Bright  : a lightness-inverted light palette

All QSS colors in the codebase are written as level-2 literals. Level 1 is
derived from the rewrite table below and restores the old palette exactly.
Level 3 inverts each canonical color's HSL lightness, turning dark surfaces
into layered off-whites while preserving the hues of accents and status colors.

``install()`` patches QWidget/QApplication ``setStyleSheet`` so every
stylesheet (global QSS, compiled .ui styles, inline calls) is transformed
through the active map before Qt sees it; ``reapply()`` restyles every
live widget when the user switches levels at runtime. The few colors that
bypass stylesheets entirely (QPainter pens, the OpenGL clear color) use
``color()`` / ``qcolor()`` / ``gl_clear_color()`` with level-2 literals.
"""

import colorsys
import re
import weakref
from dataclasses import dataclass, fields

from PySide6.QtGui import QColor

LEVEL_DARK = 1
LEVEL_STANDARD = 2
LEVEL_BRIGHT = 3

# Rewrite table of the palette brightening: original (level 1) -> current
# (level 2, canonical). Kept verbatim from dev/scripts/brighten_colors.py.
_OLD_TO_LEVEL2 = {
    "#151515": "#272727",
    "#161616": "#292929",
    "#1a1a1a": "#2c2c2c",
    "#1c1c1c": "#2e2e2e",
    "#1d1d1f": "#2f2f31",
    "#121212": "#252525",
    "#18181a": "#2a2a2c",
    "#1e1e1e": "#303030",
    "#1f1f1f": "#313131",
    "#212121": "#333333",
    "#222222": "#343434",
    "#232323": "#353535",
    "#242424": "#363636",
    "#242426": "#363637",
    "#252525": "#363636",
    "#252526": "#363637",
    "#262626": "#373737",
    "#26262a": "#37373b",
    "#26262b": "#37373c",
    "#272729": "#38383a",
    "#27272a": "#38383b",
    "#292929": "#3a3a3a",
    "#2a2929": "#3b3a3a",
    "#2a2a2a": "#3b3b3b",
    "#2a2a2d": "#3b3b3e",
    "#2a2e38": "#3b3f48",
    "#2c2c2c": "#3d3d3d",
    "#2d2d2d": "#3e3e3e",
    "#2d2d30": "#3e3e41",
    "#2d333b": "#3e434b",
    "#2e2e2e": "#3f3f3f",
    "#2e2f30": "#3f4041",
    "#2e2e32": "#3f3f42",
    "#2f2f2f": "#404040",
    "#323232": "#424242",
    "#333333": "#434343",
    "#333336": "#434346",
    "#33363d": "#43464d",
    "#333a48": "#434a57",
    "#353535": "#454545",
    "#363639": "#464649",
    "#3a3a3a": "#4a4a4a",
    "#3c3c3c": "#4c4c4c",
    "#3d3d3d": "#4d4d4d",
    "#3d3d42": "#4d4d51",
    "#3e3e3e": "#4d4d4d",
    "#3e4451": "#4d535f",
    "#3e4b5e": "#4d596b",
    "#404040": "#4f4f4f",
    "#414956": "#515965",
    "#434343": "#525252",
    "#444444": "#535353",
    "#4a4a4a": "#585858",
    "#4a5a6a": "#586776",
    "#4f5259": "#5d6066",
    "#505050": "#5e5e5e",
    "#555555": "#636363",
    "#606060": "#6d6d6d",
    "#606c77": "#6d7882",
    "#61666e": "#6e727a",
    "#666666": "#727272",
    "#6b6b6b": "#777777",
    "#6c6c6c": "#787878",
    "#6d6d6d": "#797979",
    "#71717a": "#7c7c85",
    "#7a7a7a": "#858585",
    "#7f7f7f": "#898989",
    "#808080": "#8a8a8a",
    "#888888": "#929292",
    "#8a8a8a": "#939393",
    "#8e8e93": "#97979c",
    "#909090": "#999999",
    "#999999": "#a1a1a1",
    "#9a9f91": "#a2a79a",
    "#9aa0aa": "#a2a8b1",
    "#9d9d9d": "#a5a5a5",
    "#a0a0a0": "#a8a8a8",
    "#a3a3a3": "#aaaaaa",
    "#a7a9a9": "#aeb0b0",
    "#aaaaaa": "#b1b1b1",
    "#ababab": "#b2b2b2",
    "#acacac": "#b3b3b3",
    "#b0b0b0": "#b6b6b6",
    "#b8b8b8": "#bebebe",
    "#bababa": "#c0c0c0",
    "#bbbbbb": "#c0c0c0",
    "#c3c3c3": "#c8c8c8",
    "#c8c8c8": "#cccccc",
    "#cbcbcb": "#cfcfcf",
    "#cccccc": "#d0d0d0",
    "#d0d0d0": "#d4d4d4",
    "#e0e0e0": "#e2e2e2",
    "#e3e3e3": "#e5e5e5",
    "#1e222a": "#30343b",
    "#282c34": "#393d44",
    "#2c3e50": "#3d4d5e",
    "#4e5563": "#5c636f",
    "#abb2bf": "#b2b8c4",
    "#accc8d": "#b3d096",
    "#4caf50": "#5ab55e",
    "#23272d": "#35383e",
    "#008cba": "#1495c0",
    "#3a78c4": "#4a83c9",
    "#3d88bd": "#4d92c2",
    "#515966": "#5f6672",
}

# Canonical rgb()/rgba() triplet values that appear in QSS strings but have
# no hex counterpart in the table above (they were rewritten as triplets):
# current (level 2) -> original (level 1).
_PURE_TRIPLETS_TO_OLD = {
    (135, 135, 135): (125, 125, 125),
    (112, 112, 112): (100, 100, 100),
    (80, 88, 100): (65, 73, 86),
    (193, 193, 193): (188, 188, 188),
    (57, 57, 57): (40, 40, 40),
}


def _invert_rgb_lightness(rgb):
    normalized = tuple(channel / 255 for channel in rgb)
    hue, lightness, saturation = colorsys.rgb_to_hls(*normalized)
    inverted = colorsys.hls_to_rgb(hue, 1 - lightness, saturation)
    return tuple(round(channel * 255) for channel in inverted)


def _invert_hex_lightness(hex_color):
    rgb = tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % _invert_rgb_lightness(rgb)


def _invert(spec):
    """level2 -> level1. On value collisions (sources 1-2/255 apart) the
    darkest original wins, deterministically (reverse sort + overwrite)."""
    out = {}
    for old, new in sorted(spec.items(), reverse=True):
        out[new] = old
    return out


# canonical (level 2) -> level-specific hex
PALETTE_2_TO_1 = _invert(_OLD_TO_LEVEL2)
PALETTE_2_TO_3 = {new: _invert_hex_lightness(new) for new in _OLD_TO_LEVEL2.values()}
PALETTE_2_TO_3["#ffffff"] = "#000000"
PALETTE_2_TO_3["#fff"] = "#000000"

_LEVEL_MAPS = {LEVEL_DARK: PALETTE_2_TO_1, LEVEL_STANDARD: {}, LEVEL_BRIGHT: PALETTE_2_TO_3}

# canonical hex (lowercase, no '#') -> (r, g, b) for triplet matching
_HEX_TO_RGB = {}
for _old, _new in _OLD_TO_LEVEL2.items():
    _HEX_TO_RGB[_new[1:]] = tuple(int(_new[i:i + 2], 16) for i in (1, 3, 5))

_LEVEL = LEVEL_STANDARD
_TRIPLET_MAP = {}  # canonical (r, g, b) -> active (r, g, b)
_CACHE = {}

_HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{8}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")
_TRIPLET_RE = re.compile(r"(rgba?\s*\(\s*)(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})")
_NAMED_WHITE_RE = re.compile(r"(?P<prefix>:\s*)white(?=\s*[;}])", re.IGNORECASE)


def set_brightness_level(level):
    """Select the active brightness map (1/2/3; anything else -> 2)."""
    global _LEVEL, _TRIPLET_MAP, _CACHE
    try:
        _LEVEL = int(level)
    except (TypeError, ValueError):
        _LEVEL = LEVEL_STANDARD
    if _LEVEL == LEVEL_STANDARD:
        _TRIPLET_MAP = {}
        _CACHE = {}
        return
    # canonical (r, g, b) -> active (r, g, b), covering both triplet forms
    # that mirror a hex entry and triplets that only ever existed as such
    triplets = {}
    for hex2 in _HEX_TO_RGB:
        target = _LEVEL_MAPS[_LEVEL].get("#" + hex2)
        if target:
            rgb = _HEX_TO_RGB[hex2]
            triplets[rgb] = tuple(int(target[i:i + 2], 16) for i in (1, 3, 5))
    for canon, old in _PURE_TRIPLETS_TO_OLD.items():
        if _LEVEL == LEVEL_DARK:
            triplets[canon] = old
        else:
            triplets[canon] = _invert_rgb_lightness(canon)
    _TRIPLET_MAP = triplets
    _CACHE = {}


def brightness_level():
    return _LEVEL


def transform_qss(qss):
    """Map a canonical (level 2) stylesheet string to the active level."""
    if not qss or _LEVEL == LEVEL_STANDARD:
        return qss
    cached = _CACHE.get(qss)
    if cached is not None:
        return cached

    palette = _LEVEL_MAPS.get(_LEVEL, {})

    def hex_sub(m):
        h = m.group(1)
        if len(h) == 8:  # #AARRGGBB: transform the RGB part only
            new = palette.get("#" + h[2:].lower())
            return "#" + h[:2] + new[1:] if new else m.group(0)
        new = palette.get("#" + h.lower())
        return new if new else m.group(0)

    def triplet_sub(m):
        key = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        new = _TRIPLET_MAP.get(key)
        return "%s%d, %d, %d" % (m.group(1), *new) if new else m.group(0)

    out = _HEX_RE.sub(hex_sub, qss)
    if _LEVEL == LEVEL_BRIGHT:
        out = _NAMED_WHITE_RE.sub(r"\g<prefix>#000000", out)
    if _TRIPLET_MAP:
        out = _TRIPLET_RE.sub(triplet_sub, out)
    _CACHE[qss] = out
    return out


def color(hex_level2):
    """Canonical (level 2) hex literal -> active-level hex string."""
    palette = _LEVEL_MAPS.get(_LEVEL, {})
    return palette.get(hex_level2.lower(), hex_level2)


def qcolor(hex_level2):
    return QColor(color(hex_level2))


_VIEWPORT_CLEAR = {  # matches glClearColor() for each level
    LEVEL_DARK: (0.11, 0.11, 0.11),
    LEVEL_STANDARD: (0.18, 0.18, 0.18),
    LEVEL_BRIGHT: (0.82, 0.82, 0.82),
}


def gl_clear_color():
    """OpenGL viewport clear RGB for the active level (alpha is 1.0)."""
    return _VIEWPORT_CLEAR.get(_LEVEL, _VIEWPORT_CLEAR[LEVEL_STANDARD])


# --- setStyleSheet interception -------------------------------------------

_ORIG_WIDGET_SSS = None
_ORIG_APP_SSS = None
_widget_qss = weakref.WeakKeyDictionary()  # widget -> raw canonical stylesheet
_app_qss = []  # single-slot stash for the app-level stylesheet


def _install_widget_patch():
    global _ORIG_WIDGET_SSS
    if _ORIG_WIDGET_SSS is not None:
        return
    from PySide6.QtWidgets import QWidget

    _ORIG_WIDGET_SSS = QWidget.setStyleSheet

    def patched(self, qss):
        try:
            _widget_qss[self] = qss
            qss = transform_qss(qss)
        except Exception:
            pass  # never let theming break a widget
        return _ORIG_WIDGET_SSS(self, qss)

    QWidget.setStyleSheet = patched


def _install_app_patch():
    global _ORIG_APP_SSS
    if _ORIG_APP_SSS is not None:
        return
    from PySide6.QtWidgets import QApplication

    _ORIG_APP_SSS = QApplication.setStyleSheet

    def patched(self, qss):
        try:
            _app_qss[:] = [qss]
            qss = transform_qss(qss)
        except Exception:
            pass
        return _ORIG_APP_SSS(self, qss)

    QApplication.setStyleSheet = patched


def install():
    """Route every future setStyleSheet call through the active palette."""
    _install_widget_patch()
    _install_app_patch()


def reapply():
    """Re-apply the global stylesheet and all stashed widget stylesheets
    through the currently active level (live theme switch)."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    if _app_qss:
        _ORIG_APP_SSS(app, transform_qss(_app_qss[0]))
    for widget, raw in list(_widget_qss.items()):
        try:
            _ORIG_WIDGET_SSS(widget, transform_qss(raw))
        except RuntimeError:
            pass  # C++ object already deleted


# --- Theme: semantic tokens for the new qss_compiler/manager pipeline -----
#
# This coexists with the setStyleSheet-patching machinery above during the
# migration (see the styling-refactor plan). Nothing above this point is
# used by the new pipeline; nothing below is used by the old one. Once every
# caller goes through qss_compiler/manager, the code above is deleted.

_STANDARD_HEX = {
    "background_neutral": "#272727",
    "background_primary": "#2e2e2e",
    "background_secondary": "#2f2f31",
    "text_primary": "#e5e5e5",
    "text_neutral": "#a5a5a5",
    "stroke": "#464649",
    "selected_fill": "#515965",
    "pressed": "#6d7882",
    "accent": "#4a83c9",
}


@dataclass(frozen=True)
class Theme:
    """Semantic tokens consumed by qss_compiler.compile_stylesheet().

    Field names double as the ``@token`` names QSS source files reference
    (see gui/styles/qss/). Values are plain hex strings so they can be
    substituted directly into QSS text.
    """

    background_neutral: str
    background_primary: str
    background_secondary: str
    text_primary: str
    text_neutral: str
    stroke: str
    selected_fill: str
    pressed: str
    accent: str
    viewport_clear: tuple  # (r, g, b) floats 0-1, for gl_clear_color()


def _theme_for_level(level: int) -> "Theme":
    """Derive a Theme's hex values from the existing rewrite tables, so the
    three instances stay pixel-identical to what transform_qss() used to
    produce for these same tokens."""
    palette = _LEVEL_MAPS.get(level, {})
    values = {name: palette.get(hex2, hex2) for name, hex2 in _STANDARD_HEX.items()}
    return Theme(**values, viewport_clear=_VIEWPORT_CLEAR[level])


THEMES = {
    LEVEL_DARK: _theme_for_level(LEVEL_DARK),
    LEVEL_STANDARD: _theme_for_level(LEVEL_STANDARD),
    LEVEL_BRIGHT: _theme_for_level(LEVEL_BRIGHT),
}

TOKEN_NAMES = frozenset(f.name for f in fields(Theme))


def get_theme(level: int | None = None) -> Theme:
    """The active Theme, or the Theme for a specific brightness level."""
    return THEMES.get(level if level is not None else _LEVEL, THEMES[LEVEL_STANDARD])
