# Project Architecture & Code Index

This document provides a concise indexation of the modules, classes, functions, methods, and data flows within **Hammer 5 Tools**.

---

## 1. Core Application Engine

### Launcher & Lifecycle (`Hammer5ToolsGUI/hammer5tools_gui/main.py`)
- **`main()`**: Entry point routine parsing CLI parameters (`--dev`, `--addon`), configuring PySide6 DLL search paths (`os.add_dll_directory`), handling Velopack installer hooks, instantiating `QApplication`, loading custom bundled fonts, setting window icons, and initializing `AppCore`.
- **`_handle_velopack_hook(argv)`**: Intercepts Velopack/Squirrel installation, update, or uninstallation arguments (`--velopack-install`, `--velopack-uninstall`) to run background file tasks without starting the PySide GUI.

### Native Lifecycle Host (`Hammer5ToolsLauncher/`)
- **`Hammer5Tools.exe`**: Installed entry point. It handles installer hooks, owns the process-lifetime instance mutex, forwards versioned requests to the GUI IPC server, supervises `app/Hammer5ToolsGUI.exe`, and reports startup failures.
- **`request.hpp` / `request.cpp`**: UI-neutral launcher protocol parsing, Windows argument quoting, path normalization, and JSON serialization. Protocol version 1 carries command, target file, editor type, original arguments, and working directory.
- Direct `Hammer5ToolsGUI/hammer5tools_gui/main.py` startup remains supported for development. When `H5T_LAUNCHER_OWNS_INSTANCE=1`, Python skips duplicate instance arbitration but still owns the IPC server and all request handling.
- Exit code `75` is the supervised restart contract. The launcher starts a clean GUI process without replaying the original open/quick-action arguments; all other child exit codes are propagated.

### Application Orchestrator (`Hammer5ToolsGUI/hammer5tools_gui/app_core.py`)
- **`AppCore` Class** (`QMainWindow`): Primary application controller managing main UI state, docking layouts, local IPC server, system tray icon, file watching, and standalone editor instances.
  - `__init__(app, args)`: Applies global dark QSS stylesheet, starts local IPC server socket (`QLocalServer`), sets up tray menu, and restores window settings.
  - `init_ui()`: Instantiates `UiMain` to set up main tabs, toolbars, status bar, and dockable windows.
  - `handle_ipc_message(message)`: Process incoming single-instance commands or external open request payloads.
  - `open_smartprop_editor(path=None)`: Launches or focuses the SmartProp Editor tab/window.
  - `open_soundevent_editor(path=None)`: Launches or focuses the SoundEvent Editor tab/window.
  - `run_map_builder()`: Opens the CS2 Map Builder modal dialog.
  - `run_addon_exporter()`: Launches the Addon Porter export/import dialog.

### Primary Layout Manager (`Hammer5ToolsGUI/hammer5tools_gui/ui_main.py`)
- **`UiMain` Class**: Binds compiled Qt layout (`Hammer5ToolsGUI/hammer5tools_gui/main.ui`) components to `AppCore`.
  - `setupUi(QMainWindow)`: Initializes top-level tab widget, menu bar actions, toolbars, and dock containers.
  - `bind_events()`: Maps menu actions, keyboard shortcuts, and tab events to core controller handlers.

---

## 2. Common Utilities & Data Parsers

### Common Helpers (`Hammer5ToolsGUI/hammer5tools_gui/common.py`)
- **`generate_unique_name(base_name, existing_names, separator="_")` -> `str`**: Generates non-conflicting names by incrementing numeric suffixes (`_01`, `_02`).
- **`app_version`**: GUI compatibility alias for the version loaded from root `version.json`.
- **`JsonToKv3(json_data)` -> `str`**: Serializes Python dictionary/JSON structures into Valve KeyValues3 (KV3) format.
- **`compile(file_path)`**: Calls `resourcecompiler.exe` for CS2 assets (`.vsmart`, `.vsndevts`, `.vmap`).
- **`get_counter_strike_path_from_registry()` / `get_steam_install_path()`**: Locates Steam installation directories and CS2 game paths via Windows Registry.

