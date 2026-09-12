# Materials, textures, and models

## Paths

Content-relative, forward slashes, case-insensitive. `materials/props/wall.vmat`,
not `materials\Props\Wall.vmat`. Present them to the user the same way.

## Materials (`.vmat`)

A `.vmat` is a VDF `Layer0` block: a `shader`, texture slots, `F_*` feature
flags, scalar parameters, and optional `SystemAttributes` / `Attributes` blocks.
The default CS2 world shader is `csgo_environment.vfx`; props commonly use
`csgo_complex.vfx`.

```
hammer5tools.vmat_read  path=<file>                          # shader, slots, flags, parameters
hammer5tools.vmat_edit  path=<file> set_slots={...} dry_run=true
hammer5tools.vmat_write path=<file> shader=… slots={…} flags={…} dry_run=true
```

`vmat_write` creates a file from scratch; `vmat_edit` changes one that exists.
Use `edit` on anything already in the addon — `write` replaces the whole file.

`vmat_edit` re-serialises through the writer, so formatting is normalised and
comments outside `Layer0` are not preserved. Preview with `dry_run` when that
matters.

## Textures (`.vtex`)

A `.vtex` is a compile configuration, not an image: it names input files, an
output format (`BC7`, `DXT1`, ...), a colour space (`srgb` for albedo, `linear`
for data maps such as normals and roughness), and an output type (`2D`, `Cube`).

```
hammer5tools.vtex_read  path=<file>
hammer5tools.vtex_write path=<file> input_file=… output_format="BC7" color_space="srgb"
hammer5tools.vtex_edit  path=<file> updates={…} dry_run=true
```

Getting the colour space wrong is not a compile error — it is a subtly wrong
render. Albedo and anything the eye reads as colour is `srgb`; normals,
roughness, metalness, masks, and packed data are `linear`.

## Models (`.vmdl`)

A `.vmdl` is a ModelDoc tree: `RenderMeshList` holds `RenderMeshFile` entries
pointing at `.fbx`/`.dmx` sources, `MaterialGroupList` holds remaps from the
mesh's material names to real `.vmat` paths, `PhysicsShapeList` holds collision,
and `LODGroupList` holds switch thresholds.

```
hammer5tools.vmdl_read  path=<file>
hammer5tools.vmdl_edit  path=<file> updates={"material_remaps": [...]} dry_run=true
hammer5tools.vmdl_write path=<file> mesh_rel_path=<fbx> material_remaps=[…] physics=true
```

`vmdl_write` generates a standard ModelDoc41 document around a mesh file, which
is the quick path from a freshly exported `.fbx` to something compilable.

## Naming conventions that pay off

When a kit ships at two densities, keep the suffix in both the model and the
mesh: `*_lp.vmdl` / `*_lp.fbx` for low poly, `*_mp.vmdl` / `*_mp.fbx` for mid
poly, with materials matching (`*_mp_*`). A SmartProp can then expose a single
`Quality` choice that swaps a `use_midpoly` bool, and a
`CSmartPropFilter_VariableValue` picks the branch. Renaming a material means
updating its texture references inside the shader block too — `vmat_read` shows
you the slots.

## Moving assets

`hammer5tools.vmap_rewrite_references` does batch search-and-replace across a
map's dependencies atomically. Always run it with `dry_run: true` first and read
the matched replacements before writing.
