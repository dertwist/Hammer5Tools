"""
Internal Sound Events Explorer — flat virtual list (optimized)
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import vpk
from PySide6.QtCore import (
    Qt, QAbstractListModel, QModelIndex,
    QSize, QSortFilterProxyModel, QThread, Signal,
)
from PySide6.QtGui import QAction, QCursor, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QLineEdit, QListView,
    QMenu, QStyle, QVBoxLayout, QWidget,
)

from src.common import Kv3ToJson, SoundEventEditor_path
from src.dotnet import DotNetInterop, VPKExtractor
from src.settings.main import get_cs2_path, debug
from src.styles.common import qt_stylesheet_widgetlist2


# ──────────────────────────────────────────────────────────────────────────────
#  Lazy path helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_vpk_path() -> str:
    return os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')

def _get_soundevents_cache_path() -> str:
    return os.path.join(SoundEventEditor_path, 'soundevents_cache')


# ──────────────────────────────────────────────────────────────────────────────
#  Fast event name scanner — HOT PATH
# ──────────────────────────────────────────────────────────────────────────────

def scan_event_names(path: str) -> List[str]:
    names: List[str] = []
    depth = 0
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith('<!--') or stripped.startswith('//'):
                    continue
                if depth == 1 and '=' in stripped:
                    key = stripped.split('=', 1)[0].strip().strip('"')
                    if key and not key.startswith('_') and not key.startswith('//'):
                        names.append(key)
                depth += stripped.count('{') - stripped.count('}')
                depth += stripped.count('[') - stripped.count(']')
    except OSError:
        pass
    return names


# ──────────────────────────────────────────────────────────────────────────────
#  extract_vsndevts_file
# ──────────────────────────────────────────────────────────────────────────────

def extract_vsndevts_file(
    inner_path: str,
    export: bool = False,
    output_folder: Optional[str] = None,
) -> Optional[str]:
    debug(f"[vsndevts] Extracting {inner_path}")
    if not hasattr(extract_vsndevts_file, "_interop"):
        extract_vsndevts_file._interop = DotNetInterop()
    interop = extract_vsndevts_file._interop
    interop._init_pythonnet()

    import System
    from System.IO import MemoryStream

    if not hasattr(extract_vsndevts_file, "_extractor"):
        extract_vsndevts_file._extractor = VPKExtractor(interop)
        extract_vsndevts_file._extractor._ensure_vrf_loaded()
    extractor = extract_vsndevts_file._extractor

    data = extractor.extract_file(_get_vpk_path(), inner_path)
    if data is None:
        return None
    if not isinstance(data, bytes):
        data = bytes([data[i] for i in range(data.Length)])

    Resource, _, _, FileExtract, _, _ = extractor._vrf_types
    resource = System.Activator.CreateInstance(Resource)
    ms = MemoryStream(data)
    try:
        resource.Read(ms)
        if not hasattr(extract_vsndevts_file, "_extract_method"):
            extract_vsndevts_file._extract_method = next(
                (m for m in FileExtract.GetMethods() if m.Name == "Extract"), None
            )
        extract_method = extract_vsndevts_file._extract_method
        if extract_method is None:
            return None
        params = extract_method.GetParameters()
        args = System.Array.CreateInstance(System.Object, len(params))
        args[0] = resource
        for i in range(1, len(params)):
            args[i] = None
        content_file = extract_method.Invoke(None, args)
        if not content_file or not getattr(content_file, 'Data', None):
            return None
        kv3_text = bytes(
            [content_file.Data[i] for i in range(content_file.Data.Length)]
        ).decode("utf-8", errors="replace")
    finally:
        ms.Dispose()
        if hasattr(resource, 'Dispose'):
            resource.Dispose()

    if not export:
        return kv3_text

    assert output_folder, "output_folder required when export=True"
    os.makedirs(output_folder, exist_ok=True)
    base = os.path.basename(inner_path)
    if base.endswith("_c"):
        base = base[:-2]
    if not base.endswith(".vsndevts"):
        base = os.path.splitext(base)[0] + ".vsndevts"
    out_path = os.path.join(output_folder, base)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(kv3_text)
    return out_path


# ──────────────────────────────────────────────────────────────────────────────
#  Full KV3 parse helpers — COLD PATH
# ──────────────────────────────────────────────────────────────────────────────

def parse_vsndevts_text(content: str, source_name: str) -> Dict[str, Dict[str, Any]]:
    try:
        data = Kv3ToJson(content)
    except Exception:
        try:
            from keyvalues3.textreader import KV3TextReader
            data = KV3TextReader().parse(content).value
        except Exception:
            return {}
    if not isinstance(data, dict):
        return {}
    events: Dict[str, Dict[str, Any]] = {}
    for k, v in data.items():
        if not isinstance(k, str) or k.startswith("_") or k.startswith("//"):
            continue
        v = dict(v) if isinstance(v, dict) else {"value": v}
        v["_source"] = source_name
        events[k] = v
    return events


def parse_vsndevts_file(path: str) -> Dict[str, Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return parse_vsndevts_text(f.read(), os.path.basename(path))
    except Exception:
        return {}


# ──────────────────────────────────────────────────────────────────────────────
#  Background loader thread
# ──────────────────────────────────────────────────────────────────────────────

class SoundEventLoaderThread(QThread):
    events_loaded = Signal(dict)
    progress      = Signal(str)

    def __init__(self, disk_roots: Optional[List[str]] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.disk_roots = disk_roots or []
        self._stopped   = False

    def stop(self) -> None:
        self._stopped = True

    def _scan_vpk_vsndevts(self) -> List[str]:
        seen: set = set()
        paths: List[str] = []
        try:
            with vpk.open(_get_vpk_path()) as pak:
                for fp in pak:
                    if 'vsndevts_c' not in fp:
                        continue
                    key = fp.replace("\\", "/").lower()
                    if key not in seen:
                        seen.add(key)
                        paths.append(fp)
        except Exception as e:
            debug(f'[vsndevts] VPK scan error: {e}')
        return paths

    def _load_from_vpk(self) -> Dict[str, str]:
        name_to_file: Dict[str, str] = {}
        vpaths = self._scan_vpk_vsndevts()
        total  = len(vpaths)
        cache  = _get_soundevents_cache_path()
        os.makedirs(cache, exist_ok=True)

        for idx, inner in enumerate(vpaths, 1):
            if self._stopped:
                break
            base = os.path.basename(inner)
            if base.endswith("_c"):
                base = base[:-2]
            if not base.endswith(".vsndevts"):
                base = os.path.splitext(base)[0] + ".vsndevts"
            cached = os.path.join(cache, base)

            if not os.path.isfile(cached):
                self.progress.emit(f"Decompiling {base} ({idx}/{total})")
                try:
                    cached = extract_vsndevts_file(inner, export=True, output_folder=cache)
                    if not cached:
                        continue
                except Exception as e:
                    debug(f"[vsndevts] Decompile failed {inner}: {e}")
                    continue
            else:
                self.progress.emit(f"Loading {base} ({idx}/{total})")

            for name in scan_event_names(cached):
                name_to_file[name] = cached

        return name_to_file

    def _load_from_disk(self) -> Dict[str, str]:
        name_to_file: Dict[str, str] = {}
        for root in self.disk_roots:
            if self._stopped or not os.path.isdir(root):
                continue
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    if fn.lower().endswith(".vsndevts"):
                        fpath = os.path.join(dirpath, fn)
                        self.progress.emit(f"Override: {fn}")
                        for name in scan_event_names(fpath):
                            name_to_file[name] = fpath
        return name_to_file

    def run(self) -> None:
        try:
            merged = {**self._load_from_vpk(), **self._load_from_disk()}
            self.events_loaded.emit(merged)
            self.progress.emit(f"Loaded {len(merged)} sound events")
        except Exception as e:
            debug(f"[vsndevts] Loader error: {e}")
            self.events_loaded.emit({})


# ──────────────────────────────────────────────────────────────────────────────
#  List model
#  DecorationRole returns Qt's built-in SP_MediaPlay icon — no custom resources.
# ──────────────────────────────────────────────────────────────────────────────

class _EventListModel(QAbstractListModel):
    _play_icon: Optional[QIcon] = None  # resolved once, shared by all rows

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._names: List[str] = []
        if _EventListModel._play_icon is None:
            _EventListModel._play_icon = QIcon(":/icons/assettypes/generic_sm.png")

    def set_names(self, names: List[str]) -> None:
        self.beginResetModel()
        self._names = names
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._names)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._names):
            return None
        if role == Qt.DisplayRole:
            return self._names[index.row()]
        if role == Qt.DecorationRole:
            return self._play_icon
        if role == Qt.SizeHintRole:
            return QSize(0, 22)
        return None



# ──────────────────────────────────────────────────────────────────────────────
#  Main explorer widget
# ──────────────────────────────────────────────────────────────────────────────

class InternalSoundEventExplorer(QWidget):
    """
    Self-contained panel: filter bar on top, virtual flat list below.

    UX:
      • Type in bar   → instant filter
      • Single click  → play
      • Double click  → preview
      • Context menu  → Play | Preview | Copy Name(s) | Copy to Addon
    """

    play_soundevent         = Signal(str)
    preview_soundevent      = Signal(str)
    copy_to_addon_requested = Signal(str, dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter…")
        self._search.setClearButtonEnabled(True)

        self._view = QListView()
        self._view.setStyleSheet(qt_stylesheet_widgetlist2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._search)
        layout.addWidget(self._view)

        self._source_model = _EventListModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._source_model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(0)
        self._view.setModel(self._proxy)

        self._view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._view.setUniformItemSizes(True)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._search.textChanged.connect(self._proxy.setFilterFixedString)
        self._view.clicked.connect(self._on_clicked)
        self._view.doubleClicked.connect(self._on_double_clicked)
        self._view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._open_context_menu)

        self._name_to_file:  Dict[str, str]                        = {}
        self._parsed_files:  Dict[str, Dict[str, Dict[str, Any]]]  = {}
        self.loader: Optional[SoundEventLoaderThread]               = None

        self.reload()

    # ── Public API ────────────────────────────────────────────────────────

    def reload(self) -> None:
        self._source_model.set_names([])
        self._name_to_file.clear()
        self._parsed_files.clear()
        if self.loader and self.loader.isRunning():
            self.loader.stop()
            self.loader.wait(1000)
        disk_roots = [
            p for p in [os.path.join(get_cs2_path(), 'game', 'csgo', 'soundevents')]
            if os.path.isdir(p)
        ]
        self.loader = SoundEventLoaderThread(disk_roots, self)
        self.loader.events_loaded.connect(self._on_events_loaded)
        self.loader.start()

    def filter_tree(self, text: str) -> None:
        self._search.setText(text)

    def get_event_data(self, name: str) -> Dict[str, Any]:
        fp = self._name_to_file.get(name)
        if not fp:
            return {}
        if fp not in self._parsed_files:
            debug(f"[vsndevts] Lazy-parsing {os.path.basename(fp)} for '{name}'")
            self._parsed_files[fp] = parse_vsndevts_file(fp)
        data = dict(self._parsed_files[fp].get(name, {}))
        data.pop("_source", None)
        return data

    def clear_cache(self) -> None:
        cache = _get_soundevents_cache_path()
        if not os.path.isdir(cache):
            return
        for dp, _, files in os.walk(cache):
            for fn in files:
                try:
                    os.remove(os.path.join(dp, fn))
                except Exception:
                    pass

    # ── Internals ─────────────────────────────────────────────────────────

    def _on_events_loaded(self, name_to_file: Dict[str, str]) -> None:
        self._name_to_file = name_to_file
        self._source_model.set_names(sorted(name_to_file, key=str.lower))
        debug(f"[vsndevts] List populated with {len(name_to_file)} events")

    def _selected_names(self) -> List[str]:
        return [i.data(Qt.DisplayRole) for i in self._view.selectedIndexes()
                if i.data(Qt.DisplayRole)]

    def _on_clicked(self, index: QModelIndex) -> None:
        if name := index.data(Qt.DisplayRole):
            self.play_soundevent.emit(name)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        if name := index.data(Qt.DisplayRole):
            self.preview_soundevent.emit(name)

    def _open_context_menu(self, _pos) -> None:
        names = self._selected_names()
        if not names:
            return
        count = len(names)
        s     = "s" if count > 1 else ""
        menu  = QMenu(self)

        if count == 1:
            n = names[0]
            menu.addAction(QAction(f"Play", self,
                triggered=lambda: self.play_soundevent.emit(n)))
            menu.addAction(QAction("Preview", self,
                triggered=lambda: self.preview_soundevent.emit(n)))
            menu.addSeparator()

        menu.addAction(QAction(f"Copy Name{s}  ({count})", self,
            triggered=lambda: self._copy_names(names)))
        menu.addAction(QAction(f"Copy to Addon  ({count})", self,
            triggered=lambda: self._emit_copy_addon(names)))

        menu.exec(QCursor.pos())

    def _copy_names(self, names: List[str]) -> None:
        QGuiApplication.clipboard().setText("\n".join(names))

    def _emit_copy_addon(self, names: List[str]) -> None:
        for name in names:
            self.copy_to_addon_requested.emit(name, self.get_event_data(name))
