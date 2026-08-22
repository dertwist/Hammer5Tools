import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pytest

from src.editors.smartprop_editor.viewport_3d.camera import decompose_trs
from src.editors.smartprop_editor.viewport_3d.engine.context import EvalContext
from src.editors.smartprop_editor.viewport_3d.engine.modifier_evaluator import (
    evaluate_single_modifier, evaluate_element_modifiers, resolve_color,
)


def test_user_case_sizer_before_translate():
    """Verify that CreateSizer placed before Translate captures the untranslated matrix."""
    ctx = EvalContext()
    data = {
        "_class": "CSmartPropElement_Group",
        "m_nElementID": 3,
        "m_Modifiers": [
            {
                "_class": "CSmartPropOperation_CreateSizer",
                "m_nElementID": 4,
                "m_flInitialMaxX": 32.0,
                "m_flInitialMaxY": 32.0,
                "m_flInitialMaxZ": 32.0,
                "m_flInitialMinX": 0.0,
                "m_flInitialMinY": -32.0,
                "m_flInitialMinZ": 0.0,
                "m_OutputVariableMaxX": "new_var_2",
                "m_OutputVariableMaxY": "new_var_1",
                "m_OutputVariableMaxZ": "new_var_1",
                "m_OutputVariableMinX": "new_var_2",
            },
            {
                "_class": "CSmartPropOperation_Translate",
                "m_nElementID": 46,
                "m_bEnabled": True,
                "m_vPosition": {
                    "m_Components": [44.8196, 0.0, 82.9033]
                }
            }
        ],
        "m_Children": []
    }

    local_mat, world_mat, model_mat, widgets = evaluate_element_modifiers(data, ctx)

    # 1. Exactly 1 sizer widget extracted
    assert len(widgets) == 1
    sizer = widgets[0]
    assert sizer["type"] == "sizer"
    assert sizer["element_id"] == 4

    # 2. Sizer was defined BEFORE Translate, so its position MUST be (0, 0, 0)
    np.testing.assert_allclose(sizer["position"], [0.0, 0.0, 0.0], atol=1e-4)
    np.testing.assert_allclose(sizer["world_matrix"][:3, :3], np.eye(3), atol=1e-4)
    np.testing.assert_allclose(sizer["world_matrix"][3, :3], [0.0, 0.0, 0.0], atol=1e-4)

    # 3. Final element world_mat (passed to children) MUST include Translate
    pos, rot, scale = decompose_trs(world_mat)
    np.testing.assert_allclose(pos, [44.8196, 0.0, 82.9033], atol=1e-4)


def test_user_case_translate_before_sizer():
    """Verify that Translate placed before CreateSizer translates the sizer."""
    ctx = EvalContext()
    data = {
        "_class": "CSmartPropElement_Group",
        "m_nElementID": 3,
        "m_Modifiers": [
            {
                "_class": "CSmartPropOperation_Translate",
                "m_nElementID": 46,
                "m_bEnabled": True,
                "m_vPosition": {
                    "m_Components": [44.8196, 0.0, 82.9033]
                }
            },
            {
                "_class": "CSmartPropOperation_CreateSizer",
                "m_nElementID": 4,
                "m_flInitialMaxX": 32.0,
                "m_flInitialMaxY": 32.0,
                "m_flInitialMaxZ": 32.0,
                "m_flInitialMinX": 0.0,
                "m_flInitialMinY": -32.0,
                "m_flInitialMinZ": 0.0,
                "m_OutputVariableMaxX": "new_var_2",
                "m_OutputVariableMaxY": "new_var_1",
                "m_OutputVariableMaxZ": "new_var_1",
                "m_OutputVariableMinX": "new_var_2",
            }
        ],
        "m_Children": []
    }

    local_mat, world_mat, model_mat, widgets = evaluate_element_modifiers(data, ctx)

    assert len(widgets) == 1
    sizer = widgets[0]
    # Sizer was defined AFTER Translate, so its position MUST be (44.8196, 0, 82.9033)
    np.testing.assert_allclose(sizer["position"], [44.8196, 0.0, 82.9033], atol=1e-4)
    np.testing.assert_allclose(sizer["world_matrix"][3, :3], [44.8196, 0.0, 82.9033], atol=1e-4)


