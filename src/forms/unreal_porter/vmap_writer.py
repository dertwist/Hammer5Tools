"""
vmap writer — turns a normalized UE scene (the bridge's dump-scene output) into
a Source 2 .vmap of prop_static entities.

Each UE static-mesh placement becomes a CMapEntity(prop_static) whose transform
is converted from UE space to Source 2 space via the shared transform module,
and whose `model` points at the vmdl produced for that mesh.

The map skeleton (CMapRootElement / CMapWorld) is built from scratch — see
new_vmap() — rather than cloned from a bundled empty template, which the
installed build could not always locate. Falls back to keyvalues2 text
encoding if binary saving is unavailable.
"""

import os
import random
from typing import Callable, Iterable, Optional

from src.dotnet import setup_keyvalues2
from .transform import convert_transform, mirror_placement, UETransform, UnitScale
from .vmdl_writer import ue_mesh_to_model_path, mirrored_model_path
from .light_entities import (
    ue_actor_to_entity, LIGHT_COMPONENTS, SKY_COMPONENTS, CUBEMAP_COMPONENTS,
)
from . import decal_template as DT

# Component types whose component-level transform is the world transform of a
# single placed mesh. Instanced/foliage/spline components need per-instance or
# spline handling and are reported separately, not emitted here.
_SIMPLE_COMPONENT = "StaticMeshComponent"

# prop_static's own fields; `model` is filled in per placement.
_PROP_STATIC = {
    "classname": "prop_static",
    "model": "",
    "skin": "default",
    "solid": "6",
    "rendercolor": "255 255 255",
    "disableshadows": "0",
}

# worldspawn defaults, as Hammer writes them into an empty map.
_WORLDSPAWN = {
    "classname": "worldspawn",
    "targetname": "",
    "skyname": "sky_day01_01",
    "startdark": "0",
    "startcolor": "0 0 0",
    "pvstype": "0",
    "newunit": "0",
    "maxpropscreenwidth": "-1",
    "minpropscreenwidth": "0",
    "vrchaperone": "0",
    "vrmovement": "0",
    "baked_light_index_min": "0",
    "baked_light_index_max": "256",
    "max_lightmap_resolution": "0",
    "lightmap_queries": "1",
    "steamaudio_reverb_rebake_option": "1",
    "steamaudio_reverb_grid_type": "0",
    "steamaudio_reverb_grid_spacing": "6",
    "steamaudio_reverb_height_above_floor": "1.5",
    "steamaudio_reverb_rays": "32768",
    "steamaudio_reverb_bounces": "32",
    "steamaudio_reverb_ir_duration": "1.0",
    "steamaudio_reverb_ambisonic_order": "1",
    "steamaudio_pathing_rebake_option": "1",
    "steamaudio_pathing_grid_type": "0",
    "steamaudio_pathing_grid_spacing": "6",
    "steamaudio_pathing_height_above_floor": "1.5",
    "steamaudio_pathing_visibility_samples": "1",
    "steamaudio_pathing_visibility_radius": "0.0",
    "steamaudio_pathing_visibility_threshold": "0.1",
    "steamaudio_pathing_visibility_pathrange": "100.0",
    "prefab_has_runtime_entity_by_default": "0",
}


def actor_transform(actor: dict, unit_scale: float = UnitScale.ONE_TO_ONE):
    """One actor/component dict from the bridge's dump-scene -> SourceTransform.

    The single point where a placed scene actor crosses from UE space into
    Source space, so the axis convention is asserted in one place (see demo()).
    """
    loc = actor["location"]
    rot = actor["rotation"]
    scl = actor["scale"]
    return convert_transform(
        UETransform(
            (loc["x"], loc["y"], loc["z"]),
            (rot["pitch"], rot["yaw"], rot["roll"]),
            (scl["x"], scl["y"], scl["z"]),
        ),
        unit_scale=unit_scale,
    )


