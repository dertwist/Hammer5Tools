"""System tray icon for the main window."""

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
        """Bring the window back from the tray, docks included."""
        window = self._window
        window.showNormal()
        window.raise_()
        window.activateWindow()

        from gui.app_core import restore_window as restore_native_window
        restore_native_window(window.winId().__int__())
        set_docks_visible(window, True)


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
