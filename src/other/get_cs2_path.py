import winreg, os, re
def get_steam_install_path():
    """
    Retrieve the Steam installation path from the Windows Registry.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
            steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
            return steam_path
    except WindowsError:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam") as key:
                steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
                return steam_path
        except WindowsError as e:
            print(f"Error reading Steam install path: {e}")
            return None


def get_steam_library_folders(steam_path):
    """
    Retrieve all Steam library folders from the libraryfolders.vdf file.
    """
    library_folders = [steam_path]
    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")

    try:
        with open(vdf_path, "r") as f:
            content = f.read()
            matches = re.findall(r'"path"\s+"([^"]+)"', content)
            library_folders.extend(matches)
    except Exception as e:
        print(f"Error reading libraryfolders.vdf: {e}")

    return library_folders


def find_counter_strike_path(library_folders):
    """
    Look for the Counter-Strike installation directory within the given library folders.
    """
    csgo_path_suffix = os.path.join("steamapps", "common", "Counter-Strike Global Offensive")
    for folder in library_folders:
        csgo_path = os.path.join(folder, csgo_path_suffix)
        if os.path.exists(csgo_path):
            return csgo_path
    return None


def get_counter_strike_path_from_registry():
    """
    Main function to get the Counter-Strike installation path.
    """
    steam_path = get_steam_install_path()
    if not steam_path:
        return None

    library_folders = get_steam_library_folders(steam_path)
    csgo_path = find_counter_strike_path(library_folders)
    return csgo_path
