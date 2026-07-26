"""Phase 6 - the regression gate.

The invariant: every model still resolves to a material that still resolves to
the same texture *pixels*. Paths moved and names changed, so comparison is by
model basename -> {slot: md5 of the texture bytes}. Anything that reads
differently now than it did at the baseline commit is either an intended fix or
a regression, and the two are listed separately.

Baseline comes from `git show <ref>:<path>`, so it needs no second checkout.
"""
import sys, os, re, json, hashlib, subprocess, collections, lib

BASE = sys.argv[1] if len(sys.argv) > 1 else "7d9bac8"
remap = re.compile(r'to\s*=\s*"([^"]+)"')
tex = re.compile(r'^[ \t]*(Texture\w+)[ \t]+"([^"\r\n]*)"', re.M)


def git_show(ref, path):
    r = subprocess.run(["git", "-C", lib.ROOT, "show", f"{ref}:{path}"],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def git_ls(ref):
    r = subprocess.run(["git", "-C", lib.ROOT, "ls-tree", "-r", "--name-only", ref],
                       capture_output=True, text=True)
    return [x for x in r.stdout.splitlines() if x]


def lfs_oid(blob):
    """LFS pointer -> oid; otherwise hash the bytes we were given."""
    if blob[:20].startswith(b"version https://git-lfs"):
        m = re.search(rb"oid sha256:([0-9a-f]{64})", blob)
        return m.group(1).decode() if m else None
    return hashlib.sha256(blob).hexdigest()


def side(ref):
    """{model basename: {slot: texture-content-id}} for one commit."""
    files = git_ls(ref)
    vmdls = [f for f in files if f.lower().endswith(".vmdl")]
    vmats = {f.lower(): f for f in files if f.lower().endswith(".vmat")}
    tgas = {f.lower(): f for f in files if f.lower().endswith(".tga")}
    oid_cache = {}

    def oid(rel):
        if rel not in oid_cache:
            blob = git_show(ref, tgas.get(rel, rel))
            oid_cache[rel] = lfs_oid(blob) if blob else None
        return oid_cache[rel]

    out = {}
    for v in vmdls:
        blob = git_show(ref, v)
        if blob is None:
            continue
        name = os.path.basename(v)[:-5].lower()
        slots = {}
        for m in remap.findall(blob.decode("utf-8", "ignore")):
            mv = m.lower()
            if mv not in vmats:
                continue
            mb = git_show(ref, vmats[mv])
            if mb is None:
                continue
            for slot, val in tex.findall(mb.decode("utf-8", "ignore")):
                key = f"{os.path.basename(mv)}:{slot}"
                v2 = val.lower().replace("\\", "/")
                slots[key] = val if v2.startswith("[") or v2.startswith("materials/default/") else oid(v2)
        out[name] = slots
    return out


print(f"baseline {BASE} ...")
old = side(BASE)
print(f"head ...")
new = side("HEAD")

only_old = sorted(set(old) - set(new))
only_new = sorted(set(new) - set(old))
print(f"\nmodels: baseline {len(old)}  head {len(new)}  "
      f"disappeared {len(only_old)}  appeared {len(only_new)}")
if only_old:
    print("  DISAPPEARED:", only_old[:10])
if only_new:
    print("  APPEARED   :", only_new[:10])

same, changed = 0, collections.defaultdict(list)
for m in sorted(set(old) & set(new)):
    a, b = old[m], new[m]
    keys = set(a) | set(b)
    diffs = [(k, a.get(k), b.get(k)) for k in sorted(keys) if a.get(k) != b.get(k)]
    if diffs:
        changed[m] = diffs
    else:
        same += 1

print(f"models with identical resolved materials: {same}")
print(f"models whose materials changed          : {len(changed)}")

kinds = collections.Counter()
for m, diffs in changed.items():
    for k, av, bv in diffs:
        slot = k.split(":")[1]
        if av is None:
            kinds[f"{slot}: slot added"] += 1
        elif bv is None:
            kinds[f"{slot}: slot removed"] += 1
        elif isinstance(bv, str) and bv.startswith("["):
            kinds[f"{slot}: -> scalar"] += 1
        elif isinstance(bv, str) and bv.startswith("materials/default/"):
            kinds[f"{slot}: -> engine default"] += 1
        else:
            kinds[f"{slot}: DIFFERENT PIXELS"] += 1
print("\nwhat changed:")
for k, n in kinds.most_common():
    print(f"   {n:5}  {k}")

pix = {m: [d for d in ds if d[1] and d[2] and not str(d[2]).startswith(("[", "materials/default/"))
           and not str(d[1]).startswith(("[", "materials/default/"))]
       for m, ds in changed.items()}
pix = {m: d for m, d in pix.items() if d}
print(f"\nmodels now showing DIFFERENT texture pixels: {len(pix)}")
for m, d in sorted(pix.items()):
    for k, av, bv in d:
        print(f"   {m:28} {k}")
json.dump({m: [[k, str(a), str(b)] for k, a, b in v] for m, v in changed.items()},
          open("p6_changes.json", "w"), indent=1)
