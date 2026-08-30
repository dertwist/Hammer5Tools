import pytest
import subprocess
import sys
from gui.common import JsonToKv3
from gui.editors.smartprop_editor._common import (
    CLIPBOARD_PREFIX,
    CLIPBOARD_BATCH_PREFIX,
    CLIPBOARD_FIELD_PREFIX,
    classify_smartprop_class,
    classify_smartprop_dict,
    parse_component_clipboard,
    parse_property_clipboard,
)
from gui.editors.smartprop_editor.props.model import ComponentRef


def test_classify_smartprop_class():
    assert classify_smartprop_class("CSmartPropOperation_Translate") == "modifier"
    assert classify_smartprop_class("CSmartPropOperation_Rotate") == "modifier"
    assert classify_smartprop_class("CSmartPropFilter_VariableValue") == "modifier"
    assert classify_smartprop_class("CSmartPropFilter_Expression") == "modifier"
    assert classify_smartprop_class("CSmartPropModifier_Rotate") == "modifier"
    assert classify_smartprop_class("CSmartPropSelectionCriteria_LinearLength") == "selection_criteria"
    assert classify_smartprop_class("CSmartPropElement_Group") == "element"
    assert classify_smartprop_class("CSmartPropElement_Model") == "element"
    assert classify_smartprop_class("CSmartPropVariable_Float") == "variable"
    assert classify_smartprop_class("CSmartPropChoice") == "choice"
    assert classify_smartprop_class("UnknownClass") is None
    assert classify_smartprop_class("") is None
    assert classify_smartprop_class(None) is None


def test_classify_smartprop_dict():
    assert classify_smartprop_dict({"_class": "CSmartPropOperation_Translate"}) == "modifier"
    assert classify_smartprop_dict({"_class": "CSmartPropFilter_Probability"}) == "modifier"
    assert classify_smartprop_dict({"_class": "CSmartPropSelectionCriteria_EndCap"}) == "selection_criteria"
    assert classify_smartprop_dict({"_class": "CSmartPropElement_SmartProp"}) == "element"
    assert classify_smartprop_dict({"_class": "CSmartPropVariable_Int"}) == "variable"
    assert classify_smartprop_dict({}) is None
    assert classify_smartprop_dict(None) is None


def test_kv3_single_modifier_clipboard():
    mod_dict = {
        "_class": "CSmartPropOperation_Translate",
        "m_CoordinateSpace": "ELEMENT",
        "m_bEnabled": True,
        "m_nElementID": 10,
    }
    clip_text = JsonToKv3({"m_Modifiers": [mod_dict]})
    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "modifier"
    assert len(dicts) == 1
    assert dicts[0]["_class"] == "CSmartPropOperation_Translate"
    assert dicts[0]["m_nElementID"] == 10


