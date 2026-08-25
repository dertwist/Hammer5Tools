import importlib
import sys
from pathlib import Path

from core.runtime_paths import resolve_runtime_paths


def test_launcher_roots_are_authoritative(monkeypatch, tmp_path):
    install = tmp_path / "installed"
    monkeypatch.setenv("H5T_INSTALL_ROOT", str(install))
    monkeypatch.setenv("H5T_APP_ROOT", str(install / "application"))
    monkeypatch.setenv("H5T_RUNTIME_ROOT", str(install / "application" / "runtime"))
    monkeypatch.setenv("H5T_USER_DATA_ROOT", str(tmp_path / "data"))

    paths = resolve_runtime_paths()

    assert paths.install_root == (install).resolve()
    assert paths.app_root == (install / "application").resolve()
    assert paths.runtime_root == (install / "application" / "runtime").resolve()
    assert paths.user_data_root == (tmp_path / "data").resolve()
    assert paths.runtime_resource("tools", "tool.exe") == paths.runtime_root / "tools" / "tool.exe"
    assert paths.application_resource("icon.ico") == paths.app_root / "icon.ico"


def test_development_roots_keep_mutable_data_out_of_source_package(monkeypatch):
    for name in ("H5T_INSTALL_ROOT", "H5T_APP_ROOT", "H5T_RUNTIME_ROOT", "H5T_USER_DATA_ROOT"):
        monkeypatch.delenv(name, raising=False)

    paths = resolve_runtime_paths()

    assert paths.install_root == Path(__file__).resolve().parents[2]
    assert paths.user_data_root == paths.install_root / "userdata_dev"


def test_frozen_common_resolves_paths_without_error(monkeypatch, tmp_path):
    install = tmp_path / "installed"
    monkeypatch.setenv("H5T_INSTALL_ROOT", str(install))
    monkeypatch.setenv("H5T_APP_ROOT", str(install / "app"))
    monkeypatch.setenv("H5T_RUNTIME_ROOT", str(install / "app" / "runtime"))
    monkeypatch.setenv("H5T_USER_DATA_ROOT", str(tmp_path / "userdata"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    import gui.common
    importlib.reload(gui.common)

    assert gui.common.app_dir == (install / "app").resolve()
    assert gui.common.user_data_dir == (tmp_path / "userdata").resolve()


def test_crash_handler_writes_crash_logs(monkeypatch, tmp_path):
    install = tmp_path / "installed"
    user_data = tmp_path / "userdata"
    monkeypatch.setenv("H5T_INSTALL_ROOT", str(install))
    monkeypatch.setenv("H5T_USER_DATA_ROOT", str(user_data))

    from gui.main import _install_crash_handler

    _install_crash_handler()

    try:
        raise ValueError("Simulated failure for crash report test")
    except ValueError:
        exc_type, exc_val, exc_tb = sys.exc_info()
        monkeypatch.setattr("ctypes.windll.user32.MessageBoxW", lambda *args: 0, raising=False)
        from gui.widgets import common as widget_common
        monkeypatch.setattr(widget_common.ErrorInfo, "exec", lambda self: 0, raising=False)
        sys.excepthook(exc_type, exc_val, exc_tb)

    logs_dir = user_data / "logs"
    assert (logs_dir / "crash.log").exists()
    assert (logs_dir / "last_crash.txt").exists()
    content = (logs_dir / "last_crash.txt").read_text(encoding="utf-8")
    assert "Simulated failure for crash report test" in content
    assert "ValueError" in content
