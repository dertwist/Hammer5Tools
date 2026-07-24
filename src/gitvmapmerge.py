"""Block-level merge for Source 2 .vmap files.

A .vmap is binary DMX, so git can only ever take one whole side of a conflict.
This splits a map into *blocks* — the map nodes under CMapWorld (entities,
meshes, groups, smart props, path nodes, the world itself) — keyed by the DMX
element GUID, which Hammer keeps stable across saves. Comparing per-block
digests shows which side touched what, so edits from two branches combine and
only genuine both-sides edits are reported as conflicts for the caller to
resolve by picking a primary.

Give it a common ancestor (`base`) and it is a real 3-way merge: a block only
conflicts when both sides changed it differently. Without one it falls back to
2-way union — every block present on either side survives, and blocks that
differ are conflicts.

When the two files share no GUIDs at all — a Save As, a re-import, a rebuilt
map — nodes are re-paired by content instead (identical digest first, then
class + nodeID, one-to-one) so a shared object merges rather than being added a
second time.

Two facts drive the implementation, both verified against Hammer-saved maps:

* Map-node GUIDs are stable across saves, but the GUIDs of their sub-elements
  (meshData, relayPlugData, transformPin, nodeData …) are regenerated on every
  save. Digests therefore compare values and deliberately ignore element IDs;
  comparing IDs would report every node as modified.
* Datamodel.NET's binary writer drops the DMX prefix-attribute block, which is
  where the map thumbnail and the asset-reference cache live. We copy those
  bytes back from the primary file after saving.

Typical use::

    r = merge("ours.vmap", "theirs.vmap", base="base.vmap")
    for c in r.conflicts:
        r.resolve(c.id, OURS)        # or THEIRS
    r.write("merged.vmap")
"""

import hashlib
import os
import struct

from src.dotnet import setup_keyvalues2

OURS = "ours"
THEIRS = "theirs"

# The world node is identified by its role (Root["world"]), never by GUID: it is
# the root of the block tree, and a "Save As" hands a map an all-new set of
# GUIDs. Matching it by GUID would import one map's world as a child of the
# other's, which is not a thing Hammer can load.
WORLD = "\0world"

_MAX_DEPTH = 24
_api_cache = None


def _api():
    """(Datamodel, Element, DeferredMode), loaded once."""
    global _api_cache
    if _api_cache is None:
        _api_cache = setup_keyvalues2()
    return _api_cache


# --- DMX binary-9 prefix attribute block ----------------------------------
# We only ever need each value's *size* here, never its meaning: the block is
# copied over verbatim. An unrecognised type aborts the splice, leaving the
# (valid, just thumbnail-less) file the codec wrote rather than a corrupt one.

_STRING, _BLOB, _ARRAY_BASE = 5, 6, 32
_FIXED = {2: 4, 3: 4, 4: 1, 7: 4, 8: 4, 9: 8, 10: 12,
          11: 16, 12: 16, 13: 64, 14: 1, 15: 8, 16: 12}


def _skip_value(buf, off, t):
    if t == _STRING:
        return buf.index(b"\x00", off) + 1
    if t == _BLOB:
        return off + 4 + struct.unpack_from("<i", buf, off)[0]
    if t in _FIXED:
        return off + _FIXED[t]
    if t > _ARRAY_BASE:
        count = struct.unpack_from("<i", buf, off)[0]
        off += 4
        for _ in range(count):
            off = _skip_value(buf, off, t - _ARRAY_BASE)
        return off
    raise ValueError("unsupported DMX attribute type %d" % t)


def _prefix_end(buf):
    """Offset just past the header + prefix-attribute region, or None if unparsable."""
    try:
        off = buf.index(b"\x00") + 1
        blocks = struct.unpack_from("<i", buf, off)[0]
        off += 4
        for _ in range(blocks):
            count = struct.unpack_from("<i", buf, off)[0]
            off += 4
            for _ in range(count):
                off = buf.index(b"\x00", off) + 1       # attribute name
                off = _skip_value(buf, off + 1, buf[off])
        return off
    except (ValueError, IndexError, struct.error):
        return None


def _splice_prefix(src_path, out_path):
    """Restore src's thumbnail / asset-reference block into a freshly saved file."""
    with open(src_path, "rb") as f:
        src = f.read()
    with open(out_path, "rb") as f:
        out = f.read()
    src_end, out_end = _prefix_end(src), _prefix_end(out)
    if src_end is None or out_end is None:
        return False
    with open(out_path, "wb") as f:
        f.write(src[:src_end])
        f.write(out[out_end:])
    return True


# --- blocks ----------------------------------------------------------------

def _keys(el):
    return set(str(k) for k in el.Keys)


