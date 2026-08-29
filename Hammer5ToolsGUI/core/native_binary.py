"""Compact, versioned binary payloads for the Hammer5Tools NativeAOT ABI."""

from __future__ import annotations

from enum import IntEnum
import struct
from typing import Any, Iterable, Mapping


class NativeBinaryError(ValueError):
    """Raised when a Native Core binary payload is malformed or unsupported."""


class NativeBinaryMessage(IntEnum):
    ERROR = 0
    VMAP_SCENE_REQUEST = 1
    VMAP_SCENE_RESULT = 2
    VMAP_REWRITE_REQUEST = 3
    VMAP_REWRITE_RESULT = 4
    NAVMESH_RADAR_REQUEST = 5
    NAVMESH_RADAR_RESULT = 6
    SNAPSHOT_TEXT_REQUEST = 7
    SNAPSHOT_DOCUMENT = 8
    SNAPSHOT_GENERATE_REQUEST = 9
    TEXT_RESULT = 10


_MAGIC = b"H5TB"
_VERSION = 1
_HEADER = struct.Struct("<4sHHI")
_INT32 = struct.Struct("<i")
_UINT32 = struct.Struct("<I")
_UINT16 = struct.Struct("<H")
_SINGLE = struct.Struct("<f")
_MAX_COLLECTION_COUNT = 1_000_000


class _Writer:
    def __init__(self) -> None:
        self._data = bytearray()

    def byte(self, value: int) -> None:
        self._data.append(value)

    def boolean(self, value: bool) -> None:
        self.byte(1 if value else 0)

    def int32(self, value: int) -> None:
        self._data.extend(_INT32.pack(value))

    def uint32(self, value: int) -> None:
        self._data.extend(_UINT32.pack(value))

    def single(self, value: float) -> None:
        self._data.extend(_SINGLE.pack(value))

    def string(self, value: str) -> None:
        encoded = value.encode("utf-8")
        self.int32(len(encoded))
        self._data.extend(encoded)

    def nullable_string(self, value: str | None) -> None:
        if value is None:
            self.int32(-1)
            return
        self.string(value)

    def align(self, alignment: int = 4) -> None:
        self._data.extend(b"\0" * ((-len(self._data)) & (alignment - 1)))

    def float_array(self, values: Iterable[float]) -> None:
        values = tuple(float(value) for value in values)
        self.int32(len(values))
        self.align()
        self._data.extend(struct.pack(f"<{len(values)}f", *values))

    def uint32_array(self, values: Iterable[int]) -> None:
        values = tuple(int(value) for value in values)
        self.int32(len(values))
        self.align()
        self._data.extend(struct.pack(f"<{len(values)}I", *values))

    def finish(self, message: NativeBinaryMessage) -> bytes:
        return _HEADER.pack(_MAGIC, _VERSION, int(message), len(self._data)) + self._data


