"""
vmdl writer — wraps a bulk-exported UE FBX in a Source 2 .vmdl.

A single per-asset FBX from UE's Bulk Export already contains the LOD render
meshes (``<Asset>_LOD0..N``) and the collision meshes (``UCX_<Asset>...``) as
separate mesh objects. Rather than physically splitting the FBX, the vmdl
references that one file and uses per-node ``import_filter`` selections to route
meshes: each LOD gets its own RenderMeshFile, and the PhysicsHullFile pulls the
UCX collision. The FBX is inspected directly (its mesh node names are readable
strings in the binary) so the filters are built from the real contents.

Output is modeldoc41 (matching current CS2 Hammer).
"""

import os
import re
from src.common import JsonToKv3, fast_deepcopy
from src.editors.assetgroup_maker.objects import DEFAULT_VMDL
from .transform import UnitScale
from .fbx_flatten import flatten_fbx, list_models

# modeldoc41 header (CS2). JsonToKv3(format='vmdl') emits modeldoc36; we swap the
# format token so ModelDoc opens the newer LOD/physics nodes.
_MODELDOC41_FORMAT = "format:modeldoc41:version{12fc9d44-453a-4ae4-b4d9-7e2ac0bbd4e0}"

_DEFAULT_SIMPLIFY = {
    "targetTrianglePercent": 0.5, "targetError": 0.01, "attributeAware": True,
    "normalWeight": 1.25, "uvWeight": 0.5, "jointWeightWeight": 1.0, "colorWeight": 0.0,
    "lockBorder": False, "removeSmallComponents": False, "smallComponentSize": 0.025,
    "weldVertices": True, "weldPositionTolerance": 0.001, "visualizeEdges": False,
    "recomputeVertices": False, "regularization": "default", "permissive": False,
    "prune": False,
}


# Epic's asset-name type prefixes. Source 2 content carries none of them, so all
# of them go — including stacked ones like "SM_MI_Foo".
_UE_PREFIXES = (
    "SM", "SKM", "SK",                              # meshes
    "M", "MI", "MID", "MM", "MF", "MPC",            # materials
    "T", "TX", "TEX", "RT",                         # textures
    "BP", "BPI", "ABP", "WBP",                      # blueprints
    "UCX", "UBX", "USP", "UCP", "PHYS", "PA",       # collision / physics
    "PS", "NS", "NE", "NM", "FX", "VFX",            # particles
    "AM", "AS", "BS", "ANIM",                       # animation
    "SW", "SC", "MS", "CUE", "SFX",                 # audio
    "DA", "DT", "CRV",                              # data
)
# Single letters beyond M_/T_ (A_, S_, E_, L_) are deliberately absent: they eat
# real words ("SM_A_Frame" -> "frame") for prefixes barely anyone uses.
_UE_PREFIX_RE = re.compile(r"^(?:(?:%s)_)+" % "|".join(_UE_PREFIXES), re.IGNORECASE)
# Unreal's type suffixes. Texture channel suffixes (_ALB, _N, _ORM) are NOT in
# here — they are what keeps a material's exported maps in separate files.
_UE_SUFFIX_RE = re.compile(r"(?:_(?:inst|instance|mat))+$", re.IGNORECASE)


def strip_ue_prefix(name: str) -> str:
    """Unreal asset name -> Source 2 naming style.

    Drops the standard type prefix (SM_, BP_, T_, M_, MI_, SK_, …) and the
    _Inst-style suffix, then breaks PascalCase into snake_case: "SM_ChairLeg" ->
    "chair_leg". Source 2 content paths are lowercase by convention, and without
    the word split everything collapses into unreadable runs like "chairleg".

    The single choke point for the naming option — vmdl paths, vmat paths,
    texture names, vsmart names and vmap references all route through here.
    """
    if not name:
        return name
    stripped = _UE_SUFFIX_RE.sub("", _UE_PREFIX_RE.sub("", name))
    # A name that is nothing but prefixes ("T_MI") keeps its original spelling
    # rather than converting to an empty filename.
    name = stripped if stripped.strip("_") else name
    # Split acronym boundaries before word boundaries, so "HTTPServer" becomes
    # "http_server" rather than "httpserver".
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    name = re.sub(r"[\s\-]+", "_", name)
    return re.sub(r"_+", "_", name).strip("_").lower()


