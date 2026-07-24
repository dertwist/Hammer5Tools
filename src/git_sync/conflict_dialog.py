"""Simple per-file conflict resolver.

Lists conflicted files; each row offers Keep Mine / Keep Theirs / Open. Resolving
a file runs `git checkout --ours|--theirs -- <f>` + `git add <f>`. Once every file
is resolved, Continue is enabled (the caller runs `git rebase --continue`).

.vmap rows get a third option, Merge: the map is split into blocks (entities,
meshes, groups) and both sides' edits are combined, so only nodes that both
mappers touched need a winner. See src/gitvmapmerge.py.
"""
import os
import shutil
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QScrollArea, QDialogButtonBox, QMessageBox,
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
        header = QLabel(
            "These files changed on both sides. Pick a version for each, "
            "then Continue. Maps can be merged instead of picking a side.")
        header.setWordWrap(True)
        outer.addWidget(header)

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

        choices = []
        if path.lower().endswith(".vmap"):
            merge_btn = QPushButton("Merge")
            merge_btn.setToolTip(
                "Combine both versions block by block instead of throwing one "
                "away. Only nodes you both edited need a winner.")
            merge_btn.clicked.connect(lambda: self._merge_vmap(path))
            choices.append(merge_btn)

        mine = QPushButton("Keep Mine")
        theirs = QPushButton("Keep Theirs")
        mine.clicked.connect(lambda: self._resolve(path, "--ours"))
        theirs.clicked.connect(lambda: self._resolve(path, "--theirs"))
        choices += [mine, theirs]

        open_btn = QPushButton("Open")
        open_btn.clicked.connect(lambda: self._open(path))
        for b in choices + [open_btn]:
            h.addWidget(b)

        self._list.addWidget(row)
        self._rows[path] = (status, tuple(choices))

    def _mark_resolved(self, path, label):
        status, btns = self._rows[path]
        status.setText(label)
        status.setStyleSheet("color: #7FB800;")
        for b in btns:
            b.setEnabled(False)
        self._unresolved.discard(path)
        self._update_continue()

    def _resolve(self, path, side):
        # side is "--ours" or "--theirs"
        code, _, _ = self.repo._run("checkout", side, "--", path)
        if code == 0:
            self.repo._run("add", "--", path)
            self._mark_resolved(
                path, "kept mine" if side == "--ours" else "kept theirs")

    # ---- .vmap block merge ----------------------------------------------
    def _merge_vmap(self, path):
        """Merge both sides of a conflicted map instead of discarding one.

        Git keeps all three versions in the index while a merge is unresolved:
        stage 1 is the common ancestor, 2 ours, 3 theirs. That is exactly the
        input a 3-way block merge wants, so pull them straight from there.
        """
        from src.gitvmapmerge import OURS, merge

        tmp = tempfile.mkdtemp(prefix="vmapmerge_")
        result = None
        try:
            sides = {}
            for stage, name in ((1, "base"), (2, "ours"), (3, "theirs")):
                blob = self.repo.show_stage(stage, path)
                if blob is None:
                    continue
                sides[name] = os.path.join(tmp, name + ".vmap")
                with open(sides[name], "wb") as f:
                    f.write(blob)
            if "ours" not in sides or "theirs" not in sides:
                QMessageBox.warning(
                    self, "Merge map",
                    f"Could not read both versions of {path} out of the index.")
                return

            QGuiApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                result = merge(sides["ours"], sides["theirs"], sides.get("base"))
            finally:
                QGuiApplication.restoreOverrideCursor()

            primary = OURS
            if result.conflicts:
                primary = self._ask_primary(path, result)
                if primary is None:
                    return
                result.resolve_all(primary)

            result.write(os.path.join(self.repo.dir, path))
            self.repo._run("add", "--", path)
            note = "merged"
            if result.conflicts:
                note += " (%d block%s to %s)" % (
                    len(result.conflicts), "" if len(result.conflicts) == 1 else "s",
                    "mine" if primary == OURS else "theirs")
            self._mark_resolved(path, note)
            if result.orphaned:
                QMessageBox.information(
                    self, "Merge map",
                    "%d object(s) were in a group the other side deleted. They "
                    "were kept and moved to the top level of the map."
                    % len(result.orphaned))
        except ValueError as e:
            # Not two versions of one map, or an unresolved block slipped through.
            QMessageBox.warning(self, "Merge map", str(e))
        finally:
            if result is not None:
                result.close()
            shutil.rmtree(tmp, ignore_errors=True)

    def _ask_primary(self, path, result):
        """Which side wins the blocks both mappers changed? None = cancel."""
        from src.gitvmapmerge import OURS, THEIRS

        listing = "\n".join(
            f"{c.kind}  {c.label}  — {c.reason}" for c in result.conflicts[:40])
        if len(result.conflicts) > 40:
            listing += f"\n… +{len(result.conflicts) - 40} more"

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Merge map")
        box.setText(f"{len(result.conflicts)} object(s) in "
                    f"{os.path.basename(path)} were changed on both sides.")
        box.setInformativeText(
            "Pick the primary map — its version of those objects wins. "
            "Everything else from both sides is kept either way.")
        box.setDetailedText(listing)
        mine_btn = box.addButton("Mine is primary", QMessageBox.AcceptRole)
        theirs_btn = box.addButton("Theirs is primary", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is mine_btn:
            return OURS
        if clicked is theirs_btn:
            return THEIRS
        return None

    def _open(self, path):
        full = os.path.join(self.repo.dir, path)
        if os.path.exists(full):
            os.startfile(full)

    def _update_continue(self):
        self.continue_btn.setEnabled(not self._unresolved)
