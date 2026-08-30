from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.bridge import CoreBridge, SnapshotDocument, SnapshotStream

DEFAULT_LIGHTNING_START = (0.0, 0.0, 160.0)
DEFAULT_LIGHTNING_END = (120.0, 30.0, 0.0)
DEFAULT_LIGHTNING_POINT_COUNT = 56
DEFAULT_LIGHTNING_ROUGHNESS = 48.0
DEFAULT_LIGHTNING_BRANCH_PROBABILITY = 0.65
DEFAULT_LIGHTNING_RECURSION_DEPTH = 2
DEFAULT_LIGHTNING_RADIUS = 4.5
DEFAULT_LIGHTNING_SEED = 840_388

# Neutral starting values for streams added by hand; everything else starts at zero.
DEFAULT_STREAM_VALUES = {
    "radius": 8.0,
    "opacity": 1.0,
    "color": 1.0,
    "glow_rgb": 1.0,
    "glow_alpha": 1.0,
    "alpha2": 1.0,
    "lifespan": 1.0,
    "trail_length": 0.1,
    "force_scale": 1.0,
    "normal": 0.0,
}


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

    def add_stream(self, name: str) -> None:
        """Appends an engine-loadable stream filled with the attribute's neutral value."""
        if any(stream.name == name for stream in self.data.streams):
            return
        attribute = next(item for item in CoreBridge.instance().vsnap_attributes() if item.name == name)
        fill = DEFAULT_STREAM_VALUES.get(name, 0.0)
        if attribute.width == 0:
            values = ()
        elif attribute.width == 1:
            values = tuple(float(fill) for _ in range(self.data.count))
        else:
            values = tuple((float(fill),) * 3 for _ in range(self.data.count))
        self.replace(SnapshotDocument(
            self.data.streams + (SnapshotStream(attribute.name, attribute.type, values),),
        ))

    def remove_stream(self, name: str) -> None:
        """Drops a stream. Position is the point cloud itself, so it always stays."""
        if name == "position":
            return
        self.replace(SnapshotDocument(
            tuple(stream for stream in self.data.streams if stream.name != name),
        ))

    def set_value(self, stream_index: int, row: int, component: int | None, value: float) -> None:
        """Writes one authored cell back into the document."""
        streams = list(self.data.streams)
        stream = streams[stream_index]
        values = list(stream.values)
        if component is None:
            values[row] = value
        else:
            vector = list(values[row])
            vector[component] = value
            values[row] = tuple(vector)
        streams[stream_index] = SnapshotStream(stream.name, stream.type, tuple(values))
        self.replace(SnapshotDocument(tuple(streams)))

    def set_dirty(self, dirty: bool) -> None:
        if self.dirty == dirty:
            return
        self.dirty = dirty
        self.dirty_changed.emit(dirty)

    def label(self) -> str:
        return self.path.name if self.path else "Untitled.vsnap"
