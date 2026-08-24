"""Application lifecycle requests understood by the native launcher."""

import ctypes
import os
import sys


RESTART_EXIT_CODE = 75
_LAUNCHER_HANDOFF_ENV = "H5T_LAUNCHER_HANDOFF"


def launcher_handoff_is_valid() -> bool:
    """Return whether the process inherited the launcher's private handoff."""
    if os.name != "nt":
        return False
    try:
        handle = int(os.environ[_LAUNCHER_HANDOFF_ENV])
    except (KeyError, TypeError, ValueError):
        return False
    if handle <= 0:
        return False

    flags = ctypes.c_ulong()
    return bool(
        ctypes.windll.kernel32.GetHandleInformation(
            ctypes.c_void_p(handle),
            ctypes.byref(flags),
        )
    )


def require_launcher_for_frozen_build() -> None:
    """Reject direct startup of the packaged GUI child executable."""
    if not getattr(sys, "frozen", False):
        return
    if os.environ.get("H5T_LAUNCHER_OWNS_INSTANCE") != "1" or not launcher_handoff_is_valid():
        raise RuntimeError("Hammer5ToolsGUI.exe must be started by Hammer5Tools.exe.")


def launcher_supervises_process() -> bool:
    if os.environ.get("H5T_LAUNCHER_OWNS_INSTANCE") != "1":
        return False
    return not getattr(sys, "frozen", False) or launcher_handoff_is_valid()


def request_restart(application) -> None:
    """Exit through the launcher restart contract, or restart is unavailable."""
    if not launcher_supervises_process():
        raise RuntimeError("Application restart requires the native launcher.")
    application.exit(RESTART_EXIT_CODE)
