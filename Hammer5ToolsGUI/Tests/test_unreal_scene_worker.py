from gui.forms.unreal_porter import scene_worker


def test_scene_worker_uses_native_core_bridge_without_legacy_dll_attribute(monkeypatch):
    messages = []

    class FakeBridge:
        def __init__(self, content_dir):
            self.content_dir = content_dir

        def is_available(self):
            return True

        def list(self, _substring):
            return []

    monkeypatch.setattr(scene_worker, "UnrealBridge", FakeBridge)
    worker = scene_worker.SceneModelsWorker(
        project_dir="/project/Content",
        bulk_dir="/bulk",
        output_dir="/output",
        do_scenes=False,
        do_models=False,
    )
    worker.log.connect(lambda message, level: messages.append((message, level)))

    assert worker._run()

    assert ("Bridge       : Hammer5Tools.Core NativeAOT", "info") in messages


def test_scene_worker_marks_unexpected_errors_as_failed(monkeypatch):
    messages = []

    class FailingBridge:
        def __init__(self, _content_dir):
            pass

        def is_available(self):
            return True

        def list(self, _substring):
            raise RuntimeError("boom")

    monkeypatch.setattr(scene_worker, "UnrealBridge", FailingBridge)
    worker = scene_worker.SceneModelsWorker(
        project_dir="/project/Content",
        bulk_dir="/bulk",
        output_dir="/output",
        do_scenes=True,
        do_models=False,
    )
    worker.log.connect(lambda message, level: messages.append((message, level)))

    worker.run()

    assert not worker.succeeded
    assert ("Unexpected error: boom", "error") in messages
