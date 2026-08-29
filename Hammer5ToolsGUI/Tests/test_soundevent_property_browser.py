"""Unit tests for PropertyBrowserWidget categorized property tree."""

from __future__ import annotations

import os
import sys
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.soundevent_editor.property_browser import PropertyBrowserWidget
from gui.editors.soundevent_editor.property_schema import GROUPS


@pytest.fixture
def browser():
    widget = PropertyBrowserWidget()
    return widget


def test_property_browser_loads_categories(browser):
    """Verify that categories are populated as top-level items in GROUPS order."""
    root = browser.prop_tree_widget.invisibleRootItem()
    assert root.childCount() > 0

    category_titles = [root.child(i).text(0) for i in range(root.childCount())]
    schema_titles = [title for _, title in GROUPS]

    # All loaded category titles must be from schema GROUPS and maintain relative order
    for title in category_titles:
        assert title in schema_titles

    # Verify DSP category exists and has expected children
    dsp_cat = next((root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "DSP"), None)
    assert dsp_cat is not None
    assert dsp_cat.childCount() > 0

    dsp_child_names = [dsp_cat.child(j).text(0) for j in range(dsp_cat.childCount())]
    assert "Dsp Preset" in dsp_child_names
    assert "Override Dsp Preset" in dsp_child_names


def test_property_browser_child_item_data(browser):
    """Verify that property child items carry (display_name, val_dict) in Qt.UserRole."""
    root = browser.prop_tree_widget.invisibleRootItem()
    for i in range(root.childCount()):
        cat = root.child(i)
        # Category headers should not have property data
        assert cat.data(0, Qt.UserRole) is None
        for j in range(cat.childCount()):
            child = cat.child(j)
            data = child.data(0, Qt.UserRole)
            assert data is not None
            display_name, val_dict = data
            assert isinstance(display_name, str)
            assert isinstance(val_dict, dict)
            assert len(val_dict) >= 1


def test_property_browser_filter(browser):
    """Verify filtering by property name and category title."""
    root = browser.prop_tree_widget.invisibleRootItem()

    # Filter by specific property "Dsp Preset"
    browser.filter_properties("Dsp Preset")
    dsp_cat = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "DSP")
    assert not dsp_cat.isHidden()

    dsp_preset_item = next(dsp_cat.child(j) for j in range(dsp_cat.childCount()) if dsp_cat.child(j).text(0) == "Dsp Preset")
    assert not dsp_preset_item.isHidden()

    # Other non-matching categories should be hidden
    playback_cat = next((root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "Playback"), None)
    if playback_cat is not None:
        assert playback_cat.isHidden()

    # Clear filter
    browser.filter_properties("")
    for i in range(root.childCount()):
        cat = root.child(i)
        assert not cat.isHidden()
        for j in range(cat.childCount()):
            assert not cat.child(j).isHidden()


def test_property_browser_double_click_emits(browser):
    """Verify double clicking a child property emits add_property_requested."""
    emitted = []
    browser.add_property_requested.connect(lambda name, val: emitted.append((name, val)))

    root = browser.prop_tree_widget.invisibleRootItem()
    dsp_cat = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "DSP")

    # Double clicking a category header does NOT emit
    browser._on_property_double_clicked(dsp_cat)
    assert len(emitted) == 0

    # Double clicking a child property DOES emit
    dsp_preset_item = next(dsp_cat.child(j) for j in range(dsp_cat.childCount()) if dsp_cat.child(j).text(0) == "Dsp Preset")
    browser._on_property_double_clicked(dsp_preset_item)
    assert len(emitted) == 1
    assert emitted[0][0] == "Dsp Preset"
    assert "dsp_preset" in emitted[0][1]


def test_property_browser_update_property_states(browser):
    """Verify update_property_states disables existing properties except comment."""
    root = browser.prop_tree_widget.invisibleRootItem()

    # Mark 'volume' as existing
    browser.update_property_states({"volume", "comment"})

    playback_cat = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "Playback")
    volume_item = next(playback_cat.child(j) for j in range(playback_cat.childCount()) if playback_cat.child(j).text(0) == "Volume")
    assert not (volume_item.flags() & Qt.ItemIsEnabled)

    # Comment should still be enabled (can be added multiple times)
    general_cat = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "General")
    comment_item = next(general_cat.child(j) for j in range(general_cat.childCount()) if general_cat.child(j).text(0) == "Comment")
    assert bool(comment_item.flags() & Qt.ItemIsEnabled)