def new_vmap():
    """An empty binary vmap v40 (CMapRootElement + CMapWorld), built in code.

    Same skeleton Hammer writes for File > New, minus the stored camera and
    the default world children. Returns (datamodel, world element); callers
    append to world["children"] and Save().
    """
    Datamodel, Element, _ = setup_keyvalues2()
    import Datamodel as DM
    import System
    from System.Numerics import Vector3

    dm = DM.Datamodel("vmap", 40)
    root = Element(dm, "", None, "CMapRootElement")
    dm.Root = root

    def E(cls):
        return Element(dm, "", None, cls)

    def node_defaults(el, node_id):
        """The CMapNode fields every node in the tree carries."""
        el["nodeID"] = System.Int32(node_id)
        el["referenceID"] = System.UInt64(0)
        el["children"] = DM.ElementArray()
        el["variableTargetKeys"] = DM.StringArray()
        el["variableNames"] = DM.StringArray()
        el["origin"] = Vector3(0.0, 0.0, 0.0)
        el["angles"] = DM.QAngle(0.0, 0.0, 0.0)
        el["scales"] = Vector3(1.0, 1.0, 1.0)
        el["transformLocked"] = False
        el["force_hidden"] = False
        el["editorOnly"] = False
        return el

    plug_list = E("DmePlugList")
    plug_list["names"] = DM.StringArray()
    plug_list["dataTypes"] = DM.IntArray()
    plug_list["plugTypes"] = DM.IntArray()
    plug_list["descriptions"] = DM.StringArray()

    worldspawn = E("EditGameClassProps")
    for k, v in _WORLDSPAWN.items():
        worldspawn[k] = v

    world = node_defaults(E("CMapWorld"), 1)
    world["relayPlugData"] = plug_list
    world["connectionsData"] = DM.ElementArray()
    world["entity_properties"] = worldspawn
    world["nextDecalID"] = System.Int32(0)
    world["fixupEntityNames"] = True
    world["mapUsageType"] = "standard"

    visibility = node_defaults(E("CVisibilityMgr"), 0)
    visibility["nodes"] = DM.ElementArray()
    visibility["hiddenFlags"] = DM.IntArray()

    variables = E("CMapVariableSet")
    for k in ("variableNames", "variableValues", "variableTypeNames", "variableTypeParameters"):
        variables[k] = DM.StringArray()
    variables["m_ChoiceGroups"] = DM.ElementArray()

    selection_set = E("CMapSelectionSet")
    selection_set["children"] = DM.ElementArray()
    selection_set["selectionSetName"] = ""
    selection_set["selectionSetData"] = None

    camera = E("CStoredCamera")
    camera["position"] = Vector3(0.0, -1000.0, 1000.0)
    camera["lookat"] = Vector3(0.0, 0.0, 0.0)

    cameras = E("CStoredCameras")
    cameras["activecamera"] = System.Int32(-1)
    cameras["cameras"] = DM.ElementArray()

    root["isprefab"] = False
    root["editorbuild"] = System.Int32(10430)
    root["editorversion"] = System.Int32(400)
    root["itemFile"] = ""
    root["defaultcamera"] = camera
    root["3dcameras"] = cameras
    root["world"] = world
    root["visbility"] = visibility          # sic — Hammer's spelling
    root["mapVariables"] = variables
    root["rootSelectionSet"] = selection_set
    root["m_ReferencedMeshSnapshots"] = DM.ElementArray()
    root["m_bIsCordoning"] = False
    root["m_bCordonsVisible"] = False
    root["nodeInstanceData"] = DM.ElementArray()
    return dm, world


class VmapWriteResult:
    def __init__(self):
        self.placed = 0
        self.placed_smartprops = 0
        self.placed_decals = 0
        self.placed_lights = 0
        self.placed_sky = 0
        self.placed_cubemaps = 0
        self.skipped = 0
        self.skipped_types = {}   # componentType -> count
        self.models = set()       # source model paths referenced
        self.decal_materials = set()  # UE decal material paths referenced
        # (UE mesh, mirror axes) pairs placed with a handedness-flipping scale.
        # Each distinct pair needs its own mirrored vmdl alongside the normal
        # one — the same mesh mirrored on X and on Z are two different models.
        self.mirrored_meshes = set()

    def note_skip(self, comp_type):
        self.skipped += 1
        self.skipped_types[comp_type] = self.skipped_types.get(comp_type, 0) + 1


