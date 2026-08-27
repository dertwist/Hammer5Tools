"""The Qt-free rules behind the SmartProp document."""
import sys

sys.path.insert(0, "Hammer5ToolsGUI")

from gui.editors.smartprop_editor.document_model import (
    Variable,
    decode_variable,
    is_category_marker,
    normalize_kv3_text,
    rename_references,
)


def test_normalize_kv3_text_strips_what_exporters_add():
    text = 'a = resource_name:"models/x.vmdl"\nb = null,\n'
    assert normalize_kv3_text(text) == 'a = "models/x.vmdl"\nb = \n'


def test_category_markers_are_recognised_in_both_spellings():
    assert is_category_marker("hammer5tools_category_abc123_start")
    assert is_category_marker("hammer5tools_category_outer_category_inner_end")
    assert not is_category_marker("m_flRadius")
    assert not is_category_marker(None)
    assert not is_category_marker("")


def test_decode_float_variable():
    variable = decode_variable({
        "_class": "CSmartPropVariable_Float",
        "m_VariableName": "radius",
        "m_DisplayName": "Radius",
        "m_bExposeAsParameter": True,
        "m_DefaultValue": 1.5,
        "m_nElementID": 7,
        "m_flParamaterMinValue": 0.0,
        "m_flParamaterMaxValue": 10.0,
        # An Int's range keys must not leak into a Float.
        "m_nParamaterMinValue": 999,
    })
    assert variable.var_class == "Float"
    assert variable.visible_in_editor is True
    assert variable.element_id == 7
    assert variable.value["min"] == 0.0
    assert variable.value["max"] == 10.0
    assert not variable.is_category


def test_decode_leaves_range_empty_for_non_numeric_classes():
    variable = decode_variable({
        "_class": "CSmartPropVariable_Bool",
        "m_VariableName": "enabled",
        "m_nParamaterMinValue": 3,
        "m_flParamaterMaxValue": 4,
    })
    assert variable.value["min"] is None
    assert variable.value["max"] is None


def test_display_name_falls_back_only_when_the_key_is_missing():
    assert decode_variable({"m_sCommentary": "note"}).display_name == "note"
    assert decode_variable({"m_ParameterName": "param"}).display_name == "param"
    # An empty label is a label the user set, not a missing key.
    assert decode_variable({"m_DisplayName": "", "m_sCommentary": "note"}).display_name == ""


def test_category_entry_gets_its_separator_label():
    start = decode_variable({
        "m_VariableName": "hammer5tools_category_props_start",
        "m_Hammer5ToolsCategoryName": "Props",
    })
    assert start.is_category
    assert start.display_name == "---------- Props ----------"

    end = decode_variable({
        "m_VariableName": "hammer5tools_category_props_end",
        "m_Hammer5ToolsCategoryName": "Props",
    })
    assert end.is_category
    assert end.display_name.strip() == ""


def test_category_without_a_name_still_decodes_as_a_category():
    variable = decode_variable({
        "m_VariableName": "hammer5tools_category_props_start",
        "m_DisplayName": "Legacy",
    })
    assert variable.is_category
    assert variable.display_name == "Legacy"


def test_decode_tolerates_a_missing_class():
    assert decode_variable({"m_VariableName": "x"}).var_class == ""


def test_rename_references_only_matches_whole_words():
    data = {
        "expr": "radius * 2 + radius_outer",
        "children": [{"expr": "myradius + radius"}],
        "count": 3,
    }
    renamed = rename_references(data, "radius", "size")
    assert renamed["expr"] == "size * 2 + radius_outer"
    assert renamed["children"][0]["expr"] == "myradius + size"
    assert renamed["count"] == 3
    # The input is not mutated.
    assert data["expr"] == "radius * 2 + radius_outer"


def test_variable_without_an_element_id_reports_none():
    assert Variable(name="x", var_class="Bool", display_name=None,
                    visible_in_editor=False).element_id is None


def test_the_model_does_not_import_qt():
    """The point of the split: document rules must be testable without a GUI."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, 'Hammer5ToolsGUI');"
         " import gui.editors.smartprop_editor.document_model;"
         " print('PySide6' in sys.modules)"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False", "document_model pulled Qt in"


# ── Reading and writing ──────────────────────────────────────────────────

_DOC = {"_class": "CSmartPropRoot", "m_Children": [], "m_Variables": []}


def test_parse_and_format_round_trip():
    from gui.editors.smartprop_editor import document_model

    text = document_model.format_smartprop(_DOC)
    assert document_model.parse_smartprop(text)["_class"] == "CSmartPropRoot"


def test_parse_falls_back_when_the_core_is_unavailable(monkeypatch):
    """The optional .NET Core may fail to initialise; files must still open."""
    from gui.editors.smartprop_editor import document_model

    import core.bridge as bridge
    monkeypatch.setattr(bridge.CoreBridge, "instance",
                        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("no core"))))

    text = ('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} '
            'format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->\n'
            '{\n\t_class = "CSmartPropRoot"\n\tm_Children = [ ]\n}\n')
    assert document_model.parse_smartprop(text)["_class"] == "CSmartPropRoot"
    assert "CSmartPropRoot" in document_model.format_smartprop(_DOC)


def test_parse_accepts_a_headerless_fragment(monkeypatch):
    from gui.editors.smartprop_editor import document_model

    import core.bridge as bridge
    monkeypatch.setattr(bridge.CoreBridge, "instance",
                        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("no core"))))

    assert document_model.parse_smartprop('\n\tm_Children = [ ]\n')["m_Children"] == []


def test_parse_normalises_before_reading(monkeypatch):
    """resource_name: prefixes reach the parser only through normalisation."""
    from gui.editors.smartprop_editor import document_model

    import core.bridge as bridge
    monkeypatch.setattr(bridge.CoreBridge, "instance",
                        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("no core"))))

    parsed = document_model.parse_smartprop('\n\tm_sModelName = resource_name:"models/x.vmdl"\n')
    assert parsed["m_sModelName"] == "models/x.vmdl"
