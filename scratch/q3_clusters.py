"""How packable is the addon really?

A packed folder holds a vmdl and the vmat/tga it uses. If two models share a
material they must share the folder, so the unit of packing is a connected
component of the model<->material graph, not a single model. This measures those
components at several "shared" thresholds: a material used by more than N models
is pulled out to a shared bucket instead of gluing its models together.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "q1_graph.json")))
mdl_mats = {k: v for k, v in G["mdl_mats"].items() if "/firewatch/" in k}
mat_mdls = {k: [m for m in v if "/firewatch/" in m] for k, v in G["mat_mdls"].items()}
mat_mdls = {k: v for k, v in mat_mdls.items() if v}


def components(threshold):
    """Union-find over models, joining any two that share a non-shared material."""
    parent = {m: m for m in mdl_mats}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    pulled = set()
    for mat, mdls in mat_mdls.items():
        if len(mdls) > threshold:
            pulled.add(mat)
            continue
        for m in mdls[1:]:
            if m in parent and mdls[0] in parent:
                union(mdls[0], m)

    comp = collections.defaultdict(list)
    for m in mdl_mats:
        comp[find(m)].append(m)
    return list(comp.values()), pulled


print(f"{len(mdl_mats)} firewatch models, {len(mat_mdls)} materials they reference")
print()
print(f"{'thresh':>7} {'folders':>8} {'biggest':>8} {'>8 models':>10} {'shared out':>11}")
for t in (1, 2, 3, 4, 6, 8, 999):
    comps, pulled = components(t)
    sizes = sorted((len(c) for c in comps), reverse=True)
    print(f"{t:>7} {len(comps):>8} {sizes[0]:>8} {sum(1 for s in sizes if s > 8):>10} {len(pulled):>11}")

print()
print("=" * 78)
print("COMPONENTS AT THRESHOLD 2  (a material on >2 models goes to _shared)")
print("=" * 78)
comps, pulled = components(2)
for c in sorted(comps, key=len, reverse=True):
    mats = sorted({m for mdl in c for m in mdl_mats[mdl] if m not in pulled})
    if len(c) == 1 and len(mats) <= 1:
        continue
    print(f"\n[{len(c)} models / {len(mats)} packed materials]")
    for m in sorted(c):
        print(f"    M  {os.path.basename(m)}")
    for m in mats:
        print(f"    m    {os.path.basename(m)}")

print()
print("=" * 78)
print(f"PULLED TO _shared AT THRESHOLD 2 ({len(pulled)})")
print("=" * 78)
for m in sorted(pulled, key=lambda x: -len(mat_mdls[x])):
    cats = {os.path.dirname(x).split("thirdparty/")[-1] for x in mat_mdls[m]}
    print(f"  {len(mat_mdls[m]):3}x  {os.path.basename(m):34} across {len(cats)} categor{'y' if len(cats)==1 else 'ies'}: {', '.join(sorted(cats))}")
