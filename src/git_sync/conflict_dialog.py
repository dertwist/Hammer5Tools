"""Simple per-file conflict resolver.

Lists conflicted files; each row offers Keep Mine / Keep Theirs / Open. Resolving
a file runs `git checkout --ours|--theirs -- <f>` + `git add <f>`. Once every file
is resolved, Continue is enabled (the caller runs `git rebase --continue`).
"""
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QScrollArea, QDialogButtonBox,
)


class ConflictDialog(QDialog):
    def __init__(self, repo, files, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.setWindowTitle("Resolve conflicts")
        self.resize(560, 360)
        self._rows = {}          # path -> (row_widget, status_label)
        self._unresolved = set(files)

        outer = QVBoxLayout(self)
        outer.addWidget(QLabel(
            "These files changed on both sides. Pick a version for each, "
            "then Continue."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        self._list = QVBoxLayout(holder)
        self._list.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(holder)
        outer.addWidget(scroll, 1)

        for f in files:
            self._add_row(f)
        self._list.addStretch(1)

        self.buttons = QDialogButtonBox()
        self.continue_btn = self.buttons.addButton(
            "Continue", QDialogButtonBox.AcceptRole)
        self.buttons.addButton("Abort", QDialogButtonBox.RejectRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self._update_continue()

    def _add_row(self, path):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(4, 2, 4, 2)
        name = QLabel(path)
        name.setToolTip(path)
        h.addWidget(name, 1)
        status = QLabel("conflict")
        status.setStyleSheet("color: #E5A00D;")
        h.addWidget(status)

        mine = QPushButton("Keep Mine")
        theirs = QPushButton("Keep Theirs")
        open_btn = QPushButton("Open")
        mine.clicked.connect(lambda: self._resolve(path, "--ours"))
        theirs.clicked.connect(lambda: self._resolve(path, "--theirs"))
        open_btn.clicked.connect(lambda: self._open(path))
        for b in (mine, theirs, open_btn):
            h.addWidget(b)

        self._list.addWidget(row)
        self._rows[path] = (status, (mine, theirs))

    def _resolve(self, path, side):
        # side is "--ours" or "--theirs"
        code, _, _ = self.repo._run("checkout", side, "--", path)
        if code == 0:
            self.repo._run("add", "--", path)
            status, btns = self._rows[path]
            label = "kept mine" if side == "--ours" else "kept theirs"
            status.setText(label)
            status.setStyleSheet("color: #7FB800;")
            for b in btns:
                b.setEnabled(False)
            self._unresolved.discard(path)
            self._update_continue()

    def _open(self, path):
        full = os.path.join(self.repo.dir, path)
        if os.path.exists(full):
            os.startfile(full)

    def _update_continue(self):
        self.continue_btn.setEnabled(not self._unresolved)
