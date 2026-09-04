"""Screenshot commands built for the loading editor's point_camera entities.

Core projects entity properties as text, so position and angles have to be read
back as numbers before they can go into setpos/setang. Getting that wrong put
the shots at the wrong place, pointing the wrong way, under the wrong name.
"""

from __future__ import annotations

import pytest

from gui.editors.loading_editor import commands as commands_module
from gui.editors.loading_editor.commands import PLAYER_EYE_HEIGHT, generate_commands


def build(cameras, monkeypatch, history=False):
    monkeypatch.setattr(commands_module, "parse", lambda path, show_entity_properties=False: cameras)
    monkeypatch.setattr(commands_module.CS2Netcon, "query", staticmethod(lambda *a, **k: None))
    generated, session = generate_commands("maps/de_test.vmap", history=history)
    return generated, session


def only(generated, keyword):
    return [c for c in generated if keyword in c]


CAMERA = {
    "classname": "point_camera",
    "origin": "619.40454 621.2658 284.0724",
    "angles": "7.6000166 134.80061 0",
    "targetname": "overview",
    "FOV": "90",
}


def test_angles_become_pitch_yaw_roll(monkeypatch):
    generated, _ = build([dict(CAMERA)], monkeypatch)
    assert only(generated, "setang") == [
        'ent_fire worldent addoutput "OnUser1>cmd>command>setang 7.6 134.8006 0>0.1>1"'
    ]


def test_angles_survive_the_legacy_core_projection(monkeypatch):
    """Older Core builds projected the QAngle debug text into the property."""
    camera = dict(CAMERA, angles="QAngle { Pitch = 7.6000166, Yaw = 134.80061, Roll = 0 }")
    generated, _ = build([camera], monkeypatch)
    setang, = only(generated, "setang")
    assert "QAngle" not in setang
    assert "setang 7.6 134.8006 0" in setang


def test_the_camera_is_lowered_to_put_the_eye_on_the_camera(monkeypatch):
    """setpos moves the player origin, but the shot comes from the eye."""
    generated, _ = build([dict(CAMERA)], monkeypatch)
    setpos, = only(generated, "setpos")
    expected_z = 284.0724 - PLAYER_EYE_HEIGHT
    assert f"setpos 619.4045 621.2658 {expected_z:.4f}".rstrip("0") in setpos


def test_the_fov_of_the_camera_is_used(monkeypatch):
    generated, _ = build([dict(CAMERA)], monkeypatch)
    assert only(generated, "fov_cs_debug") == [
        'ent_fire worldent addoutput "OnUser1>cmd>command>fov_cs_debug 90>0.1>1"'
    ]


def test_a_camera_without_fov_still_gets_a_shot(monkeypatch):
    """Losing the whole screenshot over a missing FOV is worse than keeping it."""
    camera = dict(CAMERA)
    del camera["FOV"]
    generated, _ = build([camera], monkeypatch)
    assert only(generated, "fov_cs_debug") == []
    assert len(only(generated, "png_screenshot")) == 1


def test_the_targetname_names_the_screenshot(monkeypatch):
    generated, _ = build([dict(CAMERA)], monkeypatch)
    assert 'screenshot_prefix overview>' in only(generated, "screenshot_prefix")[0]


def test_an_unnamed_camera_falls_back_to_the_map_name(monkeypatch):
    camera = dict(CAMERA, targetname="")
    generated, _ = build([camera], monkeypatch)
    assert 'screenshot_prefix de_test_cam0>' in only(generated, "screenshot_prefix")[0]


def test_a_name_with_spaces_cannot_break_the_output(monkeypatch):
    """The name sits inside an ent_fire addoutput parameter."""
    camera = dict(CAMERA, targetname='sky cam "one"')
    generated, _ = build([camera], monkeypatch)
    prefix = only(generated, "screenshot_prefix")[0]
    assert '"' not in prefix.split("screenshot_prefix ")[1].split(">")[0]
    assert "screenshot_prefix sky_cam_one>" in prefix


def test_a_camera_without_a_position_is_skipped(monkeypatch):
    camera = dict(CAMERA, origin=None)
    generated, _ = build([camera], monkeypatch)
    assert only(generated, "setpos") == []


def test_every_camera_gets_its_own_delayed_shot(monkeypatch):
    cameras = [dict(CAMERA, targetname=f"cam{i}") for i in range(3)]
    generated, _ = build(cameras, monkeypatch)
    assert len(only(generated, "png_screenshot")) == 3
    # ...>setpos X Y Z>delay>1"  -- the delay is the second field from the end
    delays = [c.split(">")[-2] for c in only(generated, "setpos")]
    assert delays == sorted(delays, key=float)
    assert len(set(delays)) == 3   # no two cameras share a moment


def test_history_mode_uses_a_dated_subdir(monkeypatch):
    generated, session = build([dict(CAMERA)], monkeypatch, history=True)
    assert session is not None
    assert any(f"screenshot_subdir" in c and session in c for c in generated)
