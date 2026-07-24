"""
Checks for the .vmap block merge.
Run:  python dev/test_gitvmapmerge.py [real_a.vmap real_b.vmap]

Synthesises ours/theirs variants from a bundled map, so the test needs no
external fixtures. Pass two real Hammer re-saves of the same map on the command
line and it also verifies the property this all rests on: node GUIDs stay
stable across saves while sub-element GUIDs churn.
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gitvmapmerge import (
    OURS, THEIRS, WORLD, VmapDoc, merge, _api, _element_sig, _prefix_end,
    _splice_prefix,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "Hammer5Tools", "Presets", "hammer5tools",
                       "content", "maps", "blockout_zoo.vmap")

_failed = []


def check(name, got, want):
    ok(name, got == want, "got=%r want=%r" % (got, want))


def ok(name, cond, detail=""):
    print("[%s] %s%s" % ("PASS" if cond else "FAIL", name, (" " + detail) if detail else ""))
    if not cond:
        _failed.append(name)


def raises(fn):
    """Name of the exception fn() raised, or None."""
    try:
        fn()
    except Exception as e:
        return type(e).__name__
    return None


def save_variant(src, out, mutate):
    """Write a copy of src with mutate() applied, the way Hammer would re-save it."""
    doc = VmapDoc(src)
    mutate(doc)
    doc.dm.Save(out, doc.dm.Encoding, doc.dm.EncodingVersion)
    _splice_prefix(src, out)
    doc.close()
    return out


def move(block, dx):
    """Nudge a node's origin — the most ordinary edit there is."""
    from System.Numerics import Vector3
    o = block.element["origin"]
    block.element["origin"] = Vector3(o.X + dx, o.Y, o.Z)


def top_level(doc):
    return doc.blocks[doc.world_id].child_ids


def elem_keys(el):
    return [str(k) for k in el.Keys]


tmp = tempfile.mkdtemp(prefix="vmapmerge_")
base_path = os.path.join(tmp, "base.vmap")
shutil.copyfile(FIXTURE, base_path)

_api()                      # boot pythonnet before anything imports System
import System               # noqa: E402
import Datamodel as DM      # noqa: E402
from System.Numerics import Vector3   # noqa: E402

base = VmapDoc(base_path)
kids = top_level(base)
ok("fixture has enough blocks", len(kids) >= 5, "(%d top-level)" % len(kids))
movable = [i for i in kids if "origin" in elem_keys(base.blocks[i].element)]
ok("fixture has movable nodes", len(movable) >= 4, "(%d)" % len(movable))
A, B, C, D = movable[:4]
n_base, base_ids = len(base.blocks), set(base.blocks)
base_digests = {i: base.blocks[i].digest for i in (A, B, C, D)}
base.close()

# --- the invariant everything rests on -------------------------------------
# Hammer regenerates sub-element GUIDs (meshData, transformPin, …) on every
# save. Digests must not notice that, but must still notice a real edit.
doc = VmapDoc(base_path)
target = next(b for b in doc.blocks.values()
              if any(type(b.element[k]).__name__ == "Element" for k in elem_keys(b.element)))
sub_key = next(k for k in elem_keys(target.element)
               if type(target.element[k]).__name__ == "Element")
before = _element_sig(target.element, frozenset(), 0)
target.element[sub_key].ID = System.Guid.NewGuid()
ok("digest ignores sub-element GUID churn",
   _element_sig(target.element, frozenset(), 0) == before,
   "(%s.%s)" % (target.kind, sub_key))
move(target, 8.0)
ok("digest notices a moved node",
   _element_sig(target.element, frozenset(), 0) != before)
doc.close()


# --- 3-way merge: disjoint edits combine without asking --------------------
def mutate_ours(d):
    move(d.blocks[A], 64.0)


def mutate_theirs(d):
    move(d.blocks[B], -64.0)
    world_kids = d.blocks[d.world_id].element["children"]
    for i, c in enumerate(world_kids):
        if c is not None and str(c.ID) == C:
            world_kids.RemoveAt(i)
            break
    # a brand-new node, the way a second mapper would add one
    _, Element, _unused = _api()
    el = Element(d.dm, "merge_test_node", None, "CMapEntity")
    el["nodeID"] = System.Int32(9999)
    el["referenceID"] = System.UInt64(1234567890123456789)
    el["children"] = DM.ElementArray()
    el["origin"] = Vector3(512.0, 0.0, 0.0)
    ep = Element(d.dm, "", None, "EditGameClassProps")
    ep["classname"] = "info_player_terrorist"
    el["entity_properties"] = ep
    world_kids.Add(el)


