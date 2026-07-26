"""Build the packed-layout destination map for de_firewatch.

Doubles as the plan's source of numbers and as the input to the move pass, so the
plan and the execution cannot drift apart. Writes r1_map.json + a readable tree.

Layout:   models/firewatch/<category>/<prop>/{vmdl,fbx,vmat,tga}
          models/firewatch/_shared/<name>/{vmat,tga}     material on >2 models
Frozen:   rock_01..04 and every texture they reference stay exactly where they
          are - the user authored them.
"""
import os, re, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "q1_graph.json")))
DEST_ROOT = "models/firewatch"
SHARE_AT = 2                       # material on more than this many models -> _shared

# --- scope: only the ported pack moves. dev/engine/props_survival are authored,
# and thirdparty/decals is a separate overlay set placed straight into the map.
IN = lambda p: "/firewatch/thirdparty/" in p and "/thirdparty/decals/" not in p
mdl_mats = {k: [m for m in v if IN(m)] for k, v in G["mdl_mats"].items() if IN(k)}
mat_tex = {k: v for k, v in G["mat_tex"].items() if IN(k)}
mat_mdls = collections.defaultdict(list)
for m, mats in mdl_mats.items():
    for x in mats:
        mat_mdls[x].append(m)

# --- frozen: the user's own rock materials and their textures ------------------
FROZEN_MAT = re.compile(r"/rock_0[1-4]\.vmat$")
frozen_mats = {m for m in mat_tex if FROZEN_MAT.search(m)}
frozen_tex = {t for m in frozen_mats for t in mat_tex[m].values()}

# --- merges: groups with an identical texture set collapse to one name ---------
SCALAR = re.compile(r'^\s*(g_\w+|F_\w+)\s+"?([^"\r\n]*)"?\s*$', re.M)


def real_slots(m):
    return {k: v for k, v in mat_tex.get(m, {}).items()
            if not v.startswith("materials/default/")}


# A material no vmdl uses and no map/smartprop reaches is dead whether or not it
# has textures - merging it would move a corpse into _shared.
live_vmats, _ = lib.live_vmats()
orphan_mat = sorted(m for m in mat_tex
                    if not mat_mdls[m] and m not in live_vmats and m not in frozen_mats)

by_texset = collections.defaultdict(list)
for m in mat_tex:
    s = real_slots(m)
    if s and m not in frozen_mats and m not in orphan_mat:
        by_texset[tuple(sorted(s.items()))].append(m)

# Winner = most-used, then shortest name. Merging across a pack boundary would
# drag a packed material out to _shared, which defeats the layout, so a group is
# only merged where every member lands in the same bucket.
merge = {}
for mats in by_texset.values():
    if len(mats) < 2:
        continue
    shared = [m for m in mats if len(mat_mdls[m]) > SHARE_AT]
    packed = [m for m in mats if len(mat_mdls[m]) <= SHARE_AT]
    for bucket in (shared, packed):
        if len(bucket) < 2:
            continue
        win = sorted(bucket, key=lambda m: (-len(mat_mdls[m]), len(m), m))[0]
        for m in bucket:
            if m != win:
                merge[m] = win

# --- unwired placeholders: all-default textures --------------------------------
placeholder = [m for m in mat_tex if not real_slots(m) and m not in frozen_mats]
dead_mat = sorted(set(orphan_mat) | {m for m in placeholder if not mat_mdls[m]})
live_placeholder = [m for m in placeholder if mat_mdls[m]]

# woodpile.vmdl carries ten grey placeholder slots while the correct wood
# material sits next to it - point them at it.
WOOD = "materials/firewatch/thirdparty/_shared/mi_woodenpiles.vmat"
for m in list(live_placeholder):
    if re.search(r"/woodenpiles_\d+\.vmat$", m):
        merge[m] = WOOD
        live_placeholder.remove(m)

# --- pack clusters: models glued by a material used by <= SHARE_AT models ------
def resolve(m):
    seen = set()
    while m in merge and m not in seen:
        seen.add(m)
        m = merge[m]
    return m


kept_mats = {resolve(m) for m in mat_tex if m not in dead_mat} | frozen_mats
mdl_kept = {k: sorted({resolve(x) for x in v if x not in dead_mat}) for k, v in mdl_mats.items()}
kept_mdls = collections.defaultdict(list)
for m, mats in mdl_kept.items():
    for x in mats:
        kept_mdls[x].append(m)

parent = {m: m for m in mdl_kept}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def category(m):
    return os.path.dirname(m).split("thirdparty/")[-1]


