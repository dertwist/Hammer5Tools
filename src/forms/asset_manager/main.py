import os
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                               QPushButton, QSplitter, QMessageBox)
from PySide6.QtCore import Qt
from .move_worker import MoveWorker
from src.settings.main import get_addon_name, get_cs2_path
from src.common import enable_dark_title_bar
from src.styles.common import apply_stylesheets
from src.widgets.console import ConsoleWidget
from src.widgets.explorer.main import Explorer


class AssetManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("Move Assets")
        self.resize(1100, 620)
        enable_dark_title_bar(self)
        self.setStyleSheet("background-color: #272727;")

        self.sources_to_move = []
        self.pending_moves = []
        self.worker = None

        self.dest_label = QLabel("Destination: pick a folder on the left")
        self.console = ConsoleWidget()
        self.btn_preview = QPushButton("Preview")
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setEnabled(False)
        self.btn_preview.clicked.connect(self.preview_move)
        self.btn_apply.clicked.connect(self.apply_move)

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_preview)
        buttons.addWidget(self.btn_apply)

        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.dest_label)
        right_layout.addWidget(self.console, 1)
        right_layout.addLayout(buttons)

        self.splitter = QSplitter(Qt.Horizontal, self)
        layout = QHBoxLayout(self)
        layout.addWidget(self.splitter)

        self.cs2_path = get_cs2_path()
        self.addon_name = get_addon_name() if self.cs2_path else None
        self.addon_content_path = (
            os.path.join(self.cs2_path, 'content', 'csgo_addons', self.addon_name)
            if self.cs2_path and self.addon_name else None)

        # Kept as a real branch rather than an early return: bailing out of
        # __init__ left the widget half-built, and the first button press then
        # raised AttributeError inside a slot, which terminates the app.
        self.explorer = None
        if self.addon_content_path:
            self.explorer = Explorer(
                tree_directory=self.addon_content_path,
                addon=self.addon_name,
                editor_name="AssetManager",
                use_internal_player=False,
                parent=self
            )
            self.splitter.addWidget(self.explorer.frame)
            self.explorer.tree.selectionModel().selectionChanged.connect(self._update_dest_label)
        else:
            self.console.error("CS2 path or addon is not configured - nothing can be moved.")
            self.btn_preview.setEnabled(False)

        self.splitter.addWidget(right)
        self.splitter.setSizes([520, 580])

        apply_stylesheets(self)

    def _rel(self, path):
        return os.path.relpath(path, self.addon_content_path).replace('\\', '/')

    def set_files_to_move(self, files):
        self.sources_to_move = [os.path.normpath(f) for f in files if os.path.exists(f)]
        if not self.addon_content_path:
            return
        self.console.clear()
        self.console.header(f"Selected {len(self.sources_to_move)} item(s)")
        for f in self.sources_to_move:
            self.console.info(f"    {self._rel(f)}")
        self.console.info("Pick a destination folder on the left, then press Preview.")

    def get_selected_sources(self):
        return self.sources_to_move

    def get_selected_dest_dir(self):
        if not self.explorer:
            return None
        for idx in self.explorer.tree.selectionModel().selectedIndexes():
            if idx.column() == 0:
                src_idx = self.explorer.filter_proxy_model.mapToSource(idx)
                path = self.explorer.model.filePath(src_idx)
                return path if os.path.isdir(path) else os.path.dirname(path)
        return self.addon_content_path

    def _update_dest_label(self):
        dest = self.get_selected_dest_dir()
        self.dest_label.setText(f"Destination: {self._rel(dest)}" if dest else "Destination: -")

    def preview_move(self):
        if not self.sources_to_move:
            QMessageBox.warning(self, "Move Assets", "Nothing is selected to move.")
            return
        dest_dir = self.get_selected_dest_dir()
        if not dest_dir:
            QMessageBox.warning(self, "Move Assets", "Select a destination folder.")
            return

        self.pending_moves = []
        skipped = []
        for src in self.sources_to_move:
            dst = os.path.join(dest_dir, os.path.basename(src))
            if os.path.normcase(src) == os.path.normcase(dst):
                skipped.append((src, "already in the destination"))
            elif os.path.exists(dst):
                skipped.append((src, "a file or folder of that name is already there"))
            elif os.path.isdir(src) and self._is_inside(dest_dir, src):
                # shutil.move would copy the folder into itself, forever.
                skipped.append((src, "the destination is inside this folder"))
            else:
                self.pending_moves.append((src, dst))

        self.console.clear()
        self.console.header("Preview")
        if self.pending_moves:
            self.console.info(f"Would move {len(self.pending_moves)} item(s):")
            for src, dst in self.pending_moves:
                kind = "DIR " if os.path.isdir(src) else "FILE"
                self.console.info(f"    [{kind}] {self._rel(src)}  ->  {self._rel(dst)}")
        for src, why in skipped:
            self.console.warn(f"    [SKIP] {self._rel(src)} ({why})")

        if not self.pending_moves:
            self.btn_apply.setEnabled(False)
            return
        self.console.info("Scanning the addon for references...")
        self._start_worker(dry_run=True)

    def apply_move(self):
        if not self.pending_moves:
            QMessageBox.warning(self, "Move Assets", "Nothing is pending. Press Preview first.")
            return
        self.console.header("Moving")
        self._start_worker(dry_run=False)

    def _start_worker(self, dry_run):
        if self.worker is not None and self.worker.isRunning():
            return
        self.btn_preview.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.worker = MoveWorker(self.pending_moves, self.addon_content_path,
                                 dry_run=dry_run, parent=self)
        self.worker.log.connect(self._log)
        self.worker.finished_move.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self):
        was_dry_run = self.worker.dry_run
        self.btn_preview.setEnabled(True)
        if was_dry_run:
            self.btn_apply.setEnabled(bool(self.pending_moves))
        else:
            self.pending_moves = []
            self.sources_to_move = []
            self.console.success("Done.")

    def _log(self, message, level):
        getattr(self.console, level, self.console.info)(message)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Move Assets",
                                    "A move is still running. Wait for it to finish.")
            event.ignore()
            return
        super().closeEvent(event)

    @staticmethod
    def _is_inside(path, folder):
        path = os.path.normcase(os.path.abspath(path))
        folder = os.path.normcase(os.path.abspath(folder))
        return path == folder or path.startswith(folder + os.sep)
