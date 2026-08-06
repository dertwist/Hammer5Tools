"""
Worker that converts UE scenes (-> vmap) and models (-> vmdl) via the CUE4Parse
bridge + the vmap/vmdl writers. Runs off the UI thread and reports progress and
per-step feedback to the converter's console.
"""

import os
import re
import shutil
from PySide6.QtCore import QThread, Signal

from .asset_selection import asset_stem, ref_stem, key_to_object_path
from ._worker_base import CancellableWorker
from .bridge_client import UnrealBridge, BridgeError
from .vmap_writer import write_vmap
from .vsmart_writer import write_vsmart
from .vmdl_writer import (
    write_vmdl, ue_mesh_to_model_path, mirrored_model_path, find_bulk_export_mesh, GRAYBOX_VMAT,
)
from .engine_meshes import is_engine_mesh, generate_engine_mesh_obj, bundled_fbx_for

_MESH_EXTS = (".fbx", ".obj", ".gltf", ".glb", ".dmx")

# Synthetic mesh id prefix for landscape actors. Landscapes have no static-mesh
# asset to reference, so dump_scene's "Landscape" actor entries are rewritten
# (below) into ordinary StaticMeshComponent entries pointing at one of these —
# the rest of the vmap/vmdl pipeline then treats a landscape exactly like any
# other placed mesh, with the OBJ produced on demand via bridge.export_landscape.
_LANDSCAPE_MESH_PREFIX = "/H5T/Landscape/"


def _is_external_ref(key_or_ref) -> bool:
    """Does this reference point outside the project's /Game mount?

    UE object paths are rooted ("/Engine/MapTemplates/SM_Template_Map_Floor.…",
    "/H5T/Landscape/…"); the bridge's asset keys are relative file paths
    ("MyProj/Content/Meshes/SM_Chair.uasset"). Only the former can be external.
    """
    ref = str(key_or_ref)
    if "'" in ref:                       # Class'/Game/Path/Name.Name'
        ref = ref.split("'", 2)[1] if ref.count("'") >= 2 else ref
    ref = ref.strip().replace("\\", "/").lower()
    return ref.startswith("/") and not ref.startswith("/game/")


_NON_MESH_PREFIXES = ("t_", "tx_", "tex_", "m_", "mi_", "mm_", "mf_", "cue_", "ns_", "ps_", "wbp_", "bpi_")
_NON_MESH_FOLDERS = ("/textures/", "/materials/", "/audio/", "/sounds/", "/particles/", "/ui/", "/widget/")


def _object_path_to_key(ue_object_path: str) -> str:
    """UE object path -> the asset key the bridge addresses packages by.

    "/Game/Kowloon/Meshes/Decals/D_Dirt_01.D_Dirt_01" -> "Kowloon/Meshes/Decals/D_Dirt_01"
    The bridge mounts Content as the root, so the /Game/ prefix and the
    trailing ".ObjectName" both have to come off — passing the object path
    through verbatim fails with "there is no game file with the path".
    """
    ref = str(ue_object_path or "")
    if "'" in ref:                       # Class'/Game/Path/Name.Name'
        ref = ref.split("'", 2)[1] if ref.count("'") >= 2 else ref
    ref = ref.strip().replace("\\", "/").split(".", 1)[0]
    return re.sub(r"^/?[Gg]ame/", "", ref).strip("/")


def _is_mesh_asset_path(path: str) -> bool:
    if not path:
        return False
    path_low = path.replace("\\", "/").lower()
    if any(f in path_low for f in _NON_MESH_FOLDERS):
        return False
    stem = os.path.basename(path_low).split(".", 1)[0]
    if any(stem.startswith(p) for p in _NON_MESH_PREFIXES):
        return False
    return True