def ue_mesh_to_model_path(ue_mesh_path: str, models_root: str = "models", strip_prefix: bool = True) -> str:
    """
    "/Game/FireWatchTower/Meshes/SM_Barrel.SM_Barrel"
        -> "models/firewatchtower/meshes/sm_barrel.vmdl" (or barrel.vmdl if strip_prefix=True)
    """
    if "'" in ue_mesh_path:
        match = re.search(r"'(.*?)'", ue_mesh_path)
        if match:
            ue_mesh_path = match.group(1)
    ue_mesh_path = ue_mesh_path.strip()

    p = ue_mesh_path.replace("\\", "/").strip("/")
    if p.lower().endswith(".vmdl"):
        p = p[:-5]
    p = p.split(".", 1)[0]
    p = re.sub(r"^/?[Gg]ame/", "", p).strip("/")
    if p.lower().startswith(f"{models_root.lower()}/"):
        p = p[len(models_root):].strip("/")

    parts = p.rsplit("/", 1)
    if len(parts) == 2:
        folder, filename = parts[0], parts[1]
        if strip_prefix:
            filename = strip_ue_prefix(filename)
        p = f"{folder}/{filename}"
    elif strip_prefix:
        p = strip_ue_prefix(p)

    return f"{models_root}/{p}.vmdl".lower()


def find_bulk_export_mesh(bulk_dir: str, ue_mesh_path: str):
    """Locate the bulk-exported mesh file for a UE mesh ref by asset stem."""
    if not bulk_dir or not os.path.exists(bulk_dir):
        return None

    if "'" in ue_mesh_path:
        match = re.search(r"'(.*?)'", ue_mesh_path)
        if match:
            ue_mesh_path = match.group(1)
    ue_mesh_path = ue_mesh_path.strip()

    clean_path = ue_mesh_path.replace("\\", "/")
    if clean_path.lower().endswith(".vmdl"):
        clean_path = clean_path[:-5]

    stem = clean_path.split(".", 1)[0].rstrip("/").rsplit("/", 1)[-1].lower()
    stripped_stem = strip_ue_prefix(stem)
    norm_stem = re.sub(r'[^a-z0-9]', '', stem)

    norm_match = None

    for root, _dirs, files in os.walk(bulk_dir):
        for fn in files:
            name, ext = os.path.splitext(fn)
            if ext.lower() not in (".fbx", ".obj", ".gltf", ".glb", ".dmx"):
                continue
            name_lower = name.lower()
            if name_lower == stem or strip_ue_prefix(name) == stripped_stem:
                return os.path.join(root, fn)
            norm_name = re.sub(r'[^a-z0-9]', '', name_lower)
            if norm_name == norm_stem and not norm_match:
                norm_match = os.path.join(root, fn)

    return norm_match


