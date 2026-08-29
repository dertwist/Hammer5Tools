"""Git sync scenarios plus a runnable dialog gallery.

Pytest exercises the dangerous partial-commit case with two real clones. Run
this file directly to open preview versions of repository setup, change
selection, and conflict resolution in the application theme::

    python Hammer5ToolsGUI/Tests/test_git_sync_dialogs.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if __name__ != "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget,
)

repo_root = Path(__file__).resolve().parents[2]
gui_root = repo_root / "Hammer5ToolsGUI"
if str(gui_root) not in sys.path:
    sys.path.insert(0, str(gui_root))

from gui.forms.git_sync.backend import GitRepo
from gui.forms.git_sync.changes_dialog import ChangesDialog
from gui.forms.git_sync.conflict_dialog import ConflictDialog
from gui.forms.git_sync.controller import GitController, SyncButton
from gui.forms.git_sync.setup_dialog import DEFAULT_BRANCH, SetupDialog, create_repository
from gui.forms.git_sync.templates import GITATTRIBUTES, GITIGNORE


app = QApplication.instance() or QApplication(sys.argv)


def _git(directory, *args, check=True):
    process = subprocess.run(
        ["git", *args], cwd=directory, capture_output=True,
        encoding="utf-8", errors="replace")
    if check and process.returncode != 0:
        raise AssertionError(
            "git %s failed:\n%s" % (" ".join(args), process.stderr))
    return process


def _init_repo(path, bare=False):
    path.mkdir(parents=True)
    args = ["init"]
    if bare:
        args.append("--bare")
    _git(path, *args)
    _git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    if not bare:
        _git(path, "config", "user.name", "Git Sync Test")
        _git(path, "config", "user.email", "git-sync@example.invalid")


@pytest.fixture(scope="session")
def qapp():
    return app


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_repository_setup_uses_main_and_default_rules(tmp_path):
    addon = tmp_path / "addon"
    addon.mkdir()

    ok, notes = create_repository(GitRepo(addon))

    assert ok, notes
    assert _git(addon, "branch", "--show-current").stdout.strip() == DEFAULT_BRANCH
    assert (addon / ".gitignore").read_text(encoding="utf-8") == GITIGNORE
    assert (addon / ".gitattributes").read_text(encoding="utf-8") == GITATTRIBUTES
    assert "Created repository" in notes


def test_setup_dialog_defaults_and_no_repo_warning(qapp, tmp_path):
    dialog = SetupDialog(str(tmp_path))
    button = SyncButton()
    button.resize(32, 32)
    button.set_no_repo(True)

    assert dialog.branch_edit.text() == "main"
    assert dialog.gitignore_box.isChecked()
    assert dialog.gitattributes_box.isChecked()
    assert not dialog.windowIcon().isNull()
    assert button._no_repo
    assert "not under version control" in button.toolTip()

    dialog.close()
    button.close()


def test_changes_dialog_can_select_only_maps(qapp):
    dialog = ChangesDialog([
        ("Modified", "maps/firewatch.vmap", 220 * 1024 * 1024),
        ("Modified", "materials/wip.vmat", 512),
        ("New", "models/unfinished.fbx", 8 * 1024 * 1024),
    ], behind=1)

    dialog._select_maps()

    assert dialog.tree.topLevelItemCount() == 3
    assert dialog.tree.topLevelItem(0).text(0) == "maps"
    assert dialog.tree.topLevelItem(0).checkState(0) == Qt.Checked
    assert dialog.tree.topLevelItem(1).checkState(0) == Qt.Unchecked
    assert dialog.selected_paths() == ["maps/firewatch.vmap"]
    assert dialog.left_out_paths() == [
        "materials/wip.vmat", "models/unfinished.fbx"]
    assert "2 unticked changes" in dialog.note_label.text()
    assert "merge it by hand" in dialog.note_label.text()
    assert "firewatch.vmap" in dialog.message()
    assert dialog.windowTitle() == "Sync changes"
    dialog.close()


def test_changes_dialog_folder_checks_cascade_and_become_partial(qapp):
    dialog = ChangesDialog([
        ("Modified", "maps/firewatch.vmap", 100),
        ("New", "maps/prefabs/watchtower.vmap", 200),
        ("Modified", "materials/sign.vmat", 300),
    ])
    maps = dialog.tree.topLevelItem(0)

    maps.setCheckState(0, Qt.Unchecked)
    assert dialog.selected_paths() == ["materials/sign.vmat"]
    assert maps.checkState(0) == Qt.Unchecked

    firewatch = next(
        item for item in dialog._items()
        if item.data(0, Qt.UserRole) == "maps/firewatch.vmap")
    firewatch.setCheckState(0, Qt.Checked)
    assert maps.checkState(0) == Qt.PartiallyChecked
    assert dialog.selected_paths() == [
        "maps/firewatch.vmap", "materials/sign.vmat"]
    dialog.close()


class _FakeRepo:
    def __init__(self, directory):
        self.dir = str(directory)
        self.calls = []

    def _run(self, *args):
        self.calls.append(args)
        return 0, "", ""

    def show_stage(self, _stage, _path):
        return None


def _button(dialog, text):
    return next(
        button for button in dialog.findChildren(QPushButton)
        if button.text() == text)


def test_conflict_dialog_says_local_and_server(qapp, tmp_path):
    repo = _FakeRepo(tmp_path)
    dialog = ConflictDialog(
        repo, ["maps/firewatch.vmap", "materials/sign.vmat"])

    labels = {button.text() for button in dialog.findChildren(QPushButton)}
    assert {"Keep Local", "Keep Server", "Merge both"} <= labels
    assert "Keep Mine" not in labels
    assert "Keep Theirs" not in labels
    assert not dialog.continue_btn.isEnabled()

    _button(dialog, "Keep Local").click()
    assert repo.calls[:2] == [
        ("checkout", "--ours", "--", "maps/firewatch.vmap"),
        ("add", "--", "maps/firewatch.vmap"),
    ]
    assert not dialog.continue_btn.isEnabled()

    # There are two Server buttons; the still-enabled one belongs to sign.vmat.
    next(button for button in dialog.findChildren(QPushButton)
         if button.text() == "Keep Server" and button.isEnabled()).click()
    assert repo.calls[-2:] == [
        ("checkout", "--theirs", "--", "materials/sign.vmat"),
        ("add", "--", "materials/sign.vmat"),
    ]
    assert dialog.continue_btn.isEnabled()
    dialog.close()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_selected_map_sync_preserves_unrelated_wip_during_server_conflict(tmp_path):
    """The motivating scenario: map selected, WIP omitted, server edits map too."""
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"
    teammate = tmp_path / "teammate"
    _init_repo(remote, bare=True)
    _init_repo(local)

    _git(local, "remote", "add", "origin", str(remote))
    (local / "maps").mkdir()
    (local / "notes").mkdir()
    (local / "maps" / "firewatch.vmap").write_text("base map\n", encoding="utf-8")
    (local / "notes" / "wip.txt").write_text("base note\n", encoding="utf-8")
    _git(local, "add", "-A")
    _git(local, "commit", "-m", "Base")
    _git(local, "push", "--set-upstream", "origin", "main")

    _git(tmp_path, "clone", str(remote), str(teammate))
    _git(teammate, "config", "user.name", "Teammate")
    _git(teammate, "config", "user.email", "teammate@example.invalid")
    (teammate / "maps" / "firewatch.vmap").write_text(
        "server map change\n", encoding="utf-8")
    _git(teammate, "add", "maps/firewatch.vmap")
    _git(teammate, "commit", "-m", "Server map change")
    _git(teammate, "push")

    (local / "maps" / "firewatch.vmap").write_text(
        "local map change\n", encoding="utf-8")
    (local / "notes" / "wip.txt").write_text(
        "unfinished local note\n", encoding="utf-8")
    # Pre-stage the WIP to prove an unticked index entry cannot leak into the
    # selected commit.
    _git(local, "add", "notes/wip.txt")

    controller = object.__new__(GitController)
    controller.repo = GitRepo(local)
    controller.main = None
    controller._has_origin = True
    controller._msg = "Update selected map"
    controller._leftover = True
    controller._stashed = False
    controller._stash_msg = "Hammer5Tools test stash"
    controller._pathspec = None
    controller._tail = ""
    controller._branch = "main"
    controller._busy = True
    controller._log = lambda _text: None
    controller._set_busy = lambda _busy: None
    controller.refresh = lambda: None

    def stream(args, done):
        process = _git(local, *args, check=False)
        controller._tail = (process.stderr or process.stdout).strip()
        done(process.returncode)

    def resolve_conflict():
        assert controller.repo.conflicts() == ["maps/firewatch.vmap"]
        _git(local, "checkout", "--ours", "--", "maps/firewatch.vmap")
        _git(local, "add", "--", "maps/firewatch.vmap")
        _git(local, "commit", "--no-edit")
        return True

    controller._stream = stream
    controller._resolve_conflicts = resolve_conflict

    controller._start_add(["maps/firewatch.vmap"], everything=False)

    assert _git(local, "status", "--porcelain").stdout == " M notes/wip.txt\n"
    assert _git(local, "stash", "list").stdout == ""
    selected_commit = _git(
        local, "log", "-1", "--format=%H", "--grep=Update selected map"
    ).stdout.strip()
    committed_paths = _git(
        local, "show", "--format=", "--name-only", selected_commit
    ).stdout.splitlines()
    assert committed_paths == ["maps/firewatch.vmap"]
    assert (local / "notes" / "wip.txt").read_text(
        encoding="utf-8") == "unfinished local note\n"

    verify = tmp_path / "verify"
    _git(tmp_path, "clone", str(remote), str(verify))
    assert (verify / "maps" / "firewatch.vmap").read_text(
        encoding="utf-8") == "local map change\n"
    assert (verify / "notes" / "wip.txt").read_text(
        encoding="utf-8") == "base note\n"


class GitSyncDialogGallery(QWidget):
    """Small manual-test window that opens each Git dialog with realistic data."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Git sync dialog scenarios")
        self.resize(420, 230)
        self._temp = tempfile.TemporaryDirectory(prefix="h5t_git_dialogs_")
        self._dialogs = []

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Open each scenario to review its wording, layout, Git icon, and "
            "button states. These previews do not touch a real addon.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        scenarios = (
            ("Repository setup", self._show_setup),
            ("Choose changes", self._show_changes),
            ("Resolve conflicts", self._show_conflicts),
        )
        for label, callback in scenarios:
            button = QPushButton(label)
            button.clicked.connect(callback)
            layout.addWidget(button)
        layout.addStretch(1)

    def _show(self, dialog):
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        self._dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, item=dialog: self._dialogs.remove(item)
            if item in self._dialogs else None)
        dialog.show()

    def _show_setup(self):
        addon = Path(self._temp.name) / "preview_addon"
        addon.mkdir(exist_ok=True)
        self._show(SetupDialog(str(addon), self))

    def _show_changes(self):
        self._show(ChangesDialog([
            ("Modified", "maps/firewatch.vmap", 318 * 1024 * 1024),
            ("Modified", "materials/signage/wip.vmat", 18 * 1024),
            ("New", "models/props/unfinished.fbx", 42 * 1024 * 1024),
            ("Deleted", "panorama/images/old_preview.png", 0),
        ], behind=2, parent=self))

    def _show_conflicts(self):
        self._show(ConflictDialog(_FakeRepo(self._temp.name), [
            "maps/firewatch.vmap",
            "materials/signage/firewatch_sign.vmat",
            "panorama/images/firewatch_preview.png",
        ], self))


def build_dialog_test_window():
    return GitSyncDialogGallery()


if __name__ == "__main__":
    from gui.styles import manager, theme

    manager.apply(app, theme.get_theme(theme.LEVEL_STANDARD))
    window = build_dialog_test_window()
    window.show()
    sys.exit(app.exec())
