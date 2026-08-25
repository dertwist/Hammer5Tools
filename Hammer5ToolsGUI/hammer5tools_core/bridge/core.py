"""Python-facing adapters for the UI-neutral Hammer5Tools .NET Core."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Optional

from hammer5tools_core.dotnet import DotNetInterop


class CoreBridgeError(RuntimeError):
    """Raised when the Hammer5Tools Core contract cannot be loaded or invoked."""


@dataclass(frozen=True)
class CoreStatus:
    """Python-native result of probing the Hammer5Tools Core contract."""

    available: bool
    version: str | None = None
    diagnostic: str | None = None


@dataclass(frozen=True)
class SmartPropModel:
    """Python-native model produced by Core SmartProp evaluation."""

    element_id: int
    model_name: str
    transform: tuple[float, ...]
    material_group: str | None
    tint_color: tuple[float, float, float, float] | None


@dataclass(frozen=True)
class SmartPropEvaluation:
    """Python-native SmartProp evaluation result."""

    models: tuple[SmartPropModel, ...]
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
    vertices: tuple[float, ...]
    normals: tuple[float, ...]
    uvs: tuple[float, ...]
    indices: tuple[int, ...]
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
        self._interop = interop or DotNetInterop()
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
        diagnostics = tuple(
            f"{item['code']}: {item['message']}" for item in result["diagnostics"]
        )
        return SmartPropEvaluation(models, diagnostics)

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
        return CompiledModelData(
            tuple(model["vertices"]), tuple(model["normals"]), tuple(model["uvs"]), tuple(model["indices"]),
            tuple(model["boundsMinimum"]), tuple(model["boundsMaximum"]),
            tuple(CompiledSubMeshData(item["indexOffset"], item["indexCount"], self._compiled_material(item["material"]))
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
        )

    def _smartprop_native(self):
        if self._native_client is None:
            from hammer5tools_core.native import SmartPropNativeClient

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
