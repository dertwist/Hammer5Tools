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

Welcome to **Hammer 5 Tools**. If you've ever felt that the standard CS2 Workshop Tools are missing a few essential features, you're in the right place. This toolkit is built by a mapper, for mappers, to bridge the gaps and streamline your workflow.

Whether you're wrestling with sound events, trying to make sense of Smart Props, or just want a faster way to compile your project, we've got you covered.

[**Check out the Official Website**](https://hammer5tools.github.io/)

<p align="center">
  <video src="https://hammer5tools.github.io/videos/hero.mp4" controls="controls" width="100%" muted="true" loop="true" autoplay="true"></video>
</p>

## What's Inside?

### SmartProp Editor
Stop editing `.vsmart` files in notepad. Our editor gives you a visual way to manage position, rotation, and scaling in real-time. It's fully compatible with Valve's formats and includes presets to help you build complex scenes in seconds.

![SmartProp Editor](https://hammer5tools.github.io/static/smartprop_editor.png)

### SoundEvent Editor
Managing sounds shouldn't be a chore. Explore, preview, and configure your `.vsnd` files directly. We edit your `soundevents_addon.vsndevts` file safely, so you can focus on the atmosphere, not the syntax.

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
3.  **Building**: We use a custom `makefile.py` to handle the build process:
    ```powershell
    # Build a stable release
    python makefile.py --build-all --stable
    
    # Build a development version
    python makefile.py --build-all --dev
    ```

### Distribution & Updates
We use **Velopack** for delta-based updates. The GitHub Actions pipeline handles packaging automatically whenever a new tag (e.g., `v5.0.0`) is pushed to the repository.

---

## Join the Community
Have questions? Found a bug? Or just want to show off what you've built? Join our **[Discord Server](https://discord.com/invite/DvCXEyhssd)**. We're a friendly group of mappers and developers always looking to help out.

---
*Created with ❤️ by dertwist and the community.*
