
<p align="center">
    <a href="https://github.com/dertwist/Hammer5Tools">
        <img alt="header" src="readme/header_0.png" width="512">
    </a>
</p>

<p align="center">
    <a href="https://github.com/dertwist/Hammer5Tools/releases/latest">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/download.svg" height="45" alt="Download">
    </a>
    <a href="https://discord.gg/5yzvEQnazG">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/discord.svg" height="45" alt="Discord">
    </a>
    <a href="https://twist-1.gitbook.io/hammer5tools">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/docs.svg" height="45" alt="Docs">
    </a>
</p>

# Essential Tools for Counter-Strike 2 Mapping

| ![image](https://i.imgur.com/7znAlv4.jpeg) Loading Editor | ![image](https://i.imgur.com/HMmbQgR.png) SoundEvent Editor | ![image](https://i.imgur.com/kFjGhI7.png) SmartProp Editor |
| --------------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------- |
| ![image](https://i.imgur.com/D9v7e6w.png) Hotkey Editor   | ![image](https://i.imgur.com/cRFsq49.png) AssetGroup Maker  |

### Tools Overview

|       Tool       | Description                                                               |
|:----------------:| :------------------------------------------------------------------------ |
|  Loading Editor  | Add images, descriptions, and icons to loading screens.                   |
|SoundEvent Editor | Edit in-game sounds easily.                                               |
|  Hotkey Editor   | Customize, edit, and manage new keyboard shortcuts.                       |
| AssetGroup Maker | Edit multiple files at once, ideal for large modular sets.                |
| SmartProp Editor | Simplifies creating smart props.      


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
- **Installer:**

  To create the installer, you need to install [Inno Setup](https://jrsoftware.org/isinfo.php). Do not change the default installation path.
