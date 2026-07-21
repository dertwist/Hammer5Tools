"""
Worker that converts UE scenes (-> vmap) and models (-> vmdl) via the CUE4Parse
bridge + the vmap/vmdl writers. Runs off the UI thread and reports progress and
per-step feedback to the converter's console.
"""

import os
import shutil
from PySide6.QtCore import QThread, Signal

from .bridge_client import UnrealBridge, BridgeError
from .vmap_writer import write_vmap
from .vsmart_writer import write_vsmart
from .vmdl_writer import write_vmdl, ue_mesh_to_model_path, find_bulk_export_mesh
from .engine_meshes import is_engine_mesh, generate_engine_mesh_obj, bundled_fbx_for

_MESH_EXTS = (".fbx", ".obj", ".gltf", ".glb", ".dmx")

# Synthetic mesh id prefix for landscape actors. Landscapes have no static-mesh
# asset to reference, so dump_scene's "Landscape" actor entries are rewritten
# (below) into ordinary StaticMeshComponent entries pointing at one of these —
# the rest of the vmap/vmdl pipeline then treats a landscape exactly like any
# other placed mesh, with the OBJ produced on demand via bridge.export_landscape.
_LANDSCAPE_MESH_PREFIX = "/H5T/Landscape/"


class SceneModelsWorker(QThread):
    log = Signal(str, str)      # message, level (info/warn/error/success)
    progress = Signal(int, int)  # current, total
    done = Signal()

    def __init__(self, project_dir, bulk_dir, output_dir,
                 do_scenes, do_models, do_blueprints=False, do_materials=False, strip_prefix=False, unit_scale=1.0,
                 use_graybox_fallback=False, parent=None):
        super().__init__(parent)
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

        # Discover maps from the project.
        try:
            map_keys = [k for k in bridge.list("") if k.lower().endswith(".umap")]
        except BridgeError as e:
            self._log(str(e), "error")
            return

        self._log(f"Found {len(map_keys)} map(s): {', '.join(os.path.basename(m) for m in map_keys)}", "info")

        referenced_meshes = set()

        # --- Scenes -> vmap ---
        if self.do_scenes:
            if not map_keys:
                self._log("No .umap files found in project.", "warn")
            for i, mk in enumerate(map_keys):
                obj = mk[:-len(".umap")]
                name = os.path.basename(obj)
                self.progress.emit(i + 1, len(map_keys))
                try:
                    scene = bridge.dump_scene(obj)
                except BridgeError as e:
                    self._log(f"{name}: scene read failed — {e}", "error")
                    continue

                self._normalize_landscape_actors(scene["actors"], obj)

                vmap_path = os.path.join(self.output_dir, "maps", f"{name}.vmap")
                res = write_vmap(scene["actors"], vmap_path, unit_scale=self.unit_scale, strip_prefix=self.strip_prefix)
                referenced_meshes.update(
                    a["mesh"] for a in scene["actors"]
                    if a.get("mesh") and a.get("componentType") == "StaticMeshComponent"
                )
                skip_note = ""
                if res.skipped:
                    skip_note = f" ({res.skipped} skipped: {res.skipped_types})"
                smartprop_note = f", {res.placed_smartprops} smartprop" if res.placed_smartprops else ""
                self._log(
                    f"{name}.vmap — {res.placed} prop_static{smartprop_note}, {len(res.models)} models{skip_note}",
                    "success",
                )
        else:
            # Models-only still needs the mesh list; pull it from the maps.
            for mk in map_keys:
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
                    filtered_bp_keys.append(k)

                self._log(f"Blueprints — candidate assets to inspect: {len(filtered_bp_keys)} of {len(bp_keys)}", "info")

                for i, bk in enumerate(filtered_bp_keys):
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

        # --- Materials -> vmat (before Models so vmdl remaps resolve to real vmats) ---
        if self.do_materials:
            self._convert_materials(referenced_meshes)

        # --- Models -> vmdl ---
        if self.do_models:
            self._log(f"Referenced meshes found: {len(referenced_meshes)}", "info")
            if not referenced_meshes:
                self._log("No referenced meshes to build vmdls for. Make sure Scenes is enabled or at least one map was scanned.", "warn")
            made, missing, engine, landscapes = 0, 0, 0, 0
            total = len(referenced_meshes)
            for i, mesh in enumerate(sorted(referenced_meshes)):
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
                if is_engine_mesh(mesh):
                    src = bundled_fbx_for(mesh)
                    if src:
                        fbx_rel = os.path.splitext(model_rel)[0] + ".fbx"
                        dst = os.path.join(self.output_dir, fbx_rel)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        write_vmdl(vmdl_path, fbx_rel, import_scale=self.unit_scale, fbx_path=dst, material_path=mat_rel, use_graybox_fallback=self.use_graybox_fallback)
                    else:
                        obj_rel = os.path.splitext(model_rel)[0] + ".obj"
                        generate_engine_mesh_obj(mesh, os.path.join(self.output_dir, obj_rel))
                        write_vmdl(vmdl_path, obj_rel, import_scale=self.unit_scale, material_path=mat_rel, use_graybox_fallback=self.use_graybox_fallback)
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
                write_vmdl(vmdl_path, mesh_rel, import_scale=self.unit_scale,
                           fbx_path=dst_fbx or src_fbx, material_path=mat_rel, output_dir=self.output_dir,
                           use_graybox_fallback=self.use_graybox_fallback)
                made += 1

            parts = [f"{made} vmdl written"]
            if engine:
                parts.append(f"{engine} engine primitive(s) generated")
            if landscapes:
                parts.append(f"{landscapes} landscape mesh(es) exported")
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

        # Map MI stem -> UE object path (one bridge call).
        try:
            mi_keys = self.bridge.list("Material_Instances")
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

        targets = [(s, p) for s, p in stem_to_path.items() if s in wanted]
        if not targets:
            self._log("Materials — no matching material instances for the scene meshes.", "info")
            return

        done, missing_tex = 0, 0
        for i, (stem, path) in enumerate(sorted(targets)):
            self.progress.emit(i + 1, len(targets))
            try:
                data = self.bridge.dump_material(path)
                res = convert_material(data, self.bulk_dir, self.output_dir)
                done += 1
                msg = f"  material {stem}: Success"
                if res.missing:
                    missing_tex += 1
                    msg += f" (missing: {', '.join(res.missing)})"
                self._log(msg, "info")
            except Exception as e:
                self._log(f"  material {stem}: {e}", "warn")
        note = f", {missing_tex} with missing textures" if missing_tex else ""
        self._log(f"Materials — {done} vmat written{note}", "success")

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
            write_vmdl(vmdl_path, fbx_rel, import_scale=self.unit_scale, fbx_path=dst_fbx,
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

        write_vmdl(vmdl_path, obj_rel, import_scale=self.unit_scale, material_path=mat_rel,
                   use_graybox_fallback=self.use_graybox_fallback)
        return True
