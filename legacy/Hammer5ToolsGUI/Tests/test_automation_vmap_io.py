"""Tests for the shaped VMAP reader.

Core already projects a map completely; these cover the shaping, because a
production map's node tree serializes to roughly six million tokens and no
response may carry it.
"""

from __future__ import annotations

import pytest

from automation.formats.vmap_io import read_vmap, read_vmap_scene


class _Node:
    def __init__(self, class_name, children=()):
        self.name = class_name
        self.class_name = class_name
        self.properties = {"noise": "x" * 200}
        self.children = tuple(children)


class _Entity:
    def __init__(self, class_name, origin="0 0 0", **properties):
        self.class_name = class_name
        self.origin = origin
        self.angles = "0 0 0"
        self.properties = {"classname": class_name, **properties}


class _Placement:
    def __init__(self, resource, position=(0.0, 0.0, 0.0), variables=None):
        self.name = ""
        self.class_name = "CMapSmartProp"
        self.resource = resource
        self.transform = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, *position, 1)
        self.variables = variables or {}


class _SubMesh:
    def __init__(self, material):
        self.material = material
        self.index_offset = 0
        self.index_count = 3


class _Mesh:
    def __init__(self, name, materials):
        self.name = name
        self.submeshes = tuple(_SubMesh(material) for material in materials)
        self.vertices = [0.0] * 30000
        self.indices = [0] * 30000
        self.normals = []
        self.uvs = []


class _Document:
    def __init__(self):
        self.path = "map.vmap"
        self.world = _Node("CMapWorld")
        self.nodes = (_Node("CMapGroup", [_Node("CMapMesh"), _Node("CMapMesh")]),)
        self.entities = (
            _Entity("prop_static", model="models/a.vmdl", targetname="crate"),
            _Entity("prop_static", model="models/b.vmdl"),
            _Entity("light_omni2", origin="10 20 30"),
        )
        self.asset_references = ("models/a.vmdl", "models/b.vmdl")
        self.thumbnail = b"jpeg"
        self.thumbnail_format = "jpg"


class _Scene:
    def __init__(self):
        self.path = "map.vmap"
        self.meshes = (_Mesh("brush0", ["materials/wall.vmat"]),)
        self.props = (_Placement("models/a.vmdl", (100.0, 0.0, 0.0)),)
        self.smart_props = (
            _Placement("smartprops/fence.vsmart", (-50.0, 10.0, 5.0), {"Length": 128.0}),
            _Placement("smartprops/fence.vsmart", (0.0, 0.0, 90.0), {"Length": 64.0}),
        )
        self.diagnostics = ()


class _Bridge:
    def read_valve_map(self, _path):
        return _Document()

    def read_valve_map_scene(self, _path):
        return _Scene()


@pytest.fixture
def map_file(tmp_path):
    path = tmp_path / "map.vmap"
    path.write_bytes(b"binary")
    return str(path)


def test_summary_counts_without_returning_the_node_tree(map_file):
    result = read_vmap(map_file, bridge=_Bridge())

    assert result["entity_count"] == 3
    assert result["entity_classes"] == {"prop_static": 2, "light_omni2": 1}
    assert result["node_count"] == 3, "children must be counted, not just roots"
    assert result["node_classes"]["CMapMesh"] == 2
    assert "nodes" not in result and "entities" not in result


def test_full_detail_still_withholds_the_node_tree(map_file):
    result = read_vmap(map_file, detail="full", bridge=_Bridge())

    assert result["total"] == 3
    assert result["entities"][0]["properties"]["model"] == "models/a.vmdl"
    assert "nodes" not in result


def test_classname_narrows_to_one_class(map_file):
    result = read_vmap(map_file, classname="PROP_STATIC", bridge=_Bridge())

    assert result["matched"] == 2
    assert {entity["class"] for entity in result["entities"]} == {"prop_static"}
    assert result["entities"][0]["targetname"] == "crate"


