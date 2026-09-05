"""Tests for Unreal project live analysis and in-memory lifecycle."""

import os
from pathlib import Path
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication
import pytest

from gui.forms.unreal_porter import analysis
from gui.forms.unreal_porter.asset_selection import expand_references
from gui.forms.unreal_porter.main import (
    AnalyzeWorker,
    ExpandRefsWorker,
    UnrealPorterWidget,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# 1. Truncation check tests


def test_is_truncated_reports_short_asset_lists():
    assert analysis.is_truncated(["a"], {"totalFiles": 2})
    assert not analysis.is_truncated(["a", "b"], {"totalFiles": 2})
    assert not analysis.is_truncated(["a"], {})
    assert not analysis.is_truncated(["a"], {"totalFiles": 2, "ignored": 1})
    assert analysis.is_truncated(["a"], {"totalFiles": 3, "ignored": 1})


# 2. Live analysis function tests


def test_analyze_performs_live_analysis_and_resets_provider(monkeypatch):
    class FakeBridge:
        def __init__(self):
            self.reset_called = False

        def reset(self):
            self.reset_called = True

        def info(self):
            return {"totalFiles": 2, "game": "TestGame"}

        def list_counted(self, _pattern):
            return ["Game/AssetA.uasset", "Game/AssetB.uasset"], 0

    bridge = FakeBridge()

    def fake_scan_materials(content_dir, tmp_dir, b, output_dir=None, log_cb=None, progress_cb=None):
        return {"M_Master": {"count": 1}}

    monkeypatch.setattr("gui.forms.unreal_porter.converter.scan_master_materials", fake_scan_materials)

    assets, info, materials = analysis.analyze(bridge, "/fake/content")
    assert bridge.reset_called, "bridge.reset() must be called to reset Core provider"
    assert assets == ["Game/AssetA.uasset", "Game/AssetB.uasset"]
    assert info.get("game") == "TestGame"
    assert info.get("ignored") == 0
    assert "M_Master" in materials


def test_analyze_warns_on_truncated_output(monkeypatch):
    class FakeBridge:
        def reset(self):
            pass

        def info(self):
            return {"totalFiles": 10}

        def list_counted(self, _pattern):
            return ["Game/AssetA.uasset"], 0

    logs = []
    monkeypatch.setattr("gui.forms.unreal_porter.converter.scan_master_materials", lambda *a, **kw: {})
    assets, info, materials = analysis.analyze(
        FakeBridge(), "/fake/content", log_cb=lambda msg, lvl="info": logs.append((msg, lvl))
    )
    assert any("Bridge listed only 1 of 10 files" in msg and lvl == "warn" for msg, lvl in logs)


# 3. Reference expansion and key membership tests


def test_expand_references_empty_list_cached_is_not_scanned():
    """An asset with an explicitly cached empty reference list ([]) in refs_map

    must be recognized as already scanned and NOT passed to bridge.iter_refs.
    """
    scanned = []

    class CountingBridge:
        def iter_refs(self, key, is_cancelled=None):
            scanned.append(key)
            return []

    keys = ["Game/Meshes/SM_Leaf.uasset", "Game/Meshes/SM_Root.uasset"]
    refs_map = {
        "Game/Meshes/SM_Leaf.uasset": [],
    }

    result = expand_references(
        CountingBridge(),
        keys={"Game/Meshes/SM_Leaf.uasset"},
        all_keys=keys,
        refs_map=refs_map,
    )

    assert result == {"Game/Meshes/SM_Leaf.uasset"}
    assert scanned == [], "An explicitly cached [] must not be queried through iter_refs"


def test_expand_references_records_empty_refs_and_avoids_rescanning():
    scanned = []

    class CountingBridge:
        def iter_refs(self, key, is_cancelled=None):
            scanned.append(key)
            if key == "Game/Meshes/SM_Parent":
                return ["/Game/Meshes/SM_Child.SM_Child"]
            return []

    all_keys = [
        "Game/Meshes/SM_Parent.uasset",
        "Game/Meshes/SM_Child.uasset",
    ]
    new_refs = {}

    result = expand_references(
        CountingBridge(),
        keys={"Game/Meshes/SM_Parent.uasset"},
        all_keys=all_keys,
        new_refs=new_refs,
    )

    assert result == {"Game/Meshes/SM_Parent.uasset", "Game/Meshes/SM_Child.uasset"}
    assert new_refs["Game/Meshes/SM_Parent.uasset"] == ["Game/Meshes/SM_Child.uasset"]
    assert new_refs["Game/Meshes/SM_Child.uasset"] == []
    assert scanned == ["Game/Meshes/SM_Parent", "Game/Meshes/SM_Child"]

    # Now pass new_refs back as refs_map; neither should be rescanned
    scanned.clear()
    expand_references(
        CountingBridge(),
        keys={"Game/Meshes/SM_Child.uasset"},
        all_keys=all_keys,
        refs_map=new_refs,
    )
    assert scanned == [], "SM_Child has [] in refs_map and must not be rescanned"


# 4. Worker tests: in-memory emission and no manifest written to disk


def test_analyze_worker_emits_in_memory_result_without_writing_disk(tmp_path, monkeypatch):
    class FakeBridge:
        def is_available(self):
            return True

        def why_unavailable(self):
            return ""

    monkeypatch.setattr("gui.forms.unreal_porter.bridge_client.UnrealBridge", lambda path: FakeBridge())

    def fake_analyze(bridge, content_dir, log_cb=None, progress_cb=None):
        return (["Game/Mesh.uasset", "Game/Mat.uasset"], {"game": "P", "umaps": 0}, {"M_Wood": {}})

    monkeypatch.setattr("gui.forms.unreal_porter.analysis.analyze", fake_analyze)

    worker = AnalyzeWorker(str(tmp_path))
    emitted = []
    worker.done.connect(lambda res: emitted.append(res))
    worker.run()

    assert len(emitted) == 1
    res = emitted[0]
    assert res == {
        "assets": ["Game/Mat.uasset", "Game/Mesh.uasset"],
        "info": {"game": "P", "umaps": 0},
        "materials": {"M_Wood": {}},
        "refs": {},
    }

    # Verify no manifest files were created anywhere in tmp_path
    assert list(tmp_path.rglob("*.kv3")) == []


def test_expand_refs_worker_runs_without_disk_persistence(tmp_path, monkeypatch):
    class FakeBridge:
        def iter_refs(self, key, is_cancelled=None):
            return []

    monkeypatch.setattr("gui.forms.unreal_porter.bridge_client.UnrealBridge", lambda path: FakeBridge())

    worker = ExpandRefsWorker(
        str(tmp_path),
        chosen=["Game/Mesh.uasset"],
        all_keys=["Game/Mesh.uasset"],
        refs_map={},
    )
    emitted = []
    worker.done.connect(lambda sel, refs: emitted.append((sel, refs)))
    worker.run()

    assert len(emitted) == 1
    sel, refs = emitted[0]
    assert sel == {"Game/Mesh.uasset"}
    assert refs == {"Game/Mesh.uasset": []}
    assert list(tmp_path.rglob("*.kv3")) == []


# 5. UnrealPorterWidget in-memory lifecycle tests


def test_unreal_porter_in_memory_analysis_lifecycle(qapp, tmp_path, monkeypatch):
    """Characterization of dialog analysis lifecycle:

    - Preserves completed analysis in memory.
    - Reusing same project does not re-run analysis.
    - force=True re-runs analysis.
    - Changing project re-runs analysis.
    - Newly resolved references are merged into in-memory refs.
    - No manifest file is read or written.
    """
    # Prevent background thread execution by intercepting _start_worker
    started_workers = []

    def fake_start_worker(self, name, worker):
        started_workers.append((name, worker))
        return True

    monkeypatch.setattr(UnrealPorterWidget, "_start_worker", fake_start_worker)
    monkeypatch.setattr("gui.forms.unreal_porter.main.find_installs", lambda: [])

    # Create dummy uproject files
    uproject1 = tmp_path / "ProjectA" / "ProjectA.uproject"
    uproject1.parent.mkdir(parents=True)
    uproject1.write_text("{}", encoding="utf-8")

    uproject2 = tmp_path / "ProjectB" / "ProjectB.uproject"
    uproject2.parent.mkdir(parents=True)
    uproject2.write_text("{}", encoding="utf-8")

    addon_dir = tmp_path / "addon"
    addon_dir.mkdir(parents=True)

    widget = UnrealPorterWidget()
    monkeypatch.setattr(widget, "output_dir", lambda: str(addon_dir))

    # Point to ProjectA
    monkeypatch.setattr(widget, "uproject_path", lambda: str(uproject1))
    monkeypatch.setattr(widget, "project_dir", lambda: str(uproject1.parent))

    # 1. First ensure_analysis() triggers AnalyzeWorker
    started_workers.clear()
    widget.ensure_analysis(force=False)
    assert len(started_workers) == 1
    assert started_workers[0][0] == "analyze_worker"
    assert isinstance(started_workers[0][1], AnalyzeWorker)

    # Simulate analysis completion with in-memory result
    analysis_data = {
        "assets": ["Content/MeshA.uasset", "Content/MeshB.uasset"],
        "info": {"game": "ProjectA", "umaps": 0},
        "materials": {},
        "refs": {},
    }
    widget._on_analysis_done(analysis_data, str(uproject1))

    assert widget._analyzed_uproject == str(uproject1)
    assert widget._analysis_result == analysis_data
    assert widget._project_assets == ["Content/MeshA.uasset", "Content/MeshB.uasset"]
    assert widget._project_refs == {}

    # 2. Subsequent ensure_analysis(force=False) on same project reuses in-memory result
    started_workers.clear()
    widget.ensure_analysis(force=False)
    assert started_workers == [], "Should not start worker when analysis is already in memory for same project"

    # 3. ensure_analysis(force=True) re-runs analysis
    started_workers.clear()
    widget.ensure_analysis(force=True)
    assert len(started_workers) == 1
    assert started_workers[0][0] == "analyze_worker"

    # Complete analysis again
    widget._on_analysis_done(analysis_data, str(uproject1))

    # 4. Changing project triggers fresh analysis
    started_workers.clear()
    monkeypatch.setattr(widget, "uproject_path", lambda: str(uproject2))
    monkeypatch.setattr(widget, "project_dir", lambda: str(uproject2.parent))

    widget.ensure_analysis(force=False)
    assert len(started_workers) == 1
    assert started_workers[0][0] == "analyze_worker"

    # 5. Reference expansion merges new refs into self._project_refs in memory
    widget._on_analysis_done(
        {
            "assets": ["Content/MeshA.uasset"],
            "info": {"game": "ProjectB"},
            "materials": {},
            "refs": {},
        },
        str(uproject2),
    )
    assert widget._project_refs == {}

    new_refs = {"Content/MeshA.uasset": ["Content/MatA.uasset"]}
    widget._on_refs_expanded({"Content/MeshA.uasset", "Content/MatA.uasset"}, new_refs)
    assert widget._project_refs == {"Content/MeshA.uasset": ["Content/MatA.uasset"]}

    # Expand another asset that has empty refs
    widget._on_refs_expanded(
        {"Content/MeshA.uasset", "Content/MatA.uasset"},
        {"Content/MatA.uasset": []},
    )
    assert widget._project_refs == {
        "Content/MeshA.uasset": ["Content/MatA.uasset"],
        "Content/MatA.uasset": [],
    }

    # 6. Verify no analyze_cache.kv3 file was created anywhere
    assert not (addon_dir / "hammer5tools" / "unrealporter" / "analyze_cache.kv3").exists()
    assert list(tmp_path.rglob("*analyze_cache*")) == []
