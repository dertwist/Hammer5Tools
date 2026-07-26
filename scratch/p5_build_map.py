"""Phase 5a - build the rename map as a reviewable CSV.

Models are categorised by name; a material and its textures follow whichever
model uses them, so a prop and its material land in the same category. Materials
used by several categories, and the unassigned tileable library, go to _shared/
and _library/.

Writes p5_renames.csv. Nothing is moved here.
"""
import os, re, csv, collections, lib

# Ordered: first match wins, so the specific patterns come before the loose ones.
RULES = [
    ("nature/foliage",          r"grass|leaf|leaves|fern|festuca|bush|flower|plant|moss|driedleaves|deadgrass|longgrass|drygrass|driedground"),
    ("nature/trees",            r"tree|trunk|cornus|dogwood"),
    ("nature/rocks",            r"rock|cliff|stone|pebble|smallrocks"),
    ("nature/terrain",          r"terrain|tweak|sidewalkplane|houseroad|tiremark|groundsoil|dirt|sand(?!bag|_barrier|barrier)"),
    ("props/debris",            r"carboard|cardboard|debris|trash|scrap|paper|clothes|sheet0|rope|cloth|sack"),
    ("vehicles",               r"car(?!board)|sedan|humvee|motorbike|truck|headlight|tire|wheel|cart$|suv"),
    ("structures/tower",        r"tower|watchtower|firelookout|antenna|solar_panel|satellite"),
    ("structures/buildings",    r"house|garage|repairshop|petrolrefill|roof|chimney|tent|shop"),
    ("structures/walls_windows", r"window|door|blind|wall_decor|towerwall"),
    ("structures/fences",       r"fence|post01|sandbag|sand_barrier|sandbarrier|merged_sand|net|grating"),
    ("construction/wood",       r"plank|wood|pile|log|nail|brick"),
    ("construction/metal",      r"steel|profile|bracing|rack|metalsheet|metal_sheet"),
    ("props/furniture",         r"chair|table|bed|drawer|stool|shelf|armchair|rocking|chest|case01"),
    ("props/lighting",          r"lantern|lightbulb|ceiling_light|light"),
    ("props/containers",        r"barrel|box|bucket|crate|tray|container|can\b|can[0-9_]|flammabletank|jerry"),
    ("props/small",             r"bottle|cup|ashtray|cigarette|matchbox|chips|utensil|slipper|axe|wrench|gun|cartridge|picture|flag|campfire|cornflakes|food"),
    ("infra",                   r"electricpole|pole|road|sign|bridge|merged|structure|floor|base"),
]
RULES = [(c, re.compile(p, re.I)) for c, p in RULES]
FALLBACK = "props/small"

MODEL_DST = "models/firewatch/thirdparty"
MAT_DST = "materials/firewatch/thirdparty"
remap_re = re.compile(r'to\s*=\s*"([^"]+)"')


def categorise(name):
    for cat, pat in RULES:
        if pat.search(name):
            return cat
    return FALLBACK


# ---- models --------------------------------------------------------------
models = {}
for p in lib.walk_ext("models/firewatchtower", ".vmdl", ".fbx"):
    r = lib.rel(p)
    models.setdefault(os.path.splitext(os.path.basename(r))[0], []).append(r)

model_cat = {n: categorise(n) for n in models}

# ---- materials follow the models that use them ---------------------------
mat_users = collections.defaultdict(set)
for p in lib.walk_ext("models/firewatchtower", ".vmdl"):
    stem = os.path.basename(p)[:-5].lower()
    for m in remap_re.findall(lib.read_text(p)):
        if "firewatchtower" in m.lower():
            mat_users[m.lower()].add(model_cat[stem])

live, all_vmats = lib.live_vmats()
mat_cat = {}
for m in sorted(v for v in all_vmats if "firewatchtower" in v):
    cats = mat_users.get(m, set())
    if len(cats) == 1:
        mat_cat[m] = next(iter(cats))
    elif len(cats) > 1:
        mat_cat[m] = "_shared"
    else:
        mat_cat[m] = "_shared" if m in live else "_library"

# ---- textures follow their materials -------------------------------------
tex_users = collections.defaultdict(set)
for m, cat in mat_cat.items():
    for _, val in lib.texture_refs(lib.abspath(m)):
        v = val.lower().replace("\\", "/")
        if v.startswith("materials/firewatchtower/"):
            tex_users[v].add(cat)

tex_cat = {}
for p in lib.walk_ext("materials/firewatchtower", ".tga"):
    r = lib.rel(p)
    cats = tex_users.get(r, set())
    tex_cat[r] = next(iter(cats)) if len(cats) == 1 else ("_shared" if cats else "_library")

# ---- emit -----------------------------------------------------------------
rows = []
for name, files in sorted(models.items()):
    for r in files:
        rows.append((r, f"{MODEL_DST}/{model_cat[name]}/{os.path.basename(r)}", model_cat[name], "model"))
for m, cat in sorted(mat_cat.items()):
    rows.append((m, f"{MAT_DST}/{cat}/{os.path.basename(m)}", cat, "material"))
for t, cat in sorted(tex_cat.items()):
    rows.append((t, f"{MAT_DST}/{cat}/{os.path.basename(t)}", cat, "texture"))

with open("p5_renames.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["old", "new", "category", "kind"])
    w.writerows(rows)

print(f"{len(rows)} files to move\n")
for kind in ("model", "material", "texture"):
    c = collections.Counter(r[2] for r in rows if r[3] == kind)
    tot = sum(c.values())
    print(f"{kind:9} {tot:5}   " + "  ".join(f"{k}:{v}" for k, v in sorted(c.items())))

dupes = collections.Counter(r[1] for r in rows)
clash = {k: v for k, v in dupes.items() if v > 1}
print(f"\ndestination collisions: {len(clash)}")
for k, v in list(clash.items())[:10]:
    print("   ", k, v)
print("\nwrote p5_renames.csv")
