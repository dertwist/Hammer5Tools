"""Python-facing adapters for the UI-neutral Hammer5Tools .NET Core."""

from __future__ import annotations

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

    def __init__(self, interop=None) -> None:
        self._interop = interop or DotNetInterop()
        self._assembly = None
        self._source_porter_assembly = None

    @classmethod
    def instance(cls) -> CoreBridge:
        """Gets the process-wide bridge instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_vpk_index(self) -> VpkIndex:
        """Creates a Core-owned VPK index without exposing C# namespaces to callers."""
        self._ensure_loaded()

        index_type = self._assembly.GetType("Hammer5Tools.Core.Resources.VpkIndex")
        if index_type is None:
            raise RuntimeError("Hammer5Tools.Core does not provide Resources.VpkIndex")

        import System
        return VpkIndex(System.Activator.CreateInstance(index_type))

    def probe(self) -> CoreStatus:
        """Loads and invokes the versioned Core contract without changing application state."""
        try:
            self._ensure_loaded()
            api_type = self._assembly.GetType("Hammer5Tools.Core.CoreApi")
            if api_type is None:
                raise CoreBridgeError("Hammer5Tools.Core does not provide CoreApi")

            result = api_type.GetMethod("Probe").Invoke(None, None)
            if not bool(result.IsSuccess):
                diagnostic = next((str(item.Message) for item in result.Diagnostics), "Core probe failed")
                return CoreStatus(False, diagnostic=diagnostic)
            return CoreStatus(True, version=str(result.Value))
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
        """Evaluates a SmartProp expression with Python-native context values."""
        self._ensure_loaded()

        from System import Single
        from System.Collections.Generic import Dictionary
        from System.Numerics import Vector4
        from Hammer5Tools.Core.SmartProps import SmartPropContext, SmartPropExpression

        scalar_values = Dictionary[str, Single]()
        for name, value in (variables or {}).items():
            scalar_values.Add(name, float(value))

        vector_values = Dictionary[str, Vector4]()
        for name, value in (vectors or {}).items():
            components = [float(component) for component in value[:4]]
            components.extend([0.0] * (4 - len(components)))
            vector_values.Add(name, Vector4(*components))

        context = SmartPropContext(
            scalar_values,
            vector_values,
            instance_index,
            instance_count,
            random_seed,
            linear_scale,
            None,
        )
        return float(SmartPropExpression.Evaluate(expression, context, float(default)))

    def evaluate_smartprop(
        self,
        document: Mapping,
        *,
        nested_documents: Mapping[str, Mapping] | None = None,
    ) -> SmartPropEvaluation:
        """Evaluates an uncompiled SmartProp document through Hammer5Tools Core and VRF."""
        self._ensure_loaded()

        from Hammer5Tools.Core.SmartProps import SmartPropEvaluator

        document_json = json.dumps(document, separators=(",", ":"))
        if nested_documents is None:
            result = SmartPropEvaluator.EvaluateJson(document_json)
        else:
            nested_json = json.dumps(nested_documents, separators=(",", ":"))
            result = SmartPropEvaluator.EvaluateJson(document_json, nested_json)
        models = tuple(self._convert_smartprop_model(model) for model in result.Models)
        diagnostics = tuple(f"{item.Code}: {item.Message}" for item in result.Diagnostics)
        return SmartPropEvaluation(models, diagnostics)

    def serialize_smartprop(self, document: Mapping) -> str:
        """Serializes an uncompiled SmartProp document as KeyValues3 text."""
        self._ensure_loaded()

        from Hammer5Tools.Core.SmartProps import SmartPropDocumentSerializer

        return str(SmartPropDocumentSerializer.SerializeJson(
            json.dumps(document, separators=(",", ":")),
        ))

    def deserialize_smartprop(self, text: str) -> dict:
        """Parses KeyValues3 SmartProp text into a Python-native document."""
        self._ensure_loaded()

        from Hammer5Tools.Core.SmartProps import SmartPropDocumentSerializer

        return json.loads(str(SmartPropDocumentSerializer.DeserializeText(text)))

    def read_valve_map(self, path: str) -> ValveMapDocument:
        """Reads a VMAP through SourcePorter's shared Core reader contract."""
        assembly = self._ensure_source_porter_loaded()
        reader_type = assembly.GetType("SourcePorter.Core.Vmap.ValveMapReader")
        if reader_type is None:
            raise CoreBridgeError("SourcePorter.Core does not provide Vmap.ValveMapReader")

        import System

        reader = System.Activator.CreateInstance(reader_type)
        document = reader.Read(path)
        world = self._convert_valve_map_node(document.World)
        nodes = tuple(self._convert_valve_map_node(node) for node in document.Nodes)
        entities = tuple(self._convert_valve_map_entity(entity) for entity in document.Entities)
        asset_references = tuple(str(reference) for reference in document.AssetReferences)
        thumbnail = None if document.Thumbnail is None else bytes(document.Thumbnail)
        thumbnail_format = None if document.ThumbnailFormat is None else str(document.ThumbnailFormat)
        return ValveMapDocument(
            str(document.Path),
            world,
            nodes,
            entities,
            asset_references,
            thumbnail,
            thumbnail_format,
        )

    def rewrite_vmap_references(self, path: str, renames: Mapping[str, str]) -> VmapRewriteResult:
        """Rewrites VMAP body and prefix references through SourcePorter Core."""
        assembly = self._ensure_source_porter_loaded()
        rewriter_type = assembly.GetType("SourcePorter.Core.Vmap.VmapReferenceRewriter")
        if rewriter_type is None:
            raise CoreBridgeError("SourcePorter.Core does not provide Vmap.VmapReferenceRewriter")

        from System.Collections.Generic import Dictionary

        native_renames = Dictionary[str, str]()
        for old_path, new_path in renames.items():
            native_renames.Add(old_path, new_path)
        result = rewriter_type.GetMethod("Rewrite").Invoke(None, [path, native_renames])
        diagnostics = tuple(f"{item.Code}: {item.Message}" for item in result.Diagnostics)
        return VmapRewriteResult(bool(result.Value), diagnostics)

    def write_unreal_map(self, path: str, request: Mapping) -> UnrealMapWriteResult:
        """Writes typed primitive Unreal placements through SourcePorter Core."""
        assembly = self._ensure_source_porter_loaded()
        writer_type = assembly.GetType("SourcePorter.Core.Vmap.UnrealMapWriter")
        if writer_type is None:
            raise CoreBridgeError("SourcePorter.Core does not provide Vmap.UnrealMapWriter")

        result = writer_type.GetMethod("WriteJson").Invoke(
            None,
            [json.dumps(request, separators=(",", ":")), path],
        )
        diagnostics = tuple(f"{item.Code}: {item.Message}" for item in result.Diagnostics)
        value = result.Value
        if value is None:
            return UnrealMapWriteResult(0, None, None, diagnostics)
        return UnrealMapWriteResult(
            int(value.PlacementCount),
            str(value.Encoding),
            int(value.EncodingVersion),
            diagnostics,
        )

    def read_compiled_model(self, game_directory: str, active_addon: str, resource_path: str,
                            *, context_addon: str | None = None, maximum_texture_dimension: int = 1024,
                            base_color_only: bool = False, skin: int = 0) -> CompiledModelData | None:
        """Reads a compiled model into Python-native immutable data."""
        self._ensure_loaded()
        reader_type = self._assembly.GetType("Hammer5Tools.Core.Resources.CompiledModelReader")
        import System
        reader = System.Activator.CreateInstance(reader_type, game_directory, active_addon)
        result = reader.Read(resource_path, context_addon, maximum_texture_dimension, base_color_only, skin)
        if not bool(result.IsSuccess) or result.Value is None:
            return None
        model = result.Value
        diagnostics = tuple(f"{item.Code}: {item.Message}" for item in result.Diagnostics)
        return CompiledModelData(
            tuple(float(value) for value in model.Vertices), tuple(float(value) for value in model.Normals),
            tuple(float(value) for value in model.Uvs), tuple(int(value) for value in model.Indices),
            self._vector(model.BoundsMinimum, 3), self._vector(model.BoundsMaximum, 3),
            tuple(CompiledSubMeshData(int(item.IndexOffset), int(item.IndexCount), self._compiled_material(item.Material))
                  for item in model.SubMeshes), diagnostics)

    def read_compiled_model_material_groups(self, game_directory: str, active_addon: str,
                                            resource_path: str, context_addon: str | None = None) -> tuple[str, ...]:
        self._ensure_loaded()
        reader_type = self._assembly.GetType("Hammer5Tools.Core.Resources.CompiledModelReader")
        import System
        reader = System.Activator.CreateInstance(reader_type, game_directory, active_addon)
        result = reader.ReadMaterialGroups(resource_path, context_addon)
        return tuple(str(value) for value in result.Value) if bool(result.IsSuccess) else ()

    def read_compiled_resource(self, vpk_path: str, resource_path: str, *, soundevents: bool = False) -> CompiledResourceData | None:
        """Reads and decodes a compiled sound or SoundEvent through Core."""
        self._ensure_loaded()
        index_type = self._assembly.GetType("Hammer5Tools.Core.Resources.VpkIndex")
        reader_type = self._assembly.GetType("Hammer5Tools.Core.Resources.CompiledResourceReader")
        import System
        index = System.Activator.CreateInstance(index_type)
        try:
            index.MountVpk(vpk_path)
            reader = System.Activator.CreateInstance(reader_type, index)
            result = reader.ReadSoundEvents(resource_path) if soundevents else reader.ReadSound(resource_path)
            if not bool(result.IsSuccess) or result.Value is None:
                return None
            diagnostics = tuple(f"{item.Code}: {item.Message}" for item in result.Diagnostics)
            return CompiledResourceData(bytes(result.Value.Data), str(result.Value.Format), diagnostics)
        finally:
            index.Dispose()

    @classmethod
    def _compiled_material(cls, material) -> CompiledMaterialData:
        return CompiledMaterialData(
            str(material.Name), tuple(cls._compiled_texture(getattr(material, name)) for name in
                                      ("BaseColor", "Normal", "MetallicRoughness", "AmbientOcclusion", "Emissive")),
            cls._vector(material.BaseColorFactor, 4), float(material.MetallicFactor), float(material.RoughnessFactor),
            cls._vector(material.EmissiveFactor, 3), str(material.AlphaMode), float(material.AlphaCutoff),
            bool(material.DoubleSided), int(material.WrapU), int(material.WrapV), int(material.UvSet),
            cls._vector(material.UvScale, 2), cls._vector(material.UvOffset, 2),
            cls._vector(material.UvCenter, 2), float(material.UvRotation))

    @staticmethod
    def _compiled_texture(texture) -> CompiledTextureData | None:
        return None if texture is None else CompiledTextureData(int(texture.Width), int(texture.Height), bytes(texture.Rgba))

    @staticmethod
    def _vector(value, count: int) -> tuple[float, ...]:
        return tuple(float(getattr(value, component)) for component in "XYZW"[:count])

    @staticmethod
    def _convert_smartprop_model(model) -> SmartPropModel:
        matrix = model.Transform
        transform = tuple(float(getattr(matrix, f"M{row}{column}")) for row in range(1, 5) for column in range(1, 5))
        tint = model.TintColor
        tint_color = None if tint is None else (float(tint.X), float(tint.Y), float(tint.Z), float(tint.W))
        material_group = None if model.MaterialGroup is None else str(model.MaterialGroup)
        return SmartPropModel(int(model.ElementId), str(model.ModelName), transform, material_group, tint_color)

    @staticmethod
    def _convert_valve_map_entity(entity) -> ValveMapEntity:
        properties = {str(item.Key): str(item.Value) for item in entity.Properties}
        origin = None if entity.Origin is None else str(entity.Origin)
        angles = None if entity.Angles is None else str(entity.Angles)
        return ValveMapEntity(str(entity.ClassName), origin, angles, properties)

    @classmethod
    def _convert_valve_map_node(cls, node) -> ValveMapNode:
        properties = {str(item.Key): str(item.Value) for item in node.Properties}
        children = tuple(cls._convert_valve_map_node(child) for child in node.Children)
        return ValveMapNode(str(node.Name), str(node.ClassName), properties, children)

    def _ensure_loaded(self) -> None:
        if self._assembly is not None:
            return

        try:
            self._assembly = self._interop.setup_hammer5tools_core()
        except Exception as error:
            raise CoreBridgeError(f"Hammer5Tools Core is unavailable: {error}") from error

    def _ensure_source_porter_loaded(self):
        if self._source_porter_assembly is not None:
            return self._source_porter_assembly

        try:
            self._source_porter_assembly = self._interop.setup_source_porter()
            return self._source_porter_assembly
        except Exception as error:
            raise CoreBridgeError(f"SourcePorter Core is unavailable: {error}") from error


