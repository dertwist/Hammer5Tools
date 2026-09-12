# SmartProp parameter UI

Everything here controls how a SmartProp's parameters appear in Hammer's Object
Properties panel and in the Hammer5Tools editor. None of it affects evaluation.

## Categories

Hammer5Tools recognises paired marker variables and renders everything between
them as a collapsible card. Hammer renders the markers themselves as inert
banner rows.

```kv3
{
    _class = "CSmartPropVariable_Bool"
    m_VariableName = "hammer5tools_category_sizing_start"
    m_bExposeAsParameter = true
    m_DefaultValue = ""
    m_DisplayName = "---------- Sizing ----------"
    m_Hammer5ToolsCategoryName = "Sizing"
    m_ReadOnlyExpression = "true"
}
    ... the parameters in the category, each also carrying m_Hammer5ToolsCategoryName ...
{
    _class = "CSmartPropVariable_Bool"
    m_VariableName = "hammer5tools_category_sizing_end"
    m_bExposeAsParameter = true
    m_DefaultValue = ""
    m_DisplayName = "                                             "
    m_Hammer5ToolsCategoryName = "Sizing"
    m_ReadOnlyExpression = "true"
}
```

The empty default and the whitespace display name are deliberate. Both markers
are required; a lone one leaves the card open and is reported as
`unpaired-category`.

Do not assemble this by hand. One operation does it:

```
hammer5tools.vsmart_patch path=<file> operations=[
  {"op": "add_category", "name": "Sizing", "contains": ["Length", "Height", "Width"]}
]
```

## Hiding parameters

`m_HideExpression` is a boolean expression; when it is true the parameter is
hidden. Use it to keep the panel honest about what currently matters:

| Intent | Expression |
| :--- | :--- |
| only while a mode is on | `"!EditInViewport"` |
| only while a toggle is set | `"!EnableHalfShift"` |
| a seed that cannot matter | `"Percentage == 100"` |
| a pivot for an unused rotation | `"ModelFlipAngle.x == 0 && ModelFlipAngle.y == 0 && ModelFlipAngle.z == 0"` |
| model slot N of a dynamic list | `"ModelCount < N"` |

That last row is the pattern for variable-length model lists: declare slots 1..16
and hide each behind `ModelCount < N`. Setting `ModelCount = 4` then reveals
exactly four.

## Locking parameters

`m_ReadOnlyExpression` greys a parameter out instead of hiding it. Prefer it when
the parameter still explains something about the prop's state:

- category markers: `"true"` (always inert)
- a slant angle when there is no slant: `"RingSizeTop == 0.0"`
- a taper toggle on an untapered shape: `"RingSizeTop == 0.0"`

Hiding removes information; locking keeps it visible and explains itself. Use
hiding for parameters that are irrelevant, locking for parameters that are
temporarily inapplicable.

## Interactive viewport sizers

`CSmartPropOperation_CreateSizer` draws a drag handle in the viewport and writes
the dragged value back into a variable. A linear kit usually binds X to its
length and Z to its height. A second sizer translated to the far end
(`[Radius, 0, Height]`) lets a taper be dragged directly. Gate them behind an
`EditInViewport` bool so the handles are not in the way during normal placement.
