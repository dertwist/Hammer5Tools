import io
import json

from automation.mcp.server import McpServer, run_stdio
from automation.tools import TOOLS, capabilities, invoke_tool
from core.bridge import CoreStatus


class _Bridge:
    def probe(self):
        return CoreStatus(True, version="native-abi-2")

    def read_valve_map_asset_references(self, path):
        assert path == "C:/addon/maps/example.vmap"
        return ("materials/example.vmat", "models/example.vmdl")

    def unreal_info(self, content_dir):
        return {"contentDir": content_dir, "uassets": 3}

    def unreal_list(self, content_dir, substring):
        return [f"{content_dir}/{substring}.uasset"]

    def unreal_iter_refs(self, content_dir, object_path):
        return [f"{content_dir}:{object_path}:reference"]


def test_capabilities_advertises_tools_and_write_support():
    result = capabilities(_Bridge())

    assert result["core"]["available"] is True
    assert result["tools"] == [tool.name for tool in TOOLS]
    assert result["write_tools"] is True
    assert "hammer5tools.vmdl_read" in result["tools"]
    assert "hammer5tools.vmat_write" in result["tools"]


def test_vmap_reference_tool_uses_core_bridge():
    result = invoke_tool(
        "hammer5tools.vmap_references",
        {"path": "C:/addon/maps/example.vmap"},
        bridge=_Bridge(),
    )

    assert result["references"] == ["materials/example.vmat", "models/example.vmdl"]


def test_initialize_returns_instructions_and_tool_capability():
    response = McpServer(_Bridge()).handle({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {}},
    })

    assert response["result"]["protocolVersion"] == "2025-11-25"
    assert response["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert "preview" in response["result"]["instructions"].lower()


def test_tool_call_returns_text_and_structured_content():
    response = McpServer(_Bridge()).handle({
        "jsonrpc": "2.0",
        "id": "call-1",
        "method": "tools/call",
        "params": {
            "name": "hammer5tools.unreal_info",
            "arguments": {"content_dir": "C:/Unreal/Content"},
        },
    })

    result = response["result"]
    assert result["structuredContent"]["uassets"] == 3
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
    assert result["isError"] is False


def test_stdio_uses_newline_delimited_json_and_ignores_notifications():
    source = io.StringIO(
        '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
        '{"jsonrpc":"2.0","id":2,"method":"ping"}\n'
    )
    target = io.StringIO()

    assert run_stdio(source, target, server=McpServer(_Bridge())) == 0
    lines = target.getvalue().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_tools_have_accurate_read_write_annotations():
    response = McpServer(_Bridge()).handle({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/list",
        "params": {},
    })

    tools = {t["name"]: t for t in response["result"]["tools"]}

    # Read tools
    assert tools["hammer5tools.vmdl_read"]["annotations"]["readOnlyHint"] is True
    assert tools["hammer5tools.vmat_read"]["annotations"]["readOnlyHint"] is True
    assert tools["hammer5tools.vsmart_read"]["annotations"]["readOnlyHint"] is True

    # Write tools
    assert tools["hammer5tools.vmdl_write"]["annotations"]["readOnlyHint"] is False
    assert tools["hammer5tools.vmat_write"]["annotations"]["readOnlyHint"] is False
    assert tools["hammer5tools.vsmart_write"]["annotations"]["readOnlyHint"] is False
    assert tools["hammer5tools.vsnap_write"]["annotations"]["readOnlyHint"] is False
