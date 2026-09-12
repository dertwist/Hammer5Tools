"""
Drives the UE Editor headlessly to run tools/ue_scripts/export_assets.py —
assumes the user has Unreal Engine installed locally. This is separate from
the CUE4Parse bridge (bridge_client.py), which needs no UE install but can't
read cooked texture pixels / mesh geometry out of an uncooked project (see
tools/unreal_bridge/README.md) — this fills that gap by launching the real
Editor to do the export.
"""

import collections
import json
import os
import glob
import re
import subprocess
from pathlib import Path

from core.runtime_paths import resolve_runtime_paths


def _export_script() -> Path:
    paths = resolve_runtime_paths()
    bundled = paths.runtime_resource("tools", "ue_scripts", "export_assets.py")
    if bundled.is_file():
        return bundled
    gui_root = Path(__file__).resolve().parents[2]
    return gui_root / "tools" / "ue_scripts" / "export_assets.py"


class UeExportError(RuntimeError):
    pass


# Written into the export cache: one asset path key per line, for every asset
# the Editor has been asked to export.
EXPORT_MANIFEST = "exported_assets.txt"


def load_export_manifest(tmp_dir: str) -> set:
    """The asset path keys the Editor has already been asked for.

    Files alone cannot say whether the cache is complete. Plenty of assets
    produce no file however often they are exported (curves, data assets,
    material functions), and the old check papered over that by only ever asking
    about assets whose *name* looked like a mesh or a texture — so a project's
    "BogMyrtleBush_01" in an Environments/Foliage folder was never queued at
    all, and every map that placed it got a vmdl pointing at an FBX nobody
    wrote. Recording what was asked for is the only answer that does not depend
    on guessing an asset's type from its name.
    """
    path = os.path.join(tmp_dir or "", EXPORT_MANIFEST)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return {line.strip() for line in handle if line.strip()}
    except OSError:
        return set()


def record_export_manifest(tmp_dir: str, keys) -> None:
    """Add these assets to the manifest — asked for, so never asked again."""
    from .asset_selection import asset_path_key

    if not tmp_dir or not keys:
        return
    known = load_export_manifest(tmp_dir) | {asset_path_key(k) for k in keys}
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        with open(os.path.join(tmp_dir, EXPORT_MANIFEST), "w", encoding="utf-8") as handle:
            handle.write("\n".join(sorted(known)) + "\n")
    except OSError:
        pass    # A cache that cannot be written still converts; it just re-exports.


# The Editor prints tens of thousands of lines per run — asset registry chatter,
# shader compile stats, package load warnings — none of which a user porting a
# map can act on, and all of which used to go straight into the app console one
# Qt signal at a time. export_assets.py tags the handful of lines that matter
# with "[H5T][level]"; only those and genuine engine failures are forwarded.
_H5T = re.compile(r"\[H5T\]\[(\w+)\]\s?(.*?)\s*$")
_FATAL = re.compile(r"Fatal error|Assertion failed|LogPython:\s*Error:", re.IGNORECASE)
# UE closes a run by reprinting every warning under "Warning/Error Summary
# (Unique only)", each one re-wrapped in "LogInit: Display:". Our progress lines
# go out as warnings — the only verbosity that survives the pipe — so without
# this the whole export replays itself in the console after it finishes.
_SUMMARY_ECHO = re.compile(r"LogInit:\s*Display:")
_LEVELS = frozenset(("info", "warn", "error", "success"))

# Raw Editor output kept for diagnostics. A full run's log is hundreds of
# megabytes of text; the tail is what actually explains a crash.
_RAW_TAIL_LINES = 200


