"""Tool definitions shared by the Hammer5Tools CLI and MCP server."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from core.bridge import CoreBridge
from core.version import APP_VERSION

from automation.guides.loader import TOPICS, guide
from automation.formats.fgd_io import entity_info
from automation.formats.vmap_io import read_vmap, read_vmap_scene
from automation.formats.vmdl_io import edit_vmdl, read_vmdl, write_vmdl
from automation.formats.vmat_io import edit_vmat, read_vmat, write_vmat
from automation.formats.vtex_io import edit_vtex, read_vtex, write_vtex
from automation.formats.vsmart_io import edit_vsmart, evaluate_vsmart, read_vsmart, write_vsmart
from automation.formats.vsmart_lint import lint_vsmart
from automation.formats.vsmart_patch import patch_vsmart
from automation.formats.vdata_io import edit_vdata, read_vdata, write_vdata
from automation.formats.vsnap_io import edit_vsnap, generate_vsnap, read_vsnap, write_vsnap
from automation.operations.compiler import compile_asset
from automation.operations.dependencies import resolve_dependencies
from automation.operations.validation import find_unused_assets, validate_addon
from automation.operations.vmap_blockout import DEFAULT_BOX_MODEL, write_blockout
from automation.operations.vmap_ops import vmap_rewrite_references
from automation.operations.vpk_ops import vpk_extract, vpk_search

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class AutomationTool:
    """One automation operation and its MCP metadata."""

    name: str
    description: str
    input_schema: JsonObject
    invoke: Callable[[CoreBridge, Mapping[str, Any]], JsonObject]
    read_only: bool = True
    destructive: bool = False
    idempotent: bool = True

    def mcp_definition(self) -> JsonObject:
        """Return this tool's MCP tools/list representation."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": self._annotations(),
        }


    def _annotations(self) -> JsonObject:
        """MCP annotations, omitting the hints that carry no meaning.

        destructiveHint and idempotentHint are defined only when readOnlyHint is
        false, so a read-only tool that emits them pays for nothing.
        """
        annotations: JsonObject = {
            "title": self.name.replace("hammer5tools.", "Hammer5Tools ").replace("_", " ").title(),
            "readOnlyHint": self.read_only,
            "openWorldHint": False,
        }
        if not self.read_only:
            annotations["destructiveHint"] = self.destructive
            annotations["idempotentHint"] = self.idempotent
        return annotations


def _object_schema(properties: JsonObject, required: tuple[str, ...] = ()) -> JsonObject:
    schema: JsonObject = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = list(required)
    return schema


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


def _optional_bool(arguments: Mapping[str, Any], name: str, default: bool = False) -> bool:
    value = arguments.get(name)
    return bool(value) if value is not None else default


def _optional_float(arguments: Mapping[str, Any], name: str, default: float = 1.0) -> float:
    value = arguments.get(name)
    return float(value) if value is not None else default


def _optional_int(arguments: Mapping[str, Any], name: str, default: int = 0) -> int:
    value = arguments.get(name)
    return int(value) if value is not None else default


def _optional_dict(arguments: Mapping[str, Any], name: str) -> dict[str, Any] | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"'{name}' must be an object")
    return dict(value)


def _optional_list(arguments: Mapping[str, Any], name: str) -> list[Any] | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"'{name}' must be an array")
    return list(value)


# Existing tools handlers

