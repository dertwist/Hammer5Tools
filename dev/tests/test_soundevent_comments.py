"""
Unit and integration tests for SoundEvent Editor comment preservation and editor_info handling.
Tests extracting, round-tripping, and manipulating various KV3 comment structures using relative asset paths.
"""

import os
import sys
import tempfile
import pytest

# Ensure repository root and src directory are in sys.path (relative to this file)
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_dir = os.path.join(repo_root, "src")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.common import Kv3ToJson
from src.editors.soundevent_editor.comment_handler import (
    extract_vsndevts_comments,
    serialize_vsndevts_with_comments,
)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
CASE_01_PATH = os.path.join(ASSETS_DIR, "inlinecomments_case_01.vsndevts")
CASE_02_PATH = os.path.join(ASSETS_DIR, "inlinecomments_case_02.vsndevts")


@pytest.fixture(scope="session")
def qapp():
    """Ensure a QApplication instance is running for Qt widget tests."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_asset_files_exist():
    """Verify that the test asset files exist at relative paths."""
    assert os.path.exists(CASE_01_PATH), f"Case 01 asset not found at {CASE_01_PATH}"
    assert os.path.exists(CASE_02_PATH), f"Case 02 asset not found at {CASE_02_PATH}"


# ──────────────────────────────────────────────────────────────────────────────
#  Case 1: inlinecomments_case_01.vsndevts
# ──────────────────────────────────────────────────────────────────────────────

def test_inlinecomments_case_01_extraction_and_roundtrip():
    """Test loading and roundtripping inlinecomments_case_01.vsndevts."""
    with open(CASE_01_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    hdr, ev_comments, ftr = extract_vsndevts_comments(content)
    parsed = Kv3ToJson(content)

    assert len(hdr) > 0, "Header comments should be extracted"
    assert "// For soundevents to compile into the addon" in hdr
    assert "BASE SOUNDEVENT TEMPLATES" in ev_comments.get("amb.base", "")

    serialized = serialize_vsndevts_with_comments(
        parsed,
        file_header_comments=hdr,
        event_comments=ev_comments,
        file_footer_comments=ftr,
        editor_info_data={"name": "Hammer 5 Tools", "version": "5.6.4"},
    )

    assert "// For soundevents to compile into the addon" in serialized
    assert "BASE SOUNDEVENT TEMPLATES" in serialized
    assert "editor_info =" in serialized

    reparsed = Kv3ToJson(serialized)
    for event_name, event_data in parsed.items():
        assert reparsed.get(event_name) == event_data, f"Mismatch in event {event_name}"


# ──────────────────────────────────────────────────────────────────────────────
#  Case 2: inlinecomments_case_02.vsndevts (inline comments within and between events)
# ──────────────────────────────────────────────────────────────────────────────

def test_inlinecomments_case_02_extraction_and_roundtrip():
    """Test loading and roundtripping inlinecomments_case_02.vsndevts."""
    with open(CASE_02_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    hdr, ev_comments, ftr = extract_vsndevts_comments(content)
    parsed = Kv3ToJson(content)

    assert len(hdr) > 0, "Header comments should be extracted"
    assert "// For soundevents to compile into the addon" in hdr
    assert "BASE SOUNDEVENT TEMPLATES" in ev_comments.get("amb.base", "")
    assert "//reverb_10_warehouse" in ev_comments.get("amb.base", "")

    serialized = serialize_vsndevts_with_comments(
        parsed,
        file_header_comments=hdr,
        event_comments=ev_comments,
        file_footer_comments=ftr,
        editor_info_data={"name": "Hammer 5 Tools", "version": "5.6.4"},
    )

    assert "// For soundevents to compile into the addon" in serialized
    assert "BASE SOUNDEVENT TEMPLATES" in serialized
    assert "editor_info =" in serialized

    reparsed = Kv3ToJson(serialized)
    for event_name, event_data in parsed.items():
        assert reparsed.get(event_name) == event_data, f"Mismatch in event {event_name}"


# ──────────────────────────────────────────────────────────────────────────────
#  Case 3: Comment directly above editor_info (user case)
# ──────────────────────────────────────────────────────────────────────────────

def test_comment_directly_above_editor_info():
    """Test preserving // comment positioned directly above editor_info block."""
    raw = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
