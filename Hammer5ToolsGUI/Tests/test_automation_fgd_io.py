"""Tests for entity definitions parsed from the game's FGD files.

The fixture reproduces the two declaration shapes CS2 actually uses: a name on
the same line as the class keyword, and a name below a metadata block that
contains its own brackets and `=` signs.
"""

from __future__ import annotations

import pytest

from automation.formats import fgd_io

_FGD = '''
@include "base.fgd"

@VisGroupFilter { filter_type = "toolsMaterial" material = "toolsclip.vmat" }

@BaseClass = Targetname
[
\ttargetname(target_source) : "Name" : "" : "The name that other entities refer to this entity by."
]

@PointClass base(Targetname) iconsprite("materials/editor/info_player.vmat") = info_player_terrorist :
\t"This entity marks a terrorist spawn point."
[
\tpriority(integer) : "Priority" : 0 : "Higher priority spawns are used first."
]

@PointClass
\tbase(Targetname)
\tmetadata
\t{
\t\tmodel_archetypes = [ "static_prop_model" ]
\t\tentity_tool_name = "Static Prop"
\t\tentity_tool_tip = "Adds a static model"
\t\tstatic_prop = true
\t}
= prop_static
[
\tmodel(resource:model) [report] : "Model"
\tskin(materialgroup) : "Material Group" : "default" : "Which material variation to use."
\tsolid(choices) [ group="Collision" ] : "Collision Type" : 6 =
\t[
\t\t0: "Not Solid"
\t\t6: "Use VPhysics"
\t]
]
'''


@pytest.fixture
def definitions(tmp_path, monkeypatch):
    game = tmp_path / "game" / "csgo"
    game.mkdir(parents=True)
    (game / "test.fgd").write_text(_FGD, encoding="utf-8")
    fgd_io.load_definitions.cache_clear()
    monkeypatch.setattr(fgd_io, "get_cs2_path", lambda: str(tmp_path))
    yield str(tmp_path)
    fgd_io.load_definitions.cache_clear()


def test_a_name_on_the_class_line_is_parsed(definitions):
    entry = fgd_io.entity_info("info_player_terrorist", cs2_path=definitions)

    assert entry["description"] == "This entity marks a terrorist spawn point."
    assert entry["kind"] == "PointClass"


def test_a_name_below_a_metadata_block_is_parsed(definitions):
    # The block holds "[ ... ]" arrays and its own "=" signs, either of which
    # will swallow the class name if the header is split naively.
    entry = fgd_io.entity_info("prop_static", cs2_path=definitions)

    assert entry["classname"] == "prop_static"
    assert entry["description"] == "Adds a static model", "fell back past the tool tip"


def test_properties_carry_type_and_help_text(definitions):
    properties = {item["name"]: item for item in fgd_io.entity_info("prop_static", cs2_path=definitions)["properties"]}

    assert properties["skin"]["type"] == "materialgroup"
    assert properties["skin"]["description"] == "Which material variation to use."
    assert properties["model"]["type"] == "resource:model"


def test_inherited_properties_are_included(definitions):
    names = {item["name"] for item in fgd_io.entity_info("prop_static", cs2_path=definitions)["properties"]}

    assert "targetname" in names, "base(Targetname) properties were not merged in"


def test_properties_can_be_left_out(definitions):
    entry = fgd_io.entity_info("prop_static", include_properties=False, cs2_path=definitions)

    assert "properties" not in entry
    assert entry["description"]


def test_search_matches_name_or_description(definitions):
    by_name = fgd_io.entity_info(search="prop_", cs2_path=definitions)
    by_description = fgd_io.entity_info(search="terrorist spawn", cs2_path=definitions)

    assert "prop_static" in [item["classname"] for item in by_name["matches"]]
    assert "info_player_terrorist" in [item["classname"] for item in by_description["matches"]]


def test_an_unknown_class_suggests_near_matches(definitions):
    with pytest.raises(ValueError, match="prop_static"):
        fgd_io.entity_info("prop_stati", cs2_path=definitions)


def test_describe_is_quiet_when_a_class_is_unknown(definitions):
    assert fgd_io.describe("prop_static", cs2_path=definitions) == "Adds a static model"
    assert fgd_io.describe("no_such_entity", cs2_path=definitions) == ""


def test_a_tree_without_definitions_is_reported(tmp_path):
    fgd_io.load_definitions.cache_clear()
    with pytest.raises(FileNotFoundError, match="FGD"):
        fgd_io.load_definitions(str(tmp_path))
    fgd_io.load_definitions.cache_clear()