shared_mats = set()
for mat, mdls in kept_mdls.items():
    # Count alone is not enough: a two-model atlas whose models sit in different
    # categories would otherwise glue them into one folder, which is how a rope
    # material dragged firelookouttower.vmdl into props/debris/rope01.
    if len(mdls) > SHARE_AT or mat in frozen_mats or len({category(m) for m in mdls}) > 1:
        shared_mats.add(mat)
        continue
    for m in mdls[1:]:
        ra, rb = find(mdls[0]), find(m)
        if ra != rb:
            parent[ra] = rb

clusters = collections.defaultdict(list)
for m in mdl_kept:
    clusters[find(m)].append(m)

# --- name each cluster folder ------------------------------------------------
CAT = {}                            # cluster -> category, taken from its models
for root, mdls in clusters.items():
    cats = collections.Counter(os.path.dirname(m).split("thirdparty/")[-1] for m in mdls)
    CAT[root] = cats.most_common(1)[0][0]


VAR_SUF = re.compile(r"(_lod\d+|_l|_r|_s|_\d+|\d+)$")


def cluster_name(mdls):
    """Longest common prefix of the members, trimmed of variant suffixes.

    barrel + barrel2 -> barrel; slipper_l + slipper_r -> slipper. Falls back to
    the shortest name when the members share no prefix (chair + table -> chair).
    """
    names = sorted(os.path.splitext(os.path.basename(m))[0] for m in mdls)
    pre = os.path.commonprefix(names).rstrip("_0123456789")
    if len(names) > 1 and len(pre) >= 3:
        return pre
    base = min(names, key=len)
    prev = None
    while prev != base:                 # firelookouttower_01 -> firelookouttower
        prev = base
        base = VAR_SUF.sub("", base) or prev
    return base or min(names, key=len)


folder = {}                         # model -> dest folder
used = collections.Counter()
for root, mdls in clusters.items():
    name = cluster_name(mdls)
    d = f"{DEST_ROOT}/{CAT[root]}/{name}"
    used[d] += 1
    if used[d] > 1:
        d = f"{d}_{used[d]}"
    for m in mdls:
        folder[m] = d

# --- material destinations ---------------------------------------------------
# A merge winner keeps whichever name is most-used, which reads badly once four
# materials collapse into it: the generic wood ends up called "table01" and the
# generic metal "house_leg". These are the hand-picked names for the collapsed
# groups; everything else just loses its mi_/m_/t_ prefix.
NAMES = {
    "mi_woodenpiles":    "wood_damaged",       # 15 -> 1, colour = damaged_wood
    "mi_table01":        "wood_damaged_trim",  # 5 -> 1, same colour map, other slots differ
    "mi_house_leg":      "metal_painted",      # 4 -> 1, colour = metal
    "mi_house_metal":    "metal_roof",         # 2 -> 1, colour = metal
    "mi_flower":         "grass_atlas",        # 4 -> 1, colour = grass_flower
    "mi_driedleaves":    "leaf_atlas",         # colour = leaf02
    "mi_treemidleaves":  "leaf_atlas",         # 4 -> 1 once driedleaves folded in
    "mi_fence_net":      "net",
    "mi_table04":        "wood_trim",
    "mi_barrel":         "barrel",             # stays packed next to barrel.vmdl
    "mi_cup_colorvar":   "propset_small",
    "mi_medium_clifs":   "cliff",              # not "rock" - that name is the user's
    "mi_trimbrownwood":  "trim_wood",
    "m_suv_under":       "suv_under",
}


def clean(n):
    """Drop the UE instance prefixes and the trailing-underscore litter."""
    stem = os.path.splitext(os.path.basename(n))[0]
    if stem in NAMES:
        return NAMES[stem]
    stem = re.sub(r"^(mi_|m_|t_)", "", stem)
    stem = re.sub(r"_inst(\d*)$", r"\1", stem)      # UE instance litter
    return re.sub(r"_+$", "", stem) or "material"


mat_dest = {}
for mat in sorted(kept_mats):
    if mat in frozen_mats:
        continue                                        # stays put, untouched
    mdls = kept_mdls.get(mat, [])
    if mat in shared_mats or not mdls:
        mat_dest[mat] = f"{DEST_ROOT}/_shared/{clean(mat)}/{clean(mat)}.vmat"
    else:
        d = folder[mdls[0]]
        mat_dest[mat] = f"{d}/{clean(mat)}.vmat"

# --- texture destinations: a texture follows its material when exclusive ------
tex_mats = collections.defaultdict(set)
for mat in kept_mats:
    for t in mat_tex.get(mat, {}).values():
        if not t.startswith("materials/default/"):
            tex_mats[t].add(mat)

