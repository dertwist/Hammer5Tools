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


def _content_hash(target: dict) -> int:
    """Stable content fingerprint of a property dict.

    Uses repr() of each value so nested lists/dicts (KV3 vectors, modifiers)
    contribute to the hash. Cheap relative to a full widget rebuild; stable
    across repeated QTreeWidgetItem.data() reads (which return fresh wrappers
    around equal contents).
    """
    return hash(tuple(sorted((k, repr(v)) for k, v in target.items())))


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
        # Identity signature of the last set_components() build, so reselecting
        # the exact same component(s) can short-circuit a needless rebuild.
        # None = "no previous build" / "invalidate".
        self._last_build_sig: tuple | None = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _clear_frames(self):
        # Frames are returned to PropertyWidgetPool when the backend supports it;
        # here we always owned them directly, so deleteLater is correct. Cancel
        # any in-flight data worker first so it can't populate a dead frame.
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
        self._last_build_sig = None

    def _make_frame(self, value: dict, group_layout):
        """Create a single header-less PropertyFrame with all required dependencies.

        ``value`` is expected to already be an owned deep copy produced by the
        caller (set_components), so it is passed straight through — PropertyFrame
        treats its ``value`` as owned and mutates it in place.
        """
        try:
            from src.editors.smartprop_editor.property_frame import PropertyFrame

            frame = PropertyFrame(
                value=value,
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
        """Rebuild the flat PropertyFrame list from the given (selected) ComponentRefs.

        Short-circuits when the selection resolves to the same component identity
        as the last build *and* the underlying tree-item data dicts have not been
        replaced — reselecting the same element then costs ~nothing instead of a
        full teardown + worker + widget reconstruction.
        """
        self._refs = list(refs)

        # ── Identity short-circuit ───────────────────────────────────────
        # Build a signature keyed on (item, kind, index, id(target_dict)). The
        # id() check catches the case where undo/redo swapped in a fresh dict
        # under the same item: the signature changes and we rebuild as before.
        sig = self._build_signature(self._refs)
        if sig is not None and sig == self._last_build_sig and self._frames:
            return  # nothing to do — same selection, same backing data

        self._clear_frames()
        self._last_build_sig = sig

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

    def _build_signature(self, refs: list) -> tuple | None:
        """Cheap identity tuple for the current selection.

        Returns None if the selection can't be resolved (so the caller rebuilds).

        We cannot use id() of the target dict: PySide6 returns a fresh Python
        wrapper around the QVariant on every QTreeWidgetItem.data() call, so the
        id() differs even when the stored dict is unchanged. Instead we hash the
        target dict's contents. The fingerprint costs ~tens of microseconds —
        roughly one deep copy — but lets us skip an entire teardown+worker+widget
        rebuild when the selection is genuinely unchanged, which is the common
        case for reselecting the same element or hopping selection back and forth.
        """
        if not refs:
            return ()
        sig = []
        for ref in refs:
            if ref.item is None:
                return None
            data = ref.item.data(0, Qt.UserRole)
            if not isinstance(data, dict):
                return None
            target = ref.target(data)
            if not isinstance(target, dict):
                return None
            sig.append((id(ref.item), ref.kind, ref.index, _content_hash(target)))
        return tuple(sig)

    def _commit_frame(self, ref: ComponentRef, frame) -> None:
        """Write frame.value back into the item's full data dict and push undo."""
        if self.document is None or ref.item is None or frame.value is None:
            return
        item = ref.item
        old_data = fast_deepcopy(item.data(0, Qt.UserRole))
        if not isinstance(old_data, dict):
            return

        if ref.kind == "element":
            # Preserve the sibling component lists the element frame doesn't edit.
            # Shallow-copy the arrays so new_data stays structurally independent
            # from old_data (the undo snapshot) — avoids any shared-reference
            # surprise if a future code path mutates one in place.
            modifiers = old_data.get("m_Modifiers")
            criteria = old_data.get("m_SelectionCriteria")
            new_data = dict(frame.value)
            if modifiers is not None:
                new_data["m_Modifiers"] = list(modifiers)
            if criteria is not None:
                new_data["m_SelectionCriteria"] = list(criteria)
        else:
            container_key = ref.container()
            # Build new_data from old_data via cheap SHALLOW copies: only the
            # single container array slot at ref.index changes (set to frame.value),
            # so we copy the dict and the array rather than deep-copying the whole
            # item dict a second time. old_data (the undo snapshot) stays untouched,
            # and the live frame.value reference is stored exactly as the original
            # deep-copy path stored it.
            new_data = dict(old_data)
            arr = list(new_data.get(container_key, []))
            if not (0 <= ref.index < len(arr)):
                return
            arr[ref.index] = frame.value
            new_data[container_key] = arr

        if new_data == old_data:
            return

        item.setData(0, Qt.UserRole, new_data)
        # setData replaced the backing dict, so the identity signature is stale.
        self._last_build_sig = None
        if hasattr(self.document, "property_panel"):
            panel = self.document.property_panel
            if hasattr(panel, "components_list") and panel.current_item is item:
                # The component selector (Section 1) does not change during a
                # numeric/slider drag — skip its per-tick rebuild and let the
                # consolidated _on_slider_committed path handle the final state.
                # The 3D viewport still tracks via the tree.viewport().update() below.
                dragging = getattr(self.document, "_slider_dragging", 0)
                if not dragging:
                    panel.components_list.rebuild()
        if hasattr(self.document, "ui") and hasattr(self.document.ui, "tree_hierarchy_widget"):
            tree = self.document.ui.tree_hierarchy_widget
            if hasattr(tree, "viewport"):
                tree.viewport().update()
        self.document._modified = True
        self.document._edited.emit()

        stack = getattr(self.document, "undo_stack", None)
        if stack is not None and not getattr(self.document, "_property_undo_guard", 0):
            from src.editors.smartprop_editor.commands import PropertySnapshotCommand
            stack.push(PropertySnapshotCommand(self.document, item, old_data, new_data))

    def apply_external_data(self, item, new_data: dict, changed_keys=()) -> None:
        """Apply an external update (undo/redo, gizmo drag, manual editor).

        Fast path: when we already have a frame for ``item`` and can tell which
        fields changed, reconfigure only those child widgets via
        PropertyFrame.update_property_value() — no teardown, no worker thread,
        no deep copy. This is what makes slider/gizmo drags and undo/redo
        hopping cheap instead of rebuilding every widget every tick.

        Falls back to a full set_components() rebuild when the change is broad or
        ambiguous (empty changed_keys, structural change, multi-select, or no
        matching frame) — preserving the previous behaviour for those cases.
        """
        if not self._refs or not self._frames:
            return

        # Only handle the single-selection case. Multi-select (MIXED values)
        # rebuilds the whole panel, which is both rare and correct today.
        matching = [
            (ref, frame)
            for ref, frame in zip(self._refs, self._frames)
            if ref.item is item
        ]
        if not matching:
            return
        if len(matching) > 1 or len(self._refs) > 1:
            self.set_components(self._refs)
            return

        ref, frame = matching[0]

        # No diff info → cannot target individual widgets; rebuild everything.
        # Structural changes (whole m_Modifiers / m_SelectionCriteria replaced)
        # also require a rebuild because the component set itself changed.
        if not changed_keys or any(
            k in ("m_Modifiers", "m_SelectionCriteria") for k in changed_keys
        ):
            self.set_components(self._refs)
            return

        # Map each diff key to (field, value) for this ref's frame.
        # Diff keys are either plain element fields ("m_flWidth") or container
        # paths ("m_Modifiers[2].m_flAmount"); see ComponentRef.diff_key().
        updates: list[tuple[str, object]] = []
        target = ref.target(new_data) if isinstance(new_data, dict) else None
        if not isinstance(target, dict):
            self.set_components(self._refs)
            return

        for key in changed_keys:
            if key in ("_class", "m_nElementID"):
                continue
            field = self._field_for_diff_key(key, ref)
            if field is None:
                # A change we can't pin to a single field → safe full rebuild.
                self.set_components(self._refs)
                return
            if field in target:
                updates.append((field, target[field]))
            else:
                updates.append((field, None))  # key removed (Default mode)

        if not updates:
            return

        # Apply targeted reconfigure() to each affected child widget.
        all_ok = True
        for field, val in updates:
            ok = frame.update_property_value(field, val)
            all_ok = all_ok and ok
        if not all_ok:
            # A field didn't resolve to an existing widget (e.g. a newly-added
            # key the frame hasn't built). Fall back to a correct full rebuild.
            self.set_components(self._refs)
            return

        # The backing dict was replaced upstream (item.setData already happened
        # in document.apply_property_data); invalidate our identity signature so
        # the next set_components() rebuilds rather than short-circuiting.
        self._last_build_sig = None

    @staticmethod
    def _field_for_diff_key(key: str, ref: ComponentRef) -> str | None:
        """Resolve a diff key to the single field it touches for ``ref``.

        Returns None for keys that cannot be mapped to one field (whole-component
        replacements like "m_Modifiers[2]" with no sub-field), signalling the
        caller should fall back to a full rebuild.
        """
        if ref.kind == "element":
            return key.split(".")[0]
        # Container path: "m_Modifiers[2].m_flAmount" -> need it to belong to
        # this ref's container/index, then take the trailing field.
        container = ref.container()
        prefix = f"{container}[{ref.index}]."
        if key.startswith(prefix):
            return key[len(prefix):].split(".")[0]
        if key == f"{container}[{ref.index}]":
            return None  # whole component replaced → rebuild
        return None  # belongs to a different component → ignore
