# Hammer 5 Tools

The managed Avalonia application is `src/Hammer5Tools.App`. Build with `dotnet build Hammer5Tools.slnx -c Release` and run with `dotnet run --project src/Hammer5Tools.App`.

Use PowerShell 7 and the .NET 10 SDK to run the same workflow locally as GitHub Actions:

```powershell
./build.ps1                        # Release build, all managed tests, format verification
./build.ps1 -Task Build            # Incremental Release build only
./build.ps1 -Task All              # Checks, then Velopack installer, portable ZIP and update feed
./build.ps1 -Task Publish          # Build and ZIP without tests or format verification
./build.ps1 -Task Package -Version 7.0.0-dev.1 # Package without validation (local smoke builds)
./build.ps1 -Task Package -Version 7.0.0-dev.1 -Wizard # Also compile the custom installation wizard
./build.ps1 -Task Check -Gpu -GameAssets # Also test native GPU rendering and installed CS2 assets
./build.ps1 -Task All -DryRun       # Show commands without building or changing files
```

The checks run the Core, integration and App TUnit suites, plus the SmartProp headless regression host. GPU checks open native test windows and require a desktop, graphics drivers and CS2; they are opt-in and are not run on GitHub-hosted CI. The archived Python and NativeAOT suites are separate from this managed workflow.

Published files use a fresh directory under `.build/publish/` on each run to avoid stale files. Publish creates `.build/Hammer5Tools-win-x64.zip`. Package/All create a Velopack Setup.exe, Portable.zip, full update package and release index under `.build/releases/<channel>/<version>/<build-id>/`. Fresh output directories let you rebuild the same version without mixing artifacts from earlier builds. Defaults are version `7.0.0` and channel `dev`; use `-Version` and `-Channel stable` explicitly for releases. The NuGet package and repository-local `vpk` tool are pinned to the same version. Packages are unsigned local test artifacts; the script does not upload releases or install the application.

`-Wizard` requires Inno Setup 6 (or `-InnoCompiler <path to ISCC.exe>`). It produces `Hammer5Tools-Wizard.exe`, offering installed/portable mode and destination selection. Velopack owns installed-mode uninstallation; the wrapper registers no second uninstaller. Portable mode extracts the generated portable payload. Shortcut/extension selection, legacy profile import, portable profile storage and the app's update-check/download UI remain separate application work; settings currently stay in AppData even in portable mode. Use the published `CreateToolShortcuts.ps1` for editor shortcuts.

GitHub Actions runs Check on pushes and pull requests. **Run workflow** offers the same tasks, version/channel inputs and optional wizard compilation, with artifact upload for Publish/Package/All. All runs every selected check before reporting failures and only packages if validation passes. Reuse your local incremental builds with Check/Build instead of waiting for cloud runners.

SmartProp is integrated into the main application. Workshop Manager runs in its own window in the same process. Application commands use the menu bar; the menu beside the addon selector contains addon lifecycle and folder actions. The old standalone SmartProp preview was removed; its regression host lives in `tests/Hammer5Tools.SmartProp.Tests`.

SoundEvent Editor, Map Builder and Workshop Manager can also open independently from the same installation:

```powershell
Hammer5Tools.App.exe --tool soundevents
Hammer5Tools.App.exe --tool mapbuilder
Hammer5Tools.App.exe --tool workshop
```

For source builds, use `dotnet run --project src/Hammer5Tools.App -- --tool soundevents` (or another tool name). Without `--tool`, the full toolkit opens. Launches reuse the running process and activate an existing tool window when possible. Closing a standalone tool leaves other windows open; the process exits when its last window closes. SoundEvent and Map Builder windows include addon selection and Settings, with unsaved-document confirmation before changing addons or installations.

Published Windows builds include `CreateToolShortcuts.ps1`. Run `powershell -File .\CreateToolShortcuts.ps1` from the installation folder to add optional Start-menu shortcuts. All four shortcuts target the same executable and reuse its DLLs; no extra application copies are installed. Use `-Destination <folder>` to place shortcuts elsewhere.

Create addon offers the bundled presets, previews their saved map thumbnails and renames `xxx_mapname_xxx` filenames to the new addon name. User presets under `~/Hammer5Tools/Presets` take precedence over bundled presets. Empty addons are also supported; existing addons are never overwritten.

Export addon offers content-folder and compiled-resource filters, version-control and extension exclusions, individual file selection, compression choices and cancellable progress. Exports retain the content/game ZIP layout used by legacy imports and replace the destination only after completion.

Settings includes the legacy launch switches, addon-map opening, custom arguments and a command preview. `addon_name` tokens resolve to the selected addon. NCM launches use `-nocustomermachine` and create missing internal tool configuration files without replacing existing configuration. Legacy INI launch commands migrate into the switches and custom arguments.

Fresh launch settings use the legacy defaults: open the addon map in Hammer with Workshop Tools, Steam, retail and GPU ray tracing enabled, plus `+install_dlc_workshoptools_cvar 1 +sv_steamauth_enforce 0`. Insecure mode uses the working `-insecure` flag. Saved launch choices are preserved; NCM remains optional.

