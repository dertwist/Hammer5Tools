"""Regression tests for thread_parking QThread lifecycle safety."""
import gc
import weakref

from PySide6.QtCore import QCoreApplication, QEventLoop, QThread, QTimer

from gui.editors.soundevent_editor import thread_parking


def test_parked_thread_survives_owner_drop_and_releases_on_main_thread():
    app = QCoreApplication.instance() or QCoreApplication([])

    class _SlowThread(QThread):
        def run(self):
            self.msleep(50)

    class _Owner:
        def __init__(self):
            self.thread = thread_parking.park(_SlowThread())
            self.thread.start()

    owner = _Owner()
    ref = weakref.ref(owner.thread)
    assert thread_parking.running_count() >= 1

    # Drop the only external reference while the thread is still running.
    del owner
    gc.collect()
    assert ref() is not None

    loop = QEventLoop()
    ref().finished.connect(loop.quit)
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    app.processEvents()

    assert thread_parking.running_count() == 0
