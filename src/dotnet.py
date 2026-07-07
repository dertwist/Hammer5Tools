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
import unittest
import binascii
from PySide6.QtWidgets import QMessageBox

tests_path = Path(__file__).parent.parent / 'tests'
RUNTIME_CONFIG_NAME = 'Hammer5Tools.runtimeconfig.json'


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
        self.sharp_gltf_core = base_dir / 'SharpGLTF.Core.dll'
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

            runtime_config = None

            # Check for bundled runtime in frozen (PyInstaller) state
            if getattr(sys, 'frozen', False):
                bundled_dotnet = os.path.join(sys._MEIPASS, 'dotnet')
                if os.path.exists(bundled_dotnet):
                    # Set DOTNET_ROOT to help clr_loader find the bundled runtime
                    os.environ["DOTNET_ROOT"] = bundled_dotnet
                    os.environ["DOTNET_ROOT_X64"] = bundled_dotnet
                    # Point to the runtime config if it exists
                    bundled_config = os.path.join(bundled_dotnet, RUNTIME_CONFIG_NAME)
                    if os.path.exists(bundled_config):
                        runtime_config = bundled_config

            if runtime_config is None:
                local_config = Path(__file__).parent / 'external' / 'dotnet' / RUNTIME_CONFIG_NAME
                if local_config.exists():
                    runtime_config = str(local_config)

            if runtime_config:
                load("coreclr", runtime_config=runtime_config)
            else:
                load("coreclr")
                
            import clr
            self._clr = clr
            self._initialized = True
        except ImportError as e:
            raise RuntimeError("Python.NET not available. Install with: pip install pythonnet") from e
        except Exception as e:
            raise RuntimeError(
                ".NET Desktop Runtime 9.0 or newer is required for this tool. "
                "Install it from https://dotnet.microsoft.com/download/dotnet/9.0"
            ) from e

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

        import System
        alc_type = System.Type.GetType("System.Runtime.Loader.AssemblyLoadContext")
        default_prop = alc_type.GetProperty("Default")
        default_context = default_prop.GetValue(None)
        load_method = alc_type.GetMethod("LoadFromAssemblyPath", [System.String])

        # Load dependencies first
        dependencies = [
            self.paths.valve_keyvalue,
            self.paths.zstd_sharp,
            self.paths.valve_pak,
            self.paths.system_io_hashing,
            self.paths.sharp_gltf_core,
            self.paths.sharp_gltf,
            self.paths.vrf
        ]

        for dep in dependencies:
            if not dep.exists():
                raise FileNotFoundError(f"Assembly not found: {dep}")
            load_method.Invoke(default_context, [str(dep)])

        # Get required types
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
        # 1. Check for bundled runtime first (in frozen state)
        if getattr(sys, 'frozen', False):
            bundled_dotnet = os.path.join(sys._MEIPASS, 'dotnet')
            if self._bundled_runtime_is_complete(bundled_dotnet):
                return True

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
            else:
                setup_vrf()
                setup_keyvalues2()
            return False

        except (FileNotFoundError, subprocess.CalledProcessError):
            if show_dialog:
                self._show_download_dialog()
            else:
                setup_vrf()
                setup_keyvalues2()
            return False

    def _bundled_runtime_is_complete(self, bundled_dotnet: str) -> bool:
        """Validate the bundled runtime enough to avoid pythonnet hostfxr crashes."""
        if not os.path.isdir(bundled_dotnet):
            return False

        runtime_config = os.path.join(bundled_dotnet, RUNTIME_CONFIG_NAME)
        if not os.path.isfile(runtime_config):
            return False

        shared = os.path.join(bundled_dotnet, "shared")
        for framework in ("Microsoft.NETCore.App", "Microsoft.WindowsDesktop.App"):
            framework_dir = os.path.join(shared, framework)
            if not os.path.isdir(framework_dir):
                return False
            versions = [v for v in os.listdir(framework_dir) if v.startswith(self.min_version)]
            if not versions:
                return False

        return True

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


