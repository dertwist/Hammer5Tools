from core.native import NativeCoreError
from gui.forms.unreal_porter.bridge_client import BridgeError, UnrealBridge


def test_bridge_call_forwards_content_directory_and_arguments():
    calls = []

    class FakeCoreBridge:
        def unreal_dump_scene(self, content_dir, map_path):
            calls.append((content_dir, map_path))
            return {"map": map_path}

    bridge = UnrealBridge("/project/Content")
    bridge._bridge = lambda: FakeCoreBridge()

    assert bridge.dump_scene("Maps/Example.umap") == {"map": "Maps/Example.umap"}
    assert calls == [("/project/Content", "Maps/Example.umap")]


def test_bridge_call_translates_native_errors():
    class FailingCoreBridge:
        def unreal_info(self, content_dir):
            raise NativeCoreError("missing runtime")

    bridge = UnrealBridge("/project/Content")
    bridge._bridge = lambda: FailingCoreBridge()

    try:
        bridge.info()
    except BridgeError as error:
        assert str(error) == "missing runtime"
        assert isinstance(error.__cause__, NativeCoreError)
    else:
        raise AssertionError("NativeCoreError was not translated")
