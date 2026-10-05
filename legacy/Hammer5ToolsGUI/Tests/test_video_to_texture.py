from pathlib import Path

from PIL import Image

from gui.forms.video_to_texture.convert import (
    cell_size_for,
    convert_frames,
    grid_for,
    material_reference,
    read_animation_frames,
    sample_evenly,
)


def _frames(count, size=(64, 32), alpha=255):
    return [Image.new("RGBA", size, (index, 0, 0, alpha)) for index in range(count)]


def test_grid_matches_reference_layout():
    assert grid_for(1) == (1, 1)
    assert grid_for(16) == (4, 4)
    assert grid_for(10) == (3, 4)


def test_cell_size_keeps_aspect_and_fits_the_sheet():
    assert cell_size_for((64, 32), 256, 16) == (256, 128)
    # 256 cells at 512px would be a 8192px sheet, so the cell shrinks.
    width, height = cell_size_for((64, 64), 512, 256)
    assert width * grid_for(256)[0] <= 4096 and height == width


def test_sample_evenly_covers_the_whole_source():
    assert sample_evenly(list(range(10)), 4) == [0, 2, 5, 7]
    assert sample_evenly(list(range(3)), 8) == [0, 1, 2]


def test_convert_writes_sheet_and_vmat(tmp_path):
    texture, vmat = convert_frames(_frames(4), 10.0, tmp_path / "out", "clip", 32, content_dir=tmp_path)
    assert Image.open(texture).size == (64, 32)  # 2x2 grid of 32x16 cells
    body = vmat.read_text(encoding="utf-8")
    assert 'g_nNumAnimationCells "4"' in body
    assert 'g_vAnimationGrid "[2 2]"' in body
    assert 'g_flAnimationTimePerFrame "0.100"' in body
    assert "F_TEXTURE_ANIMATION 1" in body
    assert 'TextureColor "out/clip_color.png"' in body
    assert "F_TRANSLUCENT" not in body


def test_transparent_source_gets_a_translucent_material(tmp_path):
    _, vmat = convert_frames(_frames(2, alpha=0), 10.0, tmp_path, "clip", 32)
    body = vmat.read_text(encoding="utf-8")
    assert "F_TRANSLUCENT 1" in body and "TextureTranslucency" in body


def test_gif_frames_and_fps_round_trip(tmp_path):
    gif = tmp_path / "anim.gif"
    frames = [Image.new("RGB", (8, 8), (index * 50, 0, 0)) for index in range(5)]
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=50, loop=0)
    read, fps = read_animation_frames(gif)
    assert len(read) == 5
    assert abs(fps - 20.0) < 0.01


def test_material_reference_falls_back_to_the_plain_path(tmp_path):
    outside = tmp_path / "elsewhere" / "clip_color.png"
    assert material_reference(outside, tmp_path / "content") == outside.as_posix()


def test_vmat_is_a_single_layer_block(tmp_path):
    _, vmat = convert_frames(_frames(4), 10.0, tmp_path, "clip", 32)
    body = vmat.read_text(encoding="utf-8")
    assert body.count("Layer0") == 1
    assert 'shader "csgo_complex.vfx"' in body
    assert body.count("{") == body.count("}")