def _classname(el, keys):
    """Entity classname, or "" for anything that is not an entity."""
    if "entity_properties" not in keys:
        return ""
    try:
        ep = el["entity_properties"]
        return str(ep["classname"]) if "classname" in _keys(ep) else ""
    except Exception:
        return ""


def _label(el, keys):
    """Human-readable name for conflict reporting."""
    cls = _classname(el, keys)
    if cls:
        try:
            ep = el["entity_properties"]
            name = str(ep["targetname"]) if "targetname" in _keys(ep) else ""
        except Exception:
            name = ""
        return "%s (%s)" % (cls, name) if name else cls
    return str(el.Name) or el.ClassName


def _value_sig(v, seen, depth):
    if v is None:
        return "~"
    kind = type(v).__name__
    if kind == "Element":
        return _element_sig(v, seen, depth + 1)
    if kind == "Byte[]":
        try:
            return "b" + hashlib.sha1(bytes(v[i] for i in range(v.Length))).hexdigest()
        except Exception:
            return "b?"
    if kind.endswith("Array"):
        return "[" + ",".join(_value_sig(x, seen, depth + 1) for x in v) + "]"
    return str(v)


def _element_sig(el, seen, depth):
    """Value signature of an element subtree, blind to element GUIDs.

    `children` is skipped: it is the block-tree link, merged separately, so a
    group is only "modified" when its own attributes change — not when someone
    adds an entity to it.
    """
    if el is None:
        return "~"
    key = str(el.ID)
    if depth > _MAX_DEPTH or key in seen:
        return "*"
    seen = seen | {key}
    parts = [el.ClassName, str(el.Name) or ""]
    for k in sorted(_keys(el)):
        if k == "children":
            continue
        parts.append(k + "=" + _value_sig(el[k], seen, depth))
    return "{" + "|".join(parts) + "}"


class Block:
    """One map node, identified by its (save-stable) DMX element GUID."""

    __slots__ = ("id", "kind", "label", "digest", "ident", "child_ids", "element")

    def __repr__(self):
        return "<Block %s %s %s>" % (self.kind, self.label, self.id[:8])


def _scan(dm):
    blocks = {}

    def visit(el, bid):
        keys = _keys(el)
        kids = [c for c in el["children"] if c is not None] if "children" in keys else []
        b = Block()
        b.id, b.kind, b.element = bid, el.ClassName, el
        b.label = _label(el, keys)
        # Fallback identity for maps whose GUIDs were regenerated. Class is part
        # of the key because Hammer reuses nodeIDs: nodeID 10 can be a mesh in
        # one map and a prop_static in the other.
        b.ident = ("n:%s:%s:%s" % (el.ClassName, _classname(el, keys), el["nodeID"])
                   if "nodeID" in keys else None)
        b.child_ids = [str(c.ID) for c in kids]
        b.digest = hashlib.sha1(
            _element_sig(el, frozenset(), 0).encode("utf-8", "replace")).hexdigest()
        blocks[bid] = b
        for c in kids:
            visit(c, str(c.ID))

    visit(dm.Root["world"], WORLD)
    return blocks


def _unique(blocks, ids, key):
    """key -> block id, dropping any key more than one block claims."""
    idx, dupes = {}, set()
    for i in ids:
        k = key(blocks[i])
        if k is None:
            continue
        if k in idx:
            dupes.add(k)
        idx[k] = i
    for k in dupes:
        del idx[k]
    return idx


def _realign(ours, theirs):
    """Stamp ours' GUIDs onto theirs' nodes wherever the two are the same object.

    Only for maps whose GUIDs have nothing in common — a Save As, a re-import, a
    rebuilt map hands every node a fresh one. Without this every node looks new
    and the "merge" is two copies of the map stacked in one file. Matching is
    strongest-first and strictly one-to-one: identical content, then class +
    nodeID (Hammer's per-map counter, which survives ordinary edits). Anything
    ambiguous on either side is left alone and stays a genuine addition.
    """
    o_left = set(ours.blocks) - {WORLD}
    t_left = set(theirs.blocks) - {WORLD}
    pairs = {}
    for key in (lambda b: "d:" + b.digest, lambda b: b.ident):
        o_idx = _unique(ours.blocks, o_left, key)
        t_idx = _unique(theirs.blocks, t_left, key)
        for k, tid in t_idx.items():
            oid = o_idx.get(k)
            if oid is None:
                continue
            pairs[tid] = oid
            o_left.discard(oid)
            t_left.discard(tid)
    for tid, oid in pairs.items():
        theirs.blocks[tid].element.ID = ours.blocks[oid].element.ID
    return pairs


