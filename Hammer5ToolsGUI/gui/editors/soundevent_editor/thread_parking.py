"""Keep background QThreads alive past the widget that started them.

Switching addons tears down the SoundEvent editor and deletes its explorers.
The VPK scanners they start take seconds on CS2's ~130k-entry pak01_dir.vpk, so
a switch mid-scan routinely lands while one is still running — and a QThread
destroyed while running is a `qFatal` in Qt, which kills the whole process with
no Python traceback. Both ways a widget can take its thread down apply here:

  * Qt parenting — the thread was a child of the explorer, so deleting the
    explorer deleted the thread.
  * Python GC — the widget held the only reference, so dropping it could free
    the thread even without a parent.

park() closes both: the thread is unparented and held here until it emits
finished on the main Qt thread.
"""
from __future__ import annotations

import threading
import weakref
from PySide6.QtCore import QCoreApplication, QObject, QThread, Qt, Slot

_LOCK = threading.Lock()
_RUNNING: set[QThread] = set()
_HOOKED_APPS: weakref.WeakSet[QCoreApplication] = weakref.WeakSet()
_REAPER: "_ThreadReaper | None" = None

# Long enough for a scan loop to notice the stop flag between VPK entries, short
# enough that quitting never looks hung.
_QUIESCE_MS = 5000


class _ThreadReaper(QObject):
    """Releases finished parked QThreads on the main Qt thread."""

    @Slot()
    def reap_finished(self) -> None:
        with _LOCK:
            candidates = [t for t in _RUNNING if t.isFinished()]
        for t in candidates:
            # Ensure QThreadPrivate::finish() has fully returned on the OS thread
            # before dropping the last Python reference.
            if t.wait(50):
                with _LOCK:
                    _RUNNING.discard(t)


def _ensure_reaper(app: QCoreApplication | None) -> _ThreadReaper | None:
    global _REAPER
    if app is None:
        return None
    if _REAPER is None or _REAPER.parent() is not app:
        _REAPER = _ThreadReaper(app)
    if app not in _HOOKED_APPS:
        app.aboutToQuit.connect(quiesce_all)
        _HOOKED_APPS.add(app)
    return _REAPER


def park(thread: QThread) -> QThread:
    """Hold `thread` until it finishes. Returns it, so it can wrap a call."""
    if thread.parent() is not None:
        thread.setParent(None)

    with _LOCK:
        _RUNNING.add(thread)

    app = QCoreApplication.instance()
    reaper = _ensure_reaper(app)
    if reaper is not None:
        thread.finished.connect(
            reaper.reap_finished,
            Qt.ConnectionType.QueuedConnection,
        )
    else:
        def _fallback_reap() -> None:
            with _LOCK:
                _RUNNING.discard(thread)

        thread.finished.connect(_fallback_reap)

    return thread


def quiesce_all() -> None:
    """Stop every parked thread and block until it has actually exited."""
    with _LOCK:
        threads = list(_RUNNING)
    for thread in threads:
        if not thread.isRunning():
            with _LOCK:
                _RUNNING.discard(thread)
            continue
        stop = getattr(thread, "stop", None)
        if callable(stop):
            stop()
        thread.requestInterruption()
        thread.quit()
        if thread.wait(_QUIESCE_MS):
            with _LOCK:
                _RUNNING.discard(thread)


def running_count() -> int:
    """Parked threads not yet finished — for tests and diagnostics."""
    with _LOCK:
        return len(_RUNNING)
