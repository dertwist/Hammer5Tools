"""
vmap writer — turns a normalized UE scene (the bridge's dump-scene output) into
a Source 2 .vmap of prop_static entities.

Each UE static-mesh placement becomes a CMapEntity(prop_static) whose transform
is converted from UE space to Source 2 space via the shared transform module,
and whose `model` points at the vmdl produced for that mesh.

The map skeleton (CMapRootElement / CMapWorld) is taken from a bundled empty
template so the output matches exactly what Hammer expects (binary/vmap v40);
we only clear the template's world children and inject our own. Falls back to
keyvalues2 text encoding if binary saving is unavailable.
"""

import os
import random
from pathlib import Path
from typing import Callable, Iterable, Optional

from src.dotnet import setup_keyvalues2
from .transform import convert_transform, UETransform, UnitScale
from .vmdl_writer import ue_mesh_to_model_path

# Component types whose component-level transform is the world transform of a
# single placed mesh. Instanced/foliage/spline components need per-instance or
# spline handling and are reported separately, not emitted here.
_SIMPLE_COMPONENT = "StaticMeshComponent"

_TEMPLATE_CANDIDATES = [
    "Presets/valve_default/content/maps/xxx_mapname_xxx.vmap",
    "Presets/hammer5tools/content/maps/xxx_mapname_xxx.vmap",
    "Hammer5Tools/Presets/valve_default/content/maps/xxx_mapname_xxx.vmap",
    "Hammer5Tools/Presets/hammer5tools/content/maps/xxx_mapname_xxx.vmap",
]


def find_empty_template() -> Optional[str]:
    """Locate a bundled empty vmap to use as the map skeleton."""
    root = Path(__file__).resolve().parents[3]
    for rel in _TEMPLATE_CANDIDATES:
        p = root / rel
        if p.is_file():
            return str(p)
    return None


class VmapWriteResult:
    def __init__(self):
        self.placed = 0
        self.placed_smartprops = 0
        self.skipped = 0
        self.skipped_types = {}   # componentType -> count
        self.models = set()       # source model paths referenced

    def note_skip(self, comp_type):
        self.skipped += 1
        self.skipped_types[comp_type] = self.skipped_types.get(comp_type, 0) + 1


