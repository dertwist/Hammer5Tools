"""
Drives the UE Editor headlessly to run tools/ue_scripts/export_assets.py —
assumes the user has Unreal Engine installed locally. This is separate from
the CUE4Parse bridge (bridge_client.py), which needs no UE install but can't
read cooked texture pixels / mesh geometry out of an uncooked project (see
tools/unreal_bridge/README.md) — this fills that gap by launching the real
Editor to do the export.
"""

import os
import glob
import subprocess
from pathlib import Path

from src.runtime_paths import resolve_runtime_paths


def _export_script() -> Path:
    paths = resolve_runtime_paths()
    bundled = paths.runtime_resource("tools", "ue_scripts", "export_assets.py")
    return bundled if bundled.is_file() else paths.install_root / "tools" / "ue_scripts" / "export_assets.py"


class UeExportError(RuntimeError):
    pass


def find_uproject(project_content_dir: str) -> str:
    """The .uproject file sits one folder up from the project's Content dir."""
    project_root = os.path.dirname(os.path.normpath(project_content_dir))
    matches = glob.glob(os.path.join(project_root, "*.uproject"))
    if not matches:
        raise UeExportError(f"No .uproject found in {project_root} (expected next to the Content folder).")
    return matches[0]


_EDITOR_CMD_NAMES = (
    "UnrealEditor-Cmd.exe",
    "UE4Editor-Cmd.exe",
    "UE4Cmd.exe",
    "UnrealCmd.exe",
    "UnrealEditor.exe",
    "UE4Editor.exe",
)  # UE5 / UE4.x — renamed in the UE4->5 switch


def find_editor_cmd(engine_root: str) -> str:
    """The Editor binary under a UE install root. Accepts either the
    install root (…/UE_5.x or …/UE_4.27, containing Engine/) or the Engine
    folder itself.

    ponytail: Windows-only path (Win64) — add other platforms if H5T ever
    needs to run this on Linux/Mac.
    """
    for root in (os.path.join(engine_root, "Engine", "Binaries", "Win64"),
                 os.path.join(engine_root, "Binaries", "Win64")):
        for name in _EDITOR_CMD_NAMES:
            c = os.path.join(root, name)
            if os.path.isfile(c):
                return c
    raise UeExportError(
        f"No Editor binary ({' / '.join(_EDITOR_CMD_NAMES[:2])}) found under {engine_root} — point 'Unreal Engine install' "
        f"at the UE install folder (e.g. UE_4.27 or UE_5.x, containing Engine/Binaries/Win64)."
    )


# Kept in sync with tools/ue_scripts/export_assets.py DEFAULT_CONTENT_PATHS —
# duplicated rather than imported because that module only loads inside the UE
# Editor process (it imports `unreal` at call time, but lives outside src/).
DEFAULT_CONTENT_PATHS = "/Game;/Engine/MapTemplates;/Engine/BasicShapes"


def run_export(engine_root: str, project_content_dir: str, output_dir: str,
                content_path: str = DEFAULT_CONTENT_PATHS, timeout: int = 1800,
                on_line=None, assets: list = None, is_cancelled=None) -> str:
    """Runs the Editor commandlet synchronously and returns its combined
    stdout/stderr. Raises UeExportError on a non-zero exit or missing paths.
    If on_line callback is provided, streams output line by line in real time.
    If assets list is provided, only those assets will be exported.

    If is_cancelled is a no-arg callable returning truthy, the Editor process
    is killed and UeExportError is raised — this is the close path out of an
    export that can otherwise run for minutes.
    """
    if not output_dir:
        raise UeExportError("An output folder is required.")

    export_script = _export_script()
    if not export_script.is_file():
        raise UeExportError(
            f"Export script missing: {export_script}\nThe build is incomplete — reinstall Hammer5Tools."
        )

    editor_cmd = find_editor_cmd(engine_root)
    uproject = find_uproject(project_content_dir)

    env = dict(os.environ)
    env["H5T_UE_CONTENT_PATH"] = content_path
    env["H5T_UE_OUTPUT_DIR"] = output_dir
    if assets:
        env["H5T_UE_ASSET_LIST"] = ";".join(str(a) for a in assets)
    else:
        env.pop("H5T_UE_ASSET_LIST", None)

    cmd = [
        editor_cmd, uproject,
        "-run=pythonscript", f"-script={export_script}",
        "-unattended", "-nopause", "-nosplash", "-log",
    ]
    output_lines = []
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", env=env, bufsize=1,
        )
    except Exception as e:
        raise UeExportError(f"Failed to launch Editor process: {e}") from e

    try:
        if is_cancelled is not None and is_cancelled():
            raise UeExportError("UE export cancelled.")

        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                # The Editor prints progress throughout the run; polling here is
                # the only way to kill it before the script finishes.
                if is_cancelled is not None and is_cancelled():
                    raise UeExportError("UE export cancelled.")
                output_lines.append(line)
                line_str = line.rstrip("\r\n")
                if line_str and on_line:
                    on_line(line_str)
            proc.stdout.close()

        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise UeExportError(f"UE export timed out after {timeout} seconds.")
    except UeExportError:
        # Kill the Editor on any abort path (cancel or timeout) — without this
        # a cancelled export leaves a headless UE process holding the project.
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        raise

    output = "".join(output_lines)
    if returncode != 0:
        msg = f"UE export completed with exit code {returncode} (some assets or engine checks logged warnings/errors). Proceeding with conversion..."
        if on_line:
            on_line(msg)
    return output


def demo():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = os.path.join(tmp, "MyProject", "Content")
        os.makedirs(content_dir)
        uproject = os.path.join(tmp, "MyProject", "MyProject.uproject")
        open(uproject, "w").close()
        assert find_uproject(content_dir) == uproject

        try:
            find_editor_cmd(tmp)
        except UeExportError:
            pass
        else:
            raise AssertionError("expected UeExportError for a missing editor binary")

        # Test UE5 binary path
        editor_dir_ue5 = os.path.join(tmp, "UE_5.7", "Engine", "Binaries", "Win64")
        os.makedirs(editor_dir_ue5)
        editor_exe_ue5 = os.path.join(editor_dir_ue5, "UnrealEditor-Cmd.exe")
        open(editor_exe_ue5, "w").close()
        assert find_editor_cmd(os.path.join(tmp, "UE_5.7")) == editor_exe_ue5

        # Test UE4 binary path (4.27)
        editor_dir_ue4 = os.path.join(tmp, "UE_4.27", "Engine", "Binaries", "Win64")
        os.makedirs(editor_dir_ue4)
        editor_exe_ue4 = os.path.join(editor_dir_ue4, "UE4Editor-Cmd.exe")
        open(editor_exe_ue4, "w").close()
        assert find_editor_cmd(os.path.join(tmp, "UE_4.27")) == editor_exe_ue4

    print("ok")


if __name__ == "__main__":
    demo()
