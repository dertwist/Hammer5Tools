"""Pass 2: map/vsmart usage, flat masks, bad scalars, mismatched textures."""
import os, re, sys, json, struct, collections

ROOT = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_firewatch"
d = json.load(open(os.path.join(os.path.dirname(__file__), "audit.json")))

def rel(p): return os.path.relpath(p, ROOT).replace("\\", "/").lower()

# ---- 1. references from binary vmap / vsmart -------------------------------
path_re = re.compile(rb"(?:models|materials)/[A-Za-z0-9_/\.\-]+\.(?:vmdl|vmat)")
map_refs = collections.defaultdict(set)
for sub in ("maps", "smartprops", "prefabs"):
    base = os.path.join(ROOT, sub)
    if not os.path.isdir(base): continue
    for dp, _, fns in os.walk(base):
        for fn in fns:
            if not fn.lower().endswith((".vmap", ".vsmart", ".vpk")): continue
            p = os.path.join(dp, fn)
            data = open(p, "rb").read()
            for m in path_re.findall(data):
                map_refs[rel(p)].add(m.decode("ascii", "ignore").lower())

all_map_refs = set()
for v in map_refs.values(): all_map_refs |= v
map_vmats = {r for r in all_map_refs if r.endswith(".vmat")}
map_vmdls = {r for r in all_map_refs if r.endswith(".vmdl")}

# ---- 2. flat / constant TGAs ----------------------------------------------
def tga_stats(path):
    data = open(path, "rb").read()
    if len(data) < 18: return None
    idlen, imgtype, bpp = data[0], data[2], data[16]
    if imgtype not in (2, 3): return None
    w, h = struct.unpack("<HH", data[12:16])
    off = 18 + idlen
    n = bpp // 8
    px = data[off:off + w * h * n]
    if len(px) < w * h * n: return None
    if imgtype == 3:   # grayscale
        vals = px
        return dict(kind="gray", w=w, h=h, min=min(vals), max=max(vals), bpp=bpp)
    b = px[0::4]; g = px[1::4]; r = px[2::4]; a = px[3::4] if n == 4 else None
    return dict(kind="rgba" if n == 4 else "rgb", w=w, h=h, bpp=bpp,
                rmin=min(r), rmax=max(r), gmin=min(g), gmax=max(g), bmin=min(b), bmax=max(b),
                amin=min(a) if a else None, amax=max(a) if a else None)

tgas = []
for dp, _, fns in os.walk(os.path.join(ROOT, "materials")):
    for fn in fns:
        if fn.lower().endswith(".tga"): tgas.append(os.path.join(dp, fn))

flat, stats = {}, {}
for p in tgas:
    s = tga_stats(p)
    if not s: continue
    stats[rel(p)] = s
    if s["kind"] == "gray" and s["min"] == s["max"]:
        flat[rel(p)] = ("gray", s["min"], s["w"])
    elif s["kind"] != "gray" and s["rmin"] == s["rmax"] and s["gmin"] == s["gmax"] and s["bmin"] == s["bmax"]:
        flat[rel(p)] = ("rgb", (s["rmin"], s["gmin"], s["bmin"]), s["w"])

# ---- 3. vmat scalar sanity + texture-name mismatch ------------------------
scalar_re = re.compile(r'^\s*(Texture\w+)\s+"\[([\-0-9\. ]+)\]"', re.M)
tex_re    = re.compile(r'^\s*(Texture\w+)\s+"([^"\[][^"]*)"', re.M)
bad_scalar, mismatch, no_normal, alpha_candidates = {}, {}, [], []

vmats = []
for dp, _, fns in os.walk(os.path.join(ROOT, "materials")):
    for fn in fns:
        if fn.lower().endswith(".vmat"): vmats.append(os.path.join(dp, fn))

def stem(t):
    b = os.path.basename(t).rsplit(".", 1)[0]
    b = re.sub(r"_(color|normal|rough|metal|ao|height|trans|b|n|d|o|bc|orm_ao|orm_rough|orm_metal)$", "", b)
    b = re.sub(r"^(t_|mi_|m_)", "", b)
    return b

for p in vmats:
    r = rel(p); t = open(p, encoding="utf-8", errors="ignore").read()
    for slot, vals in scalar_re.findall(t):
        nums = [float(x) for x in vals.split()]
        if any(x > 1.0001 or x < -0.0001 for x in nums[:3]):
            bad_scalar.setdefault(r, []).append((slot, nums[:3]))
    refs = tex_re.findall(t)
    mystem = stem(r)
    odd = [(s, v) for s, v in refs
           if not v.lower().startswith("materials/default/") and stem(v) != mystem]
    if odd: mismatch[r] = odd
    if not any(s.startswith("TextureNormal") for s, _ in refs): no_normal.append(r)
    # alpha candidate: its color texture has real alpha but no F_ALPHA_TEST
    for s, v in refs:
        if s.startswith("TextureColor") and v.lower().replace("\\", "/") in d["alpha_tgas"]:
            if "F_ALPHA_TEST" not in t and "F_TRANSLUCENT" not in t:
                alpha_candidates.append((r, v.lower().replace("\\", "/")))

out = dict(
    map_refs={k: sorted(v) for k, v in map_refs.items()},
    map_vmats=sorted(map_vmats), map_vmdls=sorted(map_vmdls),
    flat_tgas=flat, bad_scalar=bad_scalar, mismatch=mismatch,
    no_normal=no_normal, alpha_candidates=alpha_candidates,
)
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)

print("vmap/vsmart files scanned:", len(map_refs))
print("vmats referenced from maps/smartprops:", len(map_vmats))
print("vmdls referenced from maps/smartprops:", len(map_vmdls))
print("flat (constant) tgas:", len(flat), "of", len(stats))
print("vmats with out-of-range scalars:", len(bad_scalar))
print("vmats referencing a texture from a different asset:", len(mismatch))
print("vmats with no normal map:", len(no_normal))
print("alpha candidates (color has alpha, no alpha-test):", len(alpha_candidates))
