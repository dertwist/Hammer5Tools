from types import SimpleNamespace

from core.bridge.core import CoreBridge, SmartPropDeformer, SmartPropModel, SmartPropWidget, ValveMapEntity, VpkIndex


def test_core_bridge_is_a_process_singleton():
    original = CoreBridge._instance
    try:
        CoreBridge._instance = None
        assert CoreBridge.instance() is CoreBridge.instance()
    finally:
        CoreBridge._instance = original


class FakeInterop:
    """Placeholder for CoreBridge's accepted compatibility argument."""


class FakeNativeClient:
    ABI_VERSION = 1


class FailingNativeClient:
    @property
    def ABI_VERSION(self):
        raise OSError("missing runtime")


def test_core_probe_translates_success_to_python_status():
    status = CoreBridge(FakeInterop(), native_client=FakeNativeClient()).probe()

    assert status.available
    assert status.version == "native-abi-1"
    assert status.diagnostic is None


def test_core_probe_translates_load_failures_to_diagnostics():
    status = CoreBridge(FakeInterop(), native_client=FailingNativeClient()).probe()

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


def test_smartprop_evaluation_passes_bounded_options():
    captured = {}

    class FakeNative:
        def evaluate(self, document, nested_documents, **options):
            captured["document"] = document
            captured["nested_documents"] = nested_documents
            captured["options"] = options
            return {"models": [], "diagnostics": []}

    bridge = CoreBridge(FakeInterop(), native_client=FakeNative())

    result = bridge.evaluate_smartprop(
        {"m_Children": []},
        nested_documents={"smartprops/nested.vsmart": {"m_Children": []}},
        maximum_depth=7,
    )

    assert result.models == ()
    assert result.widgets == ()
    assert result.diagnostics == ()
    assert captured["document"] == {"m_Children": []}
    assert captured["nested_documents"] == {
        "smartprops/nested.vsmart": {"m_Children": []}
    }
    assert captured["options"]["maximum_depth"] == 7


def test_smartprop_widgets_are_converted_from_native_json():
    native_widget = {
        "type": "locator",
        "elementId": 9,
        "transform": list(range(1, 17)),
        "offset": [1, 2, 3],
        "minimumBounds": [0, 0, 0],
        "maximumBounds": [0, 0, 0],
        "axis": [0, 0, 1],
        "color": [0.6, 0.6, 0.6],
        "handles": [False] * 6,
        "activeAxes": [False] * 3,
        "scale": 2,
        "radius": 16,
        "angle": 0,
        "size": 8,
        "shape": "SQUARE",
        "name": "origin",
    }

    converted = CoreBridge._convert_native_smartprop_widget(native_widget)

    assert converted == SmartPropWidget(
        "locator", 9, tuple(float(value) for value in range(1, 17)),
        (1.0, 2.0, 3.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0), (0.6, 0.6, 0.6),
        (False,) * 6, (False,) * 3, 2.0, 16.0, 0.0, 8.0, "SQUARE", "origin",
    )


def test_smartprop_model_without_deformer_converts_from_native_json():
    native_model = {
        "elementId": 2,
        "modelName": "models/segment.vmdl",
        "transform": list(range(1, 17)),
        "materialGroup": None,
        "tintColor": None,
        "deformer": None,
    }

    converted = CoreBridge._convert_native_smartprop_model(native_model)

    assert converted == SmartPropModel(
        2, "models/segment.vmdl", tuple(float(value) for value in range(1, 17)), None, None, None,
    )


def test_smartprop_model_deformer_converts_from_native_json():
    native_model = {
        "elementId": 2,
        "modelName": "models/pipe.vmdl",
        "transform": list(range(1, 17)),
        "materialGroup": None,
        "tintColor": None,
        "deformer": {
            "size": [100, 20, 20],
            "controlPoints": [[float(i), 0.0, 0.0] for i in range(8)],
            "midpoints": [[float(i), 1.0, 0.0] for i in range(8)],
            "deformerFrame": list(range(1, 17)),
            "volumeFrame": list(range(16, 0, -1)),
        },
    }

    converted = CoreBridge._convert_native_smartprop_model(native_model)

    assert converted.deformer == SmartPropDeformer(
        (100.0, 20.0, 20.0),
        tuple((float(i), 0.0, 0.0) for i in range(8)),
        tuple((float(i), 1.0, 0.0) for i in range(8)),
        tuple(float(value) for value in range(1, 17)),
        tuple(float(value) for value in range(16, 0, -1)),
    )


def test_smartprop_serializer_uses_python_native_document():
    captured = {}

    class FakeNative:
        def serialize(self, value):
            captured["document"] = value
            return "<!-- kv3 -->"

    bridge = CoreBridge(FakeInterop(), native_client=FakeNative())

    text = bridge.serialize_smartprop({"m_Children": []})

    assert text == "<!-- kv3 -->"
    assert captured["document"] == {"m_Children": []}


def test_smartprop_deserializer_returns_python_native_document():
    class FakeNative:
        def deserialize(self, value):
            assert value == "<!-- kv3 -->"
            return {"m_Children": []}

    bridge = CoreBridge(FakeInterop(), native_client=FakeNative())

    document = bridge.deserialize_smartprop("<!-- kv3 -->")

    assert document == {"m_Children": []}


def test_valve_map_entities_are_converted_from_native_json():
    entity = {
        "className": "point_camera",
        "origin": "1 2 3",
        "angles": None,
        "properties": {"classname": "point_camera", "targetname": "camera"},
    }

    converted = CoreBridge._convert_valve_map_entity_json(entity)

    assert converted == ValveMapEntity(
        "point_camera",
        "1 2 3",
        None,
        {"classname": "point_camera", "targetname": "camera"},
    )


def test_valve_map_nodes_are_converted_recursively_from_native_json():
    node = {
        "name": "world",
        "className": "CMapWorld",
        "properties": {},
        "children": [
            {"name": "child", "className": "CMapEntity", "properties": {"classname": "prop_static"}, "children": []},
        ],
    }

    converted = CoreBridge._convert_valve_map_node_json(node)

    assert converted.name == "world"
    assert converted.class_name == "CMapWorld"
    assert len(converted.children) == 1
    assert converted.children[0].class_name == "CMapEntity"
    assert converted.children[0].properties == {"classname": "prop_static"}


class FakeNativeVpk:
    """Stands in for SmartPropNativeClient's vpk_* native ABI calls."""

    def __init__(self):
        self.package_count_value = 0
        self.roots = []
        self.closed_handles = set()

    def vpk_open(self):
        return 1

    def vpk_mount(self, handle, path):
        self.package_count_value += 1

    def vpk_add_loose_root(self, handle, directory):
        self.roots.append(directory)

    def vpk_exists(self, handle, path):
        return path == "present.txt"

    def vpk_read_bytes(self, handle, path):
        return b"data" if path == "present.txt" else None

    def vpk_package_count(self, handle):
        return self.package_count_value

    def vpk_entries(self, handle, suffixes):
        return (("models/example.vmdl", 42),)

    def vpk_close(self, handle):
        self.closed_handles.add(handle)


def test_vpk_index_converts_core_results_to_python_values():
    native = FakeNativeVpk()
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
    native = FakeNativeVpk()
    index = VpkIndex(native)

    index.close()

    assert native.closed_handles == {1}
    try:
        index.exists("present.txt")
    except RuntimeError as error:
        assert str(error) == "VpkIndex is closed"
    else:
        raise AssertionError("Closed VpkIndex accepted a call")
