# Hammer 5 Tools

Hammer 5 Tools is a Counter-Strike 2 desktop toolkit.

```text
Optional C++ launcher -> Python/PySide6 GUI -> Hammer5Tools Core (.NET) -> external libraries
```

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
- `Hammer5ToolsGUI/keyvalues3/`: the standalone KV3 library.
- `Hammer5ToolsCore/`: all domain logic. This includes Source 2 parsing,
  VPK/resource access, SmartProp evaluation, VMAP work, conversions, Source
  porting, and Unreal extraction.
- `Hammer5ToolsGUI/Tests/`: Python regression and characterization tests.
- `Hammer5ToolsGUI/gui/tools/`: external tools and scripts shipped with the app.
- `makefile.py`: build and packaging entry point.
- `version.json` and `Hammer5ToolsGUI/gui/common.py`: application version.

The GUI must use `CoreBridge` for domain work. Do not duplicate Core logic in
Python. Do not expose .NET namespaces to editors. Shipped code must not use
pythonnet, CLR reflection, or a subprocess CLI.

The Core must remain independent of the GUI and launcher. Keep it as one C#
project and publish it as one NativeAOT library. Put environment access in
`IO/`, format interpretation and conversion in `Format/`, public contracts in
`CoreApi.cs`, and unmanaged ABI methods in the root `*Api.cs` files.

The Core owns SmartProp evaluation results. The GUI only adapts those results
for display.

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
