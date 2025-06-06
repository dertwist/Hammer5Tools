
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


# Dev
---

### 1.2 Installation

1. **Clone the Repository:**
    ```shell
    git clone https://github.com/dertwist/Hammer5Tools.git
    cd Hammer5Tools
    ```

2. **(Optional) Create a Virtual Environment:**
    ```shell
    python -m venv venv
    source ./venv/Scripts/activate
    ```
    Using a virtual environment is recommended.

3. **Install Dependencies:**
    ```shell
    pip install -r requirements.txt
    ```

---

## 2. Project Structure

- `common/`: Shared helpers and logic.
- `main.py`: General code.
- `dotnet/`: .NET libraries (in `src/external`).

---

## 3. Build Configuration

- **Development Mode:**  
  Run with debug tools:
  ```shell
  python src/script.py --dev
  ```
- **Build Archive:**  
  Create a distributable package:
  ```shell
  python dev/build.py --build-all --archive
  ```

---

## 4. Creating an Installer

Use [InstallForge](https://installforge.net/) with the `hammer5tools_setup.ifp` config file.