The previous Python/PySide6 application, its tests and bridge are preserved under `legacy/Hammer5ToolsGUI`. Run legacy scripts from `legacy/` (for example, `python Hammer5ToolsGUI/gui/main.py`). The native Core remains under `Hammer5ToolsCore`.

Editing `.vsmart` files manually is no longer necessary. The editor provides a visual way to manage position, rotation, and scaling in real-time. It is fully compatible with Valve's formats and includes presets to help build complex scenes efficiently.

### SoundEvent Editor
Managing sounds is simplified. Explore, preview, and configure `.vsnd` files directly. The tool modifies the `soundevents_addon.vsndevts` file safely, allowing focus on the atmosphere rather than the syntax.

### Map Builder
A streamlined interface for the compilation process. Whether it's a quick preview or a final bake with high-quality lighting, you can monitor your system's performance (CPU/RAM/GPU) in real-time while it works.

### Cleanup Tool
Is your addon folder getting messy? This tool scans your `.vmap` and sweeps away unused assets, keeping your project lean and professional.

---
<details>
<summary>For Developers</summary>

Want to contribute or build your own version? Here's the lowdown on the project structure.

### Project Architecture
The managed GUI and CLI reference one shared Core library. The C# application starts directly and owns single-instance startup and update checks; the C++ launcher has been removed.

*   `src/Hammer5Tools.App/`: Avalonia application, editors, presentation and application lifecycle.
*   `src/Hammer5Tools.Cli/`: Command-line presentation and headless operations.
*   `src/Hammer5Tools.Core/`: Shared documents, domain logic and services; filesystem/process integrations live in `IO/`.
*   `third_party/CS2WorkshopManager/`: Pinned upstream library and GUI; Core uses the library and App hosts the GUI in-process.
*   `tests/`: Managed Core, integration, App and SmartProp regression tests.
*   `legacy/Hammer5ToolsGUI/`: Archived PySide6 application, editors, widgets, styles, and resources.
*   `Hammer5ToolsCore/`: one C# project, one NativeAOT native DLL — Source 2 parsing, porting, and Unreal bridge logic.
*   `legacy/Hammer5ToolsGUI/gui/forms/`: Minor dialogs and UI helpers.
*   `Hammer5ToolsCore/external/`: External libraries and .NET resources.
*   `legacy/Hammer5ToolsGUI/gui/common.py`: Shared logic and utility functions.

### Getting Started
1.  **Environment**: Requires Python 3.11+. Install dependencies via `pip install -r requirements.txt`.
2.  **Running**: Launch `legacy/Hammer5ToolsGUI/gui/main.py`. Ensure your working directory is set to `legacy/`.
3.  **Building the managed application**: Use the shared PowerShell workflow:
    ```powershell
    ./build.ps1 -Task All
    ```

### Distribution & Updates
The managed application bootstraps **Velopack** before normal startup. `build.ps1` and the manually dispatched GitHub Actions workflow produce installer/portable/update artifacts. The managed update service is still a placeholder; package creation does not implement its update UI or publish a feed. The separate package ID `Hammer5Tools.Managed` avoids replacing legacy installs before migration parity is verified. Tags do not currently trigger releases.

### CLI and agent automation

The existing `Hammer5ToolsGUI.exe` also hosts headless CLI and MCP stdio modes.
See [MCP_SETUP.md](MCP_SETUP.md) for source-build commands, agent
configuration, and the currently implemented read-only tools.

</details>

### Third-Party Libraries & Dependencies
Hammer 5 Tools builds upon several open-source libraries, tools, and frameworks:
*   **[PySide6](https://pypi.org/project/PySide6/)**: Official Python bindings for Qt 6, serving as the UI framework for the application.
*   **[PyOpenGL](https://pyopengl.sourceforge.net/) & [PyQtGraph](https://www.pyqtgraph.org/)**: 3D viewport rendering for models and real-time hardware performance telemetry visualization.
*   **[Velopack](https://velopack.io/)**: Installer and dynamic auto-update framework for desktop applications.
*   **[keyvalues3](https://github.com/kristiker/keyvalues3)**: Python library for reading and writing Valve's KeyValues3 (KV3) format.
*   **[SkiaSharp](https://github.com/mono/SkiaSharp)**: Cross-platform 2D graphics API for asset texture rendering and image processing.
*   **[ValveResourceFormat (VRF / Source2Viewer)](https://github.com/ValveResourceFormat/ValveResourceFormat)**: C# library for parsing, decompiling, and inspecting Valve Source 2 resources, VPK archives (`ValvePak`), and KeyValues formats (`ValveKeyValue`).
*   **[CUE4Parse](https://github.com/FabianFG/CUE4Parse)**: C# parser library for Unreal Engine packages.
*   **[Datamodel.NET](https://github.com/ValveResourceFormat/Datamodel.NET)**: C# library for reading and writing Valve DMX (Datamodel) asset files.
---
