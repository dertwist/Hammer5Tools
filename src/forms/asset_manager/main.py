import os
import json
from PySide6.QtWidgets import QWidget, QFileSystemModel, QFileDialog, QMessageBox, QInputDialog
from PySide6.QtCore import Qt, QDir
from .ui_main import Ui_AssetManagerWidget
from .move_worker import MoveWorker
from src.settings.main import get_addon_name, get_cs2_path
from src.common import enable_dark_title_bar, app_dir
from src.styles.common import apply_stylesheets
from src.widgets.explorer.main import Explorer

class AssetManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_AssetManagerWidget()
        self.ui.setupUi(self)
        
        enable_dark_title_bar(self)
        apply_stylesheets(self)
        
        # Explicitly set console dark theme since global stylesheet strips it out
        self.ui.log_output.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #ffffff; border: 1px solid #333333; }")
        
        self.cs2_path = get_cs2_path()
        if not self.cs2_path:
            return

        self.addon_name = get_addon_name()
        self.addon_content_path = os.path.join(self.cs2_path, 'content', 'csgo_addons', self.addon_name)
        
        self.sources_to_move = []

        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("Move Assets")
        self.ui.source_tree.hide()
        self.ui.source_tree.deleteLater()
        self.ui.dest_tree.hide()
        self.ui.dest_tree.deleteLater()

        self.explorer = Explorer(
            tree_directory=self.addon_content_path,
            addon=self.addon_name,
            editor_name="AssetManager",
            use_internal_player=False,
            parent=self
        )
        self.ui.splitter.insertWidget(0, self.explorer.frame)

        self.ui.btn_preview.clicked.connect(self.preview_move)
        self.ui.btn_apply.clicked.connect(self.apply_move)
        self.ui.btn_undo.hide()

        self.pending_moves = []

    def set_files_to_move(self, files):
        self.sources_to_move = files
        self.ui.log_output.clear()
        self.ui.log_output.append(f"Selected {len(files)} items to move.\nPlease select destination folder and click Preview.")

    def get_selected_sources(self):
        return self.sources_to_move

    def get_selected_dest_dir(self):
        indexes = self.explorer.tree.selectionModel().selectedIndexes()
        if indexes:
            for idx in indexes:
                if idx.column() == 0:
                    src_idx = self.explorer.filter_proxy_model.mapToSource(idx)
                    path = self.explorer.model.filePath(src_idx)
                    if os.path.isdir(path):
                        return path
                    return os.path.dirname(path)
        return self.addon_content_path

    def preview_move(self):
        sources = self.get_selected_sources()
        dest_dir = self.get_selected_dest_dir()

        if not sources:
            QMessageBox.warning(self, "Warning", "Select files from source tree.")
            return

        self.ui.log_output.clear()
        self.pending_moves.clear()
        
        for src in sources:
            if os.path.isfile(src):
                basename = os.path.basename(src)
                dst = os.path.join(dest_dir, basename)
                self.pending_moves.append((src, dst))
                rel_src = os.path.relpath(src, self.addon_content_path)
                rel_dst = os.path.relpath(dst, self.addon_content_path)
                self.ui.log_output.append(f"Ready to move:\n {rel_src} \n  -> {rel_dst}\n")

    def apply_move(self):
        if not self.pending_moves:
            QMessageBox.warning(self, "Warning", "No moves pending. Click preview first.")
            return

        self.worker = MoveWorker(self.pending_moves, self.addon_content_path)
        self.worker.log.connect(self.log_message)
        self.worker.finished_move.connect(self.on_move_finished)
        
        self.ui.btn_apply.setEnabled(False)
        self.ui.btn_preview.setEnabled(False)
        self.worker.start()

    def log_message(self, msg):
        self.ui.log_output.append(msg)

    def on_move_finished(self):
        self.ui.btn_apply.setEnabled(True)
        self.ui.btn_preview.setEnabled(True)
        self.pending_moves.clear()
        QMessageBox.information(self, "Success", "Move operation finished.")


