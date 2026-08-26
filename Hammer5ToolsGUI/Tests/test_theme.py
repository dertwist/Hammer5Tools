"""Tests for runtime palette transformations."""

from gui.styles import theme


def test_bright_theme_uses_off_white_surfaces_and_dark_text():
    theme.set_brightness_level(theme.LEVEL_BRIGHT)
    try:
        qss = theme.transform_qss(
            "QWidget { background: #272727; color: #e5e5e5; border-color: #4a83c9; }"
        )

        assert "background: #d8d8d8" in qss
        assert "color: #1a1a1a" in qss
        assert "border-color: #366fb5" in qss
        assert "#ffffff" not in qss.lower()
    finally:
        theme.set_brightness_level(theme.LEVEL_STANDARD)


def test_bright_theme_transforms_white_and_rgb_colors():
    theme.set_brightness_level(theme.LEVEL_BRIGHT)
    try:
        qss = theme.transform_qss(
            "color: #FFFFFF; selection-color: white; background: rgb(57, 57, 57);"
        )

        assert qss == (
            "color: #000000; selection-color: #000000; "
            "background: rgb(198, 198, 198);"
        )
        assert theme.gl_clear_color() == (0.82, 0.82, 0.82)
    finally:
        theme.set_brightness_level(theme.LEVEL_STANDARD)