ours_path = save_variant(base_path, os.path.join(tmp, "ours.vmap"), mutate_ours)
theirs_path = save_variant(base_path, os.path.join(tmp, "theirs.vmap"), mutate_theirs)

r = merge(ours_path, theirs_path, base=base_path)
print("  3-way:", r.summary())
check("3-way has no conflicts", len(r.conflicts), 0)
check("3-way sees 1 added", len(r.added), 1)
check("3-way sees 1 removed", len(r.removed), 1)
check("3-way sees 1 changed", len(r.changed), 1)

out_path = r.write(os.path.join(tmp, "merged.vmap"))
merged = VmapDoc(out_path)
mk = top_level(merged)

ok("our edit survived", merged.blocks[A].digest != base_digests[A])
ok("their edit survived", merged.blocks[B].digest != base_digests[B])
ok("their deletion applied", C not in merged.blocks)
ok("untouched block untouched", merged.blocks[D].digest == base_digests[D])
check("their new node imported",
      len([i for i in mk if merged.blocks[i].label == "info_player_terrorist"]), 1)
ok("no duplicate placement", len(mk) == len(set(mk)))
nids = [int(b.element["nodeID"]) for b in merged.blocks.values()
        if "nodeID" in elem_keys(b.element)]
ok("nodeIDs are unique", len(nids) == len(set(nids)), "(%d nodes)" % len(nids))
merged.close()

# --- the thumbnail / asset-reference block must survive the round trip -----
with open(base_path, "rb") as f:
    base_bytes = f.read()
with open(out_path, "rb") as f:
    out_bytes = f.read()
be, oe = _prefix_end(base_bytes), _prefix_end(out_bytes)
ok("prefix block parsed", be is not None and oe is not None, "(%s / %s)" % (be, oe))
ok("prefix block preserved", be and base_bytes[:be] == out_bytes[:oe],
   "(%d bytes)" % (be or 0))

# --- conflicts: both sides move the same node ------------------------------
c_ours = save_variant(base_path, os.path.join(tmp, "c_ours.vmap"),
                      lambda d: move(d.blocks[D], 32.0))
c_theirs = save_variant(base_path, os.path.join(tmp, "c_theirs.vmap"),
                        lambda d: move(d.blocks[D], -32.0))
our_digest = VmapDoc(c_ours).blocks[D].digest
their_digest = VmapDoc(c_theirs).blocks[D].digest

r2 = merge(c_ours, c_theirs, base=base_path)
check("competing edits conflict", len(r2.conflicts), 1)
check("conflict names the block", r2.conflicts[0].id, D)
check("write refuses while unresolved",
      raises(lambda: r2.write(os.path.join(tmp, "nope.vmap"))), "ValueError")

r2.resolve_all(THEIRS)
check("nothing left unresolved", len(r2.unresolved), 0)
p_theirs = r2.write(os.path.join(tmp, "primary_theirs.vmap"))
ok("primary=theirs wins the conflict",
   VmapDoc(p_theirs).blocks[D].digest == their_digest)

r3 = merge(c_ours, c_theirs, base=base_path)
r3.resolve_all(OURS)
p_ours = r3.write(os.path.join(tmp, "primary_ours.vmap"))
ok("primary=ours wins the conflict",
   VmapDoc(p_ours).blocks[D].digest == our_digest)

# --- one side deletes a group the other side worked inside -----------------
grp = next((b for b in VmapDoc(base_path).blocks.values() if b.child_ids and
            b.kind != "CMapWorld"), None)
if grp is None:
    print("[SKIP] fixture has no nested group; orphan re-homing not exercised")
else:
    GID, CHILD = grp.id, grp.child_ids[0]

    def drop_group(d):
        world_kids = d.blocks[d.world_id].element["children"]
        for i, c in enumerate(world_kids):
            if c is not None and str(c.ID) == GID:
                world_kids.RemoveAt(i)
                break

    g_ours = save_variant(base_path, os.path.join(tmp, "g_ours.vmap"),
                          lambda d: move(d.blocks[CHILD], 16.0))
    g_theirs = save_variant(base_path, os.path.join(tmp, "g_theirs.vmap"), drop_group)

    r5 = merge(g_ours, g_theirs, base=base_path)
    r5.resolve_all(OURS)
    g_out = VmapDoc(r5.write(os.path.join(tmp, "orphan.vmap")))
    ok("edited child survives its group's deletion", CHILD in g_out.blocks,
       "(%s)" % grp.kind)
    ok("orphan re-homed onto the world", CHILD in top_level(g_out))
    ok("re-homing is reported, not silent", any(b.id == CHILD for b in r5.orphaned))
    g_out.close()

