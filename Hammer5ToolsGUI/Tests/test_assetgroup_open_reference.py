import os
import sys
import json
import tempfile
import pytest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_dir = os.path.join(repo_root, "Hammer5ToolsGUI")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from hammer5tools_gui.editors.assetgroup_maker.monitor import get_reference_asset_path


def test_get_reference_asset_path_relative_forward_slash():
    data = {
        "process": {
            "reference": "models/firewatch/nature/rocks/groupedrock/grouped_rock_3.vmdl"
        }
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.hbat', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    try:
        res = get_reference_asset_path(temp_path)
        assert res == "models/firewatch/nature/rocks/groupedrock/grouped_rock_3.vmdl"
    finally:
        os.remove(temp_path)


def test_get_reference_asset_path_relative_backward_slash():
    data = {
        "process": {
            "reference": "models\\firewatch\\nature\\rocks\\groupedrock\\grouped_rock_3.vmdl"
        }
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.hbat', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    try:
        res = get_reference_asset_path(temp_path)
        assert res == "models/firewatch/nature/rocks/groupedrock/grouped_rock_3.vmdl"
    finally:
        os.remove(temp_path)


def test_get_reference_asset_path_empty_reference():
    data = {
        "process": {
            "reference": ""
        }
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.hbat', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    try:
        res = get_reference_asset_path(temp_path)
        assert res is None
    finally:
        os.remove(temp_path)


def test_get_reference_asset_path_missing_process():
    data = {}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.hbat', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    try:
        res = get_reference_asset_path(temp_path)
        assert res is None
    finally:
        os.remove(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
