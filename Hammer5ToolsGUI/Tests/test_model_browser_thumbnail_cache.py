"""Smoke test for the sqlite-backed model browser thumbnail cache.

Covers the branch ponytail flags as needing a check: staleness compares a
stored write time against the source file's mtime, and VPK-backed entries
skip that comparison entirely.
"""
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")


def _entry(path, fs_path=None, in_vpk=False):
    return SimpleNamespace(path=path, fs_path=fs_path, in_vpk=in_vpk)


def test_thumbnail_roundtrip_and_staleness(monkeypatch, tmp_path):
    import gui.common
    monkeypatch.setattr(gui.common, "SmartPropEditor_Path", tmp_path, raising=False)

    from gui.widgets.model_browser import cache, thumbnails

    source = tmp_path / "model.vmdl_c"
    source.write_bytes(b"source")
    import os
    os.utime(source, (1_700_000_000, 1_700_000_000))

    entry = _entry("models/foo.vmdl_c", fs_path=str(source))

    assert thumbnails._cached_thumbnail_bytes(entry, 128) is None

    thumbnails._store_thumbnail_bytes(entry.path, 128, b"fake-png-bytes")
    assert thumbnails._cached_thumbnail_bytes(entry, 128) == b"fake-png-bytes"
    assert os.path.isfile(cache.thumbnail_db_path())

    # Source changed after the thumbnail was baked -> cache entry is stale.
    os.utime(source, (2_100_000_000, 2_100_000_000))
    assert thumbnails._cached_thumbnail_bytes(entry, 128) is None

    # VPK-backed entries have no reliable source mtime, so staleness is skipped.
    vpk_entry = _entry("models/foo.vmdl_c", fs_path=None, in_vpk=True)
    assert thumbnails._cached_thumbnail_bytes(vpk_entry, 128) == b"fake-png-bytes"


def test_clear_cache_removes_sqlite_db(monkeypatch, tmp_path):
    import gui.common
    monkeypatch.setattr(gui.common, "SmartPropEditor_Path", tmp_path, raising=False)

    from gui.widgets.model_browser import cache, thumbnails

    thumbnails._store_thumbnail_bytes("models/foo.vmdl_c", 128, b"fake-png-bytes")
    assert cache.thumbnail_db_path() in cache.cache_targets()

    cache.clear_cache()

    import os
    assert not os.path.exists(cache.thumbnail_db_path())
