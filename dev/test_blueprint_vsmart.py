import os
import sys
import tempfile
import unittest

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.forms.unreal_converter.vsmart_writer import write_vsmart
from src.forms.unreal_converter.transform import UnitScale


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


if __name__ == "__main__":
    unittest.main()
