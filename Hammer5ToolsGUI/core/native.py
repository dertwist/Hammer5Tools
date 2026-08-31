"""Thin ctypes client for the versioned Hammer5Tools NativeAOT ABI."""

from __future__ import annotations

import ctypes
import json
import os
from collections.abc import Callable
from pathlib import Path

from core.native_binary import (
    NativeBinaryError,
    decode_error,
    decode_navmesh_radar,
    decode_snapshot_document,
    decode_text_result,
    decode_vmap_rewrite,
    decode_vmap_scene,
    encode_navmesh_radar_request,
    encode_snapshot_document,
    encode_snapshot_generate_request,
    encode_snapshot_text_request,
    encode_vmap_rewrite_request,
    encode_vmap_scene_request,
)
from core.runtime_paths import resolve_runtime_paths

# Matches the C ABI's `void (*)(const uint8_t* line, int32_t line_length)` log
# callback (SourcePorterApi.cs). Module-level so every streaming call shares one
# ctypes function type instead of re-deriving it per call.
_LOG_CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int)


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

    ABI_VERSION = 2
    LIBRARY_NAME = "Hammer5Tools.Core.dll"

    def __init__(self, library_path: str | os.PathLike[str] | None = None) -> None:
        path = Path(library_path).resolve() if library_path else self._find_library()
        if path is None:
            raise NativeCoreError(
                "Hammer5Tools Native Core was not found; publish Hammer5Tools.Core first"
            )

        self._dll_directories = []
        if hasattr(os, "add_dll_directory"):
            self._dll_directories.append(os.add_dll_directory(str(path.parent)))
            if path.parent.parent.is_dir():
                self._dll_directories.append(os.add_dll_directory(str(path.parent.parent)))
        # NativeAOT's own P/Invoke module resolution fails to find sibling native
        # DLLs (e.g. libSkiaSharp.dll) when this library is loaded via ctypes from
        # a non-.NET host process, even with add_dll_directory pointed at the same
        # folder — it raises BadImageFormatException instead of DllNotFoundException.
        # Loading the dependency ourselves first makes Windows resolve later
        # same-named LoadLibrary calls (including NativeAOT's internal one) against
        # the already-loaded module instead of re-searching.
        for candidate_dir in (path.parent, path.parent.parent, path.parent.parent / "runtimes" / "win-x64" / "native"):
            skia = candidate_dir / "libSkiaSharp.dll"
            if skia.is_file():
                try:
                    ctypes.CDLL(str(skia))
                except OSError:
                    pass
                break
        try:
            self._library = ctypes.CDLL(str(path))
        except OSError as error:
            raise NativeCoreError(f"Failed to load {path}: {error}") from error

        self._library.h5t_core_abi_version.argtypes = []
        self._library.h5t_core_abi_version.restype = ctypes.c_int
        version = int(self._library.h5t_core_abi_version())
        if version != self.ABI_VERSION:
            raise NativeCoreError(
                f"Unsupported Hammer5Tools Core ABI {version}; expected {self.ABI_VERSION}"
            )
        self._configure_functions()

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

    def vpk_open(self) -> int:
        """Opens a native VPK index handle. Must be closed with :meth:`vpk_close`."""
        return int(self._library.h5t_vpk_open())

    def vpk_close(self, handle: int) -> None:
        """Releases a native VPK index handle."""
        self._library.h5t_vpk_close(handle)

    def vpk_mount(self, handle: int, path: str) -> None:
        """Mounts a `_dir.vpk` archive. Missing paths are ignored."""
        self._invoke(self._library.h5t_vpk_mount, handle, *self._buffer_arguments(path.encode("utf-8")))

    def vpk_add_loose_root(self, handle: int, directory: str) -> None:
        """Adds a loose directory root to search. Missing directories are ignored."""
        self._invoke(self._library.h5t_vpk_add_loose_root, handle, *self._buffer_arguments(directory.encode("utf-8")))

    def vpk_exists(self, handle: int, path: str) -> bool:
        """Gets whether a path exists in a mounted archive or loose root."""
        buffer, length = self._buffer_arguments(path.encode("utf-8"))
        status = self._library.h5t_vpk_exists(handle, buffer, length)
        if status < 0:
            raise NativeCoreError(f"Invalid VPK handle {handle}")
        return bool(status)

    def vpk_package_count(self, handle: int) -> int:
        """Gets the number of mounted VPK archives."""
        count = self._library.h5t_vpk_package_count(handle)
        if count < 0:
            raise NativeCoreError(f"Invalid VPK handle {handle}")
        return count

    def vpk_read_bytes(self, handle: int, path: str) -> bytes | None:
        """Reads a file's raw bytes from a mounted archive or loose root, or ``None`` when absent."""
        buffer, length = self._buffer_arguments(path.encode("utf-8"))
        status, payload = self._invoke_raw(self._library.h5t_vpk_read_bytes, handle, buffer, length)
        if status == 1:
            return None
        if status != 0:
            self._raise_native_error(status, payload)
        return payload

    def vpk_entries(self, handle: int, suffixes: tuple[str, ...] = ()) -> tuple[tuple[str, int], ...]:
        """Enumerates mounted VPK entries whose paths end with one of ``suffixes``."""
        payload = self._invoke(
            self._library.h5t_vpk_entries_json, handle,
            *self._buffer_arguments(self._json_bytes(list(suffixes))),
        )
        return tuple((path, size) for path, size in json.loads(payload))

    def read_compiled_model(self, request: dict) -> dict:
        """Reads a compiled model. Returns {"value": {...} | None, "diagnostics": [...]}."""
        return json.loads(self._invoke(
            self._library.h5t_compiled_model_read_json, *self._buffer_arguments(self._json_bytes(request)),
        ))

    def read_compiled_material(self, request: dict) -> dict:
        """Reads one compiled material. Returns {"value": {...} | None, "diagnostics": [...]}."""
        return json.loads(self._invoke(
            self._library.h5t_compiled_material_read_json, *self._buffer_arguments(self._json_bytes(request)),
        ))

    def read_compiled_texture(self, request: dict) -> dict:
        """Reads one compiled texture. Returns {"value": {...} | None, "diagnostics": [...]}."""
        return json.loads(self._invoke(
            self._library.h5t_compiled_texture_read_json, *self._buffer_arguments(self._json_bytes(request)),
        ))

    def read_compiled_model_material_groups(self, request: dict) -> list[str]:
        """Reads the material group names of a compiled model."""
        return json.loads(self._invoke(
            self._library.h5t_compiled_model_material_groups_json,
            *self._buffer_arguments(self._json_bytes(request)),
        ))

    def read_compiled_resource(self, request: dict) -> dict:
        """Reads and decodes a compiled sound or SoundEvent. Returns {"value": {...} | None, "diagnostics": [...]}."""
        return json.loads(self._invoke(
            self._library.h5t_compiled_resource_read_json, *self._buffer_arguments(self._json_bytes(request)),
        ))

    def read_valve_map(self, path: str) -> dict:
        """Reads an uncompiled VMAP into the shared read-only projection (path/world/nodes/entities/...)."""
        return json.loads(self._invoke(
            self._library.h5t_vmap_read_json, *self._buffer_arguments(path.encode("utf-8")),
        ))

    def read_valve_map_asset_references(self, path: str) -> list[str]:
        """Reads only the asset-reference list from an uncompiled VMAP."""
        return json.loads(self._invoke(
            self._library.h5t_vmap_read_asset_references_json, *self._buffer_arguments(path.encode("utf-8")),
        ))

    def read_valve_map_scene(self, path: str) -> dict:
        """Reads an uncompiled VMAP into flattened, drawable scene geometry."""
        return decode_vmap_scene(self._invoke_binary(
            self._library.h5t_vmap_read_scene_binary,
            *self._buffer_arguments(encode_vmap_scene_request(path)),
        ))

    def read_vsnap(self, text: str) -> dict:
        return decode_snapshot_document(self._invoke_binary(
            self._library.h5t_vsnap_read_binary,
            *self._buffer_arguments(encode_snapshot_text_request(text)),
        ))

    def serialize_vsnap(self, document: dict) -> str:
        return decode_text_result(self._invoke_binary(
            self._library.h5t_vsnap_serialize_binary,
            *self._buffer_arguments(encode_snapshot_document(document)),
        ))

    def generate_vsnap(self, request: dict) -> dict:
        return decode_snapshot_document(self._invoke_binary(
            self._library.h5t_vsnap_generate_binary,
            *self._buffer_arguments(encode_snapshot_generate_request(request)),
        ))

    def light_vsnap(self, request: dict) -> dict:
        return json.loads(self._invoke(
            self._library.h5t_vsnap_light_json,
            *self._buffer_arguments(self._json_bytes(request)),
        ))

    def generate_vsnap_lightning(self, request: dict) -> dict:
        return json.loads(self._invoke(
            self._library.h5t_vsnap_lightning_json,
            *self._buffer_arguments(self._json_bytes(request)),
        ))

    def vsnap_attributes(self) -> dict:
        """Returns the particle attributes a VSnap stream can name, straight from Core."""
        return json.loads(self._invoke(self._library.h5t_vsnap_attributes_json))

    def rewrite_vmap_references(self, path: str, renames: dict) -> dict:
        """Rewrites content-relative asset paths in a VMAP. Returns {"value": bool | None, "diagnostics": [...]}."""
        return decode_vmap_rewrite(self._invoke_binary(
            self._library.h5t_vmap_rewrite_references_binary,
            *self._buffer_arguments(encode_vmap_rewrite_request(path, renames)),
        ))

    def generate_navmesh_radar(
        self, request: dict, progress: Callable[[float, str], None] | None = None,
    ) -> dict:
        """Generates radar geometry from compiled NAV data, streaming ``(fraction, stage)``
        progress through ``progress`` while the native call runs."""
        def on_progress(line: ctypes.c_void_p, line_length: int) -> None:
            # A Python exception must never unwind back through the native call frame.
            try:
                fraction, _, stage = ctypes.string_at(line, line_length).decode(
                    "utf-8", errors="replace").partition("|")
                progress(float(fraction), stage)
            except Exception:
                pass

        callback = _LOG_CALLBACK_TYPE(on_progress) if progress is not None else _LOG_CALLBACK_TYPE()
        return decode_navmesh_radar(self._invoke_binary(
            self._library.h5t_navmesh_radar_generate_binary,
            *self._buffer_arguments(encode_navmesh_radar_request(request)),
            callback,
        ))

    def navmesh_radar_status(self, request: dict) -> dict:
        """Reports the radar sub-map path and whether the main map already references it."""
        return json.loads(self._invoke(
            self._library.h5t_navmesh_radar_status_json,
            *self._buffer_arguments(self._json_bytes(request)),
        ))

    def write_unreal_map(self, request: dict, output_path: str) -> dict:
        """Writes typed Unreal placements to a VMAP. Returns {"value": {...} | None, "diagnostics": [...]}."""
        return json.loads(self._invoke(
            self._library.h5t_vmap_write_unreal_json,
            *self._buffer_arguments(self._json_bytes(request)),
            *self._buffer_arguments(output_path.encode("utf-8")),
        ))

    def unreal_info(self, content_dir: str) -> dict:
        """Project stats: {contentDir, game, totalFiles, uassets, umaps, externalActorFiles, sampleFiles}."""
        return json.loads(self._invoke(
            self._library.h5t_unreal_info, *self._buffer_arguments(self._json_bytes({"contentDir": content_dir})),
        ))

    def unreal_list(self, content_dir: str, substring: str = "") -> list:
        """Every mounted file path containing ``substring`` (case-insensitive), sorted."""
        return json.loads(self._invoke(
            self._library.h5t_unreal_list,
            *self._buffer_arguments(self._json_bytes({"contentDir": content_dir, "substring": substring})),
        ))

    def unreal_dump(self, content_dir: str, object_path: str):
        """Raw JSON of every export in the package — can be large."""
        return json.loads(self._invoke(
            self._library.h5t_unreal_dump,
            *self._buffer_arguments(self._json_bytes({"contentDir": content_dir, "objectPath": object_path})),
        ))

    def unreal_iter_refs(self, content_dir: str, object_path: str) -> list:
        """Every object reference in a package, flat and deduplicated."""
        return json.loads(self._invoke(
            self._library.h5t_unreal_iter_refs,
            *self._buffer_arguments(self._json_bytes({"contentDir": content_dir, "objectPath": object_path})),
        ))

    def unreal_dump_scene(self, content_dir: str, map_path: str) -> dict:
        """Normalized actor list for a map: {map, count, actors:[...]}."""
        return json.loads(self._invoke(
            self._library.h5t_unreal_dump_scene,
            *self._buffer_arguments(self._json_bytes({"contentDir": content_dir, "mapPath": map_path})),
        ))

    def unreal_dump_blueprint(self, content_dir: str, bp_path: str) -> dict:
        """Normalized Blueprint component tree: {blueprint, count, components:[...]}."""
        return json.loads(self._invoke(
            self._library.h5t_unreal_dump_blueprint,
            *self._buffer_arguments(self._json_bytes({"contentDir": content_dir, "bpPath": bp_path})),
        ))

    def unreal_dump_material(self, content_dir: str, mat_path: str) -> dict:
        """Resolved material params: {material, parent, flags, textures, scalars, vectors, switches}."""
        return json.loads(self._invoke(
            self._library.h5t_unreal_dump_material,
            *self._buffer_arguments(self._json_bytes({"contentDir": content_dir, "matPath": mat_path})),
        ))

    def unreal_export_landscape(self, content_dir: str, map_path: str, out_dir: str, flags: str = "all") -> dict:
        """Exports the map's first landscape actor into ``out_dir``. Raises
        NativeCoreError (message starts with "NO_LANDSCAPE") if the map has no
        landscape actor with components."""
        return json.loads(self._invoke(
            self._library.h5t_unreal_export_landscape,
            *self._buffer_arguments(self._json_bytes({
                "contentDir": content_dir, "mapPath": map_path, "outDir": out_dir, "flags": flags,
            })),
        ))

    def vmap_merge_open(self, ours_path: str, theirs_path: str, base_path: str | None, allow_unrelated: bool) -> dict:
        """Loads and diffs ours/theirs (and an optional base) for a 3-way .vmap
        block merge. Returns {handle, oursBlockCount, theirsBlockCount,
        realignedCount, added, removed, changed, conflicts}."""
        request = {
            "oursPath": ours_path, "theirsPath": theirs_path,
            "basePath": base_path, "allowUnrelated": allow_unrelated,
        }
        return json.loads(self._invoke(
            self._library.h5t_vmap_merge_open, *self._buffer_arguments(self._json_bytes(request)),
        ))

    def vmap_merge_resolve(self, handle: int, block_id: str, side: str) -> int:
        """Records a manual resolution for one conflicting block. Returns 0 on success."""
        block_id_buffer, block_id_length = self._buffer_arguments(block_id.encode("utf-8"))
        side_buffer, side_length = self._buffer_arguments(side.encode("utf-8"))
        return int(self._library.h5t_vmap_merge_resolve(handle, block_id_buffer, block_id_length, side_buffer, side_length))

    def vmap_merge_resolve_all(self, handle: int, side: str) -> None:
        """Picks one side for every remaining conflict."""
        side_buffer, side_length = self._buffer_arguments(side.encode("utf-8"))
        self._library.h5t_vmap_merge_resolve_all(handle, side_buffer, side_length)

    def vmap_merge_write(self, handle: int, out_path: str) -> dict:
        """Applies the merge and writes it to out_path. Returns {orphaned: [...]}.
        Raises NativeCoreError if conflicts remain unresolved."""
        return json.loads(self._invoke(
            self._library.h5t_vmap_merge_write, handle, *self._buffer_arguments(out_path.encode("utf-8")),
        ))

    def vmap_merge_close(self, handle: int) -> None:
        """Releases a merge session's loaded documents."""
        self._library.h5t_vmap_merge_close(handle)

    def source_porter_validate(
        self, request: dict, log: Callable[[str], None], *, cancellation: NativeCancellation | None = None,
    ) -> int:
        """Validates an addon's assets. Streams progress/issue lines through ``log``.
        Returns 0 (no issues), 1 (issues found — not an error), or a negative status."""
        return self._invoke_streaming(self._library.h5t_source_porter_validate, request, log, cancellation)

    def source_porter_force_import(
        self, request: dict, log: Callable[[str], None], *, cancellation: NativeCancellation | None = None,
    ) -> int:
        """Force-imports specific Source 1 asset paths into an addon. Streams progress through ``log``."""
        return self._invoke_streaming(self._library.h5t_source_porter_force_import, request, log, cancellation)

    def source_porter_repair(
        self, request: dict, log: Callable[[str], None], *, cancellation: NativeCancellation | None = None,
    ) -> int:
        """Validates then re-imports an addon's missing assets. Streams progress/issue lines through ``log``."""
        return self._invoke_streaming(self._library.h5t_source_porter_repair, request, log, cancellation)

    def source_porter_port(
        self, request: dict, log: Callable[[str], None], *, cancellation: NativeCancellation | None = None,
    ) -> int:
        """Ports a Source 1 map into a CS2 addon. Streams progress/issue lines through ``log``."""
        return self._invoke_streaming(self._library.h5t_source_porter_port, request, log, cancellation)

    def _invoke_streaming(
        self, function, request: dict, log: Callable[[str], None], cancellation: NativeCancellation | None,
    ) -> int:
        """Calls a SourcePorter-style command: JSON request in, log lines streamed
        synchronously through a native callback, an int status code out."""
        buffer, length = self._buffer_arguments(self._json_bytes(request))

        def on_log(line: ctypes.c_void_p, line_length: int) -> None:
            # A Python exception must never unwind back through the native call
            # frame that invoked this callback — swallow and drop the line.
            try:
                log(ctypes.string_at(line, line_length).decode("utf-8", errors="replace"))
            except Exception:
                pass

        callback = _LOG_CALLBACK_TYPE(on_log)
        return int(function(buffer, length, callback, 0 if cancellation is None else cancellation.handle))

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
            "h5t_compiled_model_read_json",
            "h5t_compiled_model_material_groups_json",
            "h5t_compiled_material_read_json",
            "h5t_compiled_texture_read_json",
            "h5t_compiled_resource_read_json",
            "h5t_vmap_read_json",
            "h5t_vmap_read_asset_references_json",
            "h5t_vmap_read_scene_json",
            "h5t_vmap_read_scene_binary",
            "h5t_vmap_rewrite_references_json",
            "h5t_vmap_rewrite_references_binary",
            "h5t_navmesh_radar_generate_json",
            "h5t_navmesh_radar_status_json",
            "h5t_vsnap_read_json",
            "h5t_vsnap_read_binary",
            "h5t_vsnap_serialize_json",
            "h5t_vsnap_serialize_binary",
            "h5t_vsnap_generate_json",
            "h5t_vsnap_generate_binary",
            "h5t_vsnap_light_json",
            "h5t_vsnap_lightning_json",
            "h5t_unreal_info",
            "h5t_unreal_list",
            "h5t_unreal_dump",
            "h5t_unreal_iter_refs",
            "h5t_unreal_dump_scene",
            "h5t_unreal_dump_blueprint",
            "h5t_unreal_dump_material",
            "h5t_unreal_export_landscape",
        ):
            function = getattr(self._library, name)
            function.argtypes = [pointer, length, output, output_length]
            function.restype = ctypes.c_int

        self._library.h5t_navmesh_radar_generate_binary.argtypes = [
            pointer, length, _LOG_CALLBACK_TYPE, output, output_length,
        ]
        self._library.h5t_navmesh_radar_generate_binary.restype = ctypes.c_int

        self._library.h5t_vsnap_attributes_json.argtypes = [output, output_length]
        self._library.h5t_vsnap_attributes_json.restype = ctypes.c_int

        self._library.h5t_vmap_write_unreal_json.argtypes = [pointer, length, pointer, length, output, output_length]
        self._library.h5t_vmap_write_unreal_json.restype = ctypes.c_int

        self._library.h5t_vpk_open.argtypes = []
        self._library.h5t_vpk_open.restype = ctypes.c_longlong
        self._library.h5t_vpk_close.argtypes = [ctypes.c_longlong]
        self._library.h5t_vpk_close.restype = None
        self._library.h5t_vpk_exists.argtypes = [ctypes.c_longlong, pointer, length]
        self._library.h5t_vpk_exists.restype = ctypes.c_int
        self._library.h5t_vpk_package_count.argtypes = [ctypes.c_longlong]
        self._library.h5t_vpk_package_count.restype = ctypes.c_int
        for name in ("h5t_vpk_mount", "h5t_vpk_add_loose_root", "h5t_vpk_read_bytes", "h5t_vpk_entries_json"):
            function = getattr(self._library, name)
            function.argtypes = [ctypes.c_longlong, pointer, length, output, output_length]
            function.restype = ctypes.c_int

        for name in (
            "h5t_source_porter_validate",
            "h5t_source_porter_force_import",
            "h5t_source_porter_repair",
            "h5t_source_porter_port",
        ):
            function = getattr(self._library, name)
            function.argtypes = [pointer, length, _LOG_CALLBACK_TYPE, ctypes.c_longlong]
            function.restype = ctypes.c_int

        self._library.h5t_vmap_merge_open.argtypes = [pointer, length, output, output_length]
        self._library.h5t_vmap_merge_open.restype = ctypes.c_int
        self._library.h5t_vmap_merge_resolve.argtypes = [ctypes.c_longlong, pointer, length, pointer, length]
        self._library.h5t_vmap_merge_resolve.restype = ctypes.c_int
        self._library.h5t_vmap_merge_resolve_all.argtypes = [ctypes.c_longlong, pointer, length]
        self._library.h5t_vmap_merge_resolve_all.restype = None
        self._library.h5t_vmap_merge_write.argtypes = [ctypes.c_longlong, pointer, length, output, output_length]
        self._library.h5t_vmap_merge_write.restype = ctypes.c_int
        self._library.h5t_vmap_merge_close.argtypes = [ctypes.c_longlong]
        self._library.h5t_vmap_merge_close.restype = None

    def _invoke(self, function, *arguments) -> str:
        status, payload = self._invoke_raw(function, *arguments)
        if status != 0:
            self._raise_native_error(status, payload)
        return payload.decode("utf-8") if payload else ""

    def _invoke_binary(self, function, *arguments) -> bytes:
        status, payload = self._invoke_raw(function, *arguments)
        if status == 0:
            return payload
        try:
            message = decode_error(payload)
        except NativeBinaryError:
            self._raise_native_error(status, payload)
        raise NativeCoreError(message or f"Native Core call failed with status {status}")

    def _invoke_raw(self, function, *arguments) -> tuple[int, bytes]:
        """Calls a buffer-returning native function without decoding or raising."""
        output = ctypes.c_void_p()
        output_length = ctypes.c_int()
        status = function(
            *arguments,
            ctypes.byref(output),
            ctypes.byref(output_length),
        )
        try:
            payload = ctypes.string_at(output.value, output_length.value) if output.value else b""
        finally:
            if output.value:
                self._library.h5t_core_release(output)
        return status, payload

    @staticmethod
    def _raise_native_error(status: int, payload: bytes) -> None:
        text = payload.decode("utf-8", errors="replace")
        try:
            message = json.loads(text).get("error", text)
        except json.JSONDecodeError:
            message = text
        raise NativeCoreError(message or f"Native Core call failed with status {status}")

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
        ]
        for candidate in candidates:
            if candidate and candidate.is_file():
                return candidate.resolve()

        dev_candidates = [
            paths.install_root / "Hammer5ToolsCore" / "Hammer5Tools.Core" / "bin" / "Release" / "win-x64" / "native" / cls.LIBRARY_NAME,
            paths.install_root / "Hammer5ToolsCore" / "Hammer5Tools.Core" / "publish" / cls.LIBRARY_NAME,
        ]
        existing_dev = [candidate.resolve() for candidate in dev_candidates if candidate.is_file()]
        if existing_dev:
            return max(existing_dev, key=lambda p: p.stat().st_mtime)
        return None
