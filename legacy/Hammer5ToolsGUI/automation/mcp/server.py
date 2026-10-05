"""Dependency-free MCP stdio server for Hammer5Tools."""

from __future__ import annotations

import importlib.resources
import json
import sys
from collections.abc import Mapping
from typing import Any, TextIO

from automation.tools import TOOLS, invoke_tool
from core.bridge import CoreBridge
from core.version import APP_VERSION


PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = frozenset({"2024-11-05", "2025-03-26", "2025-06-18", PROTOCOL_VERSION})


def _instructions() -> str:
    try:
        return importlib.resources.files("automation.mcp").joinpath("instructions.md").read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return "Use Hammer5Tools for Source 2 and Unreal inspection. Preview future write operations before applying them."


class McpServer:
    """Handles the MCP request subset exposed by Hammer5Tools."""

    def __init__(self, bridge: CoreBridge | None = None) -> None:
        self._bridge = bridge

    def handle(self, message: Mapping[str, Any]) -> dict[str, Any] | None:
        """Handle one decoded JSON-RPC message."""
        request_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str):
            return _error(request_id, -32600, "Invalid Request") if request_id is not None else None

        if request_id is None:
            return None

        try:
            if method == "initialize":
                params = _mapping(message.get("params"))
                requested = params.get("protocolVersion")
                protocol_version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION
                return _success(request_id, {
                    "protocolVersion": protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "Hammer5Tools", "version": APP_VERSION},
                    "instructions": _instructions(),
                })
            if method == "ping":
                return _success(request_id, {})
            if method == "tools/list":
                return _success(request_id, {"tools": [tool.mcp_definition() for tool in TOOLS]})
            if method == "tools/call":
                params = _mapping(message.get("params"))
                name = params.get("name")
                if not isinstance(name, str):
                    return _error(request_id, -32602, "Tool name must be a string")
                arguments = _mapping(params.get("arguments", {}))
                try:
                    structured = invoke_tool(name, arguments, bridge=self._bridge)
                except KeyError as error:
                    return _error(request_id, -32602, str(error))
                except Exception as error:
                    return _success(request_id, {
                        "content": [{"type": "text", "text": str(error)}],
                        "isError": True,
                    })
                text = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
                return _success(request_id, {
                    "content": [{"type": "text", "text": text}],
                    "structuredContent": structured,
                    "isError": False,
                })
            return _error(request_id, -32601, f"Method not found: {method}")
        except (TypeError, ValueError) as error:
            return _error(request_id, -32602, str(error))


def run_stdio(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    *,
    server: McpServer | None = None,
) -> int:
    """Run newline-delimited JSON-RPC over standard input and output."""
    source = input_stream or sys.stdin
    target = output_stream or sys.stdout
    if source is None or target is None:
        raise RuntimeError("MCP stdio requires an attached console input and output")

    active_server = server or McpServer()
    for line in source:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("The JSON-RPC message must be an object")
            response = active_server.handle(message)
        except (json.JSONDecodeError, ValueError) as error:
            response = _error(None, -32700, f"Parse error: {error}")
        if response is None:
            continue
        _write_response(target, response)
    return 0


def _write_response(target: TextIO, response: Mapping[str, Any]) -> None:
    """Write one response, degrading rather than ending the session.

    A single unserializable result or an encoding failure must not break the
    loop, because a client that loses the connection marks the server dead for
    the rest of its session.
    """
    try:
        payload = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        payload = json.dumps(_error(response.get("id"), -32603, f"Result is not serializable: {error}"))
    try:
        target.write(payload + "\n")
    except UnicodeEncodeError:
        target.write(payload.encode("ascii", "backslashreplace").decode("ascii") + "\n")
    target.flush()


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("Request parameters must be an object")
    return value


def _success(request_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": dict(result)}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
