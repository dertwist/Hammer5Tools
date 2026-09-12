"""Reading uncompiled Valve maps through the Core projection.

Core already deserializes a `.vmap` completely — the node tree, every entity with
its properties, triangulated brush meshes, model placements, and SmartProp
placements with their per-instance variable overrides. None of that was reachable
from automation, which could only list asset references.

Everything here is shaping. A production map's node tree serializes to roughly
six million tokens, so no tool returns it whole: reads answer with counts and
histograms, and the caller narrows by class, kind, or path.
"""

from __future__ import annotations

import os
from typing import Any

from core.bridge import CoreBridge

from automation.formats.fgd_io import describe
from automation.formats.shaping import paginate, select_path

# Translation lives in the last row of Core's row-vector 4x4 matrices.
_TRANSLATION = (12, 13, 14)


def _require(path: str) -> str:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Valve map not found: '{path}'")
    return path


def _entity(entity: Any) -> dict[str, Any]:
    return {
        "class": entity.class_name,
        "origin": entity.origin,
        "angles": entity.angles,
        "properties": dict(entity.properties),
    }


def _entity_brief(entity: Any) -> dict[str, Any]:
    """An entity reduced to what identifies and locates it."""
    properties = entity.properties or {}
    brief: dict[str, Any] = {"class": entity.class_name, "origin": entity.origin}
    for key in ("targetname", "model", "material", "hammeruniqueid"):
        value = properties.get(key)
        if value:
            brief[key] = value
    return brief


