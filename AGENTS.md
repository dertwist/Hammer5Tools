# Hammer 5 Tools

Hammer 5 Tools is a Counter-Strike 2 desktop toolkit.

```text
Managed Avalonia GUI -> Hammer5Tools Core (.NET) -> external libraries
Archived Python/PySide6 GUI -> NativeAOT Core
```

## C# migration workspace

The replacement application uses `GUI/CLI -> Core` dependencies:

- `Core/`: typed domain documents, contracts, settings, undo and shared services; no Avalonia dependencies. `IO/` owns filesystem/process integrations and the CS2WorkshopManager adapter. Workshop selection and VPK packing use the pinned upstream library; do not duplicate its packing rules. `AddHammer5ToolsCore` registers shared services for App and Cli.
- `GUI/`: Avalonia views, presentation state, editor lifecycle, update checks and single-instance startup. `Controls/WorkspaceView.cs` owns Dock layouts and persistence; preferences use the shared settings service and semantic theme resources. The managed executable starts directly; the C++ launcher has been removed.
- `CLI/`: command-line presentation.
- App startup accepts `--tool soundevents`, `--tool mapbuilder`, `--tool smartprops` and `--tool workshop`. `Services/ToolWindowService.cs` creates only the requested UI and reuses existing tool windows; all modes share the same process and Core services. `Services/Lifecycle/SingleInstanceGuard.cs` forwards launch requests over a current-user named pipe. The process exits on its last window closing. Standalone windows use the existing editor views, preserve dirty documents on cancellation, and confirm all open documents before shared installation changes. Addon selection does not affect independent editor documents. Optional Windows shortcuts use the thin editor launchers, sharing one managed application through `CreateToolShortcuts.ps1`.
- `Core/CS2WorkshopManager/`, `Core/Steamworks/`, and `GUI/CS2WorkshopManager/`: pinned upstream library, Steamworks and GUI projects. Core references the library; App hosts the GUI in-process, including standalone startup. `Misc/CS2WorkshopManager/` retains shared upstream build settings, provenance and licenses. Local build imports and `.editorconfig` files preserve upstream settings; parent Core and GUI projects exclude nested project sources. Run `dotnet format --exclude Core/Steamworks Core/CS2WorkshopManager GUI/CS2WorkshopManager` for owned code.
- `Presets/`: immutable shipped addon, editor and hotkey assets; addon presets live under `Presets/Addons/`. Published preset paths remain `presets/addons`, `presets/soundeventeditor`, and `presets/smartpropeditor`.
- The application project is `GUI/Hammer5Tools.csproj`, producing `Hammer5Tools.dll`; its existing `Hammer5Tools.App` namespaces are retained. The shared library remains `Core/Hammer5Tools.Core.csproj`. The NativeAOT workspace remains `Core/NativeAot/`.
- `Tests/Hammer5Tools.App.Tests/`: headless Avalonia render and lifecycle regression tests.

Python views remain the layout and lifecycle baseline. Preserve panel placement and dialog field order when porting them, while allowing the Explorer and editor panels to dock and float. Confirm affected dirty documents before closing, changing addons or changing installations. A cancelled or failed save must retain dirty state. Source-document writes validate, stage, retain `.bak` files and replace atomically.

`IResourceCompiler` retains its existing asset compile overload and adds an overload for map-build arguments, with cancellation terminating the process tree. `ILoadingScreenService` includes addon-description loading and SVG map-icon application; parsing and IO are kept out of views. The legacy ownership rules below apply to the existing Python/NativeAOT application, not the replacement managed application. Neither application is removed until migration parity is verified.

The managed Map Builder uses Core `MapBuildOptions` for compiler flags and
`MapBuildConfiguration` for saved presets. Core `IO/MapBuilder/` owns the serial build
queue, confined VMAP resolution, live compiler output, retained build logs and
system usage counters. `MapBuildJob.OutputLogs` is a thread-safe snapshot;
workers append through `AppendOutput`. The legacy enum build overload remains
available. App owns option presentation and usage charts; unavailable counters
are null, never simulated percentages.

The managed console uses Core `IO/Commands/` for command pipes and the console log
under `game/csgo/`. It leaves VConsole's client slot available for `vconsole2.exe`.
Core loads shared Convar Helper INI pages from `game/core/tools/convarhelper/workshop`
and user pages from `HKCU/Software/Valve/ConVarHelper/Tabs`, exposing command presets
through `ICommandService.HelperCommands`, including authored page dimensions, cell positions
and section headings. App presents a resizable right-hand page/button grid and owns Enter-to-send, helper search,
bounded batched output and pausing display. The standalone VConsole protocol client
remains available for its regression tests; the application console does not use it.
Legacy VConsole interface members remain inert for older application assembly compatibility.
`CommandPipeHost` runs in a hidden `--command-pipe-host` invocation of the managed
executable, bypassing GUI/single-instance startup. It retains CS2's command pipe handles
across UI exits/restarts; `CommandPipeClient` reconnects through a current-user control
pipe. The host exits after 30 seconds without an app client or connected game.
GUI and CLI recognize this internal mode. CS2 launch waits for host readiness before
starting the engine. App service shutdown detaches its client and log listener only;
it does not terminate the host or CS2. Pipe output is drained by the host; the app
receives game output through its independently restarted console log listener.

