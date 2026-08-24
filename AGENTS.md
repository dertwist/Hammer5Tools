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
- `Hammer5ToolsGUI/`: windows, widgets, layouts, styling, input, presentation state. Must not parse Source 2 formats or duplicate a core evaluator — go through `CoreBridge` (`hammer5tools_core/bridge/`).
- `Hammer5ToolsCore/CSharp/Hammer5Tools.Core`: Source 2 parsing, resource/VPK access, SmartProp evaluation, VMAP processing, conversions, and other non-UI logic. Never depends on GUI or launcher.
- `Hammer5ToolsCore/CSharp/Hammer5Tools.Native`: NativeAOT ABI exposing Core to Python via `ctypes` (`hammer5tools_core/native.py`).
- `src/net_core/SourcePorter.Core` stays authoritative for its existing features until a deliberate migration replaces it — do not create competing implementations.
- Consume external libraries as dependencies; keep Hammer5Tools behavior in Hammer5Tools-owned code.
- `dev/tests/`: Python regression and characterization tests.
- `makefile.py`: build and packaging entry point; `src/common.py`/root `version.json` own the application version.

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

## Python and UI Rules

- Keep Python domain-free: use bridge adapters (`CoreBridge`) rather than exposing .NET namespaces or assembly loading to editors.
- UI code is view composition, binding, input routing, dialogs, rendering, and user feedback only.
- Use the global style system in `src/styles/`; no hard-coded inline palettes. Follow [STYLESHEET.md](STYLESHEET.md).
- Preserve existing behavior while migrating. Add characterization tests/fixtures before moving uncovered behavior.

## Commits & Branches

Conventional Commits: `type(scope): description`, e.g. `feat(smartprop): add vector scaling support`, `fix(soundevent): resolve path normalization`. Breaking change: `!` before the colon or a `BREAKING CHANGE:` footer. Keep commits short and focused on one change.

**MUST NOT** mention AI coding agents (Claude, Codex, Gemini, ChatGPT, or any other AI agent name) in branch names, commit messages, PR descriptions, or contribution credits.

## Before Finishing

1. Keep the change small and modular; update this file when module ownership or public contracts change.
2. Build the project being changed while iterating. For a completed .NET change: Release build, `dotnet format`, relevant test suites. Run new TUnit core suites with `dotnet run --project <test-project>` until the legacy xUnit suite is migrated to Microsoft Testing Platform.
3. Run affected Python tests for Python or bridge changes.
4. Remove debug logging and commented-out code introduced by the change.
5. Use focused Conventional Commits. Do not include AI agent names in branches, commits, or credits.
