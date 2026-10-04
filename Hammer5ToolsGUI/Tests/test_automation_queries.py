import json

import pytest

from automation.tools import invoke_tool
from test_mcp_feedback_baseline import FeedbackBridge, MAP_PATH, REFERENCES


def test_all_references_recoverable_with_filters_and_pages():
    values = []
    for offset in range(0, 500, 50):
        result = invoke_tool("hammer5tools.vmap_references", {"path": MAP_PATH, "offset": offset}, bridge=FeedbackBridge())
        assert result["total"] == 500 and result["returned"] == 50
        assert len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 16 * 1024
        values.extend(result["references"])
    assert values == list(REFERENCES)
    result = invoke_tool("hammer5tools.vmap_references", {
        "path": MAP_PATH, "pattern": "MODELS\\PROPS\\*00?.VMDL", "extension": ".VMDL", "detail": "names",
    }, bridge=FeedbackBridge())
    assert result["total"] == 10 and len(result["references"]) == 10


@pytest.mark.parametrize("arguments", [{"limit": 0}, {"limit": 501}, {"limit": True}, {"offset": -1}, {"detail": "other"}])
def test_invalid_query_arguments(arguments):
    with pytest.raises(ValueError):
        invoke_tool("hammer5tools.vmap_references", {"path": MAP_PATH, **arguments}, bridge=FeedbackBridge())


def test_vpk_pages_deduplicate_in_mount_order(monkeypatch):
    from automation.operations import vpk_ops

    class Index:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def mount(self, _path):
            pass

        def entries(self, _suffixes):
            return [("models/B.vmdl", 10), ("models/a.vmdl", 20), ("MODELS\\b.vmdl", 99)]

    class Bridge:
        def create_vpk_index(self):
            return Index()

    monkeypatch.setattr(vpk_ops, "_archive_paths", lambda _root: ["first", "second"])
    result = vpk_ops.vpk_search("models", game_dir="fixture", bridge=Bridge(), offset=1, limit=1)
    assert result["matches"] == [{"path": "models/B.vmdl", "size_bytes": 10}]
    assert result["total"] == 2 and result["match_count"] == result["returned"] == 1
