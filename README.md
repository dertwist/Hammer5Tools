
<p align="center">
    <a href="https://github.com/dertwist/Hammer5Tools">
        <img alt="header" src="readme/header_0.png" width="512">
    </a>
</p>


<p align="center">
    <a href="https://github.com/dertwist/Hammer5Tools/releases/latest">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/download.svg" height="45" alt="Download">
    </a>
    <a href="https://discord.gg/JzcHMFbCEC">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/discord.svg" height="45" alt="Discord">
    </a>
    <a href="https://twist-1.gitbook.io/hammer5tools">
        <img src="https://gist.githubusercontent.com/cxmeel/0dbc95191f239b631c3874f4ccf114e2/raw/docs.svg" height="45" alt="Docs">
    </a>
</p>



# Essential Tools for Counter-Strike 2 Mapping:

| ![image](https://i.imgur.com/7znAlv4.jpeg) Loading Editor | ![image](https://i.imgur.com/HMmbQgR.png) SoundEvent Editor | ![image](https://i.imgur.com/kFjGhI7.png)  SmartProp Editor |
| ----------- | ----------- | ----------- |
| ![image](https://i.imgur.com/D9v7e6w.png) Hotkey Editor | ![image](https://i.imgur.com/cRFsq49.png) AssetGroup Maker |

### Tools Overview:

|        Tool       | Description                                                  |
|:-----------------:|:-------------------------------------------------------------|
| Loading Editor    | Add images, descriptions, and icons to loading screens.      |
| SoundEvent Editor | Edit in-game sounds easily.                                  |
| Hotkey Editor     | Customize and add new keyboard shortcuts.                    |
| AssetGroup Maker      | Edit multiple files at once. Perfect for large modular sets. |
| SmartProp Editor  | Simplifies smartprops creation.                              |






#  Developer Documentation  
For those who want to contribute to the project or build their own tools on top of this project.

## Setup  

### Prerequisites  
- Python with PySide6 for the GUI framework  
- IDE with Python support (PyCharm recommended)  
- All requirements in the **requirements.txt** file

### Project Structure  
Hammer5Tools/  
├── src/  
│ ├── about/ # About dialog and documentation  
│ ├── common/ # Shared utilities and constants  
│ ├── main.py # Application entry point  
│ └── updater.py # Auto-update functionality  
├── dev/  
│ └── build.py # Build configuration  
└── .run/ # Run configurations (PyCharm)


### Build Configuration  
The project uses custom run configurations for different development scenarios:  

1. **Development Mode:**  
   Gives access to button show debug info. The option prints additional information to the console, for example, dictionary properties values.  
   ```python src/main.py --dev  ```    
  
2. Build Process:  
```python dev/build.py --build-all --archive ```

## Creating Installer

For the installer program, I used [InstallForge](https://installforge.net/)  
The configuration file is `hammer5tools_setup.ifp`

## Code Structure

Each tool has its own module and adds to the `main.py` file. Most of the tools are related to the current addon, so they are removed and added again after changing the addon.

### Tool Modules

1.  **Loading Editor**  
    Handles loading screen customization
    
    -   **Screenshots applying:** Moves all images from the `screenshots` folder in the game to the content and creates `.vtex` files for each screenshot. Then compiles all.
    -   **Icon apply:** Copies and renames the `.svg` file from the window to the `csgo_content`.
    -   **Apply description:** Adds a `.txt` file near the `.vmap` file of the selected addon (e.g., for the current addon `de_dust2`, the program will create `de_dust2.txt` with the path `maps/de_dust2.vmap` in the game).
    -   All these operations use the current addon name for creation files and their names.
2.  **SoundEvent Editor**  
    Loads the `soundevents_addon.vsndevts` and edits that file.  
    The structure of this editor is:
    
    -   Main window
    -   Explorer
    -   Soundevents (tree elements list, list of all elements in the `soundevents_addon.vsndevts`)
    -   Property editor window
3.  **Hotkey Editor**  
    The editor for hotkey configurations.
    
4.  **AssetGroup Maker**  
    Batch processing for asset files.
    
5.  **SmartProp Editor**  
    Smartprop creation.