import pytest
from gui.editors.smartprop_editor._common import (
    CLIPBOARD_PREFIX,
    CLIPBOARD_BATCH_PREFIX,
    parse_component_clipboard,
)
from gui.editors.smartprop_editor.props.model import ComponentRef


def test_user_batch_modifier_clipboard():
    clip_text = (
        "hammer5tools:smartprop_editor_property_batch;;batch;;"
        "[{'_class': 'CSmartPropOperation_Translate', 'm_CoordinateSpace': 'ELEMENT', "
        "'m_bEnabled': True, 'm_nElementID': 54, 'm_vPosition': {'m_Components': [0.0, 0.0, "
        "{'m_Expression': 'LinearScale() * 64'}]}}, {'_class': 'CSmartPropOperation_CreateRotator', "
        "'m_CoordinateSpace': 'ELEMENT', 'm_Name': '', 'm_OutputVariable': '', "
        "'m_bApplyToCurrentTransform': True, 'm_bEnabled': True, 'm_bEnforceLimits': False, "
        "'m_flDisplayRadius': 16.0, 'm_flInitialAngle': 0.0, 'm_flMaxAngle': 0.0, 'm_flMinAngle': 0.0, "
        "'m_flSnappingIncrement': 0.0, 'm_nElementID': 55}];;modifier"
    )

    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "modifier"
    assert len(dicts) == 2
    assert dicts[0]["_class"] == "CSmartPropOperation_Translate"
    assert dicts[0]["m_nElementID"] == 54
    assert dicts[1]["_class"] == "CSmartPropOperation_CreateRotator"
    assert dicts[1]["m_nElementID"] == 55


def test_single_modifier_clipboard():
    mod_dict = {
        "_class": "CSmartPropOperation_Translate",
        "m_CoordinateSpace": "ELEMENT",
        "m_bEnabled": True,
        "m_nElementID": 10,
    }
    clip_text = f"{CLIPBOARD_PREFIX};;CSmartPropOperation_Translate;;{repr(mod_dict)};;modifier"

    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "modifier"
    assert len(dicts) == 1
    assert dicts[0]["_class"] == "CSmartPropOperation_Translate"
    assert dicts[0]["m_nElementID"] == 10


def test_batch_selection_criteria_clipboard():
    crit1 = {
        "_class": "CSmartPropSelectionCriteria_Linear",
        "m_bEnabled": True,
        "m_nElementID": 20,
    }
    crit2 = {
        "_class": "CSmartPropFilter_VariableValue",
        "m_VariableName": "TestVar",
        "m_bEnabled": True,
        "m_nElementID": 21,
    }
    clip_text = f"{CLIPBOARD_BATCH_PREFIX};;batch;;{repr([crit1, crit2])};;selection_criteria"

    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "selection_criteria"
    assert len(dicts) == 2
    assert dicts[0]["_class"] == "CSmartPropSelectionCriteria_Linear"
    assert dicts[1]["_class"] == "CSmartPropFilter_VariableValue"


def test_single_selection_criteria_with_criterion_group():
    crit = {
        "_class": "CSmartPropSelectionCriteria_ChoiceWeight",
        "m_bEnabled": True,
        "m_nElementID": 30,
    }
    clip_text = f"{CLIPBOARD_PREFIX};;CSmartPropSelectionCriteria_ChoiceWeight;;{repr(crit)};;criterion"

    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "selection_criteria"
    assert len(dicts) == 1
    assert dicts[0]["_class"] == "CSmartPropSelectionCriteria_ChoiceWeight"


def test_clipboard_with_embedded_semicolons():
    mod_dict = {
        "_class": "CSmartPropOperation_SetVariable",
        "m_Expression": "func(1;; 2;; 3)",
        "m_Comment": "Testing ;; delimiter in comment",
        "m_bEnabled": True,
    }
    clip_text = f"{CLIPBOARD_PREFIX};;CSmartPropOperation_SetVariable;;{repr(mod_dict)};;modifier"

    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "modifier"
    assert len(dicts) == 1
    assert dicts[0]["m_Expression"] == "func(1;; 2;; 3)"
    assert dicts[0]["m_Comment"] == "Testing ;; delimiter in comment"


def test_invalid_clipboard_texts():
    assert parse_component_clipboard("") == (None, [])
    assert parse_component_clipboard(None) == (None, [])
    assert parse_component_clipboard("random non-clipboard string") == (None, [])
    assert parse_component_clipboard("<!-- kv3 encoding:text:version... -->") == (None, [])
    assert parse_component_clipboard("hammer5tools:smartprop_editor_property;;broken") == (None, [])


def test_component_ref_containers():
    ref_mod = ComponentRef(item=None, kind="modifier", index=0)
    assert ref_mod.container() == "m_Modifiers"

    ref_crit1 = ComponentRef(item=None, kind="criterion", index=0)
    assert ref_crit1.container() == "m_SelectionCriteria"

    ref_crit2 = ComponentRef(item=None, kind="selection_criteria", index=0)
    assert ref_crit2.container() == "m_SelectionCriteria"


def test_batch_append_and_id_assignment():
    from gui.widgets.element_id import ElementIDGenerator
    gen = ElementIDGenerator()

    parent_element = {
        "_class": "CSmartPropElement_Group",
        "m_nElementID": gen.get_element_id({"_class": "CSmartPropElement_Group"}),
        "m_Modifiers": [
            {"_class": "CSmartPropOperation_Rotate", "m_nElementID": gen.get_element_id({})}
        ],
    }

    clip_text = (
        "hammer5tools:smartprop_editor_property_batch;;batch;;"
        "[{'_class': 'CSmartPropOperation_Translate', 'm_nElementID': 999}, "
        "{'_class': 'CSmartPropOperation_CreateRotator', 'm_nElementID': 999}];;modifier"
    )

    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "modifier"

    for d in dicts:
        gen.update_value(d, force=True)
        parent_element["m_Modifiers"].append(d)

    assert len(parent_element["m_Modifiers"]) == 3
    # Check all element IDs are unique
    all_ids = [parent_element["m_nElementID"]] + [m["m_nElementID"] for m in parent_element["m_Modifiers"]]
    assert len(all_ids) == len(set(all_ids))
    assert 999 not in all_ids