class SceneModelsWorker(CancellableWorker):
    log = Signal(str, str)      # message, level (info/warn/error/success)
    progress = Signal(int, int)  # current, total
    done = Signal()

    def __init__(self, project_dir, bulk_dir, output_dir,
                 do_scenes, do_models, do_blueprints=False, do_materials=False, strip_prefix=True, unit_scale=1.0,
                 use_graybox_fallback=False, master_shaders=None, master_slot_overrides=None,
                 master_param_overrides=None, master_feature_flags=None, master_blend_modes=None,
                 selected_assets=None, import_lods=True, import_collision=True,
                 tex_format="tga", invert_y_normal=True,
                 import_lights=False, import_sky=False, import_cubemaps=False,
                 import_decals=True, mirror_negative_scale=True, parent=None):
        super().__init__(parent)
        self.import_lods = import_lods
        self.import_collision = import_collision
        # Map settings — which non-geometry actors a map converts, and whether
        # handedness-flipped placements get a mirrored copy of their model.
        self.import_lights = import_lights
        self.import_sky = import_sky
        self.import_cubemaps = import_cubemaps
        self.import_decals = import_decals
        self.mirror_negative_scale = mirror_negative_scale
        # (UE mesh, mirror axes) pairs some map placed with a negative scale;
        # each gets its own mirrored vmdl written in the Models stage.
        self._mirrored_meshes = set()
        # UE materials a decal actor referenced. Nothing else pulls these in —
        # the Materials stage works from the material names inside each mesh's
        # FBX, and a decal has no mesh — so without collecting them here every
        # decal-only material goes unconverted and its overlay lands in Hammer
        # pointing at a vmat that was never written.
        self._decal_materials = set()
        self.tex_format = tex_format
        self.invert_y_normal = invert_y_normal
        # Asset keys the user picked in the port scope dialog, already expanded
        # with their references. None means no filtering — port everything.
        self.selected_stems = (
            {asset_stem(k) for k in selected_assets} if selected_assets else None
        )
        self.selected_assets = list(selected_assets or ())
        # {master material name: chosen CS2 shader / slot / param overrides}
        # straight from the Materials tab. The shader is a property of the
        # Master Material, so every instance under it converts with the same one
        # instead of each re-guessing from its own name.
        self.master_shaders = master_shaders or {}
        self.master_slot_overrides = master_slot_overrides or {}
        self.master_param_overrides = master_param_overrides or {}
        self.master_feature_flags = master_feature_flags or {}
        self.master_blend_modes = master_blend_modes or {}
        self.project_dir = project_dir
        self.bulk_dir = bulk_dir
        self.output_dir = output_dir
        self.do_scenes = do_scenes
        self.do_models = do_models
        self.do_blueprints = do_blueprints
        self.do_materials = do_materials
        self.strip_prefix = strip_prefix
        self.unit_scale = unit_scale
        self.use_graybox_fallback = use_graybox_fallback
        self.bridge = None
        self._landscape_sources = {}   # synthetic mesh id -> map object path

    def _log(self, msg, level="info"):
        self.log.emit(msg, level)

    def _cancel_check(self) -> bool:
        """True if the worker was cancelled. Logs once so each abandoned stage
        explains why it stopped, instead of going silent mid-conversion."""
        if self.is_cancelled:
            self._log("Conversion cancelled by user.", "warn")
            return True
        return False

    def _write_vmdl(self, *args, **kwargs):
        """write_vmdl with the Models tab's import options applied.

        Five call sites; injecting here keeps them from drifting apart.
        """
        kwargs.setdefault("import_lods", self.import_lods)
        kwargs.setdefault("import_collision", self.import_collision)
        kwargs.setdefault("strip_prefix", self.strip_prefix)
        return write_vmdl(*args, **kwargs)

    def _wanted(self, key_or_ref) -> bool:
        """Is this asset in the user's port scope? True when no scope is set.

        Anything outside the project's /Game mount is always in scope. The scope
        is built from the project's own asset listing, so an engine mesh (the
        template map floor, a BasicShape) or a synthetic landscape id can never
        match it — filtering them meant the vmap placed a prop whose vmdl was
        then silently never written.
        """
        if self.selected_stems is None or _is_external_ref(key_or_ref):
            return True
        return ref_stem(key_or_ref) in self.selected_stems

    def _mirror_axes_for(self, mesh):
        """Every distinct mirror-axis set some map placed this mesh with."""
        return sorted(axes for m, axes in self._mirrored_meshes if m == mesh)

    def _warn_missing_actor_kinds(self, seen_kinds):
        """Say so when a Map setting is on but the scene read returned nothing
        it could apply to.

        A bridge built before lights were added reports those actors as nothing
        at all, so the setting silently does nothing — indistinguishable from a
        map that genuinely has no lights unless it is called out here.
        """
        from .light_entities import LIGHT_COMPONENTS, SKY_COMPONENTS, CUBEMAP_COMPONENTS

        for enabled, kinds, label in (
            (self.import_lights, LIGHT_COMPONENTS, "lights"),
            (self.import_sky, SKY_COMPONENTS, "sky"),
            (self.import_cubemaps, CUBEMAP_COMPONENTS, "cubemaps"),
        ):
            if enabled and not (set(kinds) & seen_kinds):
                self._log(
                    f"Import {label} is enabled but the scene read returned no such actors. "
                    f"Either the maps have none, or the CUE4Parse bridge predates this feature "
                    f"and needs rebuilding (src/net_core/UnrealBridge/README.md).",
                    "warn",
                )

    def _normalize_landscape_actors(self, actors, map_obj_path):
        """Rewrite dump_scene's "Landscape" actor entries (in place) into ordinary
        StaticMeshComponent entries pointing at a synthetic mesh id, so the rest
        of the vmap/vmdl pipeline places/builds them like any other mesh — but
        only if a matching bulk-exported FBX already exists. Without one, the
        landscape actor is left untouched so write_vmap skips it (no prop_static
        with a missing model) instead of placing a broken reference."""
        map_name = os.path.basename(map_obj_path)
        count = 0
        for a in actors:
            if a.get("componentType") != "Landscape":
                continue
            actor_name = a.get("landscapeActor") or a.get("actor") or "Landscape"
            mesh_id = f"{_LANDSCAPE_MESH_PREFIX}{map_name}_{actor_name}.{map_name}_{actor_name}"

            src_fbx = find_bulk_export_mesh(self.bulk_dir, mesh_id) if self.bulk_dir else None
            if not src_fbx:
                self._log(
                    f"{map_name}: landscape actor '{actor_name}' has no bulk-exported FBX "
                    f"('{actor_name}.fbx' or '{map_name}_{actor_name}.fbx' in the bulk-export dir) "
                    f"— skipped, no entity placed. Export it from Unreal (Landscape -> Convert to "
                    f"Static Mesh, then bulk-export like any other mesh) to have it converted.",
                    "warn",
                )
                continue

            self._landscape_sources[mesh_id] = map_obj_path
            a["mesh"] = mesh_id
            a["componentType"] = "StaticMeshComponent"
            count += 1
            self._log(f"{map_name}: landscape actor '{actor_name}' — bulk-exported FBX found, will be placed as a mesh", "info")
        return count

    def run(self):
        try:
            self._run()
        except Exception as e:  # never let the thread die silently
            self._log(f"Unexpected error: {e}", "error")
        finally:
            self.done.emit()

    def _run(self):
        # --- Print folder summary before doing anything ---
        self._log(f"UE Project  : {self.project_dir or '(none)'}", "info")
        self._log(f"Bulk Export : {self.bulk_dir or '(none)'}", "info")
        self._log(f"Output      : {self.output_dir}", "info")
        flags = []
        if self.do_scenes:     flags.append("Scenes→vmap")
        if self.do_models:     flags.append("Models→vmdl+fbx")
        if self.do_blueprints: flags.append("Blueprints→vsmart")
        self._log(f"Enabled     : {', '.join(flags) if flags else '(nothing)'}", "info")

        bridge = UnrealBridge(self.project_dir)
        self.bridge = bridge
        if not bridge.is_available():
            self._log("CUE4Parse bridge unavailable — " + bridge.why_unavailable(), "error")
            return
        # Which dll actually ran is the first thing to check when the bridge
        # returns something the current source says it should not.
        self._log(f"Bridge       : {bridge.dll}", "info")

        # Discover maps from the project.
        try:
            map_keys = [k for k in bridge.list("") if k.lower().endswith(".umap")]
        except BridgeError as e:
            self._log(str(e), "error")
            return

        if self.selected_stems is not None:
            in_scope = [k for k in map_keys if self._wanted(k)]
            self._log(
                f"Port scope: {len(self.selected_stems)} asset(s); "
                f"{len(in_scope)} of {len(map_keys)} map(s) included.", "info",
            )
            map_keys = in_scope

        self._log(f"Found {len(map_keys)} map(s): {', '.join(os.path.basename(m) for m in map_keys)}", "info")

        referenced_meshes = set()
        seen_kinds = set()

        # --- Scenes -> vmap ---
        if self.do_scenes:
            if not map_keys:
                self._log("No .umap files found in project.", "warn")
            for i, mk in enumerate(map_keys):
                if self._cancel_check():
                    return
                obj = mk[:-len(".umap")]
                name = os.path.basename(obj)
                self.progress.emit(i + 1, len(map_keys))
                try:
                    scene = bridge.dump_scene(obj)
                except BridgeError as e:
                    self._log(f"{name}: scene read failed — {e}", "error")
                    continue

                self._normalize_landscape_actors(scene["actors"], obj)
                seen_kinds.update(a.get("componentType", "") for a in scene["actors"])

                vmap_path = os.path.join(self.output_dir, "maps", f"{name}.vmap")
                res = write_vmap(
                    scene["actors"], vmap_path,
                    unit_scale=self.unit_scale, strip_prefix=self.strip_prefix,
                    import_lights=self.import_lights, import_sky=self.import_sky,
                    import_cubemaps=self.import_cubemaps, import_decals=self.import_decals,
                    mirror_negative_scale=self.mirror_negative_scale,
                )
                referenced_meshes.update(
                    a["mesh"] for a in scene["actors"]
                    if a.get("mesh") and a.get("componentType") == "StaticMeshComponent"
                )
                self._mirrored_meshes.update(res.mirrored_meshes)
                self._decal_materials.update(res.decal_materials)
                skip_note = ""
                if res.skipped:
                    skip_note = f" ({res.skipped} skipped: {res.skipped_types})"
                extras = [
                    (res.placed_smartprops, "smartprop"),
                    (res.placed_decals, "decal"),
                    (res.placed_lights, "light"),
                    (res.placed_sky, "sky"),
                    (res.placed_cubemaps, "cubemap"),
                    (len(res.mirrored_meshes), "mirrored model"),
                ]
                extra_note = "".join(f", {n} {label}" for n, label in extras if n)
                self._log(
                    f"{name}.vmap — {res.placed} prop_static{extra_note}, {len(res.models)} models{skip_note}",
                    "success",
                )
            self._warn_missing_actor_kinds(seen_kinds)
        else:
            # Models-only still needs the mesh list; pull it from the maps.
            for i, mk in enumerate(map_keys):
                if self._cancel_check():
                    return
                self.progress.emit(i + 1, len(map_keys))
                try:
                    obj = mk[:-len(".umap")]
                    scene = bridge.dump_scene(obj)
                    self._normalize_landscape_actors(scene["actors"], obj)
                    referenced_meshes.update(
                        a["mesh"] for a in scene["actors"]
                        if a.get("mesh") and a.get("componentType") == "StaticMeshComponent"
                    )
                except BridgeError:
                    pass

        # --- Blueprints -> vsmart ---
        if self.do_blueprints:
            self._log("Scanning blueprints…", "info")
            try:
                bp_keys = [k for k in bridge.list("") if k.lower().endswith(".uasset") and not k.lower().endswith(".umap")]
            except BridgeError as e:
                self._log(str(e), "error")
                bp_keys = []

            bp_count = 0
            if bp_keys:
                from .constants import scan_unsupported
                from .vmdl_writer import strip_ue_prefix
                _NON_BP_PREFIXES = (
                    "t_", "m_", "mi_", "mm_", "sm_", "sk_", "a_", "mf_", "mpc_", "sw_", "s_",
                    "fx_", "ns_", "ps_", "ls_", "ll_", "ft_", "fc_", "rvt_", "thumb"
                )
                _NON_BP_SUFFIXES = ("_foliagetype", "_layerinfo", "_svt", "_rvt")

                filtered_bp_keys = []
                for k in bp_keys:
                    fn = os.path.basename(k).lower()
                    if fn.startswith(_NON_BP_PREFIXES) or any(fn.removesuffix(".uasset").endswith(s) for s in _NON_BP_SUFFIXES):
                        continue
                    if not self._wanted(k):
                        continue
                    filtered_bp_keys.append(k)

                self._log(f"Blueprints — candidate assets to inspect: {len(filtered_bp_keys)} of {len(bp_keys)}", "info")

                for i, bk in enumerate(filtered_bp_keys):
                    if self._cancel_check():
                        return
                    self.progress.emit(i + 1, len(filtered_bp_keys))
                    obj = bk[:-len(".uasset")]
                    name = os.path.basename(obj)

                    if scan_unsupported([os.path.basename(bk)]).get("logic_blueprints"):
                        continue

                    try:
                        bp_data = bridge.dump_blueprint(obj)
                    except BridgeError:
                        continue

                    components = bp_data.get("components", [])
                    if not components:
                        continue

                    if not any(c.get("mesh") for c in components):
                        continue

                    clean_bp_name = strip_ue_prefix(name) if self.strip_prefix else name
                    vsmart_path = os.path.join(self.output_dir, "smartprops", f"{clean_bp_name.lower()}.vsmart")
                    res = write_vsmart(clean_bp_name, components, vsmart_path, unit_scale=self.unit_scale, strip_prefix=self.strip_prefix)
                    if res.placed > 0:
                        referenced_meshes.update(res.models)
                        bp_count += 1
                        self._log(
                            f"{clean_bp_name.lower()}.vsmart — {res.placed} model element(s) converted",
                            "success",
                        )

            if bp_count == 0 and self.do_blueprints:
                self._log("Blueprints — no content-assembly blueprints converted.", "info")

        # Fold the port scope into referenced_meshes BEFORE Materials runs.
        # Directly-picked meshes (no map/blueprint places them) must be in the
        # set when _convert_materials reads their FBX material names, or the
        # "no matching material instances" path fires and the materials that
        # every selected mesh actually uses never get converted.
        if self.selected_stems is not None:
            # Drop meshes the maps reference but the user left unticked...
            referenced_meshes = {m for m in referenced_meshes if self._wanted(m)}
            # ...and add meshes picked directly, which no map places. UE
            # exported an FBX for exactly the assets that are meshes, so the
            # bulk export is the type test.
            for key in self.selected_assets:
                obj = key_to_object_path(key)
                if obj in referenced_meshes:
                    continue
                if _is_mesh_asset_path(obj) and self.bulk_dir and find_bulk_export_mesh(self.bulk_dir, obj):
                    referenced_meshes.add(obj)

        # --- Materials -> vmat (before Models so vmdl remaps resolve to real vmats) ---
        if self.do_materials:
            self._convert_materials(referenced_meshes)

        # --- Models -> vmdl ---
        if self.do_models:
            self._log(f"Referenced meshes found: {len(referenced_meshes)}", "info")
            if not referenced_meshes:
                self._log("No referenced meshes to build vmdls for. Make sure Scenes is enabled or at least one map was scanned.", "warn")
            made, missing, engine, landscapes, mirrored = 0, 0, 0, 0, 0
            total = len(referenced_meshes)
            for i, mesh in enumerate(sorted(referenced_meshes)):
                if self._cancel_check():
                    return
                self.progress.emit(i + 1, total)
                model_rel = ue_mesh_to_model_path(mesh, strip_prefix=self.strip_prefix)                 # models/.../x.vmdl
                vmdl_path = os.path.join(self.output_dir, model_rel)
                mat_rel = os.path.splitext(model_rel)[0].replace("models/", "materials/") + ".vmat" if self.do_materials else None

                # Landscapes have no bulk-export FBX — the OBJ is generated on
                # demand by the bridge from the map's heightmap/component data.
                if mesh.startswith(_LANDSCAPE_MESH_PREFIX):
                    if self._build_landscape_model(mesh, vmdl_path, model_rel, mat_rel):
                        landscapes += 1
                        made += 1
                    continue

                # UE engine defaults (BasicShapes) have no project bulk-export —
                # use the real bundled engine FBX (falling back to a generated OBJ).
                # Their only material is an engine one, which never converts, so
                # the slot goes straight to the graybox rather than to a vmat
                # under materials/engine/ that nothing writes.
                if is_engine_mesh(mesh):
                    engine_mat = GRAYBOX_VMAT if self.do_materials else None
                    src = bundled_fbx_for(mesh)
                    if src:
                        fbx_rel = os.path.splitext(model_rel)[0] + ".fbx"
                        dst = os.path.join(self.output_dir, fbx_rel)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        self._write_vmdl(vmdl_path, fbx_rel, import_scale=self.unit_scale, fbx_path=dst, material_path=engine_mat, use_graybox_fallback=self.use_graybox_fallback)
                    else:
                        obj_rel = os.path.splitext(model_rel)[0] + ".obj"
                        generate_engine_mesh_obj(mesh, os.path.join(self.output_dir, obj_rel))
                        self._write_vmdl(vmdl_path, obj_rel, import_scale=self.unit_scale, material_path=engine_mat, use_graybox_fallback=self.use_graybox_fallback)
                    engine += 1
                    made += 1
                    continue

                mesh_rel = os.path.splitext(model_rel)[0] + ".fbx"      # models/.../x.fbx
                src_fbx = find_bulk_export_mesh(self.bulk_dir, mesh) if self.bulk_dir else None
                dst_fbx = None
                if src_fbx:
                    dst_fbx = os.path.join(self.output_dir, mesh_rel)
                    os.makedirs(os.path.dirname(dst_fbx), exist_ok=True)
                    try:
                        shutil.copy2(src_fbx, dst_fbx)
                        self._log(f"  {os.path.basename(src_fbx)} -> {mesh_rel}", "info")
                    except Exception as e:
                        self._log(f"  copy failed for {os.path.basename(src_fbx)}: {e}", "warn")
                        dst_fbx = None
                else:
                    missing += 1
                    stem = mesh.split(".", 1)[0].rsplit("/", 1)[-1]
                    self._log(
                        f"  {stem}: no FBX in bulk-export dir"
                        + (f" ({self.bulk_dir})" if self.bulk_dir else " (no bulk dir set)"),
                        "warn",
                    )

                # Inspect the copied FBX (or the source) to build LODs + physics.
                self._write_vmdl(vmdl_path, mesh_rel, import_scale=self.unit_scale,
                           fbx_path=dst_fbx or src_fbx, material_path=mat_rel, output_dir=self.output_dir,
                           use_graybox_fallback=self.use_graybox_fallback)
                made += 1

                # A map placed this mesh with a handedness-flipping scale, so it
                # also needs the mirrored twin(s) the vmap now references — one
                # per distinct axis set. All reference the same FBX; the mirror
                # is a ModelDoc modifier, so no second mesh is exported.
                for axes in self._mirror_axes_for(mesh):
                    self._write_vmdl(os.path.join(self.output_dir, mirrored_model_path(model_rel, axes)),
                               mesh_rel, import_scale=self.unit_scale,
                               fbx_path=dst_fbx or src_fbx, material_path=mat_rel,
                               output_dir=self.output_dir,
                               use_graybox_fallback=self.use_graybox_fallback, mirror_axes=axes)
                    mirrored += 1
                    made += 1

            parts = [f"{made} vmdl written"]
            if engine:
                parts.append(f"{engine} engine primitive(s) generated")
            if landscapes:
                parts.append(f"{landscapes} landscape mesh(es) exported")
            if mirrored:
                parts.append(f"{mirrored} mirrored copy(ies)")
            level = "success" if missing == 0 else "warn"
            tail = f" ({missing} without a bulk-export FBX — vmdl references a missing mesh)" if missing else ""
            self._log("Models — " + ", ".join(parts) + tail, level)

    def _convert_materials(self, referenced_meshes):
        """Convert the Material Instances used by the scene's meshes into vmats
        (params from the bridge, textures from the bulk-export folder, packed
        ORM/RMA auto-split). Writes into output_dir/materials/ so the vmdl
        material remaps resolve to them by the FBX's embedded material name."""
        from .material_converter import convert_material
        from .fbx_flatten import list_materials
        from .slot_mapping import load_overrides

        slot_overrides = load_overrides()

        # Map MI stem -> UE object path (one bridge call).
        self._log("Resolving scene materials…", "info")
        try:
            mi_keys = self.bridge.list_materials()
        except BridgeError as e:
            self._log(f"Materials — could not list material instances: {e}", "warn")
            return
        stem_to_path = {}
        for k in mi_keys:
            if k.lower().endswith(".uasset"):
                stem_to_path[os.path.basename(k)[:-len(".uasset")].lower()] = k[:-len(".uasset")]

        # Gather the MI names actually referenced by the meshes' FBXs.
        wanted = set()
        for mesh in referenced_meshes:
            src = find_bulk_export_mesh(self.bulk_dir, mesh) if self.bulk_dir else None
            if src:
                for m in (list_materials(src) or []):
                    wanted.add(m.lower())

        # A decal's material is attached to the actor, not to any mesh, so it
        # never appears in an FBX and the loop above cannot see it. Its exact
        # object path is known, so it is registered directly rather than hoping
        # list_materials' name/folder heuristic recognised it — decal materials
        # routinely sit in a Decals/ folder under a D_ prefix, which it does not.
        for ue_mat in self._decal_materials:
            key = _object_path_to_key(ue_mat)
            if key:
                stem = key.rsplit("/", 1)[-1].lower()
                stem_to_path.setdefault(stem, key)
                wanted.add(stem)

        targets = [(s, p) for s, p in stem_to_path.items() if s in wanted]
        if not targets:
            self._log("Materials — no matching material instances for the scene meshes.", "info")
            return

        from .converter import (
            FALLBACK_SHADER, get_master_material_name, load_material_swaps_kv3,
            seed_shader_for, save_material_swaps_kv3,
        )

        kv3_swaps, kv3_slots, kv3_params, kv3_flags, kv3_blend = load_material_swaps_kv3(self.output_dir)
        merged_shaders = dict(kv3_swaps)
        if self.master_shaders:
            merged_shaders.update(self.master_shaders)

        done, missing_tex = 0, 0
        unmapped = set()
        self._log(
            f"Materials — {len(targets)} to convert; remap table has "
            f"{len(merged_shaders)} Master Material(s).",
            "info",
        )
        for i, (stem, path) in enumerate(sorted(targets)):
            if self._cancel_check():
                return
            self.progress.emit(i + 1, len(targets))
            try:
                data = self.bridge.dump_material(path)
                master_name = get_master_material_name(data, path)
                shader = merged_shaders.get(master_name)
                if not shader:
                    shader = seed_shader_for(master_name, data.get("flags"))
                    merged_shaders[master_name] = shader
                    save_material_swaps_kv3(self.output_dir, merged_shaders,
                                            slot_mappings=self.master_slot_overrides or kv3_slots,
                                            param_mappings=self.master_param_overrides or kv3_params,
                                            feature_flags=self.master_feature_flags or kv3_flags,
                                            blend_modes=self.master_blend_modes or kv3_blend)
                    source = f"stamped & mapped {master_name}"
                else:
                    source = f"remap of {master_name}"

                extras = []
                overrides = (self.master_slot_overrides.get(master_name)
                             if self.master_slot_overrides and master_name in self.master_slot_overrides
                             else kv3_slots.get(master_name, slot_overrides))
                param_overrides = (self.master_param_overrides.get(master_name)
                                   if self.master_param_overrides and master_name in self.master_param_overrides
                                   else kv3_params.get(master_name, {}))
                feature_flags = (self.master_feature_flags.get(master_name)
                                 if self.master_feature_flags and master_name in self.master_feature_flags
                                 else kv3_flags.get(master_name, {}))
                blend_mode = (self.master_blend_modes.get(master_name)
                              if self.master_blend_modes and master_name in self.master_blend_modes
                              else kv3_blend.get(master_name, 0))

                if overrides:
                    extras.append(f"{len(overrides)} slot")
                if param_overrides:
                    extras.append(f"{len(param_overrides)} param")
                if feature_flags:
                    extras.append(f"{len(feature_flags)} feature")
                if blend_mode:
                    extras.append(f"blend mode {blend_mode}")
                if extras:
                    source += " + " + "/".join(extras)

                res = convert_material(data, self.bulk_dir, self.output_dir,
                                       shader=shader, slot_overrides=overrides,
                                       param_overrides=param_overrides,
                                       strip_prefix=self.strip_prefix,
                                       tex_format=self.tex_format,
                                       invert_y_normal=self.invert_y_normal,
                                       feature_flags=feature_flags, blend_mode=blend_mode)
                done += 1
                msg = f"  material {stem}: Success ({shader}, {source})"
                if res.missing:
                    missing_tex += 1
                    msg += f" (missing: {', '.join(res.missing)})"
                self._log(msg, "info")
            except Exception as e:
                self._log(f"  material {stem}: {e}", "warn")
        note = f", {missing_tex} with missing textures" if missing_tex else ""
        self._log(f"Materials — {done} vmat written{note}", "success")
        if unmapped:
            # A gap in the saved table, not a conversion failure — but the shader
            # these got was a fallback constant, not a choice, so say so.
            self._log(
                f"Materials — {len(unmapped)} Master Material(s) have no shader remap entry "
                f"and converted with the {FALLBACK_SHADER} fallback. Re-analyze the project "
                f"to give them one, then set it in the Materials tab: "
                + ", ".join(sorted(unmapped)),
                "warn",
            )

    def _build_landscape_model(self, mesh_id, vmdl_path, model_rel, mat_rel) -> bool:
        """Build the landscape's vmdl from a bulk-exported FBX if the user has
        one (e.g. Unreal's Landscape "Convert to Static Mesh", then bulk-export
        it like any other mesh — find_bulk_export_mesh matches it by filename
        stem, same fuzzy lookup as regular meshes). Falls back to baking an OBJ
        straight from the map's heightmap data via the bridge, which only works
        when the project has cooked platform data (see export-landscape's
        PF_Unknown failure on uncooked/loose projects)."""
        map_obj_path = self._landscape_sources.get(mesh_id)
        if not map_obj_path:
            self._log(f"  {mesh_id}: no source map recorded, skipped", "warn")
            return False

        src_fbx = find_bulk_export_mesh(self.bulk_dir, mesh_id) if self.bulk_dir else None
        if src_fbx:
            fbx_rel = os.path.splitext(model_rel)[0] + ".fbx"
            dst_fbx = os.path.join(self.output_dir, fbx_rel)
            os.makedirs(os.path.dirname(dst_fbx), exist_ok=True)
            shutil.copy2(src_fbx, dst_fbx)
            self._log(f"  {os.path.basename(src_fbx)} -> {fbx_rel} (landscape)", "info")
            self._write_vmdl(vmdl_path, fbx_rel, import_scale=self.unit_scale, fbx_path=dst_fbx,
                       material_path=mat_rel, output_dir=self.output_dir,
                       use_graybox_fallback=self.use_graybox_fallback)
            return True

        landscape_dir = os.path.join(self.output_dir, "_landscape_export", os.path.basename(map_obj_path))
        try:
            res = self.bridge.export_landscape(map_obj_path, landscape_dir, flags="mesh")
        except BridgeError as e:
            self._log(
                f"  {os.path.basename(map_obj_path)}: no bulk-export FBX found for the landscape, "
                f"and the bridge's heightmap bake failed — {e}",
                "warn",
            )
            return False

        src_obj = res.get("saved")
        if not src_obj or not os.path.isfile(src_obj):
            self._log(f"  {os.path.basename(map_obj_path)}: landscape export did not return an OBJ", "warn")
            return False

        obj_rel = os.path.splitext(model_rel)[0] + ".obj"
        dst_obj = os.path.join(self.output_dir, obj_rel)
        os.makedirs(os.path.dirname(dst_obj), exist_ok=True)
        shutil.copy2(src_obj, dst_obj)
        self._log(f"  {os.path.basename(map_obj_path)} landscape -> {obj_rel}", "info")

        self._write_vmdl(vmdl_path, obj_rel, import_scale=self.unit_scale, material_path=mat_rel,
                   use_graybox_fallback=self.use_graybox_fallback)
        return True


