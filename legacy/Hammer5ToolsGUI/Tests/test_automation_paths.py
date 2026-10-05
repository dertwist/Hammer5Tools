from unittest.mock import Mock

import pytest

from automation.tools import TOOLS_BY_NAME, invoke_tool


def test_relative_context_is_read_on_each_call(monkeypatch):
    from gui.settings import common
    root = ["C:/addon one"]
    monkeypatch.setattr(common, "addon_content_dir", lambda: root[0])
    bridge = Mock()
    bridge.resolve_asset_path.return_value = "C:/resolved/maps/模型.vmap"
    bridge.read_valve_map_asset_references.return_value = ()
    invoke_tool("hammer5tools.vmap_references", {"path": "maps/模型.vmap"}, bridge=bridge)
    root[0] = "C:/addon two"
    invoke_tool("hammer5tools.vmap_references", {"path": "maps/模型.vmap"}, bridge=bridge)
    assert [call.args[1] for call in bridge.resolve_asset_path.call_args_list] == ["C:/addon one", "C:/addon two"]
    invoke_tool("hammer5tools.vmap_references", {"path": "maps/模型.vmap", "addon_root": "C:/explicit"}, bridge=bridge)
    assert bridge.resolve_asset_path.call_args.args == ("maps/模型.vmap", "C:/explicit", True)


def test_absolute_paths_do_not_require_addon_context():
    bridge = Mock()
    bridge.read_valve_map_asset_references.return_value = ()
    invoke_tool("hammer5tools.vmap_references", {"path": "C:/outside/模型.vmap"}, bridge=bridge)
    bridge.resolve_asset_path.assert_not_called()
    bridge.read_valve_map_asset_references.assert_called_once_with("C:/outside/模型.vmap")
    with pytest.raises(ValueError, match="Drive-relative"):
        invoke_tool("hammer5tools.vmap_references", {"path": "C:maps/test.vmap"}, bridge=bridge)


def test_path_schemas_expose_context():
    for name in ("vmdl_read", "vmat_edit", "vmap_scene", "vmap_rewrite_references", "compile_asset"):
        assert "addon_root" in TOOLS_BY_NAME[f"hammer5tools.{name}"].input_schema["properties"]
