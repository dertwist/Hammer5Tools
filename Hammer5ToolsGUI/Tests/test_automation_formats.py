"""Tests for Source 2 format IO automation tools (VMDL, VMAT, VTEX, VSMART, VDATA, VSNAP)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from automation.formats.vmdl_io import edit_vmdl, read_vmdl, write_vmdl
from automation.formats.vmat_io import edit_vmat, read_vmat, write_vmat
from automation.formats.vtex_io import edit_vtex, read_vtex, write_vtex
from automation.formats.vsmart_io import edit_vsmart, evaluate_vsmart, read_vsmart, write_vsmart
from automation.formats.vdata_io import edit_vdata, read_vdata, write_vdata
from automation.formats.vsnap_io import edit_vsnap, generate_vsnap, read_vsnap, write_vsnap
from core.bridge import SnapshotDocument, SnapshotStream, SmartPropEvaluation, SmartPropModel


def test_vmdl_write_read_edit_roundtrip(tmp_path):
    vmdl_path = str(tmp_path / "test_model.vmdl")

    # 1. Write dry-run
    preview = write_vmdl(vmdl_path, "models/props/test.fbx", [{"from": "m1.vmat", "to": "m2.vmat"}], dry_run=True)
    assert preview["dry_run"] is True
    assert not os.path.exists(vmdl_path)

    # 2. Write real
    result = write_vmdl(vmdl_path, "models/props/test.fbx", [{"from": "m1.vmat", "to": "m2.vmat"}], import_scale=2.0)
    assert os.path.exists(vmdl_path)
    assert result["dry_run"] is False

    # 3. Read
    data = read_vmdl(vmdl_path)
    assert len(data["meshes"]) == 1
    assert data["meshes"][0]["filename"] == "models/props/test.fbx"
    assert data["meshes"][0]["import_scale"] == 2.0
    assert len(data["material_remaps"]) == 1
    assert data["material_remaps"][0]["from"] == "m1.vmat"

    # 4. Edit dry-run
    edit_preview = edit_vmdl(vmdl_path, {"import_scale": 0.5}, dry_run=True)
    assert edit_preview["dry_run"] is True
    data_after_preview = read_vmdl(vmdl_path)
    assert data_after_preview["meshes"][0]["import_scale"] == 2.0

    # 5. Edit real
    edit_vmdl(vmdl_path, {"import_scale": 0.5, "material_remaps": [{"from": "a.vmat", "to": "b.vmat"}]})
    data_after = read_vmdl(vmdl_path)
    assert data_after["meshes"][0]["import_scale"] == 0.5
    assert data_after["material_remaps"][0]["from"] == "a.vmat"


def test_vmat_write_read_edit_roundtrip(tmp_path):
    vmat_path = str(tmp_path / "test_material.vmat")

    # 1. Write
    write_vmat(
        vmat_path,
        shader="csgo_environment.vfx",
        slots={"TextureColor": "materials/props/color.png"},
        parameters={"g_flRoughnessScale": 0.8},
        flags={"F_ALPHA_TEST": 1},
        system_attributes={"PhysicsSurfaceProperties": "wood"},
    )
    assert os.path.exists(vmat_path)

    # 2. Read
    data = read_vmat(vmat_path)
    assert data["shader"] == "csgo_environment.vfx"
    assert data["slots"]["TextureColor"] == "materials/props/color.png"
    assert "g_flRoughnessScale" in data["parameters"]
    assert data["system_attributes"].get("PhysicsSurfaceProperties") == "wood"

    # 3. Edit dry-run
    edit_vmat(vmat_path, set_slots={"TextureColor": "materials/props/new.png"}, dry_run=True)
    assert read_vmat(vmat_path)["slots"]["TextureColor"] == "materials/props/color.png"

    # 4. Edit real
    edit_vmat(vmat_path, set_slots={"TextureColor": "materials/props/new.png"}, set_parameters={"g_flRoughnessScale": 0.2})
    updated = read_vmat(vmat_path)
    assert updated["slots"]["TextureColor"] == "materials/props/new.png"
    assert updated["parameters"]["g_flRoughnessScale"] == "0.2"


def test_vtex_write_read_edit_roundtrip(tmp_path):
    vtex_path = str(tmp_path / "test_texture.vtex")

    # 1. Write
    write_vtex(vtex_path, input_file="materials/raw/texture.tga", output_format="BC7")
    assert os.path.exists(vtex_path)

    # 2. Read
    data = read_vtex(vtex_path)
    assert data["output_format"] == "BC7"
    assert len(data["input_textures"]) == 1
    assert data["input_textures"][0]["file_name"] == "materials/raw/texture.tga"

    # 3. Edit
    edit_vtex(vtex_path, {"input_file": "materials/raw/texture_v2.png", "output_format": "DXT1"})
    updated = read_vtex(vtex_path)
    assert updated["output_format"] == "DXT1"
    assert updated["input_textures"][0]["file_name"] == "materials/raw/texture_v2.png"


def test_vsmart_write_read_edit_and_evaluate(tmp_path):
    vsmart_path = str(tmp_path / "test_prop.vsmart")

    # 1. Write
    write_vsmart(
        vsmart_path,
        root_class="CSmartPropElement_Group",
        variables=[{"_class": "CSmartPropVariable_Float", "m_VariableName": "Length", "m_DefaultValue": 100.0}],
    )
    assert os.path.exists(vsmart_path)

    # 2. Read
    data = read_vsmart(vsmart_path)
    assert data["root_class"] == "CSmartPropElement_Group"
    assert len(data["variables"]) == 1
    assert data["variables"][0]["m_VariableName"] == "Length"

    # 3. Edit
    edit_vsmart(vsmart_path, {"set_variable": {"name": "Height", "value": 50.0}})
    updated = read_vsmart(vsmart_path)
    var_names = [v.get("m_VariableName") for v in updated["variables"]]
    assert "Height" in var_names

    # 4. Evaluate with mock bridge
    mock_bridge = MagicMock()
    mock_bridge.evaluate_smartprop.return_value = SmartPropEvaluation(
        models=(SmartPropModel(1, "models/props/test.vmdl", (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1), None, None),),
        widgets=(),
        diagnostics=(),
    )
    eval_result = evaluate_vsmart(mock_bridge, vsmart_path)
    assert eval_result["model_count"] == 1
    assert eval_result["models"][0]["model_name"] == "models/props/test.vmdl"


def test_vdata_write_read_edit_roundtrip(tmp_path):
    vdata_path = str(tmp_path / "test_props.vdata")

    # 1. Write
    write_vdata(vdata_path, {"grass_group": {"m_flDensity": 0.5}})
    assert os.path.exists(vdata_path)

    # 2. Read
    data = read_vdata(vdata_path)
    assert "grass_group" in data["entries"]
    assert data["entries"]["grass_group"]["m_flDensity"] == 0.5

    # 3. Edit
    edit_vdata(vdata_path, {"fern_group": {"m_flDensity": 0.2}}, remove_keys=["grass_group"])
    updated = read_vdata(vdata_path)
    assert "grass_group" not in updated["entries"]
    assert "fern_group" in updated["entries"]


def test_vsnap_write_read_generate_edit(tmp_path):
    vsnap_path = str(tmp_path / "test_particles.vsnap")

    mock_bridge = MagicMock()
    stream = SnapshotStream("Position", "position", ((0.0, 0.0, 0.0), (1.0, 2.0, 3.0)))
    mock_bridge.serialize_vsnap.return_value = "<!-- kv3 text vsnap -->\n{}"
    mock_bridge.read_vsnap.return_value = SnapshotDocument((stream,))
    mock_bridge.generate_vsnap.return_value = SnapshotDocument((stream,))
    mock_bridge.apply_vsnap_lighting.return_value = SnapshotDocument((stream,))

    # 1. Write
    write_vsnap(mock_bridge, vsnap_path, [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]])
    assert os.path.exists(vsnap_path)

    # 2. Read
    data = read_vsnap(mock_bridge, vsnap_path)
    assert data["stream_count"] == 1
    assert data["point_count"] == 2

    # 3. Generate
    gen_path = str(tmp_path / "gen_cube.vsnap")
    gen_res = generate_vsnap(mock_bridge, gen_path, primitive="cube", count=50)
    assert os.path.exists(gen_path)
    assert gen_res["primitive"] == "cube"

    # 4. Edit
    edit_res = edit_vsnap(mock_bridge, vsnap_path, lighting={"first_index": 0, "second_index": 1})
    assert "apply_lighting(0, 1)" in edit_res["modified_actions"]
