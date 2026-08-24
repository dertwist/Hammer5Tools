"""Application lifecycle requests understood by the native launcher."""

import os


RESTART_EXIT_CODE = 75


def launcher_supervises_process() -> bool:
    return os.environ.get("H5T_LAUNCHER_OWNS_INSTANCE") == "1"


def request_restart(application) -> None:
    """Exit through the launcher restart contract, or restart is unavailable."""
    if not launcher_supervises_process():
        raise RuntimeError("Application restart requires the native launcher.")
    application.exit(RESTART_EXIT_CODE)
