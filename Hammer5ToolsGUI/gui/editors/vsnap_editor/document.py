from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.bridge import CoreBridge, SnapshotDocument

DEFAULT_LIGHTNING_START = (0.0, 0.0, 160.0)
DEFAULT_LIGHTNING_END = (120.0, 30.0, 0.0)
DEFAULT_LIGHTNING_POINT_COUNT = 56
DEFAULT_LIGHTNING_ROUGHNESS = 48.0
DEFAULT_LIGHTNING_BRANCH_PROBABILITY = 0.65
DEFAULT_LIGHTNING_RECURSION_DEPTH = 2
DEFAULT_LIGHTNING_RADIUS = 4.5
DEFAULT_LIGHTNING_SEED = 840_388


def generate_default_lightning() -> SnapshotDocument:
    """Builds the editor's initial lightning preset through Core."""
    return CoreBridge.instance().generate_vsnap_lightning(
        DEFAULT_LIGHTNING_START,
        DEFAULT_LIGHTNING_END,
        DEFAULT_LIGHTNING_POINT_COUNT,
        DEFAULT_LIGHTNING_ROUGHNESS,
        DEFAULT_LIGHTNING_BRANCH_PROBABILITY,
        DEFAULT_LIGHTNING_RECURSION_DEPTH,
        DEFAULT_LIGHTNING_RADIUS,
        DEFAULT_LIGHTNING_SEED,
    )


class VSnapDocument(QObject):
    """Thin GUI adapter over the Core-owned snapshot document."""

    changed = Signal()
    path_changed = Signal(str)
    dirty_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = SnapshotDocument(())
        self.path: Path | None = None
        self.dirty = False

    def replace(self, data: SnapshotDocument, *, dirty: bool = True) -> None:
        self.data = data
        self.changed.emit()
        self.set_dirty(dirty)

    def new(self) -> None:
        self.path = None
        self.path_changed.emit("")
        self.replace(generate_default_lightning(), dirty=False)

    def open(self, path: str) -> None:
        source = Path(path)
        self.data = CoreBridge.instance().read_vsnap(source.read_text(encoding="utf-8"))
        self.path = source
        self.path_changed.emit(str(source))
        self.changed.emit()
        self.set_dirty(False)

    def save(self, path: str | None = None) -> None:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("A destination path is required.")
        target.write_text(CoreBridge.instance().serialize_vsnap(self.data), encoding="utf-8", newline="\n")
        self.path = target
        self.path_changed.emit(str(target))
        self.set_dirty(False)

    def set_dirty(self, dirty: bool) -> None:
        if self.dirty == dirty:
            return
        self.dirty = dirty
        self.dirty_changed.emit(dirty)

    def label(self) -> str:
        return self.path.name if self.path else "Untitled.vsnap"
