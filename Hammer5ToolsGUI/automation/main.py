"""Headless command dispatcher used by Hammer5ToolsGUI.exe."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from automation.mcp.server import run_stdio
from automation.tools import capabilities, invoke_tool


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested headless Hammer5Tools mode."""
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
    subparsers.add_parser("capabilities", help="List implemented automation tools")
    subparsers.add_parser("core-status", help="Probe the NativeAOT Core")

    vmap = subparsers.add_parser("vmap-references", help="Read references from an uncompiled VMAP")
    vmap.add_argument("path")

    unreal_info = subparsers.add_parser("unreal-info", help="Inspect an Unreal Content directory")
    unreal_info.add_argument("content_dir")

    unreal_list = subparsers.add_parser("unreal-list", help="List Unreal packages")
    unreal_list.add_argument("content_dir")
    unreal_list.add_argument("--substring", default="")

    unreal_refs = subparsers.add_parser("unreal-references", help="Read references from an Unreal package")
    unreal_refs.add_argument("content_dir")
    unreal_refs.add_argument("object_path")

    args = parser.parse_args(list(argv))
    try:
        if args.command == "capabilities":
            result = capabilities()
        elif args.command == "core-status":
            result = invoke_tool("hammer5tools.core_status")
        elif args.command == "vmap-references":
            result = invoke_tool("hammer5tools.vmap_references", {"path": args.path})
        elif args.command == "unreal-info":
            result = invoke_tool("hammer5tools.unreal_info", {"content_dir": args.content_dir})
        elif args.command == "unreal-list":
            result = invoke_tool("hammer5tools.unreal_list", {
                "content_dir": args.content_dir,
                "substring": args.substring,
            })
        else:
            result = invoke_tool("hammer5tools.unreal_references", {
                "content_dir": args.content_dir,
                "object_path": args.object_path,
            })
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