def test_kv3_filter_modifier_clipboard():
    clip_text = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
	m_Modifiers = 
	[
		{
			_class = "CSmartPropFilter_Expression"
			m_Expression = "(sizer_x == 128) ? true : false"
			m_bEnabled = true
			m_nElementID = 13
		}
	]
}"""
    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "modifier"
    assert len(dicts) == 1
    assert dicts[0]["_class"] == "CSmartPropFilter_Expression"
    assert dicts[0]["m_Expression"] == "(sizer_x == 128) ? true : false"
    assert dicts[0]["m_nElementID"] == 13


def test_kv3_batch_modifier_clipboard():
    mod1 = {
        "_class": "CSmartPropOperation_Translate",
        "m_CoordinateSpace": "ELEMENT",
        "m_bEnabled": True,
        "m_nElementID": 54,
    }
    mod2 = {
        "_class": "CSmartPropOperation_CreateRotator",
        "m_CoordinateSpace": "ELEMENT",
        "m_bApplyToCurrentTransform": True,
        "m_bEnabled": True,
        "m_nElementID": 55,
    }
    clip_text = JsonToKv3({"m_Modifiers": [mod1, mod2]})
    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "modifier"
    assert len(dicts) == 2
    assert dicts[0]["_class"] == "CSmartPropOperation_Translate"
    assert dicts[1]["_class"] == "CSmartPropOperation_CreateRotator"


def test_kv3_single_selection_criteria_clipboard():
    crit = {
        "_class": "CSmartPropSelectionCriteria_ChoiceWeight",
        "m_bEnabled": True,
        "m_nElementID": 30,
    }
    clip_text = JsonToKv3({"m_SelectionCriteria": [crit]})
    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "selection_criteria"
    assert len(dicts) == 1
    assert dicts[0]["_class"] == "CSmartPropSelectionCriteria_ChoiceWeight"


def test_kv3_batch_selection_criteria_clipboard():
    crit1 = {
        "_class": "CSmartPropSelectionCriteria_LinearLength",
        "m_bEnabled": True,
        "m_nElementID": 20,
    }
    crit2 = {
        "_class": "CSmartPropSelectionCriteria_EndCap",
        "m_bStart": True,
        "m_bEnabled": True,
        "m_nElementID": 21,
    }
    clip_text = JsonToKv3({"m_SelectionCriteria": [crit1, crit2]})
    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "selection_criteria"
    assert len(dicts) == 2
    assert dicts[0]["_class"] == "CSmartPropSelectionCriteria_LinearLength"
    assert dicts[1]["_class"] == "CSmartPropSelectionCriteria_EndCap"


def test_kv3_bare_component_object_clipboard():
    mod_dict = {
        "_class": "CSmartPropOperation_Rotate",
        "m_bEnabled": True,
        "m_nElementID": 101,
    }
    clip_text = JsonToKv3(mod_dict)
    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "modifier"
    assert len(dicts) == 1
    assert dicts[0]["_class"] == "CSmartPropOperation_Rotate"


def test_kv3_hierarchy_element_clipboard():
    elem_dict = {
        "_class": "CSmartPropElement_Group",
        "m_bEnabled": True,
        "m_nElementID": 42,
    }
    clip_text = JsonToKv3({"m_Children": [elem_dict]})
    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "element"
    assert len(dicts) == 1
    assert dicts[0]["_class"] == "CSmartPropElement_Group"


def test_user_batch_modifier_legacy_clipboard():
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


def test_single_modifier_legacy_clipboard():
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


def test_batch_selection_criteria_legacy_clipboard():
    crit1 = {
        "_class": "CSmartPropSelectionCriteria_LinearLength",
        "m_bEnabled": True,
        "m_nElementID": 20,
    }
    crit2 = {
        "_class": "CSmartPropSelectionCriteria_EndCap",
        "m_bStart": True,
        "m_bEnabled": True,
        "m_nElementID": 21,
    }
    clip_text = f"{CLIPBOARD_BATCH_PREFIX};;batch;;{repr([crit1, crit2])};;selection_criteria"

    group_type, dicts = parse_component_clipboard(clip_text)
    assert group_type == "selection_criteria"
    assert len(dicts) == 2
    assert dicts[0]["_class"] == "CSmartPropSelectionCriteria_LinearLength"
    assert dicts[1]["_class"] == "CSmartPropSelectionCriteria_EndCap"


def test_invalid_clipboard_texts():
    assert parse_component_clipboard("") == (None, [])
    assert parse_component_clipboard(None) == (None, [])
    assert parse_component_clipboard("random non-clipboard string") == (None, [])
    assert parse_component_clipboard("<!-- kv3 encoding:text:version... -->\n{\nunknown_key = 123\n}") == (None, [])
    assert parse_component_clipboard("hammer5tools:smartprop_editor_property;;broken") == (None, [])


def test_component_ref_containers():
    ref_mod = ComponentRef(item=None, kind="modifier", index=0)
    assert ref_mod.container() == "m_Modifiers"

    ref_crit1 = ComponentRef(item=None, kind="criterion", index=0)
    assert ref_crit1.container() == "m_SelectionCriteria"

    ref_crit2 = ComponentRef(item=None, kind="selection_criteria", index=0)
    assert ref_crit2.container() == "m_SelectionCriteria"


def test_component_model_does_not_import_qt():
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, 'Hammer5ToolsGUI');"
         " import gui.editors.smartprop_editor.props.model;"
         " print('PySide6' in sys.modules)"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


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

    clip_text = JsonToKv3({
        "m_Modifiers": [
            {"_class": "CSmartPropOperation_Translate", "m_nElementID": 999},
            {"_class": "CSmartPropOperation_CreateRotator", "m_nElementID": 999}
        ]
    })

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


def test_property_clipboard_kv3_vector():
    val = {"m_Components": [{"m_Expression": "sizer_x"}, 0.0, 0.0]}
    clip_text = JsonToKv3({"m_vEnd": val})
    ok, payload = parse_property_clipboard(clip_text, target_value_class="m_vEnd")
    assert ok is True
    assert payload == val


def test_property_clipboard_kv3_cross_paste():
    # Copy m_vEnd, paste into m_vStart
    val = {"m_Components": [{"m_Expression": "sizer_x"}, 0.0, 0.0]}
    clip_text = JsonToKv3({"m_vEnd": val})
    ok, payload = parse_property_clipboard(clip_text, target_value_class="m_vStart")
    assert ok is True
    assert payload == val


def test_property_clipboard_kv3_float_and_bool():
    clip_text = JsonToKv3({"m_flScale": 2.5})
    ok, payload = parse_property_clipboard(clip_text, target_value_class="m_flScale")
    assert ok is True
    assert payload == 2.5

    clip_text = JsonToKv3({"m_bEnabled": True})
    ok, payload = parse_property_clipboard(clip_text, target_value_class="m_bEnabled")
    assert ok is True
    assert payload is True


def test_property_clipboard_legacy_fallback():
    val = {"m_Components": [{"m_Expression": "sizer_x"}, 0.0, 0.0]}
    clip_text = f"{CLIPBOARD_FIELD_PREFIX};;m_vEnd;;{repr(val)}"
    ok, payload = parse_property_clipboard(clip_text, target_value_class="m_vEnd")
    assert ok is True
    assert payload == val


def test_property_clipboard_rejects_components_and_containers():
    # Elements or containers shouldn't accidentally parse as single property
    elem_clip = JsonToKv3({"_class": "CSmartPropElement_Group", "m_Children": []})
    ok, _ = parse_property_clipboard(elem_clip)
    assert ok is False

    batch_clip = JsonToKv3({"m_Modifiers": [{"_class": "CSmartPropOperation_Translate"}]})
    ok, _ = parse_property_clipboard(batch_clip)
    assert ok is False

    assert parse_property_clipboard("") == (False, None)
    assert parse_property_clipboard(None) == (False, None)

