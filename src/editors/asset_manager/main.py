import os
import json
from PySide6.QtWidgets import QWidget, QFileSystemModel, QFileDialog, QMessageBox, QInputDialog
from PySide6.QtCore import Qt, QDir
from .ui_main import Ui_AssetManagerWidget
from .move_worker import MoveWorker
from src.settings.main import get_addon_name, get_cs2_path, app_dir
from PySide6.QtWidgets import QLineEdit
from src.common import enable_dark_title_bar
from src.styles.common import apply_stylesheets

class AssetManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_AssetManagerWidget()
        self.ui.setupUi(self)
        
        enable_dark_title_bar(self)
        apply_stylesheets(self)
        
        qt_stylesheet_lineedit = """
        QLineEdit {
            font: 580 10pt "Segoe UI";
            border: 2px solid black;
            border-radius: 2px;
            border-color: rgba(80, 80, 80, 255);
            height:22px;
            padding-top: 2px;
            padding-bottom:2px;
            padding-left: 4px;
            padding-right: 4px;
            color: #E3E3E3;
            background-color: #1C1C1C;
        }
        QLineEdit:hover {
            background-color: #414956;
            color: white;
        }
        """
        for line_edit in self.findChildren(QLineEdit):
            line_edit.setStyleSheet(qt_stylesheet_lineedit)

        self.cs2_path = get_cs2_path()
        if not self.cs2_path:
            return

        self.addon_name = get_addon_name()
        self.addon_content_path = os.path.join(self.cs2_path, 'content', 'csgo_addons', self.addon_name)

        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("Asset Manager")
        self.ui.source_tree.hide()
        self.sources_to_move = []

        self.source_model = QFileSystemModel()
        self.source_model.setRootPath(self.addon_content_path)
        self.source_model.setNameFilters(['*.vmdl', '*.vsmart', '*.vmat', '*.vpcf', '*.vsndevts', '*.vsnd', '*.vtex'])
        self.source_model.setNameFilterDisables(False)

        self.ui.source_tree.setModel(self.source_model)
        self.ui.source_tree.setRootIndex(self.source_model.index(self.addon_content_path))
        self.ui.source_tree.setColumnWidth(0, 250)
        self.ui.source_tree.setSelectionMode(self.ui.source_tree.SelectionMode.ExtendedSelection)
        self.ui.source_tree.setDragEnabled(True)

        self.dest_model = QFileSystemModel()
        self.dest_model.setRootPath(self.addon_content_path)
        self.dest_model.setFilter(self.dest_model.filter() | QDir.Dirs | QDir.NoDotAndDotDot)

        self.ui.dest_tree.setModel(self.dest_model)
        self.ui.dest_tree.setRootIndex(self.dest_model.index(self.addon_content_path))
        self.ui.dest_tree.setColumnWidth(0, 250)
        self.ui.dest_tree.setAcceptDrops(True)

        self.ui.btn_preview.clicked.connect(self.preview_move)
        self.ui.btn_apply.clicked.connect(self.apply_move)
        self.ui.btn_undo.clicked.connect(self.undo_last_move)

        self.pending_moves = []
        self.log_file_path = os.path.join(app_dir, 'move_log.json')

    def set_files_to_move(self, files):
        self.sources_to_move = files
        self.ui.log_output.clear()
        self.ui.log_output.append(f"Selected {len(files)} items to move.\nPlease select destination folder and click Preview.")

    def get_selected_sources(self):
        return self.sources_to_move

    def get_selected_dest_dir(self):
        indexes = self.ui.dest_tree.selectionModel().selectedIndexes()
        if indexes:
            for idx in indexes:
                if idx.column() == 0:
                    path = self.dest_model.filePath(idx)
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

    def apply_move(self, is_undo=False):
        if not self.pending_moves:
            QMessageBox.warning(self, "Warning", "No moves pending. Click preview first.")
            return

        # Save inverse moves for undo
        if not is_undo:
            inverse_moves = [(dst, src) for src, dst in self.pending_moves]
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(inverse_moves, f)

        self.worker = MoveWorker(self.pending_moves, self.addon_content_path)
        self.worker.log.connect(self.log_message)
        self.worker.finished_move.connect(self.on_move_finished)
        
        self.ui.btn_apply.setEnabled(False)
        self.ui.btn_preview.setEnabled(False)
        self.ui.btn_undo.setEnabled(False)
        self.worker.start()

    def log_message(self, msg):
        self.ui.log_output.append(msg)

    def on_move_finished(self):
        self.ui.btn_apply.setEnabled(True)
        self.ui.btn_preview.setEnabled(True)
        self.ui.btn_undo.setEnabled(True)
        self.pending_moves.clear()
        QMessageBox.information(self, "Success", "Move operation finished.")

    def undo_last_move(self):
        if not os.path.exists(self.log_file_path):
            QMessageBox.warning(self, "Warning", "No undo history found.")
            return
            
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            inverse_moves = json.load(f)

        if not inverse_moves:
            QMessageBox.warning(self, "Warning", "Undo history is empty.")
            return

        self.pending_moves = inverse_moves
        self.ui.log_output.clear()
        self.ui.log_output.append("--- UNDOING PREVIOUS MOVES ---")
        self.apply_move(is_undo=True)
        os.remove(self.log_file_path)
