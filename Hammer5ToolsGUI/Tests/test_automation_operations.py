"""Tests for automation operations (VMAP rewriter, dependencies, validation, compiler, VPK)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from automation.operations.compiler import compile_asset
from automation.operations.dependencies import resolve_dependencies
from automation.operations.validation import validate_addon
from automation.operations.vmap_ops import vmap_rewrite_references
from automation.operations.vpk_ops import vpk_search
from core.bridge import VmapRewriteResult


def test_vmap_rewrite_references_dry_run_and_apply(tmp_path):
    vmap_file = tmp_path / "test.vmap"
    vmap_file.write_text("dummy vmap content", encoding="utf-8")
    vmap_path = str(vmap_file)

    mock_bridge = MagicMock()
    mock_bridge.read_valve_map_asset_references.return_value = (
        "materials/old_wood.vmat",
        "models/props/old_barrel.vmdl",
    )
    mock_bridge.rewrite_vmap_references.return_value = VmapRewriteResult(True, ())

    replacements = {
        "materials/old_wood.vmat": "materials/new_wood.vmat",
        "models/props/old_barrel.vmdl": "models/props/new_barrel.vmdl",
    }

    # Dry-run
    preview = vmap_rewrite_references(vmap_path, replacements, bridge=mock_bridge, dry_run=True)
    assert preview["dry_run"] is True
    assert preview["matched_count"] == 2
    mock_bridge.rewrite_vmap_references.assert_not_called()

    # Real apply
    result = vmap_rewrite_references(vmap_path, replacements, bridge=mock_bridge, dry_run=False)
    assert result["dry_run"] is False
    assert result["changed"] is True
    mock_bridge.rewrite_vmap_references.assert_called_once_with(vmap_path, replacements)


def test_resolve_dependencies_on_vmat(tmp_path):
    vmat_file = tmp_path / "test.vmat"
    vmat_file.write_text(
        'Layer0\n{\n\tshader "csgo_environment.vfx"\n\tTextureColor "materials/props/wood_color.png"\n}\n',
        encoding="utf-8",
    )

    result = resolve_dependencies(str(vmat_file), addon_dir=str(tmp_path))
    assert result["total_references"] >= 1
    assert "materials/props/wood_color.png" in result["textures"]


def test_compiler_missing_file():
    with pytest.raises(FileNotFoundError):
        compile_asset("non_existent_file.vmat", cs2_path="C:/fake_cs2")


def test_validate_addon_invokes_core_bridge():
    mock_bridge = MagicMock()
    mock_bridge.source_porter_validate.return_value = 0

    result = validate_addon(addon_name="test_addon", cs2_dir="C:/CS2", bridge=mock_bridge)
    assert result["clean"] is True
    assert result["status_code"] == 0
    mock_bridge.source_porter_validate.assert_called_once()


class _FakeVpkIndex:
    """Archive holding only compiled names, the way a real CS2 VPK does."""

    def __init__(self, stored):
        self._stored = stored

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def mount(self, _path):
        return None

    def read_bytes(self, path):
        return self._stored.get(path)


class _FakeVpkIndexRecordingMounts(_FakeVpkIndex):
    def __init__(self, stored, mounted):
        super().__init__(stored)
        self._mounted = mounted

    def mount(self, path):
        self._mounted.append(path)

    def entries(self, _suffixes):
        return [(name, len(data)) for name, data in self._stored.items()]


class _FakeVpkBridge:
    def __init__(self, stored):
        self._stored = stored
        self.mounted = []

    def create_vpk_index(self):
        return _FakeVpkIndexRecordingMounts(self._stored, self.mounted)


def test_vpk_extract_accepts_the_source_name_vpk_search_reports(tmp_path, monkeypatch):
    import os
    from automation.operations import vpk_ops

    monkeypatch.setattr(vpk_ops.os.path, "isfile", lambda _path: True)
    bridge = _FakeVpkBridge({"models/dev/dev_cube.vmdl_c": b"compiled"})
    output = str(tmp_path / "dev_cube.vmdl_c")

    result = vpk_ops.vpk_extract(
        "models/dev/dev_cube.vmdl", output, game_dir="C:/cs2", bridge=bridge
    )

    assert result["internal_path"] == "models/dev/dev_cube.vmdl_c"
    assert os.path.isfile(output)


def test_vpk_extract_reports_both_names_when_nothing_matches(tmp_path, monkeypatch):
    import pytest
    from automation.operations import vpk_ops

    monkeypatch.setattr(vpk_ops.os.path, "isfile", lambda _path: True)

    with pytest.raises(FileNotFoundError, match="also tried"):
        vpk_ops.vpk_extract(
            "models/dev/missing.vmdl",
            str(tmp_path / "out.bin"),
            game_dir="C:/cs2",
            bridge=_FakeVpkBridge({}),
        )


def test_vpk_tools_search_every_stock_archive(tmp_path, monkeypatch):
    from automation.operations import vpk_ops

    # placeholder_box lives in core, dev_cube in csgo. Searching only csgo makes
    # an asset that exists look missing, which is how a wrong "it does not
    # exist" conclusion gets drawn.
    monkeypatch.setattr(vpk_ops.os.path, "isfile", lambda _path: True)
    bridge = _FakeVpkBridge({"models/editor/placeholder_box.vmdl_c": b"box"})

    result = vpk_ops.vpk_search("placeholder", game_dir="C:/cs2", bridge=bridge)

    mounted = " ".join(bridge.mounted).replace("\\", "/")
    for archive in ("game/csgo/", "game/core/", "game/csgo_core/"):
        assert archive in mounted, f"{archive} was never mounted"
    assert result["match_count"] == 1
    assert len(result["archives"]) == len(vpk_ops._CONTENT_ARCHIVES)


def test_smartprop_expressions_are_not_mistaken_for_asset_paths(tmp_path):
    from automation.formats.vsmart_io import write_vsmart

    vsmart = tmp_path / "kit.vsmart"
    write_vsmart(str(vsmart), children=[{
        "_class": "CSmartPropElement_Model",
        "m_sModelName": "models/props/real_panel.vmdl",
        # A division expression contains a slash but is not a path.
        "m_vModelScale": {"m_Components": [{"m_Expression": " (sizer_x+32)/32 "}, 1.0, 1.0]},
    }])

    result = resolve_dependencies(str(vsmart), addon_dir=str(tmp_path))

    assert "models/props/real_panel.vmdl" in result["models"]
    assert result["other"] == []
    assert not any("sizer_x" in reference for reference in result["models"])
    assert result["total_references"] == 1


def test_material_slot_values_that_are_not_files_are_ignored(tmp_path):
    from automation.formats.vmat_io import write_vmat

    vmat = tmp_path / "surface.vmat"
    write_vmat(str(vmat), slots={
        "TextureColor": "materials/props/wood_color.png",
        "g_vTextureScale": "[1.000000 1.000000 0.000000]",
    })

    result = resolve_dependencies(str(vmat), addon_dir=str(tmp_path))

    assert result["textures"] == ["materials/props/wood_color.png"]
    assert result["other"] == []


def test_flat_reference_list_is_opt_in(tmp_path):
    from automation.formats.vmat_io import write_vmat

    vmat = tmp_path / "surface.vmat"
    write_vmat(str(vmat), slots={"TextureColor": "materials/props/wood_color.png"})

    assert "all_references" not in resolve_dependencies(str(vmat), addon_dir=str(tmp_path))
    opted_in = resolve_dependencies(str(vmat), addon_dir=str(tmp_path), include_all=True)
    assert opted_in["all_references"] == ["materials/props/wood_color.png"]
