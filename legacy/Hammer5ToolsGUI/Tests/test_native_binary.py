"""Regression coverage for the compact NativeAOT binary ABI payloads."""

import struct

from core import native_binary


def test_snapshot_document_round_trips_as_binary_payload():
    source = {
        "streams": [
            {"name": "position", "type": "position_3d", "values": [[1, 2, 3], [4, 5, 6]]},
            {"name": "radius", "type": "generic_float", "values": [2, 3]},
        ],
    }

    result = native_binary.decode_snapshot_document(
        native_binary.encode_snapshot_document(source)
    )

    assert result == {
        "count": 2,
        "streams": [
            {"name": "position", "type": "position_3d", "values": [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]},
            {"name": "radius", "type": "generic_float", "values": [2.0, 3.0]},
        ],
    }


def test_scene_decoder_keeps_large_float_buffers_as_views():
    writer = native_binary._Writer()
    writer.string("maps/example.vmap")
    writer.int32(1)
    writer.string("brush")
    writer.float_array([1, 2, 3])
    writer.float_array([0, 0, 1])
    writer.float_array([0, 1])
    writer.uint32_array([0, 1, 2])
    writer.int32(1)
    writer.int32(0)
    writer.int32(3)
    writer.string("materials/example.vmat")
    writer.int32(0)
    writer.int32(0)
    writer.int32(0)

    scene = native_binary.decode_vmap_scene(
        writer.finish(native_binary.NativeBinaryMessage.VMAP_SCENE_RESULT)
    )

    assert isinstance(scene["meshes"][0]["positionsBytes"], memoryview)
    assert struct.unpack("<3f", scene["meshes"][0]["positionsBytes"]) == (1.0, 2.0, 3.0)
    assert struct.unpack("<3I", scene["meshes"][0]["indicesBytes"]) == (0, 1, 2)


def test_navmesh_result_retains_existing_python_contract():
    writer = native_binary._Writer()
    writer.boolean(True)
    writer.string("maps/example_generated_radar.vmap")
    writer.byte(1)
    writer.int32(12)
    writer.int32(24)
    writer.int32(1)
    writer.single(16.0)
    writer.boolean(True)
    writer.nullable_string("maps/example.vmap.backup")
    writer.int32(1)
    writer.string("Warning")
    writer.string("example")
    writer.string("Example diagnostic")

    result = native_binary.decode_navmesh_radar(
        writer.finish(native_binary.NativeBinaryMessage.NAVMESH_RADAR_RESULT)
    )

    assert result["value"]["generatedVmapPath"] == "maps/example_generated_radar.vmap"
    assert result["value"]["mode"] == "navmesh_offset"
    assert result["diagnostics"] == [{
        "severity": "Warning", "code": "example", "message": "Example diagnostic",
    }]
