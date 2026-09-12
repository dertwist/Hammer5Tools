# Official CS2 assets

Stock Valve content is split across several archives under `game/` —
`csgo/pak01_dir.vpk`, `csgo_core`, `csgo_imported`, `csgo_lv`, and
`core/pak01_dir.vpk`. These tools read all of them directly; you do not need to
unpack anything.

Which archive holds an asset is **not** guessable from its path:
`models/dev/dev_cube.vmdl` is in `csgo`, `models/editor/placeholder_box.vmdl` is
in `core`. Searching one archive and concluding an asset does not exist is a
mistake the tools now prevent — the `archives` field in a search result lists
what was actually covered.

## Searching

```
hammer5tools.vpk_search query=<substring> [extension=] [game_dir=] [limit=100]
```

Case-insensitive substring match on the full internal path, so `query` can be a
directory (`"models/props/"`), a name fragment (`"dev_cube"`), or both. The
`extension` filter takes the bare extension (`"vmdl"`, `"vmat"`, `"vtex"`).

Results are capped by `limit` (default 100) and the cap is applied while
scanning, so a broad query returns the first N in archive order rather than the
best N. Narrow the query rather than raising the limit.

Search reports **source** names — `models/dev/dev_cube.vmdl` — even though the
archive stores compiled entries (`.vmdl_c`).

## Extracting

```
hammer5tools.vpk_extract internal_path=<path> output_path=<local file>
```

Accepts either spelling: hand it the path exactly as `vpk_search` reported it and
it resolves the compiled `_c` entry, or pass the `_c` name directly. The result's
`internal_path` tells you which one it actually read. What lands on disk is the
**compiled** asset, so treat it as a reference to point at, not a source file to
edit.

## Using stock assets

Most of the time you want to reference stock content, not copy it — a
`prop_static` or a SmartProp model slot can name `models/...` directly and the
engine resolves it from the archive. Extract only when you need to inspect a
file or use it as the basis for something new.

When you do copy one into an addon, it becomes yours to maintain: it will not
track Valve's updates, and `find_unused_assets` will report it the moment nothing
references it.

## Dev and blockout content

- `models/editor/placeholder_box.vmdl` (plus `placeholder_small_box` and
  `placeholder_sphere`) — the blockout boxes, in `core`
- `models/dev/dev_cube.vmdl`, `error.vmdl` — dev models, in `csgo`
- `materials/dev/blockout/` — blockout materials

See `vmap-authoring` for using these as `prop_static` blockout geometry.