def inspect_fbx_meshes(fbx_path: str) -> dict:
    """
    Extract mesh node names from a binary FBX by parsing its node structure.

    Uses list_models() to read actual Model node names directly from the FBX
    binary format. Non-binary files (ASCII FBX, OBJ, etc.) or unreadable files
    return empty info so write_vmdl falls back to a plain single-mesh wrapper.

    Returns {"lods": [primary LOD names], "lod_filters": [[exact mesh per LOD]],
             "collision": [UCX/UBX names], "base": <asset base name or None>}.
    """
    _empty = {"lods": [], "lod_filters": [], "collision": [], "base": None}

    if not fbx_path:
        return _empty

    try:
        raw_models = list_models(fbx_path)
    except Exception:
        return _empty

    if raw_models is None:
        # list_models returns None for non-binary-FBX files — no node names to use.
        return _empty

    # Use only true Mesh subtype nodes — the actual renderable geometry nodes.
    collision = []
    render_names = []
    for name, sub in raw_models:
        if sub != "Mesh":
            continue
        if name.upper().startswith(("UCX_", "UBX_", "USP_", "UCP_")):
            collision.append(name)
        else:
            render_names.append(name)

    collision = sorted(set(collision))

    # Group render meshes by LOD index from their _LODn suffix.
    lod_map = {}   # lod_idx -> [names]
    non_lod_names = []

    for n in render_names:
        m = re.search(r"_LOD(\d+)$", n, re.I)
        if m:
            lod_map.setdefault(int(m.group(1)), []).append(n)
        else:
            non_lod_names.append(n)

    # Some UE exports have a bare base name as the "LOD0" mesh (no _LOD0 suffix)
    # when LOD1+ are also present. Slot it into index 0.
    if non_lod_names and lod_map and 0 not in lod_map:
        lod_map[0] = [sorted(non_lod_names, key=len)[0]]

    if not lod_map:
        base = sorted(non_lod_names, key=len)[0] if non_lod_names else None
        return {"lods": [], "lod_filters": [], "collision": collision, "base": base}

    sorted_indices = sorted(lod_map.keys())
    primary_lods = [sorted(lod_map[i])[0] for i in sorted_indices]
    base = re.sub(r"_LOD\d+$", "", primary_lods[0], flags=re.I)

    # Exactly 1 mesh node name per LOD — taken directly from the FBX node list.
    lod_filters = [[primary_lods[i]] for i in range(len(sorted_indices))]

    return {
        "lods": primary_lods,
        "lod_filters": lod_filters,
        "collision": collision,
        "base": base,
    }


def _import_filter(exclude_by_default: bool, exception_list):
    return {"exclude_by_default": exclude_by_default, "exception_list": list(exception_list)}


def clean_material_stem(name: str) -> str:
    """
    Strips the Unreal type prefix and the texture channel suffix, plus the
    extension if present.
    e.g., 'mi_rock_3' -> 'rock_3', 'MI_Wood_01.vmat' -> 'wood_01', 't_wood_d' -> 'wood'

    No PascalCase split here (unlike strip_ue_prefix): this is a lookup key and
    _ENGINE_MATERIALS is matched against it.
    """
    if not name:
        return ""
    stem = name.rsplit(".", 1)[0].strip()
    clean = _UE_PREFIX_RE.sub("", stem)
    clean = re.sub(r"_(d|bc|color|albedo|diffuse|nrm|n|normal|rough|r|metal|m|ao|orm|rma)$", "", clean, flags=re.IGNORECASE)
    return clean.strip().lower()


def _match_key(name: str) -> str:
    """Separator-free lookup key, so an FBX's "MI_RockWall" still finds the
    Source-2-named "rock_wall.vmat" the material pass wrote."""
    return re.sub(r"[^a-z0-9]", "", clean_material_stem(name))


# CS2 stand-in for a slot we cannot convert.
GRAYBOX_VMAT = "materials/dev/reflectivity_20b.vmat"

# UE's built-in materials. They live in the engine install, not the project, so
# no amount of scoping or exporting will ever produce a vmat for them — a mesh
# with an unassigned slot carries WorldGridMaterial, and every engine mesh
# carries DefaultMaterial. Remapping them to the graybox is the only honest
# answer; without it the vmdl points each one at a vmat nothing writes.
_ENGINE_MATERIALS = frozenset((
    "defaultmaterial",
    "worldgridmaterial",
    "basicshapematerial",
    "defaultdeferreddecalmaterial",
))


