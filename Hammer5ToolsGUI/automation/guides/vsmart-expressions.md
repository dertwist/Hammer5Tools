# SmartProp expressions

Expressions appear in `m_Expression`, `m_HideExpression`, `m_ReadOnlyExpression`,
and inside vector components as `{ m_Expression = "..." }`. They are evaluated
per instance.

## Intrinsics

`InstanceIndex()`, `InstanceCount()`, `LinearScale()`, `RandomFloat(min, max)`,
`RandomInt(min, max)`, `Deg2rad(d)`, `Rad2deg(r)`, `sin`, `cos`, `tan`, `asin`,
`acos`, `atan`, `sqrt`, `abs`, `min`, `max`, `floor`, `ceil`, `round`, `Pi`, and
ternaries `(condition ? a : b)`. Vector components are addressed as `.x`, `.y`,
`.z`.

An identifier that is not an intrinsic and not a declared variable evaluates to
**0**, silently. A hide expression that names a variable you renamed will simply
never fire. `vsmart_lint` reports this as `unknown-variable`.

## The NaN cascade — the most expensive bug in this format

IEEE arithmetic gives `0 / 0 = NaN`, and `atan(NaN) = NaN`. A single NaN in one
rotation angle invalidates the whole 4x4 transform, and the instance **vanishes
without any diagnostic**. Nothing in Hammer tells you why; the prop is simply
not there.

This is why every division needs a guarded denominator:

```
// Wrong: RingSizeTop == 0 or zero vertical instances gives 0/0
atan(RingSizeTop / (Floor(CylinderHeight / StepV) * StepV))

// Right: the denominator can never reach 0
(RingSizeTop == 0.0 ? 0.0 : atan(RingSizeTop / max(StepV, Floor(CylinderHeight / max(1.0, StepV)) * StepV)))
```

Two rules follow:

1. **Wrap every divisor in `max(1.0, ...)`** unless it is a non-zero literal.
   `round(iv_CircleLength / StepH)` returns 0 for a small radius or a large step,
   and that 0 becomes someone else's denominator one line later.
2. **Guard the whole trig call with a ternary** when the numerator has a
   meaningful zero case. Guarding the denominator alone still leaves `atan(0/x)`,
   which is fine, but `RingSizeTop == 0` usually means "no slant", and saying so
   explicitly is cheaper to read than deriving it.

`vsmart_lint` reports these as `unguarded-division` and `unguarded-trig`.

## Default values must have the type of their variable

A `Vector3D` or `Angles` variable written as `m_DefaultValue = ""` is not empty,
it is wrong. Static evaluators read `""` as `0` or `false`. If that variable
feeds an instance count, the count becomes 0 and the SmartProp produces nothing
before any runtime `SetVariable` gets a chance to run.

| Class | Default to write |
| :--- | :--- |
| `CSmartPropVariable_Float` | `0.0`, or the real value such as `128.0` |
| `CSmartPropVariable_Int` | `0` |
| `CSmartPropVariable_Vector3D` | `[0.0, 0.0, 0.0]` |
| `CSmartPropVariable_Angles` | `[0.0, 0.0, 0.0]` |
| `CSmartPropVariable_Color` | `[255, 255, 255, 255]` |
| `CSmartPropVariable_Bool` | `false` — **except** the category markers, which use `""` deliberately |

`vsmart_patch` and `vsmart_write` fill these in for you; `vsmart_lint` reports
what is still wrong as `untyped-default`.

## Vector components take numbers, not empty expressions

Inside `m_Components`, write `0.0`, not `{ m_Expression = "" }`. An empty
expression object where a scalar belongs is a malformed component and is reported
as `empty-expression`. `m_Expression` on `PlaceMultiple` is a raw string, not a
nested object.

## LinearScale placement

```kv3
m_vModelScale =
{
    m_Components = [ { m_Expression = "LinearScale()" }, 1.0, 1.0 ]
}
```

X only. Never on an `EndCap`-selected model.
