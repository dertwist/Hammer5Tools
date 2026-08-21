"""
Model asset discovery for the model browser.

The index is built per *content mount*, mirroring what Hammer's asset browser
lists under its Mods chip: the addon being edited, then the engine mounts the
game itself layers underneath it.

    csgo_addons/<addon>   the active addon's content tree (.vmdl the user authors)
    csgo                  stock CS2 content
    csgo_imported         assets imported from CS:GO
    csgo_core             shared Source 2 game content
    core                  engine content

Deliberately *not* included: other addons under csgo_addons/. They are not on
the active addon's search path, so a model picked from one would fail to resolve
at compile time.

Addon assets are scanned fresh on every asset browser opening so new or modified
user files are always up to date. Game directories and VPKs are scanned only on
the first opening in the session (or loaded from persistent cache) and cached in
memory for subsequent openings.
"""
import os
import json
import glob
import time
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

# Whether an entry belongs to the addon being edited or to the game underneath.
SOURCE_ADDON = "Addon"
SOURCE_CORE = "Core"

#: Engine content mounts, in search-path precedence order (highest first).
GAME_MOUNTS = ("csgo", "csgo_imported", "csgo_core", "core")

_INDEX_VERSION = 5  # bumped: split session game cache from addon assets
# Rebuild rather than trust the cache once it is a day old. A stale index is
# only ever *missing* new models (paths are validated lazily at pick time), so
# a coarse TTL is enough and avoids stat()ing thousands of files on open.
_INDEX_TTL_SECONDS = 24 * 60 * 60

# Module-level in-memory cache for game directories (CS2 core mounts + VPKs)
# Survives across dialog opens in the session so re-opening skips scanning game
# directories and VPKs entirely.
_game_cache: Optional[List['ModelEntry']] = None
_game_cache_cs2_path: Optional[str] = None
_game_cache_time: float = 0.0

# Module-level in-memory cache for active addon assets
# Survives across dialog opens in the session so re-opening skips walking
# the addon directory tree repeatedly.
_addon_cache: Dict[str, List['ModelEntry']] = {}
_addon_cache_time: Dict[str, float] = {}


def invalidate_game_cache() -> None:
    """Clear the session-level in-memory cache of game directories."""
    global _game_cache, _game_cache_cs2_path, _game_cache_time
    _game_cache = None
    _game_cache_cs2_path = None
    _game_cache_time = 0.0


def invalidate_addon_cache(addon_name: Optional[str] = None) -> None:
    """Clear the session in-memory cache for addon assets."""
    global _addon_cache, _addon_cache_time
    if addon_name:
        for k in list(_addon_cache.keys()):
            if k.endswith(f":{addon_name}"):
                _addon_cache.pop(k, None)
                _addon_cache_time.pop(k, None)
    else:
        _addon_cache.clear()
        _addon_cache_time.clear()


def invalidate_all_caches() -> None:
    """Clear all in-memory caches (game and addon)."""
    invalidate_game_cache()
    invalidate_addon_cache()


def is_index_cached(active_addon: Optional[str] = None, addon_only: bool = False) -> bool:
    """Check if all necessary entries are already in memory cache."""
    global _game_cache, _addon_cache
    from src.settings.main import get_cs2_path, get_addon_name
    cs2_path = get_cs2_path()
    if not cs2_path:
        return False
    active_addon = active_addon or get_addon_name()
    addon_cached = f"{cs2_path}:{active_addon}" in _addon_cache
    if addon_only:
        return addon_cached
    game_cached = _game_cache is not None and _game_cache_cs2_path == cs2_path
    return addon_cached and game_cached


@dataclass
class ModelEntry:
    """One browsable asset entry."""
    path: str            # game-relative, forward slashes: "models/props/foo.vmdl"
    name: str            # basename with extension: "foo.vmdl"
    source: str          # SOURCE_ADDON | SOURCE_CORE
    mod: str             # owning addon name, or "csgo" for Core
    fs_path: str = ""    # absolute on-disk path; "" when the model lives in a VPK
    size: int = 0        # bytes; 0 when unknown (VPK entries report compiled size)
    asset_type: str = "vmdl"  # vmdl, vmat, vsmart, vsndevts, vdata, vpcf, vpost, vmap, vtex

    @property
    def folder(self) -> str:
        return os.path.dirname(self.path)

    @property
    def in_vpk(self) -> bool:
        return not self.fs_path


def _index_cache_file() -> str:
    from src.widgets.model_browser.cache import index_file
    return index_file()


def _rel_resource_path(abs_path: str, content_root: str) -> Optional[str]:
    """Convert an absolute content-tree path to a game-relative resource path."""
    try:
        rel = os.path.relpath(abs_path, content_root)
    except ValueError:
        # Different drive — not under this root at all.
        return None
    if rel.startswith(".."):
        return None
    return rel.replace("\\", "/")