def demo():
    # The port scope is built from the project's asset listing, so these can
    # never appear in it — treating them as out-of-scope is what dropped every
    # engine mesh and every landscape before the vmdl stage.
    assert _is_external_ref("/Engine/MapTemplates/SM_Template_Map_Floor.SM_Template_Map_Floor")
    assert _is_external_ref("StaticMesh'/Engine/BasicShapes/Cube.Cube'")
    assert _is_external_ref(_LANDSCAPE_MESH_PREFIX + "Arena_Landscape.Arena_Landscape")
    # Project content is scoped normally, whether given as an object path or as
    # the bridge's relative asset key.
    assert not _is_external_ref("/Game/Meshes/SM_Chair.SM_Chair")
    assert not _is_external_ref("StaticMesh'/Game/Meshes/SM_Chair.SM_Chair'")
    assert not _is_external_ref("MyProj/Content/Meshes/SM_Chair.uasset")

    scoped = SceneModelsWorker.__new__(SceneModelsWorker)
    scoped.selected_stems = {"sm_chair"}
    assert scoped._wanted("/Game/Meshes/SM_Chair.SM_Chair")
    assert not scoped._wanted("/Game/Meshes/SM_Table.SM_Table")
    assert scoped._wanted("/Engine/MapTemplates/SM_Template_Map_Floor.SM_Template_Map_Floor")

    unscoped = SceneModelsWorker.__new__(SceneModelsWorker)
    unscoped.selected_stems = None
    assert unscoped._wanted("/Game/Meshes/SM_Table.SM_Table")

    # A decal's material arrives as a UE object path; the bridge addresses
    # packages by their key. Passing the object path through unconverted fails
    # with "there is no game file with the path", which is how every decal-only
    # material went unconverted and left its overlay pointing at nothing.
    assert _object_path_to_key("/Game/Kowloon/Meshes/Decals/D_Dirt_01.D_Dirt_01") \
        == "Kowloon/Meshes/Decals/D_Dirt_01"
    assert _object_path_to_key("MaterialInstanceConstant'/Game/M/MI_A.MI_A'") == "M/MI_A"
    assert _object_path_to_key("/Game/A.A") == "A"
    assert _object_path_to_key("") == ""

    # One mesh mirrored on different axes in different places needs one vmdl
    # each; a repeat of the same axis set must not write the file twice.
    w = SceneModelsWorker.__new__(SceneModelsWorker)
    w._mirrored_meshes = {
        ("/Game/M/SM_A.SM_A", (True, False, False)),
        ("/Game/M/SM_A.SM_A", (False, False, True)),
        ("/Game/M/SM_B.SM_B", (True, False, False)),
    }
    assert w._mirror_axes_for("/Game/M/SM_A.SM_A") == [(False, False, True), (True, False, False)]
    assert w._mirror_axes_for("/Game/M/SM_B.SM_B") == [(True, False, False)]
    assert w._mirror_axes_for("/Game/M/SM_C.SM_C") == []

    print("ok")


if __name__ == "__main__":
    demo()
