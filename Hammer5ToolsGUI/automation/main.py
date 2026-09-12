"""Headless command dispatcher used by Hammer5ToolsGUI.exe."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from automation.mcp.server import run_stdio
from automation.tools import capabilities, invoke_tool


def _force_utf8_streams() -> None:
    """Make the standard streams UTF-8 before any response is written.

    Frozen PyInstaller builds run isolated and ignore PYTHONUTF8 and
    PYTHONIOENCODING, so a spawned Hammer5ToolsGUI.exe gets the Windows ANSI
    codepage on stdout. Both transports serialize with ensure_ascii=False, so
    one asset containing non-ASCII text would raise UnicodeEncodeError and kill
    the process, which makes an MCP client treat the server as dead.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested headless Hammer5Tools mode."""
    _force_utf8_streams()
    arguments = list(argv if argv is not None else sys.argv[1:])
    if arguments[:2] == ["mcp", "serve"]:
        return run_stdio()
    if not arguments or arguments[0] != "cli":
        _write_error("Expected 'cli <command>' or 'mcp serve'")
        return 2
    return _run_cli(arguments[1:])


def _run_cli(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="Hammer5ToolsGUI.exe cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # General
    subparsers.add_parser("capabilities", help="List implemented automation tools")
    subparsers.add_parser("core-status", help="Probe the NativeAOT Core")

    # Generic tool invoker
    call_tool = subparsers.add_parser("call", help="Invoke any registered automation tool by name")
    call_tool.add_argument("tool_name", help="Full tool name (e.g. hammer5tools.vmat_read)")
    call_tool.add_argument("--args", default="{}", help="JSON arguments string")

    # VMAP & Unreal
    vmap = subparsers.add_parser("vmap-references", help="Read references from an uncompiled VMAP")
    vmap.add_argument("path")

    vmap_rewrite = subparsers.add_parser("vmap-rewrite", help="Rewrite asset paths in an uncompiled VMAP")
    vmap_rewrite.add_argument("vmap_path")
    vmap_rewrite.add_argument("replacements", help="JSON dictionary of from: to path replacements")
    vmap_rewrite.add_argument("--dry-run", action="store_true")

    unreal_info = subparsers.add_parser("unreal-info", help="Inspect an Unreal Content directory")
    unreal_info.add_argument("content_dir")

    unreal_list = subparsers.add_parser("unreal-list", help="List Unreal packages")
    unreal_list.add_argument("content_dir")
    unreal_list.add_argument("--substring", default="")

    unreal_refs = subparsers.add_parser("unreal-references", help="Read references from an Unreal package")
    unreal_refs.add_argument("content_dir")
    unreal_refs.add_argument("object_path")

    # Format Readers
    vmdl_r = subparsers.add_parser("vmdl-read", help="Read and inspect a .vmdl file")
    vmdl_r.add_argument("path")

    vmat_r = subparsers.add_parser("vmat-read", help="Read and inspect a .vmat file")
    vmat_r.add_argument("path")

    vtex_r = subparsers.add_parser("vtex-read", help="Read and inspect a .vtex file")
    vtex_r.add_argument("path")

    vsmart_r = subparsers.add_parser("vsmart-read", help="Read and inspect a .vsmart file")
    vsmart_r.add_argument("path")

    vsmart_eval = subparsers.add_parser("vsmart-eval", help="Evaluate a .vsmart file through Core")
    vsmart_eval.add_argument("path")

    vdata_r = subparsers.add_parser("vdata-read", help="Read and inspect a .vdata file")
    vdata_r.add_argument("path")

    vsnap_r = subparsers.add_parser("vsnap-read", help="Read and inspect a .vsnap file")
    vsnap_r.add_argument("path")

    # Operations
    compile_cmd = subparsers.add_parser("compile", help="Compile an uncompiled asset via resourcecompiler")
    compile_cmd.add_argument("path")
    compile_cmd.add_argument("--force", action="store_true")

    validate = subparsers.add_parser("validate", help="Validate addon assets")
    validate.add_argument("--addon", default=None)
    validate.add_argument("--cs2-dir", default=None)

    unused = subparsers.add_parser("find-unused", help="Find unused assets relative to a map")
    unused.add_argument("map_path")
    unused.add_argument("--addon-dir", default=None)

    deps = subparsers.add_parser("resolve-deps", help="Recursively resolve all dependencies of an asset")
    deps.add_argument("path")

    vpk_s = subparsers.add_parser("vpk-search", help="Search official game VPK archives")
    vpk_s.add_argument("query")
    vpk_s.add_argument("--ext", default=None)

    args = parser.parse_args(list(argv))
    try:
        if args.command == "capabilities":
            result = capabilities()
        elif args.command == "core-status":
            result = invoke_tool("hammer5tools.core_status")
        elif args.command == "call":
            parsed_args = json.loads(args.args)
            result = invoke_tool(args.tool_name, parsed_args)
        elif args.command == "vmap-references":
            result = invoke_tool("hammer5tools.vmap_references", {"path": args.path})
        elif args.command == "vmap-rewrite":
            rep_dict = json.loads(args.replacements)
            result = invoke_tool("hammer5tools.vmap_rewrite_references", {
                "vmap_path": args.vmap_path,
                "replacements": rep_dict,
                "dry_run": args.dry_run,
            })
        elif args.command == "unreal-info":
            result = invoke_tool("hammer5tools.unreal_info", {"content_dir": args.content_dir})
        elif args.command == "unreal-list":
            result = invoke_tool("hammer5tools.unreal_list", {
                "content_dir": args.content_dir,
                "substring": args.substring,
            })
        elif args.command == "unreal-references":
            result = invoke_tool("hammer5tools.unreal_references", {
                "content_dir": args.content_dir,
                "object_path": args.object_path,
            })
        elif args.command == "vmdl-read":
            result = invoke_tool("hammer5tools.vmdl_read", {"path": args.path})
        elif args.command == "vmat-read":
            result = invoke_tool("hammer5tools.vmat_read", {"path": args.path})
        elif args.command == "vtex-read":
            result = invoke_tool("hammer5tools.vtex_read", {"path": args.path})
        elif args.command == "vsmart-read":
            result = invoke_tool("hammer5tools.vsmart_read", {"path": args.path})
        elif args.command == "vsmart-eval":
            result = invoke_tool("hammer5tools.vsmart_evaluate", {"path": args.path})
        elif args.command == "vdata-read":
            result = invoke_tool("hammer5tools.vdata_read", {"path": args.path})
        elif args.command == "vsnap-read":
            result = invoke_tool("hammer5tools.vsnap_read", {"path": args.path})
        elif args.command == "compile":
            result = invoke_tool("hammer5tools.compile_asset", {"path": args.path, "force": args.force})
        elif args.command == "validate":
            result = invoke_tool("hammer5tools.validate_addon", {
                "addon_name": args.addon,
                "cs2_dir": args.cs2_dir,
            })
        elif args.command == "find-unused":
            result = invoke_tool("hammer5tools.find_unused_assets", {
                "map_path": args.map_path,
                "addon_dir": args.addon_dir,
            })
        elif args.command == "resolve-deps":
            result = invoke_tool("hammer5tools.resolve_dependencies", {"path": args.path})
        elif args.command == "vpk-search":
            result = invoke_tool("hammer5tools.vpk_search", {"query": args.query, "extension": args.ext})
        else:
            _write_error(f"Unknown command: {args.command}")
            return 1
    except Exception as error:
        _write_error(str(error))
        return 1
    _write_json(result)
    return 0


def _write_json(value: Any) -> None:
    if sys.stdout is None:
        raise RuntimeError("CLI output requires an attached console")
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.flush()


def _write_error(message: str) -> None:
    if sys.stderr is not None:
        sys.stderr.write(f"Hammer5Tools: {message}\n")
        sys.stderr.flush()