# --- 2-way (no ancestor) is union + conflicts ------------------------------
r4 = merge(ours_path, theirs_path)
print("  2-way:", r4.summary())
check("2-way still adds theirs' new node", len(r4.added), 1)
ok("2-way flags divergent blocks as conflicts", len(r4.conflicts) >= 2,
   "(%d)" % len(r4.conflicts))
check("2-way never deletes (no ancestor to prove intent)", r4.decisions.get(C), OURS)

# --- the three primary-vmap cases, spelled out -----------------------------
# file 1 = ours (secondary), file 2 = theirs (primary).
def case_f1(d):
    move(d.blocks[A], 40.0)     # case 1: changed in file 1 only
    move(d.blocks[B], 40.0)     # case 2: changed in both


def case_f2(d):
    move(d.blocks[B], -40.0)
    move(d.blocks[C], -40.0)    # case 3: changed in file 2 only


f1 = save_variant(base_path, os.path.join(tmp, "case_f1.vmap"), case_f1)
f2 = save_variant(base_path, os.path.join(tmp, "case_f2.vmap"), case_f2)
d1, d2 = VmapDoc(f1), VmapDoc(f2)

rc = merge(f1, f2, base=base_path)
check("only the both-sides edit is a conflict", [c.id for c in rc.conflicts], [B])
rc.resolve_all(THEIRS)                      # file 2 is the primary map
dc = VmapDoc(rc.write(os.path.join(tmp, "cases.vmap")))
check("case 1: changed in file 1 only -> file 1's version kept",
      dc.blocks[A].digest, d1.blocks[A].digest)
check("case 2: changed in both -> primary (file 2) wins",
      dc.blocks[B].digest, d2.blocks[B].digest)
check("case 3: changed in file 2 only -> file 2's version kept",
      dc.blocks[C].digest, d2.blocks[C].digest)
check("untouched block stays untouched", dc.blocks[D].digest, base_digests[D])
check("nothing duplicated", len(dc.blocks), n_base)
for d in (dc, d1, d2):
    d.close()


# --- a Save As regenerates every GUID --------------------------------------
# Regression: the world used to be matched by GUID like any other block, so a
# map with fresh GUIDs got its CMapWorld imported as a *child* of ours. And
# without content pairing every node looked new, so the merge stacked a second
# copy of the whole map on top of the first.
def reguid(d):
    for b in list(d.blocks.values()):
        b.element.ID = System.Guid.NewGuid()


def reguid_moved(d):
    reguid(d)
    move(d.blocks[A], 96.0)


def alienate(d):
    """Fresh GUIDs *and* fresh nodeIDs — nothing left to recognise it by."""
    reguid(d)
    for b in list(d.blocks.values()):
        if "nodeID" in elem_keys(b.element):
            b.element["nodeID"] = System.Int32(int(b.element["nodeID"]) + 1000)


saveas = save_variant(base_path, os.path.join(tmp, "saveas.vmap"), reguid)
sa = VmapDoc(saveas)
ok("save-as shares no GUIDs with the original",
   len(set(sa.blocks) - {WORLD}) > 0 and
   not (set(sa.blocks) & set(VmapDoc(base_path).blocks)) - {WORLD})
sa.close()

r6 = merge(base_path, saveas)
print("  save-as:", r6.summary())
check("every re-GUIDed node pairs by content", len(r6.realigned), n_base - 1)
d6 = VmapDoc(r6.write(os.path.join(tmp, "saveas_merged.vmap")))
check("a re-GUIDed map merges without duplicating anything", len(d6.blocks), n_base)
ok("merged map keeps our GUIDs", set(d6.blocks) == base_ids)
d6.close()

saveas_moved = save_variant(base_path, os.path.join(tmp, "saveas_moved.vmap"),
                            reguid_moved)
r7 = merge(base_path, saveas_moved)
check("a moved node still pairs, and still conflicts",
      [c.id for c in r7.conflicts], [A])
