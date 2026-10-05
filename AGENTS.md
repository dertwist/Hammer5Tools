# Hammer 5 Tools

Hammer 5 Tools is a Counter-Strike 2 desktop toolkit.

```text
Optional C++ launcher -> Python/PySide6 GUI -> Hammer5Tools Core (.NET) -> external libraries
```

## C# migration workspace

The replacement application under `src/` uses `Core -> Infrastructure -> App/Cli` dependencies:

- `src/Hammer5Tools.Core/`: typed domain documents, contracts, settings and undo; no Avalonia dependencies.
- `src/Hammer5Tools.Infrastructure/`: filesystem/process integrations and the CS2WorkshopManager adapter. Workshop selection and VPK packing use the upstream NuGet package; do not duplicate its packing rules.
- `src/Hammer5Tools.App/`: Avalonia views, presentation state and editor lifecycle. `Controls/WorkspaceView.cs` owns Dock layouts and persistence; preferences use the shared settings service and semantic theme resources.
- `src/Hammer5Tools.Cli/`: command-line presentation.
- `tests/Hammer5Tools.App.Tests/`: headless Avalonia render and lifecycle regression tests.

Python views remain the layout and lifecycle baseline. Preserve panel placement and dialog field order when porting them, while allowing the Explorer and editor panels to dock and float. Confirm dirty documents before closing, changing addons or changing installations. A cancelled or failed save must retain dirty state. Source-document writes validate, stage, retain `.bak` files and replace atomically.

`IResourceCompiler` retains its existing asset compile overload and adds an overload for map-build arguments, with cancellation terminating the process tree. `ILoadingScreenService` includes addon-description loading and SVG map-icon application; parsing and IO are kept out of views. The legacy ownership rules below apply to the existing Python/NativeAOT application, not the replacement managed application. Neither application is removed until migration parity is verified.

## Mandatory Workflow

Before changing code:

1. Read [STYLESHEET.md](STYLESHEET.md) for UI work.
2. Use `codebase-memory-mcp` (`search_graph`, `get_architecture`, and
   `trace_path`) to find existing code and call chains.
3. Reuse or extend existing code when practical.
4. Check existing dependencies before adding a library. Avoid a large library
   for a small task.

Keep changes small and preserve existing behavior. Add characterization tests
before moving behavior that has no coverage.

## Ownership Boundaries

- `Hammer5ToolsLauncher/`: startup, single-instance IPC, crash reporting, and
  update startup only.
- `Hammer5ToolsGUI/gui/`: PySide6 views, input, presentation state, and OpenGL
  drawing only.
- `Hammer5ToolsGUI/core/`: the pure-Python NativeAOT `ctypes` bridge.
- `Hammer5ToolsGUI/automation/`: MCP/CLI transport, schemas, request-time settings,
  and response shaping. Compilation, source-asset mutation, map authoring,
  model bounds, and texture-channel preparation run in Core through CoreBridge.
- `Hammer5ToolsGUI/keyvalues3/`: the standalone KV3 library.
- `Hammer5ToolsCore/`: all domain logic. This includes Source 2 parsing,
  VPK/resource access, SmartProp evaluation, VMAP work, conversions, Source
  porting, and Unreal extraction.
- `Hammer5ToolsGUI/Tests/`: Python regression and characterization tests.
- `Hammer5ToolsGUI/gui/tools/`: external tools and scripts shipped with the app.
- `../Source2Houdini/`: separate Houdini 21 package and SOP presentation adapters.
  Source 2 interpretation remains in Core, accessed through its NativeAOT C ABI.
- `makefile.py`: build and packaging entry point.
- `version.json` and `Hammer5ToolsGUI/gui/common.py`: application version.

The GUI must use `CoreBridge` for domain work. Do not duplicate Core logic in
Python. Do not expose .NET namespaces to editors. Shipped code must not use
pythonnet, CLR reflection, or a subprocess CLI.

The Core must remain independent of the GUI and launcher. Keep it as one C#
project and publish it as one NativeAOT library. Put environment access in
`IO/`, format interpretation and conversion in `Format/`, public contracts in
`CoreApi.cs`, and unmanaged ABI methods in the root `*Api.cs` files.

The Python-to-Core NativeAOT ABI uses versioned binary payloads for VMAP scene,
VMAP reference rewrite, NavMesh Radar, and VSnap operations. Keep binary
readers/writers in `Hammer5Tools.Core/` or the relevant `Format/` area, use
explicit little-endian fields and bounds checks, and bump the ABI version when
changing an existing binary message.

The additive DCC import exports `h5t_vmap_read_import_json` and
`h5t_smartprop_read_import_json` share `ValveMapImportOptions` for prefab expansion,
object selection-set masks, hidden nodes, tool-material-only mesh exclusion,
SmartProp evaluation and metadata.
SmartProp source/compiled deserialization and dependency resolution stay in Core.
Compiled model `geometryOnly` requests retain material paths without decoding
textures. Source2Houdini consumes these exports through its external Core dependency.

The Core owns SmartProp evaluation results. The GUI only adapts those results
for display.

VMAP DCC import keeps child transforms in authored map space and rebases
prefab/instance references in Core. The additive import JSON options include
`ignoreStaticOverlays`; missing nested SmartProp resources remain diagnostics
and do not discard valid placements.

The additive managed `CoreApi` SmartProp editor methods create, validate, parse,
serialize, edit and save source documents, locate CS2, load source/compiled
resources and evaluate previews with nested dependencies and textured geometry.
Core owns the editor component templates and assigns fresh IDs when adding or
pasting components. Editor paths are arrays of object keys and
array indices. These methods do not change the existing NativeAOT ABI. The C#
preview keeps undo snapshots and pending input as presentation state; it does not
replace the shipped Python editor or its packaging.

