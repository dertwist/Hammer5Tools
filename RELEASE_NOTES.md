# Hammer 5 Tools 6.0.0

This release brings major new tools, faster previews, and a more reliable app experience since 5.8.1.

## General

* **Major Architecture Refactor**: All C# functionality now lives in a separate native Core, replacing the old PythonNet bridge. Heavy tasks such as Unreal Porter and VMAP processing are much faster, and the app no longer requires a separate .NET runtime.
* **Smaller & More Reliable**: The installer is smaller, dead code and unused dependencies have been removed, and startup, logging, and crash reporting are more robust.
* **Themes & UI**: Styling now uses a modular QSS system, enabling improved Light, System, and Vintage Steam themes with more consistent controls and editor layouts.
* **Console**: The built-in console can now be opened from Settings when needed.

These changes provide a cleaner, stronger foundation for future tools.

## NavMesh Radar

* Generate editable radar meshes directly from compiled CS2 navigation data, with cleaner geometry, safer offsets, and automatic prefab detection.

<img width="1562" height="486" alt="NavMesh Radar preview" src="https://github.com/user-attachments/assets/260791c3-6943-4395-934e-c7f4afaac959" />

## Hotkey Editor

* Added presets and keybinding catalogs for every CS2 tool editor, including ModelDoc and the Particle Editor.

## Sound Event Editor

* Added interactive curve anchors and tangent handles.
* Grouped properties into clear categories and added tooltips from Source 2 schemas.
* Moved playback controls into the editor and improved loading and undo/redo performance.

## Git Sync

* Added a guided repository setup and a change-selection dialog before synchronization.
* Improved conflict resolution and synchronization safety to preserve local changes.
* Expanded the default Git LFS rules for common project assets.

## SmartProp Editor

* Added preview support for `LinearScale()`, Fit On Line, material overrides, tint, transparency, and more deformer behavior.
* Improved readability by displaying long property values across multiple lines.
* Switched clipboard data to KV3 and added support for copying and pasting multiple modifiers and selection criteria.
* Improved 3D viewport navigation, material rendering, and gizmo stability.

## Model Browser

* Added thumbnail support for VTEX, VMAT, and VSMART assets.
* Improved loading, caching, and thumbnail generation speed and reliability.