def _get_system_filters(cs2_path: str) -> List[str]:
    """Extract AssetBrowser retail_filters from csgo/gameinfo.gi."""
    filters = []
    if not cs2_path:
        return filters
    gameinfo_path = os.path.join(cs2_path, "game", "csgo", "gameinfo.gi")
    if not os.path.isfile(gameinfo_path):
        return filters
    try:
        with open(gameinfo_path, "r", encoding="utf-8", errors="ignore") as f:
            in_asset_browser = False
            for line in f:
                line_stripped = line.strip()
                if line_stripped == "AssetBrowser":
                    in_asset_browser = True
                elif in_asset_browser:
                    if line_stripped == "{":
                        continue
                    if line_stripped == "}":
                        break
                    if line_stripped.startswith("retail_filter"):
                        parts = line_stripped.split()
                        if len(parts) >= 2:
                            val = parts[1].strip('"').lower()
                            if val:
                                filters.append(val)
    except Exception:
        pass
    return filters


SUPPORTED_EXTENSIONS = (".vmdl", ".vmat", ".vsmart", ".vsndevts", ".vdata", ".vpcf", ".vpost", ".vmap", ".vtex")


def _scan_disk_tree(
    root: str, source: str, mod: str, extensions: Optional[tuple] = None, is_compiled: bool = False,
    system_filters: Optional[List[str]] = None
) -> List[ModelEntry]:
    """Collect assets under <root> matching extensions."""
    entries = []
    if not os.path.isdir(root):
        return entries

    exts = tuple(extensions) if extensions else SUPPORTED_EXTENSIONS

    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            fname_lower = filename.lower()
            matched_ext = None
            if is_compiled:
                for ext in exts:
                    if fname_lower.endswith(ext + "_c"):
                        matched_ext = ext
                        break
            else:
                for ext in exts:
                    if fname_lower.endswith(ext):
                        matched_ext = ext
                        break

            if not matched_ext:
                continue

            abs_path = os.path.join(dirpath, filename)
            rel = _rel_resource_path(abs_path, root)
            if rel is None:
                continue
            if system_filters and any(rel.lower().startswith(f) for f in system_filters):
                continue
            if rel.endswith("_c"):
                rel = rel[:-2]
            clean_type = matched_ext.lstrip('.').lower()
            try:
                size = os.path.getsize(abs_path)
            except OSError:
                size = 0
            entries.append(ModelEntry(
                path=rel, name=os.path.basename(rel), source=source, mod=mod,
                fs_path=abs_path, size=size, asset_type=clean_type,
            ))
    return entries


def _scan_vpks(game_root: str, source: str, mod: str, extensions: Optional[tuple] = None, system_filters: Optional[List[str]] = None) -> List[ModelEntry]:
    """Enumerate assets inside a mount's VPKs via ValvePak."""
    vpk_paths = sorted(glob.glob(os.path.join(game_root, "*_dir.vpk")))
    if not vpk_paths:
        return []

    exts = tuple(extensions) if extensions else SUPPORTED_EXTENSIONS
    bucket_keys = [ext.lstrip('.') + "_c" for ext in exts]

    entries: List[ModelEntry] = []
    try:
        from src.dotnet import DotNetInterop

        interop = DotNetInterop()
        _, _, _, _, _, Package = interop.setup_vrf()
        import System
    except Exception as exc:
        print(f"[model_browser] VRF unavailable, skipping VPK scan: {exc}")
        return []

    for vpk_path in vpk_paths:
        package = None
        try:
            package = System.Activator.CreateInstance(Package)
            package.Read(vpk_path)

            for b_key in bucket_keys:
                try:
                    bucket = package.Entries[b_key]
                except Exception:
                    continue
                if bucket is None:
                    continue

                raw_ext = b_key[:-2]  # strip _c
                for entry in bucket:
                    directory = str(entry.DirectoryName or "").replace("\\", "/")
                    filename = f"{entry.FileName}.{raw_ext}"
                    rel = f"{directory}/{filename}" if directory else filename
                    if system_filters and any(rel.lower().startswith(f) for f in system_filters):
                        continue
                    try:
                        size = int(entry.TotalLength)
                    except Exception:
                        size = 0
                    entries.append(ModelEntry(
                        path=rel, name=filename, source=source, mod=mod,
                        fs_path="", size=size, asset_type=raw_ext,
                    ))
        except Exception as exc:
            print(f"[model_browser] VPK scan failed for {vpk_path}: {exc}")
        finally:
            if package is not None and hasattr(package, "Dispose"):
                try:
                    package.Dispose()
                except Exception:
                    pass
    return entries


def _scan_mount(
    cs2_path: str, mount: str, source: str, extensions: Optional[tuple] = None, scan_vpk: bool = True,
    system_filters: Optional[List[str]] = None
) -> List[ModelEntry]:
    """Collect one content mount from content, game, and VPKs."""
    entries: List[ModelEntry] = []
    entries += _scan_disk_tree(
        os.path.join(cs2_path, "content", mount), source, mount, extensions=extensions, is_compiled=False, system_filters=system_filters
    )
    game_root = os.path.join(cs2_path, "game", mount)
    entries += _scan_disk_tree(
        game_root, source, mount, extensions=extensions, is_compiled=True, system_filters=system_filters
    )
    if scan_vpk:
        entries += _scan_vpks(game_root, source, mount, extensions=extensions, system_filters=system_filters)
    return entries


def scan_addon_mount(
    cs2_path: str,
    addon_name: str,
    extensions: Optional[tuple] = None,
    system_filters: Optional[List[str]] = None,
    use_cache: bool = True
) -> List[ModelEntry]:
    """Scan active addon content and game directories for loose assets (no VPKs)."""
    global _addon_cache, _addon_cache_time

    cache_key = f"{cs2_path}:{addon_name}"
    if use_cache and cache_key in _addon_cache:
        cached_entries = _addon_cache[cache_key]
        if extensions:
            exts_clean = {e.lstrip('.').lower() for e in extensions}
            return [e for e in cached_entries if e.asset_type.lower() in exts_clean]
        return list(cached_entries)

    mount = f"csgo_addons/{addon_name}"
    raw_entries = _scan_mount(
        cs2_path, mount, source=SOURCE_ADDON, extensions=SUPPORTED_EXTENSIONS, scan_vpk=False, system_filters=system_filters
    )
    # Deduplicate: source files from content/ take precedence over compiled game/
    seen = set()
    unique = []
    for entry in raw_entries:
        key = entry.path.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)

    _addon_cache[cache_key] = unique
    _addon_cache_time[cache_key] = time.time()

    if extensions:
        exts_clean = {e.lstrip('.').lower() for e in extensions}
        return [e for e in unique if e.asset_type.lower() in exts_clean]
    return list(unique)


def scan_game_mounts(
    cs2_path: str,
    extensions: Optional[tuple] = None,
    system_filters: Optional[List[str]] = None
) -> List[ModelEntry]:
    """Scan all standard CS2 game mounts (content, game, and VPKs)."""
    exts = tuple(extensions) if extensions else SUPPORTED_EXTENSIONS
    entries: List[ModelEntry] = []
    for mount in GAME_MOUNTS:
        entries += _scan_mount(
            cs2_path, mount, source=SOURCE_CORE, extensions=exts, scan_vpk=True, system_filters=system_filters
        )

    seen = set()
    unique = []
    for entry in entries:
        key = entry.path.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return unique


def active_mounts(active_addon: Optional[str] = None, addon_only: bool = False) -> List[str]:
    """The mounts on the active search path."""
    mounts = []
    if active_addon:
        mounts.append(f"csgo_addons/{active_addon}")
    if not addon_only:
        mounts.extend(GAME_MOUNTS)
    return mounts


def load_cached_game_index(cs2_path: str) -> Optional[List[ModelEntry]]:
    """Return still-valid cached game entries from disk, or None."""
    cache_file = _index_cache_file()
    if not os.path.isfile(cache_file):
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as handle:
            blob = json.load(handle)
    except Exception:
        return None

    if blob.get("version") != _INDEX_VERSION:
        return None
    if blob.get("cs2_path", "").lower() != (cs2_path or "").lower():
        return None
    built_at = float(blob.get("built_at", 0))
    if time.time() - built_at > _INDEX_TTL_SECONDS:
        return None

    try:
        return [ModelEntry(**row) for row in blob.get("entries", [])]
    except (TypeError, ValueError):
        return None


def save_cached_game_index(cs2_path: str, entries: List[ModelEntry]) -> None:
    """Save game directory entries to disk cache."""
    now = time.time()
    cache_file = _index_cache_file()
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as handle:
            json.dump({
                "version": _INDEX_VERSION,
                "cs2_path": cs2_path or "",
                "built_at": now,
                "entries": [asdict(e) for e in entries],
            }, handle)
    except Exception as exc:
        print(f"[model_browser] could not write game index cache: {exc}")


def get_game_entries(
    cs2_path: str,
    use_cache: bool = True,
    system_filters: Optional[List[str]] = None
) -> List[ModelEntry]:
    """Get game directory entries, utilizing in-memory session cache and disk cache."""
    global _game_cache, _game_cache_cs2_path, _game_cache_time

    if use_cache:
        # Fast path 1: Session in-memory cache
        if (
            _game_cache is not None
            and _game_cache_cs2_path == cs2_path
            and (time.time() - _game_cache_time < _INDEX_TTL_SECONDS)
        ):
            return _game_cache

        # Fast path 2: Disk cache
        cached = load_cached_game_index(cs2_path)
        if cached is not None:
            _game_cache = cached
            _game_cache_cs2_path = cs2_path
            _game_cache_time = time.time()
            return _game_cache

    # Slow path: Rescan game mounts from disk + VPKs
    game_entries = scan_game_mounts(cs2_path, extensions=SUPPORTED_EXTENSIONS, system_filters=system_filters)
    save_cached_game_index(cs2_path, game_entries)

    _game_cache = game_entries
    _game_cache_cs2_path = cs2_path
    _game_cache_time = time.time()
    return _game_cache


def scan_all(
    active_addon: Optional[str] = None,
    addon_only: bool = False,
    asset_types: Optional[List[str]] = None,
    use_game_cache: bool = True,
    use_addon_cache: bool = True
) -> List[ModelEntry]:
    """Build or combine the asset index. Blocking — call from ScanWorker, not the GUI thread."""
    from src.settings.main import get_cs2_path, get_addon_name

    cs2_path = get_cs2_path()
    if not cs2_path:
        return []

    system_filters = _get_system_filters(cs2_path)
    active_addon = active_addon or get_addon_name()
    exts = tuple(f".{t.lstrip('.')}" for t in asset_types) if asset_types else SUPPORTED_EXTENSIONS

    addon_entries: List[ModelEntry] = []
    if active_addon:
        addon_entries = scan_addon_mount(
            cs2_path, active_addon, extensions=exts, system_filters=system_filters, use_cache=use_addon_cache
        )

    if addon_only:
        entries = addon_entries
    else:
        game_entries = get_game_entries(cs2_path, use_cache=use_game_cache, system_filters=system_filters)
        if asset_types:
            clean_types = {t.lstrip('.').lower() for t in asset_types}
            game_entries = [e for e in game_entries if e.asset_type.lower() in clean_types]

        seen = set()
        merged = []
        for e in addon_entries:
            key = e.path.lower()
            if key not in seen:
                seen.add(key)
                merged.append(e)
        for e in game_entries:
            key = e.path.lower()
            if key not in seen:
                seen.add(key)
                merged.append(e)
        entries = merged

    entries.sort(key=lambda e: e.path.lower())
    return entries


def load_cached_index(
    active_addon: Optional[str],
    addon_only: bool = False,
    asset_types: Optional[List[str]] = None
) -> Optional[List[ModelEntry]]:
    """Legacy helper: return cached index if available."""
    if addon_only:
        return None
    from src.settings.main import get_cs2_path
    cs2_path = get_cs2_path()
    if not cs2_path:
        return None
    cached = load_cached_game_index(cs2_path)
    if cached is None:
        return None
    if asset_types is not None:
        clean_types = {t.lstrip('.').lower() for t in asset_types}
        return [e for e in cached if e.asset_type.lower() in clean_types]
    return cached


def save_cached_index(active_addon: Optional[str], entries: List[ModelEntry]) -> None:
    """Legacy helper: save entries to cache."""
    from src.settings.main import get_cs2_path
    cs2_path = get_cs2_path()
    if cs2_path:
        save_cached_game_index(cs2_path, entries)


class ScanSignals(QObject):
    finished = Signal(list)   # list[ModelEntry]


class ScanWorker(QRunnable):
    """Builds the index off the GUI thread."""

    def __init__(
        self,
        active_addon: Optional[str],
        signals: ScanSignals,
        use_cache: bool = True,
        addon_only: bool = False,
        asset_types: Optional[List[str]] = None
    ):
        super().__init__()
        self.active_addon = active_addon
        self.signals = signals
        self.use_cache = use_cache
        self.addon_only = addon_only
        self.asset_types = asset_types

    def _emit(self, entries: List[ModelEntry]):
        try:
            self.signals.finished.emit(entries)
        except RuntimeError:
            pass

    @Slot()
    def run(self):
        entries: List[ModelEntry] = []
        try:
            entries = scan_all(
                self.active_addon,
                addon_only=self.addon_only,
                asset_types=self.asset_types,
                use_game_cache=self.use_cache,
                use_addon_cache=self.use_cache
            )
        except Exception as exc:
            print(f"[model_browser] scan failed: {exc}")
        self._emit(entries)


def source_counts(entries: List[ModelEntry]) -> Dict[str, int]:
    counts = {SOURCE_ADDON: 0, SOURCE_CORE: 0}
    for entry in entries:
        counts[entry.source] = counts.get(entry.source, 0) + 1
    return counts
