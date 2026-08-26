"""Apply the compiled application stylesheet.

See the styling-refactor plan (gui/styles/theme.py docstring / project plan
history) for why this split exists: qss_compiler produces text, this module
is the only thing that hands that text to Qt.
"""

from PySide6.QtWidgets import QApplication

from gui.styles.qss_compiler import compile_stylesheet
from gui.styles.theme import Theme


def apply(app: QApplication, theme: Theme) -> None:
    """Compile and set the application-wide stylesheet for ``theme``."""
    app.setStyleSheet(compile_stylesheet(theme))


def reapply(theme: Theme) -> None:
    """Recompile the one global stylesheet for a live theme switch."""
    app = QApplication.instance()
    if app is not None:
        apply(app, theme)
