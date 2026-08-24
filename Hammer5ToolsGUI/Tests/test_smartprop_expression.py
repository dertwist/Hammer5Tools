import math

import pytest

from hammer5tools_gui.editors.smartprop_editor.viewport_3d.engine.context import EvalContext
from hammer5tools_gui.editors.smartprop_editor.viewport_3d.engine.expression import evaluate_expression


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1 + 2 * 3", 7.0),
        ("(2 < 1) ? 8 : 4", 4.0),
        ("!false && true", 1.0),
        ("Clamp(10, 2, 6)", 6.0),
        ("Deg2Rad(180)", math.pi),
        ("1 / 0", 0.0),
    ],
)
def test_expression_characterization(expression, expected):
    assert evaluate_expression(expression) == pytest.approx(expected)


def test_expression_context_characterization():
    context = EvalContext(
        variables={"Block_Type": 1.0, "Tint": [1.0, 2.0, 3.0, 4.0]},
        instance_index=2,
        instance_count=5,
        linear_scale=1.5,
    )

    assert evaluate_expression("block_type == 1 ? tint.b + InstanceIndex() : 0", context) == 5.0
    assert evaluate_expression("LinearScale()", context) == 1.5


def test_expression_malformed_input_characterization():
    assert evaluate_expression("1 + )", default=9.0) == 9.0
