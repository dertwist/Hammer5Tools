import os
import shutil
from PySide6.QtCore import QThread, Signal
from .reference_updater import ReferenceUpdater

class MoveWorker(QThread):
    log = Signal(str)
    finished_move = Signal()

    def __init__(self, moves, addon_content_path):
        super().__init__()
        self.moves = moves
        self.addon_content_path = addon_content_path

    def run(self):
        updater = ReferenceUpdater(self.addon_content_path)
        for src, dst in self.moves:
            old_rel = os.path.relpath(src, self.addon_content_path).replace('\\', '/')
            new_rel = os.path.relpath(dst, self.addon_content_path).replace('\\', '/')
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
                self.log.emit(f'Moved: {old_rel} → {new_rel}')
                for m in updater.update_references(old_rel, new_rel):
                    self.log.emit(f'  Updated ref in: {m}')
            except Exception as e:
                self.log.emit(f"Error moving {old_rel}: {e}")
        self.finished_move.emit()
