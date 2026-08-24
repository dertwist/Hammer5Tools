from types import SimpleNamespace

from src.bridge.core import CoreBridge, VpkIndex


def test_core_bridge_is_a_process_singleton():
    original = CoreBridge._instance
    try:
        CoreBridge._instance = None
        assert CoreBridge.instance() is CoreBridge.instance()
    finally:
        CoreBridge._instance = original


class FakeMethod:
    def __init__(self, result):
        self.result = result

    def Invoke(self, target, arguments):
        return self.result


class FakeApiType:
    def __init__(self, result):
        self.result = result

    def GetMethod(self, name):
        assert name == "Probe"
        return FakeMethod(self.result)


class FakeAssembly:
    def __init__(self, result):
        self.result = result

    def GetType(self, name):
        assert name == "Hammer5Tools.Core.CoreApi"
        return FakeApiType(self.result)


class FakeInterop:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def setup_hammer5tools_core(self):
        if self.error:
            raise self.error
        return FakeAssembly(self.result)


def test_core_probe_translates_success_to_python_status():
    result = SimpleNamespace(IsSuccess=True, Value="1.0", Diagnostics=[])

    status = CoreBridge(FakeInterop(result)).probe()

    assert status.available
    assert status.version == "1.0"
    assert status.diagnostic is None


def test_core_probe_translates_load_failures_to_diagnostics():
    status = CoreBridge(FakeInterop(error=OSError("missing runtime"))).probe()

    assert not status.available
    assert "missing runtime" in status.diagnostic


class FakeVpkIndex:
    def __init__(self):
        self.PackageCount = 0
        self.roots = []
        self.disposed = False

    def MountVpk(self, path):
        self.PackageCount += 1

    def AddLooseRoot(self, directory):
        self.roots.append(directory)

    def Exists(self, path):
        return path == "present.txt"

    def TryReadBytes(self, path):
        return bytearray(b"data") if path == "present.txt" else None

    def Dispose(self):
        self.disposed = True


def test_vpk_index_converts_core_results_to_python_values():
    native = FakeVpkIndex()
    index = VpkIndex(native)

    index.mount("pak01_dir.vpk")
    index.add_loose_root("content")

    assert index.package_count == 1
    assert index.exists("present.txt")
    assert index.read_bytes("present.txt") == b"data"
    assert index.read_bytes("missing.txt") is None
    assert native.roots == ["content"]


def test_vpk_index_rejects_calls_after_close():
    native = FakeVpkIndex()
    index = VpkIndex(native)

    index.close()

    assert native.disposed
    try:
        index.exists("present.txt")
    except RuntimeError as error:
        assert str(error) == "VpkIndex is closed"
    else:
        raise AssertionError("Closed VpkIndex accepted a call")
