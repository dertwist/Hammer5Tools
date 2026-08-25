import os
import sys
from types import SimpleNamespace

import pytest

from gui import lifecycle
from gui.lifecycle import (
    RESTART_EXIT_CODE,
    launcher_supervises_process,
    relaunch_through_launcher,
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


def _launcher_stub(tmp_path, monkeypatch):
    launcher = tmp_path / "Hammer5Tools.exe"
    launcher.write_bytes(b"")
    monkeypatch.setattr(
        "hammer5tools_core.runtime_paths.resolve_runtime_paths",
        lambda: SimpleNamespace(install_root=tmp_path),
    )
    started = []
    monkeypatch.setattr("subprocess.Popen", lambda command, **kwargs: started.append((command, kwargs)))
    return launcher, started


@pytest.mark.skipif(os.name != "nt", reason="the launcher relaunch is Windows only")
def test_direct_start_relaunches_through_launcher(tmp_path, monkeypatch):
    monkeypatch.delenv("H5T_GUI_RELAUNCHED", raising=False)
    launcher, started = _launcher_stub(tmp_path, monkeypatch)

    assert relaunch_through_launcher(["map.vmap"])
    command, kwargs = started[0]
    assert command == [str(launcher), "map.vmap"]
    assert kwargs["env"]["H5T_GUI_RELAUNCHED"] == "1"


@pytest.mark.skipif(os.name != "nt", reason="the launcher relaunch is Windows only")
def test_relaunch_happens_only_once(tmp_path, monkeypatch):
    monkeypatch.setenv("H5T_GUI_RELAUNCHED", "1")
    _, started = _launcher_stub(tmp_path, monkeypatch)

    assert not relaunch_through_launcher([])
    assert started == []
