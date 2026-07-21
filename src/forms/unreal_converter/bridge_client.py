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
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional


class BridgeError(RuntimeError):
    pass


def _candidate_bridge_paths():
    """Locations to search for the published bridge dll, most specific first."""
    env = os.environ.get("H5T_UNREAL_BRIDGE")
    if env:
        yield Path(env)
    root = Path(__file__).resolve().parents[3]  # repo root (src/forms/unreal_converter -> repo)
    yield root / "tools" / "unreal_bridge" / "publish" / "H5T.UnrealBridge.dll"
    yield root / "src" / "external" / "unreal_bridge" / "H5T.UnrealBridge.dll"
    # Frozen (PyInstaller) bundle
    if getattr(sys, "frozen", False):
        yield Path(sys._MEIPASS) / "unreal_bridge" / "H5T.UnrealBridge.dll"


def find_bridge_dll() -> Optional[str]:
    for p in _candidate_bridge_paths():
        if p and p.is_file():
            return str(p)
    return None


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

    # --- commands ---------------------------------------------------------

    def info(self) -> dict:
        return self._run_json("info", self.content_dir)

    def list(self, substring: str = "") -> list:
        return self._run_json("list", self.content_dir, substring)

    def dump(self, object_path: str) -> Any:
        # Raw export tree can be huge; allow more time.
        return self._run_json("dump", self.content_dir, object_path, timeout=600)

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
        node_parent_map = {}

        for exp in exports:
            if not isinstance(exp, dict):
                continue
            exp_type = exp.get("Type") or exp.get("Class") or ""
            if "SCS_Node" in exp_type:
                tmpl = exp.get("Properties", {}).get("ComponentTemplate", {})
                template_name = tmpl.get("ObjectName", "").split(":")[-1] if isinstance(tmpl, dict) else ""
                parent_name = exp.get("Properties", {}).get("AttachVariableName") or exp.get("Properties", {}).get("ParentComponentOrVariableName")
                if template_name and parent_name and parent_name != "None":
                    node_parent_map[template_name] = str(parent_name)

        for exp in exports:
            if not isinstance(exp, dict):
                continue
            exp_type = exp.get("Type") or exp.get("Class") or ""
            is_sm = "StaticMeshComponent" in exp_type
            is_sc = "SceneComponent" in exp_type
            if not is_sm and not is_sc:
                continue

            props = exp.get("Properties", {})
            mesh_prop = props.get("StaticMesh")
            mesh = None
            if isinstance(mesh_prop, dict):
                mesh = mesh_prop.get("ObjectPath") or mesh_prop.get("ObjectName")
            elif isinstance(mesh_prop, str):
                mesh = mesh_prop

            if is_sm and not mesh:
                continue

            name = exp.get("Name") or exp.get("ObjectName") or "Component"
            loc_prop = props.get("RelativeLocation", {})
            rot_prop = props.get("RelativeRotation", {})
            scl_prop = props.get("RelativeScale3D", {})

            loc = {"x": float(loc_prop.get("X", 0)), "y": float(loc_prop.get("Y", 0)), "z": float(loc_prop.get("Z", 0))}
            rot = {"pitch": float(rot_prop.get("Pitch", 0)), "yaw": float(rot_prop.get("Yaw", 0)), "roll": float(rot_prop.get("Roll", 0))}
            scl = {"x": float(scl_prop.get("X", 1)), "y": float(scl_prop.get("Y", 1)), "z": float(scl_prop.get("Z", 1))}

            attach_parent = props.get("AttachParent")
            parent = None
            if isinstance(attach_parent, dict):
                parent = attach_parent.get("ObjectName", "").split(":")[-1]
            if not parent:
                parent = node_parent_map.get(name)

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

    def dump_material(self, mat_path: str) -> dict:
        """Normalized material instance properties: {material, parent, textures,
        scalars, vectors}."""
        try:
            return self._run_json("dump-material", self.content_dir, mat_path, timeout=600)
        except BridgeError as e:
            if "unknown command" in str(e).lower():
                return self._parse_dump_as_material(mat_path)
            raise

    def _parse_dump_as_material(self, mat_path: str) -> dict:
        exports = self.dump(mat_path)
        if not isinstance(exports, list):
            return {"material": mat_path, "parent": None, "textures": {}, "scalars": {}, "vectors": {}}

        textures = {}
        scalars = {}
        vectors = {}
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
                    name = tp.get("ParameterInfo", {}).get("Name")
                    val = tp.get("ParameterValue")
                    tex = val.get("ObjectPath") or val.get("ObjectName") if isinstance(val, dict) else str(val) if val else None
                    if name and tex:
                        textures[name] = tex

            for sp in props.get("ScalarParameterValues", []):
                if isinstance(sp, dict):
                    name = sp.get("ParameterInfo", {}).get("Name")
                    val = sp.get("ParameterValue")
                    if name and val is not None:
                        scalars[name] = float(val)

            for vp in props.get("VectorParameterValues", []):
                if isinstance(vp, dict):
                    name = vp.get("ParameterInfo", {}).get("Name")
                    val = vp.get("ParameterValue", {})
                    if name and isinstance(val, dict):
                        vectors[name] = {
                            "r": float(val.get("R", 0)),
                            "g": float(val.get("G", 0)),
                            "b": float(val.get("B", 0)),
                            "a": float(val.get("A", 1)),
                        }

        return {"material": mat_path, "parent": parent, "textures": textures, "scalars": scalars, "vectors": vectors}


