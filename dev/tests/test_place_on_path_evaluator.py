import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from src.editors.smartprop_editor.viewport_3d.engine.context import EvalContext
from src.editors.smartprop_editor.viewport_3d.engine.path_evaluator import (
    catmull_rom_spline,
    compute_path_samples_with_tangents,
    interpolate_at_distance,
    build_orientation_matrix,
    sample_place_on_path,
    matches_path_selection_criteria,
)


def test_catmull_rom_spline():
    points = [[-400.0, 0.0, 0.0], [-200.0, 32.0, 0.0], [200.0, -32.0, 0.0], [400.0, 0.0, 0.0]]
    spline = catmull_rom_spline(points, samples_per_segment=10)
    assert len(spline) > len(points)
    # Start and end should match input control points
    np.testing.assert_allclose(spline[0], points[0], atol=1e-5)
    np.testing.assert_allclose(spline[-1], points[-1], atol=1e-5)


def test_path_sampling_and_tangents():
    points = [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [200.0, 0.0, 0.0]]
    samples, total_len = compute_path_samples_with_tangents(points, samples_per_segment=10)
    assert abs(total_len - 200.0) < 1.0

    pos, tangent = interpolate_at_distance(samples, total_len, 50.0)
    assert abs(pos[0] - 50.0) < 1.0
    assert abs(pos[1]) < 1e-4
    assert abs(pos[2]) < 1e-4
    # Tangent should point along +X
    np.testing.assert_allclose(tangent, [1.0, 0.0, 0.0], atol=1e-4)


def test_orientation_matrix_basis():
    pos = [10.0, 20.0, 30.0]
    forward = [1.0, 0.0, 0.0] # +X
    up = [0.0, 0.0, 1.0]      # +Z
    M = build_orientation_matrix(pos, forward, up)

    # In Source 2 row-vector convention:
    # Row 0: Forward (+X) -> [1, 0, 0]
    # Row 1: Left (+Y)    -> [0, 1, 0]
    # Row 2: Up (+Z)      -> [0, 0, 1]
    # Row 3: Pos          -> [10, 20, 30]
    np.testing.assert_allclose(M[0, :3], [1.0, 0.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(M[1, :3], [0.0, 1.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(M[2, :3], [0.0, 0.0, 1.0], atol=1e-5)
    np.testing.assert_allclose(M[3, :3], [10.0, 20.0, 30.0], atol=1e-5)


def test_sample_place_on_path_defaults():
    ctx = EvalContext()
    data = {
        "_class": "CSmartPropElement_PlaceOnPath",
        "m_flSpacing": 100.0,
        "m_flOffsetAlongPath": 0.0,
        "m_DefaultPath": [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [200.0, 0.0, 0.0], [300.0, 0.0, 0.0]],
    }
    result = sample_place_on_path(data, ctx)
    instances = result["instances"]
    assert len(instances) == 4 # 0, 100, 200, 300
    assert result["total_length"] >= 299.0
    for i, inst in enumerate(instances):
        assert inst["index"] == i
        assert inst["count"] == 4
        assert abs(inst["position"][0] - i * 100.0) < 2.0


def test_selection_criteria_path_position():
    ctx = EvalContext()

    # ALL
    child_all = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_PathPosition", "m_PlaceAtPositions": "ALL"}
        ]
    }
    assert matches_path_selection_criteria(child_all, 0, 5, ctx) is True
    assert matches_path_selection_criteria(child_all, 2, 5, ctx) is True
    assert matches_path_selection_criteria(child_all, 4, 5, ctx) is True

    # START_AND_END
    child_start_end = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_PathPosition", "m_PlaceAtPositions": "START_AND_END"}
        ]
    }
    assert matches_path_selection_criteria(child_start_end, 0, 5, ctx) is True
    assert matches_path_selection_criteria(child_start_end, 1, 5, ctx) is False
    assert matches_path_selection_criteria(child_start_end, 4, 5, ctx) is True

    # START only
    child_start = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_PathPosition", "m_PlaceAtPositions": "START"}
        ]
    }
    assert matches_path_selection_criteria(child_start, 0, 5, ctx) is True
    assert matches_path_selection_criteria(child_start, 1, 5, ctx) is False

    # END only
    child_end = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_PathPosition", "m_PlaceAtPositions": "END"}
        ]
    }
    assert matches_path_selection_criteria(child_end, 4, 5, ctx) is True
    assert matches_path_selection_criteria(child_end, 0, 5, ctx) is False

    # INTERNAL only
    child_internal = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_PathPosition", "m_PlaceAtPositions": "INTERNAL"}
        ]
    }
    assert matches_path_selection_criteria(child_internal, 0, 5, ctx) is False
    assert matches_path_selection_criteria(child_internal, 2, 5, ctx) is True
    assert matches_path_selection_criteria(child_internal, 4, 5, ctx) is False

    # NTH (every 2nd, offset 0)
    child_nth = {
        "m_SelectionCriteria": [
            {
                "_class": "CSmartPropSelectionCriteria_PathPosition",
                "m_PlaceAtPositions": "NTH",
                "m_nPlaceEveryNthPosition": 2,
                "m_nNthPositionIndexOffset": 0,
            }
        ]
    }
    assert matches_path_selection_criteria(child_nth, 0, 6, ctx) is True
    assert matches_path_selection_criteria(child_nth, 1, 6, ctx) is False
    assert matches_path_selection_criteria(child_nth, 2, 6, ctx) is True
    assert matches_path_selection_criteria(child_nth, 3, 6, ctx) is False


