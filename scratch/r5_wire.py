"""Wire the two unwired materials whose textures were sitting there unreferenced.

Same class of bug as woodpile.vmdl's ten grey slots: the import wrote a material
with default/scalar slots and left the real maps on disk with nothing pointing at
them.

  mi_grating     - all six maps in _library/, including a cutout mask
                   (77% off / 4% mid / 19% on - a shape mask, not a blend mask),
                   so it also gets F_ALPHA_TEST. Renders as an opaque grey slab
                   right now.
  sedan02_body   - colour/ao/metal/rough beside it; the vmat used a flat dark-red
                   scalar. No normal map exists, so that slot stays default.

  python r5_wire.py [--apply]
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

APPLY = "--apply" in sys.argv
LIB = "materials/firewatch/thirdparty/_library"
VEH = "materials/firewatch/thirdparty/vehicles"

JOBS = {
    "materials/firewatch/thirdparty/props/furniture/mi_grating.vmat": {
        "slots": {"TextureColor1": f"{LIB}/grating_color.tga",
                  "TextureNormal1": f"{LIB}/grating_normal.tga",
                  "TextureRoughness1": f"{LIB}/grating_rough.tga",
                  "TextureMetalness1": f"{LIB}/grating_metal.tga",
                  "TextureAmbientOcclusion1": f"{LIB}/grating_ao.tga",
                  "TextureTranslucency1": f"{LIB}/grating_trans.tga"},
        "alpha_test": 0.5,          # hard-edged metal, not soft foliage
        "backfaces": True,          # modelled as single-sided plates
    },
    "materials/firewatch/thirdparty/vehicles/sedan02_body.vmat": {
        "slots": {"TextureColor1": f"{VEH}/sedan02_body_color.tga",
                  "TextureRoughness1": f"{VEH}/sedan02_body_rough.tga",
                  "TextureMetalness1": f"{VEH}/sedan02_body_metal.tga",
                  "TextureAmbientOcclusion1": f"{VEH}/sedan02_body_ao.tga"},
    },
}

for vmat, job in JOBS.items():
    p = lib.abspath(vmat)
    if not os.path.exists(p):
        raise SystemExit(f"ABORT: {vmat} missing")
    for t in job["slots"].values():
        if not os.path.exists(lib.abspath(t)):
            raise SystemExit(f"ABORT: texture missing: {t}")

    txt = lib.read_text(p)
    want = job["slots"]

    def fix(slot, val):
        return want.get(slot)

    new, n = lib.rewrite_texture_lines(txt, fix)

    # TextureTranslucency1 has no line to rewrite - add it after TextureRoughness1.
    added = 0
    for slot, val in want.items():
        if not re.search(rf'^\s*{slot}\s', new, re.M):
            new = re.sub(r'^([ \t]*)(TextureRoughness1[ \t]+"[^"]*"[ \t\r]*)$',
                         rf'\1\2\n\1{slot} "{val}"', new, count=1, flags=re.M)
            added += 1

    if job.get("alpha_test"):
        if "F_ALPHA_TEST" not in new:
            new = re.sub(r'^(\s*shader\s+"[^"]*"[ \t\r]*)$',
                         r'\1\n\n\t//---- Translucent ----\n\tF_ALPHA_TEST 1',
                         new, count=1, flags=re.M)
        if job.get("backfaces") and "F_RENDER_BACKFACES" not in new:
            new = re.sub(r'^(\tF_ALPHA_TEST 1[ \t\r]*)$',
                         r'\1\n\n\t//---- Faces ----\n\tF_RENDER_BACKFACES 1',
                         new, count=1, flags=re.M)
        if "g_flAlphaTestReference" not in new:
            tail = (f'\n\t//---- Translucent ----\n'
                    f'\tg_flAlphaTestReference "{job["alpha_test"]:.3f}"\n'
                    f'\tg_flAntiAliasedEdgeStrength "1.000"\n')
            i = new.rfind("}")
            new = new[:i] + tail + new[i:]

    print(f"{vmat}: {n} slots rewired, {added} slots added"
          + (", alpha-test" if job.get("alpha_test") else ""))
    for slot, val in sorted(want.items()):
        print(f"    {slot:28} {val}")
    if APPLY:
        lib.write_text(p, new)

print("\napplied" if APPLY else "\n(report only - pass --apply)")
