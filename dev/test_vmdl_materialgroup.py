import os
import sys
import tempfile
import unittest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.forms.unreal_converter.vmdl_writer import write_vmdl, strip_ue_prefix, ue_mesh_to_model_path


class TestVmdlMaterialGroup(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_strip_ue_prefix(self):
        self.assertEqual(strip_ue_prefix("SM_Chair"), "Chair")
        self.assertEqual(strip_ue_prefix("BP_Fence_01"), "Fence_01")
        self.assertEqual(strip_ue_prefix("MI_Wall_Base"), "Wall_Base")
        self.assertEqual(strip_ue_prefix("T_Wood_D"), "Wood_D")
        self.assertEqual(strip_ue_prefix("Chair"), "Chair")

    def test_ue_mesh_to_model_path_prefix(self):
        p1 = ue_mesh_to_model_path("/Game/Props/SM_Barrel.SM_Barrel", strip_prefix=False)
        self.assertEqual(p1, "models/props/sm_barrel.vmdl")

        p2 = ue_mesh_to_model_path("/Game/Props/SM_Barrel.SM_Barrel", strip_prefix=True)
        self.assertEqual(p2, "models/props/barrel.vmdl")

    def test_vmdl_material_remap(self):
        out_vmdl = os.path.join(self.temp_dir.name, "models", "props", "barrel.vmdl")
        mat_path = "materials/props/barrel.vmat"

        write_vmdl(out_vmdl, "models/props/barrel.fbx", material_path=mat_path)

        self.assertTrue(os.path.exists(out_vmdl))
        with open(out_vmdl, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('use_global_default = false', content)
        self.assertIn('from = "*"', content)
        self.assertIn('to = "materials/props/barrel.vmat"', content)


if __name__ == "__main__":
    unittest.main()
