# Refactoring Continuation Handoff

This document is the restart point for continuing the refactor on another computer. The authoritative long-term roadmap remains the local `docs/REFACTORING_PLAN.md`; this tracked handoff records the current repository state and the next executable work.

## Current Status (2026-08-24)

Phases 1 through 6 are complete on the `refactoring` branch. Phase 3 has Core-owned VMAP and compiled-resource workflows. Phase 4 reduced affected editors to presentation adapters. Phase 5 established the native launcher lifecycle host. Phase 6 established and package-tested the install/application/runtime/userdata layout.

Phases 5 and 6 are complete. Continue with Phase 7 only after reviewing the ownership and runtime boundaries below.

## Resume State

- Repository: `https://github.com/dertwist/Hammer5Tools.git`
- Branch: `refactoring`
- Expected starting commit: `4002ba2e refactor(vmap): route SmartProp imports through core`
- Application version: `6.0.0`
- .NET target: `net10.0`
- Working tree was clean when this handoff was created.
- `origin/refactoring` contains every completed refactoring commit through `4002ba2e`.

On the home PC:

```sh
git clone https://github.com/dertwist/Hammer5Tools.git
cd Hammer5Tools
git fetch origin
git switch --track origin/refactoring
git status
git log -1 --oneline
```

If the repository already exists:

```sh
git fetch origin
git switch refactoring
git pull --ff-only
```

Do not merge `main` into `refactoring` merely to resume the work. First confirm whether new `main` changes are actually needed.

## Required Reading

Before changing code, read:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `ConventionalCommits.md`
4. `STYLESHEET.md` before UI changes
5. This handoff

The local `docs/REFACTORING_PLAN.md` is ignored by Git. Copy the authoritative plan separately to the home PC if it is needed there. Do not reconstruct or overwrite it from progress notes.

## Completed Phases

### Phase 1: Core Foundation and Bridge

Complete.

- Added `Hammer5Tools.Core` and its TUnit test project.
- Added typed results and diagnostics.
- Added the stable Python `CoreBridge` package.
- Migrated SourcePorter and Hammer5Tools Core to .NET 10.
- Centralized ValvePak lookup behind `VpkIndex`.
- Kept VRF and SourcePorter dependency sets isolated.

### Phase 2: SmartProp Domain

Complete.

- VRF/Core owns authoritative SmartProp evaluation.
- Core owns SmartProp KV3 parsing and serialization.
- Nested SmartProps resolve through the Core request.
- Core placements are authoritative in the viewport; the Python model-placement fallback was removed.
- Python remains responsible for presentation interactions such as gizmos, handles, paths, and element markers.
- Every bundled SmartProp Editor preset has Core parse/serialize/evaluate round-trip coverage.

Key commits:

```text
89310a18 feat(smartprop): integrate VRF evaluation
28c68e48 feat(smartprop): connect editor to VRF core
c7d99275 feat(smartprop): resolve nested documents in core
2d5dcd24 feat(smartprop): move KV3 serialization to core
87778fb7 test(smartprop): cover production KV3 round trip
7726e6e4 refactor(smartprop): make core evaluation authoritative
```

## Phase 3: Complete

Phase 3 is complete. VMAP and resource workflows no longer expose VRF, ValvePak, or KeyValues2 domain objects to GUI modules.

### Completed Phase 3 Work

- Added shared `IValveMapReader`, `ValveMapDocument`, `ValveMapNode`, and `ValveMapEntity` contracts in Hammer5Tools Core.
- Kept `SourcePorter.Core.Vmap.VmapDocument` as the only authoritative KeyValues2/DMX VMAP parser.
- Added `SourcePorter.Core.Vmap.ValveMapReader` as a no-write projection into the shared contracts.
- Migrated Loading Editor point-camera discovery to `CoreBridge.read_valve_map()`.
- Migrated Cleanup `map_asset_references` discovery to the bridge.
- Migrated Create Addon VMAP thumbnail extraction to the bridge.
- Migrated SmartProp “Import VMAP into hierarchy” to Python-native Core node projections.
- Added Core VPK entry enumeration and migrated Model Browser VPK scanning.
- Removed the replaced Python VMAP readers from `src/dotnet.py`.
- Moved Asset Manager VMAP reference rewriting into `SourcePorter.Core.Vmap.VmapReferenceRewriter`, including prefix-safe output and Python-native bridge diagnostics.
- Moved Unreal Porter VMAP construction and saving into `SourcePorter.Core.Vmap.UnrealMapWriter`; Python now supplies typed primitive placements and retains import accounting only.

