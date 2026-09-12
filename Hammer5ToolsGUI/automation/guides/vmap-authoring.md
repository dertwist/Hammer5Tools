# Writing VMAP levels

For reading a map, see the `vmap-reading` topic.

Read this before writing anything into a `.vmap`. Hand-authored map structures
crash Hammer and `resourcecompiler.exe` with access violations (`0xC0000005`),
and a crash costs far more than the file it was trying to save.

## Never synthesise a CMapMesh

Do not generate `CDmePolygonMesh` from text or code. Source 2's mesh editing
requires a complete half-edge topology graph — `vertexEdgeIndices`,
`edgeVertexIndices`, `edgeOppositeIndices`, `edgeNextIndices`, `faceEdgeIndices` —
plus data streams (normals, tangents, UVs, material index arrays) whose lengths
all agree. Any mismatch corrupts memory during deserialisation, and the failure
surfaces as a crash inside `worldrenderer.dll` or `hammer.dll`, not as a parse
error.

**Use `prop_static` instead.** This is what Valve's own blockout pipeline does:
a box model placed with a non-uniform `scale`, which Source 2 supports on
`prop_static`. It is stable, compiles clean, and stays editable.

You do not have to assemble that by hand:

```
hammer5tools.vmap_write_blockout
    path  = <addon>/maps/<name>.vmap
    boxes = [ {"size": [512, 512, 16], "position": [0, 0, 0]},
              {"size": [512, 16, 256], "position": [0, 256, 128]} ]
    skeleton = <an existing .vmap>      # optional, defaults to the addon template
```

`size` is in world units and is converted to the model's scale for you;
`position`, `angles`, `model`, and `skin` are optional per box. The tool copies a
real map and adds only entities, so the container structure below is always
correct. A four-box map generated this way compiles through VRAD3 to exit 0.

### The box model

Use `models/editor/placeholder_box.vmdl`. It ships in `game/core/pak01_dir.vpk`,
with `placeholder_small_box.vmdl` and `placeholder_sphere.vmdl` beside it. Its
documented base size is 10 x 10 x 10 with the pivot at the bottom centre —
X `[-5, 5]`, Y `[-5, 5]`, Z `[0, 10]` — so a box of a given size is
`scale = dimension / 10.0`.

Note the directory: it is `models/editor/`, not `models/dev/`. `models/dev/` is a
different set (`dev_cube.vmdl`, `error.vmdl`, and similar) and lives in a
different archive.

Confirm any stock path against the install you are working on:

```
hammer5tools.vpk_search query="models/editor/placeholder" limit=10
```

`vpk_search` covers every stock archive — `csgo`, `csgo_core`, `csgo_imported`,
`csgo_lv`, and `core` — because which archive an asset lives in is not guessable
from its path. `models/dev/dev_cube.vmdl` is in `csgo`, while
`models/editor/placeholder_box.vmdl` is in `core`.

## Always start from a real Valve skeleton

`CMapWorld` inherits from `CMapEntity`/`CMapGroup` and its deserialiser expects
containers that a minimal hand-written root does not have: `relayPlugData`
(`DmePlugList`), `connectionsData`, `mapVariables` (`CMapVariableSet`),
`rootSelectionSet` (`CMapSelectionSet`), `nodeInstanceData`, `customVisGroup`,
and `randomSeed`. Missing ones are dereferenced as null pointers.

The working procedure, using `dmxconvert.exe` from `game/bin/win64/`:

```powershell
# 1. Decompile a known-good map to text
dmxconvert.exe -i <an existing simple map>.vmap -oe keyvalues2 -o skeleton.txt

# 2. Replace ONLY the contents of CMapWorld.children and map_asset_references

# 3. Recompile to binary
dmxconvert.exe -i skeleton.txt -oe binary -o maps/your_map.vmap
```

Pick the donor map from the addon you are working in. There is no guaranteed
`maps/prefabs/` directory in a stock install, so do not hard-code one.

## CMapSmartProp needs more than a reference

A `CMapSmartProp` entry in a `.vmap` requires both:

- `transformPin` — a `DmElement`
- `nodeData` — containing `evaluationVersion` (an array of class names and
  versions) and a `parameters` array

A minimal entry naming only the `.vsmart` path crashes the SmartProp loader. The
`parameters` array is where per-instance overrides of the SmartProp's exposed
variables live, which is why the variable names from `vsmart_read` matter here.

## Writing to a map

Writing is deliberately narrower than reading, because the failure mode is a
crash rather than a wrong answer.

**Supported:**

- `hammer5tools.vmap_write_blockout` — create a map of `prop_static` boxes from
  a skeleton, as above.
- `hammer5tools.vmap_rewrite_references` — re-point asset paths across an
  existing map, atomically, with a `dry_run` preview.

**Not supported, and not to be attempted by hand:** editing brush geometry,
adding arbitrary entities to an existing map, or changing a SmartProp
placement's variables. Those require writing into the DMX element graph, where a
mistake is an access violation rather than an error message. Do it in Hammer, or
extend the tools deliberately using the skeleton approach — copy a real map,
add only complete elements, and prove it with a compile.

If you need a new entity type placed programmatically, the safe pattern is the
one `vmap_write_blockout` uses: decompile a map that already contains that
entity, copy the entity block verbatim, change only its values, and recompile.
An entity block copied from real content has every container the deserializer
expects; one written from a schema does not.

## Inspecting and re-pointing an existing map

```
hammer5tools.resolve_dependencies      path=<map>       # recursive, by kind
hammer5tools.find_unused_assets        map_path=<map>   # orphans in the addon
hammer5tools.vmap_rewrite_references   vmap_path=<map> replacements={...} dry_run=true
```

`vmap_rewrite_references` matches a reference when it equals the search path or
starts with it, so a directory prefix moves a whole tree in one call. It is
atomic and it reports `planned_replacements` under `dry_run` — always read that
list before writing, because a too-short prefix silently matches more than you
meant.

## Compile the models first

`resourcecompiler.exe -i map.vmap` looks for compiled assets under `game/`. A
model with no `.vmdl_c` produces warnings rather than a clean failure, which is
easy to misread as success. Compile the models the map references before
compiling the map.

## Verify without opening Hammer

See the `compile-verify` topic. Reaching the VRAD3 lighting phase means the
geometry and entity data are structurally valid; an `.mdmp` beside the asset with
exit code 1 means they are not.
