"""Sync button + git glue, scoped to the current addon.

Fast reads/commits run synchronously (instant). fetch/pull/push run through a
QProcess so `git --progress` streams onto the console line. The sync flow is a
small async chain wired on QProcess.finished.

The button is icon-only (the settings "check updates" sync icon) with two badge
overlays: a yellow circle = uncommitted local changes, a red circle = commits
ahead of origin waiting to be pushed.
"""
from PySide6.QtCore import QProcess, QTimer, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QColor, QFont
from PySide6.QtWidgets import QPushButton, QMessageBox

from src.settings.common import get_addon_dir
from src.git_sync.backend import GitRepo
from src.git_sync.commit_msg import generate
from src.git_sync.conflict_dialog import ConflictDialog

_SYNC_ICON = ":/icons/sync_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"


class SyncButton(QPushButton):
    """Icon-only sync button that paints local-change / ahead-of-origin badges."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(_SYNC_ICON))
        self.setMinimumSize(40, 0)
        self.setStyleSheet("padding: 5px;")
        self.setToolTip(
            "<html><head/><body>"
            "<p><span style=\" font-size:11pt; font-weight:700;\">Git Sync</span></p>"
            "<p>Commit local changes, fetch, pull (merge), resolve conflicts, "
            "then push the current addon repo.</p>"
            "<p><span style=\"color:#E5A00D;\">●</span> uncommitted local changes"
            "&nbsp;&nbsp;<span style=\"color:#D64545;\">●</span> commits to pull</p>"
            "</body></html>")
        self._local = 0   # uncommitted changes -> yellow
        self._behind = 0  # commits to pull     -> red

    def set_counts(self, local, behind):
        if (local, behind) != (self._local, self._behind):
            self._local, self._behind = local, behind
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        badges = []
        if self._local > 0:
            badges.append((QColor("#E5A00D"), self._local))   # yellow
        if self._behind > 0:
            badges.append((QColor("#D64545"), self._behind))  # red
        if not badges:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        font = QFont(self.font())
        font.setPixelSize(9)
        font.setBold(True)
        p.setFont(font)
        d = 14                      # badge diameter
        x = self.width() - d - 2    # top-right, stacking leftwards
        y = 2
        for color, count in badges:
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawEllipse(QRectF(x, y, d, d))
            p.setPen(Qt.white)
            text = "99+" if count > 99 else str(count)
            p.drawText(QRectF(x, y, d, d), Qt.AlignCenter, text)
            x -= d + 2
        p.end()


class GitController:
    def __init__(self, main_window, button):
        self.main = main_window
        self.button = button
        self.repo = GitRepo(get_addon_dir())
        self.proc = None
        self._fetch_proc = None
        self._busy = False
        self.button.clicked.connect(self.sync)

        # ponytail: poll git status/rev-list (local, fast) instead of wiring a
        # recursive filesystem watcher; swap to QFileSystemWatcher if 2s lag shows.
        self._local_timer = QTimer(main_window)
        self._local_timer.setInterval(2_000)
        self._local_timer.timeout.connect(self._tick_badges)
        self._local_timer.start()

        self._fetch_timer = QTimer(main_window)
        self._fetch_timer.setInterval(15_000)
        self._fetch_timer.timeout.connect(self._auto_fetch)
        self._fetch_timer.start()
        self.refresh()

    # ---- console helper -------------------------------------------------
    def _log(self, text):
        try:
            self.main.update_title(text=text)
        except Exception:
            pass

    # ---- state / refresh ------------------------------------------------
    def refresh(self):
        """Re-point at the current addon and update the button + badges."""
        self.repo = GitRepo(get_addon_dir())
        if not self.repo.is_repo():
            self.button.setEnabled(not self._busy)  # clickable -> shows "no repo" dialog
            self.button.set_counts(0, 0)
            return
        self.button.setEnabled(not self._busy)
        _ahead, behind = self.repo.ahead_behind()
        self.button.set_counts(self.repo.local_change_count(), behind)

    def _tick_badges(self):
        """Cheap local refresh (no network) driven by the fast timer."""
        if self._busy or not self.repo.is_repo():
            return
        _ahead, behind = self.repo.ahead_behind()
        self.button.set_counts(self.repo.local_change_count(), behind)

    def _auto_fetch(self):
        """Background `git fetch origin` every 15s; refresh the pull badge after."""
        if self._busy or self._fetch_proc is not None or not self.repo.is_repo():
            return
        proc = QProcess(self.main)
        proc.setWorkingDirectory(self.repo.dir)
        proc.finished.connect(lambda *_: self._fetch_done(proc))
        self._fetch_proc = proc
        proc.start("git", ["fetch", "origin"])

    def _fetch_done(self, proc):
        proc.deleteLater()
        if self._fetch_proc is proc:
            self._fetch_proc = None
        self._tick_badges()

    # ---- the one-button sync flow --------------------------------------
    # commit existing changes -> fetch -> pull (merge) -> resolve -> push
    def sync(self):
        if self._busy:
            return
        if not self.repo.is_repo():
            QMessageBox.warning(self.main, "Git Sync",
                                "Git repository not found, cannot sync changes.")
            return
        self._set_busy(True)

        porcelain = self.repo.status_porcelain()
        self.repo._run("add", "-A")
        if self.repo.has_staged():
            msg = generate(porcelain)
            self.repo._run("commit", "-m", msg)
            self._log(f"Committed: {msg}")

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
        if dlg.exec() != dlg.Accepted:
            self.repo._run("merge", "--abort")
            return False
        # All files added by the dialog -> finish the merge commit.
        self.repo._run("commit", "--no-edit")
        return not self.repo.conflicts()

    # ---- QProcess streaming --------------------------------------------
    def _stream(self, args, on_done):
        self._log("git " + " ".join(args))
        proc = QProcess(self.main)
        proc.setWorkingDirectory(self.repo.dir)
        proc.readyReadStandardError.connect(lambda: self._pump(proc, err=True))
        proc.readyReadStandardOutput.connect(lambda: self._pump(proc, err=False))
        proc.finished.connect(lambda ec, _st: self._finish(proc, ec, on_done))
        self.proc = proc
        proc.start("git", args)
        if not proc.waitForStarted(3000):
            self._log("git not found")
            self._set_busy(False)
            self.refresh()

    def _pump(self, proc, err):
        raw = (proc.readAllStandardError() if err
               else proc.readAllStandardOutput())
        text = bytes(raw).decode("utf-8", "replace")
        for chunk in reversed(text.replace("\r", "\n").split("\n")):
            if chunk.strip():
                self._log(chunk.strip())
                break

    def _finish(self, proc, exit_code, on_done):
        proc.deleteLater()
        if self.proc is proc:
            self.proc = None
        on_done(exit_code)

    def _set_busy(self, busy):
        self._busy = busy
        self.button.setEnabled(not busy and self.repo.is_repo())
