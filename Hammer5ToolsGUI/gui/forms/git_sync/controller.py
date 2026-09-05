"""Sync button + git glue, scoped to the current addon.

Every git call except the one status read on click runs through a QProcess and
returns via a signal. Spawning git costs ~150ms on Windows and `git status` over
an addon's content tree costs more, so anything on a timer or in the sync chain
would otherwise freeze the UI — the badge poll alone used to burn three blocking
spawns every two seconds. The sync flow is an async chain wired on
QProcess.finished.

The button is icon-only (the settings "check updates" sync icon) with two badge
overlays: yellow = uncommitted local changes, red = commits out of step with
origin, whether they need pulling or pushing.
"""
import os
import re
import tempfile
from time import monotonic, monotonic_ns

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QColor, QFont
from PySide6.QtWidgets import QPushButton, QMessageBox
from shiboken6 import isValid

from gui.settings.common import get_addon_dir, get_settings_bool
from gui.forms.git_sync.backend import GitRepo, STATUS_V2_ARGS, parse_status_v2
from gui.forms.git_sync.changes_dialog import ChangesDialog
from gui.forms.git_sync.conflict_dialog import ConflictDialog
from gui.forms.git_sync.setup_dialog import DEFAULT_BRANCH, SetupDialog
from gui.forms.git_sync import git_message_box
from gui.styles import theme

_SYNC_ICON = ":/icons/sync_24dp.svg"

_LFS_LIMIT = 100 * 1024 * 1024    # GitHub rejects blobs over 100 MiB
_LARGE_COMMIT = 500 * 1024 * 1024  # warn about slow uploads over this

# Stamped on the stash that holds the changes the user did not tick, and checked
# again before popping it. See GitRepo.stash_top_message.
_STASH_MSG = "Hammer5Tools: changes left out of a sync"


