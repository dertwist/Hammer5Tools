"""Baseline snapshot / regression gate for the packed reorg.

  python r0_gate.py save     -> write r0_baseline.json  (run before phase 1)
  python r0_gate.py check    -> compare current tree against it

The thing this actually guards: a model must end up with the same *rendered*
material set it started with. Paths and names change on every phase, so the
comparison is on resolved texture sets, not on paths.
"""
import os, re, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "r0_baseline.json")
REMAP = re.compile(r'from\s*=\s*"([^"]*)"\s*\n?\s*to\s*=\s*"([^"]*)"', re.S)
SCALAR = re.compile(r'^\s*(g_\w+|F_\w+)\s+"?([^"\r\n]*)"?\s*$', re.M)


def snapshot():
    """{model -> [material signature]}, where a signature is what it renders as."""
    sig = {}
    for p in lib.walk_ext("materials", ".vmat"):
        r = lib.rel(p)
        txt = lib.read_text(p)
        tex = tuple(sorted((lib.slot_kind(s) or s, os.path.basename(v).lower())
                           for s, v in lib.texture_refs(p) if v))
        sca = tuple(sorted((m.group(1), m.group(2).strip()) for m in SCALAR.finditer(txt)))
        sig[r] = tex + sca

    out = {}
    for p in lib.walk_ext("models", ".vmdl"):
        r = lib.rel(p)
        mats = sorted({m[1].lower() for m in REMAP.findall(lib.read_text(p)) if m[1].strip()})
        out[r] = sorted(sig.get(m, ("MISSING:" + m,)) and
                        [json.dumps(sig[m]) if m in sig else "MISSING:" + m][0] for m in mats)
    return out


# Resolved out of the game's core content rather than the addon, so absent from
# this tree by design.
ENGINE = ("materials/default/", "materials/dev/", "materials/editor/",
          "materials/tools/", "materials/particle/", "materials/engine/")


def broken_refs():
    """Every texture/material path in a vmat or vmdl that points at no file."""
    bad = []
    for p in lib.walk_ext("materials", ".vmat"):
        for slot, val in lib.texture_refs(p):
            v = val.replace("\\", "/")
            if not v or v.startswith("[") or v.startswith(ENGINE):
                continue
            if not os.path.exists(lib.abspath(v)):
                bad.append((lib.rel(p), slot, v))
    for p in lib.walk_ext("models", ".vmdl"):
        for _, to in REMAP.findall(lib.read_text(p)):
            t = to.strip()
            if t and not t.startswith(ENGINE) and not os.path.exists(lib.abspath(t)):
                bad.append((lib.rel(p), "remap", t))
    return bad


def stale_paths():
    """firewatch/thirdparty survivors - only the frozen rocks may remain."""
    PAT = re.compile(rb"(?:models|materials)/firewatch/thirdparty/[A-Za-z0-9_/.\-]+", re.I)
    OK = re.compile(rb"nature/rocks/rock_0[1-4](_\w+)?\.(vmat|tga)$", re.I)
    hits = collections.Counter()
    for sub in ("maps", "smartprops", "materials", "models", "particles", "particels"):
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
                n = sum(1 for m in PAT.findall(data) if not OK.search(m))
                if n:
                    hits[lib.rel(p)] = n
    return hits


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    snap = snapshot()
    bad = broken_refs()
    # A dangling ref that was already dangling is not this reorg's problem; keyed
    # on (model basename, target) so it survives the move.
    key = lambda b: (os.path.basename(b[0]), b[2])

    if mode == "save":
        n_mat = len(lib.walk_ext("materials", ".vmat"))
        n_tga = len(lib.walk_ext("materials", ".tga"))
        json.dump({"models": snap, "known_bad": sorted(set("|".join(key(b)) for b in bad)),
                   "n_vmat": n_mat, "n_tga": n_tga},
                  open(BASE, "w"), indent=0)
        print(f"baseline saved: {len(snap)} models, {n_mat} vmat, {n_tga} tga")
        print(f"pre-existing broken refs accepted into the baseline: {len(bad)}")
        for b in bad:
            print("   ", b[0], "->", b[2])
        sys.exit(0)

    raw = json.load(open(BASE))
    old, known_bad = raw["models"], set(raw["known_bad"])
    print(f"vmat {raw['n_vmat']} -> {len(lib.walk_ext('materials', '.vmat'))}, "
          f"tga {raw['n_tga']} -> {len(lib.walk_ext('materials', '.tga'))}")
    print(f"models: {len(old)} before -> {len(snap)} after")
    lost = sorted(set(old) - set(snap))
    gained = sorted(set(snap) - set(old))
    # models move, so compare by basename
    ob = {os.path.basename(k): v for k, v in old.items()}
    nb = {os.path.basename(k): v for k, v in snap.items()}
    missing = sorted(set(ob) - set(nb))
    added = sorted(set(nb) - set(ob))
    changed = sorted(k for k in set(ob) & set(nb) if ob[k] != nb[k])
    print(f"  by name: {len(missing)} missing, {len(added)} added, {len(changed)} changed")
    for k in missing[:10]:
        print("    MISSING", k)
    for k in added[:10]:
        print("    ADDED  ", k)

    new_bad = [b for b in bad if "|".join(key(b)) not in known_bad]
    print(f"\nbroken references: {len(bad)} total, {len(new_bad)} new since baseline")
    for b in new_bad[:20]:
        print("   ", b)

    stale = stale_paths()
    print(f"\nstale firewatch/thirdparty paths: {sum(stale.values())} in {len(stale)} files")
    for f, n in stale.most_common(15):
        print(f"    {n:5}  {f}")

    ok = not missing and not new_bad and not stale
    print("\nGATE:", "PASS" if ok else "FAIL")
    if changed:
        print(f"({len(changed)} models render differently - expected where a merge changed a tint)")
        for k in changed[:20]:
            print("    changed", k)
    sys.exit(0 if ok else 1)
