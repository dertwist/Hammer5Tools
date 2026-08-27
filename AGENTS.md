# Hammer 5 Tools

Hammer 5 Tools is a Counter-Strike 2 desktop toolkit. The target design is a PySide6 GUI over reusable .NET domain code, with an optional, minimal C++ launcher.

## Read First

- [STYLESHEET.md](STYLESHEET.md) before changing any UI.
- Use `codebase-memory-mcp` (`search_graph`, `get_architecture`, `trace_path`) to find existing modules, classes, and call chains before writing new code — this repo has no separate static code-index doc; the graph is the source of truth and won't go stale.

## Architecture

```text
C++ launcher (optional) -> Python/PySide6 GUI -> Hammer5Tools Core (.NET) -> external libraries
```

- `Hammer5ToolsLauncher/`: startup, single-instance IPC handoff, crash reporting, update startup only.
- `Hammer5ToolsGUI/gui/`: windows, widgets, layouts, styling, input, presentation state. Must not parse Source 2 formats or duplicate a core evaluator — go through `CoreBridge` (`core/bridge/`).
- `Hammer5ToolsGUI/core/`: Python bridge to the C# core (NativeAOT `ctypes`, `core/native.py`). Pure Python, lives beside `gui/`, not under `Hammer5ToolsCore/`.
- `Hammer5ToolsGUI/keyvalues3/`: standalone KV3 read/write library.
- `Hammer5ToolsCore/`: 100% C#, one project (`Hammer5Tools.Core`), publishing as one NativeAOT native DLL. Source 2 parsing, resource/VPK access, SmartProp evaluation, VMAP processing, format conversions, Source-to-CS2 porting, and Unreal content extraction all live here, organized VRF-style: `IO/` (accessing the external environment — archives, processes, filesystem/install layout) and `Format/` (interpreting or converting a specific file format's bytes). The root of the project holds the public contract (`CoreApi.cs`) and the `[UnmanagedCallersOnly]` ABI surface (`NativeApi.cs`, `ResourcesApi.cs`, `VmapApi.cs`, `SourcePorterApi.cs`, `UnrealBridgeApi.cs`, `VmapMergeApi.cs`, and more as the ABI grows) — GUI code goes through this ABI via `core/native.py`/`bridge/core.py`. No pythonnet, no CLR reflection, no subprocess CLI anywhere in the shipped app. Never depends on GUI or launcher.
- SmartProp evaluation returns both model placements and editor widget placements; the GUI only adapts these Core-owned results for OpenGL drawing.
- Consume external libraries as dependencies; keep Hammer5Tools behavior in Hammer5Tools-owned code.
- `Hammer5ToolsGUI/Tests/`: Python regression and characterization tests.
- `Hammer5ToolsGUI/gui/tools/`: bundled external tools and scripts (bspsrc, import/UE scripts) shipped alongside the packaged app.
- `makefile.py`: build and packaging entry point; `Hammer5ToolsGUI/gui/common.py`/root `version.json` own the application version.

## Before Writing New Code

**Adding a feature or function:**
1. Is something similar already implemented in this project?
2. Do existing functions/utilities already cover this?
3. Does a new method actually earn its place, or should an existing one be extended instead?

**Adding or reaching for a library:**
1. Does the project already have a dependency that does this?
2. How heavy is this dependency (size, transitive deps, install cost)?
3. If you'd only use a handful of functions from a large library, would a smaller focused library — or a few lines of your own code — serve better?

## .NET Style

Follow VRF conventions for all new or migrated C# code: latest supported .NET, nullable references, file-scoped namespaces, 4 spaces, LF, final newlines, Allman braces. `var` for locals; collection expressions; pattern matching/switch expressions; null-coalescing/throw expressions; string interpolation; `MathF`; `using` declarations; early returns. Expression bodies for properties/indexers/accessors, block bodies for methods/constructors. `System` usings first, remove unused. PascalCase types/members/private fields, camelCase locals/parameters, `I`-prefixed interfaces. Prefer exact names (`Reader`, `Writer`, `Evaluator`, `Context`, `Document`, `Service`) over `Manager`/`Handler`/`Controller`. Seal internal types when appropriate; concise XML docs on public core APIs. Comments explain non-obvious reasons only, plain ASCII, no narration of changes/sessions.

## Python Style

