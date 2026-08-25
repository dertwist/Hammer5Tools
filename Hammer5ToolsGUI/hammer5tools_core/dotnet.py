"""
.NET Interop module for KeyValues (Datamodel.NET) handling — pythonnet, used only
by test_unreal_vmap_writer.py to independently verify written .vmap structure
(reading back through a different code path than the one that wrote it). Not
imported by any shipped/production code path: SmartProp, VPK/compiled resources,
VMAP, SourcePorter's porting pipeline, the Unreal bridge, and the git .vmap merge
tool all go through the NativeAOT ABI in hammer5tools_core/native.py instead.
"""

import sys
from pathlib import Path
from typing import Optional, Tuple, Any

RUNTIME_CONFIG_NAME = 'Hammer5Tools.runtimeconfig.json'


class DotNetPaths:
    """Centralized path management for .NET assemblies."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            development_external = Path(__file__).resolve().parents[2] / 'Hammer5ToolsCore' / 'external'
            if development_external.is_dir():
                base_dir = development_external
            else:
                from hammer5tools_core.runtime_paths import resolve_runtime_paths

                base_dir = resolve_runtime_paths().runtime_resource('external')
        else:
            base_dir = Path(base_dir)

        self.keyvalues2_net = base_dir / 'Datamodel.NET.dll'


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

            local_config = Path(__file__).parent / 'external' / 'dotnet' / RUNTIME_CONFIG_NAME
            if not local_config.exists():
                local_config = Path(__file__).parent / 'external' / RUNTIME_CONFIG_NAME
            runtime_config = str(local_config) if local_config.exists() else None

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


def setup_keyvalues2():
    """Setup KeyValues2 interop (legacy function)."""
    interop = DotNetInterop()
    return interop.setup_keyvalues()


if __name__ == "__main__":
    interop = DotNetInterop()
    assert interop.setup_keyvalues() is not None
    print("Self-check passed: KeyValues2 (Datamodel.NET) loaded")