def _histogram(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _count_nodes(nodes: Any) -> tuple[int, dict[str, int]]:
    total = 0
    classes: dict[str, int] = {}

    def walk(items: Any) -> None:
        nonlocal total
        for node in items:
            total += 1
            name = node.class_name or ""
            classes[name] = classes.get(name, 0) + 1
            walk(node.children)

    walk(nodes)
    return total, dict(sorted(classes.items(), key=lambda pair: (-pair[1], pair[0])))


def _bounds(placements: Any) -> dict[str, list[float]] | None:
    points = [
        tuple(placement.transform[index] for index in _TRANSLATION)
        for placement in placements
        if placement.transform is not None and len(placement.transform) >= 16
    ]
    if not points:
        return None
    return {
        "minimum": [min(axis) for axis in zip(*points)],
        "maximum": [max(axis) for axis in zip(*points)],
    }



# Structures that are not entities and so never appear in the entity list, but
# carry map meaning: decals, paths, prefab instances, and entity I/O.
_STRUCTURE_CLASSES = {
    "overlays": ("CMapStaticOverlay",),
    "paths": ("CMapPath", "CMapPathNode"),
    "instances": ("CMapInstance", "CMapPrefab"),
    "connections": ("DmeConnectionData",),
    "groups": ("CMapGroup",),
}

_STRUCTURE_FIELDS = {
    "CMapStaticOverlay": ("origin", "angles", "scales", "projectionTargets", "force_hidden"),
    "CMapPath": ("origin", "angles"),
    "CMapPathNode": ("origin", "angles"),
    "CMapInstance": ("origin", "angles", "scales", "target", "force_hidden"),
    "CMapPrefab": ("origin", "angles", "scales", "targetMapName", "fixupType",
                   "variableOverrideNames", "variableOverrideValues"),
    "DmeConnectionData": ("outputName", "targetName", "inputName", "overrideParam", "delay", "timesToFire"),
    "CMapGroup": ("origin", "angles", "force_hidden"),
}


def _collect_structures(nodes: Any, wanted: tuple[str, ...]) -> list[dict[str, Any]]:
    """Gather non-entity structures, deduplicated by node id.

    A node can be reached by more than one path through the projection, so the
    same overlay or connection would otherwise be reported repeatedly.
    """
    found: dict[Any, dict[str, Any]] = {}
    order: list[Any] = []

    def walk(items: Any, parent: str) -> None:
        for node in items:
            class_name = node.class_name or ""
            if class_name in wanted:
                properties = node.properties or {}
                entry: dict[str, Any] = {"class": class_name}
                if parent:
                    entry["parent"] = parent
                for field in _STRUCTURE_FIELDS.get(class_name, ()):
                    value = properties.get(field)
                    if value not in (None, "", "Datamodel.StringArray", "Datamodel.IntArray"):
                        entry[field] = value
                # Nodes carry a nodeID; connection data does not, so it is
                # identified by its own contents. `parent` is left out of that
                # identity because the same node is reachable both from the
                # world and from the root, and only one of those paths names a
                # parent.
                identity = properties.get("nodeID") or tuple(
                    sorted(((key, value) for key, value in entry.items() if key != "parent"), key=str)
                )
                existing = found.get(identity)
                if existing is None:
                    found[identity] = entry
                    order.append(identity)
                elif "parent" not in existing and parent:
                    existing["parent"] = parent
            walk(node.children, class_name)

    walk(nodes, "")
    return [found[identity] for identity in order]


def read_vmap(
    path: str,
    detail: str = "summary",
    classname: str | None = None,
    select: str | None = None,
    structures: str | None = None,
    limit: int = 50,
    offset: int = 0,
    bridge: CoreBridge | None = None,
) -> dict[str, Any]:
    """Read an uncompiled .vmap: entity classes, properties, and asset references.

    `classname` narrows to one entity class, which is how you find the lights,
    the spawns, or the props without paging the whole map. `structures` reaches
    the things that are not entities — decals, paths, prefab instances, groups,
    and entity I/O connections.
    """
    document = (bridge or CoreBridge.instance()).read_valve_map(_require(path))
    entities = list(document.entities)

    if select:
        return {
            "path": path.replace("\\", "/"),
            "select": select,
            "value": select_path(
                {"entities": [_entity(item) for item in entities],
                 "asset_references": list(document.asset_references)},
                select,
            ),
        }

    if structures:
        classes = _STRUCTURE_CLASSES.get(structures)
        if classes is None:
            raise ValueError(f"'structures' must be one of {', '.join(sorted(_STRUCTURE_CLASSES))}")
        collected = _collect_structures(document.nodes, classes)
        result: dict[str, Any] = {"path": path.replace("\\", "/"), "structures": structures}
        result.update(paginate(collected, "items", limit=limit, offset=offset))
        return result

    if classname:
        wanted = classname.lower()
        matched = [item for item in entities if (item.class_name or "").lower() == wanted]
        result: dict[str, Any] = {
            "path": path.replace("\\", "/"),
            "classname": classname,
            "matched": len(matched),
        }
        # One line saying what this class is, from the game's own definitions.
        explanation = describe(classname)
        if explanation:
            result["description"] = explanation
        shaped = [_entity(item) for item in matched] if detail == "full" else [_entity_brief(item) for item in matched]
        result.update(paginate(shaped, "entities", limit=limit, offset=offset))
        return result

    node_count, node_classes = _count_nodes(document.nodes)
    summary: dict[str, Any] = {
        "path": path.replace("\\", "/"),
        "entity_count": len(entities),
        "entity_classes": _histogram(item.class_name for item in entities),
        "node_count": node_count,
        "node_classes": node_classes,
        "asset_reference_count": len(document.asset_references),
        "has_thumbnail": document.thumbnail is not None,
    }
    if detail == "summary":
        return summary
    if detail != "full":
        raise ValueError("'detail' must be 'summary' or 'full'")

    # Even at full detail the node tree is withheld: a production map's tree
    # serializes to millions of tokens. Narrow with classname or select instead.
    summary.update(paginate([_entity(item) for item in entities], "entities", limit=limit, offset=offset))
    summary["asset_references"] = list(document.asset_references)
    return summary


def read_vmap_scene(
    path: str,
    include: str = "summary",
    resource: str | None = None,
    limit: int = 50,
    offset: int = 0,
    bridge: CoreBridge | None = None,
) -> dict[str, Any]:
    """Read the drawable projection: brush meshes, model placements, SmartProps.

    `include` selects what comes back in full — `props`, `smartprops`, `meshes`,
    or `summary` for counts and bounds only.
    """
    scene = (bridge or CoreBridge.instance()).read_valve_map_scene(_require(path))
    props, smart_props = list(scene.props), list(scene.smart_props)

    if resource:
        wanted = resource.replace("\\", "/").lower()
        props = [item for item in props if (item.resource or "").replace("\\", "/").lower() == wanted]
        smart_props = [item for item in smart_props if (item.resource or "").replace("\\", "/").lower() == wanted]

    result: dict[str, Any] = {
        "path": path.replace("\\", "/"),
        "mesh_count": len(scene.meshes),
        "prop_count": len(props),
        "smartprop_count": len(smart_props),
        "distinct_prop_models": _histogram(item.resource for item in props if item.resource),
        "distinct_smartprops": _histogram(item.resource for item in smart_props if item.resource),
        "bounds": _bounds(props + smart_props),
        "diagnostics": list(scene.diagnostics),
    }
    if resource:
        result["resource"] = resource

    if include == "summary":
        return result
    if include == "props":
        result.update(paginate([_placement(item) for item in props], "props", limit=limit, offset=offset))
        return result
    if include == "smartprops":
        result.update(paginate([_placement(item, variables=True) for item in smart_props],
                               "smartprops", limit=limit, offset=offset))
        return result
    if include == "meshes":
        # Vertex and index arrays stay out: they are megabytes and an agent
        # cannot act on them. Materials are the part that identifies a mesh.
        result.update(paginate(
            [
                {
                    "name": mesh.name,
                    "submesh_count": len(mesh.submeshes),
                    "materials": sorted({sub.material for sub in mesh.submeshes if sub.material}),
                }
                for mesh in scene.meshes
            ],
            "meshes", limit=limit, offset=offset,
        ))
        return result
    raise ValueError("'include' must be 'summary', 'props', 'smartprops' or 'meshes'")


def _placement(placement: Any, variables: bool = False) -> dict[str, Any]:
    transform = list(placement.transform or ())
    entry: dict[str, Any] = {
        "name": placement.name,
        "class": placement.class_name,
        "resource": placement.resource,
        "position": [transform[index] for index in _TRANSLATION] if len(transform) >= 16 else None,
    }
    if variables and placement.variables:
        # The per-instance overrides are the reason to read a SmartProp
        # placement at all: they are what the map changed about the prop.
        entry["variables"] = dict(placement.variables)
    return entry
