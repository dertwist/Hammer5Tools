"""Variable serialization rules, lifted out of the widget-walking serializer.

`variable_rows_to_kv3` used to live inside `VsmartSave.save_variables`, which
read the variable widgets straight off a QLayout. It is now pure data in, data
out, so the per-class defaults and category handling are testable without Qt.
"""

import pytest

from gui.editors.smartprop_editor.document_model import variable_rows_to_kv3


def row(name="var", var_class="Float", default=None, visible=True, display="", **value):
    payload = {"default": default, "min": None, "max": None, "model": None,
               "m_nElementID": 1, "m_HideExpression": None}
    payload.update(value)
    return [name, var_class, payload, visible, display]


def test_class_prefix_and_core_fields():
    out = variable_rows_to_kv3({0: row(name="size", var_class="Float", default=2.5)})
    assert out == [{
        "_class": "CSmartPropVariable_Float",
        "m_VariableName": "size",
        "m_bExposeAsParameter": True,
        "m_DefaultValue": 2.5,
        "m_nElementID": 1,
    }]


@pytest.mark.parametrize("var_class,expected", [
    ("Color", [255, 255, 255]), ("Bool", False), ("Vector3D", [1, 1, 1]),
    ("Vector2D", [0, 0]), ("Vector4D", [0, 0, 0, 0]), ("Int", 0),
    ("Float", 0.0), ("String", ""),
])
def test_missing_default_falls_back_per_class(var_class, expected):
    out = variable_rows_to_kv3({0: row(var_class=var_class, default=None)})
    assert out[0]["m_DefaultValue"] == expected


def test_per_class_default_is_not_shared_between_rows():
    """A mutable fallback must not be aliased across variables."""
    out = variable_rows_to_kv3({0: row(var_class="Color"), 1: row(var_class="Color")})
    out[0]["m_DefaultValue"].append(0)
    assert out[1]["m_DefaultValue"] == [255, 255, 255]


@pytest.mark.parametrize("bad", ["", 5, [1, 2]])
def test_malformed_colour_default_is_repaired(bad):
    out = variable_rows_to_kv3({0: row(var_class="Color", default=bad)})
    assert out[0]["m_DefaultValue"] == [255, 255, 255]


def test_display_name_omitted_when_blank():
    assert "m_DisplayName" not in variable_rows_to_kv3({0: row(display="")})[0]
    assert "m_DisplayName" not in variable_rows_to_kv3({0: row(display=None)})[0]
    assert variable_rows_to_kv3({0: row(display="Size")})[0]["m_DisplayName"] == "Size"


def test_min_max_keys_are_class_specific():
    out = variable_rows_to_kv3({0: row(var_class="Float", min=1.0, max=9.0)})[0]
    assert out["m_flParamaterMinValue"] == 1.0 and out["m_flParamaterMaxValue"] == 9.0

    out = variable_rows_to_kv3({0: row(var_class="Int", min=1, max=9)})[0]
    assert out["m_nParamaterMinValue"] == 1 and out["m_nParamaterMaxValue"] == 9

    # Bounds are meaningless on other classes and must not be written.
    out = variable_rows_to_kv3({0: row(var_class="String", min=1, max=9)})[0]
    assert not [k for k in out if "Paramater" in k]


def test_optional_keys_only_appear_when_set():
    out = variable_rows_to_kv3({0: row()})[0]
    for key in ("m_sModelName", "m_HideExpression", "m_ReadOnlyExpression"):
        assert key not in out

    out = variable_rows_to_kv3({0: row(model="a.vmdl", m_HideExpression="x > 1",
                                       m_ReadOnlyExpression="y")})[0]
    assert out["m_sModelName"] == "a.vmdl"
    assert out["m_HideExpression"] == "x > 1"
    assert out["m_ReadOnlyExpression"] == "y"


def test_category_start_takes_its_name_from_the_display_label():
    out = variable_rows_to_kv3({0: row(name="hammer5tools_category_abc_start",
                                       display="---------- Shape ----------")})[0]
    assert out["m_Hammer5ToolsCategoryName"] == "Shape"


def test_category_start_without_a_label_gets_a_placeholder():
    out = variable_rows_to_kv3({0: row(name="hammer5tools_category_abc_start", display="x")})[0]
    assert out["m_Hammer5ToolsCategoryName"] == "Category name"


def test_category_end_is_marked_but_unnamed():
    out = variable_rows_to_kv3({0: row(name="hammer5tools_category_abc_end")})[0]
    assert out["m_Hammer5ToolsCategoryName"] == "New category"


def test_plain_variable_is_not_treated_as_a_category():
    assert "m_Hammer5ToolsCategoryName" not in variable_rows_to_kv3({0: row(name="size")})[0]


def test_rows_are_emitted_in_layout_order_not_dict_order():
    rows = {2: row(name="third"), 0: row(name="first"), 1: row(name="second")}
    names = [v["m_VariableName"] for v in variable_rows_to_kv3(rows)]
    assert names == ["first", "second", "third"]


class _Widget:
    def __init__(self, name):
        self.name = name
        self.var_class = "Float"
        self.var_value = {"default": 1.0}
        self.var_visible_in_editor = True
        self.var_display_name = "D"


class _Layout:
    """Duck-typed stand-in: read_variable_rows only calls count/itemAt/widget."""

    def __init__(self, widgets):
        self._widgets = widgets

    def count(self):
        return len(self._widgets)

    def itemAt(self, index):
        widget = self._widgets[index]
        return None if widget is None else type("Item", (), {"widget": lambda s, w=widget: w})()


def test_reader_skips_spacers_and_missing_items():
    from gui.editors.smartprop_editor._common import read_variable_rows

    rows = read_variable_rows(_Layout([_Widget("a"), None, _Widget("b")]))
    assert [r[0] for r in rows.values()] == ["a", "b"]
    # Indices stay the layout's, so callers can map a row back to its position.
    assert sorted(rows) == [0, 2]


def test_reader_returns_empty_for_no_layout():
    from gui.editors.smartprop_editor._common import read_variable_rows

    assert read_variable_rows(None) == {}


def test_reader_only_names_returns_the_short_form():
    from gui.editors.smartprop_editor._common import read_variable_rows

    rows = read_variable_rows(_Layout([_Widget("a")]), only_names=True)
    assert rows == {0: ["a", "Float", "D"]}
