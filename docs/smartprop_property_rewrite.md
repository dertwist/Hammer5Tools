# SmartProp Property Editor Rewrite — 3-section, Source 2 style

Supersedes the earlier "Option B / virtualized widget rows" plan. Architecture changed
2026-07-27: a **components list** in front of the property tree, which removes the
performance problem structurally (the tree only ever renders one component's ~15-20 fields).

New home: `src/editors/smartprop_editor/props/`.

---

## Layout

```
┌─ 1. COMPONENTS ────────────┐   pic 1 (particle-editor style list)
│  ▸ <current element>       │   the hierarchy element itself — first entry, selected by default
│  ▾ Modifiers               │   category header, + button
│      ✓ Set position     ≡ ✕│
│      ✓ Random scale     ≡ ✕│
│  ▾ Selection Criteria      │   category header, + button
│      ✓ Probability      ≡ ✕│
└────────────────────────────┘
┌─ 2. PROPERTIES ────────────┐   pic 2 (Source 2 Object Properties)
│ (Property Name Filter)   ⚙ │   filter box + settings
│ ─ radius_inner  │ 293  ▸──┤│   QTreeView: name column | value column (delegate-painted)
│ ─ ManualScale   │ 0.073 ─▸ │
│ ⊟ Render Properties        │   collapsible group rows
│ ─ Alpha         │ 255      │
│ ⊞ Lighting                 │
└────────────────────────────┘
┌─ 3. HELP ──────────────────┐   pic 2 bottom pane
│ Fade Start Distance        │   title = active row (or active component)
│ Distance at which each…    │   body = description from property_tooltips
└────────────────────────────┘
```

Data flow: tree-hierarchy selection → section 1 rebuilds its component list →
component selection → section 2 loads that component's fields → row focus/hover →
section 3 shows its help text. Section 1 selection is what drives section 2, *not* the
hierarchy tree directly. Clicking a component in section 1 also selects the owning
element in the hierarchy tree.

---

## Reference: github.com/dertwist/VsmartEditor (MIT, same author, archived)

Cloned for reference; read-only. **Correction worth knowing before building:** that repo's
`src/property_editor/property_tree.py` is *not* QTreeView + delegate despite the filename —
it is `PropertyTreeWidget(QWidget)` holding a `QVBoxLayout` of `PropertyItemWidget(QFrame)`
rows, each calling `setStyleSheet()` per row for zebra/selection. That is the same
widget-per-row architecture H5T has today, including the per-row QSS tax measured at 1.9x.
So "QTreeView + delegate" and "same approach as VsmartEditor" are opposite designs.
This plan follows the explicit instruction — **QTreeView + delegate** — because pic 2 is a
real name/value tree (filter box, collapsible groups, uniform rows) and a delegate gets
filtering, expand/collapse, keyboard nav and sorting for free.

**Harvest (port into H5T):**
| From | Use for |
|---|---|
| `property_editor/property_tree.py` → `BaseProperty`, `PropertyRegistry`, `identifier` substring matching, `PropertyMode` enum | validates the `schema.py` registry design; port the pattern, not the code |
| `BaseProperty._generate_display_name` | prefix strip + camelCase split (H5T has a regex equivalent — keep whichever reads better) |
| `src/icon_cache.py` → `IconCache._create_property_icon` | **generated** type badges: coloured circle + letter — `fl`/`n`/`s`/`b`/`v`/`m`/`ds`/`vn` with hex colours. Cached singleton. Copy wholesale. |
| `src/icons/propertyeditor/` (43 PNG) | real Valve property-editor chrome: `attr_reset`, `attr_menu`, `hierarchy_expanded/collapsed(_hover)`, `item_add/remove`, `overlay_inherit/override`, `sort_az/za/def`, `clear_filter`, `show_hidden`, `interval_lock`, `array_drag_handle` |
| `src/icons/valve_style/` (43 PNG) | authentic S2 Qt widget chrome: `checkbox_*`, `radio_*`, `arrow_*`, `dropdown_menu_*`, `branch_open*`, `tab-*` |

**Do not copy:** the per-row `setStyleSheet` pattern (measured 1.9x cost), the QFrame-per-row
structure, or its selection colour `#3daee9` — that is KDE Breeze blue, not Source 2. Use the
existing H5T token palette, where S2 selection is slate `#4F5259` (see `src/styles/tokens.py`).

---

## Measured baseline (2026-07-27, PySide6 6.9, offscreen, 36-row viewport)

| variant | widgets/row | fill viewport | selection change | scroll/page |
|---|---|---|---|---|
| today, eager, 350-row node | 37 | **8681 ms** | rebuild | — |
| today, eager, 36 rows | 37 | 649 ms | rebuild | — |
| widget-per-row + lazy modes + panel QSS | 15 | 195 ms | rebuild | — |
| **QTreeView + delegate** | 0 | **17 ms** (2000 rows) | ~17 ms | 4.26 ms |

Repro: `scratchpad/bench_ab.py`, `bench_ab2.py`. The components list caps section 2 at
~15-20 rows, so the delegate path is far inside budget. Section 1 holds ~10-40 light rows.

---

## Contracts (fixed — do not redesign in later phases)

```python
# schema.py
MIXED = ...                                  # selected components disagree on this field
def fields_for(prop_class) -> list[str]      # ordered
def resolve(prop_class, field) -> FieldDef   # control kind + kwargs + icon key + group

@dataclass(frozen=True)
class FieldDef:
    field: str; control: str                 # 'float'|'bool'|'string'|'vector3d'|'combobox'|'color'|…
    kwargs: dict                             # int_bool, slider_range, items, filter_types, placeholder…
    label: str; icon: str                    # icon = IconCache key: 'float'|'number'|'string'|'bool'|'vector'
    group: str | None                        # collapsible group row, e.g. "Render Properties"

# components.py — section 1
class ComponentList(QWidget):
    componentSelected = Signal(object)       # ComponentRef
    Kind = "element" | "modifier" | "criterion"
    # ComponentRef = (tree_item, kind, index)   index=-1 for the element itself

# model.py — section 2 backing store
class PropertyTreeModel(QAbstractItemModel):
    def set_components(self, refs: list) -> None      # 1 = normal, N = multi-select w/ MIXED
    # col 0 = name (icon + label), col 1 = value; group rows are parents
    # data(EditRole) -> value | MIXED ; setData() diffs, pushes PropertySnapshotCommand
    def begin_drag(self) / end_drag(self)             # slider drag = one undo entry

# delegate.py — section 2 rendering + editing
class PropertyDelegate(QStyledItemDelegate):
    # paint(): value text, inline drag-slider track, colour swatch, checkbox, MIXED em-dash
    # createEditor(): the H5T control for FieldDef.control
    # mode switch (Default/Value/Variable/Expression) lives in the row, right-aligned, like pic 1
```

Rules: the model is the only owner of values. Editors are created on demand by the delegate
and destroyed on commit — no pooling, no `reconfigure()`, no widget-per-row.
Complex controls that cannot paint (vector3d, colormatch, material_replacements) use
`openPersistentEditor` on that row only, or a popup — decide per control in P4.

---

## Phases

## P0 — Harvest assets  · haiku
Files: new `src/icons/propertyeditor/`, `src/icons/valve_style/`, `src/styles/property_icons.py`
Source: the VsmartEditor clone (ask for the path; do not re-clone).
1. Copy both icon folders into `src/icons/`. Add them to the `.qrc` so `compile_ui.py` picks
   them up; verify `QIcon(":/icons/propertyeditor/attr_reset.png")` resolves at runtime.
2. Port `IconCache` → `src/styles/property_icons.py`, swapping `qtpy` imports for `PySide6`.
   Keep the singleton cache and the `type_map` colours verbatim.
3. Delete `src/editors/smartprop_editor/property/main.py` (673 lines, zero importers — verify
   with grep first).
Done when: a 10-line `__main__` renders every badge + 5 sample PNGs to a scratch PNG.

## P1 — schema.py  · DONE 2026-07-27
`props/schema.py` + `props/__init__.py`. Exposes `FieldDef`, `SKIP`, `fields_for()`,
`resolve()`, and `resolve_variable_value(prop_class, value)` for the one value-dependent case
(`m_VariableValue`, where the control depends on the runtime value — `resolve()` returns
`'set_variable'` and the caller refines).
Actual table sizes (my earlier estimates of 68/34 were wrong): **64 classes, 366 fields**,
39 exact-dispatch rules, 31 combobox substring rules, 11 prefix rules.
Verified by diffing against the live `PropertyFrame` tables, not against schema's own copy:
class map 64/64 and 366/366 fields identical, skip set identical, exact 39/39 with no
missing/extra keys, combobox 31/31 in the same order with matching item payloads, prefix
order identical, and `resolve()` vs a reimplementation of the live chain **366/366, 0
mismatches**. Repro: `scratchpad/verify_p1.py`.
`property_frame.py` untouched — schema is additive, nothing consumes it yet.

## P2 — model.py + undo  · DONE 2026-07-27
`props/model.py`: `PropertyTreeModel(QAbstractItemModel)`, `ComponentRef`, `MIXED`, `DEFAULT`,
roles `FieldDefRole`/`MixedRole`/`RefRole`. Self-check passes (run with
`PYTHONPATH=<repo> python src/editors/smartprop_editor/props/model.py`).

Four design decisions later phases depend on:
1. **Read-through, not owned copies.** The tree item's `Qt.UserRole` dict stays the only source
   of truth; the model reads through on every `data()`. No desync, and `apply_external_data`
   has nothing to re-seed — it only tells views to refresh. Deviates from the original plan
   text, which said the model owns copies.
2. **`DEFAULT` sentinel deletes the key.** The old widget layer's "Default" mode set
   `value = None` and `on_edited` merged only non-None values, so the key ended up *absent*
   from the saved dict. Writing `None` would change `.vsmart` output. `set_field(f, DEFAULT)`
   → `del target[f]`.
3. **Unknown classes fall back to their own dict keys** (schema returns `[]`), matching the old
   `reversed(self.value.items())` fallback, so a new element class still shows fields.
4. **No `begin_drag`/`end_drag`.** `PropertySnapshotCommand.mergeWith` already coalesces
   consecutive same-field edits, which covers keystrokes and slider drags. Add them only if a
   gizmo drag touching several keys at once proves it necessary.

Undo seam wired: `commands.py` both call sites now call `document.apply_property_data(...)`,
and `document.py` gained that method — it forwards to `panel.apply_external_data()` when a new
panel is installed, else to the legacy `_incremental_property_update`. So old and new panels
both work during the transition. Multi-item writes wrap in `beginMacro`/`endMacro` → one undo
entry. Verified: undo/redo round-trip through the real command path, diff-noop pushes nothing,
`apply_external_data` pushes nothing, MIXED fan-out reverts both items with a single undo.

## P2 (original spec) — model.py + undo  · sonnet
Files: new `props/model.py`; read `document.py` (`on_tree_current_item_changed`,
`update_tree_item_value`, `_on_slider_started/_committed`), `commands.py` (`PropertySnapshotCommand`)
`QAbstractItemModel` over one component's `FieldDef` list (group rows as parents once P5
lands; flat until then). `setData` writes the owned dict → writes back to the tree item →
pushes `PropertySnapshotCommand` (reuse it; do not write a new command class).
Multi-component: `data()` returns `MIXED` when values differ; `setData` writes all.

