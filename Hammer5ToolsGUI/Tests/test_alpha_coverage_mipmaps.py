"""Alpha-tested cutouts must keep their coverage down the mip chain.

``glGenerateMipmap`` box-filters alpha like colour, which is wrong for a binary alpha
test: averaging pulls a sparse cutout toward its mean alpha, and once that mean drops
under the cutoff every texel fails and the surface disappears.  In the SmartProp
viewport this made chain-link netting and razor wire dissolve with distance and at
grazing angles.  See ``build_alpha_coverage_mipmaps``.
"""
import numpy as np
import pytest

from gui.editors.smartprop_editor.viewport_3d.mesh_cache import build_alpha_coverage_mipmaps

CUTOFF = 0.5


def _coverage(level, cutoff=CUTOFF):
    """Fraction of texels that pass the alpha test, measured the way the GPU sees it."""
    return float((level[:, :, 3] >= cutoff * 255.0).mean())


def _box_filter(image, times):
    """The plain box-filtered mip level glGenerateMipmap would have produced."""
    current = image.astype(np.float32)
    for _ in range(times):
        height, width = current.shape[0] // 2, current.shape[1] // 2
        current = current[:height * 2, :width * 2].reshape(height, 2, width, 2, 4).mean(axis=(1, 3))
    return current


def _netting(size=256, spacing=16, seed=7):
    """A sparse cutout resembling chain-link netting: thin soft-edged lines on a grid.

    Edges are antialiased and line strength varies slightly, as real cutout art does.
    Both matter: a perfectly uniform hard-edged line has no gradient spanning the
    cutoff, so no filter could hold its coverage and a test built on one would be
    asserting something impossible rather than something useful.
    """
    axis = np.arange(size)
    distance = np.minimum(axis % spacing, spacing - axis % spacing)
    line = np.clip(1.0 - distance * 0.75, 0.0, 1.0)
    grid = np.maximum(line[:, None], line[None, :])

    rng = np.random.default_rng(seed)
    variation = rng.uniform(0.75, 1.0, size=(size // 4, size // 4))
    variation = np.repeat(np.repeat(variation, 4, axis=0), 4, axis=1)

    image = np.zeros((size, size, 4), np.uint8)
    image[:, :, :3] = 200
    image[:, :, 3] = np.rint(np.clip(grid * variation, 0.0, 1.0) * 255.0).astype(np.uint8)
    return image


def _expected_sizes(height, width):
    """GL's mip chain: level i is max(1, dim >> i), ending at 1x1."""
    sizes = []
    while True:
        sizes.append((height, width))
        if height == 1 and width == 1:
            return sizes
        height, width = max(1, height // 2), max(1, width // 2)


def test_box_filtering_destroys_sparse_cutout_coverage():
    """The bug being fixed: without correction the netting is simply gone by mip 5."""
    netting = _netting()
    assert _coverage(netting) > 0.05
    assert _coverage(_box_filter(netting, 5)) < 0.01


def test_coverage_survives_the_mip_chain():
    netting = _netting()
    levels = build_alpha_coverage_mipmaps(netting, CUTOFF)
    base = _coverage(levels[0])

    # Levels too small to represent the fraction at all are excluded: a 4x4 level has
    # 16 texels and cannot express 12% coverage to any better than +/-6%.
    for index, level in enumerate(levels):
        if level.shape[0] * level.shape[1] < 256:
            break
        assert _coverage(level) == pytest.approx(base, abs=0.02), f"mip{index} lost coverage"


def test_chain_matches_gl_layout():
    netting = _netting(size=256)
    levels = build_alpha_coverage_mipmaps(netting, CUTOFF)
    assert [level.shape[:2] for level in levels] == _expected_sizes(256, 256)
    assert all(level.dtype == np.uint8 for level in levels)
    # glTexImage2D reads these directly; a non-contiguous view would upload garbage.
    assert all(level.flags["C_CONTIGUOUS"] for level in levels)
    # Level 0 is the source image untouched.
    assert np.array_equal(levels[0], netting)


@pytest.mark.parametrize("size", [(48, 17), (17, 48), (1, 64), (3, 3)])
def test_handles_non_power_of_two_and_degenerate_sizes(size):
    height, width = size
    image = np.zeros((height, width, 4), np.uint8)
    image[::2, :, 3] = 255
    levels = build_alpha_coverage_mipmaps(image, CUTOFF)
    assert [level.shape[:2] for level in levels] == _expected_sizes(height, width)


@pytest.mark.parametrize("alpha", [0, 255])
def test_uniform_alpha_is_left_alone(alpha):
    """Fully clipped or fully opaque: there is no coverage to preserve, so plain
    box filtering is correct and the correction must not invent a gradient."""
    image = np.zeros((32, 32, 4), np.uint8)
    image[:, :, 3] = alpha
    levels = build_alpha_coverage_mipmaps(image, CUTOFF)
    assert all(np.all(level[:, :, 3] == alpha) for level in levels)
