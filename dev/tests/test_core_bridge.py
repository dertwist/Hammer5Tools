from types import SimpleNamespace

from src.bridge.core import CoreBridge, SmartPropModel, ValveMapEntity, VpkIndex


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


def test_smartprop_models_are_converted_without_core_types():
    matrix = SimpleNamespace(**{
        f"M{row}{column}": float((row - 1) * 4 + column)
        for row in range(1, 5)
        for column in range(1, 5)
    })
    model = SimpleNamespace(
        ElementId=7,
        ModelName="models/example.vmdl",
        Transform=matrix,
        MaterialGroup="default",
        TintColor=SimpleNamespace(X=1, Y=0.5, Z=0.25, W=1),
    )

    converted = CoreBridge._convert_smartprop_model(model)

    assert converted == SmartPropModel(
        7,
        "models/example.vmdl",
        tuple(float(value) for value in range(1, 17)),
        "default",
        (1.0, 0.5, 0.25, 1.0),
    )


def test_smartprop_serializer_uses_python_native_document(monkeypatch):
    captured = {}

    class FakeSerializer:
        @staticmethod
        def SerializeJson(value):
            captured["json"] = value
            return "<!-- kv3 -->"

    bridge = CoreBridge(FakeInterop())
    bridge._assembly = object()
    monkeypatch.setitem(
        __import__("sys").modules,
        "Hammer5Tools.Core.SmartProps",
        SimpleNamespace(SmartPropDocumentSerializer=FakeSerializer),
    )

    text = bridge.serialize_smartprop({"m_Children": []})

    assert text == "<!-- kv3 -->"
    assert captured["json"] == '{"m_Children":[]}'


def test_smartprop_deserializer_returns_python_native_document(monkeypatch):
    class FakeSerializer:
        @staticmethod
        def DeserializeText(value):
            assert value == "<!-- kv3 -->"
            return '{"m_Children":[]}'

    bridge = CoreBridge(FakeInterop())
    bridge._assembly = object()
    monkeypatch.setitem(
        __import__("sys").modules,
        "Hammer5Tools.Core.SmartProps",
        SimpleNamespace(SmartPropDocumentSerializer=FakeSerializer),
    )

    document = bridge.deserialize_smartprop("<!-- kv3 -->")

    assert document == {"m_Children": []}


def test_valve_map_entities_are_converted_without_core_types():
    properties = [
        SimpleNamespace(Key="classname", Value="point_camera"),
        SimpleNamespace(Key="targetname", Value="camera"),
    ]
    entity = SimpleNamespace(
        ClassName="point_camera",
        Origin="1 2 3",
        Angles=None,
        Properties=properties,
    )

    converted = CoreBridge._convert_valve_map_entity(entity)

    assert converted == ValveMapEntity(
        "point_camera",
        "1 2 3",
        None,
        {"classname": "point_camera", "targetname": "camera"},
    )


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

    def EnumerateEntries(self, suffixes):
        return [SimpleNamespace(Path="models/example.vmdl", Size=42)]


def test_vpk_index_converts_core_results_to_python_values(monkeypatch):
    class FakeList(list):
        @classmethod
        def __class_getitem__(cls, item):
            return cls

        def Add(self, value):
            self.append(value)

    import sys
    monkeypatch.setitem(sys.modules, "System", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "System.Collections", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "System.Collections.Generic", SimpleNamespace(List=FakeList))

    native = FakeVpkIndex()
    index = VpkIndex(native)

    index.mount("pak01_dir.vpk")
    index.add_loose_root("content")

    assert index.package_count == 1
    assert index.exists("present.txt")
    assert index.read_bytes("present.txt") == b"data"
    assert index.read_bytes("missing.txt") is None
    assert native.roots == ["content"]
    assert index.entries((".vmdl",)) == (("models/example.vmdl", 42),)


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
