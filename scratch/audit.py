"""Audit de_firewatch addon: vmdl -> vmat -> tga reference graph, orphans, broken links."""
import os, re, sys, json, hashlib, struct, collections

ROOT = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_firewatch"

def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/").lower()

def walk(sub, ext):
    out = []
    base = os.path.join(ROOT, sub)
    for dp, _, fns in os.walk(base):
        for fn in fns:
            if fn.lower().endswith(ext):
                out.append(os.path.join(dp, fn))
    return out

vmdls = walk("models", ".vmdl")
vmats = walk("materials", ".vmat")
tgas  = walk("materials", ".tga")
pngs  = walk("materials", ".png")
fbxs  = walk("models", ".fbx")

vmat_set = {rel(p) for p in vmats}
tga_set  = {rel(p) for p in tgas}
fbx_set  = {rel(p) for p in fbxs}

# ---- vmdl -> vmat / fbx ----
remap_re = re.compile(r'to\s*=\s*"([^"]+)"')
from_re  = re.compile(r'from\s*=\s*"([^"]+)"')
fname_re = re.compile(r'filename\s*=\s*"([^"]+)"')

vmdl_to_vmat = {}
vmdl_to_fbx  = {}
for p in vmdls:
    t = open(p, encoding="utf-8", errors="ignore").read()
    vmdl_to_vmat[rel(p)] = sorted({m.lower() for m in remap_re.findall(t)})
    vmdl_to_fbx[rel(p)]  = sorted({m.lower() for m in fname_re.findall(t)})

# ---- vmat -> tga ----
tex_re = re.compile(r'^\s*(Texture\w+)\s+"([^"\[][^"]*)"', re.M)
shader_re = re.compile(r'shader\s+"([^"]+)"')
vmat_to_tga = {}
vmat_shader = {}
for p in vmats:
    t = open(p, encoding="utf-8", errors="ignore").read()
    sm = shader_re.search(t)
    vmat_shader[rel(p)] = sm.group(1) if sm else "?"
    vmat_to_tga[rel(p)] = [(k, v.lower().replace("\\", "/")) for k, v in tex_re.findall(t)]

# ---- broken links ----
broken_vmat = collections.defaultdict(list)   # vmdl -> missing vmats
for m, vs in vmdl_to_vmat.items():
    for v in vs:
        if v not in vmat_set:
            broken_vmat[m].append(v)

broken_fbx = {m: [f for f in fs if f not in fbx_set] for m, fs in vmdl_to_fbx.items()}
broken_fbx = {k: v for k, v in broken_fbx.items() if v}

broken_tga = collections.defaultdict(list)    # vmat -> missing tgas
for v, refs in vmat_to_tga.items():
    for slot, t in refs:
        if t.startswith("materials/default/"):
            continue
        if t not in tga_set:
            broken_tga[v].append((slot, t))

# ---- orphans ----
used_vmats = {v for vs in vmdl_to_vmat.values() for v in vs}
orphan_vmats = sorted(vmat_set - used_vmats)
used_tgas = {t for refs in vmat_to_tga.values() for _, t in refs}
orphan_tgas = sorted(tga_set - used_tgas)

# ---- duplicate tgas by hash ----
byhash = collections.defaultdict(list)
for p in tgas:
    h = hashlib.md5(open(p, "rb").read()).hexdigest()
    byhash[h].append(rel(p))
dupes = {h: sorted(v) for h, v in byhash.items() if len(v) > 1}

# ---- alpha analysis on 32bpp tgas ----
def alpha_info(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 18 or data[2] != 2 or data[16] != 32:
        return None
    idlen = data[0]
    w, h = struct.unpack("<HH", data[12:16])
    off = 18 + idlen
    px = data[off:off + w * h * 4]
    if len(px) < w * h * 4:
        return None
    a = px[3::4]
    mn, mx = min(a), max(a)
    if mn == mx:
        return None
    n = len(a)
    frac_cut = sum(1 for v in a if v < 128) / n     # binary-mask-ish
    frac_mid = sum(1 for v in a if 16 < v < 240) / n
    return dict(w=w, h=h, min=mn, max=mx, frac_below128=round(frac_cut, 3), frac_mid=round(frac_mid, 3))

alphas = {}
for p in tgas:
    i = alpha_info(p)
    if i:
        alphas[rel(p)] = i

out = dict(
    counts=dict(vmdl=len(vmdls), vmat=len(vmats), tga=len(tgas), png=len(pngs), fbx=len(fbxs)),
    shaders=collections.Counter(vmat_shader.values()),
    broken_vmat_refs={k: v for k, v in broken_vmat.items()},
    broken_fbx_refs=broken_fbx,
    broken_tga_refs={k: v for k, v in broken_tga.items()},
    orphan_vmats=orphan_vmats,
    orphan_tgas=orphan_tgas,
    dup_tga_groups=list(dupes.values()),
    alpha_tgas=alphas,
    vmdl_to_vmat=vmdl_to_vmat,
)
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)

print("counts:", out["counts"])
print("shaders:", dict(out["shaders"]))
print("vmdls with broken vmat refs:", len(broken_vmat))
print("vmdls with broken fbx refs:", len(broken_fbx))
print("vmats with broken tga refs:", len(broken_tga))
print("orphan vmats:", len(orphan_vmats))
print("orphan tgas:", len(orphan_tgas))
print("duplicate tga groups:", len(dupes), "wasted files:", sum(len(v) - 1 for v in dupes.values()))
print("tgas with real alpha:", len(alphas))
