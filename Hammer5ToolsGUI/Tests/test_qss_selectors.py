"""Guard against QSS selectors that match nothing.

Each `#objectName` and `[prop="value"]` in gui/styles/qss/**/*.qss must
correspond to a `setObjectName(...)`/`setProperty(...)` call or a Qt
Designer `name="..."` attribute somewhere under gui/. Otherwise the rule
is dead: the widget it was meant to style no longer carries that name,
and the styling silently does nothing.
"""

import re
from pathlib import Path

_GUI_ROOT = Path(__file__).resolve().parents[1] / "gui"
_QSS_ROOT = _GUI_ROOT / "styles" / "qss"

# h5ColorRole values are computed at runtime from a hex color string
# (color.lstrip("#").lower()), never set as a Python string literal.
_RUNTIME_COMPUTED_PROPERTIES = {"h5ColorRole"}

_ID_RE = re.compile(r"#([A-Za-z_]\w*)")
_PROP_RE = re.compile(r'\[\s*([A-Za-z_]\w*)\s*[~|]?=\s*"([^"]*)"\s*\]')


def _source_blob() -> str:
    parts = []
    for path in list(_GUI_ROOT.rglob("*.py")) + list(_GUI_ROOT.rglob("*.ui")):
        if "__pycache__" in path.parts or _QSS_ROOT in path.parents:
            continue
        parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def _dead_selectors():
    blob = _source_blob()
    dead = []
    for qss_path in sorted(_QSS_ROOT.glob("**/*.qss")):
        text = re.sub(r"/\*.*?\*/", "", qss_path.read_text(encoding="utf-8"), flags=re.S)
        pos = 0
        for match in re.finditer(r"\{[^{}]*\}", text, flags=re.S):
            selector_block = text[pos:match.start()]
            line_no = text[:match.start()].count("\n") + 1
            pos = match.end()
            for selector in selector_block.split(","):
                selector = selector.strip()
                if not selector:
                    continue
                for id_match in _ID_RE.finditer(selector):
                    name = id_match.group(1)
                    if not re.search(r'["\']%s["\']' % re.escape(name), blob):
                        dead.append((qss_path.name, line_no, f"#{name}"))
                for prop_match in _PROP_RE.finditer(selector):
                    prop_name, value = prop_match.group(1), prop_match.group(2)
                    if prop_name in _RUNTIME_COMPUTED_PROPERTIES:
                        continue
                    if not re.search(r'["\']%s["\']' % re.escape(value), blob):
                        dead.append((qss_path.name, line_no, f'[{prop_name}="{value}"]'))
    return dead


def test_no_qss_selector_matches_nothing_in_code():
    dead = _dead_selectors()
    assert not dead, "QSS selectors with no matching setObjectName/setProperty in gui/:\n" + "\n".join(
        f"  {name}:{line}  {token}" for name, line, token in dead
    )
