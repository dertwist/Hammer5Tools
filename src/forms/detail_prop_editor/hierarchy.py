"""
Detail prop hierarchy tree.

Built on the same pieces as the SmartProp editor's hierarchy: HierarchyItemModel
items (icons, per-column colours, inline rename), a Label/Data/Class header, a
search bar that filters by label, alternating row colours and InternalMove drag
and drop.

The tree is the source of truth for the document — each item carries its dict in
Qt.UserRole, so reordering by drag and drop needs no separate bookkeeping.

Note that PySide marshals a dict through Qt.UserRole by value: item.data() hands
back a fresh copy every call, so mutating it in place is silently lost. Always
read with payload() and write back with set_payload().
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QAbstractItemView,
)

from src.widgets import HierarchyItemModel, on_three_hierarchyitem_clicked

from .schema import default_model, default_type

KIND_TYPE = "Detail Type"
KIND_MODEL = "Model"


class _DropSignalTree(QTreeWidget):
    """QTreeWidget that reports when an internal-move drop has completed."""

    dropped = Signal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.dropped.emit()


def payload(item) -> dict:
    """The item's dict. A copy — mutate it, then hand it to set_payload()."""
    if item is None:
        return {}
    return item.data(0, Qt.UserRole) or {}


def model_label(model: dict) -> str:
    import os
    name = (model.get("m_ModelName") or "").strip()
    return os.path.basename(name) if name else "<no model>"


def model_summary(model: dict) -> str:
    name = (model.get("m_ModelName") or "").strip()
    return name or "no model assigned"


