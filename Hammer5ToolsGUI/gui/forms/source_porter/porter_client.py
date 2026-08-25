"""
Python client & thread runner for SourcePorter.
Drives the map-porting/asset-repair pipeline through the Hammer5Tools.Core
NativeAOT ABI (``CoreBridge.source_porter_*``) — no pythonnet, no CLR.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import QThread, Signal, QObject


class SourcePorterClient:
    """Wrapper verifying the Hammer5Tools Core ABI is available."""

    def __init__(self, cli_path: Optional[str] = None, dotnet_path: Optional[str] = None):
        pass

    def is_available(self) -> bool:
        from hammer5tools_core.bridge import CoreBridge

        return CoreBridge.instance().probe().available

    def why_unavailable(self) -> str:
        from hammer5tools_core.bridge import CoreBridge

        status = CoreBridge.instance().probe()
        return "" if status.available else (status.diagnostic or "Hammer5Tools Core is unavailable.")


class PorterThread(QThread):
    """QThread worker running SourcePorter through the native Core ABI."""

    log_signal = Signal(str)
    finished_signal = Signal(int)  # return code (0 = success, 1 = success with issues, negative = error/cancelled)

    def __init__(self, client: SourcePorterClient, sub_cmd: str, cmd_args: List[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.client = client
        self.sub_cmd = sub_cmd
        self.cmd_args = cmd_args
        self._cancellation = None

    def cancel(self):
        if self._cancellation is not None:
            try:
                self._cancellation.cancel()
            except Exception:
                pass

    def run(self):
        if not self.client.is_available():
            self.log_signal.emit(f"[SourcePorter Error] {self.client.why_unavailable()}")
            self.finished_signal.emit(1)
            return

        try:
            code = self._run_native()
        except Exception as ex:
            self.log_signal.emit(f"[SourcePorter Error] {ex}")
            code = 1
        finally:
            if self._cancellation is not None:
                self._cancellation.close()
                self._cancellation = None

        self.finished_signal.emit(code)

    def _run_native(self) -> int:
        from hammer5tools_core.bridge import CoreBridge

        bridge = CoreBridge.instance()
        self._cancellation = bridge.create_smartprop_cancellation()

        def on_log(line: str) -> None:
            self.log_signal.emit(line)

        if self.sub_cmd == "validate":
            cs2_dir, addon = self.cmd_args[0], self.cmd_args[1]
            return bridge.source_porter_validate(
                cs2_dir, addon, log=on_log, cancellation=self._cancellation)

        elif self.sub_cmd == "force-import":
            cs2_dir = self.cmd_args[0]
            addon = self.cmd_args[1]
            paths_and_flags = self.cmd_args[2:]
            no_compile_assets = "--no-compile-assets" in paths_and_flags
            asset_paths = [p for p in paths_and_flags if not p.startswith("--")]
            return bridge.source_porter_force_import(
                cs2_dir, addon, asset_paths,
                no_compile_assets=no_compile_assets, log=on_log, cancellation=self._cancellation)

        elif self.sub_cmd == "repair":
            cs2_dir, addon = self.cmd_args[0], self.cmd_args[1]
            return bridge.source_porter_repair(
                cs2_dir, addon, log=on_log, cancellation=self._cancellation)

        elif self.sub_cmd == "port":
            cs2_dir = self.cmd_args[0]
            source_map = self.cmd_args[1]
            addon = self.cmd_args[2]
            flags = set(self.cmd_args[3:])

            threads = 1
            if "--threads" in self.cmd_args:
                idx = self.cmd_args.index("--threads")
                if idx + 1 < len(self.cmd_args):
                    try:
                        threads = int(self.cmd_args[idx + 1])
                    except ValueError:
                        pass

            return bridge.source_porter_port(
                cs2_dir, source_map, addon,
                bspsrc_location=self._find_bspsrc(),
                threads=threads,
                no_bsp="--no-bsp" in flags,
                no_merge="--no-merge" in flags,
                no_deps="--nodeps" in flags or "--no-deps" in flags,
                no_unpack="--no-unpack" in flags,
                compile_map="--compile" in flags,
                no_compile_assets="--no-compile-assets" in flags,
                collapse_prefabs="--collapse-prefabs" in flags,
                repair="--repair" in flags,
                use_filelist="--use-filelist" in flags,
                compact="--verbose" not in flags,
                log=on_log, cancellation=self._cancellation)

        else:
            self.log_signal.emit(f"[SourcePorter Error] Unknown subcommand: {self.sub_cmd}")
            return 1

    @staticmethod
    def _find_bspsrc() -> Optional[str]:
        """Locates bspsrc.exe alongside the packaged app or in the dev tree.
        None means "not found" — the native side treats that the same way the
        old CLI did when bspsrc wasn't bundled."""
        from hammer5tools_core.runtime_paths import resolve_runtime_paths

        gui_root = Path(__file__).resolve().parents[2]
        candidates = [
            gui_root / "tools" / "bspsrc" / "bspsrc.exe",
            resolve_runtime_paths().runtime_resource("tools", "bspsrc", "bspsrc.exe"),
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return None