def write_vmap(
    actors: Iterable[dict],
    output_path: str,
    model_resolver: Optional[Callable[[str], str]] = None,
    unit_scale: float = UnitScale.ONE_TO_ONE,
    strip_prefix: bool = True,
    import_lights: bool = False,
    import_sky: bool = False,
    import_cubemaps: bool = False,
    import_decals: bool = True,
    mirror_negative_scale: bool = True,
) -> VmapWriteResult:
    """
    Write a .vmap of prop_static entities from normalized scene actors.

    actors          : dicts with keys actor, componentType, mesh, location,
                      rotation, scale (UE space) — i.e. dump-scene output.
    model_resolver  : maps a UE mesh path to a Source model path; defaults to
                      ue_mesh_to_model_path.
    unit_scale      : UE→Source unit multiplier (shared with the vmdl import scale).

    The import_* flags are the Map settings: each gates one class of actor, and
    a disabled class is counted as skipped rather than dropped silently.
    mirror_negative_scale points handedness-flipping placements at a mirrored
    copy of their model (collected in result.mirrored_meshes for the caller to
    write) instead of placing the original inside-out.
    """
    if model_resolver is None:
        model_resolver = lambda mesh: ue_mesh_to_model_path(mesh, strip_prefix=strip_prefix)

    Datamodel, Element, DeferredMode = setup_keyvalues2()
    import Datamodel as DM
    import System
    from System.Numerics import Vector2, Vector3, Vector4

    dm, world = new_vmap()

    def E(name, cls):
        return Element(dm, name, None, cls)

    def empty_pluglist():
        p = E("", "DmePlugList")
        p["names"] = DM.StringArray()
        p["dataTypes"] = DM.IntArray()
        p["plugTypes"] = DM.IntArray()
        p["descriptions"] = DM.StringArray()
        return p

    def make_entity(name, props, origin, angles, scales, node_id):
        """A CMapEntity carrying `props` as its EditGameClassProps.

        Every point entity the converter emits — prop_static, lights, sky,
        cubemap volumes — is this element with a different property dict, so
        the node boilerplate is written once.
        """
        ep = E("", "EditGameClassProps")
        for k, v in props.items():
            ep[k] = v

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

    def make_prop(name, model, origin, angles, scales, node_id):
        return make_entity(name, dict(_PROP_STATIC, model=model),
                           origin, angles, scales, node_id)

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

    # componentType -> the Map setting that gates it. Anything not listed here
    # is geometry (or unsupported) and follows the mesh/blueprint path below.
    gated = {}
    for kinds, enabled in ((LIGHT_COMPONENTS, import_lights),
                           (SKY_COMPONENTS, import_sky),
                           (CUBEMAP_COMPONENTS, import_cubemaps),
                           (("DecalComponent",), import_decals)):
        for kind in kinds:
            gated[kind] = enabled

    for a in actors:
        comp = a.get("componentType", "")
        mesh = a.get("mesh")
        bp = a.get("blueprint")
        decal_material = a.get("material") if comp == "DecalComponent" else None

        if comp in gated:
            if not gated[comp]:
                result.note_skip(comp)  # switched off in Map settings
                continue
        elif comp != _SIMPLE_COMPONENT and comp != "BlueprintActor" and not bp:
            result.note_skip(comp)      # foliage/spline/instanced — handled elsewhere
            continue

        st = actor_transform(a, unit_scale)
        angles = st.angles
        scales = st.scales

        node_id += 1
        name = a.get("actor") or f"ent_{node_id}"

        entity = ue_actor_to_entity(a, unit_scale) if comp in gated else None
        if entity:
            _classname, props = entity
            children.Add(make_entity(name, props, st.origin, angles, scales, node_id))
            if comp in SKY_COMPONENTS:
                result.placed_sky += 1
            elif comp in CUBEMAP_COMPONENTS:
                result.placed_cubemaps += 1
            else:
                result.placed_lights += 1
        elif comp == "BlueprintActor" or bp:
            bp_name = bp or name
            from .vmdl_writer import strip_ue_prefix
            clean_bp_name = strip_ue_prefix(bp_name) if strip_prefix else bp_name
            smartprop_path = f"smartprops/{clean_bp_name.lower()}.vsmart"
            children.Add(make_smartprop(name, smartprop_path, st.origin, angles, st.scales, node_id))
            result.placed_smartprops += 1
        elif comp == "DecalComponent" and decal_material:
            from .material_converter import ue_material_to_vmat_path
            vmat_path = ue_material_to_vmat_path(decal_material, strip_prefix=strip_prefix)
            result.decal_materials.add(decal_material)
            children.Add(make_decal_overlay(name, vmat_path, st.origin, angles, st.scales, node_id))
            result.placed_decals += 1
        elif comp == _SIMPLE_COMPONENT and mesh:
            model = model_resolver(mesh)
            if mirror_negative_scale:
                # A negatively scaled prop_static renders inside-out in Source 2,
                # so the flip moves into a mirrored copy of the model and the
                # placement keeps its angles and drops the signs off its scale.
                angles, scales, mirror_axes = mirror_placement(angles, scales)
                if any(mirror_axes):
                    result.mirrored_meshes.add((mesh, mirror_axes))
                    model = mirrored_model_path(model, mirror_axes)
            result.models.add(model)
            children.Add(make_prop(name, model, st.origin, angles, scales, node_id))
            result.placed += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    try:
        dm.Save(output_path, "binary", 9)
    except Exception:
        dm.Save(output_path, "keyvalues2", 4)
    return result


