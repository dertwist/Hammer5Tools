## General

The program architecture has been changed. All C# files were moved to a separate Core and the PythonNet bridge was replaced with AOT-compatible libraries.
As a benefit, the application runs much faster in heavy scenarios such as Unreal Porter and VMAP reading. The application also no longer needs the .NET runtime to run, so the setup file is now smaller.
A lot of dead code was removed and crash handling was improved. All these changes provide a stronger foundation for future tools.
At the same time, the styling architecture was changed to more modular qss, which now allows making color themes.

* Added an option to open the console window from Settings.
* Added Light, System, and Vintage Steam themes.

## NavMesh Radar

* Generate radars from navmeshes.

<img width="1562" height="486" alt="NavMesh Radar preview" src="https://github.com/user-attachments/assets/260791c3-6943-4395-934e-c7f4afaac959" />

## Sound Event Editor

* Added curve handles.
* Added property grouping.
* Moved Play and Stop controls to the viewport window.
* Added tooltips for properties from Source 2 schemas.
* Improved loading speed and Undo/Redo action speed.

## Git Sync

* Added a feature to set up a Git repository.
* Added a change list dialog before synchronization.
* Improved the UI for resolving conflicts.
* Improved synchronization safety to preserve local changes.

## SmartProp Editor

* Added preview support for `LinearScale()`.
* Split long fields in the Property Editor into multiple lines to improve readability.
* Changed the copy and paste format for modifiers and selection criteria to KV3.
* Added support for copying and pasting multiple modifiers and selection criteria.

## Model Browser

* Added vtex, vmat, and vsmart thumbnail support.
* Improved loading speed.
