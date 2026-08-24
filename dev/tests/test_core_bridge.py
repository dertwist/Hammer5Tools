from src.bridge.core import VpkIndex


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
