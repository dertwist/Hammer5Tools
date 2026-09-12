"""Tests for targeted .vsmart patching and the static checks it runs on write."""

from __future__ import annotations

import pytest

from automation.formats.vsmart_io import read_vsmart, read_vsmart_full, write_vsmart
from automation.formats.vsmart_lint import lint_document, lint_vsmart
from automation.formats.vsmart_patch import patch_vsmart, reindex_element_ids


def _document(tmp_path) -> str:
    path = str(tmp_path / "patch.vsmart")
    write_vsmart(
        path,
        variables=[
            {"_class": "CSmartPropVariable_Float", "m_VariableName": "Length", "m_DefaultValue": 128.0},
            {"_class": "CSmartPropVariable_Float", "m_VariableName": "Height", "m_DefaultValue": 64.0},
            {"_class": "CSmartPropVariable_Bool", "m_VariableName": "EditInViewport", "m_DefaultValue": False},
        ],
        children=[{"_class": "CSmartPropElement_Model", "m_sModelName": "models/a.vmdl"}],
    )
    return path


def test_set_changes_one_field_and_leaves_the_rest(tmp_path):
    path = _document(tmp_path)

    result = patch_vsmart(path, [
        {"op": "set", "target": "m_Variables[m_VariableName=Length].m_DefaultValue", "value": 256.0},
    ])

    assert result["applied"] == ["set:m_Variables[m_VariableName=Length].m_DefaultValue"]
    payload = read_vsmart(path)
    by_name = {item["name"]: item for item in payload["variables"]}
    assert by_name["Length"]["default"] == 256.0
    assert by_name["Height"]["default"] == 64.0


def test_dry_run_leaves_the_file_untouched(tmp_path):
    path = _document(tmp_path)
    before = open(path, encoding="utf-8").read()

    patch_vsmart(path, [
        {"op": "set", "target": "m_Variables[m_VariableName=Length].m_DefaultValue", "value": 999.0},
    ], dry_run=True)

    assert open(path, encoding="utf-8").read() == before


def test_add_variable_inserts_after_a_named_variable(tmp_path):
    path = _document(tmp_path)

    patch_vsmart(path, [{
        "op": "add_variable",
        "after": "Length",
        "variable": {
            "_class": "CSmartPropVariable_Float",
            "m_VariableName": "Spacing",
            "m_HideExpression": "!EditInViewport",
        },
    }])

    names = [item["name"] for item in read_vsmart(path)["variables"]]
    assert names[:3] == ["Length", "Spacing", "Height"]


def test_add_variable_fills_a_default_of_the_right_type(tmp_path):
    path = _document(tmp_path)

    patch_vsmart(path, [{
        "op": "add_variable",
        "variable": {"_class": "CSmartPropVariable_Vector3D", "m_VariableName": "Pivot"},
    }])

    selected = read_vsmart(path, select="m_Variables[m_VariableName=Pivot].m_DefaultValue")
    assert selected["value"] == [0.0, 0.0, 0.0]


def test_add_variable_refuses_a_duplicate_name(tmp_path):
    path = _document(tmp_path)

    with pytest.raises(ValueError, match="already exists"):
        patch_vsmart(path, [{
            "op": "add_variable",
            "variable": {"_class": "CSmartPropVariable_Float", "m_VariableName": "Length"},
        }])


def test_add_category_writes_a_matched_marker_pair(tmp_path):
    path = _document(tmp_path)

    patch_vsmart(path, [{"op": "add_category", "name": "Sizing", "contains": ["Length", "Height"]}])

    names = [item["name"] for item in read_vsmart(path)["variables"]]
    assert "hammer5tools_category_sizing_start" in names
    assert "hammer5tools_category_sizing_end" in names
    assert names.index("hammer5tools_category_sizing_start") < names.index("Length")
    assert names.index("Height") < names.index("hammer5tools_category_sizing_end")
    assert lint_vsmart(path)["clean"] is True


def test_remove_deletes_the_addressed_node(tmp_path):
    path = _document(tmp_path)

    patch_vsmart(path, [{"op": "remove", "target": "m_Variables[m_VariableName=Height]"}])

    assert "Height" not in [item["name"] for item in read_vsmart(path)["variables"]]