def _guide(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return guide(_optional_string(arguments, "topic"))


def _core_status(bridge: CoreBridge, _arguments: Mapping[str, Any]) -> JsonObject:
    return asdict(bridge.probe())


def _vmap_references(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    path = _required_string(arguments, "path")
    return {"path": path, "references": list(bridge.read_valve_map_asset_references(path))}


def _entity_info(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return entity_info(
        classname=_optional_string(arguments, "classname"),
        search=_optional_string(arguments, "search"),
        include_properties=_optional_bool(arguments, "include_properties", True),
        cs2_path=_optional_string(arguments, "cs2_path"),
        limit=_optional_int(arguments, "limit", 40),
    )


def _vmap_read(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return read_vmap(
        _required_string(arguments, "path"),
        detail=_optional_string(arguments, "detail") or "summary",
        classname=_optional_string(arguments, "classname"),
        select=_optional_string(arguments, "select"),
        structures=_optional_string(arguments, "structures"),
        limit=_optional_int(arguments, "limit", 50),
        offset=_optional_int(arguments, "offset", 0),
        bridge=bridge,
    )


def _vmap_scene(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return read_vmap_scene(
        _required_string(arguments, "path"),
        include=_optional_string(arguments, "include") or "summary",
        resource=_optional_string(arguments, "resource"),
        limit=_optional_int(arguments, "limit", 50),
        offset=_optional_int(arguments, "offset", 0),
        bridge=bridge,
    )


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


# VMDL handlers
def _vmdl_read(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return read_vmdl(
        _required_string(arguments, "path"),
        detail=_optional_string(arguments, "detail") or "summary",
        select=_optional_string(arguments, "select"),
    )


def _vmdl_write(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return write_vmdl(
        path=_required_string(arguments, "path"),
        mesh_rel_path=_required_string(arguments, "mesh_rel_path"),
        material_remaps=_optional_list(arguments, "material_remaps"),
        import_scale=_optional_float(arguments, "import_scale", 1.0),
        physics=_optional_bool(arguments, "physics", True),
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vmdl_edit(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return edit_vmdl(
        path=_required_string(arguments, "path"),
        updates=_optional_dict(arguments, "updates") or {},
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


# VMAT handlers
def _vmat_read(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return read_vmat(
        _required_string(arguments, "path"),
        detail=_optional_string(arguments, "detail") or "summary",
        select=_optional_string(arguments, "select"),
    )


def _vmat_write(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return write_vmat(
        path=_required_string(arguments, "path"),
        shader=_optional_string(arguments, "shader") or "csgo_environment.vfx",
        slots=_optional_dict(arguments, "slots"),
        parameters=_optional_dict(arguments, "parameters"),
        flags=_optional_dict(arguments, "flags"),
        system_attributes=_optional_dict(arguments, "system_attributes"),
        attributes=_optional_dict(arguments, "attributes"),
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vmat_edit(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return edit_vmat(
        path=_required_string(arguments, "path"),
        set_slots=_optional_dict(arguments, "set_slots"),
        set_parameters=_optional_dict(arguments, "set_parameters"),
        set_flags=_optional_dict(arguments, "set_flags"),
        remove_keys=_optional_list(arguments, "remove_keys"),
        shader=_optional_string(arguments, "shader"),
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


# VTEX handlers
def _vtex_read(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return read_vtex(
        _required_string(arguments, "path"),
        detail=_optional_string(arguments, "detail") or "summary",
        select=_optional_string(arguments, "select"),
    )


def _vtex_write(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return write_vtex(
        path=_required_string(arguments, "path"),
        input_file=_required_string(arguments, "input_file"),
        output_format=_optional_string(arguments, "output_format") or "BC7",
        color_space=_optional_string(arguments, "color_space") or "srgb",
        output_type=_optional_string(arguments, "output_type") or "2D",
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vtex_edit(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return edit_vtex(
        path=_required_string(arguments, "path"),
        updates=_optional_dict(arguments, "updates") or {},
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


# VSMART handlers
def _vsmart_read(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return read_vsmart(
        _required_string(arguments, "path"),
        detail=_optional_string(arguments, "detail") or "summary",
        select=_optional_string(arguments, "select"),
    )


def _vsmart_write(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return write_vsmart(
        path=_required_string(arguments, "path"),
        root_class=_optional_string(arguments, "root_class") or "CSmartPropElement_Group",
        variables=_optional_list(arguments, "variables"),
        choices=_optional_list(arguments, "choices"),
        children=_optional_list(arguments, "children"),
        modifiers=_optional_list(arguments, "modifiers"),
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vsmart_edit(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return edit_vsmart(
        path=_required_string(arguments, "path"),
        updates=_optional_dict(arguments, "updates") or {},
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vsmart_evaluate(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return evaluate_vsmart(
        bridge=bridge,
        path=_required_string(arguments, "path"),
        options=_optional_dict(arguments, "options"),
    )


def _vsmart_patch(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return patch_vsmart(
        path=_required_string(arguments, "path"),
        operations=_optional_list(arguments, "operations") or [],
        dry_run=_optional_bool(arguments, "dry_run", False),
        reindex=_optional_bool(arguments, "reindex", True),
    )


def _vsmart_lint(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return lint_vsmart(_required_string(arguments, "path"))



# VDATA handlers
def _vdata_read(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return read_vdata(
        _required_string(arguments, "path"),
        detail=_optional_string(arguments, "detail") or "summary",
        select=_optional_string(arguments, "select"),
    )


def _vdata_write(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return write_vdata(
        path=_required_string(arguments, "path"),
        entries=_optional_dict(arguments, "entries") or {},
        generic_data_type=_optional_string(arguments, "generic_data_type") or "CDetailPropType",
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vdata_edit(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return edit_vdata(
        path=_required_string(arguments, "path"),
        updates=_optional_dict(arguments, "updates") or {},
        remove_keys=_optional_list(arguments, "remove_keys"),
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


# VSNAP handlers
def _vsnap_read(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return read_vsnap(bridge, _required_string(arguments, "path"))


def _vsnap_write(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    positions = _optional_list(arguments, "positions")
    if not positions:
        raise ValueError("'positions' must be a non-empty array of [x, y, z] tuples")
    return write_vsnap(
        bridge=bridge,
        path=_required_string(arguments, "path"),
        positions=positions,
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vsnap_generate(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return generate_vsnap(
        bridge=bridge,
        path=_required_string(arguments, "path"),
        primitive=_optional_string(arguments, "primitive") or "cube",
        count=_optional_int(arguments, "count", 100),
        size=_optional_float(arguments, "size", 64.0),
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vsnap_edit(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return edit_vsnap(
        bridge=bridge,
        path=_required_string(arguments, "path"),
        lighting=_optional_dict(arguments, "lighting"),
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


# Operations handlers
def _compile_asset(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return compile_asset(
        path=_required_string(arguments, "path"),
        cs2_path=_optional_string(arguments, "cs2_path"),
        force=_optional_bool(arguments, "force", False),
        timeout_seconds=_optional_int(arguments, "timeout_seconds", 120),
    )


def _validate_addon(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return validate_addon(
        addon_name=_optional_string(arguments, "addon_name"),
        cs2_dir=_optional_string(arguments, "cs2_dir"),
        bridge=bridge,
        limit=_optional_int(arguments, "limit", 50),
        offset=_optional_int(arguments, "offset", 0),
    )


def _find_unused_assets(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return find_unused_assets(
        map_path=_required_string(arguments, "map_path"),
        addon_dir=_optional_string(arguments, "addon_dir"),
        limit=_optional_int(arguments, "limit", 100),
        offset=_optional_int(arguments, "offset", 0),
    )


def _resolve_dependencies(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return resolve_dependencies(
        path=_required_string(arguments, "path"),
        addon_dir=_optional_string(arguments, "addon_dir"),
        limit=_optional_int(arguments, "limit", 200),
        offset=_optional_int(arguments, "offset", 0),
        include_all=_optional_bool(arguments, "include_all", False),
    )


def _vmap_write_blockout(_bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return write_blockout(
        path=_required_string(arguments, "path"),
        boxes=_optional_list(arguments, "boxes") or [],
        skeleton=_optional_string(arguments, "skeleton"),
        cs2_path=_optional_string(arguments, "cs2_path"),
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vmap_rewrite_references(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    replacements = _optional_dict(arguments, "replacements")
    if not replacements:
        raise ValueError("'replacements' must be an object of from_path: to_path pairs")
    return vmap_rewrite_references(
        vmap_path=_required_string(arguments, "vmap_path"),
        replacements=replacements,
        bridge=bridge,
        dry_run=_optional_bool(arguments, "dry_run", False),
    )


def _vpk_search(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return vpk_search(
        query=_required_string(arguments, "query"),
        extension=_optional_string(arguments, "extension"),
        game_dir=_optional_string(arguments, "game_dir"),
        bridge=bridge,
        limit=_optional_int(arguments, "limit", 100),
    )


def _vpk_extract(bridge: CoreBridge, arguments: Mapping[str, Any]) -> JsonObject:
    return vpk_extract(
        internal_path=_required_string(arguments, "internal_path"),
        output_path=_required_string(arguments, "output_path"),
        game_dir=_optional_string(arguments, "game_dir"),
        bridge=bridge,
    )


TOOLS: tuple[AutomationTool, ...] = (
    AutomationTool(
        "hammer5tools.guide",
        "Read a Source 2 authoring topic before doing the work: " + ", ".join(TOPICS) +
        ". Call with no topic for one-line summaries of each.",
        _object_schema({"topic": {"type": "string", "enum": sorted(TOPICS), "description": "Topic name; omit to list."}}),
        _guide,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.core_status",
        "Check whether the versioned Hammer5Tools NativeAOT Core can be loaded.",
        _object_schema({}),
        _core_status,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vmap_references",
        "Read content-relative asset references from an uncompiled VMAP without changing it.",
        _object_schema(
            {"path": {"type": "string", "description": "Absolute path to an uncompiled .vmap file."}},
            ("path",),
        ),
        _vmap_references,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.entity_info",
        "Describe a map entity class from the game's own FGD definitions: what it is for, and "
        "every keyvalue with its type and help text, including inherited ones. Pass search to "
        "find classes by name or description. Covers every entity the installed build defines.",
        _object_schema(
            {
                "classname": {"type": "string", "description": "Entity class, e.g. prop_static or light_omni2."},
                "search": {"type": "string", "description": "Find classes matching a name or description substring."},
                "include_properties": {"type": "boolean", "description": "Include keyvalues (default true)."},
                "cs2_path": {"type": "string"},
                "limit": {"type": "integer", "description": "Maximum search results (default 40)."},
            },
        ),
        _entity_info,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vmap_read",
        "Read an uncompiled .vmap: entity counts by class, node counts by class, and asset "
        "references. classname lists one class of entity with its properties; structures reaches "
        "what is not an entity - overlays (decals), paths, instances (prefabs), connections "
        "(entity I/O) and groups. The node tree is never returned whole.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the uncompiled .vmap file."},
                "classname": {"type": "string", "description": "List only entities of this class, e.g. prop_static."},
                "structures": {"type": "string", "enum": ["overlays", "paths", "instances", "connections", "groups"]},
                "detail": {"type": "string", "enum": ["summary", "full"]},
                "select": {"type": "string"},
                "limit": {"type": "integer", "description": "Maximum entities to return (default 50)."},
                "offset": {"type": "integer"},
            },
            ("path",),
        ),
        _vmap_read,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vmap_scene",
        "Read a .vmap's drawable projection: brush meshes, model placements, and SmartProp "
        "placements with the per-instance variable overrides the map applied. include selects "
        "props, smartprops, meshes, or summary for counts and world bounds.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the uncompiled .vmap file."},
                "include": {"type": "string", "enum": ["summary", "props", "smartprops", "meshes"]},
                "resource": {"type": "string", "description": "Only placements of this model or .vsmart."},
                "limit": {"type": "integer", "description": "Maximum placements to return (default 50)."},
                "offset": {"type": "integer"},
            },
            ("path",),
        ),
        _vmap_scene,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.unreal_info",
        "Inspect a loose Unreal Content directory and report mounted asset counts.",
        _object_schema(
            {"content_dir": {"type": "string", "description": "Absolute Unreal Content directory."}},
            ("content_dir",),
        ),
        _unreal_info,
        read_only=True,
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
        read_only=True,
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
        read_only=True,
    ),
    # VMDL
    AutomationTool(
        "hammer5tools.vmdl_read",
        "Read and parse a Source 2 .vmdl file, returning meshes, materials, LODs, and collision hulls.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vmdl file."},
                "detail": {"type": "string", "enum": ["names", "summary", "full"]},
                "select": {"type": "string"},
            },
            ("path",),
        ),
        _vmdl_read,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vmdl_write",
        "Create a standard modeldoc41 .vmdl file referencing a mesh and material remaps.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Destination .vmdl path."},
                "mesh_rel_path": {"type": "string", "description": "Relative path to render mesh."},
                "material_remaps": {"type": "array", "description": "List of material remap objects."},
                "import_scale": {"type": "number", "description": "Import scale factor (default 1.0)."},
                "physics": {"type": "boolean", "description": "Generate default physics hull."},
                "dry_run": {"type": "boolean"},
            },
            ("path", "mesh_rel_path"),
        ),
        _vmdl_write,
        read_only=False,
        destructive=True,
    ),
    AutomationTool(
        "hammer5tools.vmdl_edit",
        "Edit an existing .vmdl file in-place, updating material remaps, scale, or mesh source.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vmdl file."},
                "updates": {"type": "object", "description": "Dictionary of fields to update."},
                "dry_run": {"type": "boolean"},
            },
            ("path", "updates"),
        ),
        _vmdl_edit,
        read_only=False,
        destructive=False,
    ),
    # VMAT
    AutomationTool(
        "hammer5tools.vmat_read",
        "Read and parse a Source 2 .vmat file, extracting shader, texture slots, parameters, and flags.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vmat file."},
                "detail": {"type": "string", "enum": ["names", "summary", "full"]},
                "select": {"type": "string"},
            },
            ("path",),
        ),
        _vmat_read,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vmat_write",
        "Create a formatted Source 2 .vmat file with shader, texture slots, and parameters.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Destination .vmat path."},
                "shader": {"type": "string", "description": "Shader name (default csgo_environment.vfx)."},
                "slots": {"type": "object", "description": "Texture slot bindings."},
                "parameters": {"type": "object", "description": "Material parameters."},
                "flags": {"type": "object", "description": "Feature flags (F_*)."},
                "system_attributes": {"type": "object", "description": "System attributes."},
                "attributes": {"type": "object", "description": "Tool attributes."},
                "dry_run": {"type": "boolean"},
            },
            ("path",),
        ),
        _vmat_write,
        read_only=False,
        destructive=True,
    ),
    AutomationTool(
        "hammer5tools.vmat_edit",
        "Edit an existing .vmat file in-place, updating texture slots, parameters, or flags.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vmat file."},
                "set_slots": {"type": "object", "description": "Texture slots to set/update."},
                "set_parameters": {"type": "object", "description": "Parameters to set/update."},
                "set_flags": {"type": "object", "description": "Feature flags to set/update."},
                "remove_keys": {"type": "array", "description": "Keys to remove."},
                "shader": {"type": "string", "description": "New shader name."},
                "dry_run": {"type": "boolean"},
            },
            ("path",),
        ),
        _vmat_edit,
        read_only=False,
        destructive=False,
    ),
    # VTEX
    AutomationTool(
        "hammer5tools.vtex_read",
        "Read a Source 2 .vtex compile configuration, extracting input textures and output format.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vtex file."},
                "detail": {"type": "string", "enum": ["names", "summary", "full"]},
                "select": {"type": "string"},
            },
            ("path",),
        ),
        _vtex_read,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vtex_write",
        "Create a standard KeyValues3 .vtex compile configuration for CS2.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Destination .vtex path."},
                "input_file": {"type": "string", "description": "Source image path."},
                "output_format": {"type": "string", "description": "Compression format (BC7, DXT1, etc.)."},
                "color_space": {"type": "string", "description": "Color space (srgb, linear)."},
                "output_type": {"type": "string", "description": "Texture type (2D, Cube)."},
                "dry_run": {"type": "boolean"},
            },
            ("path", "input_file"),
        ),
        _vtex_write,
        read_only=False,
        destructive=True,
    ),
    AutomationTool(
        "hammer5tools.vtex_edit",
        "Edit an existing .vtex compile configuration, updating input texture sources or format.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vtex file."},
                "updates": {"type": "object", "description": "Updates dict."},
                "dry_run": {"type": "boolean"},
            },
            ("path", "updates"),
        ),
        _vtex_edit,
        read_only=False,
        destructive=False,
    ),
    # VSMART
    AutomationTool(
        "hammer5tools.vsmart_read",
        "Read a .vsmart SmartProp. Summary gives every exposed parameter plus an element outline, with CSmartProp class prefixes stripped; detail='full' returns every node and real class names; select addresses one node.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vsmart file."},
                "detail": {"type": "string", "enum": ["names", "summary", "full"]},
                "select": {"type": "string"},
            },
            ("path",),
        ),
        _vsmart_read,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vsmart_write",
        "Create a standard KeyValues3 .vsmart SmartProp file.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Destination .vsmart path."},
                "root_class": {"type": "string", "description": "Root element class."},
                "variables": {"type": "array", "description": "SmartProp variable definitions."},
                "choices": {"type": "array", "description": "SmartProp choices definitions."},
                "children": {"type": "array", "description": "Child elements."},
                "modifiers": {"type": "array", "description": "Root modifiers."},
                "dry_run": {"type": "boolean"},
            },
            ("path",),
        ),
        _vsmart_write,
        read_only=False,
        destructive=True,
    ),
    AutomationTool(
        "hammer5tools.vsmart_edit",
        "Edit an existing .vsmart file in-place, modifying variables, choices, or children.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vsmart file."},
                "updates": {"type": "object", "description": "Updates dict."},
                "dry_run": {"type": "boolean"},
            },
            ("path", "updates"),
        ),
        _vsmart_edit,
        read_only=False,
        destructive=False,
    ),
    AutomationTool(
        "hammer5tools.vsmart_evaluate",
        "Evaluate an uncompiled SmartProp document through the NativeAOT Core evaluation engine.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vsmart file."},
                "options": {"type": "object", "description": "maximum_depth, maximum_models, include_models (default false), offset, limit."},
            },
            ("path",),
        ),
        _vsmart_evaluate,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vsmart_patch",
        "Apply addressed edits to a .vsmart without sending the whole document. Operations: "
        "set (target, value), remove (target), add_variable (variable, optional after), "
        "add_category (name, contains). Reindexes element IDs and lints on write.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vsmart file."},
                "operations": {"type": "array", "description": "Ordered operations, each an object with 'op'."},
                "dry_run": {"type": "boolean"},
                "reindex": {"type": "boolean", "description": "Reassign unique element IDs (default true)."},
            },
            ("path", "operations"),
        ),
        _vsmart_patch,
        read_only=False,
        destructive=False,
    ),
    AutomationTool(
        "hammer5tools.vsmart_lint",
        "Check a .vsmart for the failure modes that make props vanish silently: NaN-producing "
        "division, empty typed defaults, duplicate element IDs, LinearScale on end caps, "
        "unpaired category markers, and expressions naming variables that do not exist.",
        _object_schema({"path": {"type": "string", "description": "A .vsmart file, or a directory to audit recursively."}}, ("path",)),
        _vsmart_lint,
        read_only=True,
    ),
    # VDATA
    AutomationTool(
        "hammer5tools.vdata_read",
        "Read a .vdata gamedata file. Summary lists entry names; detail='full' returns every entry body; select='<entry name>' returns one.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vdata file."},
                "detail": {"type": "string", "enum": ["names", "summary", "full"]},
                "select": {"type": "string"},
            },
            ("path",),
        ),
        _vdata_read,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vdata_write",
        "Create a standard KeyValues3 .vdata gamedata file.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Destination .vdata path."},
                "entries": {"type": "object", "description": "Named data entries."},
                "generic_data_type": {"type": "string", "description": "Gamedata type name."},
                "dry_run": {"type": "boolean"},
            },
            ("path", "entries"),
        ),
        _vdata_write,
        read_only=False,
        destructive=True,
    ),
    AutomationTool(
        "hammer5tools.vdata_edit",
        "Edit an existing .vdata file in-place, adding, modifying, or removing entries.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vdata file."},
                "updates": {"type": "object", "description": "Entries to add or update."},
                "remove_keys": {"type": "array", "description": "Entry keys to remove."},
                "dry_run": {"type": "boolean"},
            },
            ("path", "updates"),
        ),
        _vdata_edit,
        read_only=False,
        destructive=False,
    ),
    # VSNAP
    AutomationTool(
        "hammer5tools.vsnap_read",
        "Read a .vsnap particle snapshot and summarize its vertex streams and sample positions.",
        _object_schema({"path": {"type": "string", "description": "Path to the .vsnap file."}}, ("path",)),
        _vsnap_read,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vsnap_write",
        "Create a .vsnap particle snapshot from 3D positions.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Destination .vsnap path."},
                "positions": {"type": "array", "description": "Array of [x, y, z] points."},
                "dry_run": {"type": "boolean"},
            },
            ("path", "positions"),
        ),
        _vsnap_write,
        read_only=False,
        destructive=True,
    ),
    AutomationTool(
        "hammer5tools.vsnap_generate",
        "Generate a geometric primitive particle snapshot cloud (cube, sphere, cylinder).",
        _object_schema(
            {
                "path": {"type": "string", "description": "Destination .vsnap path."},
                "primitive": {"type": "string", "description": "Shape (cube, sphere, cylinder)."},
                "count": {"type": "integer", "description": "Number of points."},
                "size": {"type": "number", "description": "Dimensions in units."},
                "dry_run": {"type": "boolean"},
            },
            ("path",),
        ),
        _vsnap_generate,
        read_only=False,
        destructive=True,
    ),
    AutomationTool(
        "hammer5tools.vsnap_edit",
        "Edit an existing .vsnap file, applying a two-point lighting gradient.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the .vsnap file."},
                "lighting": {"type": "object", "description": "Lighting parameters (first_index, second_index)."},
                "dry_run": {"type": "boolean"},
            },
            ("path",),
        ),
        _vsnap_edit,
        read_only=False,
        destructive=False,
    ),
    # Operations
    AutomationTool(
        "hammer5tools.compile_asset",
        "Compile an uncompiled Source 2 asset headlessly using resourcecompiler.exe.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the uncompiled asset file."},
                "cs2_path": {"type": "string"},
                "force": {"type": "boolean", "description": "Force recompilation."},
                "timeout_seconds": {"type": "integer", "description": "Maximum compilation timeout in seconds."},
            },
            ("path",),
        ),
        _compile_asset,
        read_only=False,
        destructive=False,
    ),
    AutomationTool(
        "hammer5tools.validate_addon",
        "Validate an addon's asset integrity using the Core validator.",
        _object_schema(
            {
                "addon_name": {"type": "string", "description": "Optional addon name."},
                "cs2_dir": {"type": "string", "description": "Optional CS2 directory."},
                "limit": {"type": "integer", "description": "Maximum issues to return (default 50)."},
                "offset": {"type": "integer"},
            },
        ),
        _validate_addon,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.find_unused_assets",
        "Find orphan/unused assets in an addon by comparing disk files against map dependencies.",
        _object_schema(
            {
                "map_path": {"type": "string", "description": "Path to the map (.vmap)."},
                "addon_dir": {"type": "string", "description": "Optional addon content directory."},
                "limit": {"type": "integer", "description": "Maximum unused files to return (default 100)."},
                "offset": {"type": "integer"},
            },
            ("map_path",),
        ),
        _find_unused_assets,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.resolve_dependencies",
        "Recursively resolve all external asset dependencies for any Source 2 file.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Path to the asset file."},
                "addon_dir": {"type": "string", "description": "Optional addon content directory."},
                "include_all": {"type": "boolean", "description": "Also return the flat list, which duplicates the per-kind lists."},
                "limit": {"type": "integer", "description": "Maximum references to return (default 200)."},
                "offset": {"type": "integer"},
            },
            ("path",),
        ),
        _resolve_dependencies,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vmap_rewrite_references",
        "Atomically rewrite asset paths across an uncompiled VMAP level.",
        _object_schema(
            {
                "vmap_path": {"type": "string", "description": "Path to the .vmap file."},
                "replacements": {"type": "object", "description": "Dictionary of from_path: to_path pairs."},
                "dry_run": {"type": "boolean"},
            },
            ("vmap_path", "replacements"),
        ),
        _vmap_rewrite_references,
        read_only=False,
        destructive=False,
    ),
    AutomationTool(
        "hammer5tools.vmap_write_blockout",
        "Write a .vmap of prop_static blockout boxes, built on an existing valid map. Each box "
        "takes size (world units) and optional position, angles, model, skin. Use this instead of "
        "authoring map geometry directly: synthesized CMapMesh crashes Hammer and the compiler.",
        _object_schema(
            {
                "path": {"type": "string", "description": "Destination .vmap path."},
                "boxes": {"type": "array", "description": "Boxes, each {size:[x,y,z], position?, angles?, model?, skin?}."},
                "skeleton": {"type": "string", "description": "Existing .vmap to build on. Defaults to the addon template."},
                "cs2_path": {"type": "string"},
                "dry_run": {"type": "boolean"},
            },
            ("path", "boxes"),
        ),
        _vmap_write_blockout,
        read_only=False,
        destructive=True,
    ),
    AutomationTool(
        "hammer5tools.vpk_search",
        "Search for stock Valve assets inside the official CS2 game VPK archive.",
        _object_schema(
            {
                "query": {"type": "string", "description": "Search query substring."},
                "extension": {"type": "string", "description": "Optional extension filter."},
                "game_dir": {"type": "string"},
                "limit": {"type": "integer", "description": "Maximum number of results."},
            },
            ("query",),
        ),
        _vpk_search,
        read_only=True,
    ),
    AutomationTool(
        "hammer5tools.vpk_extract",
        "Extract an official asset from the CS2 game VPK archive to disk.",
        _object_schema(
            {
                "internal_path": {"type": "string", "description": "Internal asset path inside the VPK."},
                "output_path": {"type": "string", "description": "Destination file path on disk."},
                "game_dir": {"type": "string"},
            },
            ("internal_path", "output_path"),
        ),
        _vpk_extract,
        read_only=False,
        destructive=True,
    ),
)

TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def capabilities(bridge: CoreBridge | None = None) -> JsonObject:
    """Describe this automation surface without mutating application state."""
    active_bridge = bridge or CoreBridge.instance()
    has_write_tools = any(not tool.read_only for tool in TOOLS)
    return {
        "application": "Hammer5Tools",
        "version": APP_VERSION,
        "core": asdict(active_bridge.probe()),
        "tools": [tool.name for tool in TOOLS],
        "transport": ["cli", "mcp-stdio"],
        "write_tools": has_write_tools,
    }


def invoke_tool(name: str, arguments: Mapping[str, Any] | None = None, *, bridge: CoreBridge | None = None) -> JsonObject:
    """Invoke one registered tool and return a JSON-compatible object."""
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        raise KeyError(f"Unknown Hammer5Tools tool '{name}'")
    return tool.invoke(bridge or CoreBridge.instance(), arguments or {})
