"""
AbstractPropertyList — common interface for SmartProp property-list backends.

SmartPropPropertyPanel (panel.py) only ever calls two methods on Section 2:

    set_components(refs)              – point the list at selected components
    apply_external_data(item, data)   – forward an undo/redo update

This base class documents that contract.  Both the new treeview backend
(PropertyPanel in view.py) and the legacy PropertyFrame backend
(LegacyPropertyList in legacy_property_list.py) inherit from it so
panel.py can treat them identically.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget


class AbstractPropertyList(QWidget):
    """Minimal interface for Section 2 (Property List) of SmartPropPropertyPanel."""

    def set_components(self, refs: list) -> None:
        """Point the list at the given ComponentRef objects.

        Called whenever the component-selector (Section 1) changes its
        selection.  ``refs`` is a (possibly empty) list of ComponentRef.
        """
        raise NotImplementedError

    def apply_external_data(self, item, new_data: dict, changed_keys=()) -> None:
        """Forward an externally-produced data update (e.g. undo / redo).

        ``item``        – QTreeWidgetItem whose data was just changed.
        ``new_data``    – the new element dict already written to the item.
        ``changed_keys``– iterable of diff-key strings; may be empty.
        """
        raise NotImplementedError
