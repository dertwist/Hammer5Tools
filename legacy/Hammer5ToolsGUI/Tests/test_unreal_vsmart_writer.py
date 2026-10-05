"""Conditional components become IsValid selection criteria, the only
expression-based criteria CS2's smartprops schema has."""

import keyvalues3 as kv3

from gui.forms.unreal_porter.vsmart_writer import write_vsmart


def _write(tmp_path, components, choices=None):
    out = tmp_path / "bp.vsmart"
    write_vsmart("BP_Test", components, str(out), model_resolver=lambda m: m, choices=choices)
    return kv3.read(str(out)).value["m_Children"][0]["m_Children"]


def _criteria(tmp_path, component, choices=None):
    return _write(tmp_path, [{"name": "A", "mesh": "a.vmdl", **component}], choices)[0]["m_SelectionCriteria"]


def test_choice_condition_compares_the_option_value(tmp_path):
    choices = [{"name": "Style", "options": [{"name": "Broken", "value": 2}]}]
    crit = _criteria(tmp_path, {"choice_name": "Style", "choice_value": "Broken"}, choices)
    assert crit == [{"_class": "CSmartPropSelectionCriteria_IsValid", "m_Expression": "Style == 2"}]


def test_expression_and_variable_conditions_use_is_valid(tmp_path):
    assert _criteria(tmp_path, {"expression": "Size > 3"}) == [
        {"_class": "CSmartPropSelectionCriteria_IsValid", "m_Expression": "Size > 3"}]
    assert _criteria(tmp_path, {"variable_condition": {"variable": "Lit", "value": 1}}) == [
        {"_class": "CSmartPropSelectionCriteria_IsValid", "m_Expression": "Lit == 1"}]


def test_unconditional_component_has_no_criteria(tmp_path):
    assert _criteria(tmp_path, {}) == []


def test_variants_on_one_variable_are_grouped_into_pick_one(tmp_path):
    children = _write(tmp_path, [
        {"name": "A", "mesh": "a.vmdl", "variable_condition": {"variable": "Kind", "value": 0}},
        {"name": "B", "mesh": "b.vmdl", "variable_condition": {"variable": "Kind", "value": 1}},
    ])
    assert [c["_class"] for c in children] == ["CSmartPropElement_PickOne"]
    assert children[0]["m_SpecificChildIndex"] == {"m_SourceName": "Kind"}
