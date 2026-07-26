"""Phase 3 - the actual material repair.

  1. extract cutout alphas -> <name>_trans.tga           (H5T texture_utils.extract_alpha)
  2. wire F_ALPHA_TEST + TextureTranslucency1 into the materials that use them
  3. F_RENDER_BACKFACES on foliage - cutout cards are modelled single-sided
  4. clamp roughness scalars that came out of UE above 1.0
  5. repoint the three unambiguously cross-wired materials

Run with --apply to write; default is a dry run.
"""
import sys, os, re, collections
sys.path.insert(0, r"D:\CG\Projects\Other\Hammer5Tools")
import lib
from src.forms.unreal_converter.texture_utils import extract_alpha

APPLY = "--apply" in sys.argv
MATDIR = "materials/firewatchtower"

# Thick foliage cards want a lower cutoff or the silhouette erodes; hard-edged
# man-made cutouts (netting, grating, tarpaulin) want Hammer's default.
FOLIAGE = re.compile(r"grass|leaf|leaves|fern|festuca|bush|flower|plant|moss|driedground|deadgrass|drygrass|treemid|cornustree")
FOLIAGE_REF, DEFAULT_REF = 0.33, 0.5

# Wrong texture on a live material where the right one demonstrably exists.
# Everything else flagged by the audit is a UE material instance sharing a
# trimsheet or atlas, which is correct and left alone.
REWIRE = {
    "materials/firewatchtower/mi_cloth.vmat": {
        "TextureColor1": "materials/firewatchtower/cloth_color.tga"},
    "materials/firewatchtower/mi_car_02.vmat": {
        "TextureColor1": "materials/firewatchtower/car_02_color.tga",
        "TextureNormal1": "materials/firewatchtower/car_02_normal.tga",
        "TextureRoughness1": "materials/firewatchtower/car_02_rough.tga",
        "TextureMetalness1": "materials/firewatchtower/car_02_metal.tga",
        "TextureAmbientOcclusion1": "materials/firewatchtower/car_02_ao.tga"},
    # t_net_b was never imported, so the author reached for rust. net_color.tga
    # arrived in the second import pass and carries the cutout mask as well.
    "materials/firewatchtower/mi_fence_net.vmat": {
        "TextureColor1": "materials/firewatchtower/net_color.tga"},
}

SCALAR = re.compile(r'^([ \t]*)(Texture(?:Roughness|Metalness)\d*)([ \t]+)"\[([-0-9. ]+)\]"([ \t\r]*)$', re.M)


def clamp_scalars(text):
    n = 0

    def sub(m):
        nonlocal n
        indent, slot, gap, vals, tail = m.groups()
        nums = [float(x) for x in vals.split()]
        if all(-0.0001 <= x <= 1.0001 for x in nums[:3]):
            return m.group(0)
        n += 1
        c = [min(1.0, max(0.0, x)) for x in nums[:3]]
        return f'{indent}{slot}{gap}"[{c[0]:.6f} {c[1]:.6f} {c[2]:.6f} 0.000000]"{tail}'

    return SCALAR.sub(sub, text), n


# ---- 1. extract the cutout masks -----------------------------------------
colour_users = collections.defaultdict(list)
for vm in lib.walk_ext("materials", ".vmat"):
    for slot, val in lib.texture_refs(vm):
        if lib.slot_kind(slot) == "color":
            colour_users[val.lower().replace("\\", "/")].append(lib.rel(vm))

masks = {}                                    # color tga -> trans tga
for p in lib.walk_ext(MATDIR, ".tga"):
    r = lib.rel(p)
    if not r.endswith("_color.tga") or r not in colour_users:
        continue
    out_r = r[:-len("_color.tga")] + "_trans.tga"
    if APPLY:
        if extract_alpha(p, lib.abspath(out_r)):
            masks[r] = out_r
    else:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".tga", delete=False) as t:
            tmp = t.name
        if extract_alpha(p, tmp):
            masks[r] = out_r
        os.unlink(tmp)

# ---- 2-5. rewrite the materials -------------------------------------------
stats = collections.Counter()
touched = []
for vm in lib.walk_ext("materials", ".vmat"):
    r, text, orig = lib.rel(vm), lib.read_text(vm), None
    orig = text

    forced = REWIRE.get(r, {})
    colour = next((v for s, v in lib.texture_refs(vm) if lib.slot_kind(s) == "color"), "")
    colour = forced.get("TextureColor1", colour).lower().replace("\\", "/")
    mask = masks.get(colour)
    has_flag = "F_ALPHA_TEST" in text
    foliage = bool(FOLIAGE.search(os.path.basename(r)))

    # forced rewires + drop the stale .png translucency ref
    def fn(slot, val):
        if slot in forced:
            return forced[slot]
        if lib.slot_kind(slot) == "trans" and mask and val != mask:
            return mask
        return None

    text, n = lib.rewrite_texture_lines(text, fn)
    stats["rewired"] += len(forced) if forced else 0

    # insert the alpha-test block where it's missing
    if mask and not has_flag:
        ref = FOLIAGE_REF if foliage else DEFAULT_REF
        text = re.sub(r'(shader "[^"]+"\r?\n)',
                      r'\1\n\t//---- Translucent ----\n\tF_ALPHA_TEST 1\n', text, count=1)
        text = re.sub(r'(^[ \t]*TextureTintMask\d*[ \t]+"[^"]*"[ \t]*\r?$)',
                      r'\1\n\tTextureTranslucency1 "' + mask + '"', text, count=1, flags=re.M)
        text = text.rstrip().rstrip("}").rstrip() + (
            f'\n\n\t//---- Translucent ----\n'
            f'\tg_flAlphaTestReference "{ref:.3f}"\n'
            f'\tg_flAntiAliasedEdgeStrength "1.000"\n}}\n')
        stats["alpha_test"] += 1

    # cutout foliage is modelled as single-sided cards
    if foliage and mask and "F_RENDER_BACKFACES" not in text:
        text = re.sub(r'(shader "[^"]+"\r?\n)',
                      r'\1\n\t//---- Faces ----\n\tF_RENDER_BACKFACES 1\n', text, count=1)
        stats["backfaces"] += 1

    text, nc = clamp_scalars(text)
    stats["clamped"] += nc

    if text != orig:
        touched.append(r)
        if APPLY:
            lib.write_text(vm, text)

print(f"cutout masks extracted : {len(masks)}")
print(f"alpha-test blocks added: {stats['alpha_test']}")
print(f"backfaces enabled      : {stats['backfaces']}")
print(f"roughness clamped      : {stats['clamped']}")
print(f"textures rewired       : {stats['rewired']}")
print(f"vmats touched          : {len(touched)}")
print("\nmasks:", *[f"\n  {v.split('/')[-1]}" for v in sorted(masks.values())])
print("\ndry run - pass --apply to write" if not APPLY else "\nAPPLIED")
