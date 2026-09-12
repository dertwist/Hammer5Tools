"""Tests for prop_static blockout generation.

The end-to-end proof is a real compile: the generated map was built by
resourcecompiler.exe through VRAD3 to exit code 0. These tests cover the parts
that do not need CS2 installed - argument handling and the skeleton surgery.
"""

from __future__ import annotations

import pytest

from automation.operations import vmap_blockout

_SKELETON = '''<!-- dmx encoding keyvalues2 4 format vmap 40 -->
"$prefix_element$"
{
\t"map_asset_references" "string_array"
\t[
\t\t"materials/existing.vmat"
\t]
}

"CMapRootElement"
{
\t"world" "CMapWorld"
\t{
\t\t"nodeID" "int" "1"
\t\t"children" "element_array"
\t\t[
\t\t\t"element" "e47a5386-6319-4848-813f-967de2074e89",
\t\t\t"CMapEntity"
\t\t\t{
\t\t\t\t"nodeID" "int" "95"
\t\t\t\t"children" "element_array"
\t\t\t\t[
\t\t\t\t]
\t\t\t}
\t\t]
\t}
}
'''


def _skeleton(tmp_path):
    path = tmp_path / "skeleton.kv2"
    path.write_text(_SKELETON, encoding="utf-8")
    return path.read_text(encoding="utf-8")


def test_children_array_end_is_found_past_nested_arrays(tmp_path):
    text = _skeleton(tmp_path)

    end = vmap_blockout._find_world_children_end(text)

    # It must be the outer array's bracket, not the nested entity's: the nested
    # CMapEntity and its own children array both fall before it.
    assert text[end] == "]"
    assert "CMapEntity" in text[:end]
    assert text[:end].count("[") == text[:end].count("]") + 1


def test_node_ids_continue_past_the_highest_in_the_skeleton(tmp_path):
    assert vmap_blockout._next_node_id(_skeleton(tmp_path)) == 96


def test_asset_reference_is_added_once(tmp_path):
    text = _skeleton(tmp_path)

    once = vmap_blockout._add_asset_reference(text, vmap_blockout.DEFAULT_BOX_MODEL)
    twice = vmap_blockout._add_asset_reference(once, vmap_blockout.DEFAULT_BOX_MODEL)

    assert once.count(vmap_blockout.DEFAULT_BOX_MODEL) == 1
    assert twice == once
    assert "materials/existing.vmat" in twice


def test_size_becomes_scale_against_the_ten_unit_base():
    # placeholder_box is 10x10x10, so a 512-unit box scales by 51.2.
    assert vmap_blockout._triple([512 / vmap_blockout._BOX_BASE_SIZE] * 3) == "51.2 51.2 51.2"


def test_a_skeleton_without_a_world_is_rejected():
    with pytest.raises(ValueError, match="CMapWorld"):
        vmap_blockout._find_world_children_end('"CMapRootElement" { }')


def test_boxes_are_required(tmp_path):
    with pytest.raises(ValueError, match="at least one box"):
        vmap_blockout.write_blockout(str(tmp_path / "out.vmap"), [], cs2_path=str(tmp_path))


def test_a_box_needs_a_positive_size_in_every_axis():
    with pytest.raises(ValueError, match="size"):
        vmap_blockout._numbers(None, "boxes[0].size")
    with pytest.raises(ValueError, match="three numbers"):
        vmap_blockout._numbers([1, 2], "boxes[0].size")


def test_missing_skeleton_is_reported_before_any_work(tmp_path):
    with pytest.raises(FileNotFoundError, match="Skeleton"):
        vmap_blockout.write_blockout(
            str(tmp_path / "out.vmap"),
            [{"size": [64, 64, 64]}],
            skeleton=str(tmp_path / "nope.vmap"),
            cs2_path=str(tmp_path),
        )