def test_entities_are_paged(map_file):
    result = read_vmap(map_file, detail="full", limit=1, offset=1, bridge=_Bridge())

    assert result["returned"] == 1
    assert result["truncated"] is True
    assert result["total"] == 3


def test_select_addresses_one_entity(map_file):
    result = read_vmap(map_file, select="entities[class=light_omni2].origin", bridge=_Bridge())

    assert result["value"] == "10 20 30"


def test_scene_summary_reports_bounds_and_distinct_resources(map_file):
    result = read_vmap_scene(map_file, bridge=_Bridge())

    assert result["smartprop_count"] == 2
    assert result["distinct_smartprops"] == {"smartprops/fence.vsmart": 2}
    assert result["bounds"]["minimum"] == [-50.0, 0.0, 0.0]
    assert result["bounds"]["maximum"] == [100.0, 10.0, 90.0]
    assert "smartprops" not in result


def test_smartprop_placements_carry_their_variable_overrides(map_file):
    result = read_vmap_scene(map_file, include="smartprops", bridge=_Bridge())

    assert [item["variables"]["Length"] for item in result["smartprops"]] == [128.0, 64.0]
    assert result["smartprops"][0]["position"] == [-50.0, 10.0, 5.0]


def test_meshes_report_materials_not_vertex_arrays(map_file):
    result = read_vmap_scene(map_file, include="meshes", bridge=_Bridge())

    assert result["meshes"][0]["materials"] == ["materials/wall.vmat"]
    assert "vertices" not in result["meshes"][0]
    assert "indices" not in result["meshes"][0]


def test_resource_filter_selects_one_asset(map_file):
    result = read_vmap_scene(map_file, resource="SmartProps/Fence.vsmart", bridge=_Bridge())

    assert result["smartprop_count"] == 2
    assert result["prop_count"] == 0


def test_unknown_include_is_rejected(map_file):
    with pytest.raises(ValueError, match="include"):
        read_vmap_scene(map_file, include="everything", bridge=_Bridge())


def test_missing_map_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError, match="Valve map"):
        read_vmap(str(tmp_path / "nope.vmap"), bridge=_Bridge())


class _StructureNode:
    def __init__(self, class_name, properties, children=()):
        self.name = ""
        self.class_name = class_name
        self.properties = properties
        self.children = tuple(children)


class _StructureBridge:
    """A projection that reaches the same nodes twice, as the real one does."""

    def read_valve_map(self, _path):
        connection = _StructureNode("DmeConnectionData", {
            "outputName": "OnMapSpawn", "targetName": "relay", "inputName": "Trigger",
            "overrideParam": "", "delay": "0", "timesToFire": "1",
        })
        overlay = _StructureNode("CMapStaticOverlay", {"nodeID": 7, "origin": "1 2 3"})
        entity = _StructureNode("CMapEntity", {"nodeID": 5}, [connection])
        world = _StructureNode("CMapWorld", {"nodeID": 1}, [entity, overlay])

        document = _Document()
        # The same connection and overlay are reachable from the world and from
        # the root, which is what makes naive counting double everything.
        document.nodes = (world, entity, overlay, connection)
        return document


def test_structures_are_deduplicated_across_projection_paths(map_file):
    result = read_vmap(map_file, structures="connections", bridge=_StructureBridge())

    assert result["total"] == 1, "the same connection was counted once per path"
    assert result["items"][0]["outputName"] == "OnMapSpawn"
    assert result["items"][0]["parent"] == "CMapEntity", "the informative parent was kept"


def test_overlays_are_deduplicated_by_node_id(map_file):
    result = read_vmap(map_file, structures="overlays", bridge=_StructureBridge())

    assert result["total"] == 1
    assert result["items"][0]["origin"] == "1 2 3"


def test_unknown_structure_kind_lists_the_real_ones(map_file):
    with pytest.raises(ValueError, match="connections"):
        read_vmap(map_file, structures="doodads", bridge=_StructureBridge())
