"""Before deleting 'dead' textures: are they dead, or just never wired up?

The second import pass brought complete PBR sets. The live materials are from the
first pass, which in plenty of cases fell back to a scalar or an engine default for
roughness/metalness/AO/normal. So a map can look unreferenced while being exactly
the data the live material should be using.

Matches each live material to a texture stem via its colour map, then reports which
of that stem's other maps exist on disk but aren't wired into the material.
"""
import os, collections, lib

SLOTS = ["normal", "rough", "metal", "ao"]
SLOT_PARAM = {"normal": "TextureNormal1", "rough": "TextureRoughness1",
              "metal": "TextureMetalness1", "ao": "TextureAmbientOcclusion1"}

tgas = {lib.rel(p) for p in lib.walk_ext("materials/firewatchtower", ".tga")}
by_stem = collections.defaultdict(dict)
for t in tgas:
    stem, suf = lib.split_name(os.path.basename(t))
    if suf:
        by_stem[stem][suf] = t

live, _ = lib.live_vmats()
live_fw = sorted(v for v in live if "firewatchtower" in v)

upgrades = {}
for v in live_fw:
    refs = dict((lib.slot_kind(s), val.lower().replace("\\", "/")) for s, val in lib.texture_refs(lib.abspath(v)))
    colour = refs.get("color", "")
    if not colour.startswith("materials/firewatchtower/"):
        continue
    stem, _s = lib.split_name(os.path.basename(colour))
    avail = by_stem.get(stem, {})
    miss = []
    for slot in SLOTS:
        have = refs.get(slot, "")
        # placeholder = a literal scalar "[r g b a]", an engine default, or no line at all
        placeholder = (not have) or have.startswith("[") or have.startswith("materials/default/")
        if placeholder and slot in avail:
            miss.append((slot, avail[slot]))
    if miss:
        upgrades[v] = miss

n_slots = sum(len(v) for v in upgrades.values())
gain = {t for m in upgrades.values() for _, t in m}
size = sum(os.path.getsize(lib.abspath(t)) for t in gain)

print(f"live firewatchtower materials       : {len(live_fw)}")
print(f"  with a real map sitting unused    : {len(upgrades)}  ({n_slots} slots)")
print(f"  distinct textures this would wire : {len(gain)}  ({size/1073741824:.2f} GB)")
print()
by_slot = collections.Counter(s for m in upgrades.values() for s, _ in m)
print("by slot:", dict(by_slot))
print()
for v, m in sorted(upgrades.items())[:30]:
    print(f"  {v.split('/')[-1]:34} + {', '.join(s for s, _ in m)}")
print(f"  ... {len(upgrades)} total" if len(upgrades) > 30 else "")
