"""Selection state for the asset-selection tree.

The tree used to *be* the model: what was ticked, what the filter hid, and
what a folder's tri-state should look like were all read back out of
QTreeWidgetItems, guarded by an `_updating` re-entrancy flag. That made the
rules -- which are ordinary set arithmetic -- untestable without a GUI, and
subtly coupled: a folder's tick, for instance, must skip rows the filter is
hiding, because the user cannot see them and did not mean to include them.

Those rules live here, in plain Python. The widget renders this and reports
clicks back to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: A folder's tick state, derived from the visible leaves beneath it.
UNCHECKED, CHECKED, PARTIAL = "unchecked", "checked", "partial"


@dataclass
class Node:
    """One row: a folder (no key) or an asset (a key)."""

    name: str
    path: str
    key: str | None = None
    children: list = field(default_factory=list)
    checked: bool = False
    visible: bool = True

    @property
    def is_leaf(self) -> bool:
        return self.key is not None


class AssetTreeModel:
    """The asset paths as a tree, plus which of them are ticked and shown."""

    def __init__(self, asset_keys, preselected=()):
        self.roots: list[Node] = []
        self.leaves: list[Node] = []
        self._folders: dict[str, Node] = {}
        preselected = set(preselected)

        for key in sorted(asset_keys):
            parts = key.replace("\\", "/").split("/")
            parent = None
            for depth, part in enumerate(parts[:-1]):
                prefix = "/".join(parts[:depth + 1])
                folder = self._folders.get(prefix)
                if folder is None:
                    folder = Node(name=part, path=prefix)
                    self._folders[prefix] = folder
                    (parent.children if parent else self.roots).append(folder)
                parent = folder

            leaf = Node(name=parts[-1], path=key, key=key, checked=key in preselected)
            (parent.children if parent else self.roots).append(leaf)
            self.leaves.append(leaf)

    # ── Selection ────────────────────────────────────────────────────────
    def set_checked(self, node: Node, checked: bool) -> None:
        """Tick a row. A folder reaches every visible row beneath it."""
        if node.is_leaf:
            node.checked = checked
            return
        for child in node.children:
            if child.visible:
                self.set_checked(child, checked)

    def set_all(self, checked: bool) -> None:
        for leaf in self.leaves:
            if leaf.visible:
                leaf.checked = checked

    def state_of(self, node: Node) -> str:
        """checked / unchecked / partial, from the visible leaves below."""
        if node.is_leaf:
            return CHECKED if node.checked else UNCHECKED

        states = {self.state_of(child) for child in node.children if child.visible}
        states.discard(None)
        if not states or states == {UNCHECKED}:
            return UNCHECKED
        if states == {CHECKED}:
            return CHECKED
        return PARTIAL

    def checked_keys(self) -> set:
        return {leaf.key for leaf in self.leaves if leaf.checked}

    # ── Filtering ────────────────────────────────────────────────────────
    def apply_filter(self, needle: str, is_allowed) -> None:
        """Hide leaves that fail the name filter or the type filter, then hide
        every folder left with nothing visible under it."""
        needle = needle.strip().lower()
        for leaf in self.leaves:
            matches_name = not needle or needle in leaf.name.lower()
            leaf.visible = matches_name and is_allowed(leaf.key)
        for root in self.roots:
            self._prune(root)

    def _prune(self, node: Node) -> bool:
        if node.is_leaf:
            return node.visible
        # Evaluate every child: visibility is being assigned, not just read.
        node.visible = any([self._prune(child) for child in node.children])
        return node.visible
