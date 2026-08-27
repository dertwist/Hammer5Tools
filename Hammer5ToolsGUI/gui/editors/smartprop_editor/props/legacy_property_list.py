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
            └── PropertyFrame per component (header hidden)
            └── stretch (permanent tail)

Edits are written straight back into the tree item's full data dict via
the ref (read old, mutate a deep copy, setData, push PropertySnapshotCommand)
rather than through document.update_tree_item_value, which relied on
scanning three separate layouts that no longer coexist under this design.

Frame lifetime
--------------
Building a PropertyFrame is expensive — a 15-field element is ~580 QWidgets,
and each row costs 18-67 ms to construct from scratch. Two caches keep that
off the selection path:

  * The frame cache here keeps the last ``_FRAME_CACHE_MAX`` frames alive,
    parented and laid out but hidden. Reselecting a component it still holds
    is a show()/hide() pair instead of a rebuild.
  * When a frame is finally dropped it goes through ``PropertyFrame.dispose()``,
    which returns its rows to the per-class PooledPropertyMixin pools so the
    next build reconfigures them (~0.4 ms/row) rather than constructing them.

Both are keyed on a content fingerprint, so a frame is only ever reused for
data it still matches.
"""
from __future__ import annotations

import logging

from collections import OrderedDict
from dataclasses import dataclass

from gui.common import fast_deepcopy
from gui.editors.smartprop_editor.props.model import ComponentRef

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)

# How many built frames to keep alive for instant reselection. Each frame is
# ~580 QWidgets, so this trades a few MB for a ~0 ms selection change.
_FRAME_CACHE_MAX = 6


def _content_hash(target: dict) -> int:
    """Stable content fingerprint of a property dict.

    Uses repr() of each value so nested lists/dicts (KV3 vectors, modifiers)
    contribute to the hash. Cheap relative to a full widget rebuild; stable
    across repeated QTreeWidgetItem.data() reads (which return fresh wrappers
    around equal contents).
    """
    return hash(tuple(sorted((k, repr(v)) for k, v in target.items())))


def _frame_key(ref: ComponentRef) -> tuple:
    """Cache key identifying the component a frame was built for.

    ponytail: keyed on id(ref.item) — CPython can recycle an id after a tree
    item is freed. A collision only matters if the recycled item's contents
    also hash identically, in which case the cached frame renders the same
    fields anyway; the ref it commits through is re-bound on every reuse
    (see ``frame._ref``), so it can never write to the dead item.
    """
    return (id(ref.item), ref.kind, ref.index)


@dataclass
class _CachedFrame:
    frame: object
    content: int


class LegacyPropertyList(QWidget):
    """Section 2 backend — PropertyFrame-based property list."""

    # A property row was selected: (value_class, label). Drives the help panel.
    propertySelected = Signal(str, str)

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
        self._scroll.setProperty("h5Component", "smartpropLegacyListScroll")

        self._container = QWidget()
        # ID-qualified on purpose: an unqualified "background-color" rule is
        # inherited by every descendant and would paint over the row stripes
        # that PropertyFrame.paintEvent draws.
        self._container.setObjectName("propertyListContainer")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)
        # Permanent tail — frames are always inserted above it, so it never has
        # to be added or removed as the selection changes.
        self._container_layout.addStretch(1)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        # Frames currently on screen, in display order.
        self._frames: list = []
        self._refs: list[ComponentRef] = []
        # key -> _CachedFrame, oldest first. Hidden frames stay parented and in
        # the layout; only visibility distinguishes them from the live ones.
        self._cache: OrderedDict = OrderedDict()

        # Clicking or tabbing into any control inside a row selects that row.
        # One application-wide connection instead of an event filter per row:
        # rows are rebuilt constantly and their controls swallow mouse presses
        # before the row itself ever sees them.
        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_focus_changed)

    # ── Property row selection ────────────────────────────────────────────────

    def _on_focus_changed(self, _old, new):
        if new is None:
            return
        for frame in self._frames:
            row = frame.row_for_widget(new)
            if row is not None:
                frame.select_row(row)
                # Only one row can be selected across the panel.
                for other in self._frames:
                    if other is not frame:
                        other.select_row(None)
                return

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve(self, ref) -> dict | None:
        """The dict a frame for ``ref`` is built from, or None if unresolvable.

        Shallow copy: enough to strip the sibling component lists and to
        fingerprint, without paying a deep copy on the cache-hit path.
        """
        if ref.item is None:
            return None
        data = ref.item.data(0, Qt.UserRole)
        if not isinstance(data, dict):
            return None
        target = ref.target(data)
        if not isinstance(target, dict):
            return None
        value = dict(target)
        if ref.kind == "element":
            # Modifiers/criteria are separate components, not fields.
            value.pop("m_Modifiers", None)
            value.pop("m_SelectionCriteria", None)
        return value

    def _make_frame(self, value: dict):
        """Create a single header-less PropertyFrame with all required dependencies.

        ``value`` is expected to already be an owned deep copy produced by the
        caller, so it is passed straight through — PropertyFrame treats its
        ``value`` as owned and mutates it in place.
        """
        try:
            from gui.editors.smartprop_editor.property_frame import PropertyFrame

            frame = PropertyFrame(
                value=value,
                widget_list=self._container_layout,
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
            log.error(f"[LegacyPropertyList] Could not create PropertyFrame: {exc}")
            return None

    def _build(self, key, ref, value: dict, digest: int):
        """Construct a frame for ``ref`` and register it in the cache."""
        frame = self._make_frame(fast_deepcopy(value))
        if frame is None:
            return None

        # The ref is read off the frame rather than captured, so reusing a
        # cached frame for a different ref only needs the attribute rebound.
        frame._ref = ref
        frame.edited.connect(lambda f=frame: self._commit_frame(f._ref, f))
        frame.property_selected.connect(self.propertySelected)
        if self.document:
            try:
                frame.slider_pressed.connect(self.document._on_slider_started)
                frame.committed.connect(self.document._on_slider_committed)
            except Exception:
                pass

        self._cache[key] = _CachedFrame(frame, digest)
        return frame

    def _reuse(self, key, digest: int):
        """Cached frame for ``key`` if it still matches ``digest``, else None."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        if entry.content != digest:
            self._retire(key)
            return None
        self._cache.move_to_end(key)
        return entry.frame

    def _retire(self, key):
        entry = self._cache.pop(key, None)
        if entry is None:
            return
        try:
            self._frames.remove(entry.frame)
        except ValueError:
            pass
        try:
            entry.frame.dispose()
        except Exception:
            pass

    def _evict(self, protected: set):
        """Drop the oldest cached frames that are not currently on screen."""
        for key in list(self._cache):
            if len(self._cache) <= _FRAME_CACHE_MAX:
                return
            if key not in protected:
                self._retire(key)

    def _place(self, frame, position: int):
        """Ensure ``frame`` sits at ``position`` in the container layout."""
        layout = self._container_layout
        if layout.indexOf(frame) != position:
            layout.removeWidget(frame)
            layout.insertWidget(position, frame)

    def _is_current(self, wanted: list) -> bool:
        """True when exactly these frames, with this content, are already shown."""
        if len(wanted) != len(self._frames):
            return False
        for (key, _ref, _value, digest), frame in zip(wanted, self._frames):
            entry = self._cache.get(key)
            if entry is None or entry.frame is not frame or entry.content != digest:
                return False
        return True

    def _refresh_digest(self, ref) -> None:
        """Re-fingerprint a cached frame after its backing data was replaced."""
        entry = self._cache.get(_frame_key(ref))
        if entry is None:
            return
        value = self._resolve(ref)
        if value is None:
            self._retire(_frame_key(ref))
            return
        entry.content = _content_hash(value)

    # ── AbstractPropertyList interface ─────────────────────────────────────────

    def set_components(self, refs: list) -> None:
        """Show a PropertyFrame per selected ComponentRef.

        Reselecting components whose frames are still cached and whose backing
        data is unchanged costs a show()/hide(); anything else is built once and
        then cached.
        """
        self._refs = list(refs)

        wanted = []
        for ref in self._refs:
            value = self._resolve(ref)
            if value is None:
                continue
            wanted.append((_frame_key(ref), ref, value, _content_hash(value)))

        if self._is_current(wanted):
            return

        for frame in self._frames:
            frame.hide()
        self._frames = []

        for position, (key, ref, value, digest) in enumerate(wanted):
            frame = self._reuse(key, digest)
            if frame is None:
                frame = self._build(key, ref, value, digest)
                if frame is None:
                    continue
            else:
                frame._ref = ref
            self._place(frame, position)
            frame.show()
            self._frames.append(frame)

        self._evict(protected={key for key, _, _, _ in wanted})

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
        # setData replaced the backing dict — re-fingerprint so the next
        # set_components() recognises this frame as still current.
        self._refresh_digest(ref)
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
            from gui.editors.smartprop_editor.commands import PropertySnapshotCommand
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
        # in document.apply_property_data), so re-fingerprint this frame.
        self._refresh_digest(ref)

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
