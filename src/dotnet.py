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

# Paths already handed to AssemblyLoadContext.Default.LoadFromAssemblyPath this
# process. That call throws FileLoadException ("Assembly with same name is
# already loaded") the second time it sees the same assembly identity, even
# for the exact same file — and setup_vrf()/setup_source_porter() are each
# called from a fresh DotNetInterop() per call site (viewport, model browser,
# thumbnails, ...), so without this cache the second call site to run in a
# given process always fails.
_alc_loaded_paths: set = set()


def _load_into_default_alc(path: Path) -> None:
    """Load ``path`` into the default AssemblyLoadContext, once per process."""
    key = str(path)
    if key in _alc_loaded_paths:
        return
    import System
    alc_type = System.Type.GetType("System.Runtime.Loader.AssemblyLoadContext")
    default_context = alc_type.GetProperty("Default").GetValue(None)
    load_method = alc_type.GetMethod("LoadFromAssemblyPath", [System.String])
    load_method.Invoke(default_context, [key])
    _alc_loaded_paths.add(key)


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
        self.sharp_zstd = base_dir / 'SharpZstd.Interop.dll'

        self.skia_sharp = base_dir / 'SkiaSharp.dll'
        self.system_io_hashing = base_dir / 'System.IO.Hashing.dll'
        self.tiny_bc_sharp = base_dir / 'TinyBCSharp.dll'
        self.tiny_exr_net = base_dir / 'TinyEXR.NET.dll'
        self.source_porter_core = self._find_source_porter_core(base_dir)

    def _find_source_porter_core(self, base_dir: Path) -> Path:
        env = os.environ.get("H5T_SOURCE_PORTER_CORE")
        if env and Path(env).is_file():
            return Path(env)

        # Prefer the copy sitting next to SourcePorter.Cli's build output: a class
        # library project doesn't copy its own PackageReference dependencies
        # (ValveKeyValue/ValvePak/Datamodel.NET) into its own bin/, only the exe
        # that consumes it does. Loading SourcePorter.Core.dll from its own bin/
        # leaves those dependencies unresolved at runtime.
        net_core = Path(__file__).parent / 'net_core'
        candidates = [
            net_core / 'SourcePorter.Cli' / 'publish' / 'SourcePorter.Core.dll',
            net_core / 'SourcePorter.Cli' / 'bin' / 'Release' / 'net9.0' / 'SourcePorter.Core.dll',
            net_core / 'SourcePorter.Cli' / 'bin' / 'Debug' / 'net9.0' / 'SourcePorter.Core.dll',
            base_dir / 'SourcePorter.Core.dll',
            net_core / 'SourcePorter.Core' / 'publish' / 'SourcePorter.Core.dll',
            net_core / 'SourcePorter.Core' / 'bin' / 'Release' / 'net9.0' / 'SourcePorter.Core.dll',
            net_core / 'SourcePorter.Core' / 'bin' / 'Debug' / 'net9.0' / 'SourcePorter.Core.dll',
        ]
        for c in candidates:
            if c.is_file():
                return c
        return base_dir / 'SourcePorter.Core.dll'


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
                if not local_config.exists():
                    local_config = Path(__file__).parent / 'external' / RUNTIME_CONFIG_NAME
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
                ".NET Desktop Runtime 10.0 or newer is required for this tool. "
                "Install it from https://dotnet.microsoft.com/download/dotnet/10.0"
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

        # Load dependencies first.
        dependencies = [
            self.paths.valve_keyvalue,
            self.paths.zstd_sharp,
            self.paths.valve_pak,
            self.paths.system_io_hashing,
            self.paths.vrf
        ]

        for dep in dependencies:
            if not dep.exists():
                raise FileNotFoundError(f"Assembly not found: {dep}")
            _load_into_default_alc(dep)


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

    def setup_source_porter(self):
        """Setup SourcePorter.Core .NET interop via pythonnet.

        Deliberately does NOT call setup_vrf(): SourcePorter.Core never touches
        ValveResourceFormat, and setup_vrf() would preload src/external's legacy
        ValveKeyValue.dll (a much newer, binary-incompatible version) into the
        default ALC first, so SourcePorter.Core.dll's calls into ValveKeyValue
        would bind against the wrong version and throw MissingMethodException.
        """
        self._init_pythonnet()

        sp_dll = self.paths.source_porter_core
        if not sp_dll.exists():
            raise FileNotFoundError(f"SourcePorter.Core.dll assembly not found: {sp_dll}")

        import System
        alc_type = System.Type.GetType("System.Runtime.Loader.AssemblyLoadContext")
        default_prop = alc_type.GetProperty("Default")
        default_context = default_prop.GetValue(None)
        load_method = alc_type.GetMethod("LoadFromAssemblyPath", [System.String])

        # Preload the dependency versions SourcePorter.Core.dll was actually built
        # against, from whichever folder it was resolved from (see
        # _find_source_porter_core — normally SourcePorter.Cli's output, the only
        # place they're copied locally).
        for dep_name in ("ValveKeyValue.dll", "ValvePak.dll", "Datamodel.NET.dll",
                         "System.IO.Hashing.dll", "Blake3.dll"):
            dep = sp_dll.parent / dep_name
            if dep.is_file():
                load_method.Invoke(default_context, [str(dep)])

        load_method.Invoke(default_context, [str(sp_dll)])

        sp_assembly = System.Reflection.Assembly.LoadFrom(str(sp_dll))
        return sp_assembly


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

            normalized_path = file_path.replace("\\", "/")
            file_entry = package.FindEntry(normalized_path)

            if file_entry is None:
                return None

            # Find and invoke ReadEntry method
            read_method = self._find_read_entry_method(Package)
            if read_method is None:
                raise RuntimeError("Could not find ReadEntry method")

            params = read_method.GetParameters()
            args = System.Array.CreateInstance(System.Object, len(params))
            args[0] = file_entry

            output_bytes = System.Array.CreateInstance(Byte, 0)
            args[1] = output_bytes

            if len(params) > 2:
                args[2] = True  # validateCrc

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

                extract_method = self._find_extract_method(FileExtract)
                if extract_method is None:
                    return False

                params = extract_method.GetParameters()
                args = System.Array.CreateInstance(System.Object, len(params))
                args[0] = resource

                for i in range(1, len(params)):
                    args[i] = None

                content_file = extract_method.Invoke(None, args)

                if content_file and hasattr(content_file, 'Data') and content_file.Data:
                    # Save main file
                    data_bytes = bytes(content_file.Data)
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

    def __init__(self, min_version: str = "10.0"):
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
                        # Numeric compare — a lexical ">=" wrongly accepts "9.0"
                        # for a "10.0" minimum ("9" > "1").
                        def _ver_tuple(v):
                            out = []
                            for part in v.split(".")[:2]:
                                try:
                                    out.append(int(part))
                                except ValueError:
                                    out.append(0)
                            return tuple(out)
                        if _ver_tuple(version) >= _ver_tuple(self.min_version):
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
def check_dotnet_runtime(min_version: str = "10.0", dev_mode: bool = False) -> bool:
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


