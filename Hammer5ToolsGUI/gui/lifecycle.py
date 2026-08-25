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


_RELAUNCH_MARKER_ENV = "H5T_GUI_RELAUNCHED"


def relaunch_through_launcher(arguments) -> bool:
    """Hand a direct GUI start over to Hammer5Tools.exe, keeping crashes supervised.

    Returns whether the launcher took over, in which case the caller must exit.
    """
    if os.name != "nt" or os.environ.get(_RELAUNCH_MARKER_ENV) == "1":
        return False  # already relaunched once: the handoff is broken, not missing
    try:
        from hammer5tools_core.runtime_paths import resolve_runtime_paths
        launcher = resolve_runtime_paths().install_root / "Hammer5Tools.exe"
        if not launcher.is_file():
            return False
        import subprocess
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        subprocess.Popen(
            [str(launcher), *arguments],
            env={**os.environ, _RELAUNCH_MARKER_ENV: "1"},
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        )
        return True
    except (OSError, ImportError):
        return False


def launcher_supervises_process() -> bool:
    if os.environ.get("H5T_LAUNCHER_OWNS_INSTANCE") != "1":
        return False
    return not getattr(sys, "frozen", False) or launcher_handoff_is_valid()


def request_restart(application) -> None:
    """Exit through the launcher restart contract, or restart is unavailable."""
    if not launcher_supervises_process():
        raise RuntimeError("Application restart requires the native launcher.")
    application.exit(RESTART_EXIT_CODE)
