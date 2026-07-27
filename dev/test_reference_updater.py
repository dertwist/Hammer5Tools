"""Batch reference rewriting.

Three things this guards, all found while reorganising a 250-prop UE5 port:

  * a per-file loop re-walked the whole addon and reloaded every map once per
    moved asset, so a realistic move never finished;
  * chained str.replace lets one rename's *output* be eaten by another rename's
    input, silently producing paths that point nowhere;
  * the DMX prefix block's asset-reference cache is not reachable through
    Datamodel.NET's object model, so a rename left it pointing at the old paths
    and Hammer reported every moved asset as missing.

The vmap cases need Datamodel.NET and a real map, and are skipped where either is
unavailable; the text-file cases are pure Python and always run.
"""
import collections
import os
import re
import shutil
import sys
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

    def test_folder_rename_does_not_eat_a_sibling_with_the_same_prefix(self):
        """Moving a folder is one rename of 'dir/' - without the trailing slash
        'models/foo' also matches 'models/foobar' and drags the sibling along."""
        self._write('models/a.vmdl', '"models/foo/tree.vmdl"\n"models/foobar/rock.vmdl"\n')
        self.u.update_references_batch({'models/foo/': 'models/nature/foo/'})
        out = self._read('models/a.vmdl')
        self.assertIn('"models/nature/foo/tree.vmdl"', out)
        self.assertIn('"models/foobar/rock.vmdl"', out)

    def test_folder_rename_moves_every_reference_under_it(self):
        self._write('models/a.vmdl', '"models/foo/a.vmdl"\n"models/foo/deep/b.vmdl"\n')
        self.u.update_references_batch({'models/foo/': 'models/nature/foo/'})
        out = self._read('models/a.vmdl')
        self.assertIn('"models/nature/foo/a.vmdl"', out)
        self.assertIn('"models/nature/foo/deep/b.vmdl"', out)


class TestFindReferencing(unittest.TestCase):
    """The Preview list. It must name the same files the rewrite would touch,
    and must not write anything - it runs before the user has agreed to a move."""

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

    def _rel(self, paths):
        return sorted(os.path.relpath(p, self.root).replace('\\', '/') for p in paths)

    def test_finds_only_files_holding_the_path(self):
        self._write('models/hit.vmdl', 'x "materials/old/red.vmat" y')
        self._write('models/miss.vmdl', 'nothing here')
        self.assertEqual(self._rel(self.u.find_referencing({'materials/old/red.vmat': 'w'})),
                         ['models/hit.vmdl'])

    def test_ignores_unscannable_extensions(self):
        self._write('notes.txt', 'materials/old/red.vmat')
        self.assertEqual(self.u.find_referencing({'materials/old/red.vmat': 'w'}), [])

    def test_changes_nothing_on_disk(self):
        p = self._write('models/a.vmdl', '"materials/old/red.vmat"')
        before = os.stat(p).st_mtime_ns
        self.u.find_referencing({'materials/old/red.vmat': 'materials/new/red.vmat'})
        self.assertEqual(os.stat(p).st_mtime_ns, before)
        with open(p, encoding='utf-8') as f:
            self.assertIn('materials/old/red.vmat', f.read())

    def test_empty_rename_map_is_a_noop(self):
        self._write('models/a.vmdl', 'anything')
        self.assertEqual(self.u.find_referencing({}), [])

    def test_agrees_with_what_the_rewrite_touches(self):
        self._write('models/hit.vmdl', '"models/foo/tree.vmdl"')
        self._write('models/miss.vmdl', '"models/foobar/rock.vmdl"')
        renames = {'models/foo/': 'models/nature/foo/'}
        self.assertEqual(self._rel(self.u.find_referencing(renames)),
                         self._rel(self.u.update_references_batch(renames)))


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

    # Test paths come out of the fixture rather than being hardcoded: this map is a
    # live file that gets reorganised, so a literal path goes stale and the test
    # then passes vacuously against a map that no longer contains it.
    MODEL = re.compile(rb"models/[a-z0-9_/\-]+\.vmdl")

    def _pick(self, buf, prefix_end, region):
        """A model path present in `region` ("prefix" or "body") of the fixture."""
        chunk = buf[:prefix_end] if region == "prefix" else buf[prefix_end:]
        counts = collections.Counter(self.MODEL.findall(chunk))
        if not counts:
            self.skipTest(f"fixture map has no model path in its {region}")
        return counts.most_common(1)[0][0]

    def test_rewrites_prefix_asset_cache(self):
        """The prefix block's asset-reference cache must be repointed too.

        Datamodel.NET exposes only part of that region as writable attributes, so
        a rename applied through the object model left the cache holding the old
        paths - Hammer then reported every moved asset as missing even though the
        map body was correct. Measured on a real map mid-reorg: 217 of 218
        surviving stale references were in here.
        """
        from src.gitvmapmerge import _prefix_end
        with open(self.map, "rb") as f:
            before = f.read()
        pe = _prefix_end(before)
        self.assertIsNotNone(pe, "fixture map prefix block does not parse")
        old = self._pick(before, pe, "prefix")
        new = b"models/zzz_test/renamed/thing.vmdl"

        self.u.update_references_batch({old.decode(): new.decode()})

        with open(self.map, "rb") as f:
            after = f.read()
        pe2 = _prefix_end(after)
        self.assertIsNotNone(pe2, "prefix block no longer parses after rewrite")
        self.assertFalse(old in after[:pe2], "stale path survived in the asset cache")
        self.assertTrue(new in after[:pe2], "new path missing from the asset cache")

    def test_rewrites_body_and_keeps_thumbnail(self):
        """The rewrite must not cost the map its thumbnail.

        Datamodel.NET's writer drops the whole prefix region, so it is spliced
        back from the original. Byte-equality is the wrong assertion now that the
        asset cache inside it is deliberately repointed - what must survive is the
        thumbnail, which is the only large blob in there.
        """
        from src.gitvmapmerge import _prefix_end
        with open(self.map, "rb") as f:
            before = f.read()
        pe = _prefix_end(before)
        old = self._pick(before, pe, "body")
        new = b"models/zzz_test/renamed/thing.vmdl"
        body_before = before[pe:].count(old)
        self.assertTrue(body_before, "picked path is not in the body")

        mod = self.u.update_references_batch({old.decode(): new.decode()})
        self.assertEqual(len(mod), 1)

        with open(self.map, "rb") as f:
            after = f.read()
        pe2 = _prefix_end(after)
        self.assertFalse(old in after, "old path survived the rewrite")
        self.assertEqual(after[pe2:].count(new), body_before)
        # The thumbnail dominates the region; losing it would shrink it drastically.
        self.assertGreater(pe2, pe * 0.9,
                           f"prefix region collapsed from {pe} to {pe2} - thumbnail lost")


if __name__ == "__main__":
    unittest.main()
