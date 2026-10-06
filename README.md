# Hammer 5 Tools

The managed Avalonia application is `GUI`. Build with `dotnet build Hammer5Tools.slnx -c Release` and run with `dotnet run --project GUI`.

Published Windows application content has this layout:

```text
Hammer5Tools.exe
SoundEventEditor.exe
MapBuilder.exe
SmartPropEditor.exe
WorkshopManager.exe
bin/
presets/
  addons/
  soundeventeditor/
  smartpropeditor/
```

The executable aliases are small .NET hosts loading the same `bin/Hammer5Tools.dll`; local publication uses hard links where supported, while ZIPs contain equivalent host files. The executable name selects the editor, and explicit `--tool` arguments override it. All launches share the existing single-instance process. DLLs, the .NET runtime and `CreateToolShortcuts.ps1` live in `bin`. Bundled presets are immutable application content replaced by updates, separate from user presets. Velopack adds its required updater files outside `current`; this layout is the application payload inside `current`, or the root of the plain Publish ZIP.

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

`-Wizard` requires Inno Setup 6 (or `-InnoCompiler <path to ISCC.exe>`). It produces `Hammer5Tools-Wizard.exe`, offering installed/portable mode and destination selection. Velopack owns installed-mode uninstallation; the wrapper registers no second uninstaller. Portable mode extracts the generated portable payload. Shortcut/extension selection, legacy profile import and portable profile storage remain separate application work; settings currently stay in AppData even in portable mode. Use the published `CreateToolShortcuts.ps1` for editor shortcuts.

GitHub Actions runs Check on pushes and pull requests. **Run workflow** offers the same tasks, version/channel inputs and optional wizard compilation, with artifact upload for Publish/Package/All. All runs every selected check before reporting failures and only packages if validation passes. Reuse your local incremental builds with Check/Build instead of waiting for cloud runners.

SmartProp is integrated into the main application. Workshop Manager runs in its own window in the same process. Application commands use the menu bar; the menu beside the addon selector contains addon lifecycle and folder actions. The old standalone SmartProp preview was removed; its regression host lives in `Tests/Hammer5Tools.SmartProp.Tests`.

SoundEvent Editor, Map Builder, SmartProp Editor and Workshop Manager can also open independently from the same installation:

```powershell
Hammer5Tools.exe --tool soundevents
Hammer5Tools.exe --tool mapbuilder
Hammer5Tools.exe --tool smartprops
Hammer5Tools.exe --tool workshop
```

For source builds, use `dotnet run --project GUI -- --tool soundevents` (or another tool name). Without `--tool`, the full toolkit opens. Launches reuse the running process and activate an existing tool window when possible. Closing a standalone tool leaves other windows open; the process exits when its last window closes. SoundEvent and Map Builder windows include addon selection and Settings, with unsaved-document confirmation before changing addons or installations.

Published Windows builds include `bin/CreateToolShortcuts.ps1`. Run `pwsh -File .\bin\CreateToolShortcuts.ps1` from the application payload folder to add optional Start-menu shortcuts. Editor shortcuts target the corresponding thin launcher and use its embedded icon; all launchers load the same DLLs. The icon files are also shipped in `icons/` and copied into normal build outputs. Standalone SoundEvent, SmartProp and Map Builder windows have their own menu bars and do not follow the shell's selected addon. SoundEvent and SmartProp can open arbitrary source files; Map Builder derives the compiler addon from each selected VMAP under the configured CS2 installation. In the shell these editors share its dynamic menus, and addon changes preserve their tabs and unsaved edits. Use `-Destination <folder>` to place shortcuts elsewhere.

Create addon offers the bundled presets, previews their saved map thumbnails and renames `xxx_mapname_xxx` filenames to the new addon name. User presets under `~/Presets/Addons` take precedence over bundled presets. Empty addons are also supported; existing addons are never overwritten.

Export addon offers content-folder and compiled-resource filters, version-control and extension exclusions, individual file selection, compression choices and cancellable progress. Exports retain the content/game ZIP layout used by legacy imports and replace the destination only after completion.

Settings includes the legacy launch switches, addon-map opening, custom arguments and a command preview. `addon_name` tokens resolve to the selected addon. NCM launches use `-nocustomermachine` and create missing internal tool configuration files without replacing existing configuration. Legacy INI launch commands migrate into the switches and custom arguments.

Fresh launch settings use the legacy defaults: open the addon map in Hammer with Workshop Tools, Steam, retail and GPU ray tracing enabled, plus `+install_dlc_workshoptools_cvar 1 +sv_steamauth_enforce 0`. Insecure mode uses the working `-insecure` flag. Saved launch choices are preserved; NCM remains optional.

