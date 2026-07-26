"""Phase 3+4: move into the packed layout and repoint every reference.

One commit, not two: a tree with the files moved but the references still
pointing at the old paths is broken, so there is nothing useful to revert to
between the two halves.

  python r4_move.py            report
  python r4_move.py --apply    do it
"""
import os, re, sys, json, shutil, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
M = json.load(open(os.path.join(HERE, "r1_map.json")))
APPLY = "--apply" in sys.argv

MESHREF = re.compile(r'filename\s*=\s*"([^"]+)"')
renames = {}                                   # old rel -> new rel, everything

# --- vmdl + the meshes it names ---------------------------------------------
for mdl, dest_dir in M["folder"].items():
    renames[mdl] = f"{dest_dir}/{os.path.basename(mdl)}"
    for ref in MESHREF.findall(lib.read_text(lib.abspath(mdl))):
        r = ref.replace("\\", "/").lower()
        if not r.lower().endswith((".fbx", ".dmx", ".obj")):
            continue
        if not os.path.exists(lib.abspath(r)):
            print(f"  WARN mesh missing: {r}  (in {mdl})")
            continue
        renames[r] = f"{dest_dir}/{os.path.basename(r)}"

# --- vmat + tga -------------------------------------------------------------
renames.update(M["mat_dest"])
renames.update(M["tex_dest"])

# --- .txt vtex sidecars ride along with their texture, renamed to match ------
sidecars = {}
for old, new in list(M["tex_dest"].items()):
    o = os.path.splitext(lib.abspath(old))[0] + ".txt"
    if os.path.exists(o):
        sidecars[lib.rel(o)] = os.path.splitext(new)[0] + ".txt"
renames.update(sidecars)

# --- sanity -----------------------------------------------------------------
missing = [o for o in renames if not os.path.exists(lib.abspath(o))]
dests = collections.Counter(v.lower() for v in renames.values())
clash = {k: v for k, v in dests.items() if v > 1}

by_ext = collections.Counter(os.path.splitext(o)[1].lower() for o in renames)
print(f"{len(renames)} files to move")
for e, n in sorted(by_ext.items(), key=lambda kv: -kv[1]):
    print(f"   {n:5}  {e}")
print(f"\n{len(sidecars)} .txt vtex sidecars ride along")
print(f"{len(set(v.rsplit('/', 1)[0] for v in renames.values()))} destination folders")

if missing:
    print(f"\nABORT: {len(missing)} sources do not exist")
    for m in missing[:20]:
        print("   ", m)
    raise SystemExit(1)
if clash:
    print(f"\nABORT: {len(clash)} destination collisions")
    for d, n in list(clash.items())[:20]:
        print(f"   {n}x {d}")
        for o, v in renames.items():
            if v.lower() == d:
                print(f"        <- {o}")
    raise SystemExit(1)
print("\nno missing sources, no destination collisions")

# Anything left behind in thirdparty that is not a frozen rock or an already
# unreferenced library texture would be a file the map forgot about.
left = []
for dp, _, fns in os.walk(os.path.join(lib.ROOT, "materials", "firewatch", "thirdparty")):
    for fn in fns:
        r = lib.rel(os.path.join(dp, fn))
        if r in renames or r in M["frozen_tex"] or r in M["frozen_mats"]:
            continue
        if os.path.splitext(r)[0] + ".tga" in M["frozen_tex"]:
            continue                                    # frozen rock's .txt
        left.append(r)
kept_lib = [r for r in left if "/_library/" in r or "/decals/" in r]
orphan = [r for r in left if r not in kept_lib]
print(f"\nstaying behind: {len(kept_lib)} in _library//decals, {len(orphan)} elsewhere")
for r in sorted(orphan)[:40]:
    print("    ", r)
if len(orphan) > 40:
    print(f"     ... {len(orphan) - 40} more")

if not APPLY:
    json.dump(renames, open(os.path.join(HERE, "r4_renames.json"), "w"), indent=1)
    print("\n(report only - pass --apply)   renames -> r4_renames.json")
    raise SystemExit(0)

# --- move -------------------------------------------------------------------
print("\nmoving...")
n = 0
for old, new in renames.items():
    src, dst = lib.abspath(old), lib.abspath(new)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    n += 1
print(f"  moved {n} files")

# --- repoint ---------------------------------------------------------------
from src.forms.asset_manager.reference_updater import ReferenceUpdater

print("\nrewriting references...")
mod = ReferenceUpdater(lib.ROOT).update_references_batch(renames)
print(f"  {len(mod)} files rewritten")
for p in sorted(mod):
    if p.lower().endswith((".vmap", ".vsmart")):
        print(f"      {lib.rel(p)}")
json.dump(renames, open(os.path.join(HERE, "r4_renames.json"), "w"), indent=1)
