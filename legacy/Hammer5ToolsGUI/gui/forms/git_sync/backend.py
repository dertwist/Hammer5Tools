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

# First line of every Git LFS pointer file; see show_stage.
_LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"

# Read-only git commands still take .git/index.lock to write back a refreshed
# index, so a poll every 2s regularly collides with whatever else has the addon
# open — Hammer, the Steam tools, a shell — and both sides see "Unable to create
# index.lock". --no-optional-locks drops that write; it is exactly what git ships
# for background pollers. Must sit before the subcommand.
NO_LOCKS = "--no-optional-locks"

# -uall lists untracked files individually; the default collapses whole dirs to
# "dir/", which both undercounts the badge and hides per-file sizes.
STATUS_V2_ARGS = [NO_LOCKS, "status", "--porcelain=v2", "--branch", "-uall"]


# Porcelain XY code -> the word the changes picker shows. The interesting half
# of XY is whichever side is not a space; `??` has no code at all.
_CHANGE_WORDS = {"A": "New", "D": "Deleted", "R": "Renamed", "C": "Copied",
                 "M": "Modified", "T": "Modified", "U": "Conflict"}


def parse_entries(porcelain):
    """[(change word, path)] from `git status --porcelain` output, in git's order."""
    out = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        xy, path = line[:2], line[3:].strip()
        if " -> " in path:          # rename: the new name is the one on disk
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"')
        if not path:
            continue
        if xy == "??":
            word = "New"
        else:
            code = xy[0] if xy[0] != " " else xy[1]
            word = _CHANGE_WORDS.get(code, "Modified")
        out.append((word, path))
    return out


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
                # git emits UTF-8 regardless of the console codepage. text=True
                # alone decodes with the locale codec — cp1252 on a western
                # Windows — so one accented character in a branch name, author or
                # commit subject killed subprocess' reader thread and run() then
                # handed back an empty string: no error, just a repo that looked
                # clean when it was not. errors="replace" keeps a genuinely
                # mis-encoded byte cosmetic instead of silently emptying output.
                encoding="utf-8",
                errors="replace",
                creationflags=_NO_WINDOW,
            )
            return p.returncode, (p.stdout or ""), (p.stderr or "")
        except Exception:
            # git missing, bad cwd, or output this could not be read. A status
            # poll must never be able to take the app down, so the caller just
            # sees "no repo".
            return 1, "", ""

    def is_repo(self):
        code, out, _ = self._run("rev-parse", "--is-inside-work-tree")
        return code == 0 and out.strip() == "true"

    def status_porcelain(self):
        # -uall and --no-optional-locks: see STATUS_V2_ARGS.
        code, out, _ = self._run(NO_LOCKS, "status", "--porcelain", "-uall")
        return out if code == 0 else ""

    def has_origin(self):
        """True if a remote named origin exists — i.e. there is anywhere to sync to."""
        code, out, _ = self._run(NO_LOCKS, "remote")
        return code == 0 and "origin" in out.split()

    def has_commits(self):
        """False on a freshly initialised repo, where HEAD points at nothing yet."""
        return self._run("rev-parse", "--verify", "HEAD")[0] == 0

    def current_branch(self):
        return self._run(NO_LOCKS, "branch", "--show-current")[1].strip()

    def upstream_branch(self):
        """The branch tracked on origin, or "" when no origin upstream is set."""
        code, out, _ = self._run(
            NO_LOCKS, "rev-parse", "--abbrev-ref", "--symbolic-full-name",
            "@{upstream}")
        ref = out.strip() if code == 0 else ""
        return ref[len("origin/"):] if ref.startswith("origin/") else ""

    def remote_branch_exists(self, branch):
        """True when the last fetch produced an origin/<branch> ref."""
        if not branch:
            return False
        return self._run(
            NO_LOCKS, "show-ref", "--verify", "--quiet",
            "refs/remotes/origin/" + branch)[0] == 0

    def entries(self, porcelain=None):
        """[(change word, path, size_bytes)] for every local change.

        A deleted file has no size. Pass an existing status_porcelain() result to
        reuse it instead of paying for a second `git status`.
        """
        if porcelain is None:
            porcelain = self.status_porcelain()
        out = []
        for word, path in parse_entries(porcelain):
            full = os.path.join(self.dir, path) if self.dir else path
            size = os.path.getsize(full) if os.path.isfile(full) else 0
            out.append((word, path, size))
        return out

    def changed_files(self, porcelain=None):
        """(path, size_bytes) for changed files still present on disk.

        Deletions are skipped — they add no upload weight, which is all the size
        guards care about."""
        return [(path, size) for word, path, size in self.entries(porcelain)
                if word != "Deleted" and size]

    def stash_top_message(self):
        """Subject of the newest stash entry, or "" if the stash is empty.

        `git stash push` with nothing to save still exits 0, so this is how the
        sync flow tells "I stashed something" from "there was nothing to stash".
        Popping on the strength of the exit code alone would restore whatever
        unrelated stash the user happened to have sitting there.
        """
        code, out, _ = self._run(NO_LOCKS, "stash", "list", "-1", "--format=%gs")
        return out.strip() if code == 0 else ""

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

        LFS-tracked paths (which .vmap usually is) store a ~130-byte text
        pointer in the index, not the map, so run it back through the smudge
        filter to get the real bytes.
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
            if p.returncode != 0:
                return None
            if not p.stdout.startswith(_LFS_POINTER):
                return p.stdout
            p = subprocess.run(
                ["git", "lfs", "smudge", "--", path],
                cwd=self.dir,
                input=p.stdout,
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
    assert parse_entries("") == []
    assert parse_entries("?? maps/new.vmap") == [("New", "maps/new.vmap")]
    assert parse_entries(" M maps/a.vmap") == [("Modified", "maps/a.vmap")]
    assert parse_entries("M  maps/a.vmap") == [("Modified", "maps/a.vmap")]
    assert parse_entries(" D models/gone.vmdl") == [("Deleted", "models/gone.vmdl")]
    assert parse_entries("R  old.vmat -> materials/new.vmat") == [
        ("Renamed", "materials/new.vmat")]
    assert parse_entries("UU maps/a.vmap") == [("Conflict", "maps/a.vmap")]
    assert parse_entries('?? "with space.vmat"') == [("New", "with space.vmat")]

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