def demo():
    """Pins the UE -> Source 2 axis convention at the vmap boundary.

    Runs without the DMX stack: actor_transform is the whole coordinate hop,
    everything after it is serialization. A wrong mirror axis still yields a
    correct yaw, so position and roll are what actually catch it here.
    """
    def actor(x=0.0, y=0.0, z=0.0, pitch=0.0, yaw=0.0, roll=0.0, s=1.0):
        return {"location": {"x": x, "y": y, "z": z},
                "rotation": {"pitch": pitch, "yaw": yaw, "roll": roll},
                "scale": {"x": s, "y": s, "z": s}}

    def rounded(v):
        return tuple(round(c, 6) + 0.0 for c in v)

    # UE mirrors Y on FBX export, so the scene must mirror Y too. An X mirror
    # would put this prop at (-300, 400, 50) — the point rotated 180 degrees
    # about the world Z axis, which is the bug this guards.
    st = actor_transform(actor(x=300, y=400, z=50))
    assert rounded(st.origin) == (300.0, -400.0, 50.0), st.origin

    # Yaw is negated. This alone does NOT prove the axis is right — both mirrors
    # agree on yaw — so it is checked alongside the position above.
    assert rounded(actor_transform(actor(yaw=90)).angles) == (0.0, -90.0, 0.0)
    assert rounded(actor_transform(actor(yaw=-135)).angles) == (0.0, 135.0, 0.0)

    # Pitch negates, roll does not. The X mirror gets both of these backwards.
    assert rounded(actor_transform(actor(pitch=30)).angles) == (-30.0, 0.0, 0.0)
    assert rounded(actor_transform(actor(roll=45)).angles) == (0.0, 0.0, 45.0)
    assert rounded(actor_transform(actor(pitch=20, yaw=60, roll=30)).angles) == (-20.0, -60.0, 30.0)

    # Unit scale applies to position only; a mirror never changes a magnitude.
    st = actor_transform(actor(x=254, y=254, z=254, s=2.0), unit_scale=UnitScale.CM_TO_INCH)
    assert rounded(st.origin) == (100.0, -100.0, 100.0), st.origin
    assert rounded(st.scales) == (2.0, 2.0, 2.0), st.scales

    # A mirrored placement must point at a different model than the original,
    # or every mirrored prop silently reuses the inside-out one.
    assert mirrored_model_path("models/props/barrel.vmdl", (True, False, False)) \
        == "models/props/barrel_mirror_x.vmdl"

    # The end-to-end mirror contract this writer relies on: a UE actor scaled
    # -1 on one axis places the mirrored model, unrotated, at positive scale.
    st = actor_transform(actor(x=100, y=200, z=50))
    _a, _s, axes = mirror_placement(st.angles, (-1.0, 1.0, 1.0))
    assert axes == (True, False, False) and _s == (1.0, 1.0, 1.0), (axes, _s)
    assert _a == st.angles, _a

    # The skeleton needs the DMX stack, so it is checked only where that loads.
    try:
        dm, world = new_vmap()
    except Exception as e:
        print(f"ok (skeleton skipped: {e})")
        return
    assert dm.Format == "vmap" and dm.FormatVersion == 40, (dm.Format, dm.FormatVersion)
    assert dm.Root.ClassName == "CMapRootElement"
    assert world.ClassName == "CMapWorld" and world["children"].Count == 0
    assert world["entity_properties"]["classname"] == "worldspawn"
    print("ok")


if __name__ == "__main__":
    demo()
