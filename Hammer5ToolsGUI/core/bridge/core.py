"""Python-facing adapters for the UI-neutral Hammer5Tools .NET Core."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Optional


class CoreBridgeError(RuntimeError):
    """Raised when the Hammer5Tools Core contract cannot be loaded or invoked."""


@dataclass(frozen=True)
class CoreStatus:
    """Python-native result of probing the Hammer5Tools Core contract."""

    available: bool
    version: str | None = None
    diagnostic: str | None = None


@dataclass(frozen=True)
class SmartPropDeformer:
    """Python-native mesh deformation cage for a model under an active, non-rigid deformer.

    Set instead of the model's transform being bent: the model keeps its undeformed placement
    and the viewport warps its mesh vertices through this cage (Core has no mesh data of its own
    to do that itself). Shape matches what CS2 bakes into a compiled VMAP's SmartProp deformation
    data: 8 lattice corners, a 2-point cubic-Bezier handle pair per local-X edge, and the two
    frames needed to map a mesh vertex into cage-local space and back.
    """

    size: tuple[float, float, float]
    control_points: tuple[tuple[float, float, float], ...]
    midpoints: tuple[tuple[float, float, float], ...]
    deformer_frame: tuple[float, ...]
    volume_frame: tuple[float, ...]


@dataclass(frozen=True)
class SmartPropModel:
    """Python-native model produced by Core SmartProp evaluation."""

    element_id: int
    model_name: str
    transform: tuple[float, ...]
    material_group: str | None
    tint_color: tuple[float, float, float, float] | None
    deformer: SmartPropDeformer | None = None


@dataclass(frozen=True)
class SmartPropWidget:
    """Python-native editor widget produced by Core SmartProp evaluation."""

    type: str
    element_id: int
    transform: tuple[float, ...]
    offset: tuple[float, float, float]
    minimum_bounds: tuple[float, float, float]
    maximum_bounds: tuple[float, float, float]
    axis: tuple[float, float, float]
    color: tuple[float, float, float]
    handles: tuple[bool, ...]
    active_axes: tuple[bool, ...]
    scale: float
    radius: float
    angle: float
    size: float
    shape: str
    name: str


@dataclass(frozen=True)
class SmartPropEvaluation:
    """Python-native SmartProp evaluation result."""

    models: tuple[SmartPropModel, ...]
    widgets: tuple[SmartPropWidget, ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class VmapRewriteResult:
    """Python-native result of rewriting VMAP asset references."""

    changed: bool
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class UnrealMapWriteResult:
    """Python-native result of writing normalized Unreal placements."""

    placement_count: int
    encoding: str | None
    encoding_version: int | None
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class CompiledTextureData:
    width: int
    height: int
    rgba: bytes


@dataclass(frozen=True)
class CompiledMaterialData:
    name: str
    textures: tuple[CompiledTextureData | None, ...]
    base_color_factor: tuple[float, ...]
    metallic_factor: float
    roughness_factor: float
    emissive_factor: tuple[float, ...]
    alpha_mode: str
    alpha_cutoff: float
    double_sided: bool
    wrap_u: int
    wrap_v: int
    uv_set: int
    uv_scale: tuple[float, ...]
    uv_offset: tuple[float, ...]
    uv_center: tuple[float, ...]
    uv_rotation: float


@dataclass(frozen=True)
class CompiledSubMeshData:
    index_offset: int
    index_count: int
    material: CompiledMaterialData


@dataclass(frozen=True)
class CompiledModelData:
    vertices: Sequence[float]
    normals: Sequence[float]
    uvs: Sequence[float]
    indices: Sequence[int]
    bounds_minimum: tuple[float, ...]
    bounds_maximum: tuple[float, ...]
    submeshes: tuple[CompiledSubMeshData, ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class CompiledResourceData:
    data: bytes
    format: str
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class ValveMapEntity:
    """Python-native entity projected from an uncompiled Valve map."""

    class_name: str
    origin: str | None
    angles: str | None
    properties: dict[str, str]


@dataclass(frozen=True)
class ValveMapNode:
    """Python-native node projected from an uncompiled Valve map."""

    name: str
    class_name: str
    properties: dict[str, str]
    children: tuple[ValveMapNode, ...]


@dataclass(frozen=True)
class ValveMapDocument:
    """Python-native read-only Valve map projection."""

    path: str
    world: ValveMapNode
    nodes: tuple[ValveMapNode, ...]
    entities: tuple[ValveMapEntity, ...]
    asset_references: tuple[str, ...]
    thumbnail: bytes | None
    thumbnail_format: str | None


class CoreBridge:
    """Owns one initialized connection to Hammer5Tools.Core for a process."""

    _instance: Optional[CoreBridge] = None

    def __init__(self, interop=None, native_client=None) -> None:
        # Keep the accepted compatibility argument inert: CoreBridge only uses
        # the NativeAOT client for Core calls.
        self._interop = interop
        self._native_client = native_client

    @classmethod
    def instance(cls) -> CoreBridge:
        """Gets the process-wide bridge instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_vpk_index(self) -> VpkIndex:
        """Creates a Core-owned VPK index without exposing C# namespaces to callers."""
        return VpkIndex(self._smartprop_native())

    def probe(self) -> CoreStatus:
        """Loads the versioned Core contract without changing application state."""
        try:
            client = self._smartprop_native()
            return CoreStatus(True, version=f"native-abi-{client.ABI_VERSION}")
        except Exception as error:
            return CoreStatus(False, diagnostic=str(error))

    def evaluate_smartprop_expression(
        self,
        expression: str,
        *,
        variables: Mapping[str, float] | None = None,
        vectors: Mapping[str, Sequence[float]] | None = None,
        instance_index: int = 0,
        instance_count: int = 1,
        random_seed: int = 0,
        linear_scale: float = 1.0,
        default: float = 0.0,
    ) -> float:
        """Evaluates a SmartProp expression through the NativeAOT Core ABI."""
        return self._smartprop_native().evaluate_expression(
            expression,
            variables=dict(variables or {}),
            vectors={name: list(value) for name, value in (vectors or {}).items()},
            instance_index=instance_index,
            instance_count=instance_count,
            random_seed=random_seed,
            linear_scale=linear_scale,
            default=default,
        )

    def evaluate_smartprop(
        self,
        document: Mapping,
        *,
        nested_documents: Mapping[str, Mapping] | None = None,
        maximum_depth: int = 32,
        maximum_models: int = 100_000,
        cancellation=None,
    ) -> SmartPropEvaluation:
        """Evaluates an uncompiled SmartProp document through the NativeAOT Core ABI."""
        result = self._smartprop_native().evaluate(
            dict(document),
            None if nested_documents is None else dict(nested_documents),
            maximum_depth=maximum_depth,
            maximum_models=maximum_models,
            cancellation=cancellation,
        )
        models = tuple(self._convert_native_smartprop_model(model) for model in result["models"])
        widgets = tuple(self._convert_native_smartprop_widget(widget)
                        for widget in result.get("widgets", ()))
        diagnostics = tuple(
            f"{item['code']}: {item['message']}" for item in result["diagnostics"]
        )
        return SmartPropEvaluation(models, widgets, diagnostics)

    def create_smartprop_cancellation(self):
        """Create a cooperative cancellation handle for SmartProp evaluation."""
        return self._smartprop_native().create_cancellation()

    def serialize_smartprop(self, document: Mapping) -> str:
        """Serializes an uncompiled SmartProp document through the NativeAOT Core ABI."""
        return self._smartprop_native().serialize(dict(document))

    def deserialize_smartprop(self, text: str) -> dict:
        """Parses KeyValues3 SmartProp text through the NativeAOT Core ABI."""
        return self._smartprop_native().deserialize(text)

    def read_valve_map(self, path: str) -> ValveMapDocument:
        """Reads a VMAP through SourcePorter's shared Core reader contract."""
        document = self._smartprop_native().read_valve_map(path)
        thumbnail = document["thumbnail"]
        return ValveMapDocument(
            document["path"],
            self._convert_valve_map_node_json(document["world"]),
            tuple(self._convert_valve_map_node_json(node) for node in document["nodes"]),
            tuple(self._convert_valve_map_entity_json(entity) for entity in document["entities"]),
            tuple(document["assetReferences"]),
            None if thumbnail is None else base64.b64decode(thumbnail),
            document["thumbnailFormat"],
        )

    def rewrite_vmap_references(self, path: str, renames: Mapping[str, str]) -> VmapRewriteResult:
        """Rewrites VMAP body and prefix references through SourcePorter Core."""
        result = self._smartprop_native().rewrite_vmap_references(path, dict(renames))
        diagnostics = tuple(f"{item['code']}: {item['message']}" for item in result["diagnostics"])
        return VmapRewriteResult(bool(result["value"]), diagnostics)

    def write_unreal_map(self, path: str, request: Mapping) -> UnrealMapWriteResult:
        """Writes typed primitive Unreal placements through SourcePorter Core."""
        result = self._smartprop_native().write_unreal_map(dict(request), path)
        diagnostics = tuple(f"{item['code']}: {item['message']}" for item in result["diagnostics"])
        value = result["value"]
        if value is None:
            return UnrealMapWriteResult(0, None, None, diagnostics)
        return UnrealMapWriteResult(
            value["placementCount"],
            value["encoding"],
            value["encodingVersion"],
            diagnostics,
        )

    def unreal_info(self, content_dir: str) -> dict:
        """Project stats for an Unreal content directory."""
        return self._smartprop_native().unreal_info(content_dir)

    def unreal_list(self, content_dir: str, substring: str = "") -> list:
        """Every mounted file path containing ``substring``, sorted."""
        return self._smartprop_native().unreal_list(content_dir, substring)

    def unreal_dump(self, content_dir: str, object_path: str):
        """Raw JSON of every export in the package — can be large."""
        return self._smartprop_native().unreal_dump(content_dir, object_path)

    def unreal_iter_refs(self, content_dir: str, object_path: str) -> list:
        """Every object reference in a package, flat and deduplicated."""
        return self._smartprop_native().unreal_iter_refs(content_dir, object_path)

    def unreal_dump_scene(self, content_dir: str, map_path: str) -> dict:
        """Normalized actor list for a map."""
        return self._smartprop_native().unreal_dump_scene(content_dir, map_path)

    def unreal_dump_blueprint(self, content_dir: str, bp_path: str) -> dict:
        """Normalized Blueprint component tree."""
        return self._smartprop_native().unreal_dump_blueprint(content_dir, bp_path)

    def unreal_dump_material(self, content_dir: str, mat_path: str) -> dict:
        """Resolved material params (textures/scalars/vectors/switches/flags)."""
        return self._smartprop_native().unreal_dump_material(content_dir, mat_path)

    def unreal_export_landscape(self, content_dir: str, map_path: str, out_dir: str, flags: str = "all") -> dict:
        """Exports the map's first landscape actor into ``out_dir``."""
        return self._smartprop_native().unreal_export_landscape(content_dir, map_path, out_dir, flags)

    def vmap_merge_open(self, ours_path: str, theirs_path: str, base_path: str | None, allow_unrelated: bool) -> dict:
        """Loads and diffs ours/theirs (and an optional base) for a 3-way .vmap block merge."""
        return self._smartprop_native().vmap_merge_open(ours_path, theirs_path, base_path, allow_unrelated)

    def vmap_merge_resolve(self, handle: int, block_id: str, side: str) -> int:
        """Records a manual resolution for one conflicting block. Returns 0 on success."""
        return self._smartprop_native().vmap_merge_resolve(handle, block_id, side)

    def vmap_merge_resolve_all(self, handle: int, side: str) -> None:
        """Picks one side for every remaining conflict."""
        self._smartprop_native().vmap_merge_resolve_all(handle, side)

    def vmap_merge_write(self, handle: int, out_path: str) -> dict:
        """Applies the merge and writes it to out_path. Returns {orphaned: [...]}."""
        return self._smartprop_native().vmap_merge_write(handle, out_path)

    def vmap_merge_close(self, handle: int) -> None:
        """Releases a merge session's loaded documents."""
        self._smartprop_native().vmap_merge_close(handle)

    def source_porter_validate(
        self, cs2_dir: str, addon: str, *, log: Callable[[str], None], cancellation=None,
    ) -> int:
        """Validates an addon's assets. Returns 0 (clean), 1 (issues found), or a negative status."""
        return self._smartprop_native().source_porter_validate(
            {"cs2Dir": cs2_dir, "addon": addon}, log, cancellation=cancellation)

    def source_porter_force_import(
        self, cs2_dir: str, addon: str, asset_paths: Sequence[str], *,
        no_compile_assets: bool = False, log: Callable[[str], None], cancellation=None,
    ) -> int:
        """Force-imports specific Source 1 asset paths into an addon."""
        return self._smartprop_native().source_porter_force_import({
            "cs2Dir": cs2_dir, "addon": addon,
            "assetPaths": list(asset_paths), "noCompileAssets": no_compile_assets,
        }, log, cancellation=cancellation)

    def source_porter_repair(
        self, cs2_dir: str, addon: str, *, log: Callable[[str], None], cancellation=None,
    ) -> int:
        """Validates then re-imports an addon's missing assets."""
        return self._smartprop_native().source_porter_repair(
            {"cs2Dir": cs2_dir, "addon": addon}, log, cancellation=cancellation)

    def source_porter_port(
        self, cs2_dir: str, source_map: str, addon: str, *,
        bspsrc_location: str | None = None, threads: int = 1,
        no_bsp: bool = False, no_merge: bool = False, no_deps: bool = False, no_unpack: bool = False,
        compile_map: bool = False, no_compile_assets: bool = False, collapse_prefabs: bool = False,
        repair: bool = False, use_filelist: bool = False, compact: bool = True,
        log: Callable[[str], None], cancellation=None,
    ) -> int:
        """Ports a Source 1 map into a CS2 addon."""
        return self._smartprop_native().source_porter_port({
            "cs2Dir": cs2_dir, "sourceMap": source_map, "addon": addon,
            "bspsrcLocation": bspsrc_location, "threads": threads,
            "noBsp": no_bsp, "noMerge": no_merge, "noDeps": no_deps, "noUnpack": no_unpack,
            "compileMap": compile_map, "noCompileAssets": no_compile_assets,
            "collapsePrefabs": collapse_prefabs, "repair": repair,
            "useFilelist": use_filelist, "compact": compact,
        }, log, cancellation=cancellation)

    @classmethod
    def _convert_valve_map_node_json(cls, node: Mapping) -> ValveMapNode:
        return ValveMapNode(
            node["name"], node["className"], dict(node["properties"]),
            tuple(cls._convert_valve_map_node_json(child) for child in node["children"]),
        )

    @staticmethod
    def _convert_valve_map_entity_json(entity: Mapping) -> ValveMapEntity:
        return ValveMapEntity(
            entity["className"], entity["origin"], entity["angles"], dict(entity["properties"]),
        )

    def read_compiled_model(self, game_directory: str, active_addon: str, resource_path: str,
                            *, context_addon: str | None = None, maximum_texture_dimension: int = 1024,
                            base_color_only: bool = False, skin: int = 0) -> CompiledModelData | None:
        """Reads a compiled model into Python-native immutable data."""
        result = self._smartprop_native().read_compiled_model({
            "gameDirectory": game_directory,
            "activeAddon": active_addon,
            "resourcePath": resource_path,
            "contextAddon": context_addon,
            "maximumTextureDimension": maximum_texture_dimension,
            "baseColorOnly": base_color_only,
            "skin": skin,
        })
        model = result["value"]
        if model is None:
            return None
        diagnostics = tuple(f"{item['code']}: {item['message']}" for item in result["diagnostics"])
        if "verticesBytes" in model:
            import numpy as np
            vertices = np.frombuffer(base64.b64decode(model["verticesBytes"]), dtype=np.float32)
            normals = np.frombuffer(base64.b64decode(model["normalsBytes"]), dtype=np.float32)
            uvs = np.frombuffer(base64.b64decode(model["uvsBytes"]), dtype=np.float32)
            indices = np.frombuffer(base64.b64decode(model["indicesBytes"]), dtype=np.uint32)
        else:
            vertices = tuple(model.get("vertices", ()))
            normals = tuple(model.get("normals", ()))
            uvs = tuple(model.get("uvs", ()))
            indices = tuple(model.get("indices", ()))

        # Materials arrive once in "materials" and are referenced by index, so a material
        # shared by several submeshes is decoded once and the same object is handed to
        # every submesh that uses it — which is also what makes the viewport's
        # id()-keyed GPU texture dedupe work.
        materials = tuple(self._compiled_material(item) for item in model["materials"])
        return CompiledModelData(
            vertices, normals, uvs, indices,
            tuple(model["boundsMinimum"]), tuple(model["boundsMaximum"]),
            tuple(CompiledSubMeshData(item["indexOffset"], item["indexCount"], materials[item["materialIndex"]])
                  for item in model["submeshes"]), diagnostics)

    def read_compiled_model_material_groups(self, game_directory: str, active_addon: str,
                                            resource_path: str, context_addon: str | None = None) -> tuple[str, ...]:
        groups = self._smartprop_native().read_compiled_model_material_groups({
            "gameDirectory": game_directory,
            "activeAddon": active_addon,
            "resourcePath": resource_path,
            "contextAddon": context_addon,
        })
        return tuple(groups)

    def read_compiled_resource(self, vpk_path: str, resource_path: str, *, soundevents: bool = False) -> CompiledResourceData | None:
        """Reads and decodes a compiled sound or SoundEvent through Core."""
        result = self._smartprop_native().read_compiled_resource({
            "vpkPath": vpk_path,
            "resourcePath": resource_path,
            "soundEvents": soundevents,
        })
        content = result["value"]
        if content is None:
            return None
        diagnostics = tuple(f"{item['code']}: {item['message']}" for item in result["diagnostics"])
        return CompiledResourceData(base64.b64decode(content["data"]), content["format"], diagnostics)

    @classmethod
    def _compiled_material(cls, material: Mapping) -> CompiledMaterialData:
        return CompiledMaterialData(
            material["name"], tuple(cls._compiled_texture(material[name]) for name in
                                    ("baseColor", "normal", "metallicRoughness", "ambientOcclusion", "emissive")),
            tuple(material["baseColorFactor"]), material["metallicFactor"], material["roughnessFactor"],
            tuple(material["emissiveFactor"]), material["alphaMode"], material["alphaCutoff"],
            material["doubleSided"], material["wrapU"], material["wrapV"], material["uvSet"],
            tuple(material["uvScale"]), tuple(material["uvOffset"]),
            tuple(material["uvCenter"]), material["uvRotation"])

    @staticmethod
    def _compiled_texture(texture: Mapping | None) -> CompiledTextureData | None:
        if texture is None:
            return None
        return CompiledTextureData(texture["width"], texture["height"], base64.b64decode(texture["rgba"]))

    @staticmethod
    def _convert_smartprop_model(model) -> SmartPropModel:
        matrix = model.Transform
        transform = tuple(float(getattr(matrix, f"M{row}{column}")) for row in range(1, 5) for column in range(1, 5))
        tint = model.TintColor
        tint_color = None if tint is None else (float(tint.X), float(tint.Y), float(tint.Z), float(tint.W))
        material_group = None if model.MaterialGroup is None else str(model.MaterialGroup)
        return SmartPropModel(int(model.ElementId), str(model.ModelName), transform, material_group, tint_color)

    @staticmethod
    def _convert_native_smartprop_model(model: Mapping) -> SmartPropModel:
        tint = model.get("tintColor")
        return SmartPropModel(
            int(model["elementId"]),
            str(model["modelName"]),
            tuple(float(value) for value in model["transform"]),
            model.get("materialGroup"),
            None if tint is None else tuple(float(value) for value in tint),
            CoreBridge._convert_native_smartprop_deformer(model.get("deformer")),
        )

    @staticmethod
    def _convert_native_smartprop_deformer(deformer: Mapping | None) -> SmartPropDeformer | None:
        if deformer is None:
            return None
        return SmartPropDeformer(
            tuple(float(value) for value in deformer["size"]),
            tuple(tuple(float(value) for value in point) for point in deformer["controlPoints"]),
            tuple(tuple(float(value) for value in point) for point in deformer["midpoints"]),
            tuple(float(value) for value in deformer["deformerFrame"]),
            tuple(float(value) for value in deformer["volumeFrame"]),
        )

    @staticmethod
    def _convert_native_smartprop_widget(widget: Mapping) -> SmartPropWidget:
        return SmartPropWidget(
            str(widget["type"]),
            int(widget["elementId"]),
            tuple(float(value) for value in widget["transform"]),
            tuple(float(value) for value in widget["offset"]),
            tuple(float(value) for value in widget["minimumBounds"]),
            tuple(float(value) for value in widget["maximumBounds"]),
            tuple(float(value) for value in widget["axis"]),
            tuple(float(value) for value in widget["color"]),
            tuple(bool(value) for value in widget["handles"]),
            tuple(bool(value) for value in widget["activeAxes"]),
            float(widget["scale"]),
            float(widget["radius"]),
            float(widget["angle"]),
            float(widget["size"]),
            str(widget["shape"]),
            str(widget["name"]),
        )

    def _smartprop_native(self):
        if self._native_client is None:
            from core.native import SmartPropNativeClient

            self._native_client = SmartPropNativeClient()
        return self._native_client