class _Reader:
    def __init__(self, payload: bytes, expected: NativeBinaryMessage) -> None:
        if len(payload) < _HEADER.size:
            raise NativeBinaryError("Native Core binary payload is truncated")
        magic, version, message, length = _HEADER.unpack_from(payload)
        if magic != _MAGIC:
            raise NativeBinaryError("Native Core binary payload has an invalid signature")
        if version != _VERSION:
            raise NativeBinaryError(f"Unsupported Native Core binary payload version {version}")
        if message != int(expected):
            raise NativeBinaryError(
                f"Expected Native Core binary message {expected.name}, found {message}"
            )
        if length != len(payload) - _HEADER.size:
            raise NativeBinaryError("Native Core binary payload length is invalid")
        self._data = memoryview(payload)
        self._offset = _HEADER.size

    @property
    def remaining(self) -> int:
        return len(self._data) - self._offset

    def byte(self) -> int:
        return self.raw(1)[0]

    def boolean(self) -> bool:
        value = self.byte()
        if value not in (0, 1):
            raise NativeBinaryError("Native Core binary boolean is invalid")
        return bool(value)

    def int32(self) -> int:
        return _INT32.unpack(self.raw(_INT32.size))[0]

    def uint32(self) -> int:
        return _UINT32.unpack(self.raw(_UINT32.size))[0]

    def single(self) -> float:
        return _SINGLE.unpack(self.raw(_SINGLE.size))[0]

    def string(self) -> str:
        return self.raw(self.length()).tobytes().decode("utf-8")

    def nullable_string(self) -> str | None:
        length = self.int32()
        if length == -1:
            return None
        if length < 0:
            raise NativeBinaryError("Native Core binary string length is invalid")
        return self.raw(length).tobytes().decode("utf-8")

    def float_array(self) -> memoryview:
        count = self.collection_count("float array", maximum=100_000_000)
        self.align()
        return self.raw(count * _SINGLE.size)

    def uint32_array(self) -> memoryview:
        count = self.collection_count("uint32 array", maximum=100_000_000)
        self.align()
        return self.raw(count * _UINT32.size)

    def collection_count(self, name: str, *, maximum: int = _MAX_COLLECTION_COUNT) -> int:
        count = self.int32()
        if count < 0 or count > maximum:
            raise NativeBinaryError(f"Native Core binary {name} count is invalid")
        return count

    def length(self) -> int:
        length = self.int32()
        if length < 0 or length > self.remaining:
            raise NativeBinaryError("Native Core binary payload length is invalid")
        return length

    def raw(self, length: int) -> memoryview:
        if length < 0 or length > self.remaining:
            raise NativeBinaryError("Native Core binary payload is truncated")
        value = self._data[self._offset:self._offset + length]
        self._offset += length
        return value

    def align(self, alignment: int = 4) -> None:
        padding = (-self._offset) & (alignment - 1)
        if self.raw(padding).tobytes().strip(b"\0"):
            raise NativeBinaryError("Native Core binary alignment padding is invalid")

    def finish(self) -> None:
        if self.remaining:
            raise NativeBinaryError("Native Core binary payload has trailing bytes")


def encode_vmap_scene_request(path: str) -> bytes:
    writer = _Writer()
    writer.string(path)
    return writer.finish(NativeBinaryMessage.VMAP_SCENE_REQUEST)


def decode_vmap_scene(payload: bytes) -> dict[str, Any]:
    reader = _Reader(payload, NativeBinaryMessage.VMAP_SCENE_RESULT)
    result: dict[str, Any] = {
        "path": reader.string(),
        "meshes": [],
        "props": [],
        "smartProps": [],
        "diagnostics": [],
    }
    for _ in range(reader.collection_count("VMAP mesh")):
        mesh = {
            "name": reader.string(),
            "positionsBytes": reader.float_array(),
            "normalsBytes": reader.float_array(),
            "uvsBytes": reader.float_array(),
            "indicesBytes": reader.uint32_array(),
            "submeshes": [],
        }
        for _ in range(reader.collection_count("VMAP submesh")):
            mesh["submeshes"].append({
                "indexOffset": reader.int32(),
                "indexCount": reader.int32(),
                "material": reader.string(),
            })
        result["meshes"].append(mesh)

    for _ in range(reader.collection_count("VMAP prop")):
        result["props"].append({
            "name": reader.string(),
            "className": reader.string(),
            "model": reader.string(),
            "transform": _read_transform(reader),
        })

    for _ in range(reader.collection_count("VMAP SmartProp")):
        smart_prop: dict[str, Any] = {
            "name": reader.string(),
            "file": reader.string(),
            "transform": _read_transform(reader),
            "variables": {},
        }
        for _ in range(reader.collection_count("VMAP SmartProp variable")):
            name = reader.string()
            smart_prop["variables"][name] = _read_scalar(reader)
        result["smartProps"].append(smart_prop)

    result["diagnostics"] = [
        reader.string() for _ in range(reader.collection_count("VMAP diagnostic"))
    ]
    reader.finish()
    return result


