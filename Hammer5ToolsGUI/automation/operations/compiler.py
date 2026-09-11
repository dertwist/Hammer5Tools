"""Headless resource compilation for Source 2 assets."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from gui.settings.common import get_cs2_path


def compile_asset(
    path: str,
    cs2_path: str | None = None,
    force: bool = False,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Compile an uncompiled asset file (.vmat, .vmdl, .vsmart, etc.) using resourcecompiler.exe."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Asset file not found: '{path}'")

    root = cs2_path or get_cs2_path()
    if not root:
        raise RuntimeError("CS2 installation path is not configured")

    rc_exe = os.path.join(root, "game", "bin", "win64", "resourcecompiler.exe")
    if not os.path.isfile(rc_exe):
        raise FileNotFoundError(f"resourcecompiler.exe not found at '{rc_exe}'")

    cmd = [rc_exe, "-i", os.path.abspath(path)]
    if force:
        cmd.append("-f")

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        success = (proc.returncode == 0)

        # Parse warning/error indicators
        warnings = [line for line in stdout.splitlines() if "warning" in line.lower()]
        errors = [line for line in stderr.splitlines() if "error" in line.lower()]
        if not errors and proc.returncode != 0:
            errors = [line for line in stdout.splitlines() if "error" in line.lower() or "failed" in line.lower()]

        return {
            "path": path.replace("\\", "/"),
            "success": success,
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "warnings": warnings,
            "errors": errors,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "path": path.replace("\\", "/"),
            "success": False,
            "exit_code": -1,
            "error": f"Compilation timed out after {timeout_seconds} seconds",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    except Exception as exc:
        return {
            "path": path.replace("\\", "/"),
            "success": False,
            "exit_code": -1,
            "error": str(exc),
        }