//asdfas fasd
	editor_info = 
	{
		name = "Hammer 5 Tools"
		version = "5.6.4"
		m_nElementID = 108
	}
	"ambient_example.outdoors" = 
	{
		base = "amb.soundscapeParent.base"
	}
}
"""
    hdr, ev_comments, ftr = extract_vsndevts_comments(raw)
    parsed = Kv3ToJson(raw)
    ed_data = parsed.get("editor_info")

    assert ev_comments.get("editor_info") == "//asdfas fasd"

    serialized = serialize_vsndevts_with_comments(
        parsed,
        file_header_comments=hdr,
        event_comments=ev_comments,
        file_footer_comments=ftr,
        editor_info_data=ed_data,
    )

    assert "//asdfas fasd" in serialized
    assert "editor_info =" in serialized
    assert 'name = "Hammer 5 Tools"' in serialized
    assert 'version = "5.6.4"' in serialized
    assert "m_nElementID = 108" in serialized
    assert "ambient_example.outdoors" in serialized

    reparsed = Kv3ToJson(serialized)
    assert reparsed == parsed


# ──────────────────────────────────────────────────────────────────────────────
#  Case 4: Global header comment + editor_info comment + per-event doc comments
# ──────────────────────────────────────────────────────────────────────────────

def test_multiblock_header_and_event_comments():
    """Test file with global header, editor_info comment, and event doc-comments."""
    raw = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
// ==========================================
// Map Soundevents Addon File
// Generated for Counter-Strike 2
// ==========================================

// Tool Metadata
	editor_info = 
	{
		name = "Hammer 5 Tools"
		version = "5.6.4"
	}

// Ambient outdoors parent soundscape
	"ambient_example.outdoors" = 
	{
		base = "amb.soundscapeParent.base"
	}

// Ambient wind background loop
	"ambient_example.wind" = 
	{
		base = "amb.looping.stereo.base"
		volume = 0.5
	}
}
"""
    hdr, ev_comments, ftr = extract_vsndevts_comments(raw)
    parsed = Kv3ToJson(raw)

    assert "Map Soundevents Addon File" in hdr
    assert ev_comments.get("editor_info") == "// Tool Metadata"
    assert "Ambient outdoors parent soundscape" in ev_comments.get("ambient_example.outdoors", "")
    assert "Ambient wind background loop" in ev_comments.get("ambient_example.wind", "")

    serialized = serialize_vsndevts_with_comments(
        parsed,
        file_header_comments=hdr,
        event_comments=ev_comments,
        file_footer_comments=ftr,
        editor_info_data=parsed.get("editor_info"),
    )

    assert "Map Soundevents Addon File" in serialized
    assert "// Tool Metadata" in serialized
    assert "Ambient outdoors parent soundscape" in serialized
    assert "Ambient wind background loop" in serialized

    reparsed = Kv3ToJson(serialized)
    assert reparsed == parsed


# ──────────────────────────────────────────────────────────────────────────────
#  Case 5: Comments with special characters (quotes, URLs, brackets, braces)
# ──────────────────────────────────────────────────────────────────────────────

def test_comments_with_special_characters():
    """Test comments containing quotes, brackets, braces, and URLs."""
    raw = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
// Reference: https://developer.valvesoftware.com/wiki/Soundevents
// Note: [0, 0, 0] is the origin, "amb.base" is the fallback {type = "csgo_mega"}

	editor_info = 
	{
		name = "Hammer 5 Tools"
		version = "5.6.4"
	}

