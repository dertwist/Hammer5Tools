import os
import shutil
from PySide6.QtCore import QThread, Signal
from .reference_updater import ReferenceUpdater


class MoveWorker(QThread):
    log = Signal(str, str)  # message, console level
    finished_move = Signal()

    def __init__(self, moves, addon_content_path, dry_run=False, parent=None):
        # Parented so the thread cannot be garbage collected mid-run: a QThread
        # destroyed while running aborts the process.
        super().__init__(parent)
        self.moves = list(moves)
        self.addon_content_path = addon_content_path
        self.dry_run = dry_run

    def _rel(self, path):
        return os.path.relpath(path, self.addon_content_path).replace('\\', '/')

    def _rename_entry(self, src, dst, is_dir):
        old, new = self._rel(src), self._rel(dst)
        # Trailing slash on directories so 'models/foo' cannot match a sibling
        # named 'models/foobar' - the rename is of the folder, not of a prefix.
        return (old + '/', new + '/') if is_dir else (old, new)

    def run(self):
        # run() is the thread body; an exception escaping it takes the process
        # down rather than surfacing anywhere the UI can report it.
        try:
            self._run()
        except Exception as e:
            self.log.emit(f"Error: {e}", "error")
        finally:
            self.finished_move.emit()

    def _run(self):
        updater = ReferenceUpdater(self.addon_content_path)

        if self.dry_run:
            renames = dict(self._rename_entry(src, dst, os.path.isdir(src))
                           for src, dst in self.moves)
            hits = updater.find_referencing(renames)
            if hits:
                self.log.emit(f"Files that would be updated ({len(hits)}):", "warn")
                for path in sorted(hits):
                    self.log.emit(f"    {self._rel(path)}", "info")
            else:
                self.log.emit("No file references the selected assets.", "info")
            return

        renames = {}
        for src, dst in self.moves:
            is_dir = os.path.isdir(src)
            old, new = self._rename_entry(src, dst, is_dir)
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
            except Exception as e:
                self.log.emit(f"Error moving {old}: {e}", "error")
                continue
            self.log.emit(f"Moved {old} -> {new}", "success")
            renames[old] = new

        # One pass for every rename: fixing up per file re-walks the addon and
        # reloads every map once per moved asset, which does not scale past a
        # handful of files.
        if renames:
            self.log.emit(f"Updating references for {len(renames)} moved item(s)...", "info")
            modified = updater.update_references_batch(renames)
            self.log.emit(f"Updated references in {len(modified)} file(s)", "success")
