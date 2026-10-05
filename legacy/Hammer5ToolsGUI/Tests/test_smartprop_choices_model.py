"""The Qt-free rules behind the SmartProp choices panel."""
import subprocess
import sys

sys.path.insert(0, "Hammer5ToolsGUI")

from gui.editors.smartprop_editor.choices_model import (
    KIND_BOOL,
    KIND_COLOR,
    KIND_FLOAT,
    KIND_INT,
    KIND_STRING,
    KIND_VECTOR3D,
    coerce,
    format_choices,
    parse_choices,
    parse_seq,
    value_kind,
)


def test_variable_class_picks_its_editor():
    assert value_kind("CSmartPropVariable_Float") == KIND_FLOAT
    assert value_kind("Bool") == KIND_BOOL
    assert value_kind(" ANGLES ") == KIND_VECTOR3D
    assert value_kind("materialgroup") == KIND_STRING
    # Anything the editor doesn't know still has to render as something.
    assert value_kind("CSmartPropVariable_Whatever") == KIND_STRING
    assert value_kind(None) == KIND_STRING


def test_coerce_reads_values_however_they_arrive():
    assert coerce(KIND_INT, "3.7") == 3
    assert coerce(KIND_INT, "nonsense") == 0
    assert coerce(KIND_FLOAT, None) == 0.0
    assert coerce(KIND_BOOL, "True") is True
    assert coerce(KIND_BOOL, "no") is False
    assert coerce(KIND_STRING, 12) == "12"


def test_coerce_pads_and_clamps_sequences():
    assert coerce(KIND_VECTOR3D, "[1, 2]") == [1.0, 2.0, 1.0]
    assert coerce(KIND_VECTOR3D, None) == [1.0, 1.0, 1.0]
    assert coerce(KIND_COLOR, [300, -5, "40"]) == [255, 0, 40]


def test_parse_seq_truncates_and_falls_back():
    assert parse_seq([1, 2, 3, 4], [0, 0], 2) == [1, 2]
    assert parse_seq("not a list", [0, 0], 2) == [0, 0]
    assert parse_seq("(9, 8)", [0, 0], 2) == [9, 8]


def test_parse_choices_accepts_every_key_spelling():
    state = parse_choices([{
        "m_sChoiceName": "Skin",
        "m_DefaultOption": "red",
        "m_Options": [{
            "m_sOptionName": "red",
            "m_VariableValues": [{
                "m_sVariableName": "tint",
                "m_sDataType": "Color",
                "m_Value": [255, 0, 0],
            }],
        }],
    }])
    assert state == [{
        'name': "Skin",
        'default': "red",
        'expanded': False,
        'options': [{
            'name': "red",
            'expanded': False,
            'variables': [{'name': "tint", 'type': "Color", 'value': [255, 0, 0]}],
        }],
    }]


def test_parse_choices_names_what_the_file_left_unnamed():
    state = parse_choices([{"m_Options": [{"m_VariableValues": [{}]}]}])
    assert state[0]['name'] == "Choice"
    assert state[0]['default'] == ""
    assert state[0]['options'][0]['name'] == "Option"
    assert state[0]['options'][0]['variables'][0] == {'name': "", 'type': "", 'value': ""}


def test_format_choices_round_trips_what_parse_read():
    original = [{
        "_class": "CSmartPropChoice",
        "m_Name": "Skin",
        "m_Options": [{
            "_class": "CSmartPropChoiceOption",
            "m_Name": "red",
            "m_VariableValues": [
                {"m_TargetName": "tint", "m_DataType": "Color", "m_Value": [255, 0, 0]},
            ],
        }],
        "m_DefaultOption": "red",
    }]
    assert format_choices(parse_choices(original)) == original


def test_format_choices_fills_in_the_writer_defaults():
    written = format_choices([{
        'name': "Skin",
        'default': "None",
        'options': [{'name': "red", 'variables': [{'name': "tint", 'value': 1}]}],
    }])
    # "None" is the empty selection in the combo box, not an option name.
    assert written[0]["m_DefaultOption"] == ""
    assert written[0]["m_Options"][0]["m_VariableValues"][0]["m_DataType"] == "String"


def test_model_stays_free_of_qt():
    check = (
        "import sys; sys.path.insert(0, 'Hammer5ToolsGUI');"
        "import gui.editors.smartprop_editor.choices_model;"
        "assert 'PySide6' not in sys.modules"
    )
    assert subprocess.run([sys.executable, "-c", check]).returncode == 0
