import os
import sys
import tempfile
import unittest
from PIL import Image

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.forms.unreal_converter.converter import scan_and_group
from src.forms.unreal_converter.texture_utils import unpack_rma
from src.forms.unreal_converter.vmat_writer import write_vmat
from src.forms.unreal_converter.material_converter import _classify_textures


class TestMaterialConverter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_and_group(self):
        # Create dummy texture files
        filenames = [
            "T_Wall01_BC.png",
            "T_Wall01_N.png",
            "T_Wall01_ORM.png",
            "T_Floor01_ALB.tga",
            "T_Floor01_NRM.tga",
            "T_Floor01_RMAH.png",
        ]
        for name in filenames:
            path = os.path.join(self.temp_dir.name, name)
            img = Image.new("RGBA", (8, 8), (255, 255, 255, 255))
            img.save(path)

        groups = scan_and_group(self.temp_dir.name)
        self.assertIn("T_Wall01", groups)
        self.assertIn("T_Floor01", groups)

        wall_group = groups["T_Wall01"]
        self.assertIn("ALB", wall_group)
        self.assertIn("NRM", wall_group)
        self.assertIn("ORM", wall_group)

    def test_unpack_orm(self):
        orm_path = os.path.join(self.temp_dir.name, "test_ORM.png")
        # Create ORM map: R=AO (128), G=Roughness (200), B=Metalness (50)
        img = Image.new("RGBA", (16, 16), (128, 200, 50, 255))
        img.save(orm_path)

        res = unpack_rma(orm_path, self.temp_dir.name, "test", is_orm=True)
        self.assertIsNotNone(res)
        self.assertTrue(os.path.exists(res["rough"]))
        self.assertTrue(os.path.exists(res["metal"]))
        self.assertTrue(os.path.exists(res["ao"]))

        rough_img = Image.open(res["rough"])
        self.assertEqual(rough_img.getpixel((0, 0)), 200)

    def test_write_vmat(self):
        vmat_path = os.path.join(self.temp_dir.name, "test_material.vmat")
        slots = {
            "color": "materials/test_color.tga",
            "normal": "materials/test_normal.tga",
            "rough": "materials/test_rough.tga",
            "metal": "materials/test_metal.tga",
            "ao": "materials/test_ao.tga",
        }
        write_vmat(vmat_path, slots, color_tint=(0.8, 0.8, 0.8))

        self.assertTrue(os.path.exists(vmat_path))
        with open(vmat_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('shader "csgo_environment.vfx"', content)
        self.assertIn('TextureColor1 "materials/test_color.tga"', content)
        self.assertIn('TextureNormal1 "materials/test_normal.tga"', content)
        self.assertIn('g_vColorTint "[0.800000 0.800000 0.800000 0.000000]"', content)

    def test_classify_textures_heuristic(self):
        textures = {"BaseColor2": "/Game/T_Wall_BC", "Roughness": "/Game/T_Wall_R"}
        picks = _classify_textures(textures)
        # "BaseColor2" tokenizes to {"base","color","2"} -> matches "color" slot,
        # numeric-suffix penalty just lowers its score vs. an un-numbered rival.
        self.assertEqual(picks["color"], ("BaseColor2", "/Game/T_Wall_BC"))
        self.assertEqual(picks["rough"], ("Roughness", "/Game/T_Wall_R"))

    def test_classify_textures_override_wins(self):
        # "BaseColor2" would heuristically classify as "color"; force it to
        # "emissive" instead and confirm the override wins and excludes it
        # from the slot the heuristic would have picked.
        textures = {"BaseColor2": "/Game/T_Wall_BC"}
        picks = _classify_textures(textures, slot_overrides={"basecolor2": "emissive"})
        self.assertEqual(picks["emissive"], ("BaseColor2", "/Game/T_Wall_BC"))
        self.assertNotIn("color", picks)

    def test_classify_textures_override_skip(self):
        # Mapping a param to None excludes it entirely instead of forcing a slot.
        textures = {"BaseColor2": "/Game/T_Wall_BC"}
        picks = _classify_textures(textures, slot_overrides={"basecolor2": None})
        self.assertEqual(picks, {})


if __name__ == "__main__":
    unittest.main()