## Mandatory Workflow

When integrating another upstream application, keep its domain/library projects under `Core/<component>/`, its UI under `GUI/<component>/`, and provenance, licenses and shared upstream build files under `Misc/<component>/`. Preserve separate assemblies, upstream settings and dependency versions; exclude nested sources from the parent projects. Review UI framework compatibility before in-process hosting. Source2Viewer is a future integration, not bundled source in this repository.

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

- `GUI/Services/`: managed application startup, single-instance
  ownership and update checks; shared filesystem/process services stay in Core.
- `legacy/Hammer5ToolsGUI/gui/`: PySide6 views, input, presentation state, and OpenGL
  drawing only.
- `legacy/Hammer5ToolsGUI/core/`: the pure-Python NativeAOT `ctypes` bridge.
- `legacy/Hammer5ToolsGUI/automation/`: MCP/CLI transport, schemas, request-time settings,
  and response shaping. Compilation, source-asset mutation, map authoring,
  model bounds, and texture-channel preparation run in Core through CoreBridge.
- `legacy/Hammer5ToolsGUI/keyvalues3/`: the standalone KV3 library.
- `Core/NativeAot/`: native exports and the remaining NativeAOT domain logic. This includes Source 2 parsing,
  VPK/resource access, SmartProp evaluation, VMAP work, conversions, Source
  porting, and Unreal extraction.
- `legacy/Hammer5ToolsGUI/Tests/`: Python regression and characterization tests.
- `legacy/Hammer5ToolsGUI/gui/tools/`: external tools and scripts shipped with the app.
- `../Source2Houdini/`: separate Houdini 21 package and SOP presentation adapters.
  Source 2 interpretation remains in Core, accessed through its NativeAOT C ABI.
- `makefile.py`: build and packaging entry point.
- `version.json` and `legacy/Hammer5ToolsGUI/gui/common.py`: application version.

The GUI must use `CoreBridge` for domain work. Do not duplicate Core logic in
Python. Do not expose .NET namespaces to editors. Shipped code must not use
pythonnet, CLR reflection, or a subprocess CLI.

The Core must remain independent of the GUI. Keep it as one C#
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
pasting components. Managed hierarchy requests perform atomic batch moves, copies,
grouping, renames and clipboard insertion; file-reference imports resolve CS2
content paths in Core IO. Editor paths are arrays of object keys and
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
- Put global styling in `legacy/Hammer5ToolsGUI/gui/styles/`. Do not add inline palettes.
- Read settings at the point of use. Do not cache settings in module globals.
- Import setting accessors from `gui.settings.common`. Use `gui.settings.main`
  only for the Preferences dialog.
- Report failures with `logging.getLogger(__name__)`. Do not use `print()` for
  diagnostics because shipped builds have no console.
- Add a new editor by adding one `EditorSlot` to `MainWindow._editor_slots` and
  one build method. Do not add editor names to any other list.

### Background work

Pick the mechanism by the shape of the job, and never touch a widget off the GUI
thread â€” build data in the worker and emit it to a slot that builds the widgets.

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
- Python changes: `python -m pyflakes legacy/Hammer5ToolsGUI/gui` must report no
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

## Managed SmartProp editor

`GUI/Features/SmartProps/` owns the integrated Avalonia view,
hierarchy interactions, presentation and OpenGL rendering. `Tests/Hammer5Tools.SmartProp.Tests/`
owns its headless and native GPU regression host. The editor participates in the shell's
document tabs, dirty-file prompts and save/undo commands.

`Core/Format/`, `Core/IO/` and the root Core API files own the shared SmartProp
domain/resource sources. The managed Core compiles them directly; the project in
`Core/NativeAot/` links the same files into its native DLL. NativeAOT regression
projects live under `Tests/Hammer5Tools.NativeAot.Tests/` and
`Tests/SourcePorter.Core.Tests/`, with a separate solution at
`Core/NativeAot/Hammer5Tools.NativeAot.slnx`. Keep these sources shared; do not duplicate evaluators,
hierarchy mutations or source serialization in the App. `CoreApi.SmartProps.cs`
is the shared public editor contract.