def extract_vsnd_file(output_folder: str = None, export=False, vpk_file: str = None, vpk_path: str = None):
    """
    Export true will extract the file to the output folder using ValveResourceFormat's FileExtract.
    False will just return the raw file data.
    Handles both .wav and .mp3 output from .vsnd_c files.
    vpk_file: path inside VPK, e.g. 'sounds/items/healthshot_thud_01.vsnd_c'
    """
    if output_folder is None:
        export = False
    if vpk_path is None:
        raise ValueError("vpk_path must be specified.")
    if vpk_file is None:
        raise ValueError("vpk_file must be specified.")

    # Use static cache for interop and extractor
    if not hasattr(extract_vsnd_file, "_interop"):
        extract_vsnd_file._interop = DotNetInterop()
    interop = extract_vsnd_file._interop
    interop._init_pythonnet()  # Ensure pythonnet is loaded before importing System
    import System
    from System.IO import MemoryStream
    if not hasattr(extract_vsnd_file, "_extractor"):
        extract_vsnd_file._extractor = VPKExtractor(interop)
        extract_vsnd_file._extractor._ensure_vrf_loaded()
    extractor = extract_vsnd_file._extractor

    data = extractor.extract_file(vpk_path, vpk_file)
    if data is None:
        print(f"Failed to extract {vpk_file} from {vpk_path}. File not found.")
        return None
    if not isinstance(data, bytes):
        data = bytes([data[i] for i in range(data.Length)])

    if export:
        Resource, _, _, FileExtract, _, _ = extractor._vrf_types
        resource = System.Activator.CreateInstance(Resource)
        ms = MemoryStream(data)
        try:
            resource.Read(ms)
            # Find Extract method only once
            if not hasattr(extract_vsnd_file, "_extract_method"):
                extract_method = None
                for m in FileExtract.GetMethods():
                    if m.Name == "Extract":
                        extract_method = m
                        break
                extract_vsnd_file._extract_method = extract_method
            extract_method = extract_vsnd_file._extract_method
            if extract_method is None:
                print("Could not find FileExtract.Extract method.")
                return None
            params = extract_method.GetParameters()
            args = System.Array.CreateInstance(System.Object, len(params))
            args[0] = resource
            for i in range(1, len(params)):
                args[i] = None
            content_file = extract_method.Invoke(None, args)
            if content_file and hasattr(content_file, 'Data') and content_file.Data:
                ext = 'wav'
                if hasattr(content_file, 'FileName') and content_file.FileName:
                    ext = os.path.splitext(str(content_file.FileName))[1][1:] or 'wav'
                elif hasattr(content_file, 'Type') and str(content_file.Type).lower() == 'mp3':
                    ext = 'mp3'
                output_filepath = os.path.join(output_folder, vpk_file.replace('.vsnd_c', f'.{ext}'))
                os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
                out_bytes = bytes([content_file.Data[i] for i in range(content_file.Data.Length)])
                with open(output_filepath, "wb") as f:
                    f.write(out_bytes)
                print(f"Decompiled {vpk_file} to {output_filepath}. Size: {len(out_bytes)} bytes.")
                return output_filepath
            else:
                print("Failed to decompile .vsnd_c file using ValveResourceFormat.")
                return None
        finally:
            ms.Dispose()
            if hasattr(resource, 'Dispose'):
                resource.Dispose()
    else:
        return data

# Start Extract thumbnail from VMAP file

def extract_vmap_thumbnail(vmap_path):
    Datamodel, _, DeferredMode = setup_keyvalues2()
    if not os.path.exists(vmap_path):
        return None, None

    dmx_model = None
    try:
        dmx_model = Datamodel.Load(vmap_path, DeferredMode.Automatic)
        if not dmx_model or not dmx_model.Root or not hasattr(dmx_model, 'PrefixAttributes'):
            return None, None
        prefix_attrs = dmx_model.PrefixAttributes
        data = prefix_attrs.get("asset_preview_thumbnail")
        fmt = prefix_attrs.get("asset_preview_thumbnail_format", "jpg")
        if data is None:
            return None, None
        # Convert .NET byte array to hex string
        if hasattr(data, 'Length'):
            hex_data = ''.join(f'{data[i]:02X}' for i in range(data.Length))
        elif isinstance(data, bytes):
            hex_data = data.hex().upper()
        elif isinstance(data, str):
            hex_data = data.strip().replace('\n', '').replace('\t', '').replace(' ', '')
        else:
            hex_data = str(data).strip().replace('\n', '').replace('\t', '').replace(' ', '')
        return hex_data, fmt
    except Exception:
        return None, None
    finally:
        if dmx_model and hasattr(dmx_model, 'Dispose'):
            dmx_model.Dispose()
        import gc; gc.collect()

