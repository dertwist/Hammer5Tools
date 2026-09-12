# Particle snapshots and Unreal porting

Two smaller tool families that are easy to misuse because their names suggest
more than they do.

## Particle snapshots (`.vsnap`)

A `.vsnap` is a point cloud consumed by the particle system: named vertex streams
over a fixed point count. `Position` is the stream that always matters.

```
hammer5tools.vsnap_read     path=<file>                       # streams, point_count, sample positions
hammer5tools.vsnap_write    path=<file> positions=[[x,y,z],…]
hammer5tools.vsnap_generate path=<file> primitive="sphere" count=2000 size=128
hammer5tools.vsnap_edit     path=<file> lighting={first_index:…, second_index:…}
```

`vsnap_read` returns stream names, types, counts, and only the **first ten**
positions as a sample — it is a summary, not the cloud. Do not treat
`sample_positions` as the data.

`vsnap_generate` builds `cube`, `sphere`, or `cylinder` clouds and is the right
starting point for most snapshots; `vsnap_write` is for a cloud you computed
yourself. `vsnap_edit` currently applies a two-point lighting gradient and
nothing else — it is not a general editor.

Writing a snapshot goes through Core's serializer, so `core_status` failing means
these fail too.

## Unreal content (read-only)

These inspect a loose Unreal `Content` directory. They **read**; nothing here
converts or imports.

```
hammer5tools.unreal_info       content_dir=<Content dir>            # mounted asset counts
hammer5tools.unreal_list       content_dir=<…> [substring=]         # package paths
hammer5tools.unreal_references content_dir=<…> object_path=<pkg>    # deduplicated refs
```

`content_dir` is the Unreal `Content` folder itself, not the project root.
`unreal_list` filters by case-insensitive substring, which is how you narrow a
large project before asking for references.

Use these to plan a port — what a package depends on, how much there is — and
then do the actual conversion through the Unreal Porter in the application. The
automation surface deliberately stops at inspection.

## Where these fit

Neither family participates in the normal compile chain. A `.vsnap` is referenced
by a particle system, and Unreal packages are not Source 2 assets at all, so
`resolve_dependencies` and `validate_addon` will not reason about either. Verify
snapshots by reading them back and checking `point_count` and `stream_count`.
