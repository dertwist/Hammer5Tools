"""Response-size budgets for the automation read tools.

Every read tool used to return the parsed document twice: once as extracted
fields and once as `raw`. An agent reading a large SmartProp through MCP paid
for the whole asset twice in a single call, so these ceilings exist to keep a
future change from silently re-inflating a response.
"""

from __future__ import annotations

import json

import pytest

from automation.formats.vdata_io import read_vdata, read_vdata_full, write_vdata
from automation.formats.vmat_io import read_vmat, read_vmat_full, write_vmat
from automation.formats.vmdl_io import read_vmdl, read_vmdl_full, write_vmdl
from automation.formats.vsmart_io import read_vsmart, read_vsmart_full, write_vsmart
from automation.formats.vtex_io import read_vtex, read_vtex_full, write_vtex

# Largest response each read tool may return for its fixture below, in bytes of
# minified JSON. The fixtures are deliberately heavier than the shipped preset
# assets, whose largest summary is about 16 KB.
_CEILINGS = {
    "vsmart": 40_000,
    "vmdl": 8_000,
    "vmat": 8_000,
    "vtex": 4_000,
    "vdata": 8_000,
}


def _response_size(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _big_variables(count: int) -> list[dict]:
    return [
        {
            "_class": "CSmartPropVariable_Float",
            "m_VariableName": f"Parameter{index}",
            "m_DisplayName": f"Parameter {index}",
            "m_bExposeAsParameter": True,
            "m_DefaultValue": float(index),
            "m_HideExpression": f"Parameter{max(index - 1, 0)} == 0.0",
        }
        for index in range(count)
    ]


def _deep_children(breadth: int, depth: int) -> list[dict]:
    """A tree shaped like a real SmartProp: a few layout nodes over many leaves."""
    if depth == 0:
        return []
    return [
        {
            "_class": "CSmartPropElement_Model",
            "editor_info": {"m_nElementID": depth * 1000 + index},
            "m_sModelName": f"models/props/budget_{depth}_{index}.vmdl",
            "m_vModelScale": {"m_Components": [{"m_Expression": "LinearScale()"}, 1.0, 1.0]},
            "m_Modifiers": [{"_class": "CSmartPropOperation_RandomRotation", "m_flMaxAngle": 15.0}],
            "m_Children": _deep_children(breadth, depth - 1),
        }
        for index in range(breadth)
    ]


def _fixture(fmt: str, tmp_path) -> str:
    path = str(tmp_path / f"budget.{fmt}")
    if fmt == "vsmart":
        write_vsmart(path, variables=_big_variables(150), children=_deep_children(5, 3))
    elif fmt == "vmdl":
        write_vmdl(path, "models/props/budget.fbx", [{"from": "a.vmat", "to": "b.vmat"}])
    elif fmt == "vmat":
        write_vmat(path, slots={f"TextureSlot{i}": f"materials/budget_{i}.png" for i in range(40)})
    elif fmt == "vtex":
        write_vtex(path, "materials/budget_color.png")
    elif fmt == "vdata":
        write_vdata(path, {f"entry_{i}": {"value": i, "label": f"entry {i}"} for i in range(200)})
    return path


_READERS = {
    "vsmart": (read_vsmart, read_vsmart_full),
    "vmdl": (read_vmdl, read_vmdl_full),
    "vmat": (read_vmat, read_vmat_full),
    "vtex": (read_vtex, read_vtex_full),
    "vdata": (read_vdata, read_vdata_full),
}


@pytest.mark.parametrize("fmt", sorted(_READERS))
def test_read_tools_do_not_return_the_raw_document(fmt, tmp_path):
    read, _read_full = _READERS[fmt]

    assert "raw" not in read(_fixture(fmt, tmp_path))


@pytest.mark.parametrize("fmt", sorted(_READERS))
def test_read_tools_stay_under_their_response_budget(fmt, tmp_path):
    read, read_full = _READERS[fmt]
    path = _fixture(fmt, tmp_path)

    public_size = _response_size(read(path))
    full_size = _response_size(read_full(path))

    assert public_size <= _CEILINGS[fmt], f"{fmt} read returned {public_size} bytes"
    assert public_size < full_size, f"{fmt} read is not smaller than the full read"


def test_full_reader_still_exposes_raw_for_editing(tmp_path):
    path = _fixture("vsmart", tmp_path)

    assert "raw" in read_vsmart_full(path)


def test_summary_is_much_smaller_than_the_full_view(tmp_path):
    path = _fixture("vsmart", tmp_path)

    summary = _response_size(read_vsmart(path))
    full = _response_size(read_vsmart(path, detail="full"))

    # This fixture is deliberately parameter-heavy, which is the worst case: the
    # summary collapses the element tree but keeps every exposed parameter,
    # because naming them is the point of it. Tree-heavy real assets do far
    # better - the shipped presets average an 89% reduction.
    assert summary * 2 < full, f"summary {summary} is not materially smaller than full {full}"

    outline = _response_size({"elements": read_vsmart(path)["elements"]})
    tree = _response_size({"elements": read_vsmart(path, detail="full")["children"]})
    assert outline * 8 < tree, f"element outline {outline} did not collapse the tree {tree}"


def test_summary_still_names_every_exposed_parameter(tmp_path):
    payload = read_vsmart(_fixture("vsmart", tmp_path))

    assert payload["variable_count"] == 150
    assert payload["variables"][7]["name"] == "Parameter7"
    assert payload["variables"][7]["hide_when"] == "Parameter6 == 0.0"


def test_select_addresses_one_node_without_the_document(tmp_path):
    path = _fixture("vsmart", tmp_path)

    selected = read_vsmart(path, select="m_Variables[m_VariableName=Parameter42].m_DefaultValue")

    assert selected["value"] == 42.0
    assert _response_size(selected) < 400


def test_select_failure_names_the_expression(tmp_path):
    path = _fixture("vsmart", tmp_path)

    with pytest.raises(ValueError, match="Missing"):
        read_vsmart(path, select="m_Variables[m_VariableName=Missing]")


def test_vdata_summary_lists_names_without_bodies(tmp_path):
    payload = read_vdata(_fixture("vdata", tmp_path))

    assert payload["entry_count"] == 200
    assert "entry_7" in payload["entry_names"]
    assert "entries" not in payload


def test_server_instructions_stay_within_their_budget():
    from automation.mcp.server import _instructions

    # This text is in every session's context window, so it is capped. Deep
    # knowledge belongs in hammer5tools.guide, which is fetched on demand.
    assert len(_instructions()) // 4 <= 700


def test_instructions_do_not_restate_the_tool_list():
    from automation.mcp.server import _instructions
    from automation.tools import TOOLS

    text = _instructions()
    named = [tool.name for tool in TOOLS if tool.name in text]

    # tools/list already carries every name and schema; repeating them here
    # pays for the same information twice in every session.
    assert len(named) <= 4, f"instructions restate {len(named)} tool names"


def test_every_guide_topic_loads_and_stays_readable():
    from automation.guides.loader import TOPICS, guide

    index = guide()
    assert {entry["topic"] for entry in index["topics"]} == set(TOPICS)

    for topic in TOPICS:
        content = guide(topic)["content"]
        assert content, f"{topic} is empty"
        assert len(content) // 4 <= 2_000, f"{topic} is too long to fetch casually"


def test_unknown_guide_topic_lists_the_real_ones():
    from automation.guides.loader import guide

    with pytest.raises(ValueError, match="vsmart-expressions"):
        guide("how-do-i-source-2")


def test_every_tool_is_documented_in_a_guide_or_the_instructions():
    from automation.guides.loader import TOPICS, guide
    from automation.mcp.server import _instructions
    from automation.tools import TOOLS

    corpus = _instructions() + "".join(guide(topic)["content"] for topic in TOPICS)
    # A tool nobody documents is one an agent has to discover by trial.
    undocumented = sorted(
        tool.name for tool in TOOLS
        if tool.name not in corpus and tool.name.removeprefix("hammer5tools.") not in corpus
    )

    assert not undocumented, f"undocumented tools: {', '.join(undocumented)}"
