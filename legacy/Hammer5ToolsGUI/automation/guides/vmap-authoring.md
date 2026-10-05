# Writing VMAP levels

Read `vmap-reading` before changing an existing map. Core edits the actual DMX
document, preserving unrelated nodes, attributes, meshes, and references. Start
from a valid existing map, an explicit `skeleton`, or the installed addon template.
These operations do not synthesize brush topology or SmartProp parameter nodes.

## Insert props or blockout boxes

```
hammer5tools.vmap_write_blockout
    path=<addon>/maps/example.vmap
    boxes=[{"size":[512,512,16],"position":[0,0,0]},
           {"model":"models/props/chair.vmdl","scale":1,"position":[128,0,0]}]
    dry_run=true
```

Supply exactly one of `boxes` or `items_file` (UTF-8 JSON array of the same
items). Each item accepts model, position, angles, skin, and either size or scale.
Scale is a scalar or three finite nonzero components, default one for ordinary
props. Legacy size divides by ten and must be positive. Supplying both is an
error. The default model is `models/editor/placeholder_box.vmdl`, whose legacy
base size is 10 units. Use explicit scale for other models; size does not inspect
their dimensions. Confirm stock paths with
`hammer5tools.vpk_search query="models/editor/placeholder" limit=10`.

Insertion appends complete `prop_static` entities; existing children stay intact.
The tool uses Core serialization and does not run dmxconvert or splice text.
Missing source bounds are never used to infer an ordinary prop's scale.

## Stable IDs, transforms, and groups

`hammer5tools.vmap_nodes` returns paged GUIDs, names, classes, parent IDs, and
world origins. Its default limit is 50, maximum 500; read total/returned/truncated.
Use GUIDs when names are ambiguous.

`hammer5tools.vmap_transform` changes a node's local position, angles, or scale.
`hammer5tools.vmap_group` supports:

- create: name and optional parent_id; returns the new GUID.
- rename: id and name.
- reparent: id and parent_id; preserves the world transform.
- remove: a group id; ungroups children into its parent without deleting them.

Missing IDs, ambiguous names, cycles, and moving the world node are errors.
Transforms requiring shear cannot be expressed by VMAP position/angles/scales
and are rejected. Reparenting is checked before saving the document.

## Zoo layout

`hammer5tools.vmap_zoo` accepts exactly one of models (resource names) or an
addon-relative pattern, plus columns, position, three-component spacing, scale,
and optional group_id/skeleton. X/Y spacing must be positive. Models occupy a
deterministic grid using explicit spacing. Optional ground_align uses compiled
render bounds and requires game_dir/cs2_path and addon context; missing compiled
geometry is an error. Ground alignment is not inferred from source-FBX bounds.
`hammer5tools.model_bounds` reports supported
compiled LoD0 render bounds separately from unavailable physics bounds.

## Safe writes and verification

File paths accept absolute names or addon-relative names with explicit addon_root
or the configured addon read at request time. Model names remain resource names.
Every mutation supports dry_run, stages a same-directory file, reloads it, then
replaces the destination with a retained backup. Failed validation and dry runs
preserve original bytes. A successful parse/reload is not proof of Hammer reopen.
Test a copied map in Hammer and compile it before using it in production.

Compile textures/materials/models before their map; see `compile-verify`.
Missing compiled dependencies can produce warnings even when exit code is zero.
Use `hammer5tools.resolve_dependencies` and `hammer5tools.find_unused_assets`
to inspect dependencies/orphans before altering a pack.

`hammer5tools.vmap_rewrite_references` supports existing reference substitutions
and a dry-run planned_replacements preview. Its prefix matching can affect a
whole directory; inspect the preview before applying it. This operation preserves
the existing binary reference-rewrite contract.

Brush creation, destructive node deletion, and arbitrary SmartProp node authoring
remain outside these tools. Do not reconstruct an editable map from scene JSON:
the projection omits data needed by Hammer.