### KeyValues3 Parser Engine (`keyvalues3/`)
- Native Python KV3 encoder/decoder handling text representation, type headers (`<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-3596-4313-a41f-70c3226768f9} -->`), and type annotations.

### SmartProp Preview Domain (`Hammer5ToolsGUI/hammer5tools_gui/editors/smartprop_editor/viewport_3d/engine/`)
- **`EvalContext`**: Resolves SmartProp variables, expressions, scalar values, vectors, and preview-instance state.
- **`evaluate_expression()`**: Safely evaluates the supported Source 2 SmartProp expression subset without Python `eval`.
- **`modifier_evaluator.py` / `path_evaluator.py`**: Applies preview modifiers and path-placement behavior. These are the source behavior for the forthcoming `Hammer5Tools.Core/SmartProps` migration; Qt widgets must not become dependencies of that Core implementation.

---

## 3. Editor Subsystems (`Hammer5ToolsGUI/hammer5tools_gui/editors/`)

### SmartProp Editor (`Hammer5ToolsGUI/hammer5tools_gui/editors/smartprop_editor/`)
- **`SmartPropEditorMainWindow`** (`QMainWindow`): Visual editor for Valve `.vsmart` files.
  - `load_file(path)`: Imports `.vsmart` KV3 structure into the element tree.
  - `save_file(path=None)`: Writes current node hierarchy back to KV3 format.
  - `add_element(element_type)` / `remove_element(node)`: Mutates element tree.
  - `update_preview()`: Updates preview data for 3D viewports and external tools.
- **Modules**: `element_tree.py` (hierarchical node view), `property_editor.py` (attribute inspection), `variable_manager.py` (variables table).

### SoundEvent Editor (`Hammer5ToolsGUI/hammer5tools_gui/editors/soundevent_editor/`)
- **`SoundEventEditorMainWindow`** (`QMainWindow`): Graphical editor for `soundevents_addon.vsndevts`.
  - `load_soundevents(path)`: Imports sound event definitions.
  - `add_soundevent(name)` / `duplicate_soundevent(name)`: Creates/duplicates sound entries.
  - `play_sound(vsnd_path)`: Audio playback preview.
  - `export_kv3()`: Formats and exports sound event KV3 files.

### Additional Editors
- **AssetGroup Maker (`Hammer5ToolsGUI/hammer5tools_gui/editors/assetgroup_maker/`)**: `BatchCreatorMainWindow` for grouping and processing game assets.
- **Hotkey Editor (`Hammer5ToolsGUI/hammer5tools_gui/editors/hotkey_editor/`)**: `HotkeyEditorMainWindow` for managing application shortcuts.
- **Loading Screen Editor (`Hammer5ToolsGUI/hammer5tools_gui/editors/loading_editor/`)**: `Loading_editorMainWindow` for CS2 map loading screen metadata.

---

## 4. UI Widgets & Styling System (`Hammer5ToolsGUI/hammer5tools_gui/widgets/` & `Hammer5ToolsGUI/hammer5tools_gui/styles/`)

### Global QSS Stylesheet (`Hammer5ToolsGUI/hammer5tools_gui/styles/qt_global_stylesheet.py`)
- **`QT_Stylesheet_global`**: Primary Qt QSS stylesheet string defining dark palette (`#272727`, `#2E2E2E`, `#2F2F31`, `#E5E5E5`, `#464649`, `#515965`).

### Styling Helpers (`Hammer5ToolsGUI/hammer5tools_gui/styles/common.py` & `property_icons.py`)
- Utility functions for tab styling, palette colors, and property type icon generation.

### Theme Brightness (`Hammer5ToolsGUI/hammer5tools_gui/styles/theme.py`)
- **`set_brightness_level(level)`**: Activates interface brightness 1/2/3 (`APP/brightness_level` in settings.ini; level 2 = identity).
- **`install()`**: Patches `QWidget`/`QApplication` `setStyleSheet` so every stylesheet is mapped to the active level; `reapply()` restyles all live widgets (instant switching from Preferences → General).
- **`color()` / `qcolor()` / `gl_clear_color()`**: Level-aware lookups for QPainter and OpenGL sites that bypass stylesheets.

