"""
ComponentRef — component reference data model for SmartProp properties.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_CONTAINER = {
    "modifier": "m_Modifiers",
    "criterion": "m_SelectionCriteria",
    "selection_criteria": "m_SelectionCriteria",
}
_USER_ROLE = 256

# 'm_Modifiers[2].m_flAmount' / 'm_SelectionCriteria[0]' — same shape document.py parses.
_DIFF_KEY_RE = re.compile(r"^(m_Modifiers|m_SelectionCriteria)\[(\d+)\](?:\.(.+))?$")


@dataclass(frozen=True)
class ComponentRef:
    """Identifies one editable dict: the element itself, or one of its modifiers/criteria."""

    item: Any            # QTreeWidgetItem / HierarchyItemModel
    kind: str            # 'element' | 'modifier' | 'criterion'
    index: int = -1      # -1 for 'element'

    def container(self) -> str | None:
        return _CONTAINER.get(self.kind)

    def target(self, element_data: dict) -> dict | None:
        """The sub-dict this ref points at, inside ``element_data``. None if out of range."""
        if self.kind == "element":
            return element_data
        arr = element_data.get(self.container()) or []
        if 0 <= self.index < len(arr) and isinstance(arr[self.index], dict):
            return arr[self.index]
        return None

    def prop_class(self) -> str:
        if self.item is None:
            return ""
        node = getattr(self.item, "smartprop_node", None)
        data = node.data if node is not None else self.item.data(0, _USER_ROLE)
        target = self.target(data) if isinstance(data, dict) else None
        raw = (target or {}).get("_class", "") or ""
        return raw.split("_", 1)[-1] if raw else ""

    def diff_key(self, field: str) -> str:
        """Discriminator matching PropertySnapshotCommand._changed_keys output."""
        if self.kind == "element":
            return field
        return f"{self.container()}[{self.index}].{field}"
