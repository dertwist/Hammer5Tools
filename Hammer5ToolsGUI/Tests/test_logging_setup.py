"""setup_logging() must put records in a file without needing a console."""
import logging
import sys

sys.path.insert(0, "Hammer5ToolsGUI")

from gui import logs


def _reset_root():
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, "_h5t", False)]:
        root.removeHandler(handler)
        handler.close()


def test_records_reach_the_log_file(monkeypatch, tmp_path):
    monkeypatch.setattr(logs, "log_dir", lambda: tmp_path / "logs")
    _reset_root()
    try:
        logs.setup_logging()
        logging.getLogger("gui.test").error("boom %s", 1)
        for handler in logging.getLogger().handlers:
            handler.flush()
        written = (tmp_path / "logs" / "hammer5tools.log").read_text(encoding="utf-8")
    finally:
        _reset_root()
    assert "boom 1" in written
    assert "ERROR" in written


def test_setup_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(logs, "log_dir", lambda: tmp_path / "logs")
    _reset_root()
    try:
        logs.setup_logging()
        first = len(logging.getLogger().handlers)
        logs.setup_logging()
        assert len(logging.getLogger().handlers) == first
    finally:
        _reset_root()


def test_survives_a_windowed_build_with_no_stderr(monkeypatch, tmp_path):
    """sys.stderr is None without a console; a StreamHandler for it would raise."""
    monkeypatch.setattr(logs, "log_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(sys, "stderr", None)
    _reset_root()
    try:
        logs.setup_logging()
        logging.getLogger("gui.test").error("no console here")
        for handler in logging.getLogger().handlers:
            handler.flush()
        written = (tmp_path / "logs" / "hammer5tools.log").read_text(encoding="utf-8")
    finally:
        _reset_root()
    assert "no console here" in written