def encode_vmap_rewrite_request(path: str, renames: Mapping[str, str]) -> bytes:
    writer = _Writer()
    writer.string(path)
    writer.int32(len(renames))
    for source, target in renames.items():
        writer.string(str(source))
        writer.string(str(target))
    return writer.finish(NativeBinaryMessage.VMAP_REWRITE_REQUEST)


def decode_vmap_rewrite(payload: bytes) -> dict[str, Any]:
    reader = _Reader(payload, NativeBinaryMessage.VMAP_REWRITE_RESULT)
    success = reader.boolean()
    result = {
        "value": reader.boolean() if success else None,
        "diagnostics": _read_diagnostics(reader),
    }
    reader.finish()
    return result


def encode_navmesh_radar_request(request: Mapping[str, Any]) -> bytes:
    mode = request["mode"]
    mode_value = {"baked_bomb_damage": 0, "navmesh_offset": 1}.get(mode)
    if mode_value is None:
        raise NativeBinaryError(f"Unknown NavMesh Radar mode '{mode}'")
    writer = _Writer()
    writer.string(str(request["vpkPath"]))
    writer.string(str(request["mainVmapPath"]))
    writer.byte(mode_value)
    writer.single(float(request.get("offset", 16.0)))
    writer.string(str(request.get("materialPath", "materials/radgen/radgen_path.vmat")))
    writer.boolean(bool(request.get("addPrefabReference", request.get("addPrefab", True))))
    writer.boolean(bool(request.get("collapseFaces", True)))
    writer.boolean(bool(request.get("collapseFacesIntoNgons", False)))
    return writer.finish(NativeBinaryMessage.NAVMESH_RADAR_REQUEST)


def decode_navmesh_radar(payload: bytes) -> dict[str, Any]:
    reader = _Reader(payload, NativeBinaryMessage.NAVMESH_RADAR_RESULT)
    success = reader.boolean()
    value = None
    if success:
        generated_vmap_path = reader.string()
        mode = {0: "baked_bomb_damage", 1: "navmesh_offset"}.get(reader.byte())
        if mode is None:
            raise NativeBinaryError("Native Core binary NavMesh Radar mode is invalid")
        value = {
            "generatedVmapPath": generated_vmap_path,
            "mode": mode,
            "sourceCount": reader.int32(),
            "faceCount": reader.int32(),
            "meshCount": reader.int32(),
            "offset": reader.single(),
            "referenceAdded": reader.boolean(),
            "backupPath": reader.nullable_string(),
        }
    result = {"value": value, "diagnostics": _read_diagnostics(reader)}
    reader.finish()
    return result


def encode_snapshot_text_request(text: str) -> bytes:
    writer = _Writer()
    writer.string(text)
    return writer.finish(NativeBinaryMessage.SNAPSHOT_TEXT_REQUEST)


def encode_snapshot_document(document: Mapping[str, Any]) -> bytes:
    writer = _Writer()
    _write_snapshot_document(writer, document)
    return writer.finish(NativeBinaryMessage.SNAPSHOT_DOCUMENT)


def decode_snapshot_document(payload: bytes) -> dict[str, Any]:
    reader = _Reader(payload, NativeBinaryMessage.SNAPSHOT_DOCUMENT)
    document = _read_snapshot_document(reader)
    reader.finish()
    return document


def encode_snapshot_generate_request(request: Mapping[str, Any]) -> bytes:
    writer = _Writer()
    if "positions" in request:
        positions = request["positions"]
        writer.byte(1)
        writer.int32(len(positions))
        writer.align()
        for position in positions:
            if len(position) != 3:
                raise NativeBinaryError("Each snapshot position must contain three components")
            for component in position:
                writer.single(float(component))
    else:
        writer.byte(0)
        writer.string(str(request["primitive"]))
        writer.int32(int(request["count"]))
        writer.single(float(request["size"]))
    return writer.finish(NativeBinaryMessage.SNAPSHOT_GENERATE_REQUEST)


