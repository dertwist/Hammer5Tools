"""Exactly which files reference the firewatchtower pack, and how many times.

Determines what the move actually has to rewrite - and in particular whether the
12 MB de_firewatch.vmap is in scope at all.
"""
import os, re, collections, lib

PAT = re.compile(rb"(?:models|materials)/firewatchtower/[A-Za-z0-9_/\.\-]+\.(?:vmdl|vmat|fbx|tga)", re.I)

rows = []
for sub in ("maps", "smartprops", "models", "materials", "particles", "particels",
            "lighting", "postprocess", "scripts", "panorama"):
    d = os.path.join(lib.ROOT, sub)
    if not os.path.isdir(d):
        continue
    for dp, _, fns in os.walk(d):
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                data = open(p, "rb").read()
            except OSError:
                continue
            hits = PAT.findall(data)
            if hits:
                rows.append((lib.rel(p), len(hits), len(set(hits)), os.path.getsize(p)))

rows.sort(key=lambda r: -r[1])
by_ext = collections.Counter()
for r, n, u, _ in rows:
    by_ext[os.path.splitext(r)[1]] += n

print(f"{'file':52} {'refs':>6} {'uniq':>5} {'size':>9}")
print("-" * 78)
for r, n, u, s in rows[:30]:
    print(f"{r:52} {n:6} {u:5} {s/1024:8.0f}K")
print(f"\n{len(rows)} files reference the pack; refs by type: {dict(by_ext)}")

binary = [r for r in rows if r[0].endswith((".vmap", ".vsmart"))]
print(f"\nbinary files needing DMX rewrite: {len(binary)}")
for r, n, u, s in binary:
    print(f"   {r:50} {n:6} refs  {s/1048576:.1f} MB")
