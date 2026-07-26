"""Follow-up questions the plan needs answered before it can be written."""
import os, re, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "q1_graph.json")))
mdl_mats, mat_mdls, mat_tex = G["mdl_mats"], G["mat_mdls"], G["mat_tex"]

# --- 1. the 27 zero-material models: parse failure or genuinely unassigned? ---
print("=" * 78)
print("MODELS WITH NO MATERIAL REMAP")
print("=" * 78)
for r, mats in sorted(mdl_mats.items()):
    if mats:
        continue
    txt = lib.read_text(lib.abspath(r))
    has_group = "MaterialGroupList" in txt
    has_remap = "remaps" in txt
    mesh = re.findall(r'filename\s*=\s*"([^"]+)"', txt)
    print(f"  {r}")
    print(f"      MaterialGroupList={has_group} remaps={has_remap} files={len(mesh)}")

# --- 2. vmats no vmdl references: dead, or referenced by map/smartprop? -------
print()
print("=" * 78)
print("VMATS NOT REFERENCED BY ANY VMDL")
print("=" * 78)
live, all_vmats = lib.live_vmats()
orphans = sorted(all_vmats - set(mat_mdls))
placeholder, reachable, dead = [], [], []
for r in orphans:
    slots = mat_tex.get(r, {})
    real = [v for v in slots.values() if not v.startswith("materials/default/")]
    (reachable if r in live else (placeholder if not real else dead)).append(r)
print(f"reachable from a vmap/vsmart/vmat ({len(reachable)}):")
for r in reachable:
    print(f"    {r}")
print(f"\nunreachable AND all-default textures - pure dead weight ({len(placeholder)}):")
for r in placeholder:
    print(f"    {r}")
print(f"\nunreachable but has real textures ({len(dead)}):")
for r in dead:
    print(f"    {r}")

# --- 3. which model folder would each solo material land in? -----------------
print()
print("=" * 78)
print("SOLO MATERIALS: destination folder derived from their one model")
print("=" * 78)
solo = {m: v[0] for m, v in mat_mdls.items() if len(v) == 1}
by_dir = collections.defaultdict(list)
for m, mdl in solo.items():
    by_dir[os.path.dirname(mdl)].append((m, mdl))
for d in sorted(by_dir):
    print(f"\n  {d}   ({len(by_dir[d])})")
    for m, mdl in sorted(by_dir[d])[:4]:
        print(f"      {os.path.basename(mdl):40} <- {os.path.basename(m)}")
    if len(by_dir[d]) > 4:
        print(f"      ... {len(by_dir[d]) - 4} more")

# --- 4. textures: how many are exclusive to one material? -------------------
print()
print("=" * 78)
print("TEXTURE EXCLUSIVITY  (a texture used by 1 material can move with it)")
print("=" * 78)
tex_mats = G["tex_mats"]
excl = {t: v[0] for t, v in tex_mats.items() if len(v) == 1}
shared = {t: v for t, v in tex_mats.items() if len(v) > 1}
allt = {lib.rel(p) for p in lib.walk_ext("materials", ".tga")}
unref = sorted(allt - set(tex_mats))
print(f"used by 1 material : {len(excl)}")
print(f"used by >1         : {len(shared)}")
print(f"referenced by none : {len(unref)}")
sz = sum(os.path.getsize(lib.abspath(t)) for t in unref if os.path.exists(lib.abspath(t)))
print(f"                     ({sz / 1e9:.2f} GB)")
in_lib = [t for t in unref if "_library/" in t]
print(f"  of which in _library/: {len(in_lib)}")

# --- 5. name-variant families (barrel / barrel_bright style) -----------------
print()
print("=" * 78)
print("NAME-VARIANT FAMILIES")
print("=" * 78)
VARIANT = re.compile(r"_(birght|bright|dark|light|new|old|alt|var|colorvar|inst|"
                     r"\d+)$|_inst_\d+$|_\d+$")


def stem_of(r):
    n = os.path.splitext(os.path.basename(r))[0]
    n = re.sub(r"^(mi_|m_)", "", n)
    prev = None
    while prev != n:
        prev = n
        n = VARIANT.sub("", n)
    return n


fam = collections.defaultdict(list)
for r in all_vmats:
    if "/firewatch/" not in r:
        continue
    fam[stem_of(r)].append(r)
for s, rs in sorted(fam.items()):
    if len(rs) < 2:
        continue
    same_tex = len({tuple(sorted(mat_tex.get(r, {}).items())) for r in rs}) == 1
    print(f"\n  {s}  [{len(rs)}]  {'same textures' if same_tex else 'DIFFERENT textures'}")
    for r in sorted(rs):
        print(f"      {r}   ({len(mat_mdls.get(r, ()))} models)")
