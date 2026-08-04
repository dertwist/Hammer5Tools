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
from . import decal_template as DT

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
        self.placed_decals = 0
        self.skipped = 0
        self.skipped_types = {}   # componentType -> count
        self.models = set()       # source model paths referenced
        self.decal_materials = set()  # UE decal material paths referenced

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
    if model_resolver is None:
        model_resolver = lambda mesh: ue_mesh_to_model_path(mesh, strip_prefix=strip_prefix)
    template_path = template_path or find_empty_template()
    if not template_path:
        raise FileNotFoundError(
            "No empty vmap template found to use as a map skeleton "
            "(looked under Presets/*/content/maps/xxx_mapname_xxx.vmap)."
        )

    Datamodel, Element, DeferredMode = setup_keyvalues2()
    import Datamodel as DM
    import System
    from System.Numerics import Vector2, Vector3, Vector4

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
        # SmartProp placements are a dedicated CMapSmartProp element, not a
        # generic CMapEntity(subclass_prop_smart) — Hammer doesn't recognize
        # the latter as a smart prop. Schema below matches a real Hammer-saved
        # placement byte-for-byte (verified against a hand-placed example).
        eval_version = E("", "DmElement")
        eval_version["m_nDefinitionVersion"] = System.Int32(1)
        class_names = DM.StringArray()
        for cn in ("CSmartPropElement_Group", "CSmartPropElement_Model",
                   "CSmartPropOperation_Translate", "CSmartPropRoot"):
            class_names.Add(cn)
        eval_version["m_ClassNames"] = class_names
        class_versions = DM.IntArray()
        for _ in range(4):
            class_versions.Add(System.Int32(0))
        eval_version["m_ClassVersions"] = class_versions

        params_el = E("", "DmElement")
        params_el["values"] = DM.ElementArray()

        node_data = E("", "DmElement")
        node_data["evaluationVersion"] = eval_version
        node_data["parameters"] = params_el

        transform_pin = E("", "DmElement")
        transform_pin["referenceName"] = ""
        transform_pin["targetReferenceID"] = System.UInt64(0)
        transform_pin["offsetOrigin"] = Vector3(0.0, 0.0, 0.0)
        transform_pin["offsetAngles"] = DM.QAngle(0.0, 0.0, 0.0)
        transform_pin["pinAngles"] = True
        transform_pin["twoWay"] = False

        ent = E(name, "CMapSmartProp")
        ent["nodeID"] = System.Int32(node_id)
        ent["referenceID"] = System.UInt64(random.getrandbits(64))
        ent["children"] = DM.ElementArray()
        ent["variableTargetKeys"] = DM.StringArray()
        ent["variableNames"] = DM.StringArray()
        ent["origin"] = Vector3(float(origin[0]), float(origin[1]), float(origin[2]))
        ent["angles"] = DM.QAngle(float(angles[0]), float(angles[1]), float(angles[2]))
        ent["scales"] = Vector3(float(scales[0]), float(scales[1]), float(scales[2]))
        ent["transformLocked"] = False
        ent["transformPin"] = transform_pin
        ent["force_hidden"] = False
        ent["editorOnly"] = False
        ent["customVisGroup"] = ""
        ent["randomSeed"] = System.Int32(random.getrandbits(31))
        ent["smartPropFilename"] = smartprop_rel_path
        ent["tintColor"] = DM.Color(255, 255, 255, 255)
        ent["evaluationLocked"] = False
        ent["constrainToPrefab"] = False
        ent["shapeReferences"] = DM.ElementArray()
        ent["alpha"] = System.Int32(255)
        ent["cullDistance"] = System.Single(0.0)
        ent["fadeStartDistance"] = System.Single(-1.0)
        ent["lightingOriginName"] = ""
        ent["disableShadows"] = System.Int32(0)
        ent["bakedLigthtingMode"] = System.Int32(-1)
        ent["lightmapScaleBias"] = System.Int32(0)
        ent["bakeLightingDoubleSided"] = False
        ent["emissiveLightingEnabled"] = True
        ent["emissiveLightingBoost"] = System.Single(1.0)
        ent["collisionMode"] = System.Int32(-1)
        ent["collisionPropertyOverride"] = ""
        ent["isVisOccluder"] = False
        ent["renderToCubeMaps"] = True
        ent["disabledInLowQuality"] = False
        ent["bakeToWorld"] = False
        ent["disableMerging"] = False
        ent["renderWithDynamic"] = False
        ent["nodeData"] = node_data
        return ent

    def make_decal_overlay(name, material_path, origin, angles, scales, node_id):
        # CMapStaticOverlay is a native half-edge polygon-mesh primitive (not a
        # point entity) matching csgo_static_overlay.vfx. Its geometry is a
        # single 256x256 quad, cloned verbatim from a real Hammer-authored
        # decal (see decal_template.py) — every decal reuses that exact
        # topology and is positioned/oriented/resized via origin/angles/scales,
        # exactly like a prop, rather than deriving new mesh topology.
        def data_stream(attr_name, values, array_type, vec_ctor):
            s = E("", "CDmePolygonMeshDataStream")
            s["standardAttributeName"] = attr_name
            s["semanticName"] = attr_name
            s["semanticIndex"] = System.Int32(0)
            s["vertexBufferLocation"] = System.Int32(0)
            s["dataStateFlags"] = System.Int32(1)
            arr = array_type()
            for v in values:
                arr.Add(vec_ctor(*v))
            s["data"] = arr
            return s

        def int_stream(attr_name, values, flags=1):
            s = E("", "CDmePolygonMeshDataStream")
            s["standardAttributeName"] = attr_name
            s["semanticName"] = attr_name
            s["semanticIndex"] = System.Int32(0)
            s["vertexBufferLocation"] = System.Int32(0)
            s["dataStateFlags"] = System.Int32(flags)
            arr = DM.IntArray()
            for v in values:
                arr.Add(System.Int32(v))
            s["data"] = arr
            return s

        def data_array(size, streams):
            a = E("", "CDmePolygonMeshDataArray")
            a["size"] = System.Int32(size)
            sa = DM.ElementArray()
            for s in streams:
                sa.Add(s)
            a["streams"] = sa
            return a

        def int_array(values):
            a = DM.IntArray()
            for v in values:
                a.Add(System.Int32(v))
            return a

        vertex_data = data_array(4, [
            data_stream("position", DT.POSITIONS, DM.Vector3Array, Vector3),
        ])
        face_vertex_data = data_array(8, [
            data_stream("texcoord", DT.UVS, DM.Vector2Array, Vector2),
            data_stream("normal", DT.NORMALS, DM.Vector3Array, Vector3),
            data_stream("tangent", DT.TANGENTS, DM.Vector4Array, Vector4),
        ])
        edge_data = data_array(4, [int_stream("flags", DT.EDGE_FLAGS, flags=3)])
        face_data = data_array(1, [
            data_stream("textureScale", [DT.TEXTURE_SCALE], DM.Vector2Array, Vector2),
            data_stream("textureAxisU", [DT.TEXTURE_AXIS_U], DM.Vector4Array, Vector4),
            data_stream("textureAxisV", [DT.TEXTURE_AXIS_V], DM.Vector4Array, Vector4),
            int_stream("materialindex", [0], flags=8),
            int_stream("flags", [0], flags=3),
            int_stream("lightmapScaleBias", [0], flags=1),
        ])
        subdivision_data = E("", "CDmePolygonMeshSubdivisionData")
        subdivision_data["subdivisionLevels"] = DM.IntArray()
        subdivision_data["streams"] = DM.ElementArray()

        mesh_data = E("", "DmElement")
        mesh_data["vertexEdgeIndices"] = int_array(DT.VERTEX_EDGE_INDICES)
        mesh_data["vertexDataIndices"] = int_array(DT.VERTEX_DATA_INDICES)
        mesh_data["edgeVertexIndices"] = int_array(DT.EDGE_VERTEX_INDICES)
        mesh_data["edgeOppositeIndices"] = int_array(DT.EDGE_OPPOSITE_INDICES)
        mesh_data["edgeNextIndices"] = int_array(DT.EDGE_NEXT_INDICES)
        mesh_data["edgeFaceIndices"] = int_array(DT.EDGE_FACE_INDICES)
        mesh_data["edgeDataIndices"] = int_array(DT.EDGE_DATA_INDICES)
        mesh_data["edgeVertexDataIndices"] = int_array(DT.EDGE_VERTEX_DATA_INDICES)
        mesh_data["faceEdgeIndices"] = int_array(DT.FACE_EDGE_INDICES)
        mesh_data["faceDataIndices"] = int_array(DT.FACE_DATA_INDICES)
        mats = DM.StringArray(); mats.Add(material_path)
        mesh_data["materials"] = mats
        mesh_data["vertexData"] = vertex_data
        mesh_data["faceVertexData"] = face_vertex_data
        mesh_data["edgeData"] = edge_data
        mesh_data["faceData"] = face_data
        mesh_data["subdivisionData"] = subdivision_data

        transform_pin = E("", "DmElement")
        transform_pin["referenceName"] = ""
        transform_pin["targetReferenceID"] = System.UInt64(0)
        transform_pin["offsetOrigin"] = Vector3(0.0, 0.0, 0.0)
        transform_pin["offsetAngles"] = DM.QAngle(0.0, 0.0, 0.0)
        transform_pin["pinAngles"] = True
        transform_pin["twoWay"] = False

        mat_adjust = E("", "DmElement")
        mat_adjust["ColorBrightness"] = System.Single(0.5)
        mat_adjust["ColorContrast"] = System.Single(0.5)
        mat_adjust["ColorAlpha"] = System.Single(1.0)
        mat_adjust["RoughnessBrightness"] = System.Single(0.5)
        mat_adjust["RoughnessContrast"] = System.Single(0.5)
        mat_adjust["ShadingAlpha"] = System.Single(1.0)
        mat_adjust["NormalIntensity"] = System.Single(0.75)
        mat_adjust["RoughnessMetalnessOverride"] = False
        mat_adjust["NormalBlendOverride"] = True

        ov = E(name, "CMapStaticOverlay")
        ov["nodeID"] = System.Int32(node_id)
        ov["referenceID"] = System.UInt64(random.getrandbits(64))
        ov["children"] = DM.ElementArray()
        ov["variableTargetKeys"] = DM.StringArray()
        ov["variableNames"] = DM.StringArray()
        ov["meshData"] = mesh_data
        ov["projectionTargets"] = DM.IntArray()
        ov["origin"] = Vector3(float(origin[0]), float(origin[1]), float(origin[2]))
        ov["angles"] = DM.QAngle(float(angles[0]), float(angles[1]), float(angles[2]))
        ov["scales"] = Vector3(float(scales[0]), float(scales[1]), float(scales[2]))
        ov["transformLocked"] = False
        ov["transformPin"] = transform_pin
        ov["force_hidden"] = False
        ov["editorOnly"] = False
        for k, v in DT.DEFAULTS.items():
            if isinstance(v, float):
                ov[k] = System.Single(v)
            elif isinstance(v, bool):
                ov[k] = v
            elif isinstance(v, int):
                ov[k] = System.Int32(v)
            else:
                ov[k] = v
        ov["tintColor"] = DM.Color(255, 255, 255, 255)
        ov["physicsIncludedDetailLayers"] = DM.ElementArray()
        ov["physicsMissingDetailLayers"] = DM.ElementArray()
        ov["MaterialAdjustmentParamsStruct"] = mat_adjust
        return ov

    result = VmapWriteResult()
    node_id = 1000
    children = world["children"]

    for a in actors:
        comp = a.get("componentType", "")
        mesh = a.get("mesh")
        bp = a.get("blueprint")
        decal_material = a.get("material") if comp == "DecalComponent" else None

        if comp != _SIMPLE_COMPONENT and comp != "BlueprintActor" and not bp and comp != "DecalComponent":
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
            clean_bp_name = strip_ue_prefix(bp_name) if strip_prefix else bp_name
            smartprop_path = f"smartprops/{clean_bp_name.lower()}.vsmart"
            children.Add(make_smartprop(name, smartprop_path, st.origin, angles, st.scales, node_id))
            result.placed_smartprops += 1
        elif comp == "DecalComponent" and decal_material:
            from .material_converter import ue_material_to_vmat_path
            vmat_path = ue_material_to_vmat_path(decal_material)
            result.decal_materials.add(decal_material)
            children.Add(make_decal_overlay(name, vmat_path, st.origin, angles, st.scales, node_id))
            result.placed_decals += 1
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
