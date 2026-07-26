"""Consolidate _shared buckets that got split by an underscore.

The material is named from its vmat (propset01) and a shared texture bucket from
the texture stem (propset_01), so one logical asset ended up as two folders. Where
collapsing underscores makes the two names equal they are the same thing and get
merged; buckets with no matching vmat folder (metal, trimsheet, trapaulin_tile)
are genuinely shared atlases and stay as they are.

  python r6_tidy.py [--apply]
"""
import os, re, sys, glob, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib

APPLY = "--apply" in sys.argv
SHARED = os.path.join(lib.ROOT, "models", "firewatch", "_shared")
norm = lambda s: s.replace("_", "")

dirs = {d: os.path.join(SHARED, d) for d in sorted(os.listdir(SHARED))
        if os.path.isdir(os.path.join(SHARED, d))}
has_vmat = {d for d, p in dirs.items() if glob.glob(os.path.join(p, "*.vmat"))}
by_norm = {}
for d in has_vmat:
    by_norm.setdefault(norm(d), d)

renames = {}
for d, p in dirs.items():
    if d in has_vmat:
        continue
    # "propset_02_mask" is the mask map of propset_02, not a bucket of its own
    target = by_norm.get(norm(d)) or by_norm.get(norm(re.sub(r"_mask$", "", d)))
    if not target:
        print(f"  keeping {d}/  (shared atlas, no matching material)")
        continue
    for f in sorted(os.listdir(p)):
        stem, ext = os.path.splitext(f)
        # propset_02_mask_mask.png -> propset02_mask.png
        new = re.sub(rf"^{re.escape(d)}", target, stem)
        new = re.sub(r"_mask_mask$", "_mask", new)
        renames[lib.rel(os.path.join(p, f))] = f"models/firewatch/_shared/{target}/{new}{ext}"

print(f"\n{len(renames)} files to consolidate")
for o, n in sorted(renames.items()):
    print(f"    {o.split('_shared/')[-1]:44} -> {n.split('_shared/')[-1]}")

if not renames:
    raise SystemExit(0)
dup = [n for n in renames.values() if os.path.exists(lib.abspath(n))]
if dup:
    raise SystemExit(f"ABORT: {len(dup)} destinations already exist: {dup[:5]}")
if not APPLY:
    print("\n(report only - pass --apply)")
    raise SystemExit(0)

for o, n in renames.items():
    dst = lib.abspath(n)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(lib.abspath(o), dst)
print(f"\nmoved {len(renames)} files")

from src.forms.asset_manager.reference_updater import ReferenceUpdater
mod = ReferenceUpdater(lib.ROOT).update_references_batch(renames)
print(f"rewrote references in {len(mod)} files")

for d in dirs:
    p = dirs[d]
    if os.path.isdir(p) and not os.listdir(p):
        os.rmdir(p)
        print(f"removed empty {d}/")
