import os
import sys
import tempfile
import unittest
from PIL import Image

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.editors.loading_editor.timeline import render_animation


class TestRenderAnimation(unittest.TestCase):
    def setUp(self):
        self.src_dir = tempfile.TemporaryDirectory()
        self.out_dir = tempfile.TemporaryDirectory()
        # Odd, mismatched sizes + alpha to exercise the resize/flatten path and
        # the MP4 even-dimension pad filter.
        sizes = [(33, 21), (30, 20), (33, 21)]
        self.image_paths = []
        for i, size in enumerate(sizes):
            path = os.path.join(self.src_dir.name, f"frame_{i}.png")
            Image.new("RGBA", size, (i * 40, 10, 10, 255)).save(path)
            self.image_paths.append(path)

    def tearDown(self):
        self.src_dir.cleanup()
        self.out_dir.cleanup()

    def test_gif(self):
        out = render_animation(self.image_paths, self.out_dir.name, "cam", fmt="GIF")
        self.assertTrue(out.endswith("_timeline.gif"))
        self.assertTrue(os.path.exists(out))
        with Image.open(out) as img:
            self.assertEqual(img.n_frames, 3)

    def test_webp_quality_presets(self):
        out = render_animation(self.image_paths, self.out_dir.name, "cam", fmt="WEBP", quality="Low")
        self.assertTrue(out.endswith("_timeline.webp"))
        with Image.open(out) as img:
            self.assertEqual(img.n_frames, 3)

    def test_mp4(self):
        out = render_animation(self.image_paths, self.out_dir.name, "cam", fmt="MP4", quality="Medium")
        self.assertTrue(out.endswith("_timeline.mp4"))
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_no_images_raises(self):
        with self.assertRaises(ValueError):
            render_animation([], self.out_dir.name, "cam")


if __name__ == "__main__":
    unittest.main()
