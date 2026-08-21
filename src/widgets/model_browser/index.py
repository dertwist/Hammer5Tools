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

_INDEX_VERSION = 3  # bumped: pre-fix caches may have missing Core-mount VPK
                     # entries from the setup_vrf() double-load bug (see dotnet.py)
# Rebuild rather than trust the cache once it is a day old. A stale index is
# only ever *missing* new models (paths are validated lazily at pick time), so
# a coarse TTL is enough and avoids stat()ing thousands of files on open.
_INDEX_TTL_SECONDS = 24 * 60 * 60


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


SUPPORTED_EXTENSIONS = (".vmdl", ".vmat", ".vsmart", ".vsndevts", ".vdata", ".vpcf", ".vpost", ".vmap", ".vtex")


def _scan_disk_tree(
    root: str, source: str, mod: str, extensions: Optional[tuple] = None, is_compiled: bool = False
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


def _scan_vpks(game_root: str, source: str, mod: str, extensions: Optional[tuple] = None) -> List[ModelEntry]:
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
    cs2_path: str, mount: str, source: str, extensions: Optional[tuple] = None, scan_vpk: bool = True
) -> List[ModelEntry]:
    """Collect one content mount from content, game, and VPKs."""
    entries: List[ModelEntry] = []
    entries += _scan_disk_tree(
        os.path.join(cs2_path, "content", mount), source, mount, extensions=extensions, is_compiled=False
    )
    game_root = os.path.join(cs2_path, "game", mount)
    entries += _scan_disk_tree(
        game_root, source, mount, extensions=extensions, is_compiled=True
    )
    if scan_vpk:
        entries += _scan_vpks(game_root, source, mount, extensions=extensions)
    return entries


def active_mounts(active_addon: Optional[str] = None, addon_only: bool = False) -> List[str]:
    """The mounts on the active search path."""
    mounts = []
    if active_addon:
        mounts.append(f"csgo_addons/{active_addon}")
    if not addon_only:
        mounts.extend(GAME_MOUNTS)
    return mounts


def scan_all(
    active_addon: Optional[str] = None,
    addon_only: bool = False,
    asset_types: Optional[List[str]] = None
) -> List[ModelEntry]:
    """Build the full index. Blocking — call from ScanWorker, not the GUI thread."""
    from src.settings.main import get_cs2_path, get_addon_name

    cs2_path = get_cs2_path()
    if not cs2_path:
        return []

    active_addon = active_addon or get_addon_name()

    exts = tuple(f".{t.lstrip('.')}" for t in asset_types) if asset_types else SUPPORTED_EXTENSIONS

    entries: List[ModelEntry] = []
    mount_list = active_mounts(active_addon, addon_only=addon_only)
    for mount in mount_list:
        source = SOURCE_ADDON if mount.startswith("csgo_addons/") else SOURCE_CORE
        # Only scan VPKs if we are including game mounts (not addon only)
        entries += _scan_mount(cs2_path, mount, source, extensions=exts, scan_vpk=(not addon_only))

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


def load_cached_index(
    active_addon: Optional[str],
    addon_only: bool = False,
    asset_types: Optional[List[str]] = None
) -> Optional[List[ModelEntry]]:
    """Return a still-valid cached index, or None to force a rescan."""
    if addon_only:
        return None

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
        entries = [ModelEntry(**row) for row in blob.get("entries", [])]
        if asset_types is not None:
            clean_types = {t.lstrip('.').lower() for t in asset_types}
            entries = [e for e in entries if e.asset_type.lower() in clean_types]
        return entries
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
            if self.use_cache and not self.addon_only:
                cached = load_cached_index(self.active_addon, addon_only=self.addon_only, asset_types=self.asset_types)
                if cached is not None:
                    self._emit(cached)
                    return
            entries = scan_all(self.active_addon, addon_only=self.addon_only, asset_types=self.asset_types)
            if not self.addon_only and not self.asset_types:
                save_cached_index(self.active_addon, entries)
        except Exception as exc:
            print(f"[model_browser] scan failed: {exc}")
        self._emit(entries)


def source_counts(entries: List[ModelEntry]) -> Dict[str, int]:
    counts = {SOURCE_ADDON: 0, SOURCE_CORE: 0}
    for entry in entries:
        counts[entry.source] = counts.get(entry.source, 0) + 1
    return counts
