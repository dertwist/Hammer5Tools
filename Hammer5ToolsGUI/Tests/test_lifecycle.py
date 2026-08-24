import sys

import pytest

from hammer5tools_gui import lifecycle
from hammer5tools_gui.lifecycle import (
    RESTART_EXIT_CODE,
    launcher_supervises_process,
    require_launcher_for_frozen_build,
    request_restart,
)


class _Application:
    def __init__(self):
        self.exit_code = None

    def exit(self, code):
        self.exit_code = code


def test_restart_uses_supervisor_exit_code(monkeypatch):
    monkeypatch.setenv("H5T_LAUNCHER_OWNS_INSTANCE", "1")
    application = _Application()
    request_restart(application)
    assert application.exit_code == RESTART_EXIT_CODE


def test_restart_rejects_unsupervised_development_run(monkeypatch):
    monkeypatch.delenv("H5T_LAUNCHER_OWNS_INSTANCE", raising=False)
    with pytest.raises(RuntimeError):
        request_restart(_Application())


def test_source_build_does_not_require_launcher(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    require_launcher_for_frozen_build()


def test_frozen_build_rejects_direct_gui_start(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("H5T_LAUNCHER_OWNS_INSTANCE", raising=False)
    monkeypatch.delenv("H5T_LAUNCHER_HANDOFF", raising=False)
    with pytest.raises(RuntimeError, match="must be started by Hammer5Tools.exe"):
        require_launcher_for_frozen_build()


def test_frozen_build_requires_valid_handoff(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("H5T_LAUNCHER_OWNS_INSTANCE", "1")
    monkeypatch.setenv("H5T_LAUNCHER_HANDOFF", "0")
    assert not launcher_supervises_process()
    with pytest.raises(RuntimeError):
        require_launcher_for_frozen_build()


def test_frozen_build_accepts_launcher_handoff(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("H5T_LAUNCHER_OWNS_INSTANCE", "1")
    monkeypatch.setenv("H5T_LAUNCHER_HANDOFF", "123")
    monkeypatch.setattr(lifecycle, "launcher_handoff_is_valid", lambda: True)
    require_launcher_for_frozen_build()
    assert launcher_supervises_process()