class VpkIndex:
    """Owns a disposable native Core VPK index handle with Python-native arguments and results."""

    def __init__(self, native_client) -> None:
        self._native = native_client
        self._handle: int | None = native_client.vpk_open()

    @property
    def package_count(self) -> int:
        """Gets the number of mounted VPK archives."""
        self._require_open()
        return self._native.vpk_package_count(self._handle)

    def mount(self, path: str) -> None:
        """Mounts a VPK directory archive when it exists."""
        self._require_open()
        self._native.vpk_mount(self._handle, path)

    def add_loose_root(self, directory: str) -> None:
        """Adds a loose directory root when it exists."""
        self._require_open()
        self._native.vpk_add_loose_root(self._handle, directory)

    def exists(self, path: str) -> bool:
        """Gets whether a path exists in a mounted archive or loose root."""
        self._require_open()
        return self._native.vpk_exists(self._handle, path)

    def read_bytes(self, path: str) -> bytes | None:
        """Reads a file from a mounted archive or loose root."""
        self._require_open()
        return self._native.vpk_read_bytes(self._handle, path)

    def entries(self, suffixes: Sequence[str] = ()) -> tuple[tuple[str, int], ...]:
        """Returns Python-native paths and sizes from mounted VPK archives."""
        self._require_open()
        return self._native.vpk_entries(self._handle, tuple(suffixes))

    def close(self) -> None:
        """Releases archive handles. The bridge remains usable for new indexes."""
        if self._handle is not None:
            self._native.vpk_close(self._handle)
            self._handle = None

    def __enter__(self) -> VpkIndex:
        self._require_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _require_open(self) -> None:
        if self._handle is None:
            raise RuntimeError("VpkIndex is closed")
