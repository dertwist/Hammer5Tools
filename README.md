<h1 align="center">
  <img src="https://hammer5tools.github.io/static/logo.png" width="64" valign="middle" alt="Hammer 5 Tools Logo">
  &nbsp;Hammer 5 Tools
</h1>

<p align="center">
    <strong>The ultimate toolkit for Counter-Strike 2 level designers and modders.</strong>
</p>

<p align="center">
    <a href="https://github.com/dertwist/Hammer5Tools/releases/latest">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/download.svg" height="45" alt="Download">
    </a>
    <a href="https://discord.com/invite/DvCXEyhssd">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/discord.svg" height="45" alt="Discord">
    </a>
    <a href="https://hammer5tools.github.io/docs.html">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/docs.svg" height="45" alt="Docs">
    </a>
</p>

---

Welcome to **Hammer 5 Tools**. This toolkit is designed to bridge the gaps and streamline the level design workflow in Counter-Strike 2.

Whether it's managing sound events, working with Smart Props, or compiling projects, the toolkit provides the necessary solutions.

[**Check out Website**](https://hammer5tools.github.io/)

<p align="center">
  <img width="2560" height="1392" alt="image" src="https://github.com/user-attachments/assets/b273ff75-72e9-4569-b659-f2817ef7b401" />
</p>

### SmartProp Editor
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
The app is modular. Each editor lives in its own folder under `Hammer5ToolsGUI/gui/` and can run standalone if you point it to the right paths. `Hammer5ToolsGUI/gui/main.py` is the entry point that brings everything together.

*   `Hammer5ToolsGUI/`: PySide6 application, editors, widgets, styles, and resources.
*   `Hammer5ToolsCore/`: C# domain projects (SourcePorter, UnrealBridge, native core).
*   `Hammer5ToolsLauncher/`: Native startup, IPC, and GUI supervision.
*   `Hammer5ToolsGUI/gui/forms/`: Minor dialogs and UI helpers.
*   `Hammer5ToolsCore/CSharp/external/`: External libraries and .NET resources.
*   `Hammer5ToolsGUI/gui/common.py`: Shared logic and utility functions.

### Getting Started
1.  **Environment**: Requires Python 3.11+. Install dependencies via `pip install -r requirements.txt`.
2.  **Running**: Launch `Hammer5ToolsGUI/gui/main.py`. Ensure your working directory is set to the project root.
3.  **Building**: A custom `makefile.py` handles the build process:
    ```powershell
    # Build a stable release
    python makefile.py --build-all --stable
    
    # Build a development version
    python makefile.py --build-all --dev
    ```

### Distribution & Updates
The project utilizes **Velopack** for delta-based updates. The GitHub Actions pipeline handles packaging automatically whenever a new tag (e.g., `v5.0.0`) is pushed to the repository.

</details>

### Third-Party Libraries & Dependencies
Hammer 5 Tools builds upon several open-source libraries, tools, and frameworks:
*   **[PySide6](https://pypi.org/project/PySide6/)**: Official Python bindings for Qt 6, serving as the UI framework for the application.
*   **[PyOpenGL](https://pyopengl.sourceforge.net/) & [PyQtGraph](https://www.pyqtgraph.org/)**: 3D viewport rendering for models and real-time hardware performance telemetry visualization.
*   **[Velopack](https://velopack.io/)**: Installer and dynamic auto-update framework for desktop applications.
*   **[keyvalues3](https://github.com/kristiker/keyvalues3)**: Python library for reading and writing Valve's KeyValues3 (KV3) format.
*   **[pythonnet](https://pythonnet.github.io/)**: Managed .NET CLR interop for remaining non-SmartProp Core features. SmartProp evaluation and serialization use the bundled NativeAOT C ABI.
*   **[SkiaSharp](https://github.com/mono/SkiaSharp)**: Cross-platform 2D graphics API for asset texture rendering and image processing.
*   **[ValveResourceFormat (VRF / Source2Viewer)](https://github.com/ValveResourceFormat/ValveResourceFormat)**: C# library for parsing, decompiling, and inspecting Valve Source 2 resources, VPK archives (`ValvePak`), and KeyValues formats (`ValveKeyValue`).
*   **[CUE4Parse](https://github.com/FabianFG/CUE4Parse)**: C# parser library for Unreal Engine packages.
*   **[Datamodel.NET](https://github.com/ValveResourceFormat/Datamodel.NET)**: C# library for reading and writing Valve DMX (Datamodel) asset files.
---