SmartProp evaluation is shared source in `Core/Format/SmartProps/Evaluation/`, compiled into both managed Core and NativeAOT. Preserve its upstream license and pinned provenance in `Misc/Source2Viewer/`; evaluator regression tests live in `Tests/Hammer5Tools.Core.Tests/SmartProps/`. ValveResourceFormat comes from NuGet and requires ValvePak 5.
Keep the managed Core and integrated Workshop library on that same
version and retain the Workshop chunking/CRC/checksum regression tests when
updating these dependencies.

The Python application is archived in `legacy/`. Workshop UI is referenced as a library and hosted in-process in a shell editor tab; `--tool workshop` and the Workshop launcher open or focus that tab in the main window. Workshop is the initial active shell tab. The tab retains its view and submission state across editor and addon switches. Do not launch a separate Workshop executable.

Shell startup opens Workshop Manager, Loading Screen, Hotkey, SoundEvent and SmartProp editor tabs, with Workshop active. Editor views load when selected; additional editors open from the Editors menu; utility tools (Map Builder, Console, Asset Tools, NavMesh Radar and Git Sync) open as dialogs and can be dragged into the editor tab strip. Dialog-to-tab transfer preserves the document and its state. `Controls/EditorHost` retains loaded editor trees attached but hidden, preserving Dock contexts. Editors can be closed with dirty-document confirmation and reopened from the Editors menu; addon changes do not reopen closed tools. Core `ICs2Launcher.RestartSteamAsync` owns graceful Steam shutdown and restart, with cancellation and a bounded wait. App exposes it in Tools and reports status. Shared managed typography uses Workshop's bundled Inter font; `Styles/ValveControls.axaml` uses the linked legacy Valve icon set for control states. The bottom bar retains its original icons.

`build.ps1` owns the shared local/GitHub Actions managed build, validation, publish and Velopack packaging workflow. `.config/dotnet-tools.json` pins vpk to the App's Velopack package version. App `Program.Main` runs Velopack before argument parsing and single-instance startup. `installer/Hammer5Tools.iss` optionally wraps installation/portable extraction; Velopack owns installed-mode uninstallation. The managed package ID is separate from legacy until migration parity is verified. Packaging does not implement profile migration or portable data paths.

Managed startup failures automatically open `Services/Updates/UpdateWindow` with an independent updater, without requiring CS2, settings or editor services or a special launch command. Failed application XAML/theme initialization falls back to basic Fluent controls for recovery. Main and standalone editor Help menus expose the same check/download/install UI. Updates use Velopack GitHub Releases feeds (`releases.stable.json` / `releases.dev.json`) and require the matching managed packages to be published there; CI artifact uploads alone are not an update feed. Restart confirms all tracked dirty documents; failed checks/downloads remain retryable. This recovery path requires the managed runtime and Avalonia framework to load; it cannot repair a missing executable/runtime.

Self-contained Windows publishing places shared assemblies/runtime in `bin`, with `Hammer5Tools.exe`, `SoundEventEditor.exe`, `MapBuilder.exe`, `SmartPropEditor.exe` and `WorkshopManager.exe` as .NET apphosts loading the same managed assembly. The executable basename chooses the default tool; explicit `--tool` arguments override it. SmartProps participates in the existing standalone lifecycle and dirty-document checks. Immutable shipped presets live in `presets/addons`, `presets/soundeventeditor` and `presets/smartpropeditor`; Core `IO/BundledPresetFiles` resolves them from both development and published runtime locations. User preset roots remain separate and retain priority. Velopack's mandatory outer layout remains unchanged.

Managed addon creation uses Core `IO/Addons/AddonPresetFiles` for preset discovery, thumbnail reading and staged content/game copying with legacy filename-token substitution. App `Services/AddonDialogs.cs` owns the creation/export dialogs. `AddonArchive` retains its original export overload and adds filtered selection, compression, cancellation and progress through `AddonExportOptions`; cancelled exports retain the previous archive. Bundled presets come from `Presets/Addons`, with user presets taking precedence. Core `Cs2/LaunchOptions` owns launch argument construction and legacy command migration; Settings presents its switches and preview. NCM launches prepare missing internal configuration files and use `-nocustomermachine`.

Standalone SoundEvent, SmartProp and Map Builder windows own document menus and file selection, without subscribing to the shared addon selection. `Features/Shell/EditorMenus.cs` supplies editor actions for standalone menus and shell dynamic menus. Independent shell editor tabs survive addon changes; only Loading Screen and Detail Prop documents are reset. Core `Cs2Paths.GetContentAddonName` resolves file context for SmartProp resources and Map Builder compilation. Editor icons ship in `icons/` and are embedded into each thin launcher by `GUI/LauncherIcons.targets`. Editor shortcuts target those launchers, which all load the same managed application.
