import os
import shutil
from PySide6.QtCore import QThread, Signal

class ExportWorker(QThread):
    progress = Signal(int)
    file_copied = Signal(str)
    finished_export = Signal(str)

    def __init__(self, files, addon_content_path, dest_root, layout, addon_name, asset_stem, export_to_zip=False, zip_name="Export"):
        super().__init__()
        self.files = files
        self.addon_content_path = addon_content_path
        self.dest_root = dest_root
        self.layout = layout
        self.addon_name = addon_name
        self.asset_stem = asset_stem
        self.export_to_zip = export_to_zip
        self.zip_name = zip_name

    def run(self):
        import tempfile
        import zipfile
        SCANNABLE_EXTS = {'.vmdl', '.vsmart', '.vmat', '.vpcf', '.vsndevts', '.vsnd', '.vtex', '.vmap', '.vpost', '.vanim', '.vseq', '.vphys'}
        
        path_mapping = {}
        for src in self.files:
            old_rel = os.path.relpath(src, self.addon_content_path).replace('\\', '/')
            new_rel = self._compute_dest_rel(src)
            path_mapping[old_rel] = new_rel

        if self.export_to_zip:
            temp_dir = tempfile.mkdtemp()
            base_dir = temp_dir
        else:
            base_dir = self.dest_root

        for i, src in enumerate(self.files):
            dest = self._compute_dest(src, base_dir)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                ext = os.path.splitext(src)[1].lower()
                if ext in SCANNABLE_EXTS:
                    with open(src, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for old_rel in sorted(path_mapping.keys(), key=len, reverse=True):
                        new_rel = path_mapping[old_rel]
                        if old_rel != new_rel and old_rel in content:
                            content = content.replace(old_rel, new_rel)

                    with open(dest, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    shutil.copy2(src, dest)
                self.file_copied.emit(src)
            except Exception as e:
                print(f"Error copying {src} to {dest}: {e}")
            self.progress.emit(int((i + 1) / len(self.files) * 100))

        if self.export_to_zip:
            zip_path = os.path.join(self.dest_root, self.zip_name)
            shutil.make_archive(zip_path, 'zip', temp_dir)
            shutil.rmtree(temp_dir)
            
        self.finished_export.emit(self.dest_root)

    def _compute_dest_rel(self, src):
        rel = os.path.relpath(src, self.addon_content_path).replace('\\', '/')
        if self.layout == 'thirdparty':
            parts = rel.split("/", 1)
            if len(parts) == 2:
                root_dir, rest = parts[0], parts[1]
                path_suffix = "thirdparty"
                if self.addon_name:
                    path_suffix = f"{path_suffix}/{self.addon_name}"
                if self.asset_stem:
                    path_suffix = f"{path_suffix}/{self.asset_stem}"
                return f"{root_dir}/{path_suffix}/{rest}"
        return rel

    def _compute_dest(self, src, base_dir):
        rel = self._compute_dest_rel(src)
        return os.path.normpath(os.path.join(base_dir, rel))