### Reusable Widgets (`Hammer5ToolsGUI/hammer5tools_gui/widgets/`)
- **`CustomTreeWidget` (`Hammer5ToolsGUI/hammer5tools_gui/widgets/tree.py`)**: Enhanced `QTreeWidget` with drag-and-drop support, inline editing, and custom signals.
- **`ConsoleWidget` (`Hammer5ToolsGUI/hammer5tools_gui/widgets/console.py`)**: Embedded logger and output viewer.
- **`Property Inspectors` (`Hammer5ToolsGUI/hammer5tools_gui/editors/smartprop_editor/property/`)**: Specialized property inputs for Vector3, Color, Resource picker, and Enums.

---

## 5. System Interop & Build Pipeline

### .NET / C# Interop (`Hammer5ToolsCore/Python/hammer5tools_core/dotnet.py`)
- **`check_dotnet_runtime()` -> `bool`**: Checks for required .NET runtimes.
- **`DotNetManager`**: Interop wrapper utilizing `pythonnet` to invoke C# DLL binaries in `Hammer5ToolsCore/CSharp/external/`.

### Core Bridge (`Hammer5ToolsCore/Python/hammer5tools_core/bridge/`)
- **`CoreBridge`**: Process-wide Python adapter that loads the public `Hammer5Tools.Core` contract once, translates load failures, and exposes a read-only contract probe.
- **`VpkIndex`**: Python-native disposable wrapper for Core VPK lookup, reads, and entry enumeration; UI code must use this instead of direct ValvePak imports. Model Browser VPK scanning consumes this contract.
- **`CoreBridge.evaluate_smartprop_expression()`**: Python-native SmartProp expression entry point; Core namespaces remain inside the bridge.
- **`CoreBridge.evaluate_smartprop()`**: Converts editor document dictionaries and nested document graphs to Core input and returns Python-native evaluated models and diagnostics. These VRF-produced placements are authoritative; Python retains only editor handles, gizmo interaction, path drawing, and element-dot presentation.
- **`CoreBridge.serialize_smartprop()`**: Sends editor document snapshots to the Core-owned VRF KV3 serializer.
- **`CoreBridge.read_valve_map()`**: Loads the SourcePorter implementation of the shared VMAP reader and returns Python-native nodes, entities, asset references, and preview thumbnails. Loading Screen, Cleanup, Create Addon, and SmartProp hierarchy import consume this API instead of loading KeyValues2 or traversing Datamodel objects directly.
- **`CoreBridge.rewrite_vmap_references()`**: Rewrites VMAP body and prefix asset-reference paths through SourcePorter Core and returns a Python-native changed/diagnostics result. Asset Manager uses this API instead of loading Datamodel objects directly.
- **`CoreBridge.write_unreal_map()`**: Sends typed primitive Unreal placements to the SourcePorter Core writer. Python prepares transforms, asset paths, and import accounting; Core owns VMAP skeletons, native entities, SmartProps, decals, encoding, and saving.
- **`CoreBridge.read_compiled_model()`**: Returns Python-native geometry, material, and RGBA texture data decoded by Core. The SmartProp viewport retains background scheduling, NumPy containers, caching, and OpenGL upload only.
- **`CoreBridge.read_compiled_resource()`**: Returns decoded sound bytes or SoundEvent KV3 text with a format tag. SoundEvent widgets retain browsing, playback, cache, dialogs, and export presentation.

