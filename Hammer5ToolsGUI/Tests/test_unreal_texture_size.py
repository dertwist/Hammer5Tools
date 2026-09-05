import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication, QWidget

from gui.forms.unreal_porter.material_converter import process_material_textures
from gui.forms.unreal_porter import main as porter_main
from gui.forms.unreal_porter.texture_utils import (
    DEFAULT_TEXTURE_SIZE_LIMIT,
    MAX_TEXTURE_SIZE_LIMIT,
    limit_texture_size,
    normalize_texture_size_limit,
)


app = QApplication.instance() or QApplication([])


def test_texture_size_limit_defaults_and_clamps():
    assert normalize_texture_size_limit(None) == DEFAULT_TEXTURE_SIZE_LIMIT
    assert normalize_texture_size_limit(MAX_TEXTURE_SIZE_LIMIT + 1) == MAX_TEXTURE_SIZE_LIMIT
    assert normalize_texture_size_limit(0) == 1


def test_texture_size_limit_preserves_aspect_ratio_without_upscaling():
    wide = Image.new("RGB", (200, 100))
    small = Image.new("RGB", (20, 10))

    assert limit_texture_size(wide, 50).size == (50, 25)
    assert limit_texture_size(small, 50).size == (20, 10)


def test_material_texture_outputs_respect_selected_limit(tmp_path):
    bulk_dir = tmp_path / "bulk"
    output_dir = tmp_path / "output"
    bulk_dir.mkdir()
    source = bulk_dir / "T_Wall_D.png"
    Image.new("RGBA", (160, 80), (255, 0, 0, 255)).save(source)

    slots, written, missing, _summary = process_material_textures(
        {
            "material": "/Game/Materials/MI_Wall.MI_Wall",
            "textures": {"BaseColor": "/Game/Textures/T_Wall_D.T_Wall_D"},
        },
        str(bulk_dir),
        str(output_dir),
        slot_overrides={"BaseColor": "color"},
        tex_format="png",
        max_texture_size=40,
    )

    assert written == 1
    assert missing == []
    with Image.open(output_dir / slots["color"]) as converted:
        assert converted.size == (40, 20)


def test_texture_size_control_defaults_to_4096_and_caps_at_16384(monkeypatch):
    saved = []
    monkeypatch.setattr(
        porter_main, "get_settings_value", lambda _section, _key, default=None: default
    )
    monkeypatch.setattr(
        porter_main, "get_settings_bool", lambda _section, _key, default=False: default
    )
    monkeypatch.setattr(
        porter_main,
        "set_settings_value",
        lambda section, key, value: saved.append((section, key, value)),
    )

    holder = QWidget()
    box = porter_main.UnrealPorterWidget._build_textures_box(holder)

    assert box is not None
    assert holder.tex_max_size_spin.value() == DEFAULT_TEXTURE_SIZE_LIMIT
    assert holder.tex_max_size_spin.maximum() == MAX_TEXTURE_SIZE_LIMIT
    holder.tex_max_size_spin.setValue(MAX_TEXTURE_SIZE_LIMIT + 1)
    assert holder.tex_max_size_spin.value() == MAX_TEXTURE_SIZE_LIMIT
    assert saved[-1] == ("UnrealConverter", "tex_max_size", MAX_TEXTURE_SIZE_LIMIT)
