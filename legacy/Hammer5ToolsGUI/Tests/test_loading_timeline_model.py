from datetime import datetime

from gui.editors.loading_editor.timeline_model import camera_name, scan_timeline


def test_camera_names_preserve_numbered_camera_identity():
    assert camera_name("Site_0000.jpg") == "Site"
    assert camera_name("Site_0001.jpg") == "Site 1"
    assert camera_name("Overview.png") == "Overview"


def test_timeline_scan_groups_and_orders_frames(tmp_path):
    late = tmp_path / "2026-01-02_12-00-00"
    early = tmp_path / "2026-01-01_12-00-00"
    late.mkdir()
    early.mkdir()
    (late / "Site_0000.jpg").write_bytes(b"")
    (early / "Site_0000.png").write_bytes(b"")
    (early / "ignore.txt").write_text("x")

    timelines = scan_timeline(str(tmp_path))

    assert [timeline.name for timeline in timelines] == ["Site"]
    assert [frame.timestamp for frame in timelines[0].frames] == [
        datetime(2026, 1, 1, 12),
        datetime(2026, 1, 2, 12),
    ]