class VmapDoc:
    """A loaded .vmap and its blocks."""

    def __init__(self, path):
        Datamodel, _, DeferredMode = _api()
        self.path = path
        # Disabled, not Automatic: the merge reads every attribute anyway and
        # imported elements must not depend on a stream we are about to close.
        self.dm = Datamodel.Load(path, DeferredMode.Disabled)
        self.blocks = _scan(self.dm)

    @property
    def world_id(self):
        return WORLD

    def close(self):
        if self.dm is not None:
            self.dm.Dispose()
            self.dm = None


# --- merge -----------------------------------------------------------------

class Conflict:
    """A block both sides changed differently. Resolve by picking OURS or THEIRS."""

    __slots__ = ("id", "kind", "label", "reason", "ours", "theirs")

    def __repr__(self):
        return "<Conflict %s %s: %s>" % (self.kind, self.label, self.reason)


def _digest_of(block):
    return block.digest if block is not None else None


class MergeResult:
    def __init__(self, ours, theirs, base):
        self.ours, self.theirs, self.base = ours, theirs, base
        self.decisions = {}     # block id -> OURS | THEIRS
        self.conflicts = []
        self.added = []         # blocks taken from theirs that we did not have
        self.removed = []       # blocks theirs deleted and we had not touched
        self.changed = []       # blocks theirs modified and we had not touched
        self.orphaned = []      # survivors whose parent group was deleted, re-homed
        self.shared = set()     # block ids both sides have — the merge's footing
        self.realigned = {}     # theirs id -> ours id, paired by content not GUID
        self._choices = {}

    # -- resolution --------------------------------------------------------
    def resolve(self, block_id, side):
        if side not in (OURS, THEIRS):
            raise ValueError("side must be OURS or THEIRS")
        self._choices[block_id] = side

    def resolve_all(self, side):
        """Pick one side for every remaining conflict — the 'primary vmap' choice."""
        for c in self.conflicts:
            self._choices.setdefault(c.id, side)

    @property
    def unresolved(self):
        return [c for c in self.conflicts if c.id not in self._choices]

    def side_for(self, block_id):
        return self._choices.get(block_id) or self.decisions.get(block_id, OURS)

    def summary(self):
        return ("%d blocks ours / %d theirs%s — %d added, %d removed, %d changed, "
                "%d conflicts" % (len(self.ours.blocks), len(self.theirs.blocks),
                                  " (%d paired by content)" % len(self.realigned)
                                  if self.realigned else "",
                                  len(self.added), len(self.removed),
                                  len(self.changed), len(self.conflicts)))

    def close(self):
        """Release the loaded maps — needed before deleting temp inputs."""
        for doc in (self.ours, self.theirs, self.base):
            if doc is not None:
                doc.close()

    # -- output ------------------------------------------------------------
    def _alive(self):
        alive = {}
        for bid in set(self.ours.blocks) | set(self.theirs.blocks):
            src = self.theirs if self.side_for(bid) == THEIRS else self.ours
            block = src.blocks.get(bid)
            if block is not None:
                alive[bid] = block
        return alive

    def write(self, out_path):
        """Apply the merge onto our datamodel and save it to out_path."""
        if self.unresolved:
            raise ValueError("%d unresolved conflict(s); call resolve()/resolve_all() "
                             "first" % len(self.unresolved))
        Datamodel, _, _dm = _api()
        import System

        alive = self._alive()
        ours_dm = self.ours.dm

        # Detach every incoming node's children before importing: we rebuild all
        # children arrays below, and a recursive import that dragged whole
        # subtrees along would clobber blocks we decided to keep.
        for block in self.theirs.blocks.values():
            if "children" in _keys(block.element):
                block.element["children"].Clear()

        recursive = Datamodel.ImportRecursionMode.Recursive
        overwrite = Datamodel.ImportOverwriteMode.All
        elements = {}
        for bid, block in alive.items():
            if bid in self.theirs.blocks and block is self.theirs.blocks[bid]:
                elements[bid] = ours_dm.ImportElement(block.element, recursive, overwrite)
            else:
                elements[bid] = block.element

        # Rebuild the node tree from merged membership. Order follows ours, with
        # theirs' additions appended.
        # ponytail: child order is not itself 3-way merged — only relevant if two
        # sides reorder the same CMapPath's nodes; merge those by hand if it bites.
        placed = set()
        world_id = self.ours.world_id

        def rebuild(bid):
            el = elements[bid]
            if "children" not in _keys(el):
                return
            ours_kids = self.ours.blocks[bid].child_ids if bid in self.ours.blocks else []
            their_kids = self.theirs.blocks[bid].child_ids if bid in self.theirs.blocks else []
            order = [i for i in ours_kids if i in alive and i not in placed]
            seen = set(order)
            for i in their_kids:
                if i in alive and i not in placed and i not in seen:
                    order.append(i)
                    seen.add(i)
            placed.update(order)
            arr = el["children"]
            arr.Clear()
            for i in order:
                arr.Add(elements[i])
            for i in order:
                rebuild(i)

        rebuild(world_id)

        # If one side deleted a group the other side was working inside, the
        # surviving children have nowhere to hang. Re-home them on the world
        # rather than drop somebody's work on the floor.
        world_children = elements[world_id]["children"]
        for bid in [i for i in alive if i != world_id and i not in placed]:
            if bid in placed:               # picked up by an earlier re-home
                continue
            placed.add(bid)
            world_children.Add(elements[bid])
            rebuild(bid)
            self.orphaned.append(alive[bid])

        ours_dm.Root["world"] = elements[world_id]

        # Both sides allocate nodeIDs from the same counter, so imported nodes
        # routinely collide with ours. Hand collisions a fresh id.
        used = set()
        for bid, el in elements.items():
            if "nodeID" not in _keys(el):
                continue
            nid = int(el["nodeID"])
            if nid in used:
                nid = max(used) + 1
                el["nodeID"] = System.Int32(nid)
            used.add(nid)

        ours_dm.Save(out_path, ours_dm.Encoding, ours_dm.EncodingVersion)
        # The codec drops the thumbnail / asset-reference cache; put it back.
        _splice_prefix(self.ours.path, out_path)
        return out_path


