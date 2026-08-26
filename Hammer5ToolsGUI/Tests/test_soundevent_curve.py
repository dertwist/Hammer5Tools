import pytest
from gui.editors.soundevent_editor.property.curve.algorithm import (
    CurvePoint,
    setup_all_curve_values,
    sample_curve,
)


def copy_curve_point(point):
    return CurvePoint(point.xValue, point.yValue, point.slopeLeft, point.slopeRight, point.modeLeft, point.modeRight)


@pytest.fixture
def setup_curve_points():
    original_points = [
        CurvePoint(0, 1.008, 0.0174551, 0, 2, 3),
        CurvePoint(35, 0.333, -0.0146613, 0, 2, 3),
        CurvePoint(123, 0.1, 0.00696381, 0, 2, 3),
    ]
    working_points = [copy_curve_point(point) for point in original_points]
    setup_all_curve_values(working_points, len(working_points))
    return working_points


@pytest.mark.parametrize("xPosToTest, expectedYValue", [
    (3.9975, 1.044),
    (28.5975, 0.4719),
    (47.0475, 0.1796),
    (87.6375, -0.03009),
    (118.3875, 0.06965),
])
def test_curve(setup_curve_points, xPosToTest, expectedYValue):
    yValue = sample_curve(xPosToTest, setup_curve_points, len(setup_curve_points))
    assert abs(yValue - expectedYValue) < 0.001
