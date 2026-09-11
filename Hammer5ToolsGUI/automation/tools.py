"""Tool definitions shared by the Hammer5Tools CLI and MCP server."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from core.bridge import CoreBridge
from core.version import APP_VERSION


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class AutomationTool:
    """One automation operation and its MCP metadata."""

    name: str
    description: str
    input_schema: JsonObject
    invoke: Callable[[CoreBridge, Mapping[str, Any]], JsonObject]

    def mcp_definition(self) -> JsonObject:
        """Return this tool's MCP tools/list representation."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": {
                "title": self.name.replace("hammer5tools.", "Hammer5Tools ").replace("_", " ").title(),
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        }


def _object_schema(properties: JsonObject, required: tuple[str, ...] = ()) -> JsonObject:
    schema: JsonObject = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = list(required)
    return schema


def _core_status(bridge: CoreBridge, _arguments: Mapping[str, Any]) -> JsonObject:
    return asdict(bridge.probe())


def _vmap_references(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    path = _required_string(arguments, "path")
    return {"path": path, "references": list(bridge.read_valve_map_asset_references(path))}


def _unreal_info(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return dict(bridge.unreal_info(_required_string(arguments, "content_dir")))


def _unreal_list(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    content_dir = _required_string(arguments, "content_dir")
    substring = _optional_string(arguments, "substring") or ""
    return {
        "content_dir": content_dir,
        "substring": substring,
        "assets": list(bridge.unreal_list(content_dir, substring)),
    }


def _unreal_references(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    content_dir = _required_string(arguments, "content_dir")
    object_path = _required_string(arguments, "object_path")
    return {
        "content_dir": content_dir,
        "object_path": object_path,
        "references": list(bridge.unreal_iter_refs(content_dir, object_path)),
    }


def _required_string(arguments: Mapping[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string")
    return value


def _optional_string(arguments: Mapping[str, Any], name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"'{name}' must be a string")
    return value


TOOLS = (
    AutomationTool(
        "hammer5tools.core_status",
        "Check whether the versioned Hammer5Tools NativeAOT Core can be loaded.",
        _object_schema({}),
        _core_status,
    ),
    AutomationTool(
        "hammer5tools.vmap_references",
        "Read content-relative asset references from an uncompiled VMAP without changing it.",
        _object_schema(
            {"path": {"type": "string", "description": "Absolute path to an uncompiled .vmap file."}},
            ("path",),
        ),
        _vmap_references,
    ),
    AutomationTool(
        "hammer5tools.unreal_info",
        "Inspect a loose Unreal Content directory and report mounted asset counts.",
        _object_schema(
            {"content_dir": {"type": "string", "description": "Absolute Unreal Content directory."}},
            ("content_dir",),
        ),
        _unreal_info,
    ),
    AutomationTool(
        "hammer5tools.unreal_list",
        "List Unreal package paths, optionally filtered by a case-insensitive substring.",
        _object_schema(
            {
                "content_dir": {"type": "string", "description": "Absolute Unreal Content directory."},
                "substring": {"type": "string", "description": "Optional package-path filter."},
            },
            ("content_dir",),
        ),
        _unreal_list,
    ),
    AutomationTool(
        "hammer5tools.unreal_references",
        "Read the deduplicated object references used by one Unreal package.",
        _object_schema(
            {
                "content_dir": {"type": "string", "description": "Absolute Unreal Content directory."},
                "object_path": {"type": "string", "description": "Unreal object or package path."},
            },
            ("content_dir", "object_path"),
        ),
        _unreal_references,
    ),
)

TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def capabilities(bridge: CoreBridge | None = None) -> JsonObject:
    """Describe this automation surface without mutating application state."""
    active_bridge = bridge or CoreBridge.instance()
    return {
        "application": "Hammer5Tools",
        "version": APP_VERSION,
        "core": asdict(active_bridge.probe()),
        "tools": [tool.name for tool in TOOLS],
        "transport": ["cli", "mcp-stdio"],
        "write_tools": False,
    }


def invoke_tool(name: str, arguments: Mapping[str, Any] | None = None, *, bridge: CoreBridge | None = None) -> JsonObject:
    """Invoke one registered tool and return a JSON-compatible object."""
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        raise KeyError(f"Unknown Hammer5Tools tool '{name}'")
    return tool.invoke(bridge or CoreBridge.instance(), arguments or {})
