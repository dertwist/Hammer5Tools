"""Compile UnrealPorter's generated Source 2 asset descriptors."""

import os
import subprocess
import tempfile

from PySide6.QtCore import Signal

from ._worker_base import CancellableWorker


COMPILE_EXTENSIONS = frozenset({".vmap", ".vmat", ".vmdl", ".vsmart"})


def find_compile_assets(output_dir: str, excluded_dir: str = "") -> list[str]:
    """Return compilable descriptors below *output_dir*, excluding the export cache."""
    output_path = os.path.abspath(output_dir)
    excluded_path = os.path.abspath(excluded_dir) if excluded_dir else ""
    assets = []

    for root, dirs, files in os.walk(output_path):
        if excluded_path:
            dirs[:] = [
                name for name in dirs
                if not _is_within(os.path.join(root, name), excluded_path)
            ]
        for name in files:
            if os.path.splitext(name)[1].lower() in COMPILE_EXTENSIONS:
                assets.append(os.path.join(root, name))

    return sorted(assets, key=str.casefold)


def snapshot_compile_assets(output_dir: str, excluded_dir: str = "") -> dict[str, tuple[int, int]]:
    """Capture descriptor timestamps and sizes so only this port run is compiled."""
    snapshot = {}
    for path in find_compile_assets(output_dir, excluded_dir):
        try:
            stat = os.stat(path)
        except OSError:
            continue
        snapshot[path] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def find_changed_compile_assets(
    output_dir: str,
    excluded_dir: str,
    baseline: dict[str, tuple[int, int]],
) -> list[str]:
    """Return descriptors created or rewritten since *baseline* was captured."""
    changed = []
    for path in find_compile_assets(output_dir, excluded_dir):
        try:
            stat = os.stat(path)
        except OSError:
            continue
        if baseline.get(path) != (stat.st_mtime_ns, stat.st_size):
            changed.append(path)
    return changed


def _is_within(path: str, parent: str) -> bool:
    normalized = os.path.normcase(os.path.abspath(path))
    normalized_parent = os.path.normcase(os.path.abspath(parent))
    try:
        return os.path.commonpath([normalized, normalized_parent]) == normalized_parent
    except ValueError:
        return False


class CompileAssetsWorker(CancellableWorker):
    """Run Source 2 ResourceCompiler over all ported asset descriptors."""

    log = Signal(str, str)
    done = Signal(bool)

    def __init__(
        self,
        cs2_path: str,
        output_dir: str,
        excluded_dir: str = "",
        baseline: dict[str, tuple[int, int]] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.cs2_path = cs2_path
        self.output_dir = output_dir
        self.excluded_dir = excluded_dir
        self.baseline = baseline or {}
        self._process = None

    def cancel(self):
        super().cancel()
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def run(self):
        file_list_path = ""
        try:
            resource_compiler = os.path.join(
                self.cs2_path, "game", "bin", "win64", "resourcecompiler.exe"
            )
            if not os.path.isfile(resource_compiler):
                self.log.emit(f"ResourceCompiler not found: {resource_compiler}", "error")
                self.done.emit(False)
                return

            assets = find_changed_compile_assets(
                self.output_dir, self.excluded_dir, self.baseline
            )
            if not assets:
                self.log.emit("No new or changed asset descriptors found to compile.", "info")
                self.done.emit(True)
                return

            self.log.emit(f"Compiling {len(assets)} converted asset(s).", "info")
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".txt", delete=False
            ) as file_list:
                file_list.write("\n".join(assets))
                file_list.write("\n")
                file_list_path = file_list.name

            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self._process = subprocess.Popen(
                [
                    resource_compiler,
                    "-retail",
                    "-nop4",
                    "-game",
                    "csgo",
                    "-f",
                    "-filelist",
                    file_list_path,
                ],
                cwd=self.output_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
            )
            if self._process.stdout is not None:
                for line in self._process.stdout:
                    message = line.rstrip()
                    if message:
                        self.log.emit(message, "info")
                    if self.is_cancelled:
                        self._process.terminate()
                        break

            return_code = self._process.wait()
            if self.is_cancelled:
                self.log.emit("Asset compilation cancelled.", "warn")
                self.done.emit(False)
                return
            if return_code != 0:
                self.log.emit(f"ResourceCompiler exited with code {return_code}.", "error")
                self.done.emit(False)
                return

            self.log.emit("Asset compilation finished.", "success")
            self.done.emit(True)
        except Exception as error:
            self.log.emit(f"Asset compilation failed: {error}", "error")
            self.done.emit(False)
        finally:
            self._process = None
            if file_list_path:
                try:
                    os.unlink(file_list_path)
                except OSError:
                    pass
