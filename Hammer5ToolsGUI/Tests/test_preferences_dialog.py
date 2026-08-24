"""
Unit tests for PreferencesDialog tab structure and Appearance brightness option placement.
"""

import os
import sys
import pytest
from PySide6.QtWidgets import QApplication

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Ensure QApplication exists for Qt widget tests
app = QApplication.instance() or QApplication(sys.argv)

from hammer5tools_gui.settings.main import PreferencesDialog


def test_preferences_dialog_tabs():
    """Verify that Appearance tab has been moved to General tab and is no longer a separate tab."""
    dialog = PreferencesDialog(app_version="1.0.0")
    
    # Check tab count and tab names
    tab_widget = dialog.tabWidget
    tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
    
    assert "Appearance" not in tab_names
    assert tab_names == ["General", "SmartProp Editor", "AssetGroupMaker", "SoundEventEditor"]
    
    # Check that brightness combobox exists on dialog and has expected items
    assert hasattr(dialog, "appearance_combo_brightness")
    combo = dialog.appearance_combo_brightness
    assert combo.count() == 3
    assert combo.itemText(0) == "1 · Dark"
    assert combo.itemData(0) == 1
    assert combo.itemText(1) == "2 · Standard"
    assert combo.itemData(1) == 2
    assert combo.itemText(2) == "3 · Bright"
    assert combo.itemData(2) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
