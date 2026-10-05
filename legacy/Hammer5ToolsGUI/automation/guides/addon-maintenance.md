# Addon maintenance

The tools that operate on a whole addon rather than one asset. All of them are
paged: read `total` and `truncated` before treating a page as the whole answer.

## Finding what an asset needs

```
hammer5tools.resolve_dependencies path=<asset> [addon_dir=] [limit=200] [offset=]
```

Recursive. Returns references split by kind — `materials`, `textures`, `models`,
`soundevents`, `particles`, `smartprops` — plus a paged flat `all_references`.
The per-kind lists are complete; the flat list is the paged one, so prefer the
categories and page the flat list only when you need it.

Works on `.vmat`, `.vmdl`, `.vtex`, `.vsmart`, and `.vmap`. Maps go through Core,
which reads the real reference table rather than guessing from text.

## Finding what nothing needs

```
hammer5tools.find_unused_assets map_path=<map> [addon_dir=] [limit=100]
```

Compares files on disk against what the map actually pulls in, and reports
`unused_count` and `total_size_bytes` before the list. Read the counts first.

This is a map-relative answer, not an absolute one: an asset used only by a
second map in the same addon, or only by a SmartProp that no map places yet, will
be listed. Never delete from this list without checking why each entry is there.

## Checking integrity

```
hammer5tools.validate_addon [addon_name=] [cs2_dir=] [limit=50]
```

Runs the Core validator and reports `status_code`, `clean`, `issues_count`, and a
paged `issues` list filtered out of the full log. `log_line_count` tells you how
much was filtered. Both arguments fall back to the configured addon and CS2 path.

## Moving or renaming assets

```
hammer5tools.vmap_rewrite_references vmap_path=<map> replacements={from: to} dry_run=true
```

A reference matches when it equals the search path *or starts with it*, so a
directory prefix moves a whole tree in one call — and a too-short prefix silently
matches more than you meant. Always run with `dry_run: true` first and read
`planned_replacements`; the write itself is atomic.

The wider rename is a sequence, not one call: move the files, rewrite the map
references, then recompile the affected assets. A material rename also means
updating the texture paths inside its shader block, which `vmat_read` shows you.

## Compile order

Textures, then materials, then models, then SmartProps, then maps. A missing
`.vmdl_c` surfaces as a warning rather than a failure, so a map can appear to
compile while referencing models that were never built. See `compile-verify`.

## Is the Core even loaded

```
hammer5tools.core_status
```

Reports whether the versioned NativeAOT Core can be loaded. Anything that depends
on Core — map references, SmartProp evaluation, VPK access, validation — fails
without it, so check this first when several unrelated tools error at once.
