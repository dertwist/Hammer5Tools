"""Thin wrapper over the system `git` CLI, scoped to one addon directory.

Reads run through subprocess.run and capture output. Anything on a timer or in
the sync chain (status polling, add/commit/fetch/pull/push) is driven by the
controller through a QProcess instead — spawning git costs ~150ms per call here,
which is a visible stall if it happens on the UI thread.

STATUS_V2_ARGS + parse_status_v2 exist for that async path: one git call answers
"is this a repo", "how many local changes" and "how far from upstream", which
used to be three separate spawns.
"""
import os
import subprocess
import sys

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

# -uall lists untracked files individually; the default collapses whole dirs to
# "dir/", which both undercounts the badge and hides per-file sizes.
STATUS_V2_ARGS = ["status", "--porcelain=v2", "--branch", "-uall"]


def parse_status_v2(out):
    """(local_changes, ahead, behind) from STATUS_V2_ARGS output.

    Every non-`#` line is one changed path (`1`/`2`/`u`/`?`); `# branch.ab`
    carries the upstream deltas as "+N -M". No `branch.ab` == no upstream.
    """
    local = ahead = behind = 0
    for line in out.splitlines():
        if line.startswith("# branch.ab "):
            a, b = line.split()[2:4]
            ahead, behind = int(a), -int(b)
        elif line and not line.startswith("#"):
            local += 1
    return local, ahead, behind


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

    def status_porcelain(self):
        # -uall: see STATUS_V2_ARGS.
        code, out, _ = self._run("status", "--porcelain", "-uall")
        return out if code == 0 else ""

    def changed_files(self, porcelain=None):
        """(path, size_bytes) for added/modified/untracked files present on disk.

        Deletions are skipped (they add no upload weight). Pass an existing
        status_porcelain() result to reuse it instead of paying for a second
        `git status`."""
        out = []
        if porcelain is None:
            porcelain = self.status_porcelain()
        for line in porcelain.splitlines():
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

    def lfs_tracked(self, paths):
        """Subset of paths Git LFS filters, in one check-attr call for the lot."""
        if not paths:
            return set()
        code, out, _ = self._run("check-attr", "filter", "--", *paths)
        if code != 0:
            return set()
        return {ln[:-len(": filter: lfs")] for ln in out.splitlines()
                if ln.endswith(": filter: lfs")}

    def show_stage(self, stage, path):
        """Raw bytes of one side of a conflict: 1=base, 2=ours, 3=theirs.

        None if that stage does not exist — stage 1 is missing whenever both
        sides added the file, which just means there is no common ancestor.
        Deliberately not _run(): that decodes as text and would wreck a binary
        blob like a .vmap.
        """
        if not self.dir:
            return None
        try:
            p = subprocess.run(
                ["git", "show", f":{stage}:{path}"],
                cwd=self.dir,
                capture_output=True,
                creationflags=_NO_WINDOW,
            )
        except (OSError, ValueError):
            return None
        return p.stdout if p.returncode == 0 else None

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


def _demo():
    assert parse_status_v2("") == (0, 0, 0)
    assert parse_status_v2(
        "# branch.oid abc\n# branch.head main\n") == (0, 0, 0)  # no upstream
    assert parse_status_v2(
        "# branch.oid abc\n"
        "# branch.head main\n"
        "# branch.upstream origin/main\n"
        "# branch.ab +2 -3\n"
        "1 .M N... 100644 100644 100644 aa bb src/a.py\n"
        "u UU N... 100644 100644 100644 100644 aa bb cc maps/x.vmap\n"
        "? untracked.txt\n"
    ) == (3, 2, 3)
    print("backend self-check OK")


if __name__ == "__main__":
    _demo()
