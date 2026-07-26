"""Batch reference rewriting.

Two things this guards, both found while reorganising a 250-prop UE5 port:

  * a per-file loop re-walked the whole addon and reloaded every map once per
    moved asset, so a realistic move never finished;
  * chained str.replace lets one rename's *output* be eaten by another rename's
    input, silently producing paths that point nowhere.

The vmap prefix-block case needs Datamodel.NET and is skipped where that isn't
available; the text-file cases are pure Python and always run.
"""
import os
import sys
import shutil
import tempfile
import unittest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.forms.asset_manager.reference_updater import ReferenceUpdater


class TestBatchRewrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.u = ReferenceUpdater(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel, text):
        p = os.path.join(self.root, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        return p

    def _read(self, rel):
        with open(os.path.join(self.root, rel.replace('/', os.sep)), encoding='utf-8', newline='') as f:
            return f.read()

    def test_rewrites_many_paths_in_one_pass(self):
        self._write('models/a.vmdl', 'to = "materials/old/red.vmat"\nto = "materials/old/blue.vmat"\n')
        n = self.u.update_references_batch({
            'materials/old/red.vmat': 'materials/new/warm/red.vmat',
            'materials/old/blue.vmat': 'materials/new/cool/blue.vmat',
        })
        self.assertEqual(len(n), 1)
        out = self._read('models/a.vmdl')
        self.assertIn('materials/new/warm/red.vmat', out)
        self.assertIn('materials/new/cool/blue.vmat', out)
        self.assertNotIn('materials/old/', out)

    def test_rename_output_is_not_re_renamed(self):
        """A -> B where B is itself another rename's source must not double-apply."""
        self._write('models/a.vmdl', '"materials/x.vmat"\n"materials/y.vmat"\n')
        self.u.update_references_batch({
            'materials/x.vmat': 'materials/y.vmat',
            'materials/y.vmat': 'materials/z.vmat',
        })
        out = self._read('models/a.vmdl')
        self.assertIn('"materials/y.vmat"', out)   # x became y, and stayed y
        self.assertIn('"materials/z.vmat"', out)   # the original y became z

    def test_longer_path_wins_over_its_own_prefix(self):
        self._write('models/a.vmdl', '"models/pack/mesh/tree.vmdl"\n"models/pack/mesh.vmdl"\n')
        self.u.update_references_batch({
            'models/pack/mesh': 'models/NEW',
            'models/pack/mesh/tree.vmdl': 'models/nature/tree.vmdl',
        })
        out = self._read('models/a.vmdl')
        self.assertIn('"models/nature/tree.vmdl"', out)
        self.assertIn('"models/NEW.vmdl"', out)

    def test_only_scannable_extensions_touched(self):
        self._write('notes.txt', 'materials/old/red.vmat')
        self._write('models/a.vmdl', 'materials/old/red.vmat')
        mod = self.u.update_references_batch({'materials/old/red.vmat': 'materials/new/red.vmat'})
        self.assertEqual(len(mod), 1)
        self.assertEqual(self._read('notes.txt'), 'materials/old/red.vmat')

    def test_untouched_files_not_rewritten(self):
        p = self._write('models/b.vmdl', 'nothing to see')
        before = os.stat(p).st_mtime_ns
        self.assertEqual(self.u.update_references_batch({'a': 'b'}), [])
        self.assertEqual(os.stat(p).st_mtime_ns, before)

    def test_crlf_preserved(self):
        self._write('models/a.vmdl', 'x\r\n"materials/old/red.vmat"\r\ny\r\n')
        self.u.update_references_batch({'materials/old/red.vmat': 'materials/new/red.vmat'})
        self.assertEqual(self._read('models/a.vmdl'), 'x\r\n"materials/new/red.vmat"\r\ny\r\n')

    def test_empty_rename_map_is_a_noop(self):
        self.assertEqual(self.u.update_references_batch({}), [])

    def test_single_rename_wrapper_still_works(self):
        self._write('models/a.vmdl', '"materials/old/red.vmat"')
        self.u.update_references('materials/old/red.vmat', 'materials/new/red.vmat')
        self.assertIn('materials/new/red.vmat', self._read('models/a.vmdl'))


VMAP = os.path.join(
    r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive",
    "content", "csgo_addons", "de_firewatch", "maps", "Showcase.vmap")


@unittest.skipUnless(os.path.exists(VMAP), "needs a real binary vmap")
class TestVmapRewrite(unittest.TestCase):
    """Binary DMX maps go through Datamodel.NET, whose writer drops the prefix
    block that holds the thumbnail and asset-reference cache."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "maps"))
        self.map = os.path.join(self.tmp.name, "maps", "Showcase.vmap")
        shutil.copy(VMAP, self.map)
        self.u = ReferenceUpdater(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    OLD = b"models/firewatchtower/meshes/antenna.vmdl"
    NEW = b"models/firewatch/thirdparty/structures/tower/antenna.vmdl"

    def test_rewrites_model_paths_and_keeps_prefix_block(self):
        from src.gitvmapmerge import _prefix_end
        with open(self.map, "rb") as f:
            before = f.read()
        # assertTrue, not assertIn: a failed assertIn on a 500 KB blob dumps it
        self.assertTrue(self.OLD in before, "fixture map no longer contains the test path")
        prefix_before = _prefix_end(before)

        mod = self.u.update_references_batch({self.OLD.decode(): self.NEW.decode()})
        self.assertEqual(len(mod), 1)

        with open(self.map, "rb") as f:
            after = f.read()
        self.assertFalse(self.OLD in after, "old path survived the rewrite")
        self.assertTrue(self.NEW in after, "new path missing after rewrite")
        self.assertEqual(_prefix_end(after), prefix_before)
        self.assertTrue(after[:prefix_before] == before[:prefix_before],
                        "prefix block (thumbnail + asset cache) was not preserved")


if __name__ == "__main__":
    unittest.main()
