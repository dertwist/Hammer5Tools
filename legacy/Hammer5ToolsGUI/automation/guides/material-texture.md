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
# Bulk source authoring and geometry inspection

`hammer5tools.vmat_batch` and `hammer5tools.vmdl_batch` accept exactly one of
`items` or `manifest` (UTF-8 JSON array). Each item has path and action create
(default) or update. Fields mirror the single-item writer/editor; VMDL update
uses its updates object. Use addon_root for an explicit content directory, or
the active addon. All destinations and asset references in requested changes are
validated before writing. Create refuses existing files unless overwrite is
true. Shared material destinations in the same manifest can be referenced.
cs2_path (or the configured install) enables stock VPK reference validation.
Existing unknown document fields are retained by edits.

dry_run previews changes without destination writes. Every changed file is
staged beside its destination, re-parsed, and replaced with a retained .bak.
Writes are serialized. The batch has no rollback: changed/skipped/failed counts
and results report partial completion truthfully. Results and property names
are capped at 50; truncated means the response omits additional entries.
Each result also includes field_count and fields_truncated for its property preview.
Rerunning unchanged updates skips writes and creates no new backup.

`hammer5tools.model_bounds` reports compiled LoD0 render bounds, dimensions,
center, pivot-to-ground offset, vertex/triangle and render-submesh counts.
Optional position/angles/scale transform the measured geometry. Units are the
native compiled Source 2 world units; no conversion is inferred. VMDL inputs
use their compiled counterpart. Source-FBX and unavailable physics bounds are
explicitly unsupported, never labelled exact. A caller can set a positive
triangle_warning_threshold for advisory render-complexity warnings; it does
not measure or modify collision hulls.

## Explicit texture channels

`hammer5tools.texture_inspect` accepts input and optional constant_threshold
(0..255; zero tests exact constancy). It reports min/max and constancy per RGBA
channel. `hammer5tools.texture_split` accepts input and outputs, each {path,
channel:"r"|"g"|"b"|"a"}; the selected value fills RGB and alpha is opaque.
`hammer5tools.texture_pack` accepts path and channels with all r/g/b/a mappings.
Each mapping is a byte constant (0..255) or {path, channel}; at least one image
supplies dimensions and all input images must match.

These tools preserve raw channel values without gamma/linear conversion.
They support 8-bit PNG and lossless PNG output; other formats/bit depths are
rejected explicitly. Alpha is decoded unpremultiplied. Mutations support dry_run,
explicit overwrite, staged round-trip validation, and retained backups. No
default-texture substitution or FBM cleanup occurs automatically; referenced
textures and source files are retained.
