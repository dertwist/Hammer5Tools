"""
Python client & thread runner for SourcePorter.
Supports direct .NET library invocation via `pythonnet` (in-process CLR interop)
with fallback to headless subprocess execution (`SourcePorter.Cli`).
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Callable
from PySide6.QtCore import QThread, Signal, QObject


def candidate_cli_paths() -> List[Path]:
    """Locations to search for SourcePorter.Cli executable or DLL."""
    env = os.environ.get("H5T_SOURCE_PORTER_CLI")
    candidates = []
    if env:
        candidates.append(Path(env))

    root = Path(__file__).resolve().parents[3]  # repo root (src/forms/source_porter -> repo)

    # 1. Published / build binaries in net_core
    candidates.append(root / "src" / "net_core" / "SourcePorter.Cli" / "publish" / "SourcePorter.Cli.exe")
    candidates.append(root / "src" / "net_core" / "SourcePorter.Cli" / "publish" / "SourcePorter.Cli.dll")
    candidates.append(root / "src" / "net_core" / "SourcePorter.Cli" / "bin" / "Release" / "net9.0" / "SourcePorter.Cli.exe")
    candidates.append(root / "src" / "net_core" / "SourcePorter.Cli" / "bin" / "Release" / "net9.0" / "SourcePorter.Cli.dll")
    candidates.append(root / "src" / "net_core" / "SourcePorter.Cli" / "bin" / "Debug" / "net9.0" / "SourcePorter.Cli.exe")
    candidates.append(root / "src" / "net_core" / "SourcePorter.Cli" / "bin" / "Debug" / "net9.0" / "SourcePorter.Cli.dll")

    # 2. Frozen (PyInstaller) bundle
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys._MEIPASS) / "source_porter" / "SourcePorter.Cli.exe")
        candidates.append(Path(sys._MEIPASS) / "source_porter" / "SourcePorter.Cli.dll")

    return candidates


def find_cli_target() -> Optional[Path]:
    """Returns the existing Path to SourcePorter.Cli.exe or SourcePorter.Cli.dll."""
    for p in candidate_cli_paths():
        if p and p.is_file():
            return p
    return None


def find_dotnet() -> Optional[str]:
    """Locate dotnet host."""
    exe = shutil.which("dotnet")
    if exe:
        return exe
    local = Path.home() / ".dotnet" / ("dotnet.exe" if os.name == "nt" else "dotnet")
    return str(local) if local.is_file() else None


def is_pythonnet_available() -> bool:
    """Check if pythonnet and SourcePorter.Core.dll are available for direct CLR invocation."""
    try:
        from src.dotnet import DotNetInterop
        interop = DotNetInterop()
        sp_dll = interop.paths.source_porter_core
        return sp_dll.is_file()
    except Exception:
        return False


class SourcePorterClient:
    """Wrapper verifying SourcePorter availability via pythonnet or subprocess CLI."""

    def __init__(self, cli_path: Optional[str] = None, dotnet_path: Optional[str] = None):
        target = Path(cli_path) if cli_path else find_cli_target()
        self.cli_target = target
        self.dotnet = dotnet_path or find_dotnet()

    def is_available(self) -> bool:
        if is_pythonnet_available():
            return True
        if not self.cli_target:
            return False
        if self.cli_target.suffix.lower() == ".dll" and not self.dotnet:
            return False
        return True

    def why_unavailable(self) -> str:
        if not is_pythonnet_available() and not self.cli_target:
            return "SourcePorter.Core.dll assembly / CLI build not found. Build src/net_core/SourcePorter.Core."
        if not is_pythonnet_available() and self.cli_target and self.cli_target.suffix.lower() == ".dll" and not self.dotnet:
            return ".NET runtime ('dotnet') not found. Install .NET 9 or .NET 10."
        return ""

    def build_cmd(self, sub_cmd: str, args: List[str]) -> List[str]:
        if not self.cli_target:
            raise RuntimeError(self.why_unavailable())

        cmd = []
        if self.cli_target.suffix.lower() == ".dll":
            cmd = [self.dotnet, str(self.cli_target)]
        else:
            cmd = [str(self.cli_target)]

        cmd.append(sub_cmd)
        cmd.extend(args)
        return cmd


class PorterThread(QThread):
    """QThread worker running SourcePorter via pythonnet direct CLR interop or process fallback."""

    log_signal = Signal(str)
    finished_signal = Signal(int)  # return code (0 = success)

    def __init__(self, client: SourcePorterClient, sub_cmd: str, cmd_args: List[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.client = client
        self.sub_cmd = sub_cmd
        self.cmd_args = cmd_args
        self.process: Optional[subprocess.Popen] = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass

    def run(self):
        # Try direct pythonnet execution first if available
        if is_pythonnet_available():
            try:
                self.log_signal.emit(f"[SourcePorter pythonnet] Direct .NET invocation ({self.sub_cmd})...")
                code = self._run_pythonnet()
                self.finished_signal.emit(code)
                return
            except Exception as ex:
                self.log_signal.emit(f"[SourcePorter pythonnet Note] Direct call fallback to subprocess: {ex}")

        # Subprocess fallback
        try:
            full_cmd = self.client.build_cmd(self.sub_cmd, self.cmd_args)
            self.log_signal.emit(f"[SourcePorter Process] Executing: {' '.join(full_cmd)}")

            self.process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            if self.process.stdout:
                for line in iter(self.process.stdout.readline, ''):
                    if self._is_cancelled:
                        break
                    line_str = line.strip()
                    if line_str:
                        self.log_signal.emit(line_str)

            self.process.wait()
            ret_code = self.process.returncode if not self._is_cancelled else -1
            self.finished_signal.emit(ret_code)

        except Exception as ex:
            self.log_signal.emit(f"[SourcePorter Error] {ex}")
            self.finished_signal.emit(1)

    def _run_pythonnet(self) -> int:
        from src.dotnet import DotNetInterop
        interop = DotNetInterop()
        interop.setup_source_porter()

        import SourcePorter.Core.Domain as Domain
        import SourcePorter.Core.Validation as Validation
        import System
        from System import Action, String

        def on_log(line):
            if not self._is_cancelled:
                self.log_signal.emit(str(line))

        cs_log = Action[String](on_log)

        if self.sub_cmd == "validate":
            cs2_dir = self.cmd_args[0]
            addon = self.cmd_args[1]
            cs2 = Domain.Cs2Install(cs2_dir)
            validator = Validation.AssetValidator(cs2, addon)
            report = validator.Validate(cs_log)
            # Validate() only logs progress/summary lines via cs_log — the individual
            # findings live in report.Issues and were never surfaced here (the CLI's
            # subprocess path prints them via Program.cs's PrintReport, but that code
            # never runs for this in-process call). List every one, uncapped.
            for issue in report.Issues:
                if self._is_cancelled:
                    break
                self.log_signal.emit(f"  [{issue.Kind}] {issue.Source} -> {issue.Detail}")
            return 1 if report.HasIssues else 0

        # Fall back to subprocess for non-validate subcommands or if full pipeline uses Cli
        full_cmd = self.client.build_cmd(self.sub_cmd, self.cmd_args)
        self.process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )

        if self.process.stdout:
            for line in iter(self.process.stdout.readline, ''):
                if self._is_cancelled:
                    break
                line_str = line.strip()
                if line_str:
                    self.log_signal.emit(line_str)

        self.process.wait()
        return self.process.returncode if not self._is_cancelled else -1
