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
finished. Nothing else has to change at the call site, because Qt already
disconnects a signal when its receiver is destroyed — a scan that completes
after teardown just has nowhere to deliver, which is exactly right.
"""
from PySide6.QtCore import QCoreApplication, QThread

_RUNNING = set()
_HOOKED = False

# Long enough for a scan loop to notice the stop flag between VPK entries, short
# enough that quitting never looks hung.
_QUIESCE_MS = 5000


def park(thread: QThread) -> QThread:
    """Hold `thread` until it finishes. Returns it, so it can wrap a call."""
    global _HOOKED
    _RUNNING.add(thread)
    thread.finished.connect(lambda: _RUNNING.discard(thread))
    if not _HOOKED:
        app = QCoreApplication.instance()
        if app is not None:
            # Surviving widget teardown is only half of it: a parked thread still
            # running when Qt tears the app down is destroyed there instead, and
            # aborts on the way out. Quitting is the one point where waiting is
            # both safe and required.
            app.aboutToQuit.connect(quiesce_all)
            _HOOKED = True
    return thread


def quiesce_all() -> None:
    """Stop every parked thread and block until it has actually exited."""
    for thread in list(_RUNNING):
        if not thread.isRunning():
            continue
        stop = getattr(thread, "stop", None)
        if callable(stop):
            stop()
        thread.requestInterruption()
        thread.wait(_QUIESCE_MS)


def running_count() -> int:
    """Parked threads not yet finished — for the self-check below."""
    return len(_RUNNING)


if __name__ == "__main__":   # python -m src.editors.soundevent_editor.thread_parking
    import gc
    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

    app = QCoreApplication([])

    class _Slow(QThread):
        def run(self):
            self.msleep(300)

    class _Owner:
        """Stands in for an explorer widget that is dropped mid-scan."""
        def __init__(self):
            self.thread = park(_Slow())
            self.thread.start()

    owner = _Owner()
    assert running_count() == 1
    thread = owner.thread
    assert thread.parent() is None, "a parented thread dies with its owner"

    # The widget goes away mid-scan, as an addon switch does.
    del owner
    gc.collect()
    assert thread.isRunning(), "thread must survive its owner being dropped"

    loop = QEventLoop()
    thread.finished.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()

    assert not thread.isRunning()
    assert running_count() == 0, "finished threads must be released"
    print("thread parking self-check OK")
