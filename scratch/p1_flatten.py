"""Phase 1 — replace constant-fill TGAs with vmat scalars / engine defaults, then delete them.

Flat colour maps are deliberately left alone: csgo_environment's TextureColor slot is
never given a scalar anywhere in this pack, and 3 files aren't worth the unknown.

Run with --apply to write; default is a dry run.
"""
import sys, os, collections, lib

APPLY = "--apply" in sys.argv


def scalar(v):
    return f'[{v:.6f} {v:.6f} {v:.6f} 0.000000]'


def replacement(kind, val):
    """Constant fill -> what the vmat should say instead. None = leave the file alone."""
    if kind == "ao":
        # An all-black AO map renders the surface fully occluded - that is a broken
        # export, not intent. Every constant AO becomes the engine default (white).
        return "materials/default/default_ao.tga"
    if kind == "normal":
        return "materials/default/default_normal.tga"
    if kind in ("metal", "rough"):
        return scalar(val[0] / 255.0)
    return None                      # color / mask / height: hands off


tgas = lib.walk_ext("materials/firewatchtower", ".tga")
flat = {}
for p in tgas:
    v = lib.flat_value(lib.tga_stats(p))
    if v is not None:
        flat[lib.rel(p)] = v

vmats = lib.walk_ext("materials", ".vmat")
refs = collections.defaultdict(list)          # flat tga -> [(vmat, slot)]
for vm in vmats:
    for slot, val in lib.texture_refs(vm):
        v = val.lower().replace("\\", "/")
        if v in flat:
            refs[v].append((vm, slot))

# a flat file is only deletable if every reference to it can be replaced
skip = set()
for f, uses in refs.items():
    for _, slot in uses:
        if replacement(lib.slot_kind(slot), flat[f]) is None:
            skip.add(f)

edits = collections.Counter()
for vm in vmats:
    text = lib.read_text(vm)

    def fn(slot, val):
        v = val.lower().replace("\\", "/")
        if v not in flat or v in skip:
            return None
        return replacement(lib.slot_kind(slot), flat[v])

    new, n = lib.rewrite_texture_lines(text, fn)
    if n:
        edits[lib.rel(vm)] = n
        if APPLY:
            lib.write_text(vm, new)

doomed = sorted(f for f in flat if f not in skip)
freed = sum(os.path.getsize(lib.abspath(f)) for f in doomed)

print(f"flat tgas            : {len(flat)}")
print(f"  kept (flat colour) : {len(skip)}  {sorted(skip)}")
print(f"  removable          : {len(doomed)}  ({freed/1048576:.1f} MB)")
print(f"vmats edited         : {len(edits)}  ({sum(edits.values())} texture lines)")
print(f"  of which all-black AO fixes: "
      f"{sum(1 for f in refs if f in flat and flat[f]==(0,) and lib.slot_kind(refs[f][0][1])=='ao')}")

if APPLY:
    for f in doomed:
        os.remove(lib.abspath(f))
    print(f"\nAPPLIED: deleted {len(doomed)} files, edited {len(edits)} vmats")
else:
    print("\ndry run - pass --apply to write")