want = r7.conflicts[0].theirs.digest
r7.resolve_all(THEIRS)
d7 = VmapDoc(r7.write(os.path.join(tmp, "saveas_moved_merged.vmap")))
check("primary's version of the paired node won", d7.blocks[A].digest, want)
check("the changed node was not duplicated either", len(d7.blocks), n_base)
d7.close()

alien = save_variant(base_path, os.path.join(tmp, "alien.vmap"), alienate)
check("unrelated maps are refused, not silently stacked",
      raises(lambda: merge(base_path, alien)), "ValueError")

r8 = merge(base_path, alien, allow_unrelated=True)
r8.resolve_all(OURS)
u_out = VmapDoc(r8.write(os.path.join(tmp, "unrelated.vmap")))
nested = [c.ClassName for c in u_out.dm.Root["world"]["children"]
          if c is not None and c.ClassName == "CMapWorld"]
check("no CMapWorld nested inside the world", nested, [])
check("merged map has exactly one world", u_out.blocks[WORLD].kind, "CMapWorld")
u_out.close()

# --- the git conflict path behind the sync button --------------------------
# While a merge is unresolved git keeps all three versions in the index:
# stage 1 base, 2 ours, 3 theirs. That is what ConflictDialog._merge_vmap reads.
def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


gitrepo = os.path.join(tmp, "repo")
os.makedirs(gitrepo)
if git(gitrepo, "init", "-q", "-b", "main").returncode != 0:
    print("[SKIP] git unavailable; index-stage path not exercised")
else:
    from src.git_sync.backend import GitRepo

    git(gitrepo, "config", "user.email", "t@example.com")
    git(gitrepo, "config", "user.name", "test")
    target = os.path.join(gitrepo, "map.vmap")
    shutil.copyfile(base_path, target)
    git(gitrepo, "add", "map.vmap")
    git(gitrepo, "commit", "-qm", "base")
    git(gitrepo, "checkout", "-qb", "other")
    save_variant(base_path, target, case_f2)          # theirs
    git(gitrepo, "commit", "-qam", "theirs")
    git(gitrepo, "checkout", "-q", "main")
    save_variant(base_path, target, case_f1)          # ours
    git(gitrepo, "commit", "-qam", "ours")
    ok("git merge conflicts on the map",
       git(gitrepo, "merge", "--no-edit", "other").returncode != 0)

    gr = GitRepo(gitrepo)
    check("git reports the map as conflicted", gr.conflicts(), ["map.vmap"])
    stages = {}
    for stage, side in ((1, "base"), (2, "ours"), (3, "theirs")):
        blob = gr.show_stage(stage, "map.vmap")
        if blob:
            stages[side] = os.path.join(tmp, "stage_%s.vmap" % side)
            with open(stages[side], "wb") as f:
                f.write(blob)
    check("all three stages read back", sorted(stages), ["base", "ours", "theirs"])

    rg = merge(stages["ours"], stages["theirs"], stages["base"])
    check("index-stage merge finds the same one conflict",
          [c.id for c in rg.conflicts], [B])
    rg.resolve_all(THEIRS)
    rg.write(target)
    rg.close()
    git(gitrepo, "add", "--", "map.vmap")
    check("the file is no longer conflicted", gr.conflicts(), [])
    dg = VmapDoc(target)
    check("merged work-tree map has no duplicates", len(dg.blocks), n_base)
    check("primary won the both-sides edit", dg.blocks[B].digest, d2.blocks[B].digest)
    dg.close()

# --- optional: real Hammer re-saves ----------------------------------------
real = [p for p in sys.argv[1:] if os.path.isfile(p)]
if len(real) == 2:
    print("\n-- real Hammer saves --")
    ra, rb = VmapDoc(real[0]), VmapDoc(real[1])
    shared = set(ra.blocks) & set(rb.blocks)
    ok("node GUIDs stable across Hammer saves", len(shared) > 0,
       "(%d shared of %d/%d)" % (len(shared), len(ra.blocks), len(rb.blocks)))
    same = [i for i in shared if ra.blocks[i].digest == rb.blocks[i].digest]
    ok("untouched blocks digest identically", len(same) > 0,
       "(%d of %d shared unchanged)" % (len(same), len(shared)))
    ra.close()
    rb.close()

shutil.rmtree(tmp, ignore_errors=True)
print(("\n%d failed" % len(_failed)) if _failed else "\nall passed")
sys.exit(1 if _failed else 0)
