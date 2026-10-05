"""Document rules behind the detail-prop hierarchy tree."""
import sys

sys.path.insert(0, "Hammer5ToolsGUI")

from gui.forms.detail_prop_editor.hierarchy_model import (
    is_model,
    model_label,
    model_summary,
    normalize_dropped,
    unique_name,
)
from gui.forms.detail_prop_editor.schema import default_model


def _model(name):
    entry = default_model()
    entry["m_ModelName"] = name
    return entry


def test_is_model_distinguishes_payloads():
    assert is_model(_model("models/tree.vmdl"))
    assert not is_model({"m_Models": []})


def test_model_label_is_the_basename():
    assert model_label(_model("models/props/tree_01.vmdl")) == "tree_01.vmdl"
    assert model_label(_model("  ")) == "<no model>"
    assert model_label({}) == "<no model>"


def test_model_summary_is_the_full_path():
    assert model_summary(_model("models/props/tree.vmdl")) == "models/props/tree.vmdl"
    assert model_summary({}) == "no model assigned"


def test_unique_name_suffixes_until_free():
    assert unique_name("grass", []) == "grass"
    assert unique_name("grass", ["grass"]) == "grass_2"
    assert unique_name("grass", ["grass", "grass_2", "grass_3"]) == "grass_4"


def test_a_dropped_type_keeps_its_models_in_visual_order():
    rows = [("grass", {"m_flDensity": 2}, [_model("a.vmdl"), _model("b.vmdl")])]
    types = normalize_dropped(rows)
    assert list(types) == ["grass"]
    assert types["grass"]["m_flDensity"] == 2
    assert [m["m_ModelName"] for m in types["grass"]["m_Models"]] == ["a.vmdl", "b.vmdl"]


def test_a_model_dropped_at_top_level_becomes_its_own_type():
    """Qt's InternalMove allows it; the document has no place for it otherwise."""
    dropped = _model("lonely.vmdl")
    types = normalize_dropped([("lonely.vmdl", dropped, [dropped])])
    assert list(types) == ["lonely.vmdl"]
    assert [m["m_ModelName"] for m in types["lonely.vmdl"]["m_Models"]] == ["lonely.vmdl"]


def test_a_type_left_empty_gets_a_default_model():
    types = normalize_dropped([("grass", {}, [])])
    assert len(types["grass"]["m_Models"]) == 1


def test_colliding_names_are_suffixed_not_lost():
    rows = [("grass", {}, [_model("a.vmdl")]), ("grass", {}, [_model("b.vmdl")])]
    types = normalize_dropped(rows)
    assert sorted(types) == ["grass", "grass_2"]
    assert types["grass_2"]["m_Models"][0]["m_ModelName"] == "b.vmdl"


def test_an_unnamed_row_gets_the_default_name():
    types = normalize_dropped([("", {}, [_model("a.vmdl")])])
    assert list(types) == ["detail_type"]


def test_the_model_does_not_import_qt():
    import subprocess

    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, 'Hammer5ToolsGUI');"
         " import gui.forms.detail_prop_editor.hierarchy_model;"
         " print('PySide6' in sys.modules)"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
