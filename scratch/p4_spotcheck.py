"""Spot-check before deleting: is a 'dead' texture set actually the right data for
a model that is currently wearing something else?

For each dead texture stem, find any model whose name matches it and report what
material that model is actually using.
"""
import os, re, collections, lib

remap = re.compile(r'to\s*=\s*"([^"]+)"')

tgas = {lib.rel(p) for p in lib.walk_ext("materials/firewatchtower", ".tga")}
live, all_vmats = lib.live_vmats()
live_tex = set()
for v in live:
    for _, val in lib.texture_refs(lib.abspath(v)):
        live_tex.add(val.lower().replace("\\", "/"))
dead_stems = collections.defaultdict(list)
for t in sorted(tgas - live_tex):
    dead_stems[lib.split_name(os.path.basename(t))[0]].append(t)

models = {}
for p in lib.walk_ext("models/firewatchtower", ".vmdl"):
    models[os.path.basename(p)[:-5].lower()] = sorted(m.lower() for m in remap.findall(lib.read_text(p)))

print(f"{'dead stem':26} {'#maps':>5}  matching model -> material it actually uses")
print("-" * 100)
hits = 0
for stem, files in sorted(dead_stems.items()):
    match = [m for m in models if stem in m or m in stem]
    if not match:
        continue
    hits += 1
    for m in match[:2]:
        mats = [x.split("/")[-1] for x in models[m]]
        print(f"{stem:26} {len(files):5}  {m:24} -> {', '.join(mats) or '(none)'}")
print(f"\n{hits} of {len(dead_stems)} dead stems have a same-named model")
print(f"{len(dead_stems)-hits} have no model at all (unused source material)")