`snake_case` for functions, methods, variables, and module names; `PascalCase` for classes; `UPPER_SNAKE` for constants; a single leading underscore for module-private names. 4 spaces, LF, final newlines. Prefer exact names (`Reader`, `Writer`, `Document`, `Evaluator`, `Viewport`) over `Manager`/`Handler`/`Utils`/`Methods`/`Objects`. No Hungarian notation. Name a module for what it contains rather than its position in the tree — prefer `mapbuilder/dialog.py` over another `main.py`. Type hints on new public functions. Comments explain non-obvious reasons only; no narration of changes or sessions.

**Qt virtual overrides keep Qt's camelCase.** `paintEvent`, `eventFilter`, `sizeHint`, `filterAcceptsRow`, `mimeData`, `rowCount`, `initializeGL`, `mergeWith`, `drawBranches`, `showPopup`, `tabInserted` and the rest are framework dispatch points. Renaming one to `snake_case` does not raise — Qt simply stops calling it and the feature dies silently. Never bulk-convert method casing: most camelCase methods under `gui/` are framework overrides, not project-owned names.

Renaming a class means updating four places Python tooling does not reach: `.ui` `<class>` entries (or `pyside6-uic` regenerates the old name), QSS type selectors (`BoxSlider`, `CompletingPlainTextEdit`, `ConsoleWidget` are styled by class name, and `Tests/test_qss_selectors.py` guards only `#objectName` and `[prop="value"]`), `resources.qrc` paths, and any `QSettings` key string — which must *not* follow the rename, or users lose their preferences on upgrade. One symbol per commit; `git grep -w` the old name across `*.py`, `*.ui`, `*.qss`, `*.qrc` before and after.

## Python and UI Rules

- Keep Python domain-free: use bridge adapters (`CoreBridge`) rather than exposing .NET namespaces or assembly loading to editors.
- UI code is view composition, binding, input routing, dialogs, rendering, and user feedback only.
- Use the global style system in `Hammer5ToolsGUI/gui/styles/`; no hard-coded inline palettes. Follow [STYLESHEET.md](STYLESHEET.md).
- No `from x import *`. `gui/` is star-import-free — keep it that way so pyflakes can see every name; star imports hide undefined names from static analysis entirely.
- Read configuration at point of use. No module-level `value = get_something()` snapshots: they freeze the value at import time, so a Preferences change silently does nothing until restart.
- Import settings accessors from `gui.settings.common`. `gui.settings.main` is the Preferences dialog and nothing else — importing config from it drags a `QDialog` and its widget tree into every consumer.
- Report failures through `log = logging.getLogger(__name__)`, not `print()`. Shipped builds have no console (`no_console.py`), so a printed diagnostic in an `except` block is invisible in the field; `gui/logs.py` writes to the same `logs/` directory as the crash handler.
- Preserve existing behavior while migrating. Add characterization tests/fixtures before moving uncovered behavior.

## Code Comments

Before adding a code comment, answer these questions:

1. Is it necessary because the code is difficult to understand without it?
2. How important is the information it conveys?
3. Is it concise enough to justify the reader's time?
4. Does it help a user or maintainer make a better decision or avoid a mistake?

Prefer no comment when the code is self-explanatory. Keep necessary comments short, specific, and focused on non-obvious constraints or reasoning.

## Commits & Branches

Conventional Commits: `type(scope): description`, e.g. `feat(smartprop): add vector scaling support`, `fix(soundevent): resolve path normalization`. Breaking change: `!` before the colon or a `BREAKING CHANGE:` footer. Keep commits short and focused on one change.

**MUST NOT** mention AI coding agents (Claude, Codex, Gemini, ChatGPT, or any other AI agent name) in branch names, commit messages, PR descriptions, or contribution credits.

## Before Finishing

1. Keep the change small and modular; update this file when module ownership or public contracts change.
2. Build the project being changed while iterating. For a completed .NET change: Release build, `dotnet format`, relevant test suites. Run new TUnit core suites with `dotnet run --project <test-project>` until the legacy xUnit suite is migrated to Microsoft Testing Platform.
3. Run affected Python tests for Python or bridge changes.
4. For Python changes, `python -m pyflakes Hammer5ToolsGUI/gui` must report no `undefined name`.
5. Remove debug logging and commented-out code introduced by the change.
6. Use focused Conventional Commits. Do not include AI agent names in branches, commits, or credits.