The previous Python/PySide6 application, its tests and bridge are preserved under `legacy/Hammer5ToolsGUI`. Run legacy scripts from `legacy/` (for example, `python Hammer5ToolsGUI/gui/main.py`). The native Core remains under `Core/NativeAot`.

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

*   `GUI/`: Avalonia application, editors, presentation and application lifecycle.
*   `CLI/`: Command-line presentation and headless operations.
*   `Core/`: Shared documents, domain logic and services; filesystem/process integrations live in `IO/`.
*   `Core/CS2WorkshopManager/` and `Core/Steamworks/`: Separate pinned Workshop library projects.
*   `GUI/CS2WorkshopManager/`: Workshop UI hosted in-process by the main application.
*   `Misc/CS2WorkshopManager/`: Upstream build settings, provenance and licenses.
*   `Presets/`: Shipped addon presets under `Addons/`, editor presets and hotkey assets.
*   `Tests/`: Managed Core, integration, App, SmartProp and NativeAOT regression tests.
*   `legacy/Hammer5ToolsGUI/`: Archived PySide6 application, editors, widgets, styles, and resources.
*   `Core/NativeAot/`: Native exports and domain code for Python and Houdini, built as one native DLL. Shared SmartProp/resource sources live directly in `Core/Format/`, `Core/IO/` and the root Core API files and are compiled by both projects.
*   `legacy/Hammer5ToolsGUI/gui/forms/`: Minor dialogs and UI helpers.
*   `Misc/Source2Viewer/`: SmartProp evaluator provenance and upstream license. External libraries are restored through NuGet; CUE4Parse uses its pinned patched source checkout.
*   `legacy/Hammer5ToolsGUI/gui/common.py`: Shared logic and utility functions.

The optional NativeAOT solution is `Core/NativeAot/Hammer5Tools.NativeAot.slnx`.
Its regression projects are `Tests/Hammer5Tools.NativeAot.Tests/Hammer5Tools.Core.Tests.csproj`
(TUnit) and `Tests/SourcePorter.Core.Tests/SourcePorter.Core.Tests.csproj` (xUnit).
Native builds require the pinned, patched CUE4Parse dependency configured in
`.github/actions/setup-project/action.yml`; pass its checkout with
`-p:CUE4ParsePath=<checkout>` or set `CUE4ParsePathEnv`. The main managed build
continues to use `Hammer5Tools.slnx`.

After building the NativeAOT solution, run its TUnit suite with
`dotnet run --project Tests/Hammer5Tools.NativeAot.Tests -c Release --no-build`.
The legacy xUnit suite uses
`dotnet vstest Tests/SourcePorter.Core.Tests/bin/Release/SourcePorter.Core.Tests.dll`,
because the repository's `dotnet test` runner is Microsoft.Testing.Platform.
Native DLL filenames and exports are unchanged. External consumers can point
`H5T_SMARTPROP_NATIVE` at a published DLL; Source2Houdini's installer also accepts
`--core-library <published-dll>` when its default still points at the old layout.

### Getting Started
1.  **Environment**: Requires Python 3.11+. Install dependencies via `pip install -r requirements.txt`.
2.  **Running**: Launch `legacy/Hammer5ToolsGUI/gui/main.py`. Ensure your working directory is set to `legacy/`.
3.  **Building the managed application**: Use the shared PowerShell workflow:
    ```powershell
    ./build.ps1 -Task All
    ```

### Distribution & Updates
The managed application bootstraps **Velopack** before normal startup. Use **Help > Check for updates** in the toolkit or standalone editors to check, download and install updates. Installation confirms unsaved documents before restarting. Missing CS2 does not prevent startup. Recoverable startup failures automatically open an independent recovery/update window on normal launch, without a special command. Failed application UI resources fall back to basic controls so updates remain accessible. If the executable, managed runtime or Avalonia framework cannot load, download a fresh installer from [GitHub Releases](https://github.com/dertwist/Hammer5Tools/releases).

`build.ps1` and the manually dispatched GitHub Actions workflow produce installer/portable/update artifacts. Publish the generated `releases.stable.json` or `releases.dev.json` and matching `.nupkg` files as GitHub Release assets in this repository for in-app updates to work. The `dev` channel includes prereleases; `stable` uses published stable releases. CI artifact uploads alone do not publish an update feed. Plain development/Publish builds provide a link to download an installer instead of installing updates in place. The separate package ID `Hammer5Tools.Managed` avoids replacing legacy installs before migration parity is verified. Tags do not currently trigger releases.

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
