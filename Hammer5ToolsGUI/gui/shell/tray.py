"""System tray icon for the main window."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMenu, QSystemTrayIcon


class TrayIcon:
    """The tray icon, its menu, and restoring the window from it."""

    def __init__(self, window):
        self._window = window
        self.icon = QSystemTrayIcon(QIcon.fromTheme(":/icons/appicon.ico"), window)
        self.icon.setToolTip("Hammer5Tools")

        self.menu = QMenu()
        self.menu.addAction(QAction("Show", window, triggered=self.restore_window))
        self.menu.addAction(QAction("Exit", window, triggered=window.exit_application))
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._on_activated)
        self.icon.show()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.restore_window()

    def restore_window(self):
        """Bring the window to the front, un-hiding it from the tray if needed.

        Only a window that is actually away (tray-hidden or minimized) gets the
        un-hide treatment.  Every IPC handler calls this before acting on a
        request from a second launch -- "open this .vsmart in the instance that
        is already running" -- and on an on-screen window the un-hide path
        un-maximizes it, blocks the GUI thread inside the native ShowWindow
        sequence, and re-opens every dock the user had closed.  The app looked
        like it relaunched itself just to open a file.
        """
        window = self._window
        if window.isVisible() and not window.isMinimized():
            window.raise_()
            window.activateWindow()
            return

        # show(), not showNormal(): a window minimized from maximized must come
        # back maximized, which showNormal() would silently drop.
        window.setWindowState((window.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        window.show()
        window.raise_()
        window.activateWindow()

        _native_restore(window)
        set_docks_visible(window, True)


def _native_restore(window) -> None:
    """Win32 show/foreground sequence Qt's own show() doesn't reliably win."""
    from gui.app_core import restore_window as restore_native_window
    restore_native_window(window.winId().__int__())


def set_docks_visible(window, visible: bool) -> None:
    """Show or hide every dock in the window and in the editors it hosts.

    Qt does not restore a hidden dock when its top-level window reappears, so
    hiding to the tray and coming back has to walk them explicitly.
    """
    for dock in window.findChildren(QDockWidget):
        dock.setVisible(visible)
    for child in window.findChildren(QMainWindow):
        for dock in child.findChildren(QDockWidget):
            dock.setVisible(visible)
