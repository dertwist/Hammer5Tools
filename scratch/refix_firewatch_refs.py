"""Re-point de_firewatch references at the post-reorg asset paths.

Idempotent: files already carrying the new paths are left untouched, so this is
safe to run as often as needed. It exists because a *running* Hammer holds the
pre-move map and smartprops in memory and writes them back on every autosave,
undoing the fix within a minute or two. Close Hammer for it to stick; run this
after any session that saved while stale documents were open.

    python scratch/refix_firewatch_refs.py            # report only
    python scratch/refix_firewatch_refs.py --apply
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from src.forms.asset_manager.reference_updater import ReferenceUpdater

ADDON = (r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive"
         r"\content\csgo_addons\de_firewatch")
RENAMES_CSV = os.path.join(HERE, "p5_renames.csv")
OLD = re.compile(rb"firewatchtower", re.I)

# Referenced by Showcase.vmap but never present in this addon in any commit -
# a decal set that was assigned at import and never exported. No rename can fix
# these; they need the materials authored or the decals removed in Hammer.
KNOWN_MISSING = re.compile(rb"mi_decal_simple|mastermaterial/mm_decal_simple", re.I)


def stale_files():
    """Files still naming the old pack, and how many references each holds."""
    out = {}
    for sub in ("maps", "smartprops", "models", "materials"):
        d = os.path.join(ADDON, sub)
        if not os.path.isdir(d):
            continue
        for dp, _, fns in os.walk(d):
            for fn in fns:
                if os.path.splitext(fn)[1].lower() not in ReferenceUpdater.SCANNABLE_EXTS:
                    continue
                p = os.path.join(dp, fn)
                with open(p, "rb") as fh:
                    data = fh.read()
                hits = OLD.findall(data)
                if hits:
                    unfixable = len(KNOWN_MISSING.findall(data))
                    out[os.path.relpath(p, ADDON).replace("\\", "/")] = (len(hits), unfixable)
    return out


def main():
    apply = "--apply" in sys.argv
    with open(RENAMES_CSV, newline="") as fh:
        renames = {r["old"]: r["new"] for r in csv.DictReader(fh)}

    before = stale_files()
    total = sum(n for n, _ in before.values())
    print(f"{len(before)} files hold {total} stale references")
    for f, (n, bad) in sorted(before.items()):
        note = f"   ({bad} unfixable - see KNOWN_MISSING)" if bad else ""
        print(f"   {n:5}  {f}{note}")

    if not before:
        print("\nnothing to do")
        return
    if not apply:
        print("\ndry run - pass --apply to rewrite")
        return

    modified = ReferenceUpdater(ADDON).update_references_batch(renames)
    after = stale_files()
    left = sum(n for n, _ in after.values())
    unfixable = sum(bad for _, bad in after.values())

    print(f"\nrewrote {len(modified)} files")
    print(f"stale references remaining: {left}"
          + (f"  ({unfixable} are the never-exported decal set)" if unfixable else ""))
    for f, (n, bad) in sorted(after.items()):
        print(f"   {n:5}  {f}" + ("   [unfixable]" if bad == n else ""))
    if left and left != unfixable:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
