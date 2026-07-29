# Project Architecture & Code Index

This document provides a concise indexation of the modules, classes, functions, methods, and data flows within **Hammer 5 Tools**.

---

## 1. Core Application Engine

### Launcher & Lifecycle (`src/main.py`)
- **`main()`**: Entry point routine parsing CLI parameters (`--dev`, `--addon`), configuring PySide6 DLL search paths (`os.add_dll_directory`), handling Velopack installer hooks, instantiating `QApplication`, loading custom bundled fonts, setting window icons, and initializing `AppCore`.
- **`_handle_velopack_hook(argv)`**: Intercepts Velopack/Squirrel installation, update, or uninstallation arguments (`--velopack-install`, `--velopack-uninstall`) to run background file tasks without starting the PySide GUI.

### Application Orchestrator (`src/app_core.py`)
- **`AppCore` Class** (`QMainWindow`): Primary application controller managing main UI state, docking layouts, local IPC server, system tray icon, file watching, and standalone editor instances.
  - `__init__(app, args)`: Applies global dark QSS stylesheet, starts local IPC server socket (`QLocalServer`), sets up tray menu, and restores window settings.
  - `init_ui()`: Instantiates `UiMain` to set up main tabs, toolbars, status bar, and dockable windows.
  - `handle_ipc_message(message)`: Process incoming single-instance commands or external open request payloads.
  - `open_smartprop_editor(path=None)`: Launches or focuses the SmartProp Editor tab/window.
  - `open_soundevent_editor(path=None)`: Launches or focuses the SoundEvent Editor tab/window.
  - `run_map_builder()`: Opens the CS2 Map Builder modal dialog.
  - `run_addon_exporter()`: Launches the Addon Porter export/import dialog.

### Primary Layout Manager (`src/ui_main.py`)
- **`UiMain` Class**: Binds compiled Qt layout (`src/main.ui`) components to `AppCore`.
  - `setupUi(QMainWindow)`: Initializes top-level tab widget, menu bar actions, toolbars, and dock containers.
  - `bind_events()`: Maps menu actions, keyboard shortcuts, and tab events to core controller handlers.

---

## 2. Common Utilities & Data Parsers

### Common Helpers (`src/common.py`)
- **`generate_unique_name(base_name, existing_names, separator="_")` -> `str`**: Generates non-conflicting names by incrementing numeric suffixes (`_01`, `_02`).
- **`app_version`**: Global application version string (e.g., `'5.5.0'`).
- **`JsonToKv3(json_data)` -> `str`**: Serializes Python dictionary/JSON structures into Valve KeyValues3 (KV3) format.
- **`compile(file_path)`**: Calls `resourcecompiler.exe` for CS2 assets (`.vsmart`, `.vsndevts`, `.vmap`).
- **`get_counter_strike_path_from_registry()` / `get_steam_install_path()`**: Locates Steam installation directories and CS2 game paths via Windows Registry.

### KeyValues3 Parser Engine (`keyvalues3/`)
- Native Python KV3 encoder/decoder handling text representation, type headers (`<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-3596-4313-a41f-70c3226768f9} -->`), and type annotations.

### SmartProp Data Layer (`src/smartprop/`)
- **`SmartPropElement`**: Base class representing SmartProp hierarchical nodes (models, choices, filters, placement groups).
- **`SmartPropVariable`**: Class modeling configurable SmartProp parameters (Boolean, Int, Float, String, Vector3, Color, Material).
- **`SmartPropParser`**: Serializes and deserializes `.vsmart` files to/from python objects with KV3 structure preservation.

---

## 3. Editor Subsystems (`src/editors/`)

### SmartProp Editor (`src/editors/smartprop_editor/`)
- **`SmartPropEditorMainWindow`** (`QMainWindow`): Visual editor for Valve `.vsmart` files.
  - `load_file(path)`: Imports `.vsmart` KV3 structure into the element tree.
  - `save_file(path=None)`: Writes current node hierarchy back to KV3 format.
  - `add_element(element_type)` / `remove_element(node)`: Mutates element tree.
  - `update_preview()`: Updates preview data for 3D viewports and external tools.
- **Modules**: `element_tree.py` (hierarchical node view), `property_editor.py` (attribute inspection), `variable_manager.py` (variables table).

### SoundEvent Editor (`src/editors/soundevent_editor/`)
- **`SoundEventEditorMainWindow`** (`QMainWindow`): Graphical editor for `soundevents_addon.vsndevts`.
  - `load_soundevents(path)`: Imports sound event definitions.
  - `add_soundevent(name)` / `duplicate_soundevent(name)`: Creates/duplicates sound entries.
  - `play_sound(vsnd_path)`: Audio playback preview.
  - `export_kv3()`: Formats and exports sound event KV3 files.

### Additional Editors
- **AssetGroup Maker (`src/editors/assetgroup_maker/`)**: `BatchCreatorMainWindow` for grouping and processing game assets.
- **Hotkey Editor (`src/editors/hotkey_editor/`)**: `HotkeyEditorMainWindow` for managing application shortcuts.
- **Loading Screen Editor (`src/editors/loading_editor/`)**: `Loading_editorMainWindow` for CS2 map loading screen metadata.

---

## 4. UI Widgets & Styling System (`src/widgets/` & `src/styles/`)

### Global QSS Stylesheet (`src/styles/qt_global_stylesheet.py`)
- **`QT_Stylesheet_global`**: Primary Qt QSS stylesheet string defining dark palette (`#151515`, `#1C1C1C`, `#1D1D1F`, `#E3E3E3`, `#363639`, `#414956`).

### Styling Helpers (`src/styles/common.py` & `property_icons.py`)
- Utility functions for tab styling, palette colors, and property type icon generation.

### Reusable Widgets (`src/widgets/`)
- **`CustomTreeWidget` (`src/widgets/tree.py`)**: Enhanced `QTreeWidget` with drag-and-drop support, inline editing, and custom signals.
- **`ConsoleWidget` (`src/widgets/console.py`)**: Embedded logger and output viewer.
- **`Property Inspectors` (`src/widgets/property/`)**: Specialized property inputs for Vector3, Color, Resource picker, and Enums.

---

## 5. System Interop & Build Pipeline

### .NET / C# Interop (`src/dotnet.py`)
- **`check_dotnet_runtime()` -> `bool`**: Checks for required .NET runtimes.
- **`DotNetManager`**: Interop wrapper utilizing `pythonnet` to invoke C# DLL binaries in `src/external/`.

### Auto-Updater (`src/updater/`)
- **`check_updates()`**: Asynchronous update checker using Velopack package releases.

### Git Sync & VMAP Merge (`src/git_sync/` & `src/gitvmapmerge.py`)
- **`GitController`**: Manages repository sync buttons, commits, and branch operations inside the UI.
- **`gitvmapmerge.py`**: Custom git merge driver for Valve `.vmap` binary and text files.

### Build Engine (`makefile.py`)
- **`makefile.py`**: Build automation script.
  - Commands: `--build-all`, `--dev`, `--stable`.