class TestVMapThumbnail(unittest.TestCase):
    def test_extract_vmap_thumbnail(self):
        vmap_path = os.path.join(tests_path, 'files', 'vmap', 'xxx_mapname_xxx.vmap')
        hex_data, fmt = extract_vmap_thumbnail(vmap_path)
        self.assertIsNotNone(hex_data, "No thumbnail data found.")
        self.assertIsInstance(hex_data, str, "Hex data is not a string.")
        self.assertGreater(len(hex_data), 0, "Hex data is empty.")

        try:
            image_bytes = binascii.unhexlify(hex_data)
        except Exception as e:
            self.fail(f"Failed to decode hex data: {e}")

        try:
            output_path = Path(vmap_path).with_suffix(f'.thumbnail.{fmt or "jpg"}')
            output_path.write_bytes(image_bytes)
            print(f"Saved thumbnail to: {output_path}")
        except Exception as e:
            self.fail(f"Failed to save image: {e}")

# End Extract thumbnail from VMAP file

# Start Extract reference files from VMAP file


def extract_vmap_references(vmap_path):
    Datamodel, _, DeferredMode = setup_keyvalues2()
    if not os.path.exists(vmap_path):
        return None, None

    dmx_model = None
    try:
        dmx_model = Datamodel.Load(vmap_path, DeferredMode.Automatic)
        if not dmx_model or not dmx_model.Root or not hasattr(dmx_model, 'PrefixAttributes'):
            return None, None
        prefix_attrs = dmx_model.PrefixAttributes
        data = prefix_attrs.get("map_asset_references")
        if data is None:
            return None, None
        return list(data)
    except Exception:
        return None, None
    finally:
        if dmx_model and hasattr(dmx_model, 'Dispose'):
            dmx_model.Dispose()
        import gc; gc.collect()

# End Extract reference files from VMAP file
class TestVMapReferences(unittest.TestCase):
    def test_extract_vmap_references(self):
        vmap_path = os.path.join(tests_path, 'files', 'vmap', 'xxx_mapname_xxx.vmap')
        references = extract_vmap_references(vmap_path)
        print(references)
        self.assertIsNotNone(references, "No references found.")
        self.assertIsInstance(references, list, "Data is list.")
        self.assertGreater(len(references), 0, "References list is empty.")

        try:
            print(references)
        except Exception as e:
            self.fail(f"Failed to print references: {e}")

import threading
_decompile_lock = threading.Lock()

def synchronized(lock):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorator

@synchronized(_decompile_lock)
def decompile_model_to_glb(vmdl_path: str) -> Optional[str]:
    """
    Decompiles a compiled model file (.vmdl_c) to a .glb file.
    Saves the output .glb under userdata/SmartPropEditor/ organized by Addon vs Core.
    """
    import os
    from pathlib import Path
    from typing import Optional

    # Normalize paths
    vmdl_path = vmdl_path.replace("\\", "/").strip("/")
    if not vmdl_path.endswith(".vmdl") and not vmdl_path.endswith(".vmdl_c"):
        vmdl_path += ".vmdl"
        
    if vmdl_path.endswith(".vmdl_c"):
        vmdl_c_path = vmdl_path
        vmdl_path = vmdl_path[:-2]
    else:
        vmdl_c_path = vmdl_path + "_c"
        
    # Import settings/common dynamically to avoid circular dependencies
    from src.common import get_cs2_path, SmartPropEditor_Path
    from src.settings.common import get_addon_name
    
    cs2_path = get_cs2_path()
    if not cs2_path:
        return None
        
    addon_name = get_addon_name() or "addon"
    
    # Define source paths
    addon_vmdl_c = os.path.join(cs2_path, "game", "csgo_addons", addon_name, vmdl_c_path)
    core_vmdl_c = os.path.join(cs2_path, "game", "csgo", vmdl_c_path)
    vpk_path = os.path.join(cs2_path, "game", "csgo", "pak01_dir.vpk")
    
    is_addon_model = False
    source_fs_path = None
    in_vpk = False
    
    # Locate the model
    if os.path.exists(addon_vmdl_c):
        is_addon_model = True
        source_fs_path = addon_vmdl_c
    elif os.path.exists(core_vmdl_c):
        is_addon_model = False
        source_fs_path = core_vmdl_c
    else:
        in_vpk = True
        is_addon_model = False
        
    # Determine target cache path
    dest_subfolder = os.path.join("cache", addon_name if is_addon_model else "csgo")
    glb_subpath = vmdl_path.rsplit(".", 1)[0] + ".glb"
    output_glb_path = os.path.join(str(SmartPropEditor_Path), dest_subfolder, glb_subpath)
    
    # Check cache validity
    if os.path.exists(output_glb_path):
        if in_vpk:
            return output_glb_path
        elif source_fs_path:
            src_mtime = os.path.getmtime(source_fs_path)
            dest_mtime = os.path.getmtime(output_glb_path)
            if dest_mtime > src_mtime:
                return output_glb_path
                
    # Extract bytes
    data = None
    if source_fs_path:
        try:
            with open(source_fs_path, "rb") as f:
                data = f.read()
        except Exception as e:
            print(f"Error reading filesystem model {source_fs_path}: {e}")
            return None
    elif in_vpk:
        # Load interop and extract from VPK
        interop = DotNetInterop()
        interop._init_pythonnet()
        extractor = VPKExtractor(interop)
        extractor._ensure_vrf_loaded()
        try:
            data = extractor.extract_file(vpk_path, vmdl_c_path)
        except Exception as e:
            print(f"Error extracting {vmdl_c_path} from VPK: {e}")
            return None
            
    if data is None:
        return None
        
    if not isinstance(data, bytes):
        data = bytes([data[i] for i in range(data.Length)])
        
    # Decompile using GltfModelExporter (ensure assemblies loaded first)
    setup_vrf()
    
    import System
    from System.IO import MemoryStream
    
    # Resolve types from loaded assemblies
    FileExtract = System.Type.GetType("ValveResourceFormat.IO.FileExtract, ValveResourceFormat")
    if not FileExtract:
        vrf_assembly = System.Reflection.Assembly.Load("ValveResourceFormat")
        NullFileLoaderType = vrf_assembly.GetType("ValveResourceFormat.IO.NullFileLoader")
        GltfModelExporterType = vrf_assembly.GetType("ValveResourceFormat.IO.GltfModelExporter")
        Resource = vrf_assembly.GetType("ValveResourceFormat.Resource")
    else:
        vrf_assembly = FileExtract.Assembly
        NullFileLoaderType = vrf_assembly.GetType("ValveResourceFormat.IO.NullFileLoader")
        GltfModelExporterType = vrf_assembly.GetType("ValveResourceFormat.IO.GltfModelExporter")
        Resource = vrf_assembly.GetType("ValveResourceFormat.Resource")
        
    null_file_loader = System.Activator.CreateInstance(NullFileLoaderType)
    resource = System.Activator.CreateInstance(Resource)
    ms = MemoryStream(data)
    try:
        resource.Read(ms)
        exporter = System.Activator.CreateInstance(GltfModelExporterType, null_file_loader)
        
        # Ensure output folder exists
        os.makedirs(os.path.dirname(output_glb_path), exist_ok=True)
        import System.Threading
        token = getattr(System.Threading.CancellationToken, "None")
        
        # Try exporting with materials/textures first
        try:
            exporter.ExportMaterials = True
            exporter.Export(resource, output_glb_path, token)
        except Exception as e:
            print(f"Failed to decompile with materials: {e}. Retrying without materials...")
            exporter.ExportMaterials = False
            exporter.Export(resource, output_glb_path, token)
            
        if os.path.exists(output_glb_path):
            return output_glb_path
        return None
    except Exception as e:
        print(f"Error decompiling model {vmdl_path}: {e}")
        return None
    finally:
        ms.Dispose()
        if hasattr(resource, 'Dispose'):
            resource.Dispose()

