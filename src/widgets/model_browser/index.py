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

Each mount contributes from three places — content/<mount> (source .vmdl),
game/<mount> (loose compiled .vmdl_c), and game/<mount>'s VPKs. Every entry is
keyed by its *game-relative* resource path ("models/props/foo.vmdl") because
that is what gets written into a .vsmart / .vdata field; the on-disk location
only matters for thumbnail generation and mtime-based cache busting.

Scanning is done off the GUI thread (ScanWorker) and the result is memo-ised to
disk, since the VPKs alone contribute several thousand entries and walking them
takes long enough to stall a dialog open.
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

_INDEX_VERSION = 2
# Rebuild rather than trust the cache once it is a day old. A stale index is
# only ever *missing* new models (paths are validated lazily at pick time), so
# a coarse TTL is enough and avoids stat()ing thousands of files on open.
_INDEX_TTL_SECONDS = 24 * 60 * 60


@dataclass
class ModelEntry:
    """One browsable .vmdl."""
    path: str            # game-relative, forward slashes: "models/props/foo.vmdl"
    name: str            # basename with extension: "foo.vmdl"
    source: str          # SOURCE_ADDON | SOURCE_CORE
    mod: str             # owning addon name, or "csgo" for Core
    fs_path: str = ""    # absolute on-disk path; "" when the model lives in a VPK
    size: int = 0        # bytes; 0 when unknown (VPK entries report compiled size)

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


def _scan_disk_tree(root: str, source: str, mod: str, extension: str) -> List[ModelEntry]:
    """Collect every model under <root>/models matching ``extension``.

    ``extension`` is ".vmdl" for content trees and ".vmdl_c" for game trees; the
    compiled suffix is stripped so both yield the same resource path.
    """
    entries = []
    models_dir = os.path.join(root, "models")
    if not os.path.isdir(models_dir):
        return entries

    for dirpath, _dirnames, filenames in os.walk(models_dir):
        for filename in filenames:
            if not filename.endswith(extension):
                continue
            abs_path = os.path.join(dirpath, filename)
            rel = _rel_resource_path(abs_path, root)
            if rel is None:
                continue
            if rel.endswith("_c"):
                rel = rel[:-2]
            try:
                size = os.path.getsize(abs_path)
            except OSError:
                size = 0
            entries.append(ModelEntry(
                path=rel, name=os.path.basename(rel), source=source, mod=mod,
                fs_path=abs_path, size=size,
            ))
    return entries


def _scan_vpks(game_root: str, source: str, mod: str) -> List[ModelEntry]:
    """Enumerate models/**.vmdl_c inside a mount's VPKs via ValvePak.

    VPK stores *compiled* names (.vmdl_c); the browser presents source paths, so
    the trailing "_c" is stripped to match what a .vsmart field expects.
    """
    # Only *_dir.vpk are readable archives; the numbered pak01_0xx.vpk siblings
    # are data blobs the dir index points into.
    vpk_paths = sorted(glob.glob(os.path.join(game_root, "*_dir.vpk")))
    if not vpk_paths:
        return []

    entries: List[ModelEntry] = []
    try:
        from src.dotnet import DotNetInterop

        interop = DotNetInterop()
        # setup_vrf() is what bootstraps pythonnet, so the System import has to
        # follow it — importing first raises "No module named 'System'".
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

            # Entries are bucketed by extension; "vmdl_c" is the only one we want.
            try:
                bucket = package.Entries["vmdl_c"]
            except Exception:
                continue
            if bucket is None:
                continue

            for entry in bucket:
                directory = str(entry.DirectoryName or "").replace("\\", "/")
                filename = f"{entry.FileName}.vmdl"
                rel = f"{directory}/{filename}" if directory else filename
                if not rel.startswith("models/"):
                    continue
                try:
                    size = int(entry.TotalLength)
                except Exception:
                    size = 0
                entries.append(ModelEntry(
                    path=rel, name=filename, source=source, mod=mod,
                    fs_path="", size=size,
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


def _scan_mount(cs2_path: str, mount: str, source: str) -> List[ModelEntry]:
    """Collect one content mount from all three places it can hold models.

    Order matters: content-side sources first (what the user edits), then loose
    compiled files, then VPKs — the engine resolves the filesystem ahead of the
    pak, and the de-dupe in scan_all() keeps whichever it sees first.
    """
    entries: List[ModelEntry] = []
    entries += _scan_disk_tree(
        os.path.join(cs2_path, "content", mount), source, mount, ".vmdl")
    game_root = os.path.join(cs2_path, "game", mount)
    entries += _scan_disk_tree(game_root, source, mount, ".vmdl_c")
    entries += _scan_vpks(game_root, source, mount)
    return entries


def active_mounts(active_addon: Optional[str] = None) -> List[str]:
    """The mounts on the active addon's search path, highest precedence first."""
    mounts = []
    if active_addon:
        mounts.append(f"csgo_addons/{active_addon}")
    mounts.extend(GAME_MOUNTS)
    return mounts


def scan_all(active_addon: Optional[str] = None) -> List[ModelEntry]:
    """Build the full index. Blocking — call from ScanWorker, not the GUI thread."""
    from src.common import get_cs2_path
    from src.settings.common import get_addon_name

    cs2_path = get_cs2_path()
    if not cs2_path:
        return []

    active_addon = active_addon or get_addon_name()

    # Insertion order encodes precedence: the first entry to claim a resource
    # path wins, so an addon model shadows the Core model it overrides — exactly
    # how the engine resolves it.
    entries: List[ModelEntry] = []
    for mount in active_mounts(active_addon):
        source = SOURCE_ADDON if mount.startswith("csgo_addons/") else SOURCE_CORE
        entries += _scan_mount(cs2_path, mount, source)

    seen = set()
    unique = []
    for entry in entries:
        key = entry.path.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)

    unique.sort(key=lambda e: e.path.lower())
    return unique


def load_cached_index(active_addon: Optional[str]) -> Optional[List[ModelEntry]]:
    """Return a still-valid cached index, or None to force a rescan."""
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
    if blob.get("addon") != (active_addon or ""):
        return None
    if time.time() - float(blob.get("built_at", 0)) > _INDEX_TTL_SECONDS:
        return None

    try:
        return [ModelEntry(**row) for row in blob.get("entries", [])]
    except (TypeError, ValueError):
        return None


def save_cached_index(active_addon: Optional[str], entries: List[ModelEntry]) -> None:
    cache_file = _index_cache_file()
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as handle:
            json.dump({
                "version": _INDEX_VERSION,
                "addon": active_addon or "",
                "built_at": time.time(),
                "entries": [asdict(e) for e in entries],
            }, handle)
    except Exception as exc:
        print(f"[model_browser] could not write index cache: {exc}")


class ScanSignals(QObject):
    finished = Signal(list)   # list[ModelEntry]


class ScanWorker(QRunnable):
    """Builds the index off the GUI thread.

    ``signals`` is supplied by the caller rather than created here so its
    lifetime follows the dialog, not the runnable: QThreadPool deletes the
    runnable as soon as run() returns, and a scan that outlives the dialog it
    was started for would otherwise emit into a freed QObject.
    """

    def __init__(self, active_addon: Optional[str], signals: ScanSignals,
                 use_cache: bool = True):
        super().__init__()
        self.active_addon = active_addon
        self.signals = signals
        self.use_cache = use_cache

    def _emit(self, entries: List[ModelEntry]):
        try:
            self.signals.finished.emit(entries)
        except RuntimeError:
            # Dialog closed mid-scan; the index cache still got written, so the
            # work is not wasted.
            pass

    @Slot()
    def run(self):
        entries: List[ModelEntry] = []
        try:
            if self.use_cache:
                cached = load_cached_index(self.active_addon)
                if cached is not None:
                    self._emit(cached)
                    return
            entries = scan_all(self.active_addon)
            save_cached_index(self.active_addon, entries)
        except Exception as exc:
            print(f"[model_browser] scan failed: {exc}")
        self._emit(entries)


def source_counts(entries: List[ModelEntry]) -> Dict[str, int]:
    counts = {SOURCE_ADDON: 0, SOURCE_CORE: 0}
    for entry in entries:
        counts[entry.source] = counts.get(entry.source, 0) + 1
    return counts