Key commits:

```text
6f0e1ec1 feat(vmap): add shared read-only map contract
c45c7caa refactor(vmap): route loading editor through core
5433a513 refactor(vmap): move cleanup references to core
b2346ff9 refactor(vmap): move thumbnails to core
fa88844e refactor(resources): route VPK scans through core
4002ba2e refactor(vmap): route SmartProp imports through core
```

## Exact Next Work

Complete Phase 3 in the following order. Keep each item as a focused Conventional Commit.

### 1. Asset Manager VMAP Reference Writer

Completed in this continuation slice. The remaining items below are still pending.

Current direct dependency:

```text
src/forms/asset_manager/reference_updater.py
    -> src.dotnet.setup_keyvalues2
    -> Datamodel.NET
```

Target:

- Add a focused SourcePorter Core service such as `VmapReferenceWriter` or `VmapReferenceRewriter`.
- Reuse `VmapDocument.LoadInMemory()` and preserve encoding/version on save.
- Preserve the DMX prefix block and its `map_asset_references` cache. Existing Python behavior uses `src.gitvmapmerge` prefix splicing because Datamodel.NET can drop prefix metadata; characterize this before replacing it.
- Accept a typed rename map and return a typed result containing whether the file changed and structured diagnostics.
- Add synthetic text and binary VMAP tests, including prefix metadata preservation and longest-first, single-pass rename behavior.
- Expose the service through the bridge without leaking Datamodel objects.
- Migrate `ReferenceUpdater._update_vmap_references()` and delete its direct KeyValues2 path only after parity passes.

Suggested commit:

```text
refactor(vmap): move reference rewriting to core
```

### 2. Unreal Porter VMAP Writer

Completed in this continuation. Characterization covers props, transforms, SmartProps, skip accounting, decals, and binary output.

Current direct dependency:

```text
src/forms/unreal_porter/vmap_writer.py
    -> src.dotnet.setup_keyvalues2
    -> Datamodel.NET
```

Target:

- Inventory its public inputs and generated VMAP structure before moving code.
- Add characterization fixtures for representative meshes, entities, transforms, materials, and output encoding.
- Create typed writer input models in Core rather than passing Python dictionaries or raw .NET objects.
- Implement the writer in SourcePorter Core or behind a shared Hammer5Tools Core contract, respecting the existing dependency direction: `SourcePorter.Core -> Hammer5Tools.Core`.
- Bridge JSON or typed primitive requests into the writer.
- Compare generated VMAP output structurally, not only textually.
- Delete direct KeyValues2 loading from the GUI writer after parity.

Suggested commits:

```text
test(vmap): characterize Unreal map output
refactor(vmap): move Unreal map writing to core
```

### 3. SmartProp Viewport Resource Reading

Current direct dependency:

```text
src/editors/smartprop_editor/viewport_3d/vmdl_reader.py
    -> src.dotnet.setup_vrf
    -> ValveResourceFormat managed objects
```

Target:

- Define immutable Core mesh, submesh, material, texture, and diagnostic contracts.
- Keep GPU/OpenGL handles and uploads in the GUI.
- Move compiled `.vmdl_c`, `.vmat_c`, and `.vtex_c` parsing into Core.
- Return primitive buffers and metadata; never expose VRF resources through the public API.
- Add fixture tests for geometry, bounds, indices, UVs, material groups, texture channels, and malformed/missing resources.
- Preserve background loading and caching behavior in `mesh_cache.py`.
- Remove all `setup_vrf` calls from the viewport after output parity.

Do not solve this by returning the VRF assembly or raw reflected types from `CoreBridge`; that would only disguise the dependency.

Suggested commits:

```text
feat(resources): add compiled model reader contract
refactor(viewport): consume core model resources
```

### 4. SoundEvent Resource Reading

Current direct dependencies:

```text
src/editors/soundevent_editor/internal_explorer.py
src/editors/soundevent_editor/internal_soundevent_explorer.py
    -> src.dotnet decode/extract helpers
    -> VPKExtractor / VRF reflection
```

Target:

- Reuse Core `VpkIndex` for archive reads.
- Add typed Core operations for compiled sound decoding and compiled SoundEvent extraction.
- Return bytes/text plus format and structured diagnostics.
- Keep playback, lists, caching, file dialogs, and export choices in the GUI.
- Add production fixtures for WAV, MP3, missing entries, malformed resources, and SoundEvent KV3 extraction.
- Remove GUI imports of `DotNetInterop`, `VPKExtractor`, `decode_vsnd`, and `extract_vsnd_file` after parity.

