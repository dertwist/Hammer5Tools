"""Phase 4 - wire up the maps the live materials should have been using, then
delete what is genuinely unreachable.

Order matters: 'unreferenced' is not the same as 'unwanted'. The second import
pass brought complete PBR sets and the live first-pass materials fall back to a
scalar for roughness/metalness/AO in a number of cases, so those maps look dead
while being exactly the data the material wants. Wire them first; whatever is
still unreachable afterwards really is dead.

Run with --apply to write; default is a dry run.
"""
import sys, os, re, collections, lib

APPLY = "--apply" in sys.argv
SLOTS = ["normal", "rough", "metal", "ao"]
SLOT_PARAM = {"normal": "TextureNormal1", "rough": "TextureRoughness1",
              "metal": "TextureMetalness1", "ao": "TextureAmbientOcclusion1"}

tgas = {lib.rel(p) for p in lib.walk_ext("materials/firewatchtower", ".tga")}
by_stem = collections.defaultdict(dict)
for t in tgas:
    stem, suf = lib.split_name(os.path.basename(t))
    if suf:
        by_stem[stem][suf] = t

# ---- 1. upgrade placeholder slots to the real map ------------------------
live, all_vmats = lib.live_vmats()
upgraded = collections.Counter()
for v in sorted(x for x in live if "firewatchtower" in x):
    p = lib.abspath(v)
    refs = {lib.slot_kind(s): val.lower().replace("\\", "/") for s, val in lib.texture_refs(p)}
    colour = refs.get("color", "")
    if not colour.startswith("materials/firewatchtower/"):
        continue
    stem, _ = lib.split_name(os.path.basename(colour))
    avail = by_stem.get(stem, {})

    def fn(slot, val):
        k = lib.slot_kind(slot)
        if k not in SLOTS or k not in avail:
            return None
        if val and not val.startswith("[") and not val.startswith("materials/default/"):
            return None                       # already has a real map
        return avail[k]

    text, n = lib.rewrite_texture_lines(lib.read_text(p), fn)
    if n:
        upgraded[v] = n
        if APPLY:
            lib.write_text(p, text)

print(f"materials upgraded : {len(upgraded)}  ({sum(upgraded.values())} slots)")
for v, n in sorted(upgraded.items()):
    print(f"   {v.split('/')[-1]:38} +{n}")

# ---- 2. recompute reachability -------------------------------------------
if not APPLY and upgraded:
    print("\n(dry run: dead-set below is computed pre-upgrade and will be slightly larger)")

live, all_vmats = lib.live_vmats()
live_tex = set()
for v in live:
    for _, val in lib.texture_refs(lib.abspath(v)):
        live_tex.add(val.lower().replace("\\", "/"))

dead_vmats = sorted(v for v in all_vmats - live if "firewatchtower" in v)
dead_tgas = sorted(t for t in tgas if t not in live_tex)
freed = sum(os.path.getsize(lib.abspath(t)) for t in dead_tgas) + \
        sum(os.path.getsize(lib.abspath(v)) for v in dead_vmats)

print(f"\nunreachable after upgrade:")
print(f"  vmats : {len(dead_vmats)}")
print(f"  tgas  : {len(dead_tgas)}")
print(f"  frees : {freed/1073741824:.2f} GB")

stems = collections.Counter(lib.split_name(os.path.basename(t))[0] for t in dead_tgas)
print(f"\n  across {len(stems)} texture stems, top: {stems.most_common(8)}")

if APPLY:
    doomed = list(dead_vmats)
    if "--textures" in sys.argv:          # opt-in: unused source library, not clutter
        doomed += dead_tgas
    for f in doomed:
        os.remove(lib.abspath(f))
    print(f"\nAPPLIED: deleted {len(dead_vmats)} vmats"
          + (f" + {len(dead_tgas)} textures" if "--textures" in sys.argv else " (textures kept)"))
else:
    print("\ndry run - pass --apply to write")
