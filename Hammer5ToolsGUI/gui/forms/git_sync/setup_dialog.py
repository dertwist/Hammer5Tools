"""First-run repository setup for an addon that is not under version control.

The sync button paints a warning ring while this is the case; clicking it lands
here. Setup is deliberately local-only and instant — init, config files, LFS
hook, optional remote. The first commit is left to the normal sync flow, which
already has the progress reporting and size guards a multi-gigabyte content tree
needs.
"""
import os

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QVBoxLayout,
)

from gui.forms.git_sync import git_icon, git_message_box
from gui.forms.git_sync.templates import write_defaults

DEFAULT_BRANCH = "main"


def create_repository(repo, branch=DEFAULT_BRANCH, remote="",
                      gitignore=True, gitattributes=True):
    """Turn `repo.dir` into a git repository. Returns (ok, [step notes]).

    `git init` is followed by an explicit symbolic-ref rather than `init -b`:
    the flag needs git 2.28 and the two-step form works everywhere, so there is
    no version to branch on.

    Anything already present is left alone — an addon someone half-configured by
    hand keeps its own .gitignore, and re-running this on an existing repo is a
    no-op rather than a reset.
    """
    notes = []
    if not repo.dir or not os.path.isdir(repo.dir):
        return False, ["Addon folder not found."]

    branch = branch.strip() or DEFAULT_BRANCH
    code, _out, err = repo._run("check-ref-format", "--branch", branch)
    if code != 0:
        return False, ["Invalid branch name: " + (err.strip() or branch)]

    if not repo.is_repo():
        code, _out, err = repo._run("init")
        if code != 0:
            return False, ["git init failed: " + (err.strip() or "unknown error")]
        notes.append("Created repository")
    # Only safe before the first commit; afterwards it would silently rename the
    # branch the user is standing on.
    if not repo.has_commits():
        code, _out, err = repo._run(
            "symbolic-ref", "HEAD", "refs/heads/" + branch)
        if code != 0:
            return False, ["Could not create branch: " + (err.strip() or branch)]
    else:
        branch = repo.current_branch() or branch
    notes.append("Branch: " + branch)

    written = write_defaults(repo.dir, gitignore, gitattributes)
    notes.append("Wrote " + ", ".join(written) if written
                 else "Config files already present")

    # Installs the clean/smudge filters .gitattributes refers to. Without it the
    # LFS patterns are inert and a 300 MB map goes into git history verbatim.
    if gitattributes:
        code, _out, err = repo._run("lfs", "install", "--local")
        notes.append("Git LFS enabled" if code == 0
                     else "Git LFS not available — install it before committing maps")

    remote = remote.strip()
    if remote:
        if repo.has_origin():
            code, _out, err = repo._run("remote", "set-url", "origin", remote)
        else:
            code, _out, err = repo._run("remote", "add", "origin", remote)
        if code != 0:
            return False, notes + [
                "Could not configure the server: " + (err.strip() or remote)]
        notes.append("Remote: " + remote)
    return True, notes


class SetupDialog(QDialog):
    def __init__(self, addon_dir, parent=None):
        super().__init__(parent)
        self.repo_dir = addon_dir
        self.notes = []
        self.setWindowTitle("Set up Git repository")
        self.setWindowIcon(git_icon())
        self.resize(560, 0)

        outer = QVBoxLayout(self)
        intro = QLabel(
            "This addon is not under version control yet. Setting it up lets you "
            "sync your work with the rest of the team.")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        path = QLabel(addon_dir or "No addon selected")
        path.setProperty("h5Component", "gitSetupPath")
        path.setWordWrap(True)
        outer.addWidget(path)

        form = QFormLayout()
        self.branch_edit = QLineEdit(DEFAULT_BRANCH)
        form.addRow("Branch", self.branch_edit)
        self.remote_edit = QLineEdit()
        self.remote_edit.setPlaceholderText(
            "https://github.com/you/your-map.git — leave empty to stay local")
        form.addRow("Server", self.remote_edit)
        outer.addLayout(form)

        self.gitignore_box = QCheckBox(
            "Add a .gitignore for autosaves, backups and build leftovers")
        self.gitignore_box.setChecked(True)
        self.gitattributes_box = QCheckBox(
            "Store maps, models and textures with Git LFS (recommended)")
        self.gitattributes_box.setChecked(True)
        self.gitattributes_box.setToolTip(
            "Binary assets go to LFS instead of git history. Without this every "
            "saved version of a map is kept whole in every clone.")
        outer.addWidget(self.gitignore_box)
        outer.addWidget(self.gitattributes_box)

        hint = QLabel(
            "Nothing is uploaded yet — press Sync afterwards to make the first "
            "commit.")
        hint.setWordWrap(True)
        hint.setProperty("h5Component", "gitHint")
        outer.addWidget(hint)

        buttons = QDialogButtonBox()
        self.create_btn = buttons.addButton(
            "Create repository", QDialogButtonBox.AcceptRole)
        buttons.addButton(QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._create)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.create_btn.setEnabled(bool(addon_dir))

    def _create(self):
        from gui.forms.git_sync.backend import GitRepo

        ok, self.notes = create_repository(
            GitRepo(self.repo_dir),
            self.branch_edit.text(),
            self.remote_edit.text(),
            self.gitignore_box.isChecked(),
            self.gitattributes_box.isChecked(),
        )
        if not ok:
            git_message_box(
                self, "Set up Git repository", "\n".join(self.notes))
            return
        self.accept()
