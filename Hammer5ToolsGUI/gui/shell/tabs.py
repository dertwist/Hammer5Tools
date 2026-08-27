"""Tab placement for the main window's tool tabs."""


def insert_tab_after(tabs, anchor, page, icon, label) -> int:
    """Put `page` directly after `anchor`, appending if the anchor is missing.

    Tabs built in code have to land next to the Designer-authored tab they
    belong with, and their index is only knowable at runtime.
    """
    anchor_index = tabs.indexOf(anchor)
    position = tabs.count() if anchor_index < 0 else anchor_index + 1
    return tabs.insertTab(position, page, icon, label)
