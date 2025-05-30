"""
.NET Interop module for Valve Resource Format and KeyValues handling.
Provides simplified interfaces for working with VRF, VPK files, and KeyValues.
"""

import os
import sys
import json
import subprocess
import webbrowser
import urllib.request
from pathlib import Path
from typing import Optional, Tuple, Any

from PySide6.QtWidgets import QMessageBox


class DotNetPaths:
    """Centralized path management for .NET assemblies."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent / 'external'
        else:
            base_dir = Path(base_dir)

        self.vrf = base_dir / 'ValveResourceFormat.dll'
        self.valve_keyvalue = base_dir / 'ValveKeyValue.dll'
        self.valve_pak = base_dir / 'ValvePak.dll'
        self.zstd_sharp = base_dir / 'ZstdSharp.dll'
        self.keyvalues2_net = base_dir / 'Datamodel.NET.dll'
        self.compression = base_dir / 'K4os.Compression.LZ4.dll'
        self.sharp_gltf = base_dir / 'SharpGLTF.Toolkit.dll'
        self.sharp_zstd = base_dir / 'SharpZstd.Interop.dll'
        self.skia_sharp = base_dir / 'SkiaSharp.dll'
        self.system_io_hashing = base_dir / 'System.IO.Hashing.dll'
        self.tiny_bc_sharp = base_dir / 'TinyBCSharp.dll'
        self.tiny_exr_net = base_dir / 'TinyEXR.NET.dll'


class DotNetInterop:
    """Main .NET interop handler."""

    def __init__(self):
        self.paths = DotNetPaths()
        self._clr = None
        self._system = None
        self._initialized = False

    def _init_pythonnet(self):
        """Initialize Python.NET if not already done."""
        if self._initialized:
            return

        try:
            from pythonnet import load
            load("coreclr")
            import clr
            self._clr = clr
            self._initialized = True
        except ImportError as e:
            raise RuntimeError("Python.NET not available. Install with: pip install pythonnet") from e

    def _load_assembly(self, path: Path) -> None:
        """Load a .NET assembly with error handling."""
        if not path.exists():
            raise FileNotFoundError(f"Assembly not found: {path}")

        try:
            self._clr.AddReference(str(path))
        except Exception:
            # Fallback to LoadFrom for problematic assemblies
            import System
            assembly = System.Reflection.Assembly.LoadFrom(str(path))
            self._clr.AddReference(assembly)

    def setup_keyvalues(self) -> Tuple[Any, Any, Any]:
        """Setup KeyValues2 .NET interop."""
        self._init_pythonnet()

        # Ensure DLL directory is in PATH
        dll_dir = self.paths.keyvalues2_net.parent
        if str(dll_dir) not in sys.path:
            sys.path.append(str(dll_dir))

        self._load_assembly(self.paths.keyvalues2_net)

        import Datamodel
        from Datamodel.Codecs import DeferredMode

        return Datamodel.Datamodel, Datamodel.Element, DeferredMode

    def setup_vrf(self) -> Tuple[Any, Any, Any, Any, Any, Any]:
        """Setup Valve Resource Format .NET interop."""
        self._init_pythonnet()

        # Add DLL directory to PATH for assembly resolution
        dll_dir = self.paths.vrf.parent
        os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")

        # Load dependencies first
        dependencies = [
            self.paths.valve_keyvalue,
            self.paths.zstd_sharp,
            self.paths.valve_pak
        ]

        for dep in dependencies:
            self._load_assembly(dep)

        # Load main VRF assembly
        self._load_assembly(self.paths.vrf)

        # Get required types
        import System
        vrf_assembly = System.Reflection.Assembly.LoadFrom(str(self.paths.vrf))
        valvepak_assembly = System.Reflection.Assembly.LoadFrom(str(self.paths.valve_pak))

        # Find required types
        Resource = vrf_assembly.GetType("ValveResourceFormat.Resource")
        Texture = vrf_assembly.GetType("ValveResourceFormat.Texture")
        TextureExtract = vrf_assembly.GetType("ValveResourceFormat.TextureExtract")
        FileExtract = self._find_type(vrf_assembly, "FileExtract") or vrf_assembly.GetType(
            "ValveResourceFormat.IO.FileExtract")
        ContentFile = self._find_type(vrf_assembly, "ContentFile") or vrf_assembly.GetType(
            "ValveResourceFormat.IO.ContentFile")
        Package = self._find_package_type(valvepak_assembly)

        # Validate all types were found
        missing = []
        types = [Resource, FileExtract, ContentFile, Package]
        names = ["Resource", "FileExtract", "ContentFile", "Package"]

        for type_obj, name in zip(types, names):
            if type_obj is None:
                missing.append(name)

        if missing:
            raise RuntimeError(f"Could not find required .NET types: {', '.join(missing)}")

        return Resource, Texture, TextureExtract, FileExtract, ContentFile, Package

    def _find_type(self, assembly, type_name: str):
        """Find a type by partial name in assembly."""
        for type_info in assembly.GetTypes():
            if type_name in type_info.Name:
                return type_info
        return None

    def _find_package_type(self, assembly):
        """Find Package type with various possible namespaces."""
        possible_names = [
            "ValvePak.Package",
            "SteamDatabase.ValvePak.Package"
        ]

        for name in possible_names:
            package_type = assembly.GetType(name)
            if package_type:
                return package_type

        # Fallback: find any type with 'Package' in name
        return self._find_type(assembly, "Package")


class VPKExtractor:
    """Simplified VPK file extraction."""

    def __init__(self, interop: DotNetInterop):
        self.interop = interop
        self._vrf_types = None

    def _ensure_vrf_loaded(self):
        """Ensure VRF types are loaded."""
        if self._vrf_types is None:
            self._vrf_types = self.interop.setup_vrf()

    def extract_file(self, vpk_path: str, file_path: str) -> Optional[bytes]:
        """Extract a file from VPK. Returns bytes or None if not found."""
        self._ensure_vrf_loaded()

        import System
        from System import Array, Byte
        from System.Reflection import BindingFlags

        _, _, _, _, _, Package = self._vrf_types

        package = System.Activator.CreateInstance(Package)
        try:
            package.Read(vpk_path)

            # Normalize path
            normalized_path = file_path.replace("\\", "/")
            file_entry = package.FindEntry(normalized_path)

            if file_entry is None:
                return None

            # Find and invoke ReadEntry method
            read_method = self._find_read_entry_method(Package)
            if read_method is None:
                raise RuntimeError("Could not find ReadEntry method")

            # Prepare method parameters
            params = read_method.GetParameters()
            args = System.Array.CreateInstance(System.Object, len(params))
            args[0] = file_entry

            output_bytes = System.Array.CreateInstance(Byte, 0)
            args[1] = output_bytes

            if len(params) > 2:
                args[2] = True  # validateCrc

            # Invoke method
            read_method.Invoke(package, args)
            return args[1]  # The out parameter contains the data

        finally:
            if hasattr(package, 'Dispose'):
                package.Dispose()

    def _find_read_entry_method(self, package_type):
        """Find appropriate ReadEntry method."""
        from System import Type
        from System.Reflection import BindingFlags

        methods = package_type.GetMethods(BindingFlags.Public | BindingFlags.Instance)
        for method in methods:
            if method.Name == "ReadEntry":
                params = method.GetParameters()
                if len(params) >= 2:
                    return method
        return None


class ResourceProcessor:
    """Process Valve resources."""

    def __init__(self, interop: DotNetInterop):
        self.interop = interop
        self._vrf_types = None

    def _ensure_vrf_loaded(self):
        """Ensure VRF types are loaded."""
        if self._vrf_types is None:
            self._vrf_types = self.interop.setup_vrf()

    def extract_resource(self, data: bytes, output_path: str) -> bool:
        """Extract a resource from binary data."""
        self._ensure_vrf_loaded()

        import System
        from System.IO import MemoryStream

        Resource, _, _, FileExtract, _, _ = self._vrf_types

        try:
            # Create resource and load data
            resource = System.Activator.CreateInstance(Resource)
            memory_stream = MemoryStream(data)

            try:
                resource.Read(memory_stream)

                # Extract using FileExtract
                extract_method = self._find_extract_method(FileExtract)
                if extract_method is None:
                    return False

                # Invoke extract method
                params = extract_method.GetParameters()
                args = System.Array.CreateInstance(System.Object, len(params))
                args[0] = resource

                for i in range(1, len(params)):
                    args[i] = None

                content_file = extract_method.Invoke(None, args)

                if content_file and hasattr(content_file, 'Data') and content_file.Data:
                    # Save main file
                    data_bytes = bytes([content_file.Data[i] for i in range(content_file.Data.Length)])
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(data_bytes)
                    return True

            finally:
                memory_stream.Dispose()
                if hasattr(resource, 'Dispose'):
                    resource.Dispose()

        except Exception:
            return False

        return False

    def extract_resource_from_vpk(self, vpk_path: str, file_path: str, output_path: str) -> bool:
        """Extract a resource from a VPK file using VPKExtractor and process it."""
        extractor = VPKExtractor(self.interop)
        data = extractor.extract_file(vpk_path, file_path)
        if data is None:
            return False
        return self.extract_resource(data, output_path)

    def _find_extract_method(self, file_extract_type):
        """Find static Extract method."""
        from System.Reflection import BindingFlags
        import System
        from System.IO import MemoryStream

        methods = file_extract_type.GetMethods(BindingFlags.Public | BindingFlags.Static)
        for method in methods:
            if method.Name == "Extract":
                return method
        return None


class DotNetRuntimeChecker:
    """Check and manage .NET runtime installation."""

    def __init__(self, min_version: str = "9.0"):
        self.min_version = min_version

    def check_runtime(self, show_dialog: bool = True) -> bool:
        """Check if compatible .NET runtime is installed."""
        try:
            result = subprocess.run(
                ["dotnet", "--list-runtimes"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            # Check for WindowsDesktop runtime
            for line in result.stdout.splitlines():
                if line.startswith("Microsoft.WindowsDesktop.App"):
                    parts = line.split()
                    if len(parts) >= 2:
                        version = parts[1]
                        version_major_minor = ".".join(version.split(".")[:2])
                        if version_major_minor >= self.min_version:
                            return True

            if show_dialog:
                self._show_download_dialog()
            return False

        except (FileNotFoundError, subprocess.CalledProcessError):
            if show_dialog:
                self._show_download_dialog()
            return False

    def _show_download_dialog(self):
        """Show dialog to download .NET runtime."""
        try:
            latest_version = self._get_latest_version()
            download_url = self._get_download_url(latest_version)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(".NET Desktop Runtime Required")
            msg.setText(f"Required .NET Desktop runtime >= {self.min_version} not found.")
            msg.setInformativeText(f"Please download and install .NET {latest_version} for Windows.")
            msg.setStandardButtons(QMessageBox.Open | QMessageBox.Cancel)

            if msg.exec() == QMessageBox.Open:
                webbrowser.open(download_url)
                sys.exit(0)

        except Exception:
            # Fallback to generic download page
            webbrowser.open("https://dotnet.microsoft.com/download")

    def _get_latest_version(self) -> str:
        """Get latest .NET version from Microsoft API."""
        try:
            url = "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/releases-index.json"
            with urllib.request.urlopen(url) as response:
                data = json.load(response)
                releases = data.get("releases-index", [])
                for release in releases:
                    channel_version = release.get("channel-version", "")
                    if channel_version >= self.min_version:
                        return channel_version
                if releases:
                    return releases[0].get("channel-version", self.min_version)
        except Exception:
            pass
        return self.min_version

    def _get_download_url(self, version: str) -> str:
        """Get download URL for specific .NET version."""
        try:
            url = f"https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/{version}/releases.json"
            with urllib.request.urlopen(url) as response:
                data = json.load(response)
                latest = data.get("latest-release", version)
                return f"https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/{latest}/windowsdesktop-runtime-{latest}-win-x64.exe"
        except Exception:
            return f"https://dotnet.microsoft.com/en-us/download/dotnet/{version}"


# Convenience functions for backward compatibility
def check_dotnet_runtime(min_version: str = "9.0", dev_mode: bool = False) -> bool:
    """Check .NET runtime availability."""
    checker = DotNetRuntimeChecker(min_version)
    return checker.check_runtime(show_dialog=not dev_mode)


def setup_vrf():
    """Setup VRF interop (legacy function)."""
    interop = DotNetInterop()
    return interop.setup_vrf()


def setup_keyvalues2():
    """Setup KeyValues2 interop (legacy function)."""
    interop = DotNetInterop()
    return interop.setup_keyvalues()

def extract_vsnd_file(output_folder:str = None, export=False):
    """"
    Export true will extract the file to the output folder.
    False will just play the file.
    """
    if output_folder is None:
        export = False
    import os
    vpk_path = r"E:\\SteamLibrary\\steamapps\\common\\Counter-Strike Global Offensive\\csgo\\pak01_dir.vpk"
    vpk_file = r"sounds/common/talk.wav"
    vpk_file = vpk_file.replace("sounds/", "sound/")  # Normalize path for VPK

    interop = DotNetInterop()
    extractor = VPKExtractor(interop)
    extractor._ensure_vrf_loaded()
    data = extractor.extract_file(vpk_path, vpk_file)

    if data is not None and not isinstance(data, bytes):
        data = bytes([data[i] for i in range(data.Length)])

    if export:
        output_filepath = os.path.join(output_folder, vpk_file)
        if data is None:
            print((f"Failed to extract {vpk_file} from {vpk_path}. File not found."))
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        with open(output_filepath, "wb") as f:
            f.write(data)
        print(f"Extracted {vpk_file} to {output_filepath}. Size: {len(data)} bytes.")
        return output_filepath
    else:
        return data

def get_vpk_content_dict(vpk_path: str) -> dict:
    interop = DotNetInterop()
    interop._init_pythonnet()  # Ensure pythonnet is initialized before importing System
    import System
    extractor = VPKExtractor(interop)
    extractor._ensure_vrf_loaded()
    _, _, _, _, _, Package = extractor._vrf_types
    package = System.Activator.CreateInstance(Package)
    package.Read(vpk_path)
    entries = package.Entries
    file_dict = {}
    for ext_key in entries.Keys:
        entry_list = entries[ext_key]
        for entry in entry_list:
            dir_name = getattr(entry, 'DirectoryName', None)
            file_name = getattr(entry, 'FileName', None)
            type_name = getattr(entry, 'TypeName', None)
            if dir_name:
                full_path = f"{dir_name}/{file_name}.{type_name}"
            else:
                full_path = f"{file_name}.{type_name}"
            # Store entry info as needed, here just storing None as placeholder
            file_dict[full_path] = None
    return file_dict

if __name__ == "__main__":
    pass