import os
import shutil
from PySide6.QtCore import QThread, Signal

class ExportWorker(QThread):
    progress = Signal(int)
    file_copied = Signal(str)
    finished_export = Signal(str)

    def __init__(self, files, addon_content_path, dest_root, layout, addon_name, asset_stem):
        super().__init__()
        self.files = files
        self.addon_content_path = addon_content_path
        self.dest_root = dest_root
        self.layout = layout
        self.addon_name = addon_name
        self.asset_stem = asset_stem

    def run(self):
        for i, src in enumerate(self.files):
            dest = self._compute_dest(src)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.copy2(src, dest)
                self.file_copied.emit(src)
            except Exception as e:
                print(f"Error copying {src} to {dest}: {e}")
            self.progress.emit(int((i + 1) / len(self.files) * 100))
        self.finished_export.emit(self.dest_root)

    def _compute_dest(self, src):
        rel = os.path.relpath(src, self.addon_content_path)
        if self.layout == 'thirdparty':
            return os.path.join(self.dest_root,
                'folder_thirdparty', self.addon_name,
                self.asset_stem, rel)
        return os.path.join(self.dest_root, rel)
