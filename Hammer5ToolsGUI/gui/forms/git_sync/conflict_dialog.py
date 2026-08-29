"""Per-file conflict resolver.

Lists conflicted files; each row offers Keep Local / Keep Server / Open.
Resolving a file runs `git checkout --ours|--theirs -- <f>` + `git add <f>`.
Once every file is resolved, Continue is enabled (the caller finishes the merge).

Git's own words for the two sides are "ours" and "theirs", which read backwards
to anyone who has not internalised what a merge commit is — "theirs" is not a
person, it is the shared branch. The UI says Local (what is on this machine) and
Server (what the team has pushed) and only translates back at the git call.

.vmap rows get a third option, Merge: the map is split into blocks (entities,
meshes, groups) and both sides' edits are combined, so only nodes that both
mappers touched need a winner. See gui/gitvmapmerge.py.
"""
import os
import shutil
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame,
    QScrollArea, QDialogButtonBox, QMessageBox,
)
from gui.forms.git_sync import git_icon, git_message_box
from gui.styles.common import set_style_property

#: What the user reads -> the git checkout flag that means it.
LOCAL, SERVER = "--ours", "--theirs"
_SIDE_LABEL = {LOCAL: "Local", SERVER: "Server"}


class ConflictDialog(QDialog):
    def __init__(self, repo, files, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.setWindowTitle("Resolve conflicts")
        self.setWindowIcon(git_icon())
        self.resize(1000, 420)
        self._rows = {}          # path -> (status label, choice buttons)
        self._unresolved = set(files)

        outer = QVBoxLayout(self)
        header = QLabel(
            "Someone else changed these files while you were working on them.\n"
            "<b>Local</b> is your version, <b>Server</b> is the one already "
            "pushed by the team. Pick one for each file, then Continue. "
            "Maps can be merged instead, keeping both sides' work.")
        header.setWordWrap(True)
        header.setTextFormat(Qt.RichText)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        self.buttons.addButton("Cancel sync", QDialogButtonBox.RejectRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self._update_continue()

    def _add_row(self, path):
        row = QFrame()
        row.setProperty("h5Component", "gitConflictRow")
        line = QHBoxLayout(row)
        line.setContentsMargins(8, 6, 8, 6)
        line.setSpacing(8)
        name = QLabel(path)
        name.setToolTip(path)
        line.addWidget(name, 1)
        status = QLabel("conflict")
        status.setFixedWidth(70)
        status.setAlignment(Qt.AlignCenter)
        status.setProperty("h5Component", "gitConflictStatus")
        status.setProperty("h5State", "conflict")
        line.addWidget(status)

        choices = []
        if path.lower().endswith(".vmap"):
            merge_btn = QPushButton("Merge both")
            merge_btn.setToolTip(
                "Combine both versions block by block instead of throwing one "
                "away. Only objects you both edited need a winner.")
            merge_btn.clicked.connect(lambda: self._merge_vmap(path))
            choices.append(merge_btn)

        local = QPushButton("Keep Local")
        local.setToolTip("Use your version and discard what the server has.")
        server = QPushButton("Keep Server")
        server.setToolTip("Use the team's version and discard your changes to this file.")
        local.clicked.connect(lambda: self._resolve(path, LOCAL))
        server.clicked.connect(lambda: self._resolve(path, SERVER))
        choices += [local, server]

        open_btn = QPushButton("Open")
        open_btn.setToolTip("Open the file so you can see what changed.")
        open_btn.clicked.connect(lambda: self._open(path))
        for b in choices + [open_btn]:
            b.setFixedWidth(88)
            line.addWidget(b)

        self._list.addWidget(row)
        self._rows[path] = (status, tuple(choices))

    def _mark_resolved(self, path, label):
        status, btns = self._rows[path]
        status.setText(label)
        set_style_property(status, "h5State", "resolved")
        for b in btns:
            b.setEnabled(False)
        self._unresolved.discard(path)
        self._update_continue()

    def _resolve(self, path, side):
        code, _, err = self.repo._run("checkout", side, "--", path)
        if code == 0:
            code, _, err = self.repo._run("add", "--", path)
        if code != 0:
            git_message_box(
                self, "Resolve conflict",
                "Git could not keep the %s version of %s:\n\n%s" % (
                    _SIDE_LABEL[side].lower(), path,
                    err.strip() or "Unknown error"))
            return
        self._mark_resolved(path, "kept " + _SIDE_LABEL[side].lower())

    # .vmap block merge
    def _merge_vmap(self, path):
        """Merge both sides of a conflicted map instead of discarding one.

        Git keeps all three versions in the index while a merge is unresolved:
        stage 1 is the common ancestor, 2 local, 3 server. That is exactly the
        input a 3-way block merge wants, so pull them straight from there.
        """
        from gui.gitvmapmerge import OURS, merge

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
                git_message_box(
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
                note += " (%d object%s from %s)" % (
                    len(result.conflicts), "" if len(result.conflicts) == 1 else "s",
                    "Local" if primary == OURS else "Server")
            self._mark_resolved(path, note)
            if result.orphaned:
                git_message_box(
                    self, "Merge map",
                    "%d object(s) were in a group the other side deleted. They "
                    "were kept and moved to the top level of the map."
                    % len(result.orphaned), icon=QMessageBox.Information)
        except Exception as e:
            # Not two versions of one map, an unresolved block, or the DMX codec
            # refusing a side. Anything raised here escapes into Qt otherwise and
            # the button just does nothing.
            git_message_box(self, "Merge map", str(e))
        finally:
            if result is not None:
                result.close()
            shutil.rmtree(tmp, ignore_errors=True)

    def _ask_primary(self, path, result):
        """Which side wins the objects both mappers changed? None = cancel."""
        from gui.gitvmapmerge import OURS, THEIRS

        listing = "\n".join(
            f"{c.kind}  {c.label}  — {c.reason}" for c in result.conflicts[:40])
        if len(result.conflicts) > 40:
            listing += f"\n… +{len(result.conflicts) - 40} more"

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Merge map")
        box.setWindowIcon(git_icon())
        box.setText(f"{len(result.conflicts)} object(s) in "
                    f"{os.path.basename(path)} were changed on both sides.")
        box.setInformativeText(
            "Pick which side wins those objects. Everything else from both "
            "versions is kept either way.")
        box.setDetailedText(listing)
        local_btn = box.addButton("Keep Local for those", QMessageBox.AcceptRole)
        server_btn = box.addButton("Keep Server for those", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is local_btn:
            return OURS
        if clicked is server_btn:
            return THEIRS
        return None

    def _open(self, path):
        full = os.path.join(self.repo.dir, path)
        if os.path.exists(full):
            os.startfile(full)

    def _update_continue(self):
        self.continue_btn.setEnabled(not self._unresolved)
        left = len(self._unresolved)
        self.continue_btn.setToolTip(
            "" if not left else "%d file%s still need%s a decision."
            % (left, "" if left == 1 else "s", "s" if left == 1 else ""))