def engine_version(engine_root: str) -> str:
    """'5.4.4' for a UE install root, or "" when it cannot be determined.

    Read from Engine/Build/Build.version, which every install (launcher or
    source build) ships, falling back to the UE_<version> folder name.
    """
    for base in (os.path.join(engine_root, "Engine"), engine_root):
        try:
            with open(os.path.join(base, "Build", "Build.version"), encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        parts = [data.get("MajorVersion"), data.get("MinorVersion"), data.get("PatchVersion")]
        version = ".".join(str(p) for p in parts if isinstance(p, int))
        if version:
            return version
    match = re.search(r"UE_?(\d[\d.]*)", os.path.basename(os.path.normpath(engine_root)))
    return match.group(1) if match else ""


def filter_line(line: str):
    """(text, level) for a line worth showing the user, or None to drop it."""
    if _SUMMARY_ECHO.search(line):
        return None
    match = _H5T.search(line)
    if match:
        level, text = match.group(1), match.group(2)
        return text, (level if level in _LEVELS else "info")
    line = line.strip()
    if line and _FATAL.search(line):
        return line, "error"
    return None


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

    Only Windows Win64 editor binaries are supported.
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
                on_line=None, assets: list = None, is_cancelled=None,
                import_nanite: bool = False) -> str:
    """Runs the Editor commandlet synchronously and returns the tail of its raw
    output. Raises UeExportError on a non-zero exit or missing paths.

    on_line(text, level) is called for each line worth reporting — the progress
    and summary lines export_assets.py tags, plus fatal engine errors. Everything
    else the Editor prints is dropped; see filter_line.
    If assets list is provided, only those assets will be exported.

    If is_cancelled is a no-arg callable returning truthy, the Editor process
    is killed and UeExportError is raised — this is the close path out of an
    export that can otherwise run for minutes.

    import_nanite switches Nanite off on each Nanite mesh before exporting it,
    so the FBX carries the real geometry instead of the low-poly fallback proxy
    UE builds for it. It defaults off: the rebuild it forces is the single
    largest cost in a first port. See export_assets._disable_nanite.
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
    env["H5T_UE_NANITE"] = "1" if import_nanite else "0"
    if assets:
        env["H5T_UE_ASSET_LIST"] = ";".join(str(a) for a in assets)
    else:
        env.pop("H5T_UE_ASSET_LIST", None)

    cmd = [
        editor_cmd, uproject,
        "-run=pythonscript", f"-script={export_script}",
        "-unattended", "-nopause", "-nosplash", "-nosound", "-log",
    ]
    version = engine_version(engine_root)
    tag = f"[UE {version}]" if version else "[UE]"
    if on_line:
        on_line(f"Running Unreal Engine {version}".rstrip(), "info")

    output_lines = collections.deque(maxlen=_RAW_TAIL_LINES)
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
                reportable = filter_line(line) if on_line else None
                if reportable:
                    on_line(f"{tag} {reportable[0]}", reportable[1])
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
    if returncode != 0 and on_line:
        on_line(f"{tag} exited with code {returncode}; converting what was exported.", "warn")
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

        # Build.version is authoritative; the folder name is the fallback, which
        # is all a source build in a non-UE_ folder leaves us.
        assert engine_version(os.path.join(tmp, "UE_5.7")) == "5.7"
        build_dir = os.path.join(tmp, "UE_5.7", "Engine", "Build")
        os.makedirs(build_dir)
        with open(os.path.join(build_dir, "Build.version"), "w", encoding="utf-8") as handle:
            json.dump({"MajorVersion": 5, "MinorVersion": 7, "PatchVersion": 2}, handle)
        assert engine_version(os.path.join(tmp, "UE_5.7")) == "5.7.2"
        assert engine_version(os.path.join(tmp, "SourceBuild")) == ""

        # The console only ever sees our own tagged lines and real failures.
        assert filter_line("LogPython: [H5T][info] Exported 12/40  (45.3 MB)") == (
            "Exported 12/40  (45.3 MB)", "info")
        assert filter_line("[H5T][warn] 3 asset(s) produced no file.") == (
            "3 asset(s) produced no file.", "warn")
        assert filter_line("[H5T][bogus] hi") == ("hi", "info"), "unknown level degrades to info"
        # The real shape a line arrives in: export_assets._say goes out as
        # log_warning, the only verbosity that survives a commandlet's stdout,
        # so every one of our lines is wrapped in UE's timestamped Warning
        # prefix. Captured from a UE 5.7 run.
        assert filter_line(
            "[2026.09.12-14.27.43:100][  0]LogPython: Warning: [H5T][success] Exported 40/40"
        ) == ("Exported 40/40", "success")
        # The same line as UE replays it in its closing summary. Forwarding both
        # made every export print itself twice.
        assert filter_line(
            "[2026.09.12-14.27.43:100][  0]LogInit: Display: LogPython: Warning: "
            "[H5T][success] Exported 40/40"
        ) is None
        assert filter_line("LogAssetRegistry: Asset discovery search completed") is None
        assert filter_line("LogShaderCompilers: Display: Compiled 412 shaders") is None
        assert filter_line("") is None
        assert filter_line("LogWindows: Fatal error: [File:D:/x.cpp] Assertion failed")[1] == "error"

        # The manifest is what stops the cache check from having to guess an
        # asset's type from its name. An asset that was asked for counts as done
        # whether or not the Editor could write a file for it — a curve never
        # produces one — and it is keyed by path, so two packs' same-named
        # assets are tracked separately.
        cache = os.path.join(tmp, "cache")
        assert load_export_manifest(cache) == set()
        record_export_manifest(cache, ["KiteDemo/Meshes/SM_Rock.uasset",
                                       "Poplar/Meshes/SM_Rock.uasset"])
        assert load_export_manifest(cache) == {"kitedemo/meshes/sm_rock", "poplar/meshes/sm_rock"}
        # Recording again adds to the manifest rather than replacing it.
        record_export_manifest(cache, ["KiteDemo/Curves/ChromaticCurve.uasset"])
        assert load_export_manifest(cache) == {
            "kitedemo/meshes/sm_rock", "poplar/meshes/sm_rock", "kitedemo/curves/chromaticcurve",
        }

    print("ok")


if __name__ == "__main__":
    demo()
