"""Cutout-alpha handling: extract_alpha's shape-vs-blend discrimination and the
alpha-test block write_vmat emits from it.

The de_firewatch UE5 port had 313 materials and not one F_ALPHA_TEST, so every
bush, grass card and length of netting rendered as an opaque quad. The failure
mode in the other direction is worse: alpha-testing off a *blend* mask (UE packs
both kinds into the same channel) punches holes in solid geometry, so the
rejection cases below matter as much as the acceptance ones.
"""
import os
import sys
import tempfile
import unittest
from PIL import Image

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.forms.unreal_converter.texture_utils import extract_alpha
from src.forms.unreal_converter.vmat_writer import write_vmat


def _rgba(size, alpha_pixels):
    img = Image.new("RGBA", size, (128, 128, 128, 255))
    img.putalpha(Image.frombytes("L", size, bytes(alpha_pixels)))
    return img


class TestExtractAlpha(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, alpha_pixels, size=(8, 8)):
        p = os.path.join(self.tmp.name, name)
        _rgba(size, alpha_pixels).save(p)
        return p

    def test_accepts_cutout_mask(self):
        """Bimodal alpha - a leaf card - is a shape and gets extracted."""
        px = [0] * 32 + [255] * 32
        src = self._write("leaf.tga", px)
        out = os.path.join(self.tmp.name, "leaf_trans.tga")
        self.assertEqual(extract_alpha(src, out), out)
        self.assertEqual(sorted(set(Image.open(out).getdata())), [0, 255])

    def test_rejects_blend_mask(self):
        """A gradient is a layer-blend mask, not a shape - alpha-test would
        shred the geometry it is applied to."""
        src = self._write("seats.tga", list(range(64)) and [100 + (i % 60) for i in range(64)])
        self.assertIsNone(extract_alpha(src, os.path.join(self.tmp.name, "x.tga")))

    def test_rejects_constant_alpha(self):
        src = self._write("opaque.tga", [255] * 64)
        self.assertIsNone(extract_alpha(src, os.path.join(self.tmp.name, "x.tga")))

    def test_rejects_nothing_cut_out(self):
        """Bimodal but only one stray transparent pixel - not worth a mask."""
        px = [0] + [255] * 63
        src = self._write("solid.tga", px)
        self.assertIsNone(extract_alpha(src, os.path.join(self.tmp.name, "x.tga")))

    def test_rejects_non_rgba(self):
        p = os.path.join(self.tmp.name, "rgb.tga")
        Image.new("RGB", (8, 8), (1, 2, 3)).save(p)
        self.assertIsNone(extract_alpha(p, os.path.join(self.tmp.name, "x.tga")))


class TestAlphaTestVmat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_vmat(self, **kw):
        p = os.path.join(self.tmp.name, "m.vmat")
        slots = {"color": "materials/f/leaf_color.tga", "normal": "materials/f/leaf_normal.tga"}
        slots.update(kw.pop("slots", {}))
        write_vmat(p, slots, **kw)
        with open(p, encoding="utf-8") as f:
            return f.read()

    def test_emits_alpha_test_block(self):
        c = self._write_vmat(slots={"trans": "materials/f/leaf_trans.tga"},
                             alpha_test_ref=0.33, render_backfaces=True)
        self.assertIn("F_ALPHA_TEST 1", c)
        self.assertIn("F_RENDER_BACKFACES 1", c)
        self.assertIn('TextureTranslucency1 "materials/f/leaf_trans.tga"', c)
        self.assertIn('g_flAlphaTestReference "0.330"', c)
        self.assertIn('g_flAntiAliasedEdgeStrength "1.000"', c)
        # flag goes above the shader params, scalar below them - Hammer's layout
        self.assertLess(c.index("F_ALPHA_TEST"), c.index("g_vColorTint"))
        self.assertGreater(c.index("g_flAlphaTestReference"), c.index("TextureTintMask1"))

    def test_no_block_without_ref(self):
        c = self._write_vmat(slots={"trans": "materials/f/leaf_trans.tga"})
        self.assertNotIn("F_ALPHA_TEST", c)
        self.assertNotIn("TextureTranslucency1", c)

    def test_no_block_without_mask(self):
        """A cutoff with no mask to test against would be a broken material."""
        c = self._write_vmat(alpha_test_ref=0.5)
        self.assertNotIn("F_ALPHA_TEST", c)
        self.assertNotIn("g_flAlphaTestReference", c)

    def test_backfaces_alone(self):
        c = self._write_vmat(render_backfaces=True)
        self.assertIn("F_RENDER_BACKFACES 1", c)
        self.assertNotIn("F_ALPHA_TEST", c)

    def test_plain_material_unchanged(self):
        c = self._write_vmat()
        self.assertIn('shader "csgo_environment.vfx"', c)
        for absent in ("F_ALPHA_TEST", "F_RENDER_BACKFACES", "TextureTranslucency1"):
            self.assertNotIn(absent, c)


if __name__ == "__main__":
    unittest.main()
