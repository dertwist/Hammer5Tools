"""
.NET Interop module for KeyValues (Datamodel.NET) handling — the git .vmap
3-way merge tool's last pythonnet consumer (gui/gitvmapmerge.py). Everything
else that used to load a .NET assembly through here (SmartProp, VPK/compiled
resources, VMAP, SourcePorter's porting pipeline) now goes through the
NativeAOT ABI in hammer5tools_core/native.py instead.
"""

import os
import sys
import json
import subprocess
import webbrowser
import urllib.request
from pathlib import Path
from typing import Optional, Tuple, Any
import unittest
import binascii

tests_path = Path(__file__).parent.parent / 'tests'
RUNTIME_CONFIG_NAME = 'Hammer5Tools.runtimeconfig.json'


class DotNetPaths:
    """Centralized path management for .NET assemblies."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            development_external = Path(__file__).resolve().parents[2] / 'Hammer5ToolsCore' / 'external'
            if development_external.is_dir():
                base_dir = development_external
            else:
                from hammer5tools_core.runtime_paths import resolve_runtime_paths

                base_dir = resolve_runtime_paths().runtime_resource('external')
        else:
            base_dir = Path(base_dir)

        self.keyvalues2_net = base_dir / 'Datamodel.NET.dll'


class DotNetInterop:
    """Main .NET interop handler."""

    def __init__(self):
        self.paths = DotNetPaths()
        self._clr = None
        self._system = None
        self._initialized = False

    def _init_pythonnet(self):
        """Initialize Python.NET if not already done."""
        if self._initialized:
            return

        try:
            from pythonnet import load

            runtime_config = None

            # Check for bundled runtime in frozen (PyInstaller) state
            if getattr(sys, 'frozen', False):
                from hammer5tools_core.runtime_paths import resolve_runtime_paths
                bundled_dotnet = str(resolve_runtime_paths().runtime_resource('dotnet'))
                if os.path.exists(bundled_dotnet):
                    # Set DOTNET_ROOT to help clr_loader find the bundled runtime
                    os.environ["DOTNET_ROOT"] = bundled_dotnet
                    os.environ["DOTNET_ROOT_X64"] = bundled_dotnet
                    # Point to the runtime config if it exists
                    bundled_config = os.path.join(bundled_dotnet, RUNTIME_CONFIG_NAME)
                    if os.path.exists(bundled_config):
                        runtime_config = bundled_config

            if runtime_config is None:
                local_config = Path(__file__).parent / 'external' / 'dotnet' / RUNTIME_CONFIG_NAME
                if not local_config.exists():
                    local_config = Path(__file__).parent / 'external' / RUNTIME_CONFIG_NAME
                if local_config.exists():
                    runtime_config = str(local_config)

            if runtime_config:
                load("coreclr", runtime_config=runtime_config)
            else:
                load("coreclr")
                
            import clr
            self._clr = clr
            self._initialized = True
        except ImportError as e:
            raise RuntimeError("Python.NET not available. Install with: pip install pythonnet") from e
        except Exception as e:
            raise RuntimeError(
                ".NET Desktop Runtime 10.0 or newer is required for this tool. "
                "Install it from https://dotnet.microsoft.com/download/dotnet/10.0"
            ) from e

    def _load_assembly(self, path: Path) -> None:
        """Load a .NET assembly with error handling."""
        if not path.exists():
            raise FileNotFoundError(f"Assembly not found: {path}")

        try:
            self._clr.AddReference(str(path))
        except Exception:
            # Fallback to LoadFrom for problematic assemblies
            import System
            assembly = System.Reflection.Assembly.LoadFrom(str(path))
            self._clr.AddReference(assembly)

    def setup_keyvalues(self) -> Tuple[Any, Any, Any]:
        """Setup KeyValues2 .NET interop."""
        self._init_pythonnet()

        # Ensure DLL directory is in PATH
        dll_dir = self.paths.keyvalues2_net.parent
        if str(dll_dir) not in sys.path:
            sys.path.append(str(dll_dir))

        self._load_assembly(self.paths.keyvalues2_net)

        import Datamodel
        from Datamodel.Codecs import DeferredMode

        return Datamodel.Datamodel, Datamodel.Element, DeferredMode


class DotNetRuntimeChecker:
    """Check and manage .NET runtime installation."""

    def __init__(self, min_version: str = "10.0"):
        self.min_version = min_version

    def check_runtime(self, show_dialog: bool = True) -> bool:
        """Check if compatible .NET runtime is installed."""
        # 1. Check for bundled runtime first (in frozen state)
        if getattr(sys, 'frozen', False):
            from hammer5tools_core.runtime_paths import resolve_runtime_paths
            bundled_dotnet = str(resolve_runtime_paths().runtime_resource('dotnet'))
            if self._bundled_runtime_is_complete(bundled_dotnet):
                return True

        try:
            result = subprocess.run(
                ["dotnet", "--list-runtimes"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            # Check for WindowsDesktop runtime
            for line in result.stdout.splitlines():
                if line.startswith("Microsoft.WindowsDesktop.App"):
                    parts = line.split()
                    if len(parts) >= 2:
                        version = parts[1]
                        # Numeric compare — a lexical ">=" wrongly accepts "9.0"
                        # for a "10.0" minimum ("9" > "1").
                        def _ver_tuple(v):
                            out = []
                            for part in v.split(".")[:2]:
                                try:
                                    out.append(int(part))
                                except ValueError:
                                    out.append(0)
                            return tuple(out)
                        if _ver_tuple(version) >= _ver_tuple(self.min_version):
                            return True

            if show_dialog:
                self._show_download_dialog()
            else:
                setup_keyvalues2()
            return False

        except (FileNotFoundError, subprocess.CalledProcessError):
            if show_dialog:
                self._show_download_dialog()
            else:
                setup_keyvalues2()
            return False

    def _bundled_runtime_is_complete(self, bundled_dotnet: str) -> bool:
        """Validate the bundled runtime enough to avoid pythonnet hostfxr crashes."""
        if not os.path.isdir(bundled_dotnet):
            return False

        runtime_config = os.path.join(bundled_dotnet, RUNTIME_CONFIG_NAME)
        if not os.path.isfile(runtime_config):
            return False

        shared = os.path.join(bundled_dotnet, "shared")
        for framework in ("Microsoft.NETCore.App", "Microsoft.WindowsDesktop.App"):
            framework_dir = os.path.join(shared, framework)
            if not os.path.isdir(framework_dir):
                return False
            versions = [v for v in os.listdir(framework_dir) if v.startswith(self.min_version)]
            if not versions:
                return False

        return True

    def _show_download_dialog(self):
        """Show dialog to download .NET runtime."""
        try:
            from PySide6.QtWidgets import QMessageBox

            latest_version = self._get_latest_version()
            download_url = self._get_download_url(latest_version)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(".NET Desktop Runtime Required")
            msg.setText(f"Required .NET Desktop runtime >= {self.min_version} not found.")
            msg.setInformativeText(f"Please download and install .NET {latest_version} for Windows.")
            msg.setStandardButtons(QMessageBox.Open | QMessageBox.Cancel)

            if msg.exec() == QMessageBox.Open:
                webbrowser.open(download_url)
                sys.exit(0)

        except Exception:
            # Fallback to generic download page
            webbrowser.open("https://dotnet.microsoft.com/download")

    def _get_latest_version(self) -> str:
        """Get latest .NET version from Microsoft API."""
        try:
            url = "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/releases-index.json"
            with urllib.request.urlopen(url) as response:
                data = json.load(response)
                releases = data.get("releases-index", [])
                for release in releases:
                    channel_version = release.get("channel-version", "")
                    if channel_version >= self.min_version:
                        return channel_version
                if releases:
                    return releases[0].get("channel-version", self.min_version)
        except Exception:
            pass
        return self.min_version

    def _get_download_url(self, version: str) -> str:
        """Get download URL for specific .NET version."""
        try:
            url = f"https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/{version}/releases.json"
            with urllib.request.urlopen(url) as response:
                data = json.load(response)
                latest = data.get("latest-release", version)
                return f"https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/{latest}/windowsdesktop-runtime-{latest}-win-x64.exe"
        except Exception:
            return f"https://dotnet.microsoft.com/en-us/download/dotnet/{version}"


# Convenience functions for backward compatibility
def check_dotnet_runtime(min_version: str = "10.0", dev_mode: bool = False) -> bool:
    """Check .NET runtime availability."""
    checker = DotNetRuntimeChecker(min_version)
    return checker.check_runtime(show_dialog=not dev_mode)


def setup_keyvalues2():
    """Setup KeyValues2 interop (legacy function)."""
    interop = DotNetInterop()
    return interop.setup_keyvalues()


if __name__ == "__main__":
    interop = DotNetInterop()
    assert interop.setup_keyvalues() is not None
    print("Self-check passed: KeyValues2 (Datamodel.NET) loaded")
