from hammer5tools_core.dotnet import setup_keyvalues2
from hammer5tools_gui.forms.unreal_porter.vmap_writer import write_vmap


def _actor(name, component_type, *, mesh=None, blueprint=None, material=None):
    return {
        "actor": name,
        "componentType": component_type,
        "mesh": mesh,
        "blueprint": blueprint,
        "material": material,
        "location": {"x": 300.0, "y": 400.0, "z": 50.0},
        "rotation": {"pitch": 20.0, "yaw": 60.0, "roll": 30.0},
        "scale": {"x": 2.0, "y": 3.0, "z": 4.0},
    }


def _load_children(path):
    datamodel, _, deferred_mode = setup_keyvalues2()
    document = datamodel.Load(str(path), deferred_mode.Automatic)
    return list(document.Root["world"]["children"])


def test_writer_structurally_preserves_props_and_smartprops(tmp_path):
    output = tmp_path / "scene.vmap"
    result = write_vmap(
        [
            _actor("Chair", "StaticMeshComponent", mesh="/Game/Meshes/SM_Chair.SM_Chair"),
            _actor("Door", "BlueprintActor", blueprint="/Game/BP/BP_Door.BP_Door"),
            _actor("Unsupported", "InstancedStaticMeshComponent", mesh="/Game/Meshes/SM_Box.SM_Box"),
        ],
        str(output),
        model_resolver=lambda _: "models/meshes/chair.vmdl",
    )

    assert result.placed == 1
    assert result.placed_smartprops == 1
    assert result.skipped == 1
    assert result.skipped_types == {"InstancedStaticMeshComponent": 1}
    assert result.models == {"models/meshes/chair.vmdl"}

    children = _load_children(output)
    prop = next(node for node in children if node.ClassName == "CMapEntity")
    origin = prop["origin"]
    angles = prop["angles"]
    scales = prop["scales"]
    assert (origin.X, origin.Y, origin.Z) == (300.0, -400.0, 50.0)
    assert (angles.Pitch, angles.Yaw, angles.Roll) == (-20.0, -60.0, 30.0)
    assert (scales.X, scales.Y, scales.Z) == (2.0, 3.0, 4.0)
    assert prop["entity_properties"]["classname"] == "prop_static"
    assert prop["entity_properties"]["model"] == "models/meshes/chair.vmdl"

    smartprop = next(node for node in children if node.ClassName == "CMapSmartProp")
    assert smartprop["smartPropFilename"] == "smartprops//game/bp/bp_door.bp_door.vsmart"


def test_writer_emits_native_decal_mesh_and_binary_encoding(tmp_path):
    output = tmp_path / "decal.vmap"
    result = write_vmap(
        [_actor("Poster", "DecalComponent", material="/Game/M/MI_Poster.MI_Poster")],
        str(output),
        import_decals=True,
    )

    assert result.placed_decals == 1
    assert result.decal_materials == {"/Game/M/MI_Poster.MI_Poster"}
    assert output.read_bytes().startswith(b"<!-- dmx encoding binary 9")

    overlay = next(node for node in _load_children(output) if node.ClassName == "CMapStaticOverlay")
    mesh = overlay["meshData"]
    assert mesh.ClassName == "CDmePolygonMesh"
    assert list(mesh["materials"]) == ["materials/m/poster.vmat"]
    assert mesh["subdivisionData"].ClassName == "CDmePolygonMeshSubdivisionData"