def test_unknown_target_names_the_expression(tmp_path):
    path = _document(tmp_path)

    with pytest.raises(ValueError, match="Nope"):
        patch_vsmart(path, [{"op": "set", "target": "m_Variables[m_VariableName=Nope].m_DefaultValue", "value": 1.0}])


def test_element_ids_are_unique_after_a_patch(tmp_path):
    path = _document(tmp_path)
    root = read_vsmart_full(path)["raw"]
    root["m_Children"] = [
        {"_class": "CSmartPropElement_Model", "editor_info": {"m_nElementID": 81}},
        {"_class": "CSmartPropElement_Model", "editor_info": {"m_nElementID": 81}},
        {"_class": "CSmartPropElement_Model", "editor_info": {"m_nElementID": 81}},
    ]
    # Four nodes carry an ID, but the three children collide on 81.
    assert len(_check_ids(root)) == 2

    # Only the two colliding duplicates move; IDs seed random placement, so a
    # node whose ID is already unique keeps it.
    assert reindex_element_ids(root) == 2

    assert len(_check_ids(root)) == 4
    assert 81 in _check_ids(root)


def _check_ids(root) -> set:
    found = set()

    def walk(node):
        if isinstance(node, dict):
            info = node.get("editor_info")
            if isinstance(info, dict) and "m_nElementID" in info:
                found.add(info["m_nElementID"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(root)
    return found


_BROKEN = {
    "_class": "CSmartPropElement_Group",
    "editor_info": {"m_nElementID": 81},
    "m_Variables": [
        {"_class": "CSmartPropVariable_Float", "m_VariableName": "RingSizeTop", "m_DefaultValue": ""},
        {"_class": "CSmartPropVariable_Vector3D", "m_VariableName": "Pivot", "m_DefaultValue": ""},
        {
            "_class": "CSmartPropVariable_Bool",
            "m_VariableName": "hammer5tools_category_sizing_start",
            "m_DefaultValue": "",
            "m_ReadOnlyExpression": "true",
        },
    ],
    "m_Children": [
        {
            "_class": "CSmartPropElement_Model",
            "editor_info": {"m_nElementID": 81},
            "m_Expression": "atan(RingSizeTop / (Floor(CylinderHeight / StepV) * StepV))",
        },
        {
            "_class": "CSmartPropElement_Model",
            "editor_info": {"m_nElementID": 81},
            "m_vModelScale": "LinearScale()",
            "m_SelectionCriteria": [{"_class": "CSmartPropSelectionCriteria_EndCap", "m_bEnd": True}],
            "m_HideExpression": "UndeclaredName == 0",
        },
        {"_class": "CSmartPropElement_Model", "m_vOffset": {"m_Expression": ""}},
    ],
}


@pytest.mark.parametrize("check", [
    "unguarded-division",
    "unguarded-trig",
    "untyped-default",
    "empty-expression",
    "duplicate-element-id",
    "endcap-linear-scale",
    "unpaired-category",
    "unknown-variable",
])
def test_lint_reports_every_known_failure_mode(check):
    reported = {finding["check"] for finding in lint_document(_BROKEN)}

    assert check in reported


def test_lint_is_quiet_on_a_clean_document(tmp_path):
    assert lint_vsmart(_document(tmp_path))["findings"] == []


def test_lint_audits_a_whole_directory(tmp_path):
    _document(tmp_path)
    broken = tmp_path / "broken.vsmart"
    write_vsmart(str(broken), variables=[
        {"_class": "CSmartPropVariable_Float", "m_VariableName": "Bad", "m_DefaultValue": ""},
    ])
    # write_vsmart fills typed defaults, so break it after the fact.
    broken.write_text(broken.read_text(encoding="utf-8").replace("0.0", '""'), encoding="utf-8")

    report = lint_vsmart(str(tmp_path))

    assert report["files_checked"] == 2
    assert report["files_with_findings"] == 1
    assert report["counts_by_check"]["untyped-default"] >= 1
