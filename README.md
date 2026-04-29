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

# Level Up Your Mapping Workflow

Welcome to **Hammer 5 Tools**. This toolkit is designed to bridge the gaps and streamline the level design workflow in Counter-Strike 2.

Whether it's managing sound events, working with Smart Props, or compiling projects, the toolkit provides the necessary solutions.

[**Check out Website**](https://hammer5tools.github.io/)

<p align="center">
  <video src="https://hammer5tools.github.io/videos/hero.mp4" controls="controls" width="100%" muted="true" loop="true" autoplay="true"></video>
</p>

## What's Inside?

### SmartProp Editor
Editing `.vsmart` files manually is no longer necessary. The editor provides a visual way to manage position, rotation, and scaling in real-time. It is fully compatible with Valve's formats and includes presets to help build complex scenes efficiently.

![SmartProp Editor](https://hammer5tools.github.io/static/smartprop_editor.png)

### SoundEvent Editor
Managing sounds is simplified. Explore, preview, and configure `.vsnd` files directly. The tool modifies the `soundevents_addon.vsndevts` file safely, allowing focus on the atmosphere rather than the syntax.

![SoundEvent Editor](https://hammer5tools.github.io/static/soundevent_editor.png)

### Map Builder
A streamlined interface for the compilation process. Whether it's a quick preview or a final bake with high-quality lighting, you can monitor your system's performance (CPU/RAM/GPU) in real-time while it works.

![Map Builder](https://hammer5tools.github.io/static/map_builder.png)

### Cleanup Tool
Is your addon folder getting messy? This tool scans your `.vmap` and sweeps away unused assets, keeping your project lean and professional.

![Cleanup Tool](https://hammer5tools.github.io/static/cleanup_tool.png)

### Addon Porter (Export/Import)
Easily package your addon for release or collaboration. Filter out junk files, include compiled maps, and share your work with a single click.

![Export / Import Addon](https://hammer5tools.github.io/static/export_import_addon.png)

---

# For Developers

Want to contribute or build your own version? Here's the lowdown on the project structure.

### Project Architecture
The app is modular. Each editor lives in its own folder under `src/` and can run standalone if you point it to the right paths. `src/main.py` is the entry point that brings everything together.

*   `src/`: The heart of the app.
*   `src/forms/`: Minor dialogs and UI helpers.
*   `src/external/`: External libraries and .NET resources.
*   `src/common/`: Shared logic and utility functions.

### Getting Started
1.  **Environment**: Requires Python 3.11+. Install dependencies via `pip install -r requirements.txt`.
2.  **Running**: Launch `src/main.py`. Ensure your working directory is set to the project root.
3.  **Building**: A custom `makefile.py` handles the build process:
    ```powershell
    # Build a stable release
    python makefile.py --build-all --stable
    
    # Build a development version
    python makefile.py --build-all --dev
    ```

### Distribution & Updates
The project utilizes **Velopack** for delta-based updates. The GitHub Actions pipeline handles packaging automatically whenever a new tag (e.g., `v5.0.0`) is pushed to the repository.

---

## Join the Community
Have questions? Found a bug? Or just want to show off what you've built? Join the **[Discord Server](https://discord.com/invite/DvCXEyhssd)**. A community of mappers and developers is available to help out.

---
*Created by [Twist](https://github.com/dertwist) and the community.*
