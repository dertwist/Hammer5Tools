import os
import tempfile
import unittest

from gui.forms.unreal_porter.asset_compiler import (
    find_changed_compile_assets,
    find_compile_assets,
    snapshot_compile_assets,
)


class UnrealAssetCompilerTests(unittest.TestCase):
    def test_finds_all_descriptor_types_and_excludes_export_cache(self):
        with tempfile.TemporaryDirectory() as output_dir:
            expected = []
            for relative_path in (
                "materials/props/chair.vmat",
                "models/props/chair.vmdl",
                "maps/showroom.vmap",
                "smartprops/chair_set.vsmart",
            ):
                path = os.path.join(output_dir, relative_path)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as asset:
                    asset.write("test")
                expected.append(os.path.normpath(path))

            ignored = os.path.join(output_dir, "materials", "chair.tga")
            with open(ignored, "w", encoding="utf-8") as texture:
                texture.write("test")

            cache_dir = os.path.join(output_dir, "hammer5tools", "unrealporter", "tmp")
            os.makedirs(cache_dir, exist_ok=True)
            with open(os.path.join(cache_dir, "cached.vmat"), "w", encoding="utf-8") as cached:
                cached.write("test")

            actual = find_compile_assets(output_dir, cache_dir)

        self.assertEqual(sorted(expected, key=str.casefold), actual)

    def test_changed_scan_ignores_untouched_existing_assets(self):
        with tempfile.TemporaryDirectory() as output_dir:
            existing = os.path.join(output_dir, "materials", "existing.vmat")
            os.makedirs(os.path.dirname(existing), exist_ok=True)
            with open(existing, "w", encoding="utf-8") as asset:
                asset.write("existing")
            baseline = snapshot_compile_assets(output_dir)

            created = os.path.join(output_dir, "models", "new.vmdl")
            os.makedirs(os.path.dirname(created), exist_ok=True)
            with open(created, "w", encoding="utf-8") as asset:
                asset.write("new")

            actual = find_changed_compile_assets(output_dir, "", baseline)

        self.assertEqual([os.path.normpath(created)], actual)


if __name__ == "__main__":
    unittest.main()
