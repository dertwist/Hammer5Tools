# Hammer 5 Tools

Hammer 5 Tools is a Counter-Strike 2 desktop toolkit. The target design is a PySide6 GUI over reusable .NET domain code, with an optional, minimal C++ launcher.

## Read First

Before changing code, read:

- [ARCHITECTURE.md](ARCHITECTURE.md) for module ownership and existing APIs.
- [STYLESHEET.md](STYLESHEET.md) before changing any UI.
- [ConventionalCommits.md](ConventionalCommits.md) before creating a branch or commit.

## Architecture

```text
C++ launcher (optional) -> Python/PySide6 GUI -> Hammer5Tools Core (.NET) -> external libraries
```

- The launcher owns startup, single-instance IPC handoff, crash reporting, and update startup only.
- The GUI owns windows, widgets, layouts, styling, input, and presentation state.
- The core owns Source 2 parsing, resource and VPK access, SmartProp evaluation, VMAP processing, conversions, and other non-UI logic.
- The core must never depend on the GUI or launcher. The GUI must not directly use VRF, parse Source 2 formats, or duplicate a core evaluator.
- `src/net_core/SourcePorter.Core` remains authoritative for its existing features until a deliberate migration or shared abstraction replaces it. Do not create competing implementations.
- Consume external libraries as dependencies; keep Hammer5Tools behavior in Hammer5Tools-owned code.

## Project Layout

- `src/`: Python application, editors, widgets, styles, and bridge adapters.
- `src/net_core/`: .NET libraries and tests. New shared domain code belongs in `Hammer5Tools.Core`.
- `src/external/`: packaged third-party assemblies; do not edit vendor code for product behavior.
- `dev/tests/`: Python regression and characterization tests.
- `makefile.py`: build and packaging entry point. `src/common.py` owns the application version.

## .NET Style

Follow the applicable VRF conventions for all new or migrated C# code:

- Use the latest supported .NET, nullable references, file-scoped namespaces, four spaces, LF line endings, final newlines, and Allman braces.
- Use `var` for locals; collection expressions; pattern matching and switch expressions; null-coalescing and throw expressions; string interpolation; `MathF`; `using` declarations; and early returns where they clarify flow.
- Use expression bodies for properties, indexers, and accessors; use block bodies for methods and constructors.
- Sort `using` directives with `System` first and remove unused directives. Do not use `this.` unless it resolves ambiguity.
- Use PascalCase for types, members, and private fields; camelCase for locals and parameters; `I`-prefixed PascalCase for interfaces. Namespaces loosely follow folders.
- Prefer exact names such as `Reader`, `Writer`, `Evaluator`, `Context`, `Document`, or `Service`; avoid vague `Manager`, `Handler`, and `Controller` names.
- Seal internal types when appropriate. Public core APIs need concise XML documentation; use `<inheritdoc/>` where it adds nothing.
- Comments explain non-obvious reasons, workarounds, or TODOs—not the code. New C# comments must be plain ASCII and must not narrate changes, sessions, or external format provenance.

## Python and UI Rules

- Keep Python domain-free as core APIs become available: use bridge adapters rather than exposing .NET namespaces or assembly loading to editors.
- Keep UI code to view composition, binding, input routing, dialogs, rendering, and user feedback.
- Use the global style system in `src/styles/`; no hard-coded inline palettes. Follow [STYLESHEET.md](STYLESHEET.md).
- Preserve existing behavior while migrating. Add characterization tests or fixtures before moving uncovered behavior.

## Before Finishing

1. Keep the change small and modular; update architecture documentation when ownership or public contracts change.
2. Build the project being changed while iterating. For a completed .NET change, run Release build, `dotnet format`, and relevant test suites. Run new TUnit core suites with `dotnet run --project <test-project>` until the legacy xUnit suite is migrated to Microsoft Testing Platform.
3. Run affected Python tests for Python or bridge changes.
4. Remove debug logging and commented-out code introduced by the change.
5. Use focused Conventional Commits. Do not include AI agent names in branches, commits, or credits.
