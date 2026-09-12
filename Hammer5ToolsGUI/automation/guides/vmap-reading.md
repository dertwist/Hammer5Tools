# Reading VMAP levels

For creating or modifying one, see the `vmap-authoring` topic.

Core deserializes a `.vmap` completely — the node tree, every entity with its
properties, triangulated brush meshes, model placements, and SmartProp
placements with their per-instance variable overrides. The tools shape that,
because a production map's node tree is roughly six million tokens.

```
hammer5tools.vmap_read  path=<map>                        # counts by entity and node class
hammer5tools.vmap_read  path=<map> classname="prop_static" limit=50
hammer5tools.vmap_read  path=<map> select="entities[class=light_omni2].origin"
hammer5tools.vmap_scene path=<map>                        # mesh/prop/smartprop counts, world bounds
hammer5tools.vmap_scene path=<map> include="smartprops"   # placements + variable overrides
hammer5tools.vmap_scene path=<map> include="props" resource="models/props/x.vmdl"
hammer5tools.vmap_references path=<map>                   # just the content-relative references
```

Start with the summary. A full map summarises to a few hundred tokens and tells
you the entity class histogram, which is how you find what to ask for next:
`classname="light_omni2"` for the lights, `classname="info_player_terrorist"`
for the spawns, `classname="prop_static"` for placed models.

**Every entity class is available**, because entities are returned generically
with all their properties. Decals (`info_overlay`), ropes (`move_rope`,
`keyframe_rope`), triggers, lights, sound entities, and anything a future game
update adds all come back the same way — look at `entity_classes` in the summary
and narrow with `classname`. There is no per-class allowlist to fall behind.

## What is not an entity

A map holds things that are not `CMapEntity` and so never appear in the entity
list. `structures` reaches them:

```
hammer5tools.vmap_read path=<map> structures="connections"   # entity I/O
hammer5tools.vmap_read path=<map> structures="overlays"      # decals
hammer5tools.vmap_read path=<map> structures="instances"     # prefabs and instances
hammer5tools.vmap_read path=<map> structures="paths"         # paths and their nodes
hammer5tools.vmap_read path=<map> structures="groups"        # editor grouping
```

`connections` is the one that matters most for understanding a map's behaviour:
each entry is an output wired to an input — `outputName`, `targetName`,
`inputName`, `overrideParam`, `delay`, `timesToFire`. This is where map logic
lives, and no entity property shows it.

`overlays` are decals (`CMapStaticOverlay`) with their placement; `instances`
covers `CMapInstance` and `CMapPrefab`, including the prefab variable overrides.

Ropes are ordinary entities (`move_rope`, `keyframe_rope`), so they come back
through `classname`, not here.

`vmap_read` never returns the node tree, at any detail level. Use `classname` or
`select` to reach what you need.

## What an entity class actually is

```
hammer5tools.entity_info classname="light_omni2"
hammer5tools.entity_info classname="prop_static" include_properties=false
hammer5tools.entity_info search="rope"
```

This reads the game's own entity definitions from the installed build, so it
describes the class and every keyvalue it accepts — type, and the help text
Hammer shows — including keyvalues inherited from base classes. It covers
whatever the installed build defines, so an entity added by a later update is
described as soon as the game ships it.

Use it when a map read turns up a class you do not know, or before setting a
keyvalue, to check the name and type rather than guessing. `include_properties:
false` gives just the one-line description, which is a few dozen tokens.

A class-filtered `vmap_read` already carries that one-line description, so the
common case needs no extra call.

## SmartProps placed in a map

`vmap_scene` with `include="smartprops"` is the one to know. Each placement
reports its `.vsmart` resource, its world position, and `variables` — the
per-instance overrides the map applied on top of the SmartProp's own defaults.
That is what makes one fence in a map different from another using the same
asset, and it is the only place those values exist.

To understand a placement fully, read both halves: the placement's `variables`
here, and the SmartProp's exposed parameters and defaults through
`hammer5tools.vsmart_read`. An override names a variable the asset declares; if
it names one the asset no longer has, that override is dead.

`distinct_smartprops` in the summary counts placements per `.vsmart`, which
answers "where is this SmartProp used, and how often" without paging.

## Meshes

`include="meshes"` reports each brush mesh's name, submesh count, and materials.
Vertex, index, normal, and UV arrays are deliberately not returned — they run to
megabytes and there is nothing an agent can do with them. Use the materials to
identify what a mesh is.

## Where a map's assets come from

```
hammer5tools.resolve_dependencies path=<map>     # recursive, split by kind
hammer5tools.find_unused_assets   map_path=<map>  # orphans in the addon
```

Both are paged and report counts first. See `addon-maintenance`.
