from pathlib import Path

from core.bridge.core import SmartPropWidget
from gui.editors.smartprop_editor.viewport_3d.gizmo import GizmoAxis, GizmoMode
from gui.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea
from gui.editors.smartprop_editor.viewport_3d.viewport import _bundled_hammer_icon_path


class _TransformMethodHost:
    _MODEL_LIKE_CLASSES = SmartProp3DRenderArea._MODEL_LIKE_CLASSES
    _find_modifier = staticmethod(SmartProp3DRenderArea._find_modifier)
    _scale_axis_availability = SmartProp3DRenderArea._scale_axis_availability


def test_core_widget_is_adapted_to_viewport_draw_schema():
    widget = SmartPropWidget(
        "locator",
        9,
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            12.0, 3.0, -2.0, 1.0,
        ),
        (1.0, 2.0, 3.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
        (0.6, 0.6, 0.6),
        (False,) * 6,
        (False,) * 3,
        2.0,
        16.0,
        0.0,
        8.0,
        "SQUARE",
        "origin",
    )

    draw_info = SmartProp3DRenderArea._widget_draw_info(widget)

    assert draw_info["type"] == "locator"
    assert draw_info["element_id"] == 9
    assert draw_info["position"] == [13.0, 5.0, 1.0]
    assert draw_info["rotation"] == [0.0, 0.0, 0.0]
    assert draw_info["scale"] == 2.0


def test_core_group_is_adapted_to_selectable_scene_object():
    widget = SmartPropWidget(
        "group",
        4,
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            12.0, 3.0, -2.0, 1.0,
        ),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
        (0.6, 0.6, 0.6),
        (False,) * 6,
        (False,) * 3,
        1.0,
        16.0,
        0.0,
        8.0,
        "SQUARE",
        "",
    )
    data = {"_class": "CSmartPropElement_Group", "m_nElementID": 4}

    draw_info = SmartProp3DRenderArea._group_draw_info(widget, data)

    assert draw_info["id"] == 4
    assert draw_info["position"] == [12.0, 3.0, -2.0]
    assert draw_info["is_group"] is True
    assert draw_info["data"] is data


def test_group_supports_move_and_rotate_gizmos():
    render_area = _TransformMethodHost()
    group = {"_class": "CSmartPropElement_Group", "m_nElementID": 4}

    availability, scale_source = SmartProp3DRenderArea._compute_axis_availability(render_area, group)
    translate = availability[GizmoMode.TRANSLATE]
    rotate = availability[GizmoMode.ROTATE]

    assert all(translate[axis] for axis in (GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z))
    assert all(rotate[axis] for axis in (GizmoAxis.X, GizmoAxis.Y, GizmoAxis.Z))
    assert scale_source is None


def test_group_move_and_rotate_create_transform_modifiers():
    render_area = _TransformMethodHost()
    group = {"_class": "CSmartPropElement_Group", "m_nElementID": 4}

    translate = SmartProp3DRenderArea._find_or_create_modifier(
        render_area,
        group,
        "CSmartPropOperation_Translate",
        "m_vPosition",
    )
    rotate = SmartProp3DRenderArea._find_or_create_modifier(
        render_area,
        group,
        "CSmartPropOperation_Rotate",
        "m_vRotation",
    )

    assert group["m_Modifiers"] == [translate, rotate]
    assert translate["m_vPosition"]["m_Components"] == [0.0, 0.0, 0.0]
    assert rotate["m_vRotation"]["m_Components"] == [0.0, 0.0, 0.0]


def test_display_groups_toggle_uses_bundled_group_icon():
    icon_path = Path(_bundled_hammer_icon_path("selection_mode_groups.png"))

    assert icon_path.name == "selection_mode_groups.png"
    assert icon_path.is_file()
