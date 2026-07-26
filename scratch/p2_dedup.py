"""Phase 2 — collapse byte-identical textures that play the same role.

Grouping is (md5, slot-suffix), not md5 alone: the same grey image legitimately
serves as one material's AO and another's metalness, and collapsing those onto a
single filename would leave a map called _metal doing an AO job. Same-role
duplicates - which is where the two import passes overlap - merge; cross-role
coincidences are left alone.

Run with --apply to write; default is a dry run.
"""
import sys, os, collections, lib

APPLY = "--apply" in sys.argv


def canon_score(r):
    """Higher = better canonical name. Prefers the _color/_normal/... convention."""
    base = os.path.basename(r)
    stem, suf = lib.split_name(base)
    return (
        0 if base.startswith(("t_", "mi_", "m_")) else 10,   # no import-pass prefix
        5 if suf else 0,                                      # recognised role suffix
        -len(base),                                           # shorter wins
        base,                                                 # stable tiebreak
    )


tgas = lib.walk_ext("materials/firewatchtower", ".tga")
groups = collections.defaultdict(list)
for p in tgas:
    r = lib.rel(p)
    _, suf = lib.split_name(os.path.basename(r))
    groups[(lib.md5(p), suf)].append(r)

alias = {}          # doomed -> canonical
for (_, suf), members in groups.items():
    if len(members) < 2:
        continue
    winner = max(members, key=canon_score)
    for m in members:
        if m != winner:
            alias[m] = winner

edits = collections.Counter()
for vm in lib.walk_ext("materials", ".vmat"):
    text = lib.read_text(vm)
    new, n = lib.rewrite_texture_lines(text, lambda slot, val: alias.get(val.lower().replace("\\", "/")))
    if n:
        edits[lib.rel(vm)] = n
        if APPLY:
            lib.write_text(vm, new)

freed = sum(os.path.getsize(lib.abspath(f)) for f in alias)
merged = collections.Counter(suf for (_, suf), m in groups.items() if len(m) > 1)

print(f"textures scanned  : {len(tgas)}")
print(f"duplicate groups  : {sum(1 for m in groups.values() if len(m) > 1)}")
print(f"  by role         : {dict(merged)}")
print(f"files removed     : {len(alias)}  ({freed/1073741824:.2f} GB)")
print(f"vmats edited      : {len(edits)}  ({sum(edits.values())} texture lines)")

sample = [k for k in alias if k.startswith("materials/firewatchtower/t_")][:6]
print("\nsample merges:")
for s in sample:
    print(f"  {os.path.basename(s):40} -> {os.path.basename(alias[s])}")

if APPLY:
    lib.assert_no_refs(alias)          # nothing is deleted until every ref is repointed
    for f in alias:
        os.remove(lib.abspath(f))
    print(f"\nAPPLIED: deleted {len(alias)} files, edited {len(edits)} vmats")
else:
    print("\ndry run - pass --apply to write")
