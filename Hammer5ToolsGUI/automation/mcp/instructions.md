Hammer5Tools inspects and authors Source 2 (CS2) and Unreal assets. Asset paths are content-relative, case-insensitive, and presented with forward slashes.

Common parameters, the same on every tool that takes them: `dry_run` previews without writing; `detail` is `summary` (default) or `full`; `select` addresses one node (`m_Variables[m_VariableName=Length]`); `limit` and `offset` page a result; `cs2_path` and `game_dir` override the configured CS2 root.

Working rules:

- Read tools return a summary; escalate to `full` or `select` deliberately. Never read a whole document to look at one field.
- Change a SmartProp with `vsmart_patch` (`set`, `remove`, `add_variable`, `add_category`), not `vsmart_edit`: it edits one node, repairs duplicate element IDs, and lints on write, where `vsmart_edit` replaces whole arrays.
- Preview modifying calls with `dry_run: true` and read the diff before writing. Never report a file as changed when `dry_run` was set, or when a read-only tool was used.
- Verify before reporting success. `compile_asset` exit code 0 is the claim you may make; for SmartProps, `vsmart_lint` and `vsmart_evaluate` first. A `model_count` of 0 means something is broken, not that the prop is empty.
- List results are paged. Check `total` and `truncated` before treating a page as the whole answer.
- Never hand-author `.vmap` geometry: synthesized mesh structures crash Hammer and the compiler. Use `vmap_write_blockout` for boxes, and `guide("vmap-authoring")` for anything else.

Call `hammer5tools.guide` before writing Source 2 content; one call prevents a compile cycle spent guessing. Topics:

- `vsmart-authoring` — elements, modifiers, filters
- `vsmart-creating` — building one from scratch, with recipes
- `vsmart-expressions` — intrinsics, the NaN cascade that makes props vanish
- `vsmart-ui` — categories, hide/read-only expressions, sizers
- `vsmart-enums` — Hammer labels to KV3 enum values
- `vmap-reading` — map entities, meshes, SmartProp placements, entity definitions
- `vmap-authoring` — map geometry, blockout, what writing supports
- `addon-maintenance` — dependencies, orphans, validation, compile order
- `official-assets` — stock content in the CS2 VPK archives
- `particles-and-porting` — vsnap clouds, read-only Unreal tools
- `gamedata-vdata` — gamedata tables and their schema type
- `compile-verify` — the compiler as a test harness
- `material-texture` — vmat/vtex/vmdl conventions, colour spaces
