"""
Unit tests for Detail Prop Editor multiline vector formatting.
"""

import os
import sys
import tempfile
import pytest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from gui.common import Kv3ToJson
from gui.forms.detail_prop_editor.vdata_io import (
    save_vdata,
    load_vdata,
    default_type,
    _format_vdata_kv3,
    _serialize_type,
    GENERIC_DATA_TYPE,
)


def test_detail_prop_vector_multiline_format():
    """Verify that vector properties in DetailProp editor are serialized multiline with 6 decimal places."""
    payload = {
        "generic_data_type": GENERIC_DATA_TYPE,
        "test_grass": _serialize_type(default_type()),
    }

    formatted = _format_vdata_kv3(payload)

    # Verify multiline structure for m_vRandomRotationMin
    assert "m_vRandomRotationMin =" in formatted
    assert "m_vRandomRotationMax =" in formatted

    # Check for expected indented multiline bracket layout and values
    expected_min_fragment = """m_vRandomRotationMin = 
\t\t\t\t[
\t\t\t\t\t0.000000,
\t\t\t\t\t0.000000,
\t\t\t\t\t0.000000,
\t\t\t\t]"""
    assert expected_min_fragment in formatted

    expected_max_fragment = """m_vRandomRotationMax = 
\t\t\t\t[
\t\t\t\t\t0.000000,
\t\t\t\t\t360.000000,
\t\t\t\t\t0.000000,
\t\t\t\t]"""
    assert expected_max_fragment in formatted

    # Verify that the formatted text can be parsed back into correct python data
    parsed = Kv3ToJson(formatted)
    assert parsed["generic_data_type"] == "CDetailPropType"
    models = parsed["test_grass"]["m_Models"]
    assert len(models) == 1
    assert models[0]["m_vRandomRotationMin"] == [0.0, 0.0, 0.0]
    assert models[0]["m_vRandomRotationMax"] == [0.0, 360.0, 0.0]


def test_save_and_load_vdata_roundtrip():
    """Test save_vdata writing to disk and load_vdata reading back."""
    types = {"my_custom_detail": default_type()}
    types["my_custom_detail"]["m_Models"][0]["m_vRandomRotationMax"] = [15.0, 360.0, 5.0]

    with tempfile.NamedTemporaryFile(suffix=".vdata", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        save_vdata(tmp_path, types)

        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check multiline formatting in saved file
        assert "m_vRandomRotationMax = \n" in content
        assert "\t360.000000,\n" in content
        assert "\t5.000000,\n" in content

        # Check editor_info presence in saved file
        assert "editor_info =" in content
        assert 'name = "Hammer 5 Tools"' in content

        # Load back
        loaded = load_vdata(tmp_path)
        assert "my_custom_detail" in loaded
        assert "editor_info" not in loaded  # editor_info is metadata, not a detail prop type
        assert loaded["my_custom_detail"]["m_Models"][0]["m_vRandomRotationMax"] == [15.0, 360.0, 5.0]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