def decode_text_result(payload: bytes) -> str:
    reader = _Reader(payload, NativeBinaryMessage.TEXT_RESULT)
    result = reader.string()
    reader.finish()
    return result


def decode_error(payload: bytes) -> str:
    reader = _Reader(payload, NativeBinaryMessage.ERROR)
    message = reader.string()
    reader.finish()
    return message


def _read_transform(reader: _Reader) -> tuple[float, ...]:
    values = reader.float_array()
    if len(values) != 16 * _SINGLE.size:
        raise NativeBinaryError("Native Core binary transform must contain 16 floats")
    return struct.unpack("<16f", values)


def _read_scalar(reader: _Reader) -> Any:
    scalar_type = reader.byte()
    if scalar_type == 0:
        return None
    if scalar_type == 1:
        return reader.boolean()
    if scalar_type == 2:
        return reader.string()
    if scalar_type == 3:
        return reader.single()
    if scalar_type == 4:
        return reader.int32()
    if scalar_type == 5:
        return (reader.single(), reader.single())
    if scalar_type == 6:
        return (reader.single(), reader.single(), reader.single())
    raise NativeBinaryError(f"Unknown Native Core binary scalar type {scalar_type}")


def _read_diagnostics(reader: _Reader) -> list[dict[str, str]]:
    return [
        {"severity": reader.string(), "code": reader.string(), "message": reader.string()}
        for _ in range(reader.collection_count("diagnostic"))
    ]


def _snapshot_width(stream_type: str) -> int:
    widths = {
        "position_3d": 3,
        "normal_3d": 3,
        "generic_vector_3d": 3,
        "generic_float": 1,
        "bone_index_and_weight": 0,
    }
    try:
        return widths[stream_type]
    except KeyError as error:
        raise NativeBinaryError(f"Unsupported snapshot stream type '{stream_type}'") from error


def _write_snapshot_document(writer: _Writer, document: Mapping[str, Any]) -> None:
    streams = list(document["streams"])
    count = 0 if not streams else len(streams[0]["values"])
    writer.int32(count)
    writer.int32(len(streams))
    for stream in streams:
        name = str(stream["name"])
        stream_type = str(stream["type"])
        values = list(stream["values"])
        width = _snapshot_width(stream_type)
        if width == 0 and not values:
            writer.string(name)
            writer.string(stream_type)
            writer.int32(0)
            continue
        if len(values) != count:
            raise NativeBinaryError(f"Snapshot stream '{name}' has inconsistent values")
        writer.string(name)
        writer.string(stream_type)
        writer.int32(len(values))
        writer.align()
        for value in values:
            components = (value,) if width == 1 and not isinstance(value, (list, tuple)) else value
            if len(components) != width:
                raise NativeBinaryError(f"Snapshot stream '{name}' has an invalid value width")
            for component in components:
                writer.single(float(component))


def _read_snapshot_document(reader: _Reader) -> dict[str, Any]:
    count = reader.collection_count("snapshot value")
    stream_count = reader.collection_count("snapshot stream")
    streams = []
    for _ in range(stream_count):
        name = reader.string()
        stream_type = reader.string()
        width = _snapshot_width(stream_type)
        value_count = reader.collection_count(f"snapshot stream '{name}' value")
        if width == 0 and value_count == 0:
            streams.append({"name": name, "type": stream_type, "values": []})
            continue
        if value_count != count:
            raise NativeBinaryError(
                f"Snapshot stream '{name}' contains {value_count} values; expected {count}"
            )
        reader.align()
        values = []
        for _ in range(value_count):
            components = tuple(reader.single() for _ in range(width))
            values.append(components[0] if width == 1 else components)
        streams.append({"name": name, "type": stream_type, "values": values})
    return {"count": count, "streams": streams}
