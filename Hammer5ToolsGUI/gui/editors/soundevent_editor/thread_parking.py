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
from PySide6.QtCore import QCoreApplication, QObject, QThread, Qt

_LOCK = threading.Lock()
_RUNNING: set[QThread] = set()
_HOOKED_APPS: weakref.WeakSet[QCoreApplication] = weakref.WeakSet()
_REAPER: "_ThreadReaper | None" = None

# Long enough for a scan loop to notice the stop flag between VPK entries, short
# enough that quitting never looks hung.
_QUIESCE_MS = 5000


class _ThreadReaper(QObject):
    """Releases finished parked QThreads on the main Qt thread."""

    def release(self, thread: QThread) -> None:
        with _LOCK:
            _RUNNING.discard(thread)


def _ensure_reaper(app: QCoreApplication | None) -> _ThreadReaper | None:
    global _REAPER
    if app is None:
        return None
    if _REAPER is None or _REAPER.thread() is not app.thread():
        _REAPER = _ThreadReaper()
        _REAPER.moveToThread(app.thread())
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

    def _on_finished() -> None:
        with _LOCK:
            _RUNNING.discard(thread)

    if reaper is not None:
        # QueuedConnection with a main-thread QObject receiver guarantees
        # _on_finished runs on the main thread after QThreadPrivate::finish.
        thread.finished.connect(
            _on_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        # Keep reaper as receiver context via QObject.destroyed? No: in PySide6,
        # connecting to a plain function ignores QueuedConnection unless a QObject
        # receiver is used or the slot is bound to a QObject. Bind via reaper.
        thread.finished.disconnect(_on_finished)
        thread.finished.connect(
            lambda t=thread: reaper.release(t),
            Qt.ConnectionType.QueuedConnection,
        )
    else:
        thread.finished.connect(_on_finished)

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
