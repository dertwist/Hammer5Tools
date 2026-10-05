"""Restoring the window must not disturb one that is already on screen.

The IPC handlers call TrayIcon.restore_window() for every request forwarded
from a second launch (opening a .vsmart from Explorer, the quick actions).  On
an already-visible window the tray un-hide path un-maximized it, ran a blocking
native ShowWindow sequence, and re-showed every dock the user had closed --
which read as the whole application relaunching itself to open one file.

Plain fakes, no QApplication: restore_window only duck-types the window.
"""
from PySide6.QtCore import Qt

from gui.shell import tray
from gui.shell.tray import TrayIcon


class _Window:
    def __init__(self, visible=True, minimized=False, state=Qt.WindowMaximized):
        self._visible = visible
        self._minimized = minimized
        self._state = state
        self.calls = []

    def isVisible(self):
        return self._visible

    def isMinimized(self):
        return self._minimized

    def windowState(self):
        return self._state

    def setWindowState(self, state):
        self._state = state
        self._minimized = bool(state & Qt.WindowMinimized)
        self.calls.append("setWindowState")

    def show(self):
        self._visible = True
        self.calls.append("show")

    def showNormal(self):
        self._visible = True
        self._state = Qt.WindowNoState
        self.calls.append("showNormal")

    def raise_(self):
        self.calls.append("raise_")

    def activateWindow(self):
        self.calls.append("activateWindow")


def _tray_for(window, monkeypatch):
    """A TrayIcon without running __init__ (which needs a QApplication)."""
    icon = TrayIcon.__new__(TrayIcon)
    icon._window = window
    monkeypatch.setattr(tray, "_native_restore", lambda w: window.calls.append("native"))
    monkeypatch.setattr(tray, "set_docks_visible",
                        lambda w, visible: window.calls.append(f"docks={visible}"))
    return icon


def test_visible_window_is_only_raised(monkeypatch):
    window = _Window(visible=True, minimized=False)
    _tray_for(window, monkeypatch).restore_window()

    assert window.calls == ["raise_", "activateWindow"]
    # The three things that made it look like a relaunch.
    assert "showNormal" not in window.calls
    assert "native" not in window.calls
    assert "docks=True" not in window.calls
    assert window.windowState() == Qt.WindowMaximized  # still maximized


def test_tray_hidden_window_is_fully_restored(monkeypatch):
    window = _Window(visible=False, minimized=False)
    _tray_for(window, monkeypatch).restore_window()

    assert window.isVisible()
    assert "native" in window.calls and "docks=True" in window.calls


def test_minimized_window_comes_back_maximized(monkeypatch):
    window = _Window(visible=True, minimized=True,
                     state=Qt.WindowMaximized | Qt.WindowMinimized)
    _tray_for(window, monkeypatch).restore_window()

    assert "native" in window.calls
    assert window.windowState() & Qt.WindowMaximized
    assert not window.windowState() & Qt.WindowMinimized
