from pathlib import Path
from typing import List, Optional
import logging
import os
import re

log = logging.getLogger(__name__)

try:
    import winreg
except ImportError:
    winreg = None


def is_valid_cs2_path(path: Optional[str]) -> bool:
    """Verifies that the directory is a valid Counter-Strike 2 installation root."""
    if not path:
        return False
    p = Path(path)
    if not p.is_dir():
        return False
    return (p / "game" / "bin" / "win64" / "cs2.exe").is_file() or (p / "game" / "csgo" / "gameinfo.gi").is_file()


def get_steam_install_path() -> Optional[str]:
    """
    Retrieve the Steam installation path from the Windows Registry or standard paths.
    """
    candidates = []

    if winreg is not None:
        # Check HKCU first (Steam writes this for current user)
        for key_path in (r"Software\Valve\Steam", r"Software\Valve\Steam\ActiveProcess"):
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    for val_name in ("SteamPath", "InstallPath"):
                        try:
                            val, _ = winreg.QueryValueEx(key, val_name)
                            if val:
                                candidates.append(str(val))
                        except OSError:
                            pass
                    try:
                        val, _ = winreg.QueryValueEx(key, "SteamExe")
                        if val:
                            candidates.append(os.path.dirname(str(val)))
                    except OSError:
                        pass
            except OSError:
                pass

        # Check HKLM 64-bit and 32-bit keys
        for subkey in (
            r"SOFTWARE\WOW6432Node\Valve\Steam",
            r"SOFTWARE\Valve\Steam",
        ):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as key:
                    val, _ = winreg.QueryValueEx(key, "InstallPath")
                    if val:
                        candidates.append(str(val))
            except OSError:
                pass

    # Common fallback locations
    for env_var in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"):
        base = os.environ.get(env_var)
        if base:
            candidates.append(os.path.join(base, "Steam"))
    candidates.append(r"C:\Program Files (x86)\Steam")
    candidates.append(r"C:\Program Files\Steam")

    for candidate in candidates:
        if candidate:
            normalized = os.path.normpath(str(candidate).replace("/", "\\").strip())
            if os.path.isdir(normalized):
                return normalized

    return None


def get_steam_library_folders(steam_path: Optional[str]) -> List[str]:
    """
    Retrieve all Steam library folders from the libraryfolders.vdf file,
    prioritizing folders known to contain Counter-Strike 2 (app 730).
    """
    if not steam_path:
        return []

    owns_cs2 = []
    others = []
    found_paths = set()

    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.isfile(vdf_path):
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Modern Steam libraryfolders.vdf: "0" { "path" "..." "apps" { "730" "..." } }
            blocks = re.findall(r'"\d+"\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', content)
            for block in blocks:
                path_m = re.search(r'"path"\s+"([^"]+)"', block)
                if path_m:
                    raw_path = path_m.group(1).replace("\\\\", "\\").replace("/", "\\").strip()
                    norm_path = os.path.normpath(raw_path)
                    has_730 = bool(re.search(r'"730"\s+"', block))
                    found_paths.add(norm_path.lower())
                    if has_730:
                        owns_cs2.append(norm_path)
                    else:
                        others.append(norm_path)

            # Fallback regex matching all path entries (or legacy format: "1" "D:\\SteamLibrary")
            all_path_matches = re.findall(r'"path"\s+"([^"]+)"', content)
            all_path_matches.extend(re.findall(r'"\d+"\s+"([^"]+)"', content))
            for raw_match in all_path_matches:
                norm_match = os.path.normpath(raw_match.replace("\\\\", "\\").replace("/", "\\").strip())
                if norm_match.lower() not in found_paths and os.path.isdir(norm_match):
                    found_paths.add(norm_match.lower())
                    others.append(norm_match)
        except Exception as e:
            log.error(f"Error reading libraryfolders.vdf: {e}")

    # Ensure steam_path itself is included
    norm_steam = os.path.normpath(steam_path)
    all_candidates = owns_cs2 + others
    if norm_steam.lower() not in [c.lower() for c in all_candidates]:
        all_candidates.append(norm_steam)

    # Re-order and deduplicate: prioritize folders that contain appmanifest_730.acf or were marked owns_cs2
    priority = []
    remaining = []
    seen = set()

    for folder in all_candidates:
        folder_clean = os.path.normpath(folder)
        folder_key = folder_clean.lower()
        if folder_key in seen:
            continue
        seen.add(folder_key)

        if not os.path.isdir(folder_clean):
            continue

        manifest_path = os.path.join(folder_clean, "steamapps", "appmanifest_730.acf")
        if os.path.isfile(manifest_path) or folder_clean in owns_cs2:
            priority.append(folder_clean)
        else:
            remaining.append(folder_clean)

    return priority + remaining


def find_counter_strike_path(library_folders: List[str]) -> Optional[str]:
    """
    Look for the Counter-Strike installation directory within the given library folders.
    Verifies that the target directory contains a valid CS2 installation (cs2.exe or gameinfo.gi),
    preventing empty or stale directories from blocking valid installations in other libraries.
    """
    if not library_folders:
        return None

    # Pass 1: find a verified valid CS2 install in any of the library folders
    for folder in library_folders:
        # Check appmanifest_730.acf for custom or exact installdir
        manifest_path = os.path.join(folder, "steamapps", "appmanifest_730.acf")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8", errors="ignore") as f:
                    manifest_content = f.read()
                m = re.search(r'"installdir"\s+"([^"]+)"', manifest_content)
                if m:
                    cs_dir = m.group(1).replace("\\\\", "\\").strip()
                    candidate = os.path.join(folder, "steamapps", "common", cs_dir)
                    if is_valid_cs2_path(candidate):
                        return os.path.normpath(candidate)
            except Exception as e:
                log.debug(f"Error reading appmanifest_730.acf in {folder}: {e}")

        # Standard installation folder name
        candidate = os.path.join(folder, "steamapps", "common", "Counter-Strike Global Offensive")
        if is_valid_cs2_path(candidate):
            return os.path.normpath(candidate)

    # Pass 2: fallback if no folder passed is_valid_cs2_path, check if standard folder exists on disk
    for folder in library_folders:
        candidate = os.path.join(folder, "steamapps", "common", "Counter-Strike Global Offensive")
        if os.path.isdir(candidate):
            return os.path.normpath(candidate)

    return None


def get_counter_strike_path_from_registry() -> Optional[str]:
    """
    Main function to get the Counter-Strike installation path.
    """
    # 1. Direct registry check for Steam App 730 InstallLocation
    if winreg is not None:
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 730",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 730",
            ):
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        install_loc, _ = winreg.QueryValueEx(key, "InstallLocation")
                        if install_loc and is_valid_cs2_path(str(install_loc)):
                            return os.path.normpath(str(install_loc))
                except OSError:
                    pass

    # 2. Enumerate Steam library folders
    steam_path = get_steam_install_path()
    if not steam_path:
        return None

    library_folders = get_steam_library_folders(steam_path)
    csgo_path = find_counter_strike_path(library_folders)
    return csgo_path
