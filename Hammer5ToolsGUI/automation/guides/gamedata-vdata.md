# Gamedata (`.vdata`)

A `.vdata` file is a KeyValues3 document of named data entries plus a
`generic_data_type` naming the schema those entries follow. CS2 uses them for
table-shaped game data — detail prop types, loadout and economy tables, and
similar — rather than for anything geometric.

```
hammer5tools.vdata_read  path=<file>                       # summary: type + entry names
hammer5tools.vdata_read  path=<file> detail="full"         # every entry body
hammer5tools.vdata_read  path=<file> select="<entry name>" # one entry
hammer5tools.vdata_write path=<file> entries={…} generic_data_type="…" dry_run=true
hammer5tools.vdata_edit  path=<file> updates={…} remove_keys=[…] dry_run=true
```

## Read the summary first

A gamedata file is often a long table, and its entries are the bulk of it. The
default summary returns `generic_data_type`, `entry_count`, and `entry_names` —
enough to find the entry you want — and `select` then returns just that one.
Reach for `detail="full"` only when you genuinely need every body.

## Writing

`vdata_write` creates a document from an `entries` mapping and a
`generic_data_type`; the type must match the schema the engine expects for that
file, so copy it from an existing file of the same kind rather than inventing
one. `vdata_edit` adds or updates the keys in `updates` and deletes the ones in
`remove_keys`, leaving everything else alone — prefer it over a full rewrite.

Both re-serialise through the KV3 writer, so formatting is normalised. Preview
with `dry_run: true` when that matters.

## Verifying

`.vdata` compiles like any other asset:

```
hammer5tools.compile_asset path=<file>
```

A wrong `generic_data_type` or a field the schema does not know is a compile
error, not a silent one — which makes the compiler the fastest way to check a
hand-built table. See `compile-verify`.