def test_sequential_rotate_then_translate_element_space():
    """Rotate Yaw 90 then Translate local X 50 -> world pos should be (0, 50, 0)."""
    ctx = EvalContext()
    data = {
        "_class": "CSmartPropElement_Group",
        "m_Modifiers": [
            {
                "_class": "CSmartPropOperation_Rotate",
                "m_vRotation": [0.0, 90.0, 0.0],
                "m_CoordinateSpace": "ELEMENT"
            },
            {
                "_class": "CSmartPropOperation_Translate",
                "m_vPosition": [50.0, 0.0, 0.0],
                "m_CoordinateSpace": "ELEMENT"
            }
        ]
    }
    local_mat, world_mat, _, _ = evaluate_element_modifiers(data, ctx)
    pos, rot, scale = decompose_trs(world_mat)

    # In Source 2: Yaw 90 rotates +X to +Y. Translating +50 along local X results in world Y = 50.
    np.testing.assert_allclose(pos, [0.0, 50.0, 0.0], atol=1e-4)
    assert abs(rot[1] - 90.0) < 1e-4


def test_sequential_translate_then_rotate_element_space():
    """Translate local X 50 then Rotate Yaw 90 -> world pos should be (50, 0, 0)."""
    ctx = EvalContext()
    data = {
        "_class": "CSmartPropElement_Group",
        "m_Modifiers": [
            {
                "_class": "CSmartPropOperation_Translate",
                "m_vPosition": [50.0, 0.0, 0.0],
                "m_CoordinateSpace": "ELEMENT"
            },
            {
                "_class": "CSmartPropOperation_Rotate",
                "m_vRotation": [0.0, 90.0, 0.0],
                "m_CoordinateSpace": "ELEMENT"
            }
        ]
    }
    local_mat, world_mat, _, _ = evaluate_element_modifiers(data, ctx)
    pos, rot, scale = decompose_trs(world_mat)

    np.testing.assert_allclose(pos, [50.0, 0.0, 0.0], atol=1e-4)
    assert abs(rot[1] - 90.0) < 1e-4


def test_save_and_restore_state():
    """Verify SaveState and RestoreState preserves and recovers local transform matrix."""
    ctx = EvalContext()
    state_map = {}
    data = {
        "_class": "CSmartPropElement_Group",
        "m_Modifiers": [
            {"_class": "CSmartPropOperation_Translate", "m_vPosition": [10.0, 20.0, 30.0]},
            {"_class": "CSmartPropOperation_SaveState", "m_StateName": "checkpoint"},
            {"_class": "CSmartPropOperation_Translate", "m_vPosition": [100.0, 100.0, 100.0]},
            {"_class": "CSmartPropOperation_Rotate", "m_vRotation": [45.0, 45.0, 45.0]},
            {"_class": "CSmartPropOperation_RestoreState", "m_StateName": "checkpoint"},
        ]
    }
    local_mat, world_mat, _, _ = evaluate_element_modifiers(data, ctx, state_map=state_map)
    pos, rot, scale = decompose_trs(world_mat)

    # Restored back to (10, 20, 30) with 0 rotation
    np.testing.assert_allclose(pos, [10.0, 20.0, 30.0], atol=1e-4)
    np.testing.assert_allclose(rot, [0.0, 0.0, 0.0], atol=1e-4)


def test_multiple_progressive_locators():
    """Verify progressive CreateLocator operations in a modifier chain (like bend.vsmart)."""
    ctx = EvalContext()
    data = {
        "_class": "CSmartPropElement_Group",
        "m_nElementID": 100,
        "m_Modifiers": [
            {"_class": "CSmartPropOperation_Translate", "m_vPosition": [10.0, 0.0, 0.0]},
            {"_class": "CSmartPropOperation_CreateLocator", "m_LocatorName": "loc_1", "m_vOffset": [0.0, 0.0, 0.0]},
            {"_class": "CSmartPropOperation_Translate", "m_vPosition": [20.0, 0.0, 0.0]},
            {"_class": "CSmartPropOperation_CreateLocator", "m_LocatorName": "loc_2", "m_vOffset": [0.0, 0.0, 0.0]},
            {"_class": "CSmartPropOperation_Translate", "m_vPosition": [30.0, 0.0, 0.0]},
            {"_class": "CSmartPropOperation_CreateLocator", "m_LocatorName": "loc_3", "m_vOffset": [0.0, 0.0, 0.0]},
        ]
    }
    _, _, _, widgets = evaluate_element_modifiers(data, ctx)

    assert len(widgets) == 3
    assert widgets[0]["name"] == "loc_1"
    np.testing.assert_allclose(widgets[0]["position"], [10.0, 0.0, 0.0], atol=1e-4)

    assert widgets[1]["name"] == "loc_2"
    np.testing.assert_allclose(widgets[1]["position"], [30.0, 0.0, 0.0], atol=1e-4)

    assert widgets[2]["name"] == "loc_3"
    np.testing.assert_allclose(widgets[2]["position"], [60.0, 0.0, 0.0], atol=1e-4)


