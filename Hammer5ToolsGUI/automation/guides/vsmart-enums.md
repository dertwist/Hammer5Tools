# SmartProp enum values

The strings Hammer shows in a dropdown are not the strings stored in the file.
Guessing here costs a full write-compile-open cycle, so check the table.

## Scale mode (`m_ScaleMode` on `FitOnLine`)

| Hammer label | KV3 value |
| :--- | :--- |
| Scale equally | `SCALE_EQUALLY` |
| **Scale last** | **`SCALE_END_TO_FIT`** |
| Maximize scale | `SCALE_MAXIMIZE` |

`"Scale last"` mapping to `SCALE_END_TO_FIT` is the trap. It is also usually the
right default for a kit: preceding segments stay at 1:1 and only the final
segment stretches to close the gap.

## Path position filter (`CSmartPropSelectionCriteria_PathPosition`)

`ALL`, `EVERY_NTH`, `NTH_OFFSET`, `START_ONLY`, `END_ONLY`.

## Pick mode (`PickOne`, `FitOnLine`)

`SEQUENCE`, `RANDOM`, `SPECIFIC_INDEX`.

## Grid origin (`Layout2DGrid`)

`CENTER`, `CORNER`.

## End caps (`CSmartPropSelectionCriteria_EndCap`)

Not an enum — two booleans, `m_bStart` and `m_bEnd`. An end post is
`m_bStart = false, m_bEnd = true`. Setting both selects both ends.

## Variable classes

`CSmartPropVariable_` + `Bool`, `Int`, `Float`, `Vector3D`, `Color`, `Angles`,
`MaterialGroup`, `Model`, `String`.

## Checking a value you are unsure about

Read a shipped preset that already does the thing:

```
hammer5tools.vsmart_read path=<preset> select="m_Children[0].m_ScaleMode"
```

That costs a few tokens and is always current, where a guess costs a compile.