def test_selection_criteria_endcap():
    ctx = EvalContext()
    cap_start = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_EndCap", "m_bStart": True, "m_bEnd": False}
        ]
    }
    cap_end = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_EndCap", "m_bStart": False, "m_bEnd": True}
        ]
    }
    assert matches_path_selection_criteria(cap_start, 0, 5, ctx) is True
    assert matches_path_selection_criteria(cap_start, 1, 5, ctx) is False
    assert matches_path_selection_criteria(cap_end, 4, 5, ctx) is True
    assert matches_path_selection_criteria(cap_end, 0, 5, ctx) is False


def test_selection_criteria_is_valid():
    ctx = EvalContext(variables={"enable_post": 1})
    valid_child = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_IsValid", "m_Expression": "enable_post == 1"}
        ]
    }
    invalid_child = {
        "m_SelectionCriteria": [
            {"_class": "CSmartPropSelectionCriteria_IsValid", "m_Expression": "enable_post == 0"}
        ]
    }
    assert matches_path_selection_criteria(valid_child, 0, 5, ctx) is True
    assert matches_path_selection_criteria(invalid_child, 0, 5, ctx) is False


def test_traverse_vsmart_place_on_path():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from src.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea

    render_area = SmartProp3DRenderArea()

    vsmart_data = {
        "_class": "CSmartPropElement_PlaceOnPath",
        "m_nElementID": 10,
        "m_flSpacing": 100.0,
        "m_flOffsetAlongPath": 0.0,
        "m_DefaultPath": [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [200.0, 0.0, 0.0]],
        "m_Children": [
            {
                "_class": "CSmartPropElement_Model",
                "m_nElementID": 11,
                "m_sModelName": "models/props/fence_post.vmdl",
                "m_SelectionCriteria": [
                    {
                        "_class": "CSmartPropSelectionCriteria_PathPosition",
                        "m_PlaceAtPositions": "ALL"
                    }
                ]
            }
        ]
    }

    models_list = []
    render_area._traverse_vsmart_dict(vsmart_data, models_list)

    # Should have placed the child model at 3 positions (0, 100, 200)
    assert len(models_list) == 3
    for i, m in enumerate(models_list):
        assert m["id"] == 11
        assert m["path"] == "models/props/fence_post.vmdl"
        assert abs(m["position"][0] - i * 100.0) < 2.0


