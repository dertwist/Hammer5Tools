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
from time import monotonic

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QColor, QFont
from PySide6.QtWidgets import QPushButton, QMessageBox, QInputDialog, QLineEdit
from shiboken6 import isValid

from src.settings.common import get_addon_dir, get_settings_bool
from src.git_sync.backend import GitRepo, STATUS_V2_ARGS, parse_status_v2
from src.git_sync.commit_msg import generate
from src.git_sync.conflict_dialog import ConflictDialog

_SYNC_ICON = ":/icons/sync_24dp.svg"

_LFS_LIMIT = 100 * 1024 * 1024    # GitHub rejects blobs over 100 MiB
_LARGE_COMMIT = 500 * 1024 * 1024  # warn about slow uploads over this


def _human(nbytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024 or unit == "TB":
            return f"{nbytes:.0f} {unit}" if unit in ("B", "KB") else f"{nbytes:.1f} {unit}"
        nbytes /= 1024


# What the status line says while each step runs, before git reports progress.
_VERBS = {"add": "Staging changes", "commit": "Committing",
          "fetch": "Checking for updates", "pull": "Downloading changes",
          "push": "Uploading changes"}

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


class SyncButton(QPushButton):
    """Icon-only sync button that paints uncommitted / out-of-step-with-origin badges."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(_SYNC_ICON))
        self.setStyleSheet("padding: 5px;")
        self.setToolTip(
            "<html><head/><body>"
            "<p><span style=\" font-size:11pt; font-weight:700;\">Git Sync</span></p>"
            "<p>Commit local changes, fetch, pull (merge), resolve conflicts, "
            "then push the current addon repo.</p>"
            "<p><span style=\"color:#E5A00D;\">●</span> uncommitted local changes"
            "&nbsp;&nbsp;<span style=\"color:#D64545;\">●</span> commits to pull "
            "or push</p>"
            "</body></html>")
        self._local = 0    # uncommitted changes          -> yellow
        self._remote = 0   # commits to pull and/or push  -> red

    def set_counts(self, local, remote):
        if (local, remote) != (self._local, self._remote):
            self._local, self._remote = local, remote
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() != self.height():
            self.setFixedWidth(self.height())    # square; the row sets the height

    def paintEvent(self, event):
        super().paintEvent(event)
        if not (self._local or self._remote):
            return
        # Both badges have to fit along the top edge of a square that is only as
        # tall as the icon, so cap the diameter at half of it.
        d = min(13, (min(self.width(), self.height()) - 2) // 2)
        # One fixed corner each: a badge that moves when its neighbour clears is
        # unreadable.
        corners = ((self._local,  "#E5A00D", (self.width() - d - 1, 1)),
                   (self._remote, "#D64545", (1, 1)))
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
        self._busy = False
        self._prog = None      # (when, bytes, rate) sample, for _tick_progress
        self._lfs = _LfsProgress()
        self.button.clicked.connect(self.sync)

        # git-lfs writes stderr in coarse bursts but logs every chunk, so poll
        # the log: that is what makes the percent creep instead of jump.
        self._prog_timer = QTimer(main_window)
        self._prog_timer.setInterval(200)
        self._prog_timer.timeout.connect(self._tick_progress)

        # ponytail: poll git status instead of wiring a recursive filesystem
        # watcher; swap to QFileSystemWatcher if 2s lag shows.
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
        local, ahead, behind = parse_status_v2(out) if self._is_repo else (0, 0, 0)
        self.button.set_counts(local, behind + ahead)
        self.button.setEnabled(not self._busy)  # no repo -> shows "no repo" dialog

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
            r = QMessageBox.warning(
                self.main, "Large files not tracked by LFS",
                "These files are over 100 MB and are not tracked by Git LFS:\n\n"
                f"{listing}\n\n"
                "Hosts like GitHub reject files this large. Consider tracking "
                "them with Git LFS (git lfs track) before committing.\n\n"
                "Commit anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if r != QMessageBox.Yes:
                return False

        total = sum(s for _, s in files)
        if total > _LARGE_COMMIT:
            r = QMessageBox.question(
                self.main, "Large commit",
                f"You're going to upload {_human(total)} of files, this might "
                "take longer than usual. Proceed?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if r != QMessageBox.Yes:
                return False
        return True

    def _commit_message(self, porcelain):
        """The message to commit with, or None if the user cancelled.

        Generated from the changed paths unless the user turned that off, in
        which case the generated text seeds an editable prompt.
        """
        suggested = generate(porcelain)
        if get_settings_bool('GitSync', 'generate_commit_messages', True):
            return suggested
        msg, ok = QInputDialog.getText(
            self.main, "Commit message", "Describe what changed:",
            QLineEdit.Normal, suggested)
        if not ok:
            return None
        # An empty box means "just use the suggestion", not an empty commit.
        return msg.strip() or suggested

    # the one-button sync flow
    # commit existing changes -> fetch -> pull (merge) -> resolve -> push
    # With no origin there is nowhere to fetch from, so it stops after the commit.
    def sync(self):
        if self._busy:
            return
        if not self.repo.is_repo():
            QMessageBox.warning(self.main, "Git Sync",
                                "Git repository not found, cannot sync changes.")
            return

        # Cheap to re-read and the repo may have gained a remote since the last
        # refresh, so the sync path never runs on a stale answer.
        self._has_origin = self.repo.has_origin()

        # The one blocking git call left: it gates a modal dialog, so it has to
        # answer before we go on. Its output feeds the size checks *and* the
        # commit message instead of running `git status` twice.
        porcelain = self.repo.status_porcelain()
        if not self._precommit_size_checks(self.repo.changed_files(porcelain)):
            return  # user cancelled

        if not porcelain.strip():
            if not self._has_origin:
                self._log("Nothing to commit")
                return
            self._set_busy(True)
            self._start_fetch()
            return

        msg = self._commit_message(porcelain)
        if msg is None:
            return  # user cancelled the prompt
        self._msg = msg
        self._set_busy(True)
        self._stream(["add", "-A"], self._after_add)

    def _after_add(self, _code):
        self._stream(["commit", "-m", self._msg], self._after_commit)

    def _after_commit(self, code):
        # Non-zero == `add -A` staged nothing after all (everything ignored, or
        # touched-but-identical). Nothing to report, carry on with the sync.
        if code == 0:
            self._log(f"Committed: {self._msg}")
        if not self._has_origin:
            # Local-only repo. Committing is the whole sync; fetch/pull/push
            # would just fail on a missing remote.
            self._set_busy(False)
            self.refresh()
            return
        self._start_fetch()

    def _start_fetch(self):
        self._stream(["fetch", "--progress"], self._after_fetch)

    def _after_fetch(self, _code):
        self._stream(["pull", "--no-rebase", "--progress"], self._after_pull)

    def _after_pull(self, code):
        if code != 0 and self.repo.conflicts():
            if not self._resolve_conflicts():
                self._log("Sync aborted")
                self._set_busy(False)
                self.refresh()
                return
        self._stream(["push", "--progress", "origin", "HEAD"], self._after_push)

    def _after_push(self, _code):
        self._log("Sync complete")
        self._set_busy(False)
        self.refresh()

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
        self.repo._run("commit", "--no-edit")
        return not self.repo.conflicts()

    # QProcess streaming
    def _stream(self, args, on_done):
        self._log(_VERBS.get(args[0], "git " + args[0]) + "…")
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
            self.button.setEnabled(not busy and self._is_repo)


if __name__ == "__main__":   # python -m src.git_sync.controller
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
