# Compiling and verifying

## The compiler is the test harness

`resourcecompiler.exe` runs the real parser, the real loaders, and the Embree BVH
builder. You do not need to open Hammer to find out whether an asset is sound.

```
hammer5tools.compile_asset path=<file>
```

Use an absolute source-file path. Optional `cs2_path` selects the installation;
otherwise the configured CS2 path is read at call time. `force: true` forwards
`-f` to the compiler. `timeout_seconds` defaults to 120 and controls the execution
deadline, separately from the MCP client's tool timeout. These options already
exist in the single-file tool.

Check `success`, `exit_code`, and `error` in the structured result. The MCP
envelope's `isError: false` alone does not mean compilation succeeded. Output
is bounded. Full Unicode logs live in Core-owned files; timeout and cancellation
results remain JSON-safe.

## Batch and background compilation

`hammer5tools.compile_assets` accepts exactly one of `paths` (string array),
`pattern` (addon-relative glob), or `paths_file` (UTF-8 JSON array of strings).
Compiler/grid patterns use * and ? (crossing path separators); directory links
are not traversed. Reference-list patterns also support bracket character sets.
Use `addon_root` for the explicit absolute content directory, otherwise the
active addon is read at request time. Absolute asset paths work independently.
Drive-relative paths such as `C:foo` and relative escapes through `..` or links
are rejected. Resource names inside materials/models remain resource names.

Inputs are validated, deduplicated, and sorted before launching anything.
`dry_run: true` returns a bounded preview. Batches use the compiler's documented
`-filelist` option with one temporary UTF-8 line list; it is removed afterwards.
`force: true` forwards `-f`. The aggregate `success`/`exit_code` describe the
compiler invocation. `unknown_count` honestly records that aggregate output
does not establish individual asset outcomes; zero per-asset compiled/failed
counts are not a promise that every asset succeeded.

Pass `background: true` to either compilation tool to get a `job_id` promptly.
`hammer5tools.compile_job_status` returns queued/running/succeeded/failed/
cancelled/interrupted state. `hammer5tools.compile_job_cancel` requests cancellation
of the live owned process tree; poll until the job reaches a terminal state.
Compilation runs in Core, with one shared slot per host for foreground/background
calls. Independent server processes must not compile into the same output scope.

`hammer5tools.compile_log` accepts `log_id`, `offset` (Unicode scalar character
offset), and `limit` (default 4096, maximum 8192 characters). Responses contain
bounded warning/error samples and counts from both streams, duration, and a log
ID. Full logs and job metadata live under LocalAppData/Hammer5Tools/automation
and are retained seven days. Backups of authored files are retained separately.

A client timeout/disconnection does not cancel a running job while its server
process remains alive. Closing the server ends its in-process job supervision;
on restart, persisted active jobs become interrupted and report any possible
surviving process. Stale PIDs are never killed or restarted automatically.
Jobs belonging to another live host can be inspected from persisted metadata;
cancellable_here is false and cancellation must use their original server.
No tool terminates CS2/Hammer. Ping/status remain responsive during background
work. EOF still means the transport input closed; encoding recovery is preserved.

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
