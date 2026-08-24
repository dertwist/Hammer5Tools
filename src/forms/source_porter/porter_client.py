"""
Python client & thread runner for SourcePorter.
Direct .NET library invocation via `pythonnet` using `SourcePorter.Core.dll`.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
from PySide6.QtCore import QThread, Signal, QObject


def is_pythonnet_available() -> bool:
    """Check if pythonnet and SourcePorter.Core.dll are available for direct CLR invocation."""
    try:
        from src.bridge import CoreBridge
        from src.dotnet import DotNetInterop

        if not CoreBridge.instance().probe().available:
            return False
        interop = DotNetInterop()
        sp_dll = interop.paths.source_porter_core
        return sp_dll.is_file()
    except Exception:
        return False


class SourcePorterClient:
    """Wrapper verifying SourcePorter availability via pythonnet."""

    def __init__(self, cli_path: Optional[str] = None, dotnet_path: Optional[str] = None):
        pass

    def is_available(self) -> bool:
        return is_pythonnet_available()

    def why_unavailable(self) -> str:
        from src.bridge import CoreBridge

        status = CoreBridge.instance().probe()
        if not status.available:
            return status.diagnostic or "Hammer5Tools Core is unavailable."
        if not is_pythonnet_available():
            return "SourcePorter.Core.dll assembly not found. Build src/net_core/SourcePorter.Core."
        return ""


class PorterThread(QThread):
    """QThread worker running SourcePorter via pythonnet direct CLR interop."""

    log_signal = Signal(str)
    finished_signal = Signal(int)  # return code (0 = success)

    def __init__(self, client: SourcePorterClient, sub_cmd: str, cmd_args: List[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.client = client
        self.sub_cmd = sub_cmd
        self.cmd_args = cmd_args
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if not is_pythonnet_available():
            self.log_signal.emit("[SourcePorter Error] SourcePorter.Core.dll is not available. Please build src/net_core/SourcePorter.Core.")
            self.finished_signal.emit(1)
            return

        try:
            code = self._run_pythonnet()
            self.finished_signal.emit(code)
        except Exception as ex:
            self.log_signal.emit(f"[SourcePorter Error] {ex}")
            self.finished_signal.emit(1)

    def _run_pythonnet(self) -> int:
        from src.dotnet import DotNetInterop
        interop = DotNetInterop()
        interop.setup_source_porter()

        import SourcePorter.Core.Domain as Domain
        import SourcePorter.Core.Validation as Validation
        import SourcePorter.Core.Toolchain as Toolchain
        import SourcePorter.Core.Vmap as Vmap
        from System import Action, String
        from System.Collections.Generic import List as CsList

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
            for issue in report.Issues:
                if self._is_cancelled:
                    break
                self.log_signal.emit(f"  [{issue.Kind}] {issue.Source} -> {issue.Detail}")
            return 1 if report.HasIssues else 0

        elif self.sub_cmd == "force-import":
            cs2_dir = self.cmd_args[0]
            addon = self.cmd_args[1]
            paths_and_flags = self.cmd_args[2:]
            no_compile_assets = "--no-compile-assets" in paths_and_flags
            asset_paths = [p for p in paths_and_flags if not p.startswith("--")]

            cs2 = Domain.Cs2Install(cs2_dir)
            runner = Toolchain.ProcessRunner()
            runner.OnOutput += Action[Toolchain.ProcessLine](lambda line: on_log(line.Text))

            import_options = Domain.ImportOptions()
            import_options.CompileAssets = not no_compile_assets
            dummy_vmf = os.path.join(cs2.ContentAddonDir(addon), "maps", "import.vmf")
            project = cs2.BuildProject(dummy_vmf, addon, import_options)

            import_scripts_dir = cs2.ImportScriptsDir if os.path.exists(cs2.ImportScriptsDir) else os.getcwd()
            service = Toolchain.MapImportService(cs2.Tools, runner, import_scripts_dir)
            service.OnLog += cs_log

            importer = Toolchain.MissingAssetImporter(service, cs2)
            importer.OnLog += cs_log

            cs_paths = CsList[String]()
            for p in asset_paths:
                cs_paths.Add(p)

            extra_roots = CsList[String]()
            staging_root = Toolchain.MapStaging.StagingRoot
            if os.path.isdir(staging_root):
                for entry in os.listdir(staging_root):
                    cand = os.path.join(staging_root, entry)
                    if os.path.isdir(cand):
                        extra_roots.Add(cand)
                        cand_sub = os.path.join(cand, entry)
                        if os.path.isdir(cand_sub):
                            extra_roots.Add(cand_sub)

            res = importer.ForceImportAsync(project, cs_paths, extraContentRoots=extra_roots).GetAwaiter().GetResult()
            on_log(f"=== FORCE IMPORT {addon}: imported {res.ModelsImported} model(s), {res.MaterialsImported} material(s) ===")
            return 0

        elif self.sub_cmd == "repair":
            cs2_dir = self.cmd_args[0]
            addon = self.cmd_args[1]

            cs2 = Domain.Cs2Install(cs2_dir)
            runner = Toolchain.ProcessRunner()
            runner.OnOutput += Action[Toolchain.ProcessLine](lambda line: on_log(line.Text))

            validator = Validation.AssetValidator(cs2, addon)
            report = validator.Validate(cs_log)

            if report.MissingImportCount > 0:
                import_scripts_dir = cs2.ImportScriptsDir if os.path.exists(cs2.ImportScriptsDir) else os.getcwd()
                service = Toolchain.MapImportService(cs2.Tools, runner, import_scripts_dir)
                service.OnLog += cs_log

                import_options = Domain.ImportOptions()
                dummy_vmf = os.path.join(cs2.ContentAddonDir(addon), "maps", "repair.vmf")
                project = cs2.BuildProject(dummy_vmf, addon, import_options)

                importer = Toolchain.MissingAssetImporter(service, cs2)
                importer.OnLog += cs_log

                extra_roots = CsList[String]()
                staging_root = Toolchain.MapStaging.StagingRoot
                if os.path.isdir(staging_root):
                    for entry in os.listdir(staging_root):
                        cand = os.path.join(staging_root, entry)
                        if os.path.isdir(cand):
                            extra_roots.Add(cand)
                            cand_sub = os.path.join(cand, entry)
                            if os.path.isdir(cand_sub):
                                extra_roots.Add(cand_sub)

                rr = importer.RepairAsync(project, report, extraContentRoots=extra_roots).GetAwaiter().GetResult()
                on_log(f"=== REPAIR {addon}: imported {rr.ModelsImported} model(s)/{rr.MaterialsImported} material(s) in {rr.Rounds} round(s) ===")
                report = rr.FinalReport

            for issue in report.Issues:
                if self._is_cancelled:
                    break
                self.log_signal.emit(f"  [{issue.Kind}] {issue.Source} -> {issue.Detail}")

            return 1 if report.HasIssues else 0

        elif self.sub_cmd == "port":
            cs2_dir = self.cmd_args[0]
            source_map = self.cmd_args[1]
            addon = self.cmd_args[2]
            flags = set(self.cmd_args[3:])

            no_bsp = "--no-bsp" in flags
            no_merge = "--no-merge" in flags
            no_deps = "--nodeps" in flags or "--no-deps" in flags
            no_unpack = "--no-unpack" in flags
            compile_map = "--compile" in flags
            no_compile_assets = "--no-compile-assets" in flags
            collapse = "--collapse-prefabs" in flags
            no_uv_fix = "--no-uv-fix" in flags
            repair = "--repair" in flags
            use_filelist = "--use-filelist" in flags
            compact = "--verbose" not in flags
            bsp_imported = False

            threads = 1
            if "--threads" in self.cmd_args:
                idx = self.cmd_args.index("--threads")
                if idx + 1 < len(self.cmd_args):
                    try:
                        threads = int(self.cmd_args[idx + 1])
                    except ValueError:
                        pass

            cs2 = Domain.Cs2Install(cs2_dir)
            runner = Toolchain.ProcessRunner()
            runner.OnOutput += Action[Toolchain.ProcessLine](lambda line: on_log(line.Text))

            # Locate bspsrc.exe
            root = Path(__file__).resolve().parents[3]
            from src.runtime_paths import resolve_runtime_paths
            runtime_paths = resolve_runtime_paths()
            bspsrc_candidates = [
                root / "tools" / "bspsrc" / "bspsrc.exe",
                runtime_paths.runtime_resource("tools", "bspsrc", "bspsrc.exe"),
            ]
            bspsrc_location = None
            for candidate in bspsrc_candidates:
                if candidate.is_file():
                    bspsrc_location = str(candidate)
                    break

            if source_map.lower().endswith(".bsp") and not no_bsp:
                decompiler = Toolchain.BspDecompiler(runner, bspsrc_location)
                decompiler.OnLog += cs_log
                vmf = Toolchain.MapStaging.StageBspAsync(decompiler, source_map, not no_unpack).GetAwaiter().GetResult()
                no_merge = True
                bsp_imported = True
            else:
                vmf = Toolchain.MapStaging.StageVmf(source_map, cs_log)

            import_options = Domain.ImportOptions()
            import_options.UseBsp = not no_bsp and not no_merge
            import_options.UseBspNoMergeInstances = no_merge and not no_bsp
            import_options.SkipDeps = no_deps
            import_options.MaxParallelism = threads
            import_options.CompileAssets = not no_compile_assets
            import_options.CompactLog = compact
            import_options.UseFilelist = use_filelist

            project = cs2.BuildProject(vmf, addon, import_options)
            import_scripts_dir = cs2.ImportScriptsDir if os.path.exists(cs2.ImportScriptsDir) else os.getcwd()
            service = Toolchain.MapImportService(cs2.Tools, runner, import_scripts_dir)
            service.OnLog += cs_log

            on_log(f"=== IMPORT {project.MapName} -> {addon} ===")
            service.ImportAsync(project).GetAwaiter().GetResult()

            if collapse:
                Vmap.PostImportVmapTools.CollapsePrefabs(cs2, addon, project.MapName, cs_log)
                Vmap.PostImportVmapTools.FlattenSingleChildGroups(cs2, addon, cs_log)

            if compile_map:
                on_log(f"=== COMPILE {project.MapName} ===")
                service.CompileMapAsync(project).GetAwaiter().GetResult()

            stats = Validation.AddonStats.Collect(cs2.ContentAddonDir(addon), os.path.join(cs2.GameDir, "csgo_addons", addon))
            for line in stats.Format():
                on_log(line)

            validator = Validation.AssetValidator(cs2, addon)
            report = validator.Validate(cs_log)

            if repair and report.MissingImportCount > 0:
                importer = Toolchain.MissingAssetImporter(service, cs2)
                importer.OnLog += cs_log
                rr = importer.RepairAsync(project, report).GetAwaiter().GetResult()
                on_log(f"=== REPAIR {addon}: imported {rr.ModelsImported} model(s)/{rr.MaterialsImported} material(s) in {rr.Rounds} round(s) ===")
                report = rr.FinalReport

            for issue in report.Issues:
                if self._is_cancelled:
                    break
                self.log_signal.emit(f"  [{issue.Kind}] {issue.Source} -> {issue.Detail}")

            return 1 if report.HasIssues else 0

        else:
            on_log(f"[SourcePorter Error] Unknown subcommand: {self.sub_cmd}")
            return 1