class VpkIndex:
    """Owns a disposable Core VPK index with Python-native arguments and results."""

    def __init__(self, index) -> None:
        self._index = index

    @property
    def package_count(self) -> int:
        """Gets the number of mounted VPK archives."""
        self._require_open()
        return int(self._index.PackageCount)

    def mount(self, path: str) -> None:
        """Mounts a VPK directory archive when it exists."""
        self._require_open()
        self._index.MountVpk(path)

    def add_loose_root(self, directory: str) -> None:
        """Adds a loose directory root when it exists."""
        self._require_open()
        self._index.AddLooseRoot(directory)

    def exists(self, path: str) -> bool:
        """Gets whether a path exists in a mounted archive or loose root."""
        self._require_open()
        return bool(self._index.Exists(path))

    def read_bytes(self, path: str) -> bytes | None:
        """Reads a file from a mounted archive or loose root."""
        self._require_open()
        data = self._index.TryReadBytes(path)
        return None if data is None else bytes(data)

    def entries(self, suffixes: Sequence[str] = ()) -> tuple[tuple[str, int], ...]:
        """Returns Python-native paths and sizes from mounted VPK archives."""
        self._require_open()

        from System.Collections.Generic import List

        native_suffixes = List[str]()
        for suffix in suffixes:
            native_suffixes.Add(suffix)
        return tuple(
            (str(entry.Path), int(entry.Size))
            for entry in self._index.EnumerateEntries(native_suffixes)
        )

    def close(self) -> None:
        """Releases archive handles. The bridge remains usable for new indexes."""
        if self._index is not None:
            self._index.Dispose()
            self._index = None

    def __enter__(self) -> VpkIndex:
        self._require_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _require_open(self) -> None:
        if self._index is None:
            raise RuntimeError("VpkIndex is closed")
