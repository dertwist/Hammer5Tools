"""Classify alpha-carrying colour maps: cutout mask vs blend/detail mask.

A cutout mask is bimodal - nearly every pixel is fully on or fully off, because it
describes a *shape*. A blend mask sits in the middle of the range because it
describes a *gradient*. Only the former wants F_ALPHA_TEST; running alpha-test on
the latter would punch holes in solid geometry.
"""
import struct, collections, lib

MID_LO, MID_HI = 32, 223          # "neither on nor off"


def alpha_hist(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 18 or data[2] != 2 or data[16] != 32:
        return None
    w, h = struct.unpack("<HH", data[12:16])
    off = 18 + data[0]
    px = data[off:off + w * h * 4]
    if len(px) < w * h * 4:
        return None
    a = px[3::4]
    hist = collections.Counter(a)
    n = len(a)
    return dict(
        w=w, h=h, n=n,
        off=sum(v for k, v in hist.items() if k < MID_LO) / n,
        mid=sum(v for k, v in hist.items() if MID_LO <= k <= MID_HI) / n,
        on=sum(v for k, v in hist.items() if k > MID_HI) / n,
        lo=min(a), hi=max(a),
    )


rows = []
for p in lib.walk_ext("materials/firewatchtower", ".tga"):
    st = alpha_hist(p)
    if st and st["lo"] != st["hi"]:
        rows.append((lib.rel(p), st))

# which vmats use each as TextureColor
users = collections.defaultdict(list)
for vm in lib.walk_ext("materials", ".vmat"):
    text = lib.read_text(vm)
    for slot, val in lib.texture_refs(vm):
        if lib.slot_kind(slot) == "color":
            users[val.lower().replace("\\", "/")].append((lib.rel(vm), "F_ALPHA_TEST" in text))

print(f"{'texture':46} {'off%':>6} {'mid%':>6} {'on%':>6}  verdict   users")
print("-" * 100)
cutout, blend = [], []
for r, st in sorted(rows, key=lambda x: -x[1]["mid"]):
    is_cut = st["mid"] < 0.10 and st["off"] > 0.02
    (cutout if is_cut else blend).append(r)
    u = users.get(r, [])
    print(f"{r.split('/')[-1]:46} {st['off']*100:6.1f} {st['mid']*100:6.1f} {st['on']*100:6.1f}  "
          f"{'CUTOUT' if is_cut else 'blend ':8}  {len(u)}{' [has F_ALPHA_TEST]' if any(x[1] for x in u) else ''}")

print(f"\ncutout: {len(cutout)}   blend/detail: {len(blend)}")
print("\ncutout materials to fix:")
seen = set()
for t in cutout:
    for vm, has in users.get(t, []):
        if not has:
            seen.add((vm, t))
for vm, t in sorted(seen):
    print(f"  {vm.split('/')[-1]:40} <- {t.split('/')[-1]}")
print(f"\n=> {len(seen)} vmats need the alpha-test block")
print(f"=> {len(set(t for _, t in seen))} alphas to extract")