def _human(nbytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024 or unit == "TB":
            return f"{nbytes:.0f} {unit}" if unit in ("B", "KB") else f"{nbytes:.1f} {unit}"
        nbytes /= 1024


# What the status line says while each step runs, before git reports progress.
_VERBS = {"add": "Staging changes", "commit": "Committing",
          "fetch": "Checking for updates", "pull": "Downloading changes",
          "push": "Uploading changes", "stash": "Setting other changes aside"}

# git's own progress-line names -> what a mapper waiting on the button wants to
# read. LFS transfers are not here: they come from the byte log below instead.
_PHASES = (
    ("Receiving objects", "Downloading"),
    ("Writing objects", "Uploading"),
    ("Compressing objects", "Compressing"),
    ("Counting objects", "Processing"),
    ("Enumerating objects", "Processing"),
    ("Resolving deltas", "Processing"),
    ("Updating files", "Updating files"),
    ("Checking out files", "Updating files"),
)
_PCT = re.compile(r"(\d{1,3})%")

# git-lfs' stderr meter counts *whole objects*, so one 300 MB map reads 0% for
# its entire transfer. Muted in favour of the byte log, which the poll timer
# turns into a percent that actually moves.
_MUTED = ("LFS objects:", "Filtering content:")
_LFS_LABEL = {"upload": "Uploading", "download": "Downloading"}
# git-lfs appends "<dir> <n>/<of> <bytes>/<total> <name>" here, once per chunk;
# pid-scoped so two running copies of H5T do not read each other's transfer.
_LFS_LOG = os.path.join(tempfile.gettempdir(), "h5t_lfs_progress_%d.log" % os.getpid())


class _LfsProgress:
    """Whole-transfer progress, accumulated from git-lfs' per-file byte log.

    Each line reports one file ("upload 1/3 12/300 a.vmap"), so a transfer-wide
    percent means summing them here. Files that have not started have no line at
    all and no known size; they are priced at the average of the files that do,
    which self-corrects as the transfer runs and is exact once all have started.
    Read forward from the last offset — the log gets a line per chunk, so
    re-reading it whole every 200 ms would go quadratic on a big map.
    """

    __slots__ = ("path", "pos", "part", "files", "of", "direction")

    def __init__(self, path=_LFS_LOG):
        self.path = path
        self.pos = 0
        self.part = b""      # trailing half-written line, completed by the next read
        self.files = {}      # name -> (bytes done, bytes total)
        self.of = 0          # objects in the transfer, per git-lfs
        self.direction = ""

    def read(self):
        """Consume whatever git-lfs appended. True if any byte counter moved."""
        try:
            with open(self.path, "rb") as f:
                f.seek(self.pos)
                new = f.read()
        except OSError:
            return False
        if not new:
            return False
        self.pos += len(new)
        lines = (self.part + new).split(b"\n")
        self.part = lines.pop()
        moved = False
        for line in lines:
            try:
                direction, files, byts, name = line.decode(
                    "utf-8", "replace").split(" ", 3)
                done, total = (int(x) for x in byts.split("/"))
                _n, of = (int(x) for x in files.split("/"))
            except ValueError:
                continue
            if total <= 0:
                continue
            self.direction, self.of = direction, max(self.of, of)
            if self.files.get(name) != (done, total):
                self.files[name] = (done, total)
                moved = True
        return moved

    @property
    def done(self):
        return sum(d for d, _t in self.files.values())

    def status(self, rate=0.0):
        """"Uploading 42% (1/3) — 126.0 MB / ~300.0 MB | 4.2 MB/s"."""
        known = sum(t for _d, t in self.files.values())
        if not known:
            return None
        estimated = self.of > len(self.files)
        total = known * self.of // len(self.files) if estimated else known
        finished = sum(1 for d, t in self.files.values() if d >= t)
        return "%s %d%%%s — %s / %s%s%s" % (
            _LFS_LABEL.get(self.direction, self.direction.title()),
            min(100, self.done * 100 // total),
            " (%d/%d)" % (finished, self.of) if self.of > 1 else "",
            _human(self.done), "~" if estimated else "", _human(total),
            " | %s/s" % _human(rate) if rate > 0 else "")


def _ask(parent, text, title="Git Sync", icon=QMessageBox.Warning, buttons=None,
         default=None):
    """A message box wearing the git icon. Returns the standard button clicked.

    QMessageBox's static helpers take no window icon, and these boxes are part of
    the same flow as the conflict resolver — they have to look like it.
    """
    buttons = buttons if buttons is not None else QMessageBox.Ok
    default = default if default is not None else QMessageBox.NoButton
    return git_message_box(parent, title, text, icon, buttons, default)


def _read(proc, err=False):
    """Decoded output, or "" if the window closed and took the QProcess with it."""
    if not isValid(proc):
        return ""
    return bytes(proc.readAllStandardError() if err
                 else proc.readAllStandardOutput()).decode("utf-8", "replace")


def _progress(line):
    """"Downloading 45% — 1.20 MiB | 500 KiB/s" for a git progress line, else None."""
    for needle, label in _PHASES:
        if needle not in line:
            continue
        pct = _PCT.search(line)
        if not pct:
            return label + "…"
        tail = line.split(", ", 1)[1].strip() if ", " in line else ""
        return "%s %s%%%s" % (label, pct.group(1),
                              " — " + tail if "|" in tail else "")
    return None


_SYNC_TOOLTIP = (
    "<html><head/><body>"
    "<p><span style=\" font-size:11pt; font-weight:700;\">Git Sync</span></p>"
    "<p>Pick the changes to send, then fetch, merge the server's work, resolve "
    "conflicts and push.</p>"
    "<p><span style=\"color:#E5A00D;\">●</span> uncommitted local changes"
    "&nbsp;&nbsp;<span style=\"color:#D64545;\">●</span> commits to pull "
    "or push</p>"
    "</body></html>")

_NO_REPO_TOOLTIP = (
    "<html><head/><body>"
    "<p><span style=\" font-size:11pt; font-weight:700;\">Git Sync</span></p>"
    "<p>This addon is not under version control. Click to set up a repository.</p>"
    "</body></html>")


class SyncButton(QPushButton):
    """Icon-only sync button that paints uncommitted / out-of-step-with-origin badges.

    A third state replaces both: no repository at all, drawn as a warning circle,
    because a button with no badges otherwise reads as "everything is in sync"
    when in fact nothing is being tracked.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(_SYNC_ICON))
        self.setProperty("h5Component", "gitSyncButton")
        self.setToolTip(_SYNC_TOOLTIP)
        self._local = 0    # uncommitted changes          -> yellow
        self._remote = 0   # commits to pull and/or push  -> red
        self._no_repo = False   # not a git repository     -> warning circle

    def set_counts(self, local, remote):
        if (local, remote) != (self._local, self._remote):
            self._local, self._remote = local, remote
            self.update()

    def set_no_repo(self, no_repo):
        if bool(no_repo) == self._no_repo:
            return
        self._no_repo = bool(no_repo)
        self.setToolTip(_NO_REPO_TOOLTIP if self._no_repo else _SYNC_TOOLTIP)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() != self.height():
            self.setFixedWidth(self.height())    # square; the row sets the height

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._no_repo:
            self._paint_warning()
            return
        if not (self._local or self._remote):
            return
        # Both badges have to fit along the top edge of a square that is only as
        # tall as the icon, so cap the diameter at half of it.
        d = min(13, (min(self.width(), self.height()) - 2) // 2)
        # One fixed corner each: a badge that moves when its neighbour clears is
        # unreadable.
        corners = ((self._local,  theme.color("#e5a00d"), (self.width() - d - 1, 1)),
                   (self._remote, theme.color("#d64545"), (1, 1)))
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        font = QFont(self.font())
        font.setPixelSize(max(7, d - 4))
        font.setBold(True)
        p.setFont(font)
        for count, color, (x, y) in corners:
            if count <= 0:
                continue
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color))
            p.drawEllipse(QRectF(x, y, d, d))
            p.setPen(Qt.white)
            p.drawText(QRectF(x, y, d, d), Qt.AlignCenter,
                       "99+" if count > 99 else str(count))
        p.end()

    def _paint_warning(self):
        """Amber "!" circle: no repository here."""
        d = min(13, (min(self.width(), self.height()) - 2) // 2)
        rect = QRectF(self.width() - d - 1, 1, d, d)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        font = QFont(self.font())
        font.setPixelSize(max(7, d - 3))
        font.setBold(True)
        p.setFont(font)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.color("#e5a00d")))
        p.drawEllipse(rect)
        p.setPen(Qt.white)
        p.drawText(rect, Qt.AlignCenter, "!")
        p.end()


class GitController:
    def __init__(self, main_window, button):
        self.main = main_window
        self.button = button
        self.repo = GitRepo(get_addon_dir())
        self.proc = None
        self._fetch_proc = None
        self._status_proc = None
        self._is_repo = True   # assumed until the first status says otherwise
        self._has_origin = False   # set by refresh(); no origin -> commit only
        self._msg = ""         # pending commit message, mid-sync
        self._leftover = False  # user left changes unticked
        self._stashed = False   # a stash of ours is waiting to be popped
        self._stash_msg = ""    # unique marker so an older stash is never popped
        self._tail = ""        # last thing git said, for failure reporting
        self._pathspec = None  # temp file listing a partial selection
        self._busy = False
        self._behind = 0       # commits the server is ahead, from the status poll
        self._branch = DEFAULT_BRANCH  # origin branch used by the active sync
        self._prog = None      # (when, bytes, rate) sample, for _tick_progress
        self._lfs = _LfsProgress()
        self.button.clicked.connect(self.sync)

        # git-lfs writes stderr in coarse bursts but logs every chunk, so poll
        # the log: that is what makes the percent creep instead of jump.
        self._prog_timer = QTimer(main_window)
        self._prog_timer.setInterval(200)
        self._prog_timer.timeout.connect(self._tick_progress)

        # Polling avoids the overhead and recursive-watch limitations of a
        # filesystem watcher for repository status.
        self._local_timer = QTimer(main_window)
        self._local_timer.setInterval(2_000)
        self._local_timer.timeout.connect(self._tick_badges)
        self._local_timer.start()

        self._fetch_timer = QTimer(main_window)
        self._fetch_timer.setInterval(15_000)
        self._fetch_timer.timeout.connect(self._auto_fetch)
        self._fetch_timer.start()
        self.refresh()

    # console helper
    def _log(self, text):
        try:
            self.main.update_title(text=text)
        except Exception:
            pass

    # state / refresh
    def refresh(self):
        """Re-point at the current addon and kick a badge refresh.

        `git remote` is read here rather than per-sync so the 15s fetch timer has
        an answer without spawning git on the UI thread. Addons switch and syncs
        finish rarely; one blocking spawn at each is cheap.
        """
        # Anything still in flight was started against the previous addon. Its
        # answer would paint this addon's badges with the old addon's counts, and
        # letting it run on means the QProcess outlives the reason it exists —
        # which is where "QProcess: Destroyed while process is still running"
        # came from on every switch.
        self._discard(self._status_proc)
        self._status_proc = None
        self._discard(self._fetch_proc)
        self._fetch_proc = None

        self.repo = GitRepo(get_addon_dir())
        self._has_origin = self.repo.has_origin()
        self._tick_badges()

    @staticmethod
    def _discard(proc):
        """Drop a poll we no longer want the answer to, without leaving it running.

        Disconnect first: kill() makes finished/errorOccurred fire, and those
        callbacks would otherwise walk into state that has already moved on.
        deleteLater only after the process is actually gone — deleting a live
        QProcess is what Qt warns about.
        """
        if proc is None or not isValid(proc):
            return
        try:
            proc.disconnect()
        except (RuntimeError, TypeError):
            pass    # nothing was connected
        if proc.state() != QProcess.NotRunning:
            proc.kill()
            proc.waitForFinished(2000)
        proc.deleteLater()

    def _tick_badges(self):
        """One async `git status` (no network) driven by the fast timer.

        porcelain=v2 --branch answers is-a-repo, local change count and distance
        from upstream in a single spawn, replacing the rev-parse + status +
        rev-list trio this used to run blocking on the UI thread. Skipped while
        one is still in flight, so a slow addon just polls less often.
        """
        if self._busy or self._status_proc is not None or not self.repo.dir:
            return
        proc = QProcess(self.main)
        proc.setWorkingDirectory(self.repo.dir)
        proc.finished.connect(lambda code, _st: self._status_done(proc, code))
        proc.errorOccurred.connect(lambda *_: self._status_done(proc, 1))
        self._status_proc = proc
        proc.start("git", STATUS_V2_ARGS)

    def _status_done(self, proc, code):
        # finished + errorOccurred can both fire; the guard makes it idempotent.
        # isValid: closing the window mid-poll destroys the QProcess and *then*
        # emits finished, so everything below would touch a dead C++ object.
        if self._status_proc is not proc or not isValid(proc):
            return
        self._status_proc = None
        out = _read(proc)
        # errorOccurred can fire while git is still alive (a read error mid-run,
        # not just FailedToStart); deleting it here would destroy a live process.
        self._discard(proc)
        self._is_repo = code == 0
        local, ahead, self._behind = (
            parse_status_v2(out) if self._is_repo else (0, 0, 0))
        self.button.set_counts(local, self._behind + ahead)
        self.button.set_no_repo(not self._is_repo)
        self.button.setEnabled(not self._busy)  # no repo -> opens the setup dialog

    def _auto_fetch(self):
        """Background `git fetch origin` every 15s; refresh the pull badge after."""
        if (self._busy or self._fetch_proc is not None or not self._is_repo
                or not self._has_origin):
            return
        proc = QProcess(self.main)
        proc.setWorkingDirectory(self.repo.dir)
        proc.finished.connect(lambda *_: self._fetch_done(proc))
        self._fetch_proc = proc
        proc.start("git", ["fetch", "origin"])

    def _fetch_done(self, proc):
        if not isValid(proc):   # window closed mid-fetch; see _status_done
            return
        proc.deleteLater()
        if self._fetch_proc is proc:
            self._fetch_proc = None
        self._tick_badges()

    # pre-commit size guards
    def _precommit_size_checks(self, files):
        """Warn about >100MB non-LFS files and large total uploads.

        Returns True to proceed, False if the user cancelled."""
        huge = [(p, s) for p, s in files if s > _LFS_LIMIT]
        lfs = self.repo.lfs_tracked([p for p, _ in huge])
        big = [(p, s) for p, s in huge if p not in lfs]
        if big:
            listing = "\n".join(f"  • {p} ({_human(s)})" for p, s in big[:10])
            if len(big) > 10:
                listing += f"\n  … +{len(big) - 10} more"
            r = _ask(
                self.main,
                "These files are over 100 MB and are not tracked by Git LFS:\n\n"
                f"{listing}\n\n"
                "Hosts like GitHub reject files this large. Set the repository "
                "up with Git LFS, or untick them, before syncing.\n\n"
                "Commit anyway?",
                title="Large files not tracked by LFS",
                buttons=QMessageBox.Yes | QMessageBox.No,
                default=QMessageBox.No)
            if r != QMessageBox.Yes:
                return False

        total = sum(s for _, s in files)
        if total > _LARGE_COMMIT:
            r = _ask(
                self.main,
                f"You're going to upload {_human(total)} of files, this might "
                "take longer than usual. Proceed?",
                title="Large commit", icon=QMessageBox.Question,
                buttons=QMessageBox.Yes | QMessageBox.No,
                default=QMessageBox.Yes)
            if r != QMessageBox.Yes:
                return False
        return True

    def _open_setup(self):
        """No repository here yet — offer to make one, then sync into it."""
        addon = get_addon_dir()
        if not addon:
            _ask(self.main, "No addon selected.")
            return
        dlg = SetupDialog(addon, self.main)
        if not dlg.exec():
            return
        self.refresh()
        self._log("Repository ready — " + "; ".join(dlg.notes))

    # the one-button sync flow
    # pick changes -> commit them -> fetch -> push directly when the server is
    # already behind us. Only stash the rest when a pull/merge is actually needed,
    # then resolve -> push -> restore the stash.
    # With no origin there is nowhere to fetch from, so it stops after the commit.
    def sync(self):
        if self._busy:
            return
        if not self.repo.is_repo():
            self._open_setup()
            return

        # Cheap to re-read and the repo may have gained a remote since the last
        # refresh, so the sync path never runs on a stale answer.
        self._has_origin = self.repo.has_origin()

        # The one blocking git call left: it gates a modal dialog, so it has to
        # answer before we go on. Its output feeds the picker *and* the size
        # checks instead of running `git status` twice.
        entries = self.repo.entries(self.repo.status_porcelain())
        if any(word == "Conflict" for word, _path, _size in entries):
            _ask(
                self.main,
                "This repository already has unresolved conflicts. Finish or "
                "abort that Git operation before starting a new sync.")
            return
        if not entries and not self._has_origin:
            self._log("Nothing to commit")
            return

        selected, left_out = [], []
        self._msg = ""
        if entries:
            dlg = ChangesDialog(
                entries, self._behind,
                get_settings_bool('GitSync', 'generate_commit_messages', True),
                self.main)
            if not dlg.exec():
                return  # user cancelled
            selected = dlg.selected_paths()
            left_out = dlg.left_out_paths()
            self._msg = dlg.message() if selected else ""
            if not selected and not self._has_origin:
                self._log("Nothing selected")
                return
            if left_out and not selected and not self.repo.has_commits():
                _ask(
                    self.main,
                    "The first sync must include at least one change. Git cannot "
                    "temporarily set unticked work aside until the repository "
                    "has its first commit.")
                return

        chosen = set(selected)
        if not self._precommit_size_checks(
                [(p, s) for _w, p, s in entries if p in chosen and s]):
            return  # user cancelled

        self._leftover = bool(left_out)
        self._stash_msg = (
            "%s [%d-%d]" % (_STASH_MSG, os.getpid(), monotonic_ns())
            if self._leftover else "")
        self._branch = (self.repo.upstream_branch()
                        or self.repo.current_branch()
                        or DEFAULT_BRANCH)
        self._set_busy(True)
        if selected:
            self._start_add(selected, len(selected) == len(entries))
        else:
            self._after_commit(0)

    def _start_add(self, selected, everything):
        """Stage the ticked paths.

        A partial selection goes through a NUL-separated pathspec file rather
        than the argument list: a content tree can easily produce thousands of
        changed paths, which blows past Windows' 32k command line. Pathspecs are
        forced literal so a map called `de_dust[2].vmap` is a filename and not a
        character class.
        """
        if everything:
            self._stream(["add", "-A"], self._after_add)
            return
        # A user may already have staged WIP. `git add <selected>` does not
        # remove those index entries, so committing now would include unticked
        # files. Clear only the index first; both commands preserve every byte
        # in the working tree.
        if self.repo.has_commits():
            args = ["reset", "--mixed", "--quiet", "HEAD"]
        else:
            args = ["rm", "-r", "--cached", "--ignore-unmatch", "."]
        self._stream(args, lambda code: self._after_index_reset(code, selected))

    def _after_index_reset(self, code, selected):
        if code != 0:
            self._end(
                "Could not prepare the selected changes",
                failed="git could not clear the staging area:\n\n" + self._tail)
            return
        fd, path = tempfile.mkstemp(prefix="h5t_pathspec_", suffix=".txt")
        with os.fdopen(fd, "wb") as f:
            f.write(b"\0".join(p.encode("utf-8") for p in selected))
        self._pathspec = path
        self._stream(["--literal-pathspecs", "add", "-A",
                      "--pathspec-from-file=" + path, "--pathspec-file-nul"],
                     self._after_add)

    def _after_add(self, code):
        if self._pathspec:
            try:
                os.remove(self._pathspec)
            except OSError:
                pass
            self._pathspec = None
        if code != 0:
            self._end(
                "Could not stage the selected changes",
                failed="git add failed:\n\n" + self._tail)
            return
        self._stream(["commit", "-m", self._msg], self._after_commit)

    def _after_commit(self, code):
        if code != 0 and self._msg:
            self._end(
                "Could not commit the selected changes",
                failed="git commit failed:\n\n" + self._tail)
            return
        if self._msg:
            self._log(f"Committed: {self._msg}")
        if not self._has_origin:
            # Local-only repo. Committing is the whole sync; fetch/pull/push
            # would just fail on a missing remote.
            self._end("Committed — no server configured yet")
            return
        self._start_fetch()

    def _after_stash(self, code):
        # `stash push` exits 0 even when it saved nothing, so confirm ours is
        # actually on top before anything later pops it. The exit code does not
        # gate that check: stash writes refs/stash *first* and only then runs the
        # internal `reset --hard` that clears the working tree. If that reset
        # fails, the stash it left behind still holds real work, so ours is popped
        # on the way out whether the push reported success or not. Otherwise the
        # saved changes disappear from the working tree with no recovery notice.
        self._stashed = bool(self._stash_msg) and (
            self.repo.stash_top_message().endswith(self._stash_msg))
        if code != 0:
            recovery = (
                "\n\nGit created a backup stash before the failure. Hammer 5 "
                "Tools will try to restore it now; if that cannot be completed, "
                "the backup stash will be kept."
                if self._stashed else "")
            self._end("Could not set your other changes aside — sync stopped",
                      failed="git stash failed:\n\n" + self._tail + recovery)
            return
        self._start_pull()

    def _start_fetch(self):
        self._stream(["fetch", "--progress", "origin"], self._after_fetch)

    def _after_fetch(self, code):
        if code != 0:
            self._end(
                "Could not contact the server",
                failed="git fetch failed:\n\n" + self._tail)
            return
        if not self.repo.remote_branch_exists(self._branch):
            self._start_push()
            return
        if self._leftover:
            # Fetch is safe with a dirty tree. In the common ahead-only case the
            # selected commit can be pushed without ever moving an unticked file,
            # avoiding stash-pop collisions with open or regenerated assets.
            self._stream([
                "merge-base", "--is-ancestor",
                "origin/" + self._branch, "HEAD"],
                self._after_remote_ancestor)
            return
        self._start_pull()

    def _after_remote_ancestor(self, code):
        if code == 0:
            self._start_push()
            return
        if code != 1:
            self._end(
                "Could not compare local and server history",
                failed="git merge-base failed:\n\n" + self._tail)
            return
        # The server has work that is not in HEAD, so Git must merge it over a
        # clean tree. Only this less-common path needs to set unticked work aside.
        self._stream(["stash", "push", "-u", "-m", self._stash_msg],
                     self._after_stash)

    def _start_pull(self):
        self._stream([
            "pull", "--no-rebase", "--allow-unrelated-histories", "--progress",
            "origin", self._branch], self._after_pull)

    def _after_pull(self, code):
        if code != 0:
            if not self.repo.conflicts():
                # Unrelated histories, no upstream, refused merge, auth. Pushing
                # on top of this only produces a second, more confusing error.
                self._end("Could not get the server's changes",
                          failed="git pull failed:\n\n" + self._tail)
                return
            if not self._resolve_conflicts():
                self._end("Sync cancelled")
                return
        self._start_push()

    def _start_push(self):
        if not self.repo.has_commits():
            self._end("Nothing to sync")
            return
        self._stream([
            "push", "--progress", "--set-upstream", "origin",
            "HEAD:" + self._branch], self._after_push)

    def _after_push(self, code):
        if code != 0:
            self._end("Push failed", failed="git push failed:\n\n" + self._tail)
            return
        self._end("Sync complete")

    def _end(self, message, failed=None):
        """Finish the sync: put the user's other changes back, then report.

        Every exit from the chain lands here, including the failures — a stash
        left behind after an aborted sync is work that has silently vanished
        from the user's editor.
        """
        if failed:
            _ask(self.main, failed.strip())
        if self._stashed:
            self._stashed = False
            self._stream(["stash", "pop"], lambda code: self._after_unstash(code, message))
            return
        self._leftover = False
        self._stash_msg = ""
        self._log(message)
        self._set_busy(False)
        self.refresh()

    def _after_unstash(self, code, message):
        if code != 0:
            # A failed pop leaves the stash in place. This can be a conflict after
            # a pull or a partially cleared tree after `stash push` itself failed.
            _ask(
                self.main,
                "Git could not put all of your unticked changes back "
                "automatically. Some may still be modified on disk; the backup "
                "stash was kept so the remaining work is not lost.\n\nInspect the "
                "working tree and the newest stash in a Git client or terminal. "
                "After confirming all of your work is present, remove the backup "
                "with \"git stash drop\".")
            message += " (your other changes are still in the stash)"
        self._end(message)

    def _resolve_conflicts(self):
        """Merge conflict resolution. Returns True if resolved, False if aborted."""
        files = self.repo.conflicts()
        if not files:
            return True
        dlg = ConflictDialog(self.repo, files, self.main)
        if not dlg.exec():          # 0 == rejected; dlg.Accepted is not a thing in PySide6
            self.repo._run("merge", "--abort")
            return False
        # All files added by the dialog -> finish the merge commit.
        code, _out, err = self.repo._run("commit", "--no-edit")
        if code != 0:
            _ask(
                self.main,
                "Git could not finish the merge:\n\n" +
                (err.strip() or "Unknown error"))
            self.repo._run("merge", "--abort")
            return False
        return not self.repo.conflicts()

    # QProcess streaming
    def _stream(self, args, on_done):
        # args[0] can be a git-level option (--literal-pathspecs); the step is
        # the first word that is not one.
        step = next((a for a in args if not a.startswith("-")), args[0])
        self._log(_VERBS.get(step, "git " + step) + "…")
        self._tail = ""
        proc = QProcess(self.main)
        proc.setWorkingDirectory(self.repo.dir)
        # git-lfs prints transfer progress only when stderr is a terminal, and
        # the LFS objects are exactly the part worth watching in a map repo.
        try:
            os.remove(_LFS_LOG)      # git-lfs appends; each step starts clean
        except OSError:
            pass
        env = QProcessEnvironment.systemEnvironment()
        env.insert("GIT_LFS_FORCE_PROGRESS", "1")
        env.insert("GIT_LFS_PROGRESS", _LFS_LOG)
        proc.setProcessEnvironment(env)
        self._prog, self._lfs = None, _LfsProgress()
        self._prog_timer.start()
        proc.readyReadStandardError.connect(lambda: self._pump(proc, err=True))
        proc.readyReadStandardOutput.connect(lambda: self._pump(proc, err=False))
        proc.finished.connect(lambda ec, _st: self._finish(proc, ec, on_done))
        self.proc = proc
        proc.start("git", args)
        if not proc.waitForStarted(3000):
            self._log("git not found")
            self._set_busy(False)
            self.refresh()

    def _tick_progress(self):
        """Advance the status line from git-lfs' byte log, five times a second.

        Only on movement: when the transfer ends the label is left alone so the
        next git phase from _pump can take it over. The rate is smoothed, an
        instant delta over a 200 ms window swings wildly.
        """
        if not self._lfs.read():
            return
        done, now = self._lfs.done, monotonic()
        if self._prog is None:
            self._prog = (now, done, 0.0)    # a rate needs two samples
            return
        was, before, rate = self._prog
        if done == before:
            return
        instant = (done - before) / max(1e-3, now - was)
        rate = instant if rate <= 0 else rate * 0.7 + instant * 0.3
        self._prog = (now, done, rate)
        self._log(self._lfs.status(rate))

    def _pump(self, proc, err):
        """Report the newest thing git said, as a phase where we recognise one.

        git redraws one line with \\r, so a single read holds several updates and
        its tail is often a half-written line. Newest recognised phase wins;
        anything else falls through to the last line so errors still show.
        """
        text = _read(proc, err)
        lines = [c.strip() for c in text.replace("\r", "\n").split("\n")
                 if c.strip() and not any(m in c for m in _MUTED)]
        for line in reversed(lines):
            phase = _progress(line)
            if phase:
                self._log(phase)
                return
        if lines:
            self._tail = lines[-1]
            self._log(lines[-1])

    def _finish(self, proc, exit_code, on_done):
        if not isValid(proc):       # window closed mid-step; see _status_done
            return                  # the timer died with it — nothing to stop
        self._prog_timer.stop()
        proc.deleteLater()
        if self.proc is proc:
            self.proc = None
        # Off the signal, not inside it. deleteLater() above only *posts* the
        # delete; a step that opens a modal dialog (the conflict resolver) spins
        # a nested event loop, which delivers that event and destroys the
        # QProcess while Qt is still emitting its finished signal — a hard crash,
        # and the reason sync only ever died on merges. singleShot(0) runs the
        # rest of the chain from the event loop, once the emit has unwound.
        # Bound to the window so a close in that gap drops the callback instead
        # of running it against freed widgets.
        QTimer.singleShot(0, self.main, lambda: on_done(exit_code))

    def _set_busy(self, busy):
        self._busy = busy
        if isValid(self.button):
            # Enabled even without a repo: that click opens the setup dialog.
            self.button.setEnabled(not busy)


if __name__ == "__main__":   # python -m gui.forms.git_sync.controller
    assert _progress("Receiving objects:  45% (450/1000), 1.20 MiB | 500.00 KiB/s") \
        == "Downloading 45% — 1.20 MiB | 500.00 KiB/s"
    assert _progress("remote: Counting objects:  9% (2/20)") == "Processing 9%"
    assert _progress("Compressing objects: 100% (20/20), done.") == "Compressing 100%"
    assert _progress("Enumerating objects: 20, done.") == "Processing…"
    assert _progress("fatal: could not read Username for 'https://github.com'") is None

    # git-lfs' own object-count percent is muted; the byte log replaces it
    assert _progress("Uploading LFS objects:   0% (0/1), 12 MB | 517 KB/s") is None

    log = os.path.join(tempfile.gettempdir(), "h5t_lfs_selfcheck.log")
    p = _LfsProgress(log)
    assert p.read() is False                        # no log yet
    mb = 1024 * 1024
    with open(log, "wb") as f:                      # one of three files, part done
        f.write(b"upload 1/3 %d/%d a.vmap\nupload 1/3 %d/%d a.vm" % (
            10 * mb, 100 * mb, 11 * mb, 100 * mb))  # trailing partial: ignored
    assert p.read() is True
    # 100 MB seen for 1 of 3 files -> total priced at 300 MB, so 10 of ~300
    assert p.status() == "Uploading 3% (0/3) — 10.0 MB / ~300.0 MB"
    assert p.read() is False                        # nothing new appended
    with open(log, "ab") as f:                      # finish it, start the rest
        f.write(b"ap\nupload 2/3 %d/%d a.vmap\nupload 2/3 %d/%d b.vmap\n"
                b"upload 3/3 %d/%d c.vmap\n" % (100 * mb, 100 * mb, 50 * mb,
                                                200 * mb, 0, 100 * mb))
    assert p.read() is True
    # every file seen now: real total, no ~, and the percent is transfer-wide
    assert p.status(4404019) == "Uploading 37% (1/3) — 150.0 MB / 400.0 MB | 4.2 MB/s"
    os.remove(log)

    # badge counts: 2 changed paths, 3 to push, 1 to pull
    assert parse_status_v2("# branch.ab +3 -1\n1 .M N... a\n? b\n") == (2, 3, 1)
    print("ok")
