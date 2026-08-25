"""
Python client for H5T.UnrealBridge — the .NET CLI over CUE4Parse.

Reads Unreal `.uasset` / `.umap` files (the raw project) by shelling out to the
bridge, which returns JSON. Used for the "entity" half of the hybrid migration
(scenes, blueprints, material params); meshes/textures come from a UE bulk-export
folder instead.

The bridge is a self-contained net10 build. It runs under the .NET 10 runtime
that Hammer5Tools already requires, invoked as `dotnet H5T.UnrealBridge.dll`.
"""

import os
import re
import sys
import json
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Optional


class BridgeError(RuntimeError):
    pass


# Packages that exist only to serve the Editor and hold nothing portable.
# "_BuiltData" is the MapBuildDataRegistry Unreal writes beside every map: it
# carries baked lightmaps and nothing else, so listing it only ever costs a
# reference scan and a slot in the port scope.
_IGNORED_ASSET_SUFFIXES = ("_builtdata",)


def is_ignored_asset(key: str) -> bool:
    """Editor-only packages that must never reach the asset list or a scan."""
    stem = os.path.splitext(os.path.basename(str(key).replace("\\", "/")))[0].lower()
    return stem.endswith(_IGNORED_ASSET_SUFFIXES)


# How CUE4Parse writes references in a dump — string values under ObjectPath,
# ObjectName, AssetPathName, MaterialSlotName, Parent, etc.
_REF_FIELD = re.compile(r'"([^"]+)"')


def _read_error(fh, limit: int = 300) -> str:
    """First line of what the bridge wrote to stderr — CUE4Parse exception text.
    Without it a failure reads as a bare 'exit 1' and says nothing."""
    try:
        fh.seek(0)
        text = fh.read().decode("utf-8", "replace").strip()
    except Exception:
        return "no error output"
    finally:
        fh.close()
    return (text.splitlines()[0][:limit] if text else "no error output")


def _candidate_bridge_paths():
    """Locations to search for the published bridge dll."""
    root = Path(__file__).resolve().parents[4]
    yield root / "Hammer5ToolsCore" / "UnrealBridge" / "publish" / "H5T.UnrealBridge.dll"
    yield root / "Hammer5ToolsCore" / "UnrealBridge" / "bin" / "Release" / "net10.0" / "H5T.UnrealBridge.dll"
    yield root / "Hammer5ToolsGUI" / "gui" / "tools" / "unreal_bridge" / "publish" / "H5T.UnrealBridge.dll"
    yield root / "Hammer5ToolsCore" / "external" / "unreal_bridge" / "H5T.UnrealBridge.dll"
    # Frozen (PyInstaller) bundle
    if getattr(sys, "frozen", False):
        from hammer5tools_core.runtime_paths import resolve_runtime_paths
        yield resolve_runtime_paths().runtime_resource("unreal_bridge", "H5T.UnrealBridge.dll")


def find_bridge_dll() -> Optional[str]:
    """The bridge dll to run: an explicit override, else the newest one built.

    Newest wins rather than a fixed search order, because `dotnet build` and
    `dotnet publish` write to different directories: a stale publish/ dll used
    to shadow a freshly built bin/Release one, so rebuilding the bridge changed
    nothing and said nothing about why.
    """
    env = os.environ.get("H5T_UNREAL_BRIDGE")
    if env and Path(env).is_file():
        return str(Path(env))
    found = [p for p in _candidate_bridge_paths() if p and p.is_file()]
    if not found:
        return None
    return str(max(found, key=lambda p: p.stat().st_mtime))


def find_dotnet() -> Optional[str]:
    """Locate the dotnet host: PATH first, then a local ~/.dotnet install."""
    exe = shutil.which("dotnet")
    if exe:
        return exe
    local = Path.home() / ".dotnet" / ("dotnet.exe" if os.name == "nt" else "dotnet")
    return str(local) if local.is_file() else None


