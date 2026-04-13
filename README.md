<h1 align="center">
  <img src="https://hammer5tools.github.io/static/logo.png" width="64" valign="middle" alt="Hammer 5 Tools Logo">
  &nbsp;Hammer 5 Tools
</h1>

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

# Essential Tools for Counter-Strike 2 Mapping

A powerful toolkit for Counter-Strike 2 Workshop Tools. Edit sound events, create smart props, build maps, manage keybindings, and customize loading screens.

[**Visit Official Website**](https://hammer5tools.github.io/)

<p align="center">
  <video src="https://hammer5tools.github.io/videos/hero.mp4" controls="controls" width="100%" muted="true" loop="true" autoplay="true"></video>
</p>

## Tools

### SmartProp Editor
Edit .vsmart files using an intuitive interface. The tool supports all essential properties while maintaining compatibility with older formats. Modify properties in real-time to precisely adjust the position, rotation, and scaling of your models. Utilize presets to rapidly construct repetitive elements.

![SmartProp Editor](https://hammer5tools.github.io/static/smartprop_editor.png)

---

### SoundEvent Editor
Manage in-game sounds seamlessly. The editor works directly with Counter-Strike 2 sounds (.vsnd files) and allows you to explore, preview, and configure sound events. Use presets to quickly set up sound events or define your own custom configurations. Edits the `soundevents_addon.vsndevts` file directly.

![SoundEvent Editor](https://hammer5tools.github.io/static/soundevent_editor.png)

---

### Map Builder
Streamline the map compilation process with a dedicated and powerful interface. Access fast, full, or custom compile options such as building geometry, visibility, or baking lighting. Configure settings like lightmap resolution and quality while monitoring CPU, RAM, and GPU usage during the build in real-time.

![Map Builder](https://hammer5tools.github.io/static/map_builder.png)

---

### Cleanup Tool
Effortlessly remove unused and redundant files from your addon's content folder. By scanning your project's .vmap file, the tool identifies and keeps only the actively referenced assets, freeing up valuable storage space and simplifying project management.

![Cleanup Tool](https://hammer5tools.github.io/static/cleanup_tool.png)

---

### Export / Import Addon
Simplify the distribution of your projects by exporting and importing entire addons seamlessly. Filter out unnecessary folders or VCS files, and include compiled maps, materials, or models effortlessly. Ideal for packaging your map for release or collaborating with other developers.

![Export / Import Addon](https://hammer5tools.github.io/static/export_import_addon.png)

---

### AssetGroup Maker
Batch-create assets for Source 2 effortlessly. By utilizing a straightforward configuration file and a folder scan, you can automatically generate files for massive asset sets. This ensures consistency across all your assets and drastically minimizes time spent on manual edits.

![AssetGroup Maker](https://hammer5tools.github.io/static/assetgroup_maker.png)

---

### Hotkey Editor
Configure and manage custom keyboard shortcuts for a wide variety of tasks. Streamline your workflow by keeping essential functions right at your fingertips. Store multiple hotkey presets tailored to different projects and switch between them seamlessly.

![Hotkey Editor](https://hammer5tools.github.io/static/hotkeyeditor.png)

---

### Loading Editor
Customize your map's loading experience by managing screenshots, map icons, and descriptions. Capture high-quality screenshots and history snapshots directly from CS2, process them into multiple resolutions, and configure rich-text descriptions for the community workshop.

![Loading Editor](https://hammer5tools.github.io/static/loading_editor.png)


# Development Guide
---
## 1. Project Structure

The application is organized into modules, with each editor implemented as a separate module. Editors can be run independently if you provide the paths to CS2 and the addon. All editors are integrated through the main application (src/main.py), which manages their settings. If you wish to use an editor separately from the main application, you must create separate settings and handle the CS2 and addon paths manually.

Project folder overview:
- `src/`: Contains the main application code and all editor modules.
    - `forms/`: Minor Qt dialogs, such as About or Launch Options.
    - `external/`: External libraries and resources not related to Python (e.g., .NET libraries).
    - `dotnet/`: .NET handle, functions (located in `src/external`).

Each major feature or editor has its own folder:
- `common/`: Shared helpers and logic used across editors.
- `main.py`: General functions, entry point.
---

## 2. Launch and Build configurations
Run configurations are available for PyCharm and Visual Studio Code.
- **Run:**
  To run the application, you need to run the main.py file in the src folder.
  Do not forget to set the working directory to the `hammer5tools` folder, which is in the same root folder as src.
  Otherwise, just use the ready-made run configurations in your IDE.
- **Build:**
  ```shell
  python makefile.py --build-all --archive
  ```
  The script will generate exe file in the `hammer5tools` folder. After that
  it will create a zip archive of the application in the `dist` folder for distribution.
  The archive used by automic updates and can be used to run the application on other computers without installation.


- **Installer:**

  To create the installer, you need to install [Inno Setup](https://jrsoftware.org/isinfo.php). Do not change the default installation path.
  
