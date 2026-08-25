"""Shared base for UnrealPorter's QThread workers.

Keeps the cooperative cancel flag in one place so the dialog's close path
(``UnrealPorterWidget.closeEvent``) can stop every job the same way, matching
the pattern already used by ``src/forms/source_porter/porter_client.PorterThread``.

Lives in its own module so both ``main.py`` and its siblings
(``converter.py``, ``scene_worker.py``) can import it without a cycle — those
modules can't import from ``main.py``.
"""

from PySide6.QtCore import QThread


class CancellableWorker(QThread):
    """QThread with a one-way stop flag.

    ``cancel()`` flips the flag; ``run()`` implementations poll ``is_cancelled``
    between units of work and bail out. Cooperative only — a worker blocked in
    a single un-pollable call (a bridge ``subprocess.run`` past its own timeout)
    finishes that call first, but the flag stops the *next* unit of work.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        """Request this worker stop after its current unit of work."""
        self._is_cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled
