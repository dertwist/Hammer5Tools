"""Runtime root contract shared by packaged and development startup."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class RuntimePaths:
    """Separates installed application, bundled runtime, and mutable user data."""

    install_root: Path
    app_root: Path
    runtime_root: Path
    user_data_root: Path

    def runtime_resource(self, *parts: str) -> Path:
        """Return a resource inside the immutable bundled runtime."""
        return self.runtime_root.joinpath(*parts)

    def application_resource(self, *parts: str) -> Path:
        """Return a resource shipped beside the GUI executable."""
        return self.app_root.joinpath(*parts)


def resolve_runtime_paths() -> RuntimePaths:
    """Resolve launcher-provided roots with safe packaged/development fallbacks."""
    environment = os.environ
    if environment.get("H5T_INSTALL_ROOT"):
        install = Path(environment["H5T_INSTALL_ROOT"]).resolve()
        app = Path(environment.get("H5T_APP_ROOT", install / "app")).resolve()
        runtime = Path(environment.get("H5T_RUNTIME_ROOT", app / "runtime")).resolve()
        user_data = Path(environment.get("H5T_USER_DATA_ROOT", install / "userdata")).resolve()
        return RuntimePaths(install, app, runtime, user_data)

    if getattr(sys, "frozen", False):
        app = Path(sys.executable).resolve().parent
        install = app.parent if app.name.lower() == "app" else app
        runtime = Path(getattr(sys, "_MEIPASS", app)).resolve()
        return RuntimePaths(install, app, runtime, Path.home() / "Hammer5Tools")

    install = Path(__file__).resolve().parents[3]
    return RuntimePaths(install, install, install, install / "userdata_dev")
