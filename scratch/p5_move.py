"""Phase 5b - execute the move through H5T's own ReferenceUpdater.

Moves every file in p5_renames.csv, then fixes up all references in one batch
pass (models, materials, smartprops and the binary vmaps alike).

Run with --apply to write; default is a dry run.
"""
import sys, os, csv, shutil, collections
sys.path.insert(0, r"D:\CG\Projects\Other\Hammer5Tools")
import lib
from src.forms.asset_manager.reference_updater import ReferenceUpdater

APPLY = "--apply" in sys.argv

rows = list(csv.DictReader(open("p5_renames.csv")))
renames = {r["old"]: r["new"] for r in rows}

missing = [o for o in renames if not os.path.exists(lib.abspath(o))]
occupied = [n for n in renames.values() if os.path.exists(lib.abspath(n))]
clash = [k for k, v in collections.Counter(renames.values()).items() if v > 1]

print(f"renames        : {len(renames)}")
print(f"missing sources: {len(missing)}  {missing[:5]}")
print(f"occupied dests : {len(occupied)}  {occupied[:5]}")
print(f"dest collisions: {len(clash)}  {clash[:5]}")
if missing or occupied or clash:
    raise SystemExit("ABORT: fix the map first")

if not APPLY:
    print("\ndry run - pass --apply to move")
    raise SystemExit

moved = 0
for old, new in renames.items():
    src, dst = lib.abspath(old), lib.abspath(new)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    moved += 1
print(f"\nmoved {moved} files")

updater = ReferenceUpdater(lib.ROOT)
modified = updater.update_references_batch(renames)
print(f"rewrote references in {len(modified)} files:")
for m in sorted(modified):
    print("   ", lib.rel(m))

# prune the now-empty source trees
for base in ("models/firewatchtower", "materials/firewatchtower"):
    d = lib.abspath(base)
    for dp, dns, fns in os.walk(d, topdown=False):
        if not os.listdir(dp):
            os.rmdir(dp)
    print(f"{base}: {'removed' if not os.path.exists(d) else 'still has files: ' + str(os.listdir(d))}")
