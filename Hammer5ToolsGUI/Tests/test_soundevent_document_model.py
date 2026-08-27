"""Characterization tests for the Qt-free SoundEvent document model."""

from __future__ import annotations

import subprocess
import sys

from gui.editors.soundevent_editor.document_model import SoundEventDocument


SAMPLE_VSNDEVTS = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
    // Global header comment

    // Base template comment
    "amb.base" = 
    {
        type = "csgo_mega"
        volume = 0.8
    }

    "amb.wind" = 
    {
        base = "amb.base"
        volume = 0.5
    }

    // Trailing footer comment
}
"""


def test_soundevent_document_from_text_parses_content():
    doc = SoundEventDocument.from_text(SAMPLE_VSNDEVTS)

    assert "amb.base" in doc.events
    assert "amb.wind" in doc.events
    assert doc.events["amb.base"]["volume"] == 0.8
    assert "Global header comment" in doc.file_header_comments
    assert "Base template comment" in doc.event_comments.get("amb.base", "")
    assert "Trailing footer comment" in doc.file_footer_comments


def test_soundevent_document_rename():
    doc = SoundEventDocument.from_text(SAMPLE_VSNDEVTS)
    doc.rename("amb.base", "amb.base_custom")

    assert "amb.base" not in doc.events
    assert "amb.base_custom" in doc.events
    assert "Base template comment" in doc.event_comments.get("amb.base_custom", "")
    assert "amb.base" not in doc.event_comments

    text = doc.to_text()
    assert '"amb.base_custom"' in text
    assert '"amb.base" =' not in text
    assert "Base template comment" in text

    reloaded = SoundEventDocument.from_text(text)
    assert "amb.base" not in reloaded.events
    assert "amb.base_custom" in reloaded.events


def test_soundevent_document_does_not_import_qt():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'Hammer5ToolsGUI');"
            " import gui.editors.soundevent_editor.document_model;"
            " print('PySide6' in sys.modules)",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
