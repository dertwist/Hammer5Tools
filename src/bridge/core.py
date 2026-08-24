"""Python-facing adapters for the UI-neutral Hammer5Tools .NET Core."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Optional

from src.dotnet import DotNetInterop


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


class CoreBridge:
    """Owns one initialized connection to Hammer5Tools.Core for a process."""

    _instance: Optional[CoreBridge] = None

    def __init__(self, interop=None) -> None:
        self._interop = interop or DotNetInterop()
        self._assembly = None

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

    @staticmethod
    def _convert_smartprop_model(model) -> SmartPropModel:
        matrix = model.Transform
        transform = tuple(float(getattr(matrix, f"M{row}{column}")) for row in range(1, 5) for column in range(1, 5))
        tint = model.TintColor
        tint_color = None if tint is None else (float(tint.X), float(tint.Y), float(tint.Z), float(tint.W))
        material_group = None if model.MaterialGroup is None else str(model.MaterialGroup)
        return SmartPropModel(int(model.ElementId), str(model.ModelName), transform, material_group, tint_color)

    def _ensure_loaded(self) -> None:
        if self._assembly is not None:
            return

        try:
            self._assembly = self._interop.setup_hammer5tools_core()
        except Exception as error:
            raise CoreBridgeError(f"Hammer5Tools Core is unavailable: {error}") from error


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
