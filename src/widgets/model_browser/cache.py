"""
On-disk cache locations for the model browser, and the routine that clears them.

Kept free of Qt, numpy and .NET imports so the settings dialog can offer a
"clear cache" action without dragging in the browser UI or the VRF stack.

Two things are cached:

    model_index.json   the flattened asset index (see index.py)
    thumbs/            one PNG per model per tile size (see thumbnails.py)

Both are pure derived data — deleting them costs nothing but the time to rebuild.
Notably *not* included is cache/<addon>/**.glb, the decompiled geometry, which is
shared with the SmartProp viewport and expensive to regenerate.
"""
import os
import shutil
from typing import List, Tuple


def cache_root() -> str:
    from src.common import SmartPropEditor_Path
    return os.path.join(str(SmartPropEditor_Path), "cache")


def index_file() -> str:
    return os.path.join(cache_root(), "model_index.json")


def thumbnail_dir() -> str:
    return os.path.join(cache_root(), "thumbs")


def cache_targets() -> List[str]:
    """Every path clear_cache() would remove, whether or not it exists."""
    return [index_file(), thumbnail_dir()]


def cache_size() -> Tuple[int, int]:
    """Return (bytes, file_count) currently held by the browser's cache."""
    total_bytes = 0
    file_count = 0
    for target in cache_targets():
        if os.path.isfile(target):
            try:
                total_bytes += os.path.getsize(target)
                file_count += 1
            except OSError:
                pass
        elif os.path.isdir(target):
            for dirpath, _dirnames, filenames in os.walk(target):
                for filename in filenames:
                    try:
                        total_bytes += os.path.getsize(os.path.join(dirpath, filename))
                        file_count += 1
                    except OSError:
                        pass
    return total_bytes, file_count


def clear_cache() -> Tuple[int, int, List[str]]:
    """Delete the index and every thumbnail.

    Returns (bytes_freed, files_removed, errors). Size is measured before the
    delete, so a partial failure still reports what was actually there.
    """
    total_bytes, file_count = cache_size()
    errors: List[str] = []

    for target in cache_targets():
        try:
            if os.path.isfile(target):
                os.remove(target)
            elif os.path.isdir(target):
                shutil.rmtree(target)
        except Exception as exc:
            errors.append(f"{os.path.basename(target)}: {exc}")

    if errors:
        # Some of what was counted survived; re-measure so the caller does not
        # report freeing bytes that are still on disk.
        remaining_bytes, remaining_files = cache_size()
        total_bytes = max(0, total_bytes - remaining_bytes)
        file_count = max(0, file_count - remaining_files)

    return total_bytes, file_count, errors


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} GB"
