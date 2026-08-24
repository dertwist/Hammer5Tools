"""Python-facing adapters for the UI-neutral Hammer5Tools .NET Core."""

from __future__ import annotations

from typing import Optional

from src.dotnet import DotNetInterop


class CoreBridge:
    """Owns one initialized connection to Hammer5Tools.Core for a process."""

    _instance: Optional[CoreBridge] = None

    def __init__(self) -> None:
        self._interop = DotNetInterop()
        self._assembly = None

    @classmethod
    def instance(cls) -> CoreBridge:
        """Gets the process-wide bridge instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_vpk_index(self) -> VpkIndex:
        """Creates a Core-owned VPK index without exposing C# namespaces to callers."""
        if self._assembly is None:
            self._assembly = self._interop.setup_hammer5tools_core()

        index_type = self._assembly.GetType("Hammer5Tools.Core.Resources.VpkIndex")
        if index_type is None:
            raise RuntimeError("Hammer5Tools.Core does not provide Resources.VpkIndex")

        import System
        return VpkIndex(System.Activator.CreateInstance(index_type))


class VpkIndex:
    """Owns a disposable Core VPK index with Python-native arguments and results."""

    def __init__(self, index) -> None:
        self._index = index

    @property
    def package_count(self) -> int:
        """Gets the number of mounted VPK archives."""
        self._require_open()
        return int(self._index.PackageCount)

    def mount(self, path: str) -> None:
        """Mounts a VPK directory archive when it exists."""
        self._require_open()
        self._index.MountVpk(path)

    def add_loose_root(self, directory: str) -> None:
        """Adds a loose directory root when it exists."""
        self._require_open()
        self._index.AddLooseRoot(directory)

    def exists(self, path: str) -> bool:
        """Gets whether a path exists in a mounted archive or loose root."""
        self._require_open()
        return bool(self._index.Exists(path))

    def read_bytes(self, path: str) -> bytes | None:
        """Reads a file from a mounted archive or loose root."""
        self._require_open()
        data = self._index.TryReadBytes(path)
        return None if data is None else bytes(data)

    def close(self) -> None:
        """Releases archive handles. The bridge remains usable for new indexes."""
        if self._index is not None:
            self._index.Dispose()
            self._index = None

    def __enter__(self) -> VpkIndex:
        self._require_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _require_open(self) -> None:
        if self._index is None:
            raise RuntimeError("VpkIndex is closed")