def _is_real_vmat(filepath: str) -> bool:
    """True if a .vmat file contains real texture references rather than default stand-ins."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            c = f.read(2048).lower()
        return "default_color.tga" not in c and "default_color" not in c
    except Exception:
        return False


def resolve_material_remaps(fbx_path: str = None, output_dir: str = None, model_rel_path: str = None, default_mat_path: str = None) -> list:
    """
    Inspects fbx_path for embedded FBX material names (e.g. 'mi_rock_3').
    Strips mi_, m_, mm_, t_ prefixes to find material stems.
    Searches output_dir/materials/ for matching .vmat files.
    Returns remaps list for DefaultMaterialGroup:
    [
        {"from": "mi_rock_3.vmat", "to": "materials/firewatch/rock_3.vmat"}
    ]
    """
    from .fbx_flatten import list_materials
    embedded_mats = list_materials(fbx_path) if (fbx_path and os.path.isfile(fbx_path)) else []
    remaps = []

    vmat_lookup = {}
    vmat_quality = {}
    if output_dir:
        mats_root = os.path.join(output_dir, "materials")
        if os.path.exists(mats_root):
            for root, _dirs, files in os.walk(mats_root):
                for f in files:
                    if f.lower().endswith(".vmat"):
                        full_p = os.path.join(root, f)
                        rel_p = os.path.relpath(full_p, output_dir).replace("\\", "/").lower()
                        q = 2 if _is_real_vmat(full_p) else 1
                        stems = [clean_material_stem(f), _match_key(f), f[:-5].lower()]
                        for st in stems:
                            if not st:
                                continue
                            if st not in vmat_lookup or q > vmat_quality.get(st, 0):
                                vmat_lookup[st] = rel_p
                                vmat_quality[st] = q

    if embedded_mats:
        for raw_mat in embedded_mats:
            from_name = raw_mat if raw_mat.lower().endswith(".vmat") else f"{raw_mat}.vmat"
            stem = clean_material_stem(raw_mat)
            raw_clean = raw_mat.lower()

            to_path = (vmat_lookup.get(stem) or vmat_lookup.get(raw_clean)
                       or vmat_lookup.get(_match_key(raw_mat)))
            # After the project lookup: a converted material of the same name
            # still wins over the stand-in.
            if not to_path and stem in _ENGINE_MATERIALS:
                to_path = GRAYBOX_VMAT

            if not to_path:
                # Nothing on disk yet — guess the name the material pass would
                # write, i.e. the same Source 2 spelling ue_material_to_vmat_path
                # produces.
                guess = strip_ue_prefix(raw_mat.rsplit(".", 1)[0]) or stem
                if model_rel_path:
                    cat_dir = os.path.dirname(model_rel_path).replace("models/", "materials/").replace("models", "materials")
                    to_path = f"{cat_dir}/{guess}.vmat".lower()
                elif default_mat_path:
                    to_path = default_mat_path.replace("\\", "/").lower()
                else:
                    to_path = f"materials/{stem}.vmat"

            remaps.append({
                "from": from_name,
                "to": to_path
            })

    if not remaps:
        if default_mat_path:
            remaps.append({"from": "*", "to": default_mat_path.replace("\\", "/").lower()})
        elif model_rel_path:
            fallback_mat = model_rel_path.replace("models/", "materials/").replace(".vmdl", ".vmat").lower()
            remaps.append({"from": "*", "to": fallback_mat})

    return remaps


def apply_import_options(mesh_info: dict, import_lods: bool = True, import_collision: bool = True) -> dict:
    """Narrow what inspect_fbx_meshes found to what the user asked to import."""
    if import_lods and import_collision:
        return mesh_info
    trimmed = dict(mesh_info)
    if not import_lods:
        # Keep LOD0 rather than clearing: see write_vmdl's note on stacking.
        trimmed["lods"] = (trimmed.get("lods") or [])[:1]
        trimmed["lod_filters"] = (trimmed.get("lod_filters") or [])[:1]
    if not import_collision:
        trimmed["collision"] = []
    return trimmed


def _build_vmdl_dict(mesh_rel_path, import_scale, mesh_info, material_remaps=None, use_graybox_fallback=False):
    """Build the modeldoc rootNode dict with LOD + physics from mesh_info."""
    lods = mesh_info.get("lods") or []
    lod_filters = mesh_info.get("lod_filters") or []
    collision = mesh_info.get("collision") or []
    base = mesh_info.get("base") or os.path.splitext(os.path.basename(mesh_rel_path))[0]

    render_children = []
    lod_groups = []
    if lods:
        for i, lod_name in enumerate(lods):
            ref = f"lod{i}"
            exceptions = lod_filters[i] if (lod_filters and i < len(lod_filters)) else [lod_name]
            render_children.append({
                "_class": "RenderMeshFile",
                "name": ref,
                "filename": mesh_rel_path,
                "import_scale": float(import_scale),
                "import_filter": _import_filter(True, exceptions),
            })
            lod_groups.append({
                "_class": "LODGroup",
                "mesh_references": [{
                    "mesh_name": ref,
                    "copy_and_simplify": False,
                    "simplify_params": dict(_DEFAULT_SIMPLIFY),
                }],
                "switch_threshold": float(i * 60),   # LOD0=0, LOD1=60, LOD2=120…
            })
    else:
        # Single-mesh fbx: one render mesh. Exclude any UCX collision meshes so
        # they don't render (they still feed the physics hull below).
        render_children.append({
            "_class": "RenderMeshFile",
            "name": "mesh0",
            "filename": mesh_rel_path,
            "import_scale": float(import_scale),
            "import_filter": _import_filter(False, collision),
        })

    # Physics: prefer UCX collision; else hull LOD0 / the whole mesh.
    if collision:
        phys_filter = _import_filter(True, collision)           # import only UCX
    elif lods:
        phys_exceptions = lod_filters[0] if lod_filters else [lods[0]]
        phys_filter = _import_filter(True, phys_exceptions)     # hull from LOD0
    else:
        phys_filter = _import_filter(False, [])                 # hull whole mesh

    physics_hull = {
        "_class": "PhysicsHullFile",
        "name": base,
        "parent_bone": "",
        "surface_prop": "default",
        "collision_prop": "default",
        "tool_material": "",
        "recenter_on_parent_bone": False,
        "offset_origin": [0.0, 0.0, 0.0],
        "offset_angles": [0.0, 0.0, 0.0],
        "filename": mesh_rel_path,
        "import_scale": float(import_scale),
        "faceMergeAngle": 5.0,
        "maxHullVertices": 64,
        "import_mode": "HullPerElement",
        "small_element_threshold": 0.0,
        "thin_element_threshold": 0.0,
        "optimization_algorithm": "QEM",
        "disable_region_svm": False,
        "import_filter": phys_filter,
    }

    if use_graybox_fallback:
        mat_group = {
            "_class": "DefaultMaterialGroup",
            "name": "",
            "remaps": material_remaps or [],
            "use_global_default": True,
            "global_default_material": GRAYBOX_VMAT,
        }
    elif material_remaps:
        mat_group = {
            "_class": "DefaultMaterialGroup",
            "name": "",
            "remaps": material_remaps,
            "use_global_default": False,
            "global_default_material": "",
        }
    else:
        mat_group = {
            "_class": "DefaultMaterialGroup",
            "remaps": [],
            "use_global_default": True,
            "global_default_material": GRAYBOX_VMAT,
        }

    children = []
    if lod_groups:
        children.append({"_class": "LODGroupList", "children": lod_groups})
    children.append({
        "_class": "MaterialGroupList",
        "children": [mat_group],
    })
    children.append({
        "_class": "PhysicsShapeList",
        "children": [physics_hull],
        "leave_body_collision_unmodified": False,
        "body_order": "default",
    })
    children.append({"_class": "RenderMeshList", "children": render_children})

    return {
        "rootNode": {
            "_class": "RootNode",
            "children": children,
            "model_archetype": "",
            "primary_associated_entity": "",
            "anim_graph_name": "",
            "document_sub_type": "ModelDocSubType_None",
        }
    }


def write_vmdl(output_path: str, mesh_rel_path: str,
               import_scale: float = UnitScale.ONE_TO_ONE,
               fbx_path: str = None,
               material_path: str = None,
               output_dir: str = None,
               use_graybox_fallback: bool = False,
               import_lods: bool = True,
               import_collision: bool = True,
               strip_prefix: bool = True) -> str:
    """
    Write a .vmdl at output_path referencing mesh_rel_path (relative to the addon
    content root, forward slashes). If fbx_path is given, the FBX is inspected to
    build per-LOD render meshes and UCX physics; otherwise a simple single-mesh
    vmdl is written. FBX files are automatically flattened in place.
    If material_path or output_dir is provided, material remapping will be set directly on the material group.

    import_lods=False keeps LOD0 only — dropping the LOD list entirely would fall
    through to the single-mesh path, which imports every mesh in the FBX and so
    would render all the LODs stacked on top of each other.
    import_collision=False discards the UCX/UBX hulls, leaving the physics hull
    to be generated from the render mesh as it is for any FBX without them.
    """
    mesh_rel_path = mesh_rel_path.replace("\\", "/")
    mesh_info = {}

    if fbx_path and os.path.isfile(fbx_path):
        try:
            flatten_fbx(fbx_path, strip_prefix=strip_prefix)
        except Exception:
            pass
        mesh_info = inspect_fbx_meshes(fbx_path)
        mesh_info = apply_import_options(mesh_info, import_lods, import_collision)

    material_remaps = None
    if material_path or fbx_path or output_dir:
        material_remaps = resolve_material_remaps(
            fbx_path=fbx_path,
            output_dir=output_dir,
            model_rel_path=mesh_rel_path,
            default_mat_path=material_path
        )
        if output_dir and material_remaps:
            from .vmat_writer import write_vmat
            for remap in material_remaps:
                to_path = remap.get("to")
                if to_path and not to_path.startswith("materials/dev/") and not to_path.startswith("materials/default/"):
                    abs_vmat_path = os.path.join(output_dir, to_path)
                    if not os.path.exists(abs_vmat_path):
                        try:
                            write_vmat(abs_vmat_path, {})
                        except Exception:
                            pass

    vmdl = _build_vmdl_dict(mesh_rel_path, import_scale, mesh_info, material_remaps=material_remaps, use_graybox_fallback=use_graybox_fallback)

    content = JsonToKv3(vmdl, format="vmdl")
    # Upgrade the header format token modeldoc36 -> modeldoc41.
    content = re.sub(r"format:modeldoc\d+:version\{[0-9a-f-]+\}", _MODELDOC41_FORMAT, content, count=1)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)
    return output_path


def demo():
    import tempfile

    # No UE type prefix or _Inst suffix survives, stacked ones included.
    assert strip_ue_prefix("MI_RockWall_Inst") == "rock_wall"
    assert strip_ue_prefix("T_Rock_ALB") == "rock_alb"
    assert strip_ue_prefix("MM_MasterFoliage") == "master_foliage"
    assert strip_ue_prefix("SM_MI_Barrel") == "barrel"
    assert strip_ue_prefix("TX_Concrete") == "concrete"
    # Prefix-only names keep their spelling instead of becoming "".
    assert strip_ue_prefix("MI_") == "mi"
    # A word that merely starts like a prefix is not one.
    assert strip_ue_prefix("Metal_Beam") == "metal_beam"

    from .material_converter import ue_material_to_vmat_path
    assert ue_material_to_vmat_path(
        "/Game/FireWatchTower/Materials/Material_Instances/MI_RockWall.MI_RockWall",
        strip_prefix=True) == "materials/firewatchtower/rock_wall.vmat"

    # Engine content keeps its mount in the output path — this is the exact
    # string a converted UE template map places in its vmap.
    assert ue_mesh_to_model_path(
        "/Engine/MapTemplates/SM_Template_Map_Floor.SM_Template_Map_Floor", strip_prefix=True
    ) == "models/engine/maptemplates/template_map_floor.vmdl"

    # The bundled BasicShapes really do carry WorldGridMaterial (the engine
    # meshes carry DefaultMaterial), and neither will ever have a vmat.
    cube = os.path.join(os.path.dirname(__file__), "assets", "basicshapes", "cube.fbx")
    remaps = resolve_material_remaps(fbx_path=cube, model_rel_path="models/engine/basicshapes/cube.vmdl")
    assert remaps == [{"from": "WorldGridMaterial.vmat", "to": GRAYBOX_VMAT}], remaps

    # ...but a converted material of the same name still wins over the stand-in.
    with tempfile.TemporaryDirectory() as out:
        mats = os.path.join(out, "materials", "proj")
        os.makedirs(mats)
        open(os.path.join(mats, "worldgridmaterial.vmat"), "w").close()
        remaps = resolve_material_remaps(
            fbx_path=cube, output_dir=out, model_rel_path="models/engine/basicshapes/cube.vmdl")
        assert remaps == [{"from": "WorldGridMaterial.vmat",
                           "to": "materials/proj/worldgridmaterial.vmat"}], remaps

    print("ok")


if __name__ == "__main__":
    demo()