def test_reset_rotation_and_scale():
    """Verify ResetRotation and ResetScale modifiers."""
    ctx = EvalContext()
    data = {
        "_class": "CSmartPropElement_Group",
        "m_Modifiers": [
            {"_class": "CSmartPropOperation_Rotate", "m_vRotation": [30.0, 45.0, 60.0]},
            {"_class": "CSmartPropOperation_Scale", "m_flScale": 3.0},
            {"_class": "CSmartPropOperation_Translate", "m_vPosition": [5.0, 5.0, 5.0]},
            {"_class": "CSmartPropOperation_ResetRotation", "m_bResetPitch": True, "m_bResetYaw": True, "m_bResetRoll": True},
            {"_class": "CSmartPropOperation_ResetScale"},
        ]
    }
    _, world_mat, _, _ = evaluate_element_modifiers(data, ctx)
    pos, rot, scale = decompose_trs(world_mat)

    np.testing.assert_allclose(rot, [0.0, 0.0, 0.0], atol=1e-4)
    np.testing.assert_allclose(scale, [1.0, 1.0, 1.0], atol=1e-4)


def test_set_variable_modifier():
    """Verify SetVariable updates EvalContext dynamically during modifier evaluation."""
    ctx = EvalContext(variables={"test_scale": 1.0})
    data = {
        "_class": "CSmartPropElement_Group",
        "m_Modifiers": [
            {
                "_class": "CSmartPropOperation_SetVariableFloat",
                "m_VariableName": "test_scale",
                "m_flValue": 4.0
            },
            {
                "_class": "CSmartPropOperation_Scale",
                "m_flScale": {"m_SourceName": "test_scale"}
            }
        ]
    }
    _, world_mat, _, _ = evaluate_element_modifiers(data, ctx)
    _, _, scale = decompose_trs(world_mat)
    np.testing.assert_allclose(scale, [4.0, 4.0, 4.0], atol=1e-4)


def test_render_area_vsmart_traversal_user_case():
    """Integration test with SmartProp3DRenderArea rendering the user's sample structure."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from src.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea

    render_area = SmartProp3DRenderArea()
    vsmart_data = {
        "_class": "CSmartPropElement_Group",
        "m_nElementID": 3,
        "m_Modifiers": [
            {
                "_class": "CSmartPropOperation_CreateSizer",
                "m_nElementID": 4,
                "m_flInitialMaxX": 32.0,
                "m_flInitialMaxY": 32.0,
                "m_flInitialMaxZ": 32.0,
                "m_flInitialMinX": 0.0,
                "m_flInitialMinY": -32.0,
                "m_flInitialMinZ": 0.0,
                "m_OutputVariableMaxX": "new_var_2",
                "m_OutputVariableMaxY": "new_var_1",
                "m_OutputVariableMaxZ": "new_var_1",
                "m_OutputVariableMinX": "new_var_2",
            },
            {
                "_class": "CSmartPropOperation_Translate",
                "m_nElementID": 46,
                "m_vPosition": {
                    "m_Components": [44.8196, 0.0, 82.9033]
                }
            }
        ],
        "m_Children": [
            {
                "_class": "CSmartPropElement_Model",
                "m_nElementID": 10,
                "m_sModelName": "models/props/test.vmdl"
            }
        ]
    }

    models_list = []
    render_area._widget_infos = []
    render_area._traverse_vsmart_dict(vsmart_data, models_list)

    # 1. Verify model is placed at translated position
    assert len(models_list) == 1
    np.testing.assert_allclose(models_list[0]["position"], [44.8196, 0.0, 82.9033], atol=1e-4)

    # 2. Verify sizer widget in render_area._widget_infos is at untranslated position (0, 0, 0)
    assert len(render_area._widget_infos) == 1
    sizer_widget = render_area._widget_infos[0]
    assert sizer_widget["type"] == "sizer"
    assert sizer_widget["element_id"] == 4
    np.testing.assert_allclose(sizer_widget["position"], [0.0, 0.0, 0.0], atol=1e-4)
