"""Phase 1: collapse duplicate materials onto one name.

Every group here points at an identical texture set, so the winner renders what
the losers rendered - except where the group differed only in g_vColorTint, which
you asked to collapse too. The winner keeps its own tint (it is the most-used
member, so that is the smallest total change), and the losers are deleted after
every reference to them has been repointed.

  python r2_merge.py            report
  python r2_merge.py --apply    do it
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
M = json.load(open(os.path.join(HERE, "r1_map.json")))
MERGE = M["merge"]
APPLY = "--apply" in sys.argv

inv = collections.defaultdict(list)
for loser, win in MERGE.items():
    inv[win].append(loser)

print(f"{len(MERGE)} materials merge into {len(inv)}")
for win, losers in sorted(inv.items(), key=lambda kv: -len(kv[1])):
    print(f"\n  {win}")
    for l in sorted(losers):
        exists = "" if os.path.exists(lib.abspath(l)) else "   [ALREADY GONE]"
        print(f"      <- {l}{exists}")

missing_win = [w for w in inv if not os.path.exists(lib.abspath(w))]
if missing_win:
    raise SystemExit(f"ABORT: {len(missing_win)} merge winners do not exist: {missing_win}")

if not APPLY:
    print("\n(report only - pass --apply)")
    raise SystemExit(0)

from src.forms.asset_manager.reference_updater import ReferenceUpdater

print("\nrewriting references...")
mod = ReferenceUpdater(lib.ROOT).update_references_batch(MERGE)
print(f"  {len(mod)} files rewritten")
for p in sorted(mod):
    print(f"      {lib.rel(p)}")

# Nothing is removed until every reference to it is gone. This is the check that
# was missing when the last pass deleted 277 still-referenced textures.
print("\nverifying no live references to the merged-away materials...")
still = []
for p in lib.scannable():
    txt = lib.read_text(p)
    for l in MERGE:
        if l in txt.lower():
            still.append((lib.rel(p), l))
import re
PAT = re.compile("|".join(re.escape(l) for l in MERGE).encode(), re.I)
for sub in ("maps", "smartprops", "particles", "particels", "lighting", "postprocess"):
    d = os.path.join(lib.ROOT, sub)
    if not os.path.isdir(d):
        continue
    for dp, _, fns in os.walk(d):
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                hits = PAT.findall(open(p, "rb").read())
            except OSError:
                continue
            if hits:
                still.append((lib.rel(p), f"{len(hits)} binary hits"))
if still:
    for s in still[:20]:
        print("   STILL REFERENCED:", s)
    raise SystemExit(f"ABORT: {len(still)} live references remain - nothing deleted")
print("  clean")

n = 0
for l in MERGE:
    p = lib.abspath(l)
    if os.path.exists(p):
        os.remove(p)
        n += 1
print(f"\ndeleted {n} merged-away materials")
