"""The one place in the app allowed to call QApplication.setStyleSheet().

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
    """Re-run apply() against the current QApplication instance, e.g. after
    the user changes the brightness level at runtime."""
    app = QApplication.instance()
    if app is not None:
        apply(app, theme)
