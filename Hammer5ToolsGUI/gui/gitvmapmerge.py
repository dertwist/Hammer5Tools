"""Block-level merge for Source 2 .vmap files.

Thin Python wrapper over the native `h5t_vmap_merge_*` ABI
(`Hammer5Tools.Core`'s `VmapMerger.cs`), which does the actual block scan,
3-way diff, tree rebuild, and DMX prefix-block splice — this module just
marshals requests/responses through `CoreBridge` and manages the native
session handle. See `VmapMerger.cs`'s doc comment for the full algorithm
description (block identity, digesting, content re-pairing for GUID-less
maps); it's unchanged from this module's own former pythonnet implementation.

Typical use::

    r = merge("ours.vmap", "theirs.vmap", base="base.vmap")
    for c in r.conflicts:
        r.resolve(c.id, OURS)        # or THEIRS
    r.write("merged.vmap")
    r.close()
"""
from __future__ import annotations

import logging

import os

log = logging.getLogger(__name__)

OURS = "ours"
THEIRS = "theirs"


class Block:
    """One map node, identified by its (save-stable) DMX element GUID."""

    __slots__ = ("id", "kind", "label")

    def __init__(self, data: dict):
        self.id = data["id"]
        self.kind = data["kind"]
        self.label = data["label"]

    def __repr__(self):
        return "<Block %s %s %s>" % (self.kind, self.label, self.id[:8])


class Conflict:
    """A block both sides changed differently. Resolve by picking OURS or THEIRS."""

    __slots__ = ("id", "kind", "label", "reason", "ours_digest", "theirs_digest")

    def __init__(self, data: dict):
        self.id = data["id"]
        self.kind = data["kind"]
        self.label = data["label"]
        self.reason = data["reason"]
        self.ours_digest = data.get("oursDigest")
        self.theirs_digest = data.get("theirsDigest")

    def __repr__(self):
        return "<Conflict %s %s: %s>" % (self.kind, self.label, self.reason)


class MergeResult:
    """Owns one native merge session handle."""

    def __init__(self, handle: int, summary: dict, bridge):
        self._handle: int | None = handle
        self._bridge = bridge
        self.ours_block_count = summary["oursBlockCount"]
        self.theirs_block_count = summary["theirsBlockCount"]
        self.realigned_count = summary["realignedCount"]
        self.added = [Block(b) for b in summary["added"]]
        self.removed = [Block(b) for b in summary["removed"]]
        self.changed = [Block(b) for b in summary["changed"]]
        self.conflicts = [Conflict(c) for c in summary["conflicts"]]
        self.orphaned: list[Block] = []

    # resolution
    def resolve(self, block_id: str, side: str):
        if side not in (OURS, THEIRS):
            raise ValueError("side must be OURS or THEIRS")
        if self._bridge.vmap_merge_resolve(self._handle, block_id, side) != 0:
            raise ValueError("invalid merge handle or block id")

    def resolve_all(self, side: str):
        """Pick one side for every remaining conflict — the 'primary vmap' choice."""
        if side not in (OURS, THEIRS):
            raise ValueError("side must be OURS or THEIRS")
        self._bridge.vmap_merge_resolve_all(self._handle, side)

    def summary(self) -> str:
        return ("%d blocks ours / %d theirs%s — %d added, %d removed, %d changed, "
                "%d conflicts" % (self.ours_block_count, self.theirs_block_count,
                                  " (%d paired by content)" % self.realigned_count
                                  if self.realigned_count else "",
                                  len(self.added), len(self.removed),
                                  len(self.changed), len(self.conflicts)))

    # output
    def write(self, out_path: str) -> str:
        """Apply the merge and save it to out_path. Raises RuntimeError if
        conflicts remain — call resolve()/resolve_all() first."""
        result = self._bridge.vmap_merge_write(self._handle, out_path)
        self.orphaned = [Block(b) for b in result["orphaned"]]
        return out_path

    def close(self):
        """Release the loaded maps — needed before deleting temp inputs."""
        if self._handle is not None:
            self._bridge.vmap_merge_close(self._handle)
            self._handle = None


def merge(ours_path: str, theirs_path: str, base: str | None = None, allow_unrelated: bool = False) -> MergeResult:
    """Merge two .vmap files block by block.

    base is the common ancestor (git's %O). Without it the merge is 2-way: the
    union of both sides, with differing blocks reported as conflicts. Only a
    base can tell "they changed it" apart from "we changed it" — pass one if
    you want one side's edits kept without being asked about every difference.

    Maps whose GUIDs share nothing are re-paired by content first, so a Save As
    still merges rather than duplicating every object.

    Raises ValueError if even that finds no common object: the two files are
    not versions of one map, and a "merge" would just stack two sets of
    geometry on top of each other. Pass allow_unrelated=True if that
    pile-everything-in behaviour is genuinely what you want.
    """
    from core.bridge import CoreBridge
    from core.native import NativeCoreError

    bridge = CoreBridge.instance()
    try:
        result = bridge.vmap_merge_open(ours_path, theirs_path, base, allow_unrelated)
    except NativeCoreError as e:
        raise ValueError(str(e)) from e
    return MergeResult(result["handle"], result, bridge)


# CLI

def main(argv=None):
    import argparse

    p = argparse.ArgumentParser(
        prog="gitvmapmerge",
        description="Merge two Source 2 .vmap files block by block.")
    p.add_argument("ours")
    p.add_argument("theirs")
    p.add_argument("-o", "--output", help="write the merged map here")
    p.add_argument("-b", "--base", help="common ancestor, for a true 3-way merge")
    p.add_argument("--primary", choices=(OURS, THEIRS),
                   help="the primary map: it wins every conflict")
    p.add_argument("--allow-unrelated", action="store_true",
                   help="proceed even if the two maps share no block identity")
    args = p.parse_args(argv)

    try:
        r = merge(args.ours, args.theirs, args.base, args.allow_unrelated)
    except ValueError as e:
        log.error("error: %s" % e)
        return 2
    print(r.summary())
    for kind, blocks in (("+", r.added), ("-", r.removed), ("~", r.changed)):
        for b in blocks:
            print("  %s %-16s %s" % (kind, b.kind, b.label))
    for c in r.conflicts:
        detail = []
        for side, digest in ((OURS, c.ours_digest), (THEIRS, c.theirs_digest)):
            detail.append("%s=%s" % (side, digest[:8] if digest else "deleted"))
        print("  ! %-16s %-40s %s  [%s]" % (c.kind, c.label, c.reason, " ".join(detail)))

    if not args.output:
        r.close()
        return 0
    try:
        if r.conflicts:
            if not args.primary:
                print("\n%d conflict(s); rerun with --primary ours|theirs to pick a side."
                      % len(r.conflicts))
                return 1
            r.resolve_all(args.primary)
            print("\nresolved %d conflict(s) in favour of %s" % (len(r.conflicts), args.primary))
        r.write(args.output)
        for b in r.orphaned:
            print("  moved to world root (its group was deleted): %s %s" % (b.kind, b.label))
        print("wrote %s (%d bytes)" % (args.output, os.path.getsize(args.output)))
        return 0
    finally:
        r.close()


if __name__ == "__main__":
    raise SystemExit(main())