@synchronized(_decompile_lock)
def decompile_texture_to_png(vtex_path: str) -> Optional[str]:
    """
    Decompiles a compiled texture (.vtex_c) to a .png file.
    Saves the output .png under userdata/SmartPropEditor/cache/ organized by Addon vs csgo.
    """
    import os
    from pathlib import Path
    from typing import Optional
    import System
    from System.IO import MemoryStream
    from src.common import get_cs2_path, SmartPropEditor_Path
    from src.settings.common import get_addon_name
    
    # Normalize paths
    vtex_path = vtex_path.replace("\\", "/").strip("/")
    if not vtex_path.endswith(".vtex") and not vtex_path.endswith(".vtex_c"):
        vtex_path += ".vtex"
        
    if vtex_path.endswith(".vtex_c"):
        vtex_c_path = vtex_path
        vtex_path = vtex_path[:-2]
    else:
        vtex_c_path = vtex_path + "_c"
        
    cs2_path = get_cs2_path()
    if not cs2_path:
        return None
        
    addon_name = get_addon_name() or "addon"
    
    # Define source paths
    addon_vtex_c = os.path.join(cs2_path, "game", "csgo_addons", addon_name, vtex_c_path)
    core_vtex_c = os.path.join(cs2_path, "game", "csgo", vtex_c_path)
    vpk_path = os.path.join(cs2_path, "game", "csgo", "pak01_dir.vpk")
    
    is_addon_texture = False
    source_fs_path = None
    in_vpk = False
    
    # Locate the texture
    if os.path.exists(addon_vtex_c):
        is_addon_texture = True
        source_fs_path = addon_vtex_c
    elif os.path.exists(core_vtex_c):
        is_addon_texture = False
        source_fs_path = core_vtex_c
    else:
        in_vpk = True
        is_addon_texture = False
        
    # Determine target cache path
    dest_subfolder = os.path.join("cache", addon_name if is_addon_texture else "csgo")
    png_subpath = vtex_path.rsplit(".", 1)[0] + ".png"
    output_png_path = os.path.join(str(SmartPropEditor_Path), dest_subfolder, png_subpath)
    
    # Check cache validity
    if os.path.exists(output_png_path):
        if in_vpk:
            return output_png_path
        elif source_fs_path:
            src_mtime = os.path.getmtime(source_fs_path)
            dest_mtime = os.path.getmtime(output_png_path)
            if dest_mtime > src_mtime:
                return output_png_path
                
    # Extract bytes
    data = None
    if source_fs_path:
        try:
            with open(source_fs_path, "rb") as f:
                data = f.read()
        except Exception as e:
            print(f"Error reading filesystem texture {source_fs_path}: {e}")
            return None
    elif in_vpk:
        # Load interop and extract from VPK
        from src.dotnet import DotNetInterop, VPKExtractor
        interop = DotNetInterop()
        interop._init_pythonnet()
        extractor = VPKExtractor(interop)
        extractor._ensure_vrf_loaded()
        try:
            data = extractor.extract_file(vpk_path, vtex_c_path)
        except Exception as e:
            print(f"Error extracting {vtex_c_path} from VPK: {e}")
            return None
            
    if data is None:
        return None
        
    if not isinstance(data, bytes):
        data = bytes([data[i] for i in range(data.Length)])
        
    # Decompile using VRF
    setup_vrf()
    
    FileExtract = System.Type.GetType("ValveResourceFormat.IO.FileExtract, ValveResourceFormat")
    if not FileExtract:
        vrf_assembly = System.Reflection.Assembly.Load("ValveResourceFormat")
        Resource = vrf_assembly.GetType("ValveResourceFormat.Resource")
        NullFileLoaderType = vrf_assembly.GetType("ValveResourceFormat.IO.NullFileLoader")
    else:
        vrf_assembly = FileExtract.Assembly
        Resource = vrf_assembly.GetType("ValveResourceFormat.Resource")
        NullFileLoaderType = vrf_assembly.GetType("ValveResourceFormat.IO.NullFileLoader")
        
    resource = System.Activator.CreateInstance(Resource)
    resource.FileName = vtex_path
    
    ms = MemoryStream(data)
    try:
        resource.Read(ms)
        
        # Find FileExtract.Extract method
        extract_method = None
        for m in FileExtract.GetMethods():
            if m.Name == "Extract":
                extract_method = m
                break
        if extract_method is None:
            print("Could not find FileExtract.Extract method.")
            return None
            
        null_file_loader = System.Activator.CreateInstance(NullFileLoaderType)
        params = extract_method.GetParameters()
        args = System.Array.CreateInstance(System.Object, len(params))
        args[0] = resource
        args[1] = null_file_loader
        for i in range(2, len(params)):
            args[i] = None
            
        content_file = extract_method.Invoke(None, args)
        if content_file:
            # Check SubFiles first
            if hasattr(content_file, 'SubFiles') and content_file.SubFiles and content_file.SubFiles.Count > 0:
                sub = content_file.SubFiles[0]
                sub_data = sub.Extract()
                if sub_data:
                    out_bytes = bytes([sub_data[i] for i in range(sub_data.Length)])
                    os.makedirs(os.path.dirname(output_png_path), exist_ok=True)
                    with open(output_png_path, "wb") as f:
                        f.write(out_bytes)
                    return output_png_path
            # Fallback to Data property
            elif hasattr(content_file, 'Data') and content_file.Data:
                out_bytes = bytes([content_file.Data[i] for i in range(content_file.Data.Length)])
                os.makedirs(os.path.dirname(output_png_path), exist_ok=True)
                with open(output_png_path, "wb") as f:
                    f.write(out_bytes)
                return output_png_path
        return None
    except Exception as e:
        print(f"Error decompiling texture {vtex_path}: {e}")
        return None
    finally:
        ms.Dispose()
        if hasattr(resource, 'Dispose'):
            resource.Dispose()

if __name__ == "__main__":
    pass