// Event doc: uses "amb.base" with custom curve [0.0, 1.0] -> {fade = 0.5}
	"test_special" = 
	{
		type = "csgo_mega"
		volume = 1.0
	}
}
"""
    hdr, ev_comments, ftr = extract_vsndevts_comments(raw)
    parsed = Kv3ToJson(raw)

    assert "https://developer.valvesoftware.com/wiki/Soundevents" in hdr
    assert 'uses "amb.base" with custom curve' in ev_comments.get("test_special", "")

    serialized = serialize_vsndevts_with_comments(
        parsed,
        file_header_comments=hdr,
        event_comments=ev_comments,
        file_footer_comments=ftr,
        editor_info_data=parsed.get("editor_info"),
    )

    assert "https://developer.valvesoftware.com/wiki/Soundevents" in serialized
    assert 'uses "amb.base" with custom curve' in serialized

    reparsed = Kv3ToJson(serialized)
    assert reparsed == parsed


# ──────────────────────────────────────────────────────────────────────────────
#  Case 6: Footer comments at the end of the file
# ──────────────────────────────────────────────────────────────────────────────

def test_footer_comments_preservation():
    """Test preserving comments at the end of the file before closing brace."""
    raw = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
	editor_info = 
	{
		name = "Hammer 5 Tools"
		version = "5.6.4"
	}
	"sound_1" = 
	{
		type = "csgo_mega"
	}

// End of soundevents file
// Footer note line 2
}
"""
    hdr, ev_comments, ftr = extract_vsndevts_comments(raw)
    parsed = Kv3ToJson(raw)

    assert "End of soundevents file" in ftr
    assert "Footer note line 2" in ftr

    serialized = serialize_vsndevts_with_comments(
        parsed,
        file_header_comments=hdr,
        event_comments=ev_comments,
        file_footer_comments=ftr,
        editor_info_data=parsed.get("editor_info"),
    )

    assert "End of soundevents file" in serialized
    assert "Footer note line 2" in serialized

    reparsed = Kv3ToJson(serialized)
    assert reparsed == parsed


# ──────────────────────────────────────────────────────────────────────────────
#  Case 7: Event mutations (rename, add, delete)
# ──────────────────────────────────────────────────────────────────────────────

def test_event_modifications_with_comments():
    """Test adding, deleting, and renaming events while preserving associated comments."""
    sample_kv3 = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
// Global Header
// Version 1.0

// Tool info
	editor_info = 
	{
		name = "Hammer 5 Tools"
		version = "5.6.4"
	}

// Soundevent 1 documentation
	sound_1 = 
	{
		type = "csgo_mega"
		volume = 1.0
	}

// Soundevent 2 documentation
	sound_2 = 
	{
		type = "csgo_mega"
		volume = 0.5
	}
}
"""
    hdr, ev_comments, ftr = extract_vsndevts_comments(sample_kv3)
    data = Kv3ToJson(sample_kv3)

    assert "sound_1" in ev_comments
    assert "sound_2" in ev_comments

    # Rename sound_1 -> sound_1_renamed
    data["sound_1_renamed"] = data.pop("sound_1")
    ev_comments["sound_1_renamed"] = ev_comments.pop("sound_1")

    # Add sound_3
    data["sound_3"] = {"type": "csgo_mega", "volume": 0.8}

    # Delete sound_2
    del data["sound_2"]
    del ev_comments["sound_2"]

    serialized = serialize_vsndevts_with_comments(
        data,
        file_header_comments=hdr,
        event_comments=ev_comments,
        file_footer_comments=ftr,
        editor_info_data=data.get("editor_info"),
    )

    assert "// Global Header" in serialized
    assert "// Soundevent 1 documentation" in serialized
    assert "sound_1_renamed" in serialized
    assert "sound_3" in serialized
    assert "sound_2" not in serialized
    assert "// Soundevent 2 documentation" not in serialized

    reparsed = Kv3ToJson(serialized)
    assert reparsed == data


# ──────────────────────────────────────────────────────────────────────────────
#  Case 8: QTreeWidget Load and Save Integration with Case 01 & Case 02
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("asset_path", [CASE_01_PATH, CASE_02_PATH])
def test_load_and_save_integration_with_assets(qapp, asset_path):
    """Test LoadSoundEvents and SaveSoundEvents with real test assets."""
    from PySide6.QtWidgets import QTreeWidget
    from src.editors.soundevent_editor.main import LoadSoundEvents, SaveSoundEvents

    tree = QTreeWidget()
    LoadSoundEvents(tree=tree, path=asset_path)

    assert tree.invisibleRootItem().childCount() > 0
    assert hasattr(tree, "file_header_comments")
    assert "// For soundevents to compile into the addon" in tree.file_header_comments

    with tempfile.NamedTemporaryFile(suffix=".vsndevts", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        SaveSoundEvents(tree=tree, path=tmp_path)

        with open(tmp_path, "r", encoding="utf-8") as f:
            saved_content = f.read()

        assert "// For soundevents to compile into the addon" in saved_content
        assert "BASE SOUNDEVENT TEMPLATES" in saved_content
        assert "editor_info =" in saved_content

        original_data = Kv3ToJson(open(asset_path, "r", encoding="utf-8").read())
        saved_data = Kv3ToJson(saved_content)

        assert "editor_info" in saved_data
        for k, v in original_data.items():
            assert saved_data[k] == v
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
