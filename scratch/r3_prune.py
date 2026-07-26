"""Phase 2: delete materials nothing can reach.

Each candidate is checked live rather than trusted from the survey - a vmdl
remap, a binary vmap/vsmart, or another vmat pointing at it disqualifies it.

  python r3_prune.py            report
  python r3_prune.py --apply    do it
"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "r1_map.json")))
APPLY = "--apply" in sys.argv

cand = [c for c in M["dead_mat"] if os.path.exists(lib.abspath(c))]
gone = [c for c in M["dead_mat"] if not os.path.exists(lib.abspath(c))]
print(f"{len(cand)} candidates present, {len(gone)} already gone")

# Re-derive reachability instead of trusting r1_map: phase 1 rewrote references,
# so a material that looked dead during the survey may have gained one.
live, _ = lib.live_vmats()
alive = [c for c in cand if c in live]
if alive:
    print(f"\n{len(alive)} are reachable after all - keeping:")
    for c in alive:
        print(f"    {c}")
cand = [c for c in cand if c not in live]

PAT = re.compile("|".join(re.escape(c) for c in cand).encode(), re.I) if cand else None
hits = {}
if PAT:
    for sub in ("maps", "smartprops", "models", "materials", "particles", "particels",
                "lighting", "postprocess", "scripts"):
        d = os.path.join(lib.ROOT, sub)
        if not os.path.isdir(d):
            continue
        for dp, _, fns in os.walk(d):
            for fn in fns:
                p = os.path.join(dp, fn)
                if lib.rel(p) in cand:
                    continue                      # a file referencing itself is fine
                try:
                    found = PAT.findall(open(p, "rb").read())
                except OSError:
                    continue
                if found:
                    hits[lib.rel(p)] = len(found)

print(f"\n{len(cand)} unreachable materials to delete:")
for c in sorted(cand):
    print(f"    {c}")

if hits:
    print(f"\nABORT: {sum(hits.values())} references found in {len(hits)} files")
    for f, n in sorted(hits.items(), key=lambda kv: -kv[1])[:20]:
        print(f"    {n:5}  {f}")
    raise SystemExit(1)
print("\nno file references any of them")

if not APPLY:
    print("(report only - pass --apply)")
    raise SystemExit(0)

n = 0
for c in cand:
    os.remove(lib.abspath(c))
    n += 1
print(f"\ndeleted {n} materials")