Suggested commits:

```text
feat(resources): add compiled sound reader
refactor(soundevents): consume core resource APIs
```

### 5. Direct-Dependency Audit and Cleanup

After the migrations, run:

```sh
rg -n "from src\.dotnet|setup_vrf|setup_keyvalues2|DotNetInterop|VPKExtractor" src -g '*.py'
```

Expected intentional exceptions before later phases:

- `src/bridge/core.py` may own transitional Python.NET initialization.
- `src/main.py` and `src/app_core.py` may probe runtime/package availability.
- `src/gitvmapmerge.py` is a standalone Git merge-driver workflow, not a GUI consumer; document its ownership if it remains on KeyValues2.
- `src/forms/source_porter/porter_client.py` is transitional transport and will ultimately move to the Phase 8 NativeAOT boundary. It still must not expose managed domain objects to ordinary GUI modules.

Everything else should be removed or explicitly justified in `ARCHITECTURE.md`.

## Phase 3 Exit Checklist

- [x] Asset Manager VMAP reference rewriting is Core-owned and prefix-safe.
- [x] Unreal Porter VMAP writing is Core-owned and fixture-tested.
- [x] SmartProp viewport model/material/texture parsing is Core-owned.
- [x] SoundEvent compiled resource extraction is Core-owned.
- [x] GUI modules do not import VRF, ValvePak, KeyValues2, or raw managed domain namespaces.
- [x] `CoreBridge` returns Python-native typed models and diagnostics.
- [x] No competing VMAP parser or resource evaluator exists.
- [ ] Relevant Python tests pass.
- [ ] Hammer5Tools Core Release build and TUnit tests pass.
- [ ] SourcePorter Core Release build and xUnit tests pass.
- [ ] `dotnet format` passes for every changed project.
- [ ] Windows packaged Python.NET smoke test passes.
- [ ] Architecture documentation reflects final ownership.
- [ ] Focused commits are pushed to `origin/refactoring`.

## Validation Commands

Run proportionally while iterating, then run the full set before closing Phase 3:

```sh
python3 -m pytest dev/tests/test_core_bridge.py dev/tests/test_loading_vmap_parser.py -q

dotnet format src/net_core/Hammer5Tools.Core/Hammer5Tools.Core.csproj --verify-no-changes --verbosity minimal
dotnet format src/net_core/Hammer5Tools.Core.Tests/Hammer5Tools.Core.Tests.csproj --verify-no-changes --verbosity minimal
dotnet format src/net_core/SourcePorter.Core/SourcePorter.Core.csproj --verify-no-changes --verbosity minimal
dotnet format src/net_core/SourcePorter.Core.Tests/SourcePorter.Core.Tests.csproj --verify-no-changes --verbosity minimal

dotnet build src/net_core/Hammer5Tools.Core/Hammer5Tools.Core.csproj -c Release
dotnet run --project src/net_core/Hammer5Tools.Core.Tests/Hammer5Tools.Core.Tests.csproj -c Release
dotnet build src/net_core/SourcePorter.Core/SourcePorter.Core.csproj -c Release
dotnet test src/net_core/SourcePorter.Core.Tests/SourcePorter.Core.Tests.csproj -c Release
```

The full `net_core.sln` currently includes `UnrealBridge`, whose build requires external CUE4Parse assemblies. A solution-wide failure caused only by missing CUE4Parse is not evidence that Hammer5Tools Core or SourcePorter Core failed; build and report the affected projects separately.

## Last Verified Results

- Python bridge/loading tests: 10 passed.
- Hammer5Tools Core tests: 18 passed.
- SourcePorter Core tests: 119 passed.
- Hammer5Tools Core Release build: passed with zero warnings/errors.
- SourcePorter Core Release build: passed with zero warnings/errors.
- Changed-project formatter checks: passed.
- PySide-dependent viewport tests could not run in the system Python on the original machine because PySide6 was unavailable there.

## Rules While Continuing

- Preserve user changes and unrelated dirty files.
- Use focused Conventional Commits with no AI attribution.
- Do not modify the ignored authoritative plan unless explicitly asked.
- Do not add a second VMAP parser beside `SourcePorter.Core.Vmap.VmapDocument`.
- Do not expose raw VRF, ValvePak, Datamodel, or Python.NET objects through GUI-facing contracts.
- Keep Core free of PySide6 and GUI dependencies.
- Add parity tests before deleting a working implementation.
- Push each completed, validated slice to `origin/refactoring` so work remains portable between computers.