Compiled-model JSON requests may opt into `collisionFallback` when render LoD0
is absent. The response `geometrySource` distinguishes `render` and `collision`.
Fallback defaults off for existing callers; collision geometry has flat normals
and zero UVs. Houdini opts in through its external Core dependency.

The additive `h5t_vmap_read_import_json` export returns schema-versioned DCC
import data, preserving polygon corners, node identities, hierarchy and editor
metadata. It is separate from the flattened binary VMAP preview contract.
Increment its `schemaVersion` when changing existing fields or semantics.
DCC import schema 2 includes the saved `CVisibilityMgr` hidden flags in node
visibility and exposes a selection-set catalog with stable keys. Per-set
overrides use 0 (Hammer state), 1 (enabled) or 2 (disabled); disabled wins on
overlapping membership. `metadataOnly` omits mesh projection and evaluation for
catalog refresh. Binary preview messages are unchanged.

Assetgroup source-name normalization and template token expansion use
`CoreBridge` and the Core `Format/AssetGroup/` implementation. The additive
`h5t_assetgroup_*` exports accept JSON requests and return UTF-8 text; keep
these rules out of Python when extending the remaining legacy batch workflow.

NavMesh Radar requests keep rectangle merging (`collapseFaces`) separate from
same-height connected-region N-gon dissolving (`collapseFacesIntoNgons`).

Automation uses additive `h5t_*_json` exports in `AutomationApi.cs` for confined
loose-file path resolution, compilation/jobs/log windows, VMAT/VMDL authoring,
structured map editing, model bounds, and texture preparation. These exports
leave existing versioned binary messages unchanged. JSON serialization must use
source-generated metadata under NativeAOT. Compilation job metadata and Unicode
logs are Core-owned; recovered active jobs become interrupted without signalling
stale PIDs. Source/map/texture writes stage and validate before per-file atomic
replacement with retained backups; batches have no rollback.

## C# Rules

- Use current .NET, nullable references, file-scoped namespaces, four spaces,
  LF, and final newlines.
- Use Allman braces, `var` for locals, collection expressions, pattern matching,
  null-coalescing, interpolation, `MathF`, using declarations, and early returns.
- Use PascalCase for types and members, camelCase for locals and parameters, and
  `I` prefixes for interfaces.
- Prefer specific names such as `Reader`, `Writer`, `Evaluator`, `Context`,
  `Document`, and `Service`. Avoid `Manager`, `Handler`, and `Controller`.
- Seal internal types when appropriate. Add concise XML documentation to public
  Core APIs. Remove unused usings.

## Python and UI Rules

- Use `snake_case` for project functions, methods, variables, and modules. Use
  `PascalCase` for classes and `UPPER_SNAKE_CASE` for constants.
- Add type hints to new public functions. Use four spaces, LF, and final
  newlines. Do not use star imports.
- Keep Qt virtual overrides in Qt camelCase. Names such as `paintEvent`,
  `eventFilter`, `rowCount`, and `initializeGL` are framework entry points.
  Renaming them silently breaks dispatch.
- Before renaming a class, search its old name in `*.py`, `*.ui`, `*.qss`,
  `*.qrc`, and `QSettings` keys. Update UI class entries, QSS type selectors,
  and resource paths. Never rename an existing `QSettings` key.
- Put global styling in `Hammer5ToolsGUI/gui/styles/`. Do not add inline palettes.
- Read settings at the point of use. Do not cache settings in module globals.
- Import setting accessors from `gui.settings.common`. Use `gui.settings.main`
  only for the Preferences dialog.
- Report failures with `logging.getLogger(__name__)`. Do not use `print()` for
  diagnostics because shipped builds have no console.
- Add a new editor by adding one `EditorSlot` to `MainWindow._editor_slots` and
  one build method. Do not add editor names to any other list.

### Background work

Pick the mechanism by the shape of the job, and never touch a widget off the GUI
thread — build data in the worker and emit it to a slot that builds the widgets.

- Long-running, cancellable jobs that report progress: subclass `QThread` and
  communicate with signals. Compiles, exports, VPK loads, and porting use this.
- Short fan-out work over many items: subclass `QRunnable` and submit it to a
  `QThreadPool`. Thumbnails, model loading, and scans use this.
- Fire-and-forget work that should not depend on Qt: a daemon
  `threading.Thread`. The updater and the resource compiler launch use this.

Guard state shared between workers with a lock. `ElementIDGenerator` is the
worked example.

Use comments only for important, non-obvious constraints or reasoning.

## Required Validation

Run the checks affected by the change:

- C#: Release build, `dotnet format`, and relevant tests.
- New TUnit Core suites: `dotnet run --project <test-project>`.
- Legacy xUnit suites: `dotnet test <test-project>`.
- Python or bridge changes: affected Python tests.
- Python changes: `python -m pyflakes Hammer5ToolsGUI/gui` must report no
  `undefined name` errors.

Before finishing, remove debug logging and commented-out code introduced by the
change. Update this file when ownership or a public contract changes.

## Git Policy

- Use focused Conventional Commits: `type(scope): description`.
- Mark breaking changes with `!` before the colon or a `BREAKING CHANGE:` footer.
- Never put AI coding-agent names in branch names, commit messages, PR text, or
  contribution credits.
- Never add generated-by notices or AI `Co-Authored-By` trailers.

After cloning, run:

```sh
git config core.hooksPath .githooks
```

The tracked hook checks local commit messages. CI checks commits pushed to
GitHub.
