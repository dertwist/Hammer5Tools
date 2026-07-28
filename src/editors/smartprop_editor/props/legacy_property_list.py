"""
LegacyPropertyList — Section 2 backend that uses the old PropertyFrame system.

This wraps the original form-based property widgets (PropertyFrame from
property_frame.py) behind the AbstractPropertyList interface so
SmartPropPropertyPanel can swap it in place of the new treeview backend.

Architecture
------------
Section 1 (ComponentList) already owns identity, enable/disable, add,
paste, delete, copy and reordering for every component (the element
itself, each modifier, each selection criterion). This list only has to
show the fields of whichever component(s) are currently selected there —
one flat, header-less PropertyFrame per selected ComponentRef:

    LegacyPropertyList (QScrollArea)
    └── _container (QWidget)
        └── _container_layout (QVBoxLayout)
            └── PropertyFrame per selected ref (header hidden)

Edits are written straight back into the tree item's full data dict via
the ref (read old, mutate a deep copy, setData, push PropertySnapshotCommand)
rather than through document.update_tree_item_value, which relied on
scanning three separate layouts that no longer coexist under this design.
"""

from __future__ import annotations

from src.common import fast_deepcopy
from src.editors.smartprop_editor.props.property_list_base import AbstractPropertyList
from src.editors.smartprop_editor.props.model import ComponentRef

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class LegacyPropertyList(AbstractPropertyList):
    """Section 2 backend — old PropertyFrame-based property list."""

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document

        # Outer scroll area
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background-color: #1C1C1C; border: none; }
            QScrollBar:vertical { width: 8px; background: #1C1C1C; }
            QScrollBar::handle:vertical { background: #444; border-radius: 3px; }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background-color: #1C1C1C;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        # Active PropertyFrame widgets, one per currently-selected ref
        self._frames: list = []
        self._refs: list[ComponentRef] = []

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _clear_frames(self):
        while self._container_layout.count():
            item = self._container_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                try:
                    if hasattr(w, "cancel_worker"):
                        w.cancel_worker()
                    w.hide()
                    w.deleteLater()
                except Exception:
                    pass
        self._frames.clear()

    def _make_frame(self, value: dict, group_layout):
        """Create a single header-less PropertyFrame with all required dependencies."""
        try:
            from src.editors.smartprop_editor.property_frame import PropertyFrame

            frame = PropertyFrame(
                value=fast_deepcopy(value),
                widget_list=group_layout,
                variables_scrollArea=(
                    self.document.variable_viewport.ui.variables_scrollArea
                    if self.document
                    else None
                ),
                # Section 1 already shows class name/id/enable/delete/copy for
                # every component, so every frame here uses the same chrome-free
                # "element" mode and has its header row hidden below.
                element=True,
                tree_hierarchy=(
                    self.document.ui.tree_hierarchy_widget if self.document else None
                ),
                element_id_generator=(
                    self.document.element_id_generator if self.document else None
                ),
                parent=self._container,
            )
            frame.ui.frame.setVisible(False)
            return frame
        except Exception as exc:
            print(f"[LegacyPropertyList] Could not create PropertyFrame: {exc}")
            return None

    # ── AbstractPropertyList interface ─────────────────────────────────────────

    def set_components(self, refs: list) -> None:
        """Rebuild the flat PropertyFrame list from the given (selected) ComponentRefs."""
        self._refs = list(refs)
        self._clear_frames()

        for ref in self._refs:
            data = ref.item.data(0, Qt.UserRole) if ref.item is not None else None
            if not isinstance(data, dict):
                continue
            target = ref.target(data)
            if not isinstance(target, dict):
                continue

            value = fast_deepcopy(target)
            if ref.kind == "element":
                # Modifiers/criteria are separate components, not fields.
                value.pop("m_Modifiers", None)
                value.pop("m_SelectionCriteria", None)

            frame = self._make_frame(value, group_layout=self._container_layout)
            if frame is None:
                continue
            frame.edited.connect(lambda r=ref, f=frame: self._commit_frame(r, f))
            if self.document:
                try:
                    frame.slider_pressed.connect(self.document._on_slider_started)
                    frame.committed.connect(self.document._on_slider_committed)
                except Exception:
                    pass
            self._container_layout.addWidget(frame)
            self._frames.append(frame)

        if self._frames:
            self._container_layout.addStretch(1)

    def _commit_frame(self, ref: ComponentRef, frame) -> None:
        """Write frame.value back into the item's full data dict and push undo."""
        if self.document is None or ref.item is None or frame.value is None:
            return
        item = ref.item
        old_data = fast_deepcopy(item.data(0, Qt.UserRole))
        if not isinstance(old_data, dict):
            return
        new_data = fast_deepcopy(old_data)

        if ref.kind == "element":
            # Preserve the sibling component lists the element frame doesn't edit.
            modifiers = new_data.get("m_Modifiers")
            criteria = new_data.get("m_SelectionCriteria")
            new_data = dict(frame.value)
            if modifiers is not None:
                new_data["m_Modifiers"] = modifiers
            if criteria is not None:
                new_data["m_SelectionCriteria"] = criteria
        else:
            container_key = ref.container()
            arr = new_data.setdefault(container_key, [])
            if not (0 <= ref.index < len(arr)):
                return
            arr[ref.index] = frame.value

        if new_data == old_data:
            return

        item.setData(0, Qt.UserRole, new_data)
        self.document._modified = True
        self.document._edited.emit()

        stack = getattr(self.document, "undo_stack", None)
        if stack is not None and not getattr(self.document, "_property_undo_guard", 0):
            from src.editors.smartprop_editor.commands import PropertySnapshotCommand
            stack.push(PropertySnapshotCommand(self.document, item, old_data, new_data))

    def apply_external_data(self, item, new_data: dict, changed_keys=()) -> None:
        """Rebuild entirely on external update (undo/redo) — legacy frames have
        no incremental update path at the panel level."""
        if self._refs and self._refs[0].item is item:
            self.set_components(self._refs)