## Phase 4: Complete

- SmartProp model loading is a small Core adapter; background jobs, caching, and GPU ownership remain in `mesh_cache.py`.
- SoundEvent explorers use `CoreBridge` and `VpkIndex` directly and no longer instantiate interop/extractor objects.
- Dead `decode_vsnd` and `extract_vsnd_file` compatibility functions were removed from `src/dotnet.py`.
- Core ownership and bridge APIs are documented in `ARCHITECTURE.md`.

## Phase 5: Complete — C++ Launcher

Phase 5 will refactor the existing `launcher/` into a deliberately small Windows lifecycle host. It must not absorb editor or domain behavior.

1. Define a versioned launcher-to-GUI startup contract covering original arguments, working directory, addon/open-file requests, and a ready/failed status channel.
2. Move first-instance arbitration into the launcher. A second launch will forward its normalized request to the running instance and exit; Python's `QLocalSocket` preflight and `QLocalServer` ownership will then be removed after compatibility tests pass.
3. Start the packaged Python GUI as a supervised child process with explicit executable/runtime discovery, quoted Unicode-safe arguments, inherited environment policy, and deterministic exit-code propagation.
4. Add native crash capture for launcher failures and child startup/early-exit failures. Preserve Python exception reporting for faults after the GUI is running; do not duplicate editor-level error dialogs in C++.
5. Move only update-startup/install-hook dispatch needed before Python starts into the launcher. Update discovery, release notes, user prompts, and progress UI remain in Python until a later lifecycle phase deliberately changes them.
6. Add launcher tests for argument forwarding, stale-instance recovery, concurrent starts, paths containing spaces/non-ASCII characters, missing GUI/runtime, child exit codes, and installer/update hook dispatch.
7. Update packaging so the launcher is the installed entry point while direct Python startup remains available for development.

Phase 5 exit criterion: one native process owns startup, single-instance handoff, early crash reporting, and update startup; the Python GUI owns all windows and application behavior and can still be run directly in development.

### Phase 5 Result

- Added launcher protocol version 1 with normalized commands, target paths, working directory, and original arguments.
- Added native process-lifetime instance arbitration, retrying request forwarding, and abandoned-instance recovery.
- The launcher now supervises the GUI, propagates exit codes, detects IPC readiness, and logs/displays early startup failures.
- Installer hooks remain native; update discovery and UI remain in Python.
- Python skips its duplicate preflight only when explicitly launched by the native host, while direct development startup remains compatible.
- Added native contract tests, a real process-level named-pipe forwarding test, and Python protocol compatibility tests.
- Added supervised restart through exit code 75 and deterministic normal-shutdown exit propagation.
- Validated packaged GUI bootstrap (`--help`) and native installer-hook execution from the installed layout.
- A separate control pipe is unnecessary: child process state provides failure status and named-pipe availability is the readiness boundary.

Phase 5 exit criterion is satisfied: the native process owns startup, instance arbitration, forwarding, early failure reporting, restart, installer hooks, and child supervision while Python owns all windows and application behavior.

## Phase 6: Complete — Runtime Layout and Shipping

- Added a centralized install/application/runtime/userdata path contract in `src/runtime_paths.py`.
- Packaging now stages the immutable GUI in `app/`, with PyInstaller dependencies in `app/runtime/`; the launcher remains at the install root and user data remains in `userdata/`.
- File associations resolve the launcher from the install root rather than assuming it is beside the frozen Python executable.
- Environment-provided roots are covered by regression tests, with a repository-local development fallback.
- Migrated bundled .NET, Core assemblies, Unreal bridge, BSP tool, UE export script, defaults, version, icons, and file associations onto the root contract. `_MEIPASS` remains only inside the centralized frozen fallback.
- CI validates the three required shipping paths before Velopack packaging.
- Repeated full development package builds pass without recursively ingesting prior package output; UI compilation is source-scoped and defaults are explicitly staged.
- Packaged launcher bootstrap and installer hooks pass locally with exit code 0.

Phase 6 exit criterion is satisfied: shipping has distinct launcher/install, immutable application/runtime, and mutable user-data roots; package/update entry points use that layout; and the GUI lifecycle is supervised.

After Phase 5, continue with Phase 6 (three-root structure, shipping, and supervised GUI lifecycle), Phase 7 (cross-language naming/style), and Phase 8 (NativeAOT transport replacing Python.NET).

Do not begin the Phase 6 folder cutover while VMAP/resource ownership is still split across GUI and Core.
