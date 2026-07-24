"""Thin wrapper over the system `git` CLI, scoped to one addon directory.

Fast reads (branch, status, ahead/behind) run through subprocess.run and capture
output. Long streaming ops (fetch/pull/push) are driven by the controller through
a QProcess so `git --progress` reaches the console line; those are not here.
"""
import os
import subprocess
import sys

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


class GitRepo:
    def __init__(self, addon_dir):
        self.dir = str(addon_dir) if addon_dir else None

    def _run(self, *args):
        """Run a git command, return (returncode, stdout, stderr). Never raises."""
        if not self.dir:
            return 1, "", ""
        try:
            p = subprocess.run(
                ["git", *args],
                cwd=self.dir,
                capture_output=True,
                text=True,
                creationflags=_NO_WINDOW,
            )
            return p.returncode, (p.stdout or ""), (p.stderr or "")
        except (OSError, ValueError):
            # git not installed / bad cwd
            return 1, "", ""

    def is_repo(self):
        code, out, _ = self._run("rev-parse", "--is-inside-work-tree")
        return code == 0 and out.strip() == "true"

    def current_branch(self):
        code, out, _ = self._run("rev-parse", "--abbrev-ref", "HEAD")
        return out.strip() if code == 0 else ""

    def branches(self):
        """Local branch names, current first."""
        code, out, _ = self._run("branch", "--format=%(refname:short)")
        if code != 0:
            return []
        names = [ln.strip() for ln in out.splitlines() if ln.strip()]
        cur = self.current_branch()
        if cur in names:
            names.remove(cur)
            names.insert(0, cur)
        return names

    def status_porcelain(self):
        # -uall lists untracked files individually (default collapses whole
        # untracked dirs to "dir/", which hides per-file sizes).
        code, out, _ = self._run("status", "--porcelain", "-uall")
        return out if code == 0 else ""

    def has_staged(self):
        code, _, _ = self._run("diff", "--cached", "--quiet")
        return code != 0  # non-zero exit == there are staged changes

    def is_dirty(self):
        return bool(self.status_porcelain().strip())

    def local_change_count(self):
        """Number of changed/untracked paths in the working tree."""
        return len([ln for ln in self.status_porcelain().splitlines() if ln.strip()])

    def changed_files(self):
        """(path, size_bytes) for added/modified/untracked files present on disk.

        Deletions are skipped (they add no upload weight)."""
        out = []
        for line in self.status_porcelain().splitlines():
            if len(line) < 4:
                continue
            if "D" in line[:2]:
                continue
            path = line[3:].strip().strip('"')
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            full = os.path.join(self.dir, path)
            if os.path.isfile(full):
                out.append((path, os.path.getsize(full)))
        return out

    def is_lfs_tracked(self, path):
        code, out, _ = self._run("check-attr", "filter", "--", path)
        return code == 0 and "filter: lfs" in out

    def conflicts(self):
        """Paths with an unresolved merge conflict (both sides touched)."""
        out = []
        for line in self.status_porcelain().splitlines():
            if len(line) < 3:
                continue
            xy = line[:2]
            if xy in ("UU", "AA", "DD", "AU", "UA", "DU", "UD"):
                out.append(line[3:].strip())
        return out

    def ahead_behind(self):
        """(ahead, behind) vs the upstream, or (0, 0) if no upstream."""
        code, out, _ = self._run(
            "rev-list", "--left-right", "--count", "@{u}...HEAD"
        )
        if code != 0:
            return 0, 0
        try:
            behind, ahead = out.split()
            return int(ahead), int(behind)
        except ValueError:
            return 0, 0
