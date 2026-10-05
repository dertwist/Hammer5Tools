"""Transport regression coverage; structured DMX behavior is tested in Core."""
from unittest.mock import Mock
import pytest
from automation.operations.vmap_blockout import write_blockout


def test_blockout_forwards_explicit_scale_and_file_source():
    bridge = Mock()
    bridge.author_map.return_value = {"dry_run": True, "box_count": 154}
    result = write_blockout("C:/addon/maps/out.vmap", items_file="C:/addon/items.json",
                            skeleton="C:/addon/maps/base.vmap", dry_run=True, bridge=bridge)
    request, operation = bridge.author_map.call_args.args
    assert operation == "insert" and "boxes" not in request
    assert request["items_file"].endswith("items.json") and result["box_count"] == 154
    write_blockout("C:/addon/maps/out.vmap", [{"model": "models/a.vmdl", "scale": 1}], bridge=bridge)
    assert bridge.author_map.call_args.args[0]["boxes"][0]["scale"] == 1


def test_core_failure_reaches_caller():
    bridge = Mock()
    bridge.author_map.side_effect = ValueError("size and scale conflict")
    with pytest.raises(ValueError, match="conflict"):
        write_blockout("C:/addon/maps/out.vmap", [{"size": [1,1,1], "scale": 2}], bridge=bridge)
