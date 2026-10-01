"""Missing optional Smart Prop configuration must not block tool startup."""

from unittest.mock import Mock

import pytest

from gui.other import assettypes


@pytest.fixture
def assettypes_path(tmp_path, monkeypatch):
    monkeypatch.setattr(assettypes, "get_cs2_path", lambda: str(tmp_path))
    return tmp_path / "game" / "bin" / assettypes.ASSETTYPES_FILENAME


def test_missing_assettypes_skips_setup_and_configuration_check(assettypes_path, monkeypatch, caplog):
    write = Mock()
    warning = Mock()
    monkeypatch.setattr(assettypes, "write_assettypes", write)
    monkeypatch.setattr(assettypes, "show_vsmart_warning", warning)

    assettypes.ensure_vsmart_configured()
    assettypes.check_vsmart_configuration()

    write.assert_not_called()
    warning.assert_not_called()
    assert not assettypes_path.exists()
    assert str(assettypes_path) in caplog.text
    assert "Skipping Smart Prop configuration" in caplog.text


def test_setup_retries_after_missing_file_is_restored(assettypes_path):
    assettypes.ensure_vsmart_configured()
    assettypes_path.parent.mkdir(parents=True)
    original = {"assettypes": {"existing_asset": {"m_Ext": "example"}}}
    assettypes.keyvalues3.write(original, str(assettypes_path))

    assettypes.ensure_vsmart_configured()

    data = assettypes.keyvalues3.read(str(assettypes_path)).value
    assert data["assettypes"]["existing_asset"] == original["assettypes"]["existing_asset"]
    assert data["assettypes"]["smart_prop"]["m_Ext"] == "vsmart"
    assert assettypes.is_editor_info_processed(data)


@pytest.mark.parametrize("error", [PermissionError("Access denied"), ValueError("Invalid KV3")])
def test_other_read_failures_remain_visible(assettypes_path, monkeypatch, error):
    monkeypatch.setattr(assettypes.keyvalues3, "read", Mock(side_effect=error))

    with pytest.raises(ValueError, match="Failed to read assettypes"):
        assettypes.ensure_vsmart_configured()