def test_evaluate_preset_path_vsmart():
    from pathlib import Path
    from src.common import Kv3ToJson
    from PySide6.QtWidgets import QApplication
    from src.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea

    app = QApplication.instance() or QApplication([])
    render_area = SmartProp3DRenderArea()

    preset_path = Path(__file__).resolve().parent.parent.parent / "Hammer5Tools" / "Presets" / "hammer5tools" / "content" / "smartprops" / "generic" / "path.vsmart"
    if not preset_path.exists():
        return

    with open(preset_path, "r", encoding="utf-8") as f:
        content = f.read()

    import re
    content = re.sub(re.compile(r"= resource_name:"), "= ", content)
    content = content.replace("null,", "")
    vsmart_data = Kv3ToJson(content)

    # Build eval context from variables
    var_dict = {}
    for var in vsmart_data.get("m_Variables", []):
        name = var.get("m_VariableName")
        val = var.get("m_DefaultValue")
        if name:
            var_dict[name] = val

    from src.editors.smartprop_editor.viewport_3d.engine.context import EvalContext
    ctx = EvalContext(variables=var_dict)

    models_list = []
    render_area._traverse_vsmart_dict(vsmart_data, models_list, ctx=ctx)

    # Confirm exactly 26 bricks placed along the 812-unit path with step 32
    assert len(models_list) == 26
    for m in models_list:
        assert m["path"] == "models/props/de_inferno/hr_i/broken_wall_bricks/broken_wall_brick_05.vmdl"
        assert len(m["position"]) == 3


def test_projected_distance():
    # 3D diagonal path
    points = [[0.0, 0.0, 0.0], [100.0, 0.0, 100.0]]
    ctx = EvalContext()
    data_3d = {
        "_class": "CSmartPropElement_PlaceOnPath",
        "m_DefaultPath": points,
        "m_bUseProjectedDistance": False,
    }
    res_3d = sample_place_on_path(data_3d, ctx)

    data_proj = {
        "_class": "CSmartPropElement_PlaceOnPath",
        "m_DefaultPath": points,
        "m_bUseProjectedDistance": True,
        "m_vUpDirection": [0.0, 0.0, 1.0],
    }
    res_proj = sample_place_on_path(data_proj, ctx)

    # 3D length is ~141.4, projected horizontal length is ~100.0
    assert abs(res_3d["total_length"] - 141.42) < 2.0
    assert abs(res_proj["total_length"] - 100.0) < 2.0


def test_evaluate_preview_vsmart():
    from pathlib import Path
    from src.common import Kv3ToJson
    from PySide6.QtWidgets import QApplication
    from src.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea

    app = QApplication.instance() or QApplication([])
    render_area = SmartProp3DRenderArea()

    preview_path = Path("e:/steamlibrary/steamapps/common/counter-strike global offensive/content/csgo_addons/smartprop_guide/models/preview.vsmart")
    if not preview_path.exists():
        return

    with open(preview_path, "r", encoding="utf-8") as f:
        content = f.read()

    import re
    content = re.sub(re.compile(r"= resource_name:"), "= ", content)
    content = content.replace("null,", "")
    vsmart_data = Kv3ToJson(content)

    # Test ALL mode with allow_start=False, allow_end=False -> 9 rocks placed
    for ch in vsmart_data.get("m_Children", []):
        if ch.get("_class") == "CSmartPropElement_PlaceOnPath":
            for model_ch in ch.get("m_Children", []):
                for crit in model_ch.get("m_SelectionCriteria", []):
                    crit["m_PlaceAtPositions"] = "ALL"
                    crit["m_bAllowAtStart"] = False
                    crit["m_bAllowAtEnd"] = False

    from src.editors.smartprop_editor.viewport_3d.engine.context import EvalContext
    ctx = EvalContext()

    models_list = []
    render_area._traverse_vsmart_dict(vsmart_data, models_list, ctx=ctx)

    # In preview.vsmart with step 3, exactly 5 rocks are placed
    assert len(models_list) == 5
    for m in models_list:
        assert m["path"] == "models/props/de_aztec/hr_aztec/aztec_stairs/aztec_stairs_01_loose_rock_03.vmdl"


def run_all_tests():
    test_catmull_rom_spline()
    test_path_sampling_and_tangents()
    test_orientation_matrix_basis()
    test_sample_place_on_path_defaults()
    test_selection_criteria_path_position()
    test_selection_criteria_endcap()
    test_selection_criteria_is_valid()
    test_traverse_vsmart_place_on_path()
    test_evaluate_preset_path_vsmart()
    test_evaluate_preview_vsmart()
    test_projected_distance()
    print("All Place on Path tests passed successfully!")


if __name__ == "__main__":
    run_all_tests()
