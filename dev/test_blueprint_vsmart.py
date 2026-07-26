import os
import sys
import tempfile
import unittest

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.common import Kv3ToJson
from src.forms.unreal_converter.bridge_client import UnrealBridge
from src.forms.unreal_converter.vsmart_writer import write_vsmart
from src.forms.unreal_converter.transform import UnitScale


def comp(name, mesh=None, parent=None, loc=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    return {
        "name": name,
        "componentType": "StaticMeshComponent" if mesh else "SceneComponent",
        "mesh": mesh,
        "parent": parent,
        "location": {"x": loc[0], "y": loc[1], "z": loc[2]},
        "rotation": {"pitch": rot[0], "yaw": rot[1], "roll": rot[2]},
        "scale": {"x": scale[0], "y": scale[1], "z": scale[2]},
    }


def walk(elem):
    """Yield every element in a vsmart tree, depth first."""
    yield elem
    for child in elem.get("m_Children", []) or []:
        yield from walk(child)


class TestBlueprintVsmartWriter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_vsmart = os.path.join(self.temp_dir.name, "smartprops", "BP_TestFence.vsmart")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_vsmart_hierarchy(self):
        bp_name = "BP_TestFence"
        components = [
            {
                "name": "DefaultSceneRoot",
                "componentType": "SceneComponent",
                "mesh": None,
                "parent": None,
                "location": {"x": 0.0, "y": 0.0, "z": 0.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
            {
                "name": "Post_Left",
                "componentType": "StaticMeshComponent",
                "mesh": "/Game/Props/Meshes/SM_Post.SM_Post",
                "parent": "DefaultSceneRoot",
                "location": {"x": -100.0, "y": 50.0, "z": 0.0},
                "rotation": {"pitch": 0.0, "yaw": 90.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
            {
                "name": "Post_Right",
                "componentType": "StaticMeshComponent",
                "mesh": "/Game/Props/Meshes/SM_Post.SM_Post",
                "parent": "DefaultSceneRoot",
                "location": {"x": 100.0, "y": 50.0, "z": 0.0},
                "rotation": {"pitch": 0.0, "yaw": 90.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
            {
                "name": "Rail_Top",
                "componentType": "StaticMeshComponent",
                "mesh": "/Game/Props/Meshes/SM_Rail.SM_Rail",
                "parent": "Post_Left",
                "location": {"x": 0.0, "y": 0.0, "z": 120.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            },
        ]

        res = write_vsmart(
            bp_name=bp_name,
            components=components,
            output_path=self.output_vsmart,
            unit_scale=UnitScale.ONE_TO_ONE,
        )

        self.assertEqual(res.placed, 3)
        self.assertTrue(os.path.exists(self.output_vsmart))

        with open(self.output_vsmart, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('generic_data_type = "CSmartPropRoot"', content)
        self.assertIn("CSmartPropElement_Group", content)
        self.assertIn("CSmartPropElement_Model", content)
        self.assertIn("CSmartPropOperation_Translate", content)
        self.assertIn("CSmartPropOperation_Rotate", content)
        self.assertIn("models/props/meshes/sm_post.vmdl", content)
        self.assertIn("models/props/meshes/sm_rail.vmdl", content)

    def _write(self, components, bp_name="BP_Test"):
        res = write_vsmart(bp_name, components, self.output_vsmart, unit_scale=UnitScale.ONE_TO_ONE)
        with open(self.output_vsmart, "r", encoding="utf-8") as f:
            return res, Kv3ToJson(f.read())

    def test_model_is_a_leaf_children_survive_under_a_group(self):
        """A mesh component with children must not lose them: CSmartPropElement_Model
        ignores m_Children, so the transform has to hoist onto a Group."""
        res, doc = self._write([
            comp("Base", mesh="/Game/M/SM_Base.SM_Base", loc=(0.0, 0.0, 0.0)),
            comp("Top", mesh="/Game/M/SM_Top.SM_Top", parent="Base", loc=(0.0, 0.0, 120.0)),
        ])

        elements = list(walk(doc["m_Children"][0]))
        models = [e for e in elements if e["_class"] == "CSmartPropElement_Model"]
        self.assertEqual(res.placed, 2)
        self.assertEqual(len(models), 2, "the child mesh was dropped")
        for m in models:
            self.assertNotIn("m_Children", m, "Model is a leaf in Source 2")

        # The child's 120-unit offset must still be on something.
        translates = [
            m for e in elements for m in e.get("m_Modifiers", [])
            if m["_class"] == "CSmartPropOperation_Translate"
        ]
        self.assertTrue(any(t["m_vPosition"]["m_Components"][2] == 120.0 for t in translates))

    def test_transform_only_parent_offsets_its_children(self):
        """A mesh-less scene component only exists to carry an offset — its
        translate has to reach the meshes parented under it."""
        _, doc = self._write([
            comp("Pivot", parent=None, loc=(0.0, 0.0, 64.0)),
            comp("Panel", mesh="/Game/M/SM_Panel.SM_Panel", parent="Pivot"),
        ])

        groups = [
            e for e in walk(doc["m_Children"][0])
            if e["_class"] == "CSmartPropElement_Group" and e["m_sLabel"] == "Pivot"
        ]
        self.assertEqual(len(groups), 1)
        translate = groups[0]["m_Modifiers"][0]
        self.assertEqual(translate["_class"], "CSmartPropOperation_Translate")
        self.assertEqual(translate["m_vPosition"]["m_Components"][2], 64.0)
        self.assertEqual(
            [c["_class"] for c in groups[0]["m_Children"]],
            ["CSmartPropElement_Model"],
        )

    def test_cyclic_parenting_terminates(self):
        res = write_vsmart("BP_Test", [
            comp("A", mesh="/Game/M/SM_A.SM_A", parent="B"),
            comp("B", mesh="/Game/M/SM_B.SM_B", parent="A"),
        ], self.output_vsmart)
        self.assertEqual(res.placed, 0)  # unreachable from any root, but no hang


class TestBlueprintDumpFallback(unittest.TestCase):
    """The raw-`dump` fallback parser has to recover the same SCS hierarchy the
    C# bridge does: parenting lives in USCS_Node.ChildNodes, and templates are
    exported as '<Var>_GEN_VARIABLE'."""

    def _parse(self, exports):
        bridge = UnrealBridge(content_dir="")
        bridge.dump = lambda _path: exports
        return bridge._parse_dump_as_blueprint("BP_Fence")["components"]

    def test_scs_child_nodes_rebuild_parenting(self):
        def node(name, template, children=(), parent_var=None):
            props = {
                "ComponentTemplate": {"ObjectName": "StaticMeshComponent'" + template + "'"},
                "InternalVariableName": template[:-len("_GEN_VARIABLE")],
                "ChildNodes": [{"ObjectName": "SCS_Node'" + c + "'"} for c in children],
            }
            if parent_var:
                props["ParentComponentOrVariableName"] = parent_var
            return {"Type": "SCS_Node", "Name": name, "Properties": props}

        exports = [
            node("SCS_Node_0", "Pivot_GEN_VARIABLE", children=["SCS_Node_1"], parent_var="DefaultSceneRoot"),
            node("SCS_Node_1", "Panel_GEN_VARIABLE"),
            {
                "Type": "SceneComponent", "Name": "Pivot_GEN_VARIABLE",
                "Properties": {"RelativeLocation": {"X": 0, "Y": 0, "Z": 64}},
            },
            {
                "Type": "StaticMeshComponent", "Name": "Panel_GEN_VARIABLE",
                "Properties": {"StaticMesh": {"ObjectPath": "/Game/M/SM_Panel.SM_Panel"}},
            },
        ]

        by_name = {c["name"]: c for c in self._parse(exports)}
        self.assertEqual(set(by_name), {"Pivot", "Panel"})
        self.assertEqual(by_name["Panel"]["parent"], "Pivot")
        self.assertEqual(by_name["Pivot"]["parent"], "DefaultSceneRoot")
        self.assertEqual(by_name["Pivot"]["location"]["z"], 64.0)

    def test_child_actor_component_mesh_is_resolved(self):
        """"Convert selected actors to Blueprint -> child actors" puts the mesh on
        a template actor, not on the ChildActorComponent. Export indices matter:
        every template holds a component called "StaticMeshComponent0"."""
        exports = [
            {"Type": "BlueprintGeneratedClass", "Name": "BP_Fence_C", "Properties": {}},
            {
                "Type": "SCS_Node", "Name": "SCS_Node_0",
                "Properties": {
                    "ComponentTemplate": {"ObjectName": "ChildActorComponent'Plank_GEN_VARIABLE'",
                                          "ObjectPath": "BP_Fence.2"},
                    "InternalVariableName": "Plank",
                },
            },
            {
                "Type": "ChildActorComponent", "Name": "Plank_GEN_VARIABLE",
                "Properties": {
                    "ChildActorTemplate": {"ObjectName": "StaticMeshActor'Plank_CAT'",
                                           "ObjectPath": "BP_Fence.3"},
                    "RelativeLocation": {"X": 0, "Y": 0, "Z": 200},
                },
            },
            {
                "Type": "StaticMeshActor", "Name": "Plank_CAT",
                "Properties": {
                    "StaticMeshComponent": {"ObjectName": "StaticMeshComponent'StaticMeshComponent0'",
                                            "ObjectPath": "BP_Fence.4"},
                },
            },
            {
                "Type": "StaticMeshComponent", "Name": "StaticMeshComponent0",
                "Outer": {"ObjectName": "StaticMeshActor'Plank_CAT'", "ObjectPath": "BP_Fence.3"},
                "Properties": {"StaticMesh": {"ObjectPath": "/Game/M/SM_Plank"}},
            },
        ]

        components = self._parse(exports)
        self.assertEqual([c["name"] for c in components], ["Plank"],
                         "the template's own component must not be emitted too")
        self.assertEqual(components[0]["mesh"], "/Game/M/SM_Plank")
        self.assertEqual(components[0]["location"]["z"], 200.0)


if __name__ == "__main__":
    unittest.main()
