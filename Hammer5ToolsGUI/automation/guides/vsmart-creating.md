# Creating a SmartProp from scratch

`vsmart-authoring` covers the vocabulary; this is the order of operations for
building a new one. Every recipe ends the same way, with lint, evaluate, compile.

## The skeleton

`vsmart_write` creates a valid empty document. It fills typed defaults and
assigns element IDs, so you never hand-write either.

```
hammer5tools.vsmart_write
    path        = <addon>/smartprops/<name>.vsmart
    root_class  = "CSmartPropElement_Group"
    variables   = [ ... ]
    children    = [ ... ]
    dry_run     = true          # look first
```

Class names may be written short — `"Float"` instead of
`"CSmartPropVariable_Float"` — and are expanded on write. Then add parameters
and structure incrementally with `vsmart_patch` rather than rewriting the file.

## Recipe: a scatter prop

A group that places one of several models many times inside an area.

1. Variables: `Count` (Int), `Radius` (Float), `Seed` (Int), `ModelCount` (Int),
   and `Model1..N` (Model). Hide slot N behind `"ModelCount < N"` so the panel
   shows only the slots in use.
2. Child: `CSmartPropElement_PlaceMultiple` with `m_Expression = "Count"` —
   a raw string, not a nested object.
3. Under it, `CSmartPropElement_PickOne` over the model slots, filtered by
   `CSmartPropFilter_VariableValue` on `ModelCount`.
4. Modifiers on the group: `RandomOffset` bounded by `Radius`, `RandomRotation`
   on Z, `RandomScale` if wanted — all seeded from `Seed`.
5. Group the parameters: one `add_category` call per group.

Guard anything that divides by `Count` or `Radius`; both can be zero while an
artist is typing. See `vsmart-expressions`.

## Recipe: a linear kit (fence, pipe, railing)

```
FitOnLine (m_ScaleMode = SCALE_END_TO_FIT)
├── Model  panel     m_vModelScale.m_Components[0] = LinearScale()
└── Model  end post  m_SelectionCriteria = [EndCap m_bEnd = true], scale 1.0
```

`SCALE_END_TO_FIT` is what Hammer labels **"Scale last"**; see `vsmart-enums`.
Add a `CreateSizer` bound to length on X and height on Z, gated behind an
`EditInViewport` bool. Never put `LinearScale()` on the end cap — `vsmart_lint`
reports that as `endcap-linear-scale`.

For a kit shipping at two densities, expose a `Quality` choice driving a
`use_midpoly` bool and switch models with `CSmartPropFilter_VariableValue`. See
`material-texture` for the `_lp` / `_mp` naming that makes this mechanical.

## Recipe: a grid

`CSmartPropElement_Layout2DGrid` with `CENTER` or `CORNER` origin, segment counts
driven by `round(Size / max(1.0, Spacing))` — note the guarded denominator — and
optional row shifting for a running bond. A per-row rotation offset turns the
same tree into a spiral.

## Choosing models

Stock models come from the official archives:

```
hammer5tools.vpk_search  query="models/props/" extension="vmdl" limit=50   # all stock archives
hammer5tools.vpk_extract internal_path=<path from search> output_path=<local>
```

Extraction accepts the source name that search reports and resolves the compiled
`_c` entry for you.

## Finishing every SmartProp

```
hammer5tools.vsmart_lint     path=<file>   # or a directory, to audit a whole kit
hammer5tools.vsmart_evaluate path=<file>   # model_count, bounds, diagnostics
hammer5tools.compile_asset   path=<file>   # exit code 0
```

`model_count` of 0 means broken, not empty. Compile the models the SmartProp
references before the SmartProp itself.

One caution when editing existing props: element IDs seed `RandomOffset`,
`RandomRotation`, and `RandomScale`, so changing an ID moves the instances it
places. The tools only reassign genuinely duplicated IDs for that reason, and you
should not renumber by hand.