def decode_vsnd(vpk_path: str, vpk_file: str) -> tuple[bytes | None, str]:
    """
    Decodes a .vsnd_c file from a VPK in memory using ValveResourceFormat.
    Returns (audio_bytes, extension) e.g. (b'...', 'wav') or (b'...', 'mp3').
    Returns (None, '') on failure.
    """
    if vpk_path is None or vpk_file is None:
        return None, ''

    if not hasattr(decode_vsnd, "_interop"):
        decode_vsnd._interop = DotNetInterop()
    interop = decode_vsnd._interop
    interop._init_pythonnet()  # Ensure pythonnet is loaded before importing System
    import System
    from System.IO import MemoryStream
    if not hasattr(decode_vsnd, "_extractor"):
        decode_vsnd._extractor = VPKExtractor(interop)
        decode_vsnd._extractor._ensure_vrf_loaded()
    extractor = decode_vsnd._extractor

    data = extractor.extract_file(vpk_path, vpk_file)
    if data is None:
        print(f"Failed to extract {vpk_file} from {vpk_path}. File not found.")
        return None, ''
    if not isinstance(data, bytes):
        data = bytes(data)

    Resource, _, _, FileExtract, _, _ = extractor._vrf_types
    resource = System.Activator.CreateInstance(Resource)
    ms = MemoryStream(data)
    try:
        resource.Read(ms)
        if not hasattr(decode_vsnd, "_extract_method"):
            extract_method = None
            for m in FileExtract.GetMethods():
                if m.Name == "Extract":
                    extract_method = m
                    break
            decode_vsnd._extract_method = extract_method
        extract_method = decode_vsnd._extract_method
        if extract_method is None:
            print("Could not find FileExtract.Extract method.")
            return None, ''
        params = extract_method.GetParameters()
        args = System.Array.CreateInstance(System.Object, len(params))
        args[0] = resource
        for i in range(1, len(params)):
            args[i] = None
        content_file = extract_method.Invoke(None, args)
        if content_file and hasattr(content_file, 'Data') and content_file.Data:
            out_bytes = bytes(content_file.Data)
            ext = 'wav'
            if out_bytes.startswith(b'ID3') or (len(out_bytes) >= 2 and out_bytes[0] == 0xFF and (out_bytes[1] & 0xE0) == 0xE0):
                ext = 'mp3'
            elif out_bytes.startswith(b'RIFF'):
                ext = 'wav'
            elif hasattr(content_file, 'FileName') and content_file.FileName:
                ext = os.path.splitext(str(content_file.FileName))[1][1:] or 'wav'
            elif hasattr(content_file, 'Type') and str(content_file.Type).lower() == 'mp3':
                ext = 'mp3'
            return out_bytes, ext
        else:
            print("Failed to decompile .vsnd_c file using ValveResourceFormat.")
            return None, ''
    except Exception as e:
        print(f"Error decoding .vsnd file {vpk_file}: {e}")
        return None, ''
    finally:
        ms.Dispose()
        if hasattr(resource, 'Dispose'):
            resource.Dispose()


