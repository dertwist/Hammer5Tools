# SmartProp authoring

A `.vsmart` is a KeyValues3 tree. The root is a `CSmartPropElement_Group` with
`m_Variables`, `m_Choices`, `m_Children`, and `m_Modifiers`. Evaluation walks the
tree, and each element contributes placements to its children through a transform
stack.

## Vocabulary

**Elements** (`CSmartPropElement_*`) place things:

| Element | Use it for |
| :--- | :--- |
| `Model` | one model instance; the leaf of most trees |
| `Group` | a container that shares modifiers with its children |
| `PlaceOnPath` | spacing along a Bezier/Hermite spline with oriented frames |
| `FitOnLine` | tiling or stretching between `vStart` and `vEnd` — fences, pipes, railings |
| `Layout2DGrid` | rectangular grids with `CENTER`/`CORNER` origins and row shifting |
| `PlaceInSphere` | scattering inside a sphere or hemisphere |
| `PickOne` | a selection dispatcher over its children |
| `PlaceMultiple` | repeat with an expression-driven count |

**Modifiers** (`CSmartPropOperation_*`) transform what an element places:
`SaveState`/`RestoreState` (push and pop the transform and variable stack),
`TraceInDirection` (snap to a surface and align to its normal), `SetOrientation`,
`RandomOffset` / `RandomRotation` / `RandomScale` (all seeded), `MaterialOverride`,
`SetTintColor`, `CreateSizer` (the interactive viewport handle).

**Selection criteria and filters** decide whether a branch runs at all:
`EndCap` (`m_bStart` / `m_bEnd`), `PathPosition` (`ALL`, `EVERY_NTH`, `START_ONLY`,
`END_ONLY`), `LinearLength`, `ChoiceWeight`, `SurfaceAngle`, `SurfaceProperties`,
and `Expression` for anything else.

## The shape of a working linear kit

A fence, pipe run, or railing is almost always the same structure:

```
FitOnLine (m_ScaleMode = SCALE_END_TO_FIT)
├── Model  panel     m_vModelScale.m_Components[0] = LinearScale()
└── Model  end post  m_SelectionCriteria = [EndCap m_bEnd = true], scale stays 1.0
```

`LinearScale()` stretches a panel along the line axis (X) so segments close
without a seam. Leave Y and Z at `1.0` — scaling thickness or height is visible
immediately. **Never put `LinearScale()` on an end-cap model**; a distorted
termination post is the single most common visual bug in a generated kit, and
`vsmart_lint` reports it as `endcap-linear-scale`.

## Authoring through the tools

Read the shape first, then patch one node:

```
hammer5tools.vsmart_read   path=<file>                      # summary: parameters + element outline
hammer5tools.vsmart_patch  path=<file> operations=[...]     # targeted edit, dry_run first
hammer5tools.vsmart_lint   path=<file>                      # named findings with fixes
hammer5tools.vsmart_evaluate path=<file>                    # counts, bounds, diagnostics
hammer5tools.compile_asset path=<file>                      # exit code 0 is the claim
```

`vsmart_patch` reindexes every `m_nElementID` on write, so duplicate IDs cannot
survive a patch, and it fills typed defaults for numeric, vector, angle, and
colour variables. You do not need to manage either by hand.

Do not read a document at `detail='full'` to change one field. Use
`select='m_Variables[m_VariableName=<name>]'` to look, and a `set` operation to
change it.

## Verifying

`vsmart_evaluate` returns `model_count`, `distinct_models`, a bounding box, and
diagnostics. A `model_count` of 0 on a prop that should place something almost
always means a `NaN` reached a transform or an instance count evaluated to zero —
see the `vsmart-expressions` topic.
