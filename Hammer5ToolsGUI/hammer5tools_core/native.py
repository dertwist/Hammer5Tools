"""Thin ctypes client for the versioned Hammer5Tools NativeAOT ABI."""

from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path

from hammer5tools_core.runtime_paths import resolve_runtime_paths


class NativeCoreError(RuntimeError):
    """Raised when the NativeAOT Core library cannot be loaded or invoked."""


class NativeCancellation:
    """Owns one cooperative Native Core cancellation handle."""

    def __init__(self, client: SmartPropNativeClient, handle: int) -> None:
        self._client = client
        self.handle = handle

    def cancel(self) -> None:
        """Request cancellation of the associated operation."""
        if self.handle and self._client._library.h5t_core_cancel(self.handle) != 0:
            raise NativeCoreError("The Native Core cancellation handle is invalid")

    def close(self) -> None:
        """Release the native cancellation handle."""
        if self.handle:
            self._client._library.h5t_core_release_cancellation(self.handle)
            self.handle = 0

    def __enter__(self) -> NativeCancellation:
        return self

    def __exit__(self, *_args) -> None:
        self.close()


class SmartPropNativeClient:
    """Marshals primitive SmartProp requests across the stable C ABI."""

    ABI_VERSION = 1
    LIBRARY_NAME = "Hammer5Tools.Native.dll"

    def __init__(self, library_path: str | os.PathLike[str] | None = None) -> None:
        path = Path(library_path).resolve() if library_path else self._find_library()
        if path is None:
            raise NativeCoreError(
                "Hammer5Tools Native Core was not found; publish Hammer5Tools.Native first"
            )

        self._dll_directory = None
        if hasattr(os, "add_dll_directory"):
            self._dll_directory = os.add_dll_directory(str(path.parent))
        try:
            self._library = ctypes.CDLL(str(path))
        except OSError as error:
            raise NativeCoreError(f"Failed to load {path}: {error}") from error

        self._configure_functions()
        version = int(self._library.h5t_core_abi_version())
        if version != self.ABI_VERSION:
            raise NativeCoreError(
                f"Unsupported Hammer5Tools Core ABI {version}; expected {self.ABI_VERSION}"
            )

    def evaluate(
        self,
        document: dict,
        nested_documents: dict[str, dict] | None = None,
        *,
        maximum_depth: int = 32,
        maximum_models: int = 100_000,
        cancellation: NativeCancellation | None = None,
    ) -> dict:
        """Evaluate an editor document and return a primitive result dictionary."""
        document_bytes = self._json_bytes(document)
        nested_bytes = (
            None if nested_documents is None else self._json_bytes(nested_documents)
        )
        payload = self._invoke(
            self._library.h5t_smartprop_evaluate_json,
            *self._buffer_arguments(document_bytes),
            *self._buffer_arguments(nested_bytes),
            int(maximum_depth),
            int(maximum_models),
            0 if cancellation is None else cancellation.handle,
        )
        return json.loads(payload)

    def create_cancellation(self) -> NativeCancellation:
        """Create a cooperative cancellation handle for an evaluation call."""
        handle = int(self._library.h5t_core_create_cancellation())
        if handle <= 0:
            raise NativeCoreError("Native Core could not create a cancellation handle")
        return NativeCancellation(self, handle)

    def evaluate_expression(
        self,
        expression: str,
        *,
        variables: dict[str, float] | None = None,
        vectors: dict[str, list[float]] | None = None,
        instance_index: int = 0,
        instance_count: int = 1,
        random_seed: int = 0,
        linear_scale: float = 1.0,
        default: float = 0.0,
    ) -> float:
        """Evaluate one expression using only primitive context values."""
        request = self._json_bytes({
            "expression": expression,
            "variables": variables or {},
            "vectors": vectors or {},
            "instanceIndex": instance_index,
            "instanceCount": instance_count,
            "randomSeed": random_seed,
            "linearScale": linear_scale,
            "default": default,
        })
        return float(self._invoke(
            self._library.h5t_smartprop_evaluate_expression,
            *self._buffer_arguments(request),
        ))

    def serialize(self, document: dict) -> str:
        """Serialize a primitive editor document to KV3 text."""
        payload = self._json_bytes(document)
        return self._invoke(
            self._library.h5t_smartprop_serialize_json,
            *self._buffer_arguments(payload),
        )

    def deserialize(self, text: str) -> dict:
        """Deserialize KV3 text to a primitive editor document."""
        payload = text.encode("utf-8")
        return json.loads(self._invoke(
            self._library.h5t_smartprop_deserialize_text,
            *self._buffer_arguments(payload),
        ))

    def _configure_functions(self) -> None:
        pointer = ctypes.c_void_p
        length = ctypes.c_int
        output = ctypes.POINTER(pointer)
        output_length = ctypes.POINTER(length)

        self._library.h5t_core_abi_version.argtypes = []
        self._library.h5t_core_abi_version.restype = ctypes.c_int
        self._library.h5t_core_release.argtypes = [pointer]
        self._library.h5t_core_release.restype = None
        self._library.h5t_core_create_cancellation.argtypes = []
        self._library.h5t_core_create_cancellation.restype = ctypes.c_longlong
        self._library.h5t_core_cancel.argtypes = [ctypes.c_longlong]
        self._library.h5t_core_cancel.restype = ctypes.c_int
        self._library.h5t_core_release_cancellation.argtypes = [ctypes.c_longlong]
        self._library.h5t_core_release_cancellation.restype = None
        self._library.h5t_smartprop_evaluate_json.argtypes = [
            pointer, length, pointer, length, length, length, ctypes.c_longlong,
            output, output_length,
        ]
        self._library.h5t_smartprop_evaluate_json.restype = ctypes.c_int
        for name in (
            "h5t_smartprop_evaluate_expression",
            "h5t_smartprop_serialize_json",
            "h5t_smartprop_deserialize_text",
        ):
            function = getattr(self._library, name)
            function.argtypes = [pointer, length, output, output_length]
            function.restype = ctypes.c_int

    def _invoke(self, function, *arguments) -> str:
        output = ctypes.c_void_p()
        output_length = ctypes.c_int()
        status = function(
            *arguments,
            ctypes.byref(output),
            ctypes.byref(output_length),
        )
        try:
            payload = (
                ctypes.string_at(output.value, output_length.value).decode("utf-8")
                if output.value else ""
            )
        finally:
            if output.value:
                self._library.h5t_core_release(output)

        if status != 0:
            try:
                message = json.loads(payload).get("error", payload)
            except json.JSONDecodeError:
                message = payload
            raise NativeCoreError(message or f"Native Core call failed with status {status}")
        return payload

    @staticmethod
    def _json_bytes(value: object) -> bytes:
        return json.dumps(value, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _buffer_arguments(payload: bytes | None):
        if payload is None:
            return None, 0
        buffer = ctypes.create_string_buffer(payload)
        return buffer, len(payload)

    @classmethod
    def _find_library(cls) -> Path | None:
        override = os.environ.get("H5T_SMARTPROP_NATIVE")
        paths = resolve_runtime_paths()
        candidates = [
            Path(override) if override else None,
            paths.runtime_resource("smartprop_native", cls.LIBRARY_NAME),
            paths.application_resource("smartprop_native", cls.LIBRARY_NAME),
            paths.install_root / "Hammer5ToolsCore" / "CSharp" / "Hammer5Tools.Native" / "publish" / cls.LIBRARY_NAME,
            paths.install_root / "Hammer5ToolsCore" / "CSharp" / "Hammer5Tools.Native" / "bin" / "Release" / "win-x64" / "native" / cls.LIBRARY_NAME,
        ]
        return next((candidate.resolve() for candidate in candidates if candidate and candidate.is_file()), None)
