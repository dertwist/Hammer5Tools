"""Window geometry persistence.

Saves continuously (debounced) rather than only on close, so the geometry
survives a crash or an abrupt termination such as stopping the debugger.
"""

import logging

from PySide6.QtCore import QTimer

log = logging.getLogger(__name__)

_KEY = "MainWindow/geometry"
_QUIET_MS = 500


class WindowStateSaver:
    """Restores the saved geometry and writes it back as the window changes."""

    def __init__(self, window, settings):
        self._window = window
        self._settings = settings
        self._timer = QTimer(window)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_QUIET_MS)
        self._timer.timeout.connect(self.save)

    def restore(self) -> None:
        """QWidget.restoreGeometry round-trips maximized/fullscreen too, so a
        window that was maximized reopens maximized."""
        try:
            geometry = self._settings.value(_KEY)
            if geometry:
                self._window.restoreGeometry(geometry)
        except Exception as error:
            log.error(f"Failed to restore window geometry: {error}")

    def save(self) -> None:
        try:
            self._settings.setValue(_KEY, self._window.saveGeometry())
            # Flush now: QSettings otherwise buffers writes and loses them if
            # the process is killed before its normal shutdown.
            self._settings.sync()
        except Exception as error:
            log.error(f"Failed to save window geometry: {error}")

    def schedule_save(self) -> None:
        """Called from resize/move; a single save fires once the window settles."""
        self._timer.start()