# Name a texture after the slot it is wired into, not after its filename. Parsing
# the name collides: humvee_glass_ao.tga and t_humvee_glass_b_o.tga both parse to
# "humvee_glass" + "ao", and debris_color.tga and debris_01_color.tga both to
# "debris" + "color" - three files would have been overwritten. A material has
# exactly one texture per slot, so keying on the slot cannot collide.
tex_dest = {}
for mat in sorted(kept_mats):
    if mat not in mat_dest:
        continue                                        # frozen - stays put
    for slot, t in sorted(mat_tex.get(mat, {}).items()):
        if t.startswith("materials/default/") or t in frozen_tex or not IN(t):
            continue
        owners = {os.path.dirname(mat_dest[m]) for m in tex_mats[t] if m in mat_dest}
        ext = os.path.splitext(t)[1]
        if len(owners) == 1:
            base, d = clean(mat), owners.pop()
        else:
            base = clean(lib.split_name(os.path.basename(t))[0])   # atlas across folders
            d = f"{DEST_ROOT}/_shared/{base}"
        cand = f"{d}/{base}_{slot}{ext}"
        # Two textures wanting one name means two materials in one folder share a
        # stem; fall back to the source stem to keep them distinct.
        if tex_dest.get(t, cand) != cand or (cand in set(tex_dest.values()) and tex_dest.get(t) != cand):
            base = clean(lib.split_name(os.path.basename(t))[0])
            cand = f"{d}/{base}_{slot}{ext}"
        tex_dest.setdefault(t, cand)

# --- two destinations for one path would silently eat a file -----------------
dests = collections.Counter()
for src, d in list(mat_dest.items()) + list(tex_dest.items()):
    dests[d.lower()] += 1
for m, d in folder.items():
    dests[f"{d}/{os.path.basename(m)}".lower()] += 1
clash = {d: n for d, n in dests.items() if n > 1}
if clash:
    print(f"ABORT: {len(clash)} destination collisions")
    for d, n in sorted(clash.items())[:20]:
        srcs = [s for s, x in list(mat_dest.items()) + list(tex_dest.items()) if x.lower() == d]
        print(f"   {n}x  {d}")
        for s in srcs:
            print(f"        <- {s}")
    raise SystemExit(1)

# --- report -----------------------------------------------------------------
print(f"scope: {len(mdl_mats)} models, {len(mat_tex)} materials, {len(tex_mats)} live textures")
print()
print(f"materials merged away      : {len(merge)}")
print(f"dead materials to delete   : {len(dead_mat)}")
print(f"materials kept             : {len(kept_mats)}  ({len(frozen_mats)} frozen)")
print(f"  packed into a prop folder: {len(kept_mats) - len(shared_mats) - len(frozen_mats)}")
print(f"  in _shared/              : {len(shared_mats - frozen_mats)}")
print(f"still all-default (unwired): {len(live_placeholder)}")
print()
sizes = sorted((len(c) for c in clusters.values()), reverse=True)
print(f"pack folders               : {len(clusters)}   biggest {sizes[0]} models")
print(f"textures relocated         : {len(tex_dest)}")
print(f"textures frozen in place   : {len(frozen_tex)}")

json.dump({"folder": folder, "mat_dest": mat_dest, "tex_dest": tex_dest,
           "merge": {k: resolve(k) for k in merge}, "dead_mat": dead_mat,
           "frozen_mats": sorted(frozen_mats), "frozen_tex": sorted(frozen_tex),
           "live_placeholder": live_placeholder},
          open(os.path.join(HERE, "r1_map.json"), "w"), indent=1)

print()
print("=" * 78)
print("MERGES")
print("=" * 78)
inv = collections.defaultdict(list)
for k in merge:
    inv[resolve(k)].append(k)
for win, losers in sorted(inv.items(), key=lambda kv: -len(kv[1])):
    print(f"\n  {clean(win)}.vmat  <-  {len(losers) + 1} materials -> {mat_dest.get(win, '(frozen)')}")
    for l in sorted([win] + losers):
        mark = "*" if l == win else " "
        print(f"    {mark} {os.path.basename(l):36} ({len(mat_mdls[l])} models)")

print()
print("=" * 78)
print("SAMPLE PACKED FOLDERS")
print("=" * 78)
tree = collections.defaultdict(list)
for m, d in folder.items():
    tree[d].append(("vmdl", os.path.basename(m)))
for mat, d in mat_dest.items():
    tree[os.path.dirname(d)].append(("vmat", os.path.basename(d)))
for t, d in tex_dest.items():
    tree[os.path.dirname(d)].append(("tga", os.path.basename(d)))
for d in sorted(tree)[:6] + [x for x in sorted(tree) if "/barrel" in x]:
    print(f"\n  {d}/")
    for kind, n in sorted(set(tree[d]), key=lambda x: (x[0] != "vmdl", x[1])):
        print(f"      {n}")
print(f"\n... {len(tree)} folders total")
