"""Application logging.

Shipped builds run without a console (see no_console.py), so anything a
swallowed exception prints goes nowhere. One rotating file next to the crash
logs keeps those failures readable after the fact.

Modules log through ``logging.getLogger(__name__)``; this module only decides
where the records end up, and is configured once from main().
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_MAX_BYTES = 2 * 1024 * 1024
_BACKUPS = 3


def log_dir() -> Path:
    """The same logs/ directory the crash handler writes to."""
    try:
        from core.runtime_paths import resolve_runtime_paths
        return resolve_runtime_paths().user_data_root / "logs"
    except Exception:
        return Path.home() / "Hammer5Tools" / "logs"


def setup_logging(level: int = logging.INFO) -> None:
    """Attach the file handler (and stderr, when there is one). Idempotent."""
    root = logging.getLogger()
    if any(getattr(handler, "_h5t", False) for handler in root.handlers):
        return

    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT)

    try:
        directory = log_dir()
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            directory / "hammer5tools.log", maxBytes=_MAX_BYTES,
            backupCount=_BACKUPS, encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler._h5t = True
        root.addHandler(file_handler)
    except OSError:
        # A read-only or missing user-data directory must not stop the app.
        pass

    # sys.stderr is None in a windowed build; adding a handler for it would
    # make every log call raise.
    if sys.stderr is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler._h5t = True
        root.addHandler(stream_handler)
