"""
Unit tests for verifying that variable categories are hidden from variable selectors,
completion utilities, and expression editors in SmartProp Editor.
"""

import os
import sys
import pytest
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Ensure QApplication exists for Qt widget tests
app = QApplication.instance() or QApplication(sys.argv)

from src.editors.smartprop_editor._common import is_category_variable_name, is_category_widget
from src.editors.smartprop_editor.widgets.main import ComboboxVariables, ComboboxVariablesWidget
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.widgets.element_id import ElementIDGenerator


class MockVariableWidget(QWidget):
    def __init__(self, name, var_class, default=None):
        super().__init__()
        self.name = name
        self.var_class = var_class
        self.var_value = {'default': default}


class MockCategoryWidget(QWidget):
    def __init__(self, name, is_start=True):
        super().__init__()
        self.name = name
        self.var_class = 'Bool'
        self.var_value = {'default': None}
        self.is_start = is_start
        self.is_end = not is_start


def test_is_category_variable_name():
    """Verify regex and prefix matching for category variable names."""
    # Category variable names
    assert is_category_variable_name("hammer5tools_category_abc123_start") is True
    assert is_category_variable_name("hammer5tools_category_abc123_end") is True
    assert is_category_variable_name("hammer5tools_category_group_category_xyz789_start") is True
    assert is_category_variable_name("hammer5tools_category_group_category_xyz789_end") is True
    assert is_category_variable_name("hammer5tools_category_test") is True

    # Regular variable names
    assert is_category_variable_name("my_bool_var") is False
    assert is_category_variable_name("category_name") is False
    assert is_category_variable_name("m_bEnabled") is False
    assert is_category_variable_name("") is False
    assert is_category_variable_name(None) is False


def test_is_category_widget():
    """Verify is_category_widget detects category frames and ignores regular variable frames."""
    regular_var = MockVariableWidget("prop_scale", "Float", 1.0)
    category_start = MockCategoryWidget("hammer5tools_category_a1b2_start", is_start=True)
    category_end = MockCategoryWidget("hammer5tools_category_a1b2_end", is_start=False)

    assert is_category_widget(regular_var) is False
    assert is_category_widget(category_start) is True
    assert is_category_widget(category_end) is True
    assert is_category_widget(None) is False


def test_combobox_variables_filters_categories():
    """Verify that ComboboxVariables.get_variables() excludes category markers."""
    container = QWidget()
    layout = QVBoxLayout(container)

    # Add a normal variable, a category start, a categorized variable, a category end, and another normal variable
    var1 = MockVariableWidget("radius", "Float", 10.0)
    cat_start = MockCategoryWidget("hammer5tools_category_f4a1_start", is_start=True)
    var2 = MockVariableWidget("enable_lighting", "Bool", True)
    cat_end = MockCategoryWidget("hammer5tools_category_f4a1_end", is_start=False)
    var3 = MockVariableWidget("model_path", "String", "models/test.vmdl")

    layout.addWidget(var1)
    layout.addWidget(cat_start)
    layout.addWidget(var2)
    layout.addWidget(cat_end)
    layout.addWidget(var3)

    combobox = ComboboxVariables(layout=layout)
    variables = combobox.get_variables()

    var_names = [v['name'] for v in variables]
    assert "radius" in var_names
    assert "enable_lighting" in var_names
    assert "model_path" in var_names
    assert "hammer5tools_category_f4a1_start" not in var_names
    assert "hammer5tools_category_f4a1_end" not in var_names
    assert len(variables) == 3

    # Test updateItems
    combobox.updateItems()
    items = [combobox.itemText(i) for i in range(combobox.count())]
    assert items == ["None", "radius", "enable_lighting", "model_path"]


def test_completion_utils_filters_categories():
    """Verify CompletionUtils ignores category markers."""
    container = QWidget()
    layout = QVBoxLayout(container)

    var1 = MockVariableWidget("scale", "Float", 1.0)
    cat_start = MockCategoryWidget("hammer5tools_category_123_start", is_start=True)
    var2 = MockVariableWidget("is_active", "Bool", False)
    cat_end = MockCategoryWidget("hammer5tools_category_123_end", is_start=False)

    layout.addWidget(var1)
    layout.addWidget(cat_start)
    layout.addWidget(var2)
    layout.addWidget(cat_end)

    CompletionUtils.invalidate_cache(layout)
    var_list = CompletionUtils.get_available_variables_with_types(layout)
    names = CompletionUtils.get_available_variable_names(layout)

    assert names == ["scale", "is_active"]
    assert len(var_list) == 2
    assert var_list[0] == {'name': 'scale', 'type': 'Float'}
    assert var_list[1] == {'name': 'is_active', 'type': 'Bool'}


def test_combobox_variables_widget_get_all_variables_filters_categories():
    """Verify ComboboxVariablesWidget.get_all_variables() ignores category items."""
    container = QWidget()
    layout = QVBoxLayout(container)

    var1 = MockVariableWidget("speed", "Float", 100.0)
    cat_start = MockCategoryWidget("hammer5tools_category_999_start", is_start=True)
    cat_end = MockCategoryWidget("hammer5tools_category_999_end", is_start=False)

    layout.addWidget(var1)
    layout.addWidget(cat_start)
    layout.addWidget(cat_end)

    elem_gen = ElementIDGenerator()
    widget = ComboboxVariablesWidget(
        element_id_generator=elem_gen,
        variables_layout=layout,
        filter_types=['Float'],
        variable_name="speed"
    )

    all_vars = widget.get_all_variables()
    assert all_vars == ["speed"]

    # Verify search popup elements also exclude categories
    popup_elements = widget.get_variables()
    assert popup_elements == [{"speed": "speed"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
