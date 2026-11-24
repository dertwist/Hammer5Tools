---
name: hammer5tools-cli
description: Inspect, author, validate, and compile Counter-Strike 2 / Source 2 assets (.vmap, .vmdl, .vmat, .vtex, .vsmart, .vdata, .vsnap, .vpk) and Unreal packages using Hammer5Tools CLI or direct Hammer5Tools.Core.dll calls. Use when working with CS2 addon assets, Source 2 formats, or Hammer5Tools automation.
---

# Hammer5Tools CLI & Core DLL Skill

Use Hammer5Tools headlessly from any terminal or Python script — **even while the Hammer5Tools GUI is already running**.

## Locating the Executable

- **Installed build**: `<install_dir>\app\Hammer5ToolsGUI.exe` (e.g. `%LOCALAPPDATA%\Hammer5Tools\current\app\Hammer5ToolsGUI.exe`).
  - Always invoke **`app\Hammer5ToolsGUI.exe cli ...`**, not `Hammer5Tools.exe` (which is the single-instance GUI launcher).
- **Source checkout**: `.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli ...`

`cli` dispatches before Qt/OpenGL/single-instance initialization, runs in a separate process, writes JSON to stdout, and exits.

## Choosing CLI vs Direct DLL (`Hammer5Tools.Core.dll`)

- **Use `cli`** for single-shot inspection, safe `--dry-run` edits, compilation, validation, and built-in guides (no Python environment or C ABI boilerplate required).
- **Use Python + `Hammer5Tools.Core.dll` (or `core.bridge.CoreBridge`)** when you need tight loops, batch processing across hundreds of files, or low-level Core exports (`h5t_vmap_read_import_json`, `h5t_smartprop_read_import_json`, binary VMAP/NavMesh exports) without spawning a process per call.

See `AUTOMATION.md` beside the launcher (or at repo root) for full CLI examples, `ctypes` DLL loading instructions, and Source 2 format details.

## Quick CLI Commands

```powershell
# Discover all registered tools and their JSON schemas
app\Hammer5ToolsGUI.exe cli capabilities

# Check NativeAOT Core & CS2 environment status
app\Hammer5ToolsGUI.exe cli core-status

# Read Source 2 assets (summary by default)
app\Hammer5ToolsGUI.exe cli vmdl-read C:\addon\models\prop.vmdl
app\Hammer5ToolsGUI.exe cli vmat-read C:\addon\materials\surface.vmat
app\Hammer5ToolsGUI.exe cli vsmart-read C:\addon\smartprops\fence.vsmart
app\Hammer5ToolsGUI.exe cli vmap-references C:\addon\maps\example.vmap

# Invoke any registered tool with JSON arguments
app\Hammer5ToolsGUI.exe cli call hammer5tools.vmat_edit --args '{"path":"C:/addon/materials/surface.vmat","set_slots":{"TextureColor":"materials/new_color.png"},"dry_run":true}'

# Fetch a built-in Source 2 format guide before authoring
app\Hammer5ToolsGUI.exe cli call hammer5tools.guide --args '{"topic":"vsmart-authoring"}'

# Compile and validate
app\Hammer5ToolsGUI.exe cli compile C:\addon\models\prop.vmdl --background
app\Hammer5ToolsGUI.exe cli validate --addon example
```

## Working Rules

1. **Read summaries first**: Read tools default to `detail: "summary"`. Escalate to `detail: "full"` or `select` (e.g. `m_Variables[m_VariableName=Length]`) only when needed.
2. **Preview writes with `dry_run`**: Pass `"dry_run": true` (or `--dry-run`) and inspect the diff before writing to disk. Never report a file as modified after a dry run.
3. **Edit SmartProps with `vsmart_patch`**: Use `hammer5tools.vsmart_patch` (`set`, `remove`, `add_variable`, `add_category`) instead of `vsmart_edit` when modifying individual nodes, because `vsmart_patch` repairs duplicate element IDs and lints on write.
4. **Never hand-author `.vmap` mesh geometry**: Synthesized `CMapMesh` structures crash Hammer and `resourcecompiler`. Use `hammer5tools.vmap_write_blockout` for boxes and fetch `guide("vmap-authoring")` first.
5. **Verify before reporting success**: For SmartProps, run `hammer5tools.vsmart_lint` and `hammer5tools.vsmart_evaluate` (`model_count == 0` indicates a broken prop, not an empty one). For compiled assets, verify `compile_asset` / `compile_assets` exits with code `0`.
6. **Check pagination**: List results default to paged windows; check `total` and `truncated` and use `limit` / `offset` to fetch remaining items.

## Built-in Source 2 Guide Topics

Fetch any topic via `cli call hammer5tools.guide --args '{"topic":"<name>"}'`:

- `vsmart-authoring` — elements, modifiers, filters
- `vsmart-creating` — building SmartProps from scratch with recipes
- `vsmart-expressions` — intrinsics, NaN cascade pitfalls, typed defaults
- `vsmart-ui` — categories, hide/read-only expressions, sizers
- `vsmart-enums` — Hammer dropdown labels to KV3 enum values
- `vmap-reading` — map entities, brush meshes, SmartProp placements, FGD definitions
- `vmap-authoring` — map geometry, blockout, supported write operations
- `addon-maintenance` — dependencies, orphans, validation, compile order
- `official-assets` — stock content in CS2 VPK archives
- `particles-and-porting` — `.vsnap` point clouds and Unreal inspection tools
- `gamedata-vdata` — KeyValues3 `.vdata` tables and schema types
- `compile-verify` — using `resourcecompiler` as a verification harness
- `material-texture` — `.vmat`, `.vtex`, and `.vmdl` conventions and colour spaces
