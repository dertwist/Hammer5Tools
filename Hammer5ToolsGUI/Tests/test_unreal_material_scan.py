"""The project material scan runs its Core dumps in parallel; grouping must not
depend on which one finishes first."""

import threading

from gui.forms.unreal_porter.converter import scan_master_materials


class FakeBridge:
    """Answers dump_material out of order and records how many run at once."""

    def __init__(self, materials):
        self.materials = materials
        self.peak_concurrency = 0
        self._live = 0
        self._lock = threading.Lock()
        self._barrier = threading.Barrier(len(materials), timeout=5)

    def is_available(self):
        return True

    def list_materials(self):
        return [f"{path}.uasset" for path in self.materials] + ["Game/Notes.txt"]

    def dump_material(self, path):
        with self._lock:
            self._live += 1
            self.peak_concurrency = max(self.peak_concurrency, self._live)
        # Every dump waits for the others, so the results can only be in key
        # order if the scan puts them there rather than appending as they land.
        self._barrier.wait()
        with self._lock:
            self._live -= 1
        data = self.materials[path]
        if isinstance(data, Exception):
            raise data
        return data


def test_material_scan_is_parallel_and_keeps_key_order():
    bridge = FakeBridge({
        "Game/MI_A": {"parent": "/Game/M_Master.M_Master", "textures": {"Base": "/Game/T_A"}},
        "Game/MI_B": {"parent": "/Game/M_Master.M_Master", "textures": {}},
        "Game/MI_C": {"parent": "/Game/M_Master.M_Master", "textures": {}},
    })

    groups = scan_master_materials("", None, bridge)

    assert bridge.peak_concurrency > 1, "dumps ran one at a time"
    assert list(groups) == ["M_Master"], groups
    instances = [stem for stem, _path, _data in groups["M_Master"]["instances"]]
    assert instances == ["MI_A", "MI_B", "MI_C"], instances
    assert groups["M_Master"]["count"] == 3
    assert groups["M_Master"]["textures"] == {"Base": "/Game/T_A"}


def test_material_scan_skips_the_assets_core_cannot_read():
    bridge = FakeBridge({
        "Game/MI_A": {"parent": "/Game/M_Master.M_Master", "textures": {}},
        "Game/MI_Broken": RuntimeError("unreadable"),
    })
    warnings = []

    groups = scan_master_materials("", None, bridge, log_cb=lambda msg, level="info": warnings.append((level, msg)))

    assert [stem for stem, _p, _d in groups["M_Master"]["instances"]] == ["MI_A"]
    assert any(level == "warn" and "MI_Broken" in msg for level, msg in warnings), warnings
