"""Git sync UI: the toolbar button, the changes picker, and the conflict resolver.

Everything the user sees here is branded with one icon so a git dialog is
recognisable as one before it is read.
"""
import importlib

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox

# Register the qrc before a Git dialog can ask Qt for its shared icon. Main-window
# imports normally do this first, but dialog tests and standalone previews do not.
importlib.import_module("gui.resources_rc")

#: prefix="/icons" + alias="icons/git.png" in gui/resources.qrc.
GIT_ICON_PATH = ":/icons/icons/git.png"


def git_icon() -> QIcon:
    """The shared window icon for every git dialog."""
    return QIcon(GIT_ICON_PATH)


def git_message_box(parent, title, text, icon=QMessageBox.Warning,
                    buttons=QMessageBox.Ok, default=QMessageBox.NoButton):
    """Show a message box carrying the same Git window icon as the dialogs."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setWindowIcon(git_icon())
    box.setIcon(icon)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default != QMessageBox.NoButton:
        box.setDefaultButton(default)
    return box.exec()
