"""P0 characterization fixtures; known gaps are retained until their package.

Run with pytest -q -s to reproduce UTF-8 logical and complete wire sizes.
Compiler output and map projections are deterministic fakes, not Valve smoke tests.
"""

from __future__ import annotations

import io
import json
from time import perf_counter

import pytest

from automation.mcp.server import McpServer, _write_response
from automation.tools import TOOLS_BY_NAME, invoke_tool
from test_automation_budget import _fixture, _response_size
from test_automation_vmap_io import _Bridge as MapBridge


MAP_PATH = "C:/addon/maps/基準.vmap"
ASSET_PATH = "C:/addon/models/基準.vmdl"
CS2_PATH = "C:/fake cs2"
REFERENCES = tuple(f"models/props/基準_{index:03d}.vmdl" for index in range(500))
STDOUT = "".join(f"Compiled 基準_{index:04d}.vmdl\n" for index in range(2000)) + "Warning: missing dependency\n"
STDERR = "Error: 模型 failed\n"


class FeedbackBridge(MapBridge):
    """Reuse the existing small entity/group/scene projection fixture."""

    def __init__(self, compiler_success: bool = True):
        self.compiler_success = compiler_success

    def read_valve_map_asset_references(self, path: str) -> tuple[str, ...]:
        assert path == MAP_PATH
        return REFERENCES


    def compile_assets(self, request: dict) -> dict:
        # Response-envelope fixture; actual diagnostics/process behavior is tested in Core.
        return {"path": request["path"], "success": self.compiler_success, "exit_code": 0 if self.compiler_success else 1,
                "duration_seconds": 0.01, "warnings": ["Warning: missing dependency"],
                "warning_count": 1, "errors": [], "error_count": 0, "tail": [],
                "log_id": "00000000000000000000000000000001", "unknown_count": 1}


def _call(server: McpServer, name: str, arguments: dict) -> dict:
    return server.handle({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": f"hammer5tools.{name}", "arguments": arguments},
    })


def _utf8_size(value: dict) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def test_compilation_request_forwards_force_timeout_and_absolute_path():
    from unittest.mock import Mock
    bridge = Mock()
    bridge.compile_assets.return_value = {"success": False, "exit_code": -1, "error": "Compilation timed out"}
    response = _call(McpServer(bridge), "compile_asset", {
        "path": ASSET_PATH, "cs2_path": CS2_PATH, "force": True, "timeout_seconds": 7,
    })
    request = bridge.compile_assets.call_args.args[0]
    assert request["path"] == ASSET_PATH and request["force"] is True and request["timeout_seconds"] == 7
    result = response["result"]
    assert result["structuredContent"]["success"] is False
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
    assert result["isError"] is False


@pytest.mark.parametrize("fmt", ["vsmart", "vmdl", "vmat", "vtex", "vdata"])
def test_registered_readers_default_to_existing_summary(fmt, tmp_path):
    path = _fixture(fmt, tmp_path)
    name = f"hammer5tools.{fmt}_read"
    default = invoke_tool(name, {"path": path}, bridge=FeedbackBridge())
    explicit = invoke_tool(name, {"path": path, "detail": "summary"}, bridge=FeedbackBridge())
    assert default == explicit
    assert "raw" not in default


def test_map_fixture_keeps_summary_entities_and_groups_reachable(tmp_path):
    path = str(tmp_path / "基準 map.vmap")
    # This is a projected Core fixture, not a parseable DMX file.
    with open(path, "wb") as stream:
        stream.write(b"fake Core projection input")
    server = McpServer(FeedbackBridge())
    summary = _call(server, "vmap_read", {"path": path})["result"]["structuredContent"]
    entities = _call(server, "vmap_read", {"path": path, "detail": "full"})["result"]["structuredContent"]
    groups = _call(server, "vmap_read", {"path": path, "structures": "groups"})["result"]["structuredContent"]
    assert summary["entity_count"] == 3 and summary["node_classes"]["CMapGroup"] == 1
    assert "entities" not in summary and "nodes" not in summary
    assert len(entities["entities"]) == 3
    assert groups["total"] == 1 and groups["items"][0]["class"] == "CMapGroup"


def test_compile_schema_exposes_existing_force_and_timeout():
    schema = TOOLS_BY_NAME["hammer5tools.compile_asset"].mcp_definition()["inputSchema"]
    assert schema["properties"]["force"]["type"] == "boolean"
    assert schema["properties"]["timeout_seconds"]["type"] == "integer"
    assert schema["required"] == ["path"]


def test_budget_helper_counts_utf8_bytes():
    payload = {"path": "模型/基準.vmdl"}
    assert _response_size(payload) == _utf8_size(payload)


@pytest.mark.parametrize("case", ["references", "compile_success", "compile_failure", "map_summary", "tools_list"])
def test_baseline_sizes(case, monkeypatch):
    from automation.formats import vmap_io
    monkeypatch.setattr(vmap_io, "_require", lambda path: path)
    server = McpServer(FeedbackBridge(case != "compile_failure"))
    started = perf_counter()
    if case == "tools_list":
        response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        payload = response["result"]
    else:
        name = "compile_asset" if case.startswith("compile_") else "vmap_references" if case == "references" else "vmap_read"
        arguments = {"path": ASSET_PATH, "cs2_path": CS2_PATH} if name == "compile_asset" else {"path": MAP_PATH}
        response = _call(server, name, arguments)
        payload = response["result"]["structuredContent"]
        assert json.loads(response["result"]["content"][0]["text"]) == payload
    elapsed = perf_counter() - started
    if case == "references":
        assert payload["references"] == list(REFERENCES[:50])
        assert payload["truncated"] is True and payload["total"] == 500
    if case.startswith("compile_"):
        assert payload["log_id"]
        assert _utf8_size(payload) < 8 * 1024
    assert _utf8_size(response) > _utf8_size(payload)
    output = io.StringIO()
    _write_response(output, response)
    wire = output.getvalue().encode("utf-8")
    assert wire.endswith(b"\n") and json.loads(wire) == response
    assert len(wire) == _utf8_size(response) + 1
    print(json.dumps({"case": case, "logical_utf8_bytes": _utf8_size(payload),
                      "wire_utf8_bytes": len(wire), "tool_calls": 0 if case == "tools_list" else 1,
                      "fake_process_calls": 1 if case.startswith("compile_") else 0, "handler_ms": round(elapsed * 1000, 3)}))