class DetailPropTree(QWidget):
    """Search bar + hierarchy tree of detail types and their models."""

    selection_changed = Signal(object)   # the current QTreeWidgetItem, or None
    structure_changed = Signal()         # items added/removed/moved/renamed

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(
            lambda text: self.search_hierarchy(text, self.tree.invisibleRootItem())
        )
        layout.addWidget(self.search_bar)

        self.tree = _DropSignalTree()
        header = QTreeWidgetItem()
        header.setText(0, "Label")
        header.setText(1, "Data")
        header.setText(2, "Class")
        self.tree.setHeaderItem(header)
        self.tree.setColumnCount(3)
        self.tree.hideColumn(1)  # Hide Data column
        self.tree.setDragEnabled(True)
        self.tree.setDragDropOverwriteMode(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setUniformRowHeights(True)
        self.tree.setAllColumnsShowFocus(False)
        self.tree.setWordWrap(False)
        self.tree.header().setMinimumSectionSize(20)
        self.tree.header().setDefaultSectionSize(135)
        self.tree.header().setStretchLastSection(True)
        layout.addWidget(self.tree, 1)

        # Column 0 is the only editable column, same rule as SmartProp.
        self.tree.itemClicked.connect(on_three_hierarchyitem_clicked)
        self.tree.currentItemChanged.connect(
            lambda current, previous: self.selection_changed.emit(current)
        )
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.dropped.connect(self._on_dropped)

        self._loading = False

    # --------------------------------------------------------------- items --

    @staticmethod
    def _make_type_item(name: str, detail_type: dict) -> HierarchyItemModel:
        data = {k: v for k, v in detail_type.items() if k != "m_Models"}
        item = HierarchyItemModel(_name=name, _data=data, _class="Category", show_id=False)
        item.setText(2, KIND_TYPE)
        item.setText(1, f"density {data.get('m_flDensity', 1.0):g}")
        return item

    @staticmethod
    def _make_model_item(model: dict) -> HierarchyItemModel:
        item = HierarchyItemModel(_name=model_label(model), _data=model,
                                  _class="Model", show_id=False)
        item.setText(2, KIND_MODEL)
        item.setText(1, model_summary(model))
        item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled)   # models take no children
        return item

    def set_payload(self, item: QTreeWidgetItem, data: dict):
        """Store the item's dict without the write tripping the change handler."""
        if item is None:
            return
        self._loading = True
        item.setData(0, Qt.UserRole, data)
        self._loading = False

    def refresh_item(self, item: QTreeWidgetItem):
        """Re-render an item's Label/Data columns after its dict was edited."""
        if item is None:
            return
        data = payload(item)
        self._loading = True
        if self.kind_of(item) == KIND_MODEL:
            item.setText(0, model_label(data))
            item.setText(1, model_summary(data))
        else:
            item.setText(1, f"density {data.get('m_flDensity', 1.0):g}")
        self._loading = False

    # ---------------------------------------------------------------- load --

    def load(self, types: dict):
        self._loading = True
        self.tree.clear()
        for name, detail_type in types.items():
            type_item = self._make_type_item(name, detail_type)
            self.tree.addTopLevelItem(type_item)
            for model in detail_type.get("m_Models", []):
                type_item.addChild(self._make_model_item(model))
            type_item.setExpanded(True)
        self._loading = False
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        else:
            self.selection_changed.emit(None)

    def to_types(self) -> dict:
        """Rebuild the document dict from the tree, preserving visual order."""
        types = {}
        for i in range(self.tree.topLevelItemCount()):
            type_item = self.tree.topLevelItem(i)
            detail_type = dict(payload(type_item))
            detail_type["m_Models"] = [
                payload(type_item.child(j))
                for j in range(type_item.childCount())
            ]
            types[type_item.text(0)] = detail_type
        return types

    # ------------------------------------------------------------ mutation --

    @staticmethod
    def kind_of(item: QTreeWidgetItem) -> str:
        if item is None:
            return ""
        return KIND_TYPE if item.parent() is None else KIND_MODEL

    def type_item_for(self, item: QTreeWidgetItem) -> QTreeWidgetItem:
        if item is None:
            return None
        return item if item.parent() is None else item.parent()

    def unique_type_name(self, base: str) -> str:
        existing = {self.tree.topLevelItem(i).text(0)
                    for i in range(self.tree.topLevelItemCount())}
        if base not in existing:
            return base
        suffix = 2
        while f"{base}_{suffix}" in existing:
            suffix += 1
        return f"{base}_{suffix}"

    def add_type(self, name: str):
        detail_type = default_type()
        item = self._make_type_item(self.unique_type_name(name), detail_type)
        self._loading = True
        self.tree.addTopLevelItem(item)
        for model in detail_type["m_Models"]:
            item.addChild(self._make_model_item(model))
        item.setExpanded(True)
        self._loading = False
        self.tree.setCurrentItem(item)
        self.structure_changed.emit()

    def add_model(self):
        type_item = self.type_item_for(self.tree.currentItem())
        if type_item is None:
            return
        self._loading = True
        item = self._make_model_item(default_model())
        type_item.addChild(item)
        type_item.setExpanded(True)
        self._loading = False
        self.tree.setCurrentItem(item)
        self.structure_changed.emit()

    def duplicate_current(self):
        from src.common import fast_deepcopy
        current = self.tree.currentItem()
        if current is None:
            return
        self._loading = True
        if self.kind_of(current) == KIND_TYPE:
            models = [fast_deepcopy(payload(current.child(j)))
                      for j in range(current.childCount())]
            data = fast_deepcopy(payload(current))
            item = self._make_type_item(self.unique_type_name(current.text(0)),
                                        dict(data, m_Models=models))
            self.tree.insertTopLevelItem(self.tree.indexOfTopLevelItem(current) + 1, item)
            for model in models:
                item.addChild(self._make_model_item(model))
            item.setExpanded(True)
        else:
            parent = current.parent()
            model = fast_deepcopy(payload(current))
            item = self._make_model_item(model)
            parent.insertChild(parent.indexOfChild(current) + 1, item)
        self._loading = False
        self.tree.setCurrentItem(item)
        self.structure_changed.emit()

    def remove_current(self) -> str:
        """Delete the selected item. Returns an error message, or '' on success."""
        current = self.tree.currentItem()
        if current is None:
            return ""
        self._loading = True
        try:
            if self.kind_of(current) == KIND_TYPE:
                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(current))
            else:
                parent = current.parent()
                if parent.childCount() == 1:
                    return "A detail type must contain at least one model."
                parent.removeChild(current)
        finally:
            self._loading = False
        self.structure_changed.emit()
        return ""

    # -------------------------------------------------------------- events --

    def _on_item_changed(self, item, column):
        """Inline rename of a detail type; model labels come from their path."""
        if self._loading:
            return
        if column == 0 and self.kind_of(item) == KIND_TYPE:
            # Two types sharing a name would silently collapse into one on save.
            others = {self.tree.topLevelItem(i).text(0)
                      for i in range(self.tree.topLevelItemCount())
                      if self.tree.topLevelItem(i) is not item}
            name = item.text(0).strip() or "detail_type"
            if name in others:
                base, suffix = name, 2
                while name in others:
                    name, suffix = f"{base}_{suffix}", suffix + 1
            if name != item.text(0):
                self._loading = True
                item.setText(0, name)
                self._loading = False
            self.structure_changed.emit()

    def _on_dropped(self):
        """
        A drag-drop landed. Qt's InternalMove serialises items through mime data
        and rebuilds them as plain QTreeWidgetItems — the HierarchyItemModel
        subclass (and its icons) is lost, and nothing stops a model being dropped
        at top level or nested under another model. The Qt.UserRole payloads do
        survive, so read the structure back, normalise it, and rebuild the tree.
        """
        if self._loading:
            return
        types = self._harvest_after_drop()
        selected = self.tree.currentItem()
        selected_name = selected.text(0) if selected is not None else None
        self.load(types)
        if selected_name:
            matches = self.tree.findItems(selected_name, Qt.MatchExactly | Qt.MatchRecursive, 0)
            if matches:
                self.tree.setCurrentItem(matches[0])
        self.structure_changed.emit()

    def _harvest_after_drop(self) -> dict:
        """Read the post-drop tree into a well-formed {name: type} dict."""
        def models_under(item):
            """All model payloads at or below item, in visual order."""
            found = []
            data = payload(item)
            if "m_ModelName" in data:
                found.append(data)
            for j in range(item.childCount()):
                found.extend(models_under(item.child(j)))
            return found

        types = {}
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            data = payload(item)
            models = models_under(item)
            if "m_ModelName" in data:
                # A model dropped at top level becomes a type of its own.
                detail_type = default_type()
                detail_type["m_Models"] = models
            else:
                detail_type = dict(data)
                detail_type["m_Models"] = models or [default_model()]
            base = item.text(0) or "detail_type"
            name, suffix = base, 2
            while name in types:
                name, suffix = f"{base}_{suffix}", suffix + 1
            types[name] = detail_type
        return types

    # -------------------------------------------------------------- search --

    def search_hierarchy(self, filter_text, parent_item):
        self.filter_tree_item(parent_item, filter_text.lower(), True)

    def filter_tree_item(self, item, filter_text, is_root=False):
        if not isinstance(item, QTreeWidgetItem):
            return False

        item_visible = filter_text in item.text(0).lower()
        item.setHidden(False if is_root else not item_visible)

        any_child_visible = False
        for i in range(item.childCount()):
            if self.filter_tree_item(item.child(i), filter_text, False):
                any_child_visible = True

        if any_child_visible:
            item.setHidden(False)
            item.setExpanded(True)

        return item_visible or any_child_visible
