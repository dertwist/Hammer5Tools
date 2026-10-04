"""P0 characterization fixtures; known gaps are retained until their package.

Run with pytest -q -s to reproduce UTF-8 logical and complete wire sizes.
Compiler output and map projections are deterministic fakes, not Valve smoke tests.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
from time import perf_counter
from unittest.mock import Mock

import pytest

from automation.mcp.server import McpServer, _write_response, run_stdio
from automation.operations import compiler
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

    def read_valve_map_asset_references(self, path: str) -> tuple[str, ...]:
        assert path == MAP_PATH
        return REFERENCES


def _call(server: McpServer, name: str, arguments: dict) -> dict:
    return server.handle({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": f"hammer5tools.{name}", "arguments": arguments},
    })


def _utf8_size(value: dict) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


@pytest.fixture
def compiler_files(tmp_path):
    root = tmp_path / "CS2 with spaces"
    executable = root / "game/bin/win64/resourcecompiler.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    assets = []
    for name in ("成功", "失敗", "timeout"):
        path = tmp_path / f"{name} asset.vmdl"
        path.write_text("fixture", encoding="utf-8")
        assets.append(str(path))
    return str(root), assets


@pytest.mark.parametrize("force", [False, True])
def test_compile_forwards_force_timeout_and_absolute_unicode_path(compiler_files, monkeypatch, force):
    root, assets = compiler_files
    runner = Mock(return_value=subprocess.CompletedProcess([], 0, STDOUT, ""))
    monkeypatch.setattr(compiler.subprocess, "run", runner)

    response = _call(McpServer(FeedbackBridge()), "compile_asset", {
        "path": assets[0], "cs2_path": root, "force": force, "timeout_seconds": 7,
    })

    command = [os.path.join(root, "game", "bin", "win64", "resourcecompiler.exe"), "-i", os.path.abspath(assets[0])]
    if force:
        command.append("-f")
    runner.assert_called_once_with(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, timeout=7, check=False)
    result = response["result"]
    payload = result["structuredContent"]
    assert payload["success"] is True and payload["exit_code"] == 0
    assert payload["stdout"] == STDOUT
    assert payload["warnings"] == ["Warning: missing dependency"]
    assert json.loads(result["content"][0]["text"]) == payload
    assert result["isError"] is False


@pytest.mark.parametrize("streams", [("partial", "error"), (b"partial", b"error"), (None, None)])
def test_timeout_preserves_current_stream_types(compiler_files, monkeypatch, streams):
    root, assets = compiler_files
    runner = Mock(side_effect=subprocess.TimeoutExpired("fake compiler", 7, output=streams[0], stderr=streams[1]))
    monkeypatch.setattr(compiler.subprocess, "run", runner)

    result = compiler.compile_asset(assets[2], cs2_path=root, timeout_seconds=7)

    assert result["success"] is False and result["exit_code"] == -1
    assert result["stdout"] == (streams[0] or "")
    assert result["stderr"] == (streams[1] or "")
    assert "7 seconds" in result["error"]
    runner.assert_called_once()


def test_timeout_bytes_currently_produce_rpc_error_but_ping_survives(compiler_files, monkeypatch):
    root, assets = compiler_files
    monkeypatch.setattr(compiler.subprocess, "run", Mock(side_effect=subprocess.TimeoutExpired(
        "fake compiler", 7, output="部分".encode("utf-8"), stderr=b"error",
    )))
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "hammer5tools.compile_asset", "arguments": {
                "path": assets[2], "cs2_path": root, "timeout_seconds": 7,
            },
        }},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    ]
    output = io.StringIO()
    run_stdio(io.StringIO("".join(json.dumps(item) + "\n" for item in requests)), output,
              server=McpServer(FeedbackBridge()))
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    # P2 must replace this characterization with safely decoded stream results.
    assert replies[0]["error"]["code"] == -32602
    assert "bytes" in replies[0]["error"]["message"]
    assert replies[1] == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_mixed_asset_fixture_requires_one_call_and_process_per_asset(compiler_files, monkeypatch):
    root, assets = compiler_files
    runner = Mock(side_effect=[
        subprocess.CompletedProcess([], 0, STDOUT, ""),
        subprocess.CompletedProcess([], 1, STDOUT, STDERR),
        subprocess.TimeoutExpired("fake compiler", 7, output="partial"),
    ])
    monkeypatch.setattr(compiler.subprocess, "run", runner)
    server = McpServer(FeedbackBridge())
    replies = [_call(server, "compile_asset", {"path": path, "cs2_path": root}) for path in assets]
    payloads = [reply["result"]["structuredContent"] for reply in replies]

    assert [item["success"] for item in payloads] == [True, False, False]
    assert [item["exit_code"] for item in payloads] == [0, 1, -1]
    assert payloads[1]["errors"] == [STDERR.strip()]
    # Current transport isError does not encode compilation success.
    assert all(reply["result"]["isError"] is False for reply in replies)
    assert runner.call_count == len(assets) == 3


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
    server = McpServer(FeedbackBridge())
    runner = Mock(return_value=subprocess.CompletedProcess([], 1 if case == "compile_failure" else 0,
                                                         STDOUT, STDERR if case == "compile_failure" else ""))
    monkeypatch.setattr(compiler.subprocess, "run", runner)
    monkeypatch.setattr(compiler.os.path, "isfile", lambda _path: True)
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
        assert payload["references"] == list(REFERENCES)
        assert "truncated" not in payload and "total" not in payload
    if case.startswith("compile_"):
        assert payload["stdout"] == STDOUT
        assert _utf8_size(payload) > 16 * 1024, "P2 fixture must expose the current unbounded logs"
    assert _utf8_size(response) > _utf8_size(payload)
    output = io.StringIO()
    _write_response(output, response)
    wire = output.getvalue().encode("utf-8")
    assert wire.endswith(b"\n") and json.loads(wire) == response
    assert len(wire) == _utf8_size(response) + 1
    print(json.dumps({"case": case, "logical_utf8_bytes": _utf8_size(payload),
                      "wire_utf8_bytes": len(wire), "tool_calls": 0 if case == "tools_list" else 1,
                      "fake_process_calls": runner.call_count, "handler_ms": round(elapsed * 1000, 3)}))