def write_vmap(
    actors: Iterable[dict],
    output_path: str,
    model_resolver: Optional[Callable[[str], str]] = None,
    unit_scale: float = UnitScale.ONE_TO_ONE,
    template_path: Optional[str] = None,
    strip_prefix: bool = False,
) -> VmapWriteResult:
    """
    Write a .vmap of prop_static entities from normalized scene actors.

    actors          : dicts with keys actor, componentType, mesh, location,
                      rotation, scale (UE space) — i.e. dump-scene output.
    model_resolver  : maps a UE mesh path to a Source model path; defaults to
                      ue_mesh_to_model_path.
    unit_scale      : UE→Source unit multiplier (shared with the vmdl import scale).
    """
    model_resolver = model_resolver or ue_mesh_to_model_path
    template_path = template_path or find_empty_template()
    if not template_path:
        raise FileNotFoundError(
            "No empty vmap template found to use as a map skeleton "
            "(looked under Presets/*/content/maps/xxx_mapname_xxx.vmap)."
        )

    Datamodel, Element, DeferredMode = setup_keyvalues2()
    import Datamodel as DM
    import System
    from System.Numerics import Vector3

    dm = Datamodel.Load(template_path, DeferredMode.Automatic)
    world = dm.Root["world"]
    world["children"].Clear()

    def E(name, cls):
        return Element(dm, name, None, cls)

    def empty_pluglist():
        p = E("", "DmePlugList")
        p["names"] = DM.StringArray()
        p["dataTypes"] = DM.IntArray()
        p["plugTypes"] = DM.IntArray()
        p["descriptions"] = DM.StringArray()
        return p

    def make_prop(name, model, origin, angles, scales, node_id):
        ep = E("", "EditGameClassProps")
        ep["classname"] = "prop_static"
        ep["model"] = model
        ep["skin"] = "default"
        ep["solid"] = "6"
        ep["rendercolor"] = "255 255 255"
        ep["disableshadows"] = "0"

        ent = E(name, "CMapEntity")
        ent["nodeID"] = System.Int32(node_id)
        ent["referenceID"] = System.UInt64(random.getrandbits(64))
        ent["children"] = DM.ElementArray()
        ent["variableTargetKeys"] = DM.StringArray()
        ent["variableNames"] = DM.StringArray()
        ent["relayPlugData"] = empty_pluglist()
        ent["connectionsData"] = DM.ElementArray()
        ent["entity_properties"] = ep
        ent["origin"] = Vector3(float(origin[0]), float(origin[1]), float(origin[2]))
        ent["angles"] = DM.QAngle(float(angles[0]), float(angles[1]), float(angles[2]))
        ent["scales"] = Vector3(float(scales[0]), float(scales[1]), float(scales[2]))
        ent["hitNormal"] = Vector3(0.0, 0.0, 1.0)
        for b in ("transformLocked", "force_hidden", "editorOnly", "isProceduralEntity"):
            ent[b] = False
        return ent

    def make_smartprop(name, smartprop_rel_path, origin, angles, scales, node_id):
        ep = E("", "EditGameClassProps")
        ep["classname"] = "subclass_prop_smart"
        ep["smartprop"] = smartprop_rel_path

        ent = E(name, "CMapEntity")
        ent["nodeID"] = System.Int32(node_id)
        ent["referenceID"] = System.UInt64(random.getrandbits(64))
        ent["children"] = DM.ElementArray()
        ent["variableTargetKeys"] = DM.StringArray()
        ent["variableNames"] = DM.StringArray()
        ent["relayPlugData"] = empty_pluglist()
        ent["connectionsData"] = DM.ElementArray()
        ent["entity_properties"] = ep
        ent["origin"] = Vector3(float(origin[0]), float(origin[1]), float(origin[2]))
        ent["angles"] = DM.QAngle(float(angles[0]), float(angles[1]), float(angles[2]))
        ent["scales"] = Vector3(float(scales[0]), float(scales[1]), float(scales[2]))
        ent["hitNormal"] = Vector3(0.0, 0.0, 1.0)
        for b in ("transformLocked", "force_hidden", "editorOnly", "isProceduralEntity"):
            ent[b] = False
        return ent

    result = VmapWriteResult()
    node_id = 1000
    children = world["children"]

    for a in actors:
        comp = a.get("componentType", "")
        mesh = a.get("mesh")
        bp = a.get("blueprint")

        if comp != _SIMPLE_COMPONENT and comp != "BlueprintActor" and not bp:
            result.note_skip(comp)      # foliage/spline/instanced — handled elsewhere
            continue

        loc = a["location"]; rot = a["rotation"]; scl = a["scale"]
        st = convert_transform(
            UETransform(
                (loc["x"], loc["y"], loc["z"]),
                (rot["pitch"], rot["yaw"], rot["roll"]),
                (scl["x"], scl["y"], scl["z"]),
            ),
            unit_scale=unit_scale,
        )
        angles = st.angles

        node_id += 1
        name = a.get("actor") or f"ent_{node_id}"

        if comp == "BlueprintActor" or bp:
            bp_name = bp or name
            from .vmdl_writer import strip_ue_prefix
            smartprop_path = f"smartprops/{strip_ue_prefix(bp_name).lower()}.vsmart"
            children.Add(make_smartprop(name, smartprop_path, st.origin, angles, st.scales, node_id))
            result.placed_smartprops += 1
        elif comp == _SIMPLE_COMPONENT and mesh:
            model = model_resolver(mesh)
            result.models.add(model)
            children.Add(make_prop(name, model, st.origin, angles, st.scales, node_id))
            result.placed += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    try:
        dm.Save(output_path, "binary", 9)
    except Exception:
        dm.Save(output_path, "keyvalues2", 4)
    return result
