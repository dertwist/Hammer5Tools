"""Regression test for the get_material_references cyclic-vmat recursion fix.

Two .vmat files reference each other (a -> b -> a). Before the visited-set +
memoization fix this recursed forever inside get_material_references and
crashed with a RecursionError.
"""
import os
import tempfile
import unittest
from unittest import mock

import vdf

from gui.forms.cleanup import parse

VMAT_A = '''Layer0
{
\tshader "vr_standard.vfx"
\tTextureColor "materials/tex_a.tga"
\tMaterialToUse "materials/b.vmat"
}
'''

VMAT_B = '''Layer0
{
\tshader "vr_standard.vfx"
\tTextureColor "materials/tex_b.tga"
\tMaterialToUse "materials/a.vmat"
}
'''


class MaterialCycleTests(unittest.TestCase):
    def test_cyclic_materials_terminate_and_parse_once(self):
        with tempfile.TemporaryDirectory() as addon_dir:
            materials_dir = os.path.join(addon_dir, "materials")
            os.makedirs(materials_dir)
            with open(os.path.join(materials_dir, "a.vmat"), "w") as f:
                f.write(VMAT_A)
            with open(os.path.join(materials_dir, "b.vmat"), "w") as f:
                f.write(VMAT_B)

            vmap_path = os.path.join(addon_dir, "maps", "test.vmap")
            with mock.patch.object(parse, "extract_vmap_references", return_value=["materials/a.vmat"]), \
                 mock.patch.object(vdf, "load", wraps=vdf.load) as load_spy:
                # Should not raise RecursionError.
                addon_assets, referenced_files = parse.get_vmap_references(
                    addon_dir=addon_dir, vmap=vmap_path, scan_meshes=False,
                )

            self.assertEqual(load_spy.call_count, 2)
            self.assertIn("materials/a.vmat", referenced_files)
            self.assertIn("materials/b.vmat", referenced_files)


if __name__ == "__main__":
    unittest.main()
