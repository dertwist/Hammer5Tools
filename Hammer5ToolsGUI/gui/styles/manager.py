"""Apply the compiled application stylesheet.

See the styling-refactor plan (gui/styles/theme.py docstring / project plan
history) for why this split exists: qss_compiler produces text, this module
is the only thing that hands that text to Qt.
"""

import os
import time

from PySide6.QtWidgets import QApplication

from gui.styles.qss_compiler import compile_stylesheet
from gui.styles.theme import Theme

_TIMING = os.environ.get("H5T_STYLE_TIMING") == "1"


def apply(app: QApplication, theme: Theme) -> None:
    """Compile and set the application-wide stylesheet for ``theme``."""
    app.setStyleSheet(compile_stylesheet(theme))


def reapply(theme: Theme) -> None:
    """Recompile the one global stylesheet for a live theme switch.

    Expensive, and not because of anything on this side: compiling the sheet
    is ~0.02 ms, while Qt's repolish of every live widget measured ~5 s for a
    ~5000-widget tree, growing faster than linearly with widget count. Content
    of the sheet barely matters -- an empty stylesheet still costs ~25% of the
    full one. Callers should therefore fire this only on a real user-initiated
    change, never speculatively. Set H5T_STYLE_TIMING=1 to print the split.
    """
    app = QApplication.instance()
    if app is None:
        return

    start = time.perf_counter()
    qss = compile_stylesheet(theme)
    compiled = time.perf_counter()
    app.setStyleSheet(qss)

    if _TIMING:
        done = time.perf_counter()
        print(
            f"[style] compile {(compiled - start) * 1000:.1f} ms, "
            f"repolish {(done - compiled) * 1000:.1f} ms, "
            f"{len(app.allWidgets())} widgets",
            flush=True,
        )
