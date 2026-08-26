"""
On-disk cache locations for the model browser, and the routine that clears them.

Kept free of Qt, numpy and .NET imports so the settings dialog can offer a
"clear cache" action without dragging in the browser UI or the VRF stack.

Two things are cached:

    model_index.json               the flattened asset index (see index.py)
    tools_thumbnail_cache.sqlite3  one row per model per tile size (see thumbnails.py)

Both are pure derived data — deleting them costs nothing but the time to rebuild.
Geometry is read directly from compiled assets without glTF/GLB decompilation.

``thumbs/`` is a legacy PNG-per-thumbnail directory from before the sqlite
cache; it is only kept in ``cache_targets()`` so an old install's leftover
files get swept up the next time the cache is cleared.
"""
import os
import shutil
from typing import List, Tuple


def clear_legacy_glb_cache():
    """One-time purge of legacy decompiled .glb files from old cache directories."""
    root = cache_root()
    if not os.path.isdir(root):
        return
    for item in os.listdir(root):
        item_path = os.path.join(root, item)
        if os.path.isdir(item_path) and item != "thumbs":
            # Check for legacy glb files in addon/csgo cache folders
            has_glb = False
            for dirpath, _, filenames in os.walk(item_path):
                if any(fn.endswith(".glb") for fn in filenames):
                    has_glb = True
                    break
            if has_glb:
                try:
                    shutil.rmtree(item_path)
                except Exception:
                    pass



def cache_root() -> str:
    from gui.common import SmartPropEditor_Path
    return os.path.join(str(SmartPropEditor_Path), "cache")


def index_file() -> str:
    return os.path.join(cache_root(), "game_index.json")


def legacy_index_file() -> str:
    return os.path.join(cache_root(), "model_index.json")


def thumbnail_dir() -> str:
    """Legacy PNG-per-thumbnail directory, kept only for cleanup. See module docstring."""
    return os.path.join(cache_root(), "thumbs")


def thumbnail_db_path() -> str:
    return os.path.join(cache_root(), "tools_thumbnail_cache.sqlite3")


def cache_targets() -> List[str]:
    """Every path clear_cache() would remove, whether or not it exists."""
    return [index_file(), legacy_index_file(), thumbnail_db_path(), thumbnail_dir()]


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
    try:
        from gui.widgets.model_browser.index import invalidate_all_caches
        invalidate_all_caches()
    except Exception:
        pass

    try:
        from gui.widgets.model_browser.main import clear_dialog_cache
        clear_dialog_cache()
    except Exception:
        pass

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
