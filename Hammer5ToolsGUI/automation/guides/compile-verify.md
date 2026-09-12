# Compiling and verifying

## The compiler is the test harness

`resourcecompiler.exe` runs the real parser, the real loaders, and the Embree BVH
builder. You do not need to open Hammer to find out whether an asset is sound.

```
hammer5tools.compile_asset path=<file>
```

Reading the result:

- **exit code 0** — the asset parsed, loaded, and compiled.
- **exit code 1 with an `.mdmp` next to the asset** — an access violation. For a
  map this almost always means invalid mesh topology or a missing container in
  the root element; see the `vmap-authoring` topic.
- **reaches the VRAD3 lighting phase** — for a map, this means the geometry and
  entity data are structurally valid. Lighting can be slow; getting there is the
  signal you wanted.
- **warnings about missing `.vmdl_c`** — a referenced model was never compiled.
  This is a warning, not a failure, and it is easy to mistake for success.
  Compile the dependencies first.

## Order of operations

Compile dependencies before dependents: textures, then materials, then models,
then SmartProps, then maps. `hammer5tools.resolve_dependencies` gives you the
list, and its response is paged — read `total` and `truncated` rather than
assuming the first page is everything.

## Reporting honestly

Exit code 0 is the claim you are allowed to make. "It should work" is not a
result. If you did not compile it, say that you did not compile it.

When a modifying tool was called with `dry_run: true`, nothing was written.
Never describe a dry run as a change.

## A full verification pass for a SmartProp

```
hammer5tools.vsmart_lint      path=<file>   # named findings, each with a fix
hammer5tools.vsmart_evaluate  path=<file>   # model_count, bounds, diagnostics
hammer5tools.compile_asset    path=<file>   # exit code 0
```

A `model_count` of 0 with no diagnostics is the signature of a NaN transform or a
zeroed instance count — `vsmart-expressions` explains both.

## Validating a whole addon

`hammer5tools.validate_addon` reports broken references; `find_unused_assets`
finds orphans relative to a map. Both are paged, and both report counts before
contents, so check `issues_count` or `unused_count` before asking for more pages.
