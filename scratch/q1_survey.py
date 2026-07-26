"""Survey pass for the packed reorg: build the model<->material<->texture graph.

Answers the three questions the plan hangs on:
  1. which materials are duplicates of each other (same textures, differing only
     in scalars/tint) - the barrel / barrel_bright case;
  2. which materials are shared by more than one model - those cannot live inside
     a single model's folder, so they need a shared bucket;
  3. which textures are byte-identical or shared across materials.
"""
import os, re, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REMAP = re.compile(r'from\s*=\s*"([^"]*)"\s*\n?\s*to\s*=\s*"([^"]*)"', re.S)
MESH = re.compile(r'filename\s*=\s*"([^"]+\.(?:fbx|dmx|vmdl))"', re.I)

# --- vmdl -> vmats -----------------------------------------------------------
mdl_mats, mat_mdls = {}, collections.defaultdict(set)
for p in lib.walk_ext("models", ".vmdl"):
    r = lib.rel(p)
    txt = lib.read_text(p)
    mats = sorted({m[1].lower() for m in REMAP.findall(txt) if m[1].strip()})
    mdl_mats[r] = mats
    for m in mats:
        mat_mdls[m].add(r)

# --- vmat -> textures --------------------------------------------------------
mat_tex, tex_mats = {}, collections.defaultdict(set)
all_vmats = {lib.rel(p) for p in lib.walk_ext("materials", ".vmat")}
for p in lib.walk_ext("materials", ".vmat"):
    r = lib.rel(p)
    slots = {}
    for slot, val in lib.texture_refs(p):
        k = lib.slot_kind(slot)
        if not k or not val or val.startswith("["):
            continue
        slots[k] = val.lower().replace("\\", "/")
        tex_mats[slots[k]].add(r)
    mat_tex[r] = slots

# --- scalar/flag fingerprint so we can tell "same texture set" apart ---------
SCALAR = re.compile(r'^\s*(g_\w+|F_\w+)\s+"?([^"\r\n]*)"?\s*$', re.M)


def fingerprint(r):
    return tuple(sorted((m.group(1), m.group(2).strip()) for m in SCALAR.finditer(lib.read_text(lib.abspath(r)))))


# --- duplicate material families: identical non-scalar texture sets ----------
by_texset = collections.defaultdict(list)
for r, slots in mat_tex.items():
    if not slots.get("color"):
        continue
    by_texset[tuple(sorted(slots.items()))].append(r)

print("=" * 78)
print("MATERIALS SHARING AN IDENTICAL TEXTURE SET  (dedup candidates)")
print("=" * 78)
dupe_groups = 0
for key, mats in sorted(by_texset.items(), key=lambda kv: -len(kv[1])):
    if len(mats) < 2:
        continue
    dupe_groups += 1
    fps = {r: fingerprint(r) for r in mats}
    same = len(set(fps.values())) == 1
    print(f"\n[{len(mats)}] {'IDENTICAL' if same else 'differs in scalars'}")
    for r in sorted(mats):
        n = len(mat_mdls.get(r, ()))
        print(f"    {r}   ({n} model{'' if n == 1 else 's'})")
    if not same:
        base = collections.Counter()
        for fp in fps.values():
            base.update(fp)
        common = {k for k, c in base.items() if c == len(mats)}
        for r in sorted(mats):
            diff = sorted(set(fps[r]) - common)
            if diff:
                print(f"      ~ {r.rsplit('/', 1)[-1]}: " + ", ".join(f"{k}={v}" for k, v in diff))
print(f"\n{dupe_groups} groups of materials with an identical texture set")

# --- byte-identical textures -------------------------------------------------
print()
print("=" * 78)
print("BYTE-IDENTICAL TEXTURES")
print("=" * 78)
by_hash = collections.defaultdict(list)
for p in lib.walk_ext("materials", ".tga"):
    by_hash[(os.path.getsize(p), lib.md5(p))].append(lib.rel(p))
n_dupe_tex = 0
for (sz, h), ps in sorted(by_hash.items(), key=lambda kv: -len(kv[1])):
    if len(ps) < 2:
        continue
    n_dupe_tex += len(ps) - 1
    print(f"\n[{len(ps)}] {sz / 1e6:.1f} MB each")
    for p in sorted(ps):
        used = len(tex_mats.get(p, ()))
        print(f"    {p}   ({used} vmat{'' if used == 1 else 's'})")
print(f"\n{n_dupe_tex} redundant texture files")

# --- sharing: how packable is this? -----------------------------------------
print()
print("=" * 78)
print("PACKABILITY")
print("=" * 78)
shared_mats = {m: v for m, v in mat_mdls.items() if len(v) > 1}
solo_mats = {m: v for m, v in mat_mdls.items() if len(v) == 1}
orphan = sorted(all_vmats - set(mat_mdls))
print(f"materials used by exactly 1 model : {len(solo_mats)}   <- packable")
print(f"materials used by >1 model        : {len(shared_mats)}  <- shared bucket")
print(f"materials no vmdl references      : {len(orphan)}")
print(f"models with 1 material            : {sum(1 for v in mdl_mats.values() if len(v) == 1)}")
print(f"models with >1 material           : {sum(1 for v in mdl_mats.values() if len(v) > 1)}")
print(f"models with 0 materials           : {sum(1 for v in mdl_mats.values() if not v)}")

print("\ntop shared materials:")
for m, v in sorted(shared_mats.items(), key=lambda kv: -len(kv[1]))[:20]:
    print(f"  {len(v):3}x  {m}")

# textures shared between materials that live in different model folders
tex_shared = {t: v for t, v in tex_mats.items() if len(v) > 1}
print(f"\ntextures used by >1 material: {len(tex_shared)}")

json.dump({"mdl_mats": mdl_mats, "mat_mdls": {k: sorted(v) for k, v in mat_mdls.items()},
           "mat_tex": mat_tex, "tex_mats": {k: sorted(v) for k, v in tex_mats.items()}},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "q1_graph.json"), "w"), indent=1)
print("\ngraph -> q1_graph.json")