### Shared Core Foundation (`Hammer5ToolsCore/CSharp/Hammer5Tools.Core/`)
- **`Hammer5Tools.slnx`**: Managed solution entry point for Core, SourcePorter, bridge, and test projects.
- **`CoreApi.Version`**: Versioned public-contract marker for future Python bridge clients.
- **`CoreResult<T>` / `CoreDiagnostic`**: Typed operation-result and diagnostic contracts shared by future Core features.
- **`Resources.VpkIndex`**: Typed VPK and loose-file lookup boundary backed by ValvePak, shared by SourcePorter and future core consumers.
- **`Resources.CompiledModelReader`**: Owns compiled model, material, texture, skin-group, geometry, and preview texture decoding through ValveResourceFormat and returns immutable primitive contracts.
- **`Resources.CompiledResourceReader`**: Owns compiled sound and SoundEvent extraction from `VpkIndex`, returning decoded bytes and format metadata with structured diagnostics.
- **`Vmap.IValveMapReader` / `ValveMapDocument` / `ValveMapNode`**: Shared UI-neutral, read-only VMAP contracts. `SourcePorter.Core.Vmap.ValveMapReader` implements them by projecting the existing authoritative `VmapDocument`; consumers must not introduce another VMAP parser.
- **`VmapReferenceRewriter`**: Rewrites string paths in the authoritative VMAP document and preserves the binary DMX prefix block, including `map_asset_references`, when saving.
- **`UnrealMapWriter`**: Accepts typed Unreal placement requests and writes binary VMAPs, including native point entities, SmartProp nodes, and half-edge decal overlays, with text fallback and structured diagnostics.
- **`SmartProps.SmartPropExpression` / `SmartPropContext` / `SmartPropValue`**: UI-neutral numeric expressions and typed literal, variable, expression, and vector value resolution for the staged SmartProp migration.
- **`SmartProps.SmartPropEvaluator`**: Converts uncompiled editor document data to VRF evaluation input and maps placed models to Hammer5Tools-owned results and diagnostics.
- **`SmartProps.SmartPropDocumentSerializer`**: Serializes editor document data with VRF's public KeyValues3 writer; serializer output is parsed and evaluated in Core round-trip tests.
- **`Hammer5Tools.Core.Tests`**: TUnit suite for new core behavior; run with `dotnet run --project Hammer5ToolsCore/CSharp/Hammer5Tools.Core.Tests/Hammer5Tools.Core.Tests.csproj` while the legacy xUnit suite remains on VSTest.

### Runtime Roots (`Hammer5ToolsCore/Python/hammer5tools_core/runtime_paths.py`)
- **Install root**: Native launcher, update-owned installation metadata, and the mutable `userdata/` root.
- **Application root**: Immutable packaged GUI payload under `app/`.
- **Runtime root**: PyInstaller and bundled dependency payload under `app/runtime/`.
- The launcher exports these roots through `H5T_INSTALL_ROOT`, `H5T_APP_ROOT`, `H5T_RUNTIME_ROOT`, and `H5T_USER_DATA_ROOT`. Development startup resolves all code roots to the repository and uses `userdata_dev/`.
- Bundled .NET, SourcePorter, Unreal bridge, BSP, UE export, defaults, version, icon, and file-association lookups resolve through this contract. Direct `_MEIPASS` access is isolated to the frozen fallback inside `runtime_paths.py`.

### Auto-Updater (`Hammer5ToolsGUI/hammer5tools_gui/updater/`)
- **`check_updates()`**: Asynchronous update checker using Velopack package releases.
- **`Hammer5ToolsGUI/hammer5tools_gui/updater/attachment_preview.py`**: Attachment extraction from markdown/HTML/assets, asynchronous image caching, thumbnail preview cards, animated GIF playback, and integration with SmartProp Editor's `HelpImageDialog` for full-size viewing.

### Git Sync & VMAP Merge (`Hammer5ToolsGUI/hammer5tools_gui/git_sync/` & `Hammer5ToolsGUI/hammer5tools_gui/gitvmapmerge.py`)
- **`GitController`**: Manages repository sync buttons, commits, and branch operations inside the UI.
- **`gitvmapmerge.py`**: Custom git merge driver for Valve `.vmap` binary and text files.

### Build Engine (`makefile.py`)
- **`makefile.py`**: Build automation script.
  - Root `version.json` is the single release-version authority consumed by Python, C#, CMake resources, CI, `version.txt`, and Velopack.
  - Commands: `--build-all`, `--dev`, `--stable`.
