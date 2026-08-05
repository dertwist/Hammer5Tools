"""Locate local Unreal Engine installs without asking the user for a path.

Three sources, cheapest first:
  * the Epic launcher manifest (covers every launcher-installed engine),
  * the registry (source builds register themselves under HKCU Builds),
  * a glob over the default install root (covers a hand-copied engine).

A .uproject names its engine in "EngineAssociation" — a version string like
"5.4" for launcher installs, or a GUID for source builds — so a project can
usually pick its own engine with no user input at all.
"""
import glob
import json
import os
import re

_LAUNCHER_MANIFEST = r"C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat"
_DEFAULT_ROOTS = (r"C:\Program Files\Epic Games", r"D:\Program Files\Epic Games")


class UeInstall:
    """A usable engine install: an identifier plus the folder holding Engine/."""

    def __init__(self, version: str, root: str):
        self.version = version
        self.root = root.replace("\\", "/")

    def __repr__(self):
        return f"UeInstall({self.version!r}, {self.root!r})"

    def __eq__(self, other):
        return isinstance(other, UeInstall) and self.root.lower() == other.root.lower()

    def __hash__(self):
        return hash(self.root.lower())

    @property
    def label(self) -> str:
        return f"Unreal Engine {self.version}  ({self.root})"


def _is_engine_root(path: str) -> bool:
    return bool(path) and os.path.isdir(os.path.join(path, "Engine", "Binaries", "Win64"))


def _from_launcher_manifest():
    try:
        with open(_LAUNCHER_MANIFEST, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return
    for entry in data.get("InstallationList", []):
        root = entry.get("InstallLocation", "")
        if not _is_engine_root(root):
            continue
        # AppName is like "UE_5.4"; AppVersion is a long build string.
        name = entry.get("AppName", "")
        yield UeInstall(name[3:] if name.startswith("UE_") else name or "?", root)


def _from_registry():
    try:
        import winreg
    except ImportError:  # non-Windows
        return
    # Launcher installs land in HKLM; source builds register a GUID in HKCU.
    for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\EpicGames\Unreal Engine"),
                      (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Epic Games\Unreal Engine\Builds")):
        try:
            with winreg.OpenKey(hive, key) as handle:
                if key.endswith("Builds"):
                    for i in range(winreg.QueryInfoKey(handle)[1]):
                        name, value, _ = winreg.EnumValue(handle, i)
                        if _is_engine_root(value):
                            yield UeInstall(name, value)
                    continue
                for i in range(winreg.QueryInfoKey(handle)[0]):
                    version = winreg.EnumKey(handle, i)
                    with winreg.OpenKey(handle, version) as sub:
                        try:
                            root, _ = winreg.QueryValueEx(sub, "InstalledDirectory")
                        except FileNotFoundError:
                            continue
                        if _is_engine_root(root):
                            yield UeInstall(version, root)
        except OSError:
            continue


def _from_default_roots():
    for base in _DEFAULT_ROOTS:
        for path in glob.glob(os.path.join(base, "UE_*")):
            if _is_engine_root(path):
                yield UeInstall(os.path.basename(path)[3:], path)


def _normalize_version(install: UeInstall) -> UeInstall:
    """Trust the folder name over the registry key name.

    HKCU\\...\\Builds is a free-for-all — plugin installers register entries
    there under names like "FabPlugin_5.6" pointing at a stock engine root.
    Every launcher install lives in a UE_<version> folder, so that name is the
    reliable one. Source builds keep their registry key (a GUID), which is what
    a .uproject's EngineAssociation holds for them anyway.
    """
    match = re.fullmatch(r"UE_(\d[\d.]*)", os.path.basename(install.root.rstrip("/")))
    return UeInstall(match.group(1), install.root) if match else install


def find_installs() -> list:
    """Every engine install found, newest version first."""
    found = {}
    for source in (_from_launcher_manifest, _from_registry, _from_default_roots):
        for install in source():
            found.setdefault(install.root.lower(), _normalize_version(install))

    def sort_key(install):
        # "5.4" sorts above "5.10" numerically, not lexically.
        parts = re.findall(r"\d+", install.version)
        return [-int(p) for p in parts] or [0]

    return sorted(found.values(), key=sort_key)


def read_engine_association(uproject_path: str) -> str:
    """The engine id a .uproject asks for, or "" if it doesn't name one."""
    try:
        with open(uproject_path, encoding="utf-8") as f:
            return str(json.load(f).get("EngineAssociation", "")).strip()
    except (OSError, ValueError):
        return ""


def install_for_project(uproject_path: str, installs=None):
    """The engine a project should build with.

    Prefers the engine the project names; falls back to the newest install,
    because an unset or stale EngineAssociation is common and a wrong-version
    export still beats refusing to do anything.
    """
    installs = find_installs() if installs is None else installs
    if not installs:
        return None
    wanted = read_engine_association(uproject_path) if uproject_path else ""
    if wanted:
        for install in installs:
            if install.version.lower().strip("{}") == wanted.lower().strip("{}"):
                return install
        # "5.4" should still match an install reporting "5.4.4".
        for install in installs:
            if install.version.startswith(wanted + "."):
                return install
    return installs[0]


def demo():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "UE_5.4")
        os.makedirs(os.path.join(root, "Engine", "Binaries", "Win64"))
        assert _is_engine_root(root)
        assert not _is_engine_root(os.path.join(tmp, "nope"))

        uproject = os.path.join(tmp, "P.uproject")
        with open(uproject, "w", encoding="utf-8") as f:
            json.dump({"EngineAssociation": "5.4"}, f)
        assert read_engine_association(uproject) == "5.4"

        installs = [UeInstall("5.10", "x"), UeInstall("5.4.4", root), UeInstall("4.27", "z")]
        # Exact miss, prefix hit: "5.4" must resolve to 5.4.4, not the newest.
        assert install_for_project(uproject, installs).version == "5.4.4"
        # No association falls back to the first (newest) install.
        assert install_for_project("", installs).version == "5.10"
        assert install_for_project(uproject, []) is None

        # 5.10 must outrank 5.4 despite sorting lower lexically.
        ordered = sorted(installs, key=lambda i: [-int(p) for p in re.findall(r"\d+", i.version)])
        assert ordered[0].version == "5.10", ordered

        # A junk registry name loses to the UE_<version> folder it points at.
        assert _normalize_version(UeInstall("FabPlugin_5.6", root)).version == "5.4"
        # A source build (non-UE_ folder) keeps its GUID, which is what
        # EngineAssociation holds for it.
        guid = UeInstall("{A1B2}", os.path.join(tmp, "MySourceBuild"))
        assert _normalize_version(guid).version == "{A1B2}"

    print("ok")


if __name__ == "__main__":
    demo()