def extract_vsnd_file(output_folder: str = None, export=False, vpk_file: str = None, vpk_path: str = None):
    """
    Extracts a .vsnd_c file from a VPK to the specified output folder.
    Returns output file path, or None on failure.
    vpk_file: path inside VPK, e.g. 'sounds/items/healthshot_thud_01.vsnd_c'
    """
    if output_folder is None or vpk_path is None or vpk_file is None:
        return None

    out_bytes, ext = decode_vsnd(vpk_path, vpk_file)
    if out_bytes is None:
        return None

    output_filepath = os.path.join(output_folder, vpk_file.replace('.vsnd_c', f'.{ext}'))
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "wb") as f:
        f.write(out_bytes)
    print(f"Decompiled {vpk_file} to {output_filepath}. Size: {len(out_bytes)} bytes.")
    return output_filepath

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
import contextlib
_decompile_lock = threading.Lock()

def synchronized(lock):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextlib.contextmanager
def _suppress_dotnet_console():
    """Silence VRF's Console output (VPK preloads, "Failed to load ..." notes)
    for the duration of a block. Restores the streams afterwards. Safe because
    decompilation is serialised by _decompile_lock. Requires pythonnet to be
    initialised (call setup_vrf() first)."""
    import System
    import System.IO
    orig_out, orig_err = System.Console.Out, System.Console.Error
    try:
        System.Console.SetOut(System.IO.TextWriter.Null)
        System.Console.SetError(System.IO.TextWriter.Null)
        yield
    finally:
        System.Console.SetOut(orig_out)
        System.Console.SetError(orig_err)


if __name__ == "__main__":
    from src.settings.main import get_cs2_path
    cs2_path = get_cs2_path()
    vpk_path = os.path.join(cs2_path, 'game', 'csgo', 'pak01_dir.vpk') if cs2_path else None
    if vpk_path and os.path.exists(vpk_path):
        vpk_file = r'sounds\items\healthshot_thud_01.vsnd_c'
        data, ext = decode_vsnd(vpk_path, vpk_file)
        if data:
            assert len(data) > 0, "Decoded data is empty"
            assert data.startswith(b'RIFF') or data.startswith(b'ID3') or data.startswith(b'\xff\xfb') or data.startswith(b'\xff\xf3') or data.startswith(b'\xff\xf2'), f"Unexpected header: {data[:4]}"
            print(f"Self-check passed: decoded {vpk_file} -> {len(data)} bytes ({ext})")
        else:
            print(f"Self-check skipped: file {vpk_file} not found in VPK")
    else:
        print("Self-check skipped: CS2 or pak01_dir.vpk not found")


if __name__ == "__main__":
    from src.settings.main import get_cs2_path
    cs2_path = get_cs2_path()
    vpk_path = os.path.join(cs2_path, 'game', 'csgo', 'pak01_dir.vpk') if cs2_path else None
    if vpk_path and os.path.exists(vpk_path):
        vpk_file = r'sounds\items\healthshot_thud_01.vsnd_c'
        data, ext = decode_vsnd(vpk_path, vpk_file)
        if data:
            assert len(data) > 0, "Decoded data is empty"
            assert data.startswith(b'RIFF') or data.startswith(b'ID3') or data.startswith(b'\xff\xfb') or data.startswith(b'\xff\xf3') or data.startswith(b'\xff\xf2'), f"Unexpected header: {data[:4]}"
            print(f"Self-check passed: decoded {vpk_file} -> {len(data)} bytes ({ext})")
        else:
            print(f"Self-check skipped: file {vpk_file} not found in VPK")
    else:
        print("Self-check skipped: CS2 or pak01_dir.vpk not found")


