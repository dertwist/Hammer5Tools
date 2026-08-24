import pytest

from hammer5tools_gui.lifecycle import RESTART_EXIT_CODE, request_restart


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