**Two constraints discovered in `commands.py` (2026-07-27) — get these right or undo breaks:**
1. `PropertySnapshotCommand.undo()`/`redo()` call
   `document._incremental_property_update(item, data, diff_keys)` when the item is current.
   That method is on P7's delete list, so **P2 must provide the replacement**:
   `panel.apply_external_data(item, data, diff_keys)` — re-seed the model from the given dict
   and refresh affected rows without re-pushing an undo command. Update the two call sites in
   `commands.py` to the new hook. This is the one edit P2 makes outside `props/`.
2. `redo()` deliberately skips its **first** invocation (`_first_redo`) — the edit is applied
   *before* the command is pushed. The model must keep that contract: mutate, then push.
Coalescing: `mergeWith` already merges consecutive edits sharing the same `_diff_keys`, so
keystrokes and slider drags on one field collapse to one entry for free. Try relying on that
before adding explicit `begin_drag()`/`end_drag()`; only add them if merge proves insufficient
(e.g. gizmo drags that touch several keys at once).
Done when: self-check (`if __name__ == "__main__"`, asserts, no pytest) covers
get/set/MIXED/diff-noop/drag-coalescing. Not wired to any view yet.

## P3 — components.py (section 1)  · sonnet
Files: new `props/components.py`; reuse `PropertiesGroupFrame` for the category headers
List with: the element itself as row 0, then `Modifiers` and `Selection Criteria` category
headers each with a `+` button, then their entries. Per row: enabled checkbox, class icon
(`IconCache.get_node_icon`), label, the summary hint on the right (pic 1 shows
`Position; Position Previous`, `Creation Time`), drag handle, delete `✕`.
Carry over from the old panel: drag-reorder, context menu, clipboard string
`hammer5tools:smartprop_editor_property;;<name>;;<value>;;<group>`, group accent colours
(`modifier` `#8B5E3C`, `selection_criteria` `#2E6B9E`).
Emits `componentSelected`. Row 0 selected by default on hierarchy change.
Done when: selecting each component type emits the right `ComponentRef`; reorder + delete +
paste all round-trip through the existing undo commands.