class UnrealBridge:
    """Thin wrapper that runs the bridge and parses its JSON output."""

    def __init__(self, content_dir: str, dll: Optional[str] = None, dotnet: Optional[str] = None):
        self.content_dir = content_dir
        self.dll = dll or find_bridge_dll()
        self.dotnet = dotnet or find_dotnet()

    def is_available(self) -> bool:
        return bool(self.dll and self.dotnet)

    def why_unavailable(self) -> str:
        if not self.dotnet:
            return "The .NET runtime ('dotnet') was not found. Install .NET 10."
        if not self.dll:
            return ("H5T.UnrealBridge.dll not found. Build it (see tools/unreal_bridge/README.md) "
                    "or set H5T_UNREAL_BRIDGE to its path.")
        return ""

    def _run(self, *cmd_args: str, timeout: int = 300) -> str:
        if not self.is_available():
            raise BridgeError(self.why_unavailable())
        proc = subprocess.run(
            [self.dotnet, self.dll, *cmd_args],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            raise BridgeError(f"bridge '{cmd_args[0]}' failed: {msg[:500]}")
        return proc.stdout

    def _run_json(self, *cmd_args: str, timeout: int = 300) -> Any:
        out = self._run(*cmd_args, timeout=timeout)
        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            raise BridgeError(f"bridge returned non-JSON output: {e}") from e

    # commands

    def info(self) -> dict:
        return self._run_json("info", self.content_dir)

    def list(self, substring: str = "") -> list:
        return self.list_counted(substring)[0]

    def list_counted(self, substring: str = "") -> tuple:
        """(assets, ignored) — the listing plus how many entries were dropped.

        The truncation check compares the listing against the bridge's own
        totalFiles, so anything filtered out here has to be reported or an
        intact project reads as a cut-off one.
        """
        raw = self._run_json("list", self.content_dir, substring)
        kept = [k for k in raw if not is_ignored_asset(k)]
        return kept, len(raw) - len(kept)

    def list_materials(self) -> list:
        """Find all Material / MaterialInstance .uasset keys under the project,
        regardless of exact subfolder layout (e.g. Materials/ or Environment/...)."""
        all_keys = self.list("")
        mat_keys = []
        for k in all_keys:
            lk = k.lower()
            if not lk.endswith(".uasset") or lk.endswith(".umap"):
                continue
            filename = os.path.basename(lk)
            if (any(x in lk for x in ("/materials/", "/material/", "/material_instances/", "/mi/", "/mastermaterials/", "/inst/", "/m/"))
                or filename.startswith(("mi_", "m_", "mm_", "mat_"))
                or "material" in filename):
                mat_keys.append(k)
        if not mat_keys:
            mat_keys = [k for k in all_keys if k.lower().endswith(".uasset") and not k.lower().endswith(".umap")]
        return mat_keys

    def dump(self, object_path: str) -> Any:
        # Raw export tree can be huge; allow more time. Only call this for assets
        # whose whole tree is actually needed — see iter_refs for the cheap path.
        return self._run_json("dump", self.content_dir, object_path, timeout=600)

    def iter_refs(self, object_path: str, timeout: int = 600, is_cancelled=None) -> set:
        """Every object reference in an asset, read as a stream.

        If is_cancelled is a no-arg callable returning truthy, the bridge
        process is killed and a BridgeError is raised mid-stream — used by the
        reference-scan worker's cancel path so closing the dialog stops it.
        """
        if not self.is_available():
            raise BridgeError(self.why_unavailable())
        # stderr goes to a temp file, not a pipe: nothing reads it until the
        # process is done, and a pipe that fills up deadlocks the child.
        err = tempfile.TemporaryFile()
        proc = subprocess.Popen(
            [self.dotnet, self.dll, "dump", self.content_dir, object_path],
            stdout=subprocess.PIPE, stderr=err,
            text=True, encoding="utf-8", errors="replace",
        )
        deadline = time.monotonic() + timeout
        refs = set()
        cancelled = False
        try:
            for line in proc.stdout:
                if is_cancelled is not None and is_cancelled():
                    cancelled = True
                    break
                refs.update(_REF_FIELD.findall(line))
                if time.monotonic() > deadline:
                    raise BridgeError(f"bridge 'dump' timed out after {timeout}s")
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        if cancelled:
            raise BridgeError("bridge 'dump' cancelled")
        if proc.returncode != 0:
            raise BridgeError(f"bridge 'dump' failed (exit {proc.returncode}): {_read_error(err)}")
        err.close()
        return refs

    def dump_scene(self, map_path: str) -> dict:
        """Normalized actor list: {map, count, actors:[{actor, componentType,
        mesh, location, rotation, scale}]} — transforms are in UE space."""
        return self._run_json("dump-scene", self.content_dir, map_path, timeout=600)

    def dump_blueprint(self, bp_path: str) -> dict:
        """Normalized blueprint component tree: {blueprint, count, components:[{name,
        componentType, mesh, parent, location, rotation, scale}]} — transforms in UE space."""
        try:
            return self._run_json("dump-blueprint", self.content_dir, bp_path, timeout=600)
        except BridgeError as e:
            if "unknown command" in str(e).lower():
                return self._parse_dump_as_blueprint(bp_path)
            raise

    def _parse_dump_as_blueprint(self, bp_path: str) -> dict:
        exports = self.dump(bp_path)
        if not isinstance(exports, list):
            return {"blueprint": bp_path, "count": 0, "components": []}

        components = []

        # Mirrors DumpBlueprint in tools/unreal_bridge/Program.cs: a Blueprint's
        # component hierarchy lives in the SimpleConstructionScript's ChildNodes,
        # not in AttachParent, and templates are exported as "<Var>_GEN_VARIABLE".
        def _var_name(n: str) -> str:
            n = str(n).split(":")[-1]
            return n[:-len("_GEN_VARIABLE")] if n.endswith("_GEN_VARIABLE") else n

        def _ref_name(prop) -> str:
            # CUE4Parse writes object refs as {"ObjectName": "Class'Name'", ...}.
            raw = str((prop.get("ObjectName") if isinstance(prop, dict) else prop) or "").strip()
            if raw.endswith("'") and "'" in raw[:-1]:
                raw = raw[raw.index("'") + 1:-1]
            return raw.split(":")[-1].split(".")[-1]

        def _resolve(prop):
            """Follow a reference to its export. ObjectPath ends with the export
            index, which is what disambiguates sub-objects — names repeat (every
            child actor template holds a "StaticMeshComponent0")."""
            if not isinstance(prop, dict):
                return None
            idx = str(prop.get("ObjectPath") or "").rsplit(".", 1)[-1]
            if idx.isdigit() and int(idx) < len(exports):
                target = exports[int(idx)]
                return target if isinstance(target, dict) else None
            return None

        def _mesh_path(prop):
            if isinstance(prop, dict):
                return prop.get("ObjectPath") or prop.get("ObjectName")
            return prop or None

        def _child_actor_mesh(props):
            """A ChildActorComponent's mesh lives on the actor template it spawns."""
            template = _resolve(props.get("ChildActorTemplate"))
            if not template:
                return None
            tprops = template.get("Properties", {})
            root = _resolve(tprops.get("StaticMeshComponent")) or _resolve(tprops.get("RootComponent"))
            return _mesh_path(root.get("Properties", {}).get("StaticMesh")) if root else None

        # Components inside a child actor template belong to the spawned actor;
        # the ChildActorComponent stands in for them.
        child_actor_templates = set()
        for exp in exports:
            if not isinstance(exp, dict):
                continue
            template = _resolve(exp.get("Properties", {}).get("ChildActorTemplate"))
            if template:
                child_actor_templates.add(template.get("Name"))

        scs_nodes = {}   # export name -> properties
        for exp in exports:
            if not isinstance(exp, dict):
                continue
            if "SCS_Node" in (exp.get("Type") or exp.get("Class") or ""):
                scs_nodes[exp.get("Name") or ""] = exp.get("Properties", {})

        template_vars = {}   # template export name -> SCS variable name
        for props in scs_nodes.values():
            tmpl = _ref_name(props.get("ComponentTemplate"))
            if not tmpl:
                continue
            internal = props.get("InternalVariableName")
            template_vars[tmpl] = str(internal) if internal and internal != "None" else _var_name(tmpl)

        def _node_var(props) -> str:
            tmpl = _ref_name(props.get("ComponentTemplate"))
            return template_vars.get(tmpl, _var_name(tmpl)) if tmpl else ""

        node_parent_map = {}
        for props in scs_nodes.values():
            my_var = _node_var(props)
            if not my_var:
                continue
            for child_ref in props.get("ChildNodes") or []:
                child = _resolve(child_ref)
                child_props = child.get("Properties", {}) if child else scs_nodes.get(_ref_name(child_ref))
                child_var = _node_var(child_props) if child_props else ""
                if child_var and child_var != my_var:
                    node_parent_map[child_var] = my_var

        for props in scs_nodes.values():
            my_var = _node_var(props)
            parent_name = props.get("ParentComponentOrVariableName")
            if my_var and my_var not in node_parent_map and parent_name and parent_name != "None":
                if str(parent_name) != my_var:
                    node_parent_map[my_var] = str(parent_name)

        seen = set()
        for exp in exports:
            if not isinstance(exp, dict):
                continue
            exp_type = exp.get("Type") or exp.get("Class") or ""
            raw_name = exp.get("Name") or exp.get("ObjectName") or "Component"
            # Keep every transform-carrying node, mesh or not: dropping an empty
            # scene node orphans its children and loses the offset it held.
            if raw_name not in template_vars and not exp_type.endswith("Component"):
                continue
            if _ref_name(exp.get("Outer")) in child_actor_templates:
                continue

            name = template_vars.get(raw_name, _var_name(raw_name))
            if name in seen:
                continue
            seen.add(name)

            props = exp.get("Properties", {})
            mesh = _mesh_path(props.get("StaticMesh")) or _child_actor_mesh(props)

            loc_prop = props.get("RelativeLocation", {})
            rot_prop = props.get("RelativeRotation", {})
            scl_prop = props.get("RelativeScale3D", {})

            loc = {"x": float(loc_prop.get("X", 0)), "y": float(loc_prop.get("Y", 0)), "z": float(loc_prop.get("Z", 0))}
            rot = {"pitch": float(rot_prop.get("Pitch", 0)), "yaw": float(rot_prop.get("Yaw", 0)), "roll": float(rot_prop.get("Roll", 0))}
            scl = {"x": float(scl_prop.get("X", 1)), "y": float(scl_prop.get("Y", 1)), "z": float(scl_prop.get("Z", 1))}

            parent = node_parent_map.get(name)
            if not parent:
                attach = _ref_name(props.get("AttachParent"))
                parent = _var_name(attach) if attach else None

            components.append({
                "name": name,
                "componentType": exp_type,
                "mesh": mesh,
                "parent": parent,
                "location": loc,
                "rotation": rot,
                "scale": scl,
            })

        return {"blueprint": bp_path, "count": len(components), "components": components}

    def export_landscape(self, map_path: str, out_dir: str, flags: str = "mesh") -> dict:
        """Export the map's (first) landscape actor as an OBJ mesh into out_dir.

        flags: "mesh" (just the OBJ — what the Scenes/Models pipeline uses),
        "heightmap", "weightmap", or "all". Returns {ok, components, label,
        saved} where `saved` is the absolute path of the exported OBJ.
        Raises BridgeError (message starts with "NO_LANDSCAPE") if the map has
        no landscape actor with components.
        """
        return self._run_json("export-landscape", self.content_dir, map_path, out_dir, flags, timeout=600)

    def dump_material(self, mat_path: str) -> dict:
        """Normalized material instance properties: {material, parent, textures,
        scalars, vectors, switches}. `switches` are the MI's static-switch bools
        (e.g. "Use Normal Map") — a signal for whether a param even applies,
        not currently used to gate slot selection but available for it."""
        try:
            return self._run_json("dump-material", self.content_dir, mat_path, timeout=600)
        except BridgeError as e:
            if "unknown command" in str(e).lower():
                return self._parse_dump_as_material(mat_path)
            raise

    @staticmethod
    def _param_name(p: dict):
        """UE 4.19+ nests the name in FMaterialParameterInfo ('ParameterInfo':
        {'Name': ...}); older assets (4.16 and down) serialise a flat
        'ParameterName'. Reading only the former drops every override on
        pre-4.19 content, which then silently inherits the master's defaults."""
        info = p.get("ParameterInfo")
        if isinstance(info, dict) and info.get("Name"):
            return info["Name"]
        return p.get("ParameterName")

    def _parse_dump_as_material(self, mat_path: str) -> dict:
        exports = self.dump(mat_path)
        if not isinstance(exports, list):
            return {"material": mat_path, "parent": None, "textures": {}, "scalars": {}, "vectors": {}, "switches": {}}

        textures = {}
        scalars = {}
        vectors = {}
        switches = {}
        parent = None

        for exp in exports:
            if not isinstance(exp, dict):
                continue
            props = exp.get("Properties", {})
            parent_ref = props.get("Parent")
            if isinstance(parent_ref, dict):
                parent = parent_ref.get("ObjectPath") or parent_ref.get("ObjectName")

            for tp in props.get("TextureParameterValues", []):
                if isinstance(tp, dict):
                    name = self._param_name(tp)
                    val = tp.get("ParameterValue")
                    tex = val.get("ObjectPath") or val.get("ObjectName") if isinstance(val, dict) else str(val) if val else None
                    if name and tex:
                        textures[name] = tex

            for sp in props.get("ScalarParameterValues", []):
                if isinstance(sp, dict):
                    name = self._param_name(sp)
                    val = sp.get("ParameterValue")
                    if name and val is not None:
                        scalars[name] = float(val)

            for vp in props.get("VectorParameterValues", []):
                if isinstance(vp, dict):
                    name = self._param_name(vp)
                    val = vp.get("ParameterValue", {})
                    if name and isinstance(val, dict):
                        vectors[name] = {
                            "r": float(val.get("R", 0)),
                            "g": float(val.get("G", 0)),
                            "b": float(val.get("B", 0)),
                            "a": float(val.get("A", 1)),
                        }

            static_params = props.get("StaticParameters") or {}
            for swp in (static_params.get("StaticSwitchParameters") or []):
                if isinstance(swp, dict):
                    name = self._param_name(swp)
                    val = swp.get("Value")
                    if name and val is not None:
                        switches[name] = bool(val)

        return {"material": mat_path, "parent": parent, "textures": textures, "scalars": scalars,
                "vectors": vectors, "switches": switches}


