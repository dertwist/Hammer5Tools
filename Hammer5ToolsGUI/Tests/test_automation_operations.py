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