def merge(ours_path, theirs_path, base=None, allow_unrelated=False):
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
    result = MergeResult(VmapDoc(ours_path), VmapDoc(theirs_path),
                         VmapDoc(base) if base else None)
    ours, theirs, anc = result.ours, result.theirs, result.base

    result.shared = (set(ours.blocks) & set(theirs.blocks)) - {WORLD}
    if not result.shared and len(ours.blocks) > 1 and len(theirs.blocks) > 1:
        # No GUID footing at all — recognise the same objects by content so they
        # merge instead of being imported alongside the copies we already have.
        result.realigned = _realign(ours, theirs)
        if result.realigned:
            theirs.blocks = _scan(theirs.dm)
            result.shared = (set(ours.blocks) & set(theirs.blocks)) - {WORLD}
    if not result.shared and len(ours.blocks) > 1 and len(theirs.blocks) > 1 \
            and not allow_unrelated:
        raise ValueError(
            "%s and %s share no block identity (0 of %d/%d nodes) and no node "
            "pairs by content either, so they are not two versions of the same "
            "map. Merging them would just stack both maps' contents in one file. "
            "Pass allow_unrelated=True (CLI: --allow-unrelated) if that is what "
            "you want."
            % (os.path.basename(ours_path), os.path.basename(theirs_path),
               len(ours.blocks) - 1, len(theirs.blocks) - 1))

    for bid in set(ours.blocks) | set(theirs.blocks):
        o, t = ours.blocks.get(bid), theirs.blocks.get(bid)
        od, td = _digest_of(o), _digest_of(t)

        if anc is None:
            if o is None:
                decision, note = THEIRS, "added"
            elif t is None or od == td:
                decision, note = OURS, None
            else:
                decision, note = None, "both sides differ (no common ancestor)"
        else:
            bd = _digest_of(anc.blocks.get(bid))
            if td == bd or od == td:
                decision, note = OURS, None          # only we changed, or same edit
            elif od == bd:
                decision = THEIRS                    # only they changed
                note = "added" if o is None else ("removed" if t is None else "changed")
            elif o is None or t is None:
                decision, note = None, "deleted on one side, changed on the other"
            else:
                decision, note = None, "both sides changed it"

        if decision is None:
            c = Conflict()
            c.id, c.reason = bid, note
            src = o or t
            c.kind, c.label, c.ours, c.theirs = src.kind, src.label, o, t
            result.conflicts.append(c)
        else:
            result.decisions[bid] = decision
            if note == "added":
                result.added.append(t)
            elif note == "removed":
                result.removed.append(o)
            elif note == "changed":
                result.changed.append(t)

    result.conflicts.sort(key=lambda c: (c.kind, c.label))
    return result


# --- CLI -------------------------------------------------------------------

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
        print("error: %s" % e)
        return 2
    print(r.summary())
    for kind, blocks in (("+", r.added), ("-", r.removed), ("~", r.changed)):
        for b in blocks:
            print("  %s %-16s %s" % (kind, b.kind, b.label))
    for c in r.conflicts:
        detail = []
        for side, b in ((OURS, c.ours), (THEIRS, c.theirs)):
            detail.append("%s=%s" % (side, b.digest[:8] if b else "deleted"))
        print("  ! %-16s %-40s %s  [%s]" % (c.kind, c.label, c.reason, " ".join(detail)))

    if not args.output:
        return 0
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


if __name__ == "__main__":
    raise SystemExit(main())
