
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


# Developer Documentation

This part provides a complete overview of the Hammer5Tools project, covering its setup and structure.  
Whether you’re building tools on top of this foundation or maintaining the existing code, this guide will help you get started.

---

## 1. Setup

### Prerequisites
- Python 3.10+ (3.12 recommended)  
- PySide6 for the GUI framework  
- All requirements declared in the `requirements.txt` file  
- An IDE with Python support (PyCharm recommended)

### 1.2 Installation Steps

1.  **Clone the Repository:**

    ```shell
    git clone https://github.com/dertwist/Hammer5Tools.git
    ```
    
    ```shell
    cd Hammer5Tools
    ```

2.  **(Optional) Create and Activate a Virtual Environment:**

    ```shell
    python -m venv venv source ./venv/Scripts/activate
    ```

    It is recommended to use a virtual environment to manage project dependencies.

3.  **Install Dependencies:**

    ```shell
    pip install -r requirements.txt
    ```
---

## 2. Project Structure

Hammer5Tools/  
├── src/    
│ ├── common/ # Shared utilities and constants  
│ ├── main.py # Application entry point  
│ └── updater.py # Auto-update functionality  
├── dev/  
│ └── build.py # Build file  
└── .run/ # Run configurations (PyCharm)


- **common/**: Contains helper functions, tools, and shared logic used in multiple parts of the application.  
- **main.py**: Launches the overall UI and integrates the available tool modules.  
- **updater.py**: Handles auto-update features, ensuring the user always has the latest version.

---

## 3. Build Configuration

The project uses a custom build script and supports multiple run modes:

1. **Development Mode**  
   - Adds debugging utilities and detailed console logs.  
   - Launch by running:  
     ```shell
     python src/script.py --dev
     ```
   - Useful for diagnosing problems or stepping through new features.

2. **Build Process**  
   - Creates a distributable archive of the Hammer5Tools suite.  
   - Execute:
     ```shell
     python dev/build.py --build-all --archive
     ```
   - This process compiles relevant data and ensures everything is packaged consistently for distribution.

---

## 4. Creating an Installer

Hammer5Tools uses [InstallForge](https://installforge.net/) for generating installers.  
Refer to the `hammer5tools_setup.ifp` configuration file within the project for settings related to the installer.
