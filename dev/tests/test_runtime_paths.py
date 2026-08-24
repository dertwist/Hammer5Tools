from pathlib import Path

from src.runtime_paths import resolve_runtime_paths


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


def test_development_roots_keep_mutable_data_out_of_source_package(monkeypatch):
    for name in ("H5T_INSTALL_ROOT", "H5T_APP_ROOT", "H5T_RUNTIME_ROOT", "H5T_USER_DATA_ROOT"):
        monkeypatch.delenv(name, raising=False)

    paths = resolve_runtime_paths()

    assert paths.install_root == Path(__file__).resolve().parents[2]
    assert paths.user_data_root == paths.install_root / "userdata_dev"
