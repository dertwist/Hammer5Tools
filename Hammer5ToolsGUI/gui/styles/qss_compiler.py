"""Compiles gui/styles/qss/*.qss fragments into one QSS string.

Pure function, no Qt application/widget access — see the styling-refactor
plan for why that split matters (StyleManager owns setStyleSheet(), this
module only produces text). QSS source files reference semantic colors as
``@token_name``; compile_stylesheet() substitutes those against a
``theme.Theme`` instance and fails loudly on anything left unresolved.
"""

import re
from functools import lru_cache
from pathlib import Path

from gui.styles.theme import Theme, TOKEN_NAMES

_QSS_DIR = Path(__file__).parent / "qss"
_FEATURES_DIR = _QSS_DIR / "features"

_TOKEN_RE = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")


def _base_fragment_paths() -> list[Path]:
    """base.qss first (generic QWidget/QDialog rules other selectors rely on
    losing to via specificity), then the rest alphabetically for determinism."""
    paths = sorted(_QSS_DIR.glob("*.qss"))
    base = _QSS_DIR / "base.qss"
    if base in paths:
        paths.remove(base)
        paths.insert(0, base)
    return paths


def _feature_fragment_paths() -> list[Path]:
    if not _FEATURES_DIR.is_dir():
        return []
    return sorted(_FEATURES_DIR.glob("*.qss"))


def _substitute(qss_text: str, theme: Theme, source: Path) -> str:
    def resolve(match: re.Match) -> str:
        name = match.group(1)
        if name not in TOKEN_NAMES:
            raise ValueError(f"Unknown QSS token '@{name}' in {source}")
        return str(getattr(theme, name))

    return _TOKEN_RE.sub(resolve, qss_text)


@lru_cache(maxsize=8)
def compile_stylesheet(theme: Theme) -> str:
    """Concatenate every qss/*.qss and qss/features/*.qss fragment, with
    ``@token`` references resolved against ``theme``. Cached per Theme
    instance (there are only 3: dark/standard/bright)."""
    chunks = []
    for path in _base_fragment_paths() + _feature_fragment_paths():
        text = path.read_text(encoding="utf-8")
        chunks.append(_substitute(text, theme, path))
    return "\n".join(chunks)