## P4 — delegate.py + view (section 2)  · sonnet
Files: new `props/delegate.py`, `props/view.py`
`QTreeView`, 2 columns, `setUniformRowHeights(True)`, header `Name | Value`, filter box
above wired to a `QSortFilterProxyModel` (`clear_filter.png` button), `hierarchy_expanded/
collapsed` PNGs as the branch indicators via QSS, `valve_style` checkbox/arrow/dropdown PNGs
for the widget chrome.
Delegate paints: value text, inline drag-slider track (pic 2's right column), colour swatch,
checkbox, `MIXED` as a dimmed em-dash. `createEditor` returns the existing H5T control for
`FieldDef.control`; commit on `editingFinished`/focus-out.
Decide per control: paintable+editor (float, int, bool, string, combobox, color) vs
`openPersistentEditor` (vector3d, colormatch, material_replacements, set_variable,
comparison, path_editor). Prefer paintable; a persistent editor is the fallback, not the default.
Watch: `CompletionUtils.get_available_variable_names` walks the variables scroll area — call
it when an editor opens, never from `paint()` or `data()`.
Note (found in P0): `IconCache._create_icon` bakes a fixed 24×24 pixmap, so
`QIcon.pixmap(n, n)` never returns more than 24px of real detail — badges drawn at 16px are
downscaled and slightly soft, and HiDPI will not sharpen them. If that reads badly in the
view, add a `size` argument through `get_property_icon` and cache per size.
Done when: every control kind is editable, sliders drag as one undo entry, filter narrows
rows live, and a 20-field component renders in ≤20 ms.

## P5 — help pane + groups  · sonnet
Files: new `props/help.py`; `props/schema.py` (fill `group`)
Help pane: title + body from `property_tooltips`, driven by the view's `currentChanged`
and by `componentSelected` (component description when no row is focused). Empty state
when nothing is selected.
Groups: populate `FieldDef.group` so related fields collapse under a parent row
(pic 2's `Render Properties` / `Lighting` / `Build Settings`). Persist expand state per class.
Layout2DGrid field suppression becomes a schema-driven visibility predicate on the proxy
model — not per-widget signal wiring.
Done when: focusing any row shows its help text; groups collapse and remember state.

## P6 — wire into document.py  · sonnet
Files: `document.py`
Replace the three-layout panel with the 3-section stack. `on_tree_current_item_changed`
becomes `self.components.set_element(item)`; everything else flows from `componentSelected`.
Keep: 3D-viewport sync, gizmo drag commit, manual-editor refresh, `properties_groups_show/hide`
placeholder behaviour.
Gate: open a real `.vsmart`, edit a float / bool / vector / combobox / string, undo+redo each,
save, confirm the file is unchanged vs. before the edit-undo cycle. No crash, no traceback.

## P7 — delete scaffolding  · haiku (pure deletion, only after P6 ships)
Delete: `property_frame.py`, `ui_property_frame.py`, `property_widget_pool.py`,
`property_data_worker.py`, `property/base_pooled.py`, and in `document.py`:
`_prewarm_property_pools`, `_prewarm_node_modifiers`, `_on_modifier_prewarm_*`,
`_take_prewarm_modifier_results`, `_submit_modifier_batch_worker`, `_on_modifier_batch_*`,
`_wire_modifier_property_frame`, `_acquire_modifier_property_frame`,
`_load_next_modifier_chunk`, `_populate_modifiers_progressive`, `_cancel_modifier_load`,
`_modifier_load_*`, `_modifier_batch_*`, `_property_undo_guard`, `_dec_property_undo_guard`,
`_get_nth_property_frame`, `_rebuild_group_section`, `update_property_frame_values`.
`_incremental_property_update` is **replaced, not merely deleted** — P2 introduces
`panel.apply_external_data()` and repoints the two `commands.py` call sites. Confirm those
call sites no longer reference the old method before deleting it.
Keep the old `property/*.py` control widgets only if P4 reuses them as delegate editors;
otherwise delete those too.
Rule: delete only; if a caller still needs something, stop and report instead of patching.
Done when: grep for `PropertyFrame|PropertyWidgetPool|PooledPropertyMixin|PropertyDataWorker`
returns nothing under `smartprop_editor/`, app launches, gate passes.

## P8 — multi-select  · sonnet
Files: `props/components.py`, `props/model.py`
Ctrl/shift-click in section 1 selects multiple components; `set_components()` takes the list;
rows = intersection of their classes' fields (schema order); differing values show MIXED;
one edit writes all, one undo reverts all. Header shows "N components selected".
Done when: select 3 same-class modifiers, edit one float, all three change, single undo reverts all three.

---

## Open question (answer before P8, does not block P0-P7)
"Multi-selection" could mean components in section 1, elements in the hierarchy tree, or
property rows in section 2. P8 above assumes **section 1 components**. Hierarchy-element
multi-select is a superset (section 1 would show the intersection of N elements' component
stacks) and would need its own phase.
