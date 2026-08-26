# UI/UX and Stylesheet Guidelines

Hammer 5 Tools uses one compiled, application-wide QSS theme. Keep ordinary
widget appearance in this system so every editor and dialog responds uniformly
to the interface-brightness setting.

## 1. UI/UX principles

- Match the compact visual language of Source 2 Hammer and modern desktop tools.
- Maintain strong contrast between surfaces, controls, and text.
- Give controls clear hover, pressed, selected, disabled, and focus states.
- Keep widget construction and behavior in Python and reusable visual rules in QSS.
- Do not add local `setStyleSheet()` calls for static appearance.

## 2. Semantic theme tokens

QSS fragments use `@token` references. `theme.py` defines these fields for Dark,
Standard, and Bright explicitly; values are never derived at runtime.

| Token | Standard | Purpose |
|---|---:|---|
| `@background` | `#2e2e2e` | Main content and dock surfaces |
| `@surface` | `#272727` | Outer and recessed surfaces |
| `@surface_raised` | `#2f2f31` | Raised rows and panels |
| `@surface_input` | `#363637` | Input fields |
| `@text` | `#e5e5e5` | Primary text |
| `@text_muted` | `#a5a5a5` | Secondary and placeholder text |
| `@text_disabled` | `#797979` | Disabled text |
| `@border` | `#464649` | Borders, splitters, and dividers |
| `@border_strong` | `#5e5e5e` | Emphasized borders |
| `@accent` | `#4a83c9` | Primary actions and focus |
| `@accent_hover` | `#586776` | Accent hover state |
| `@accent_pressed` | `#6d7882` | Pressed and active state |
| `@selection` | `#515965` | Selected rows and items |
| `@selection_text` | `#ffffff` | Text on selections |
| `@error` | `#d1494a` | Error state |
| `@warning` | `#e5a00d` | Warning state |
| `@success` | `#5ab55e` | Success state |

The theme also owns `@control_height`, `@spacing_unit`, `@radius`,
`@border_width`, and `@icon_size` metrics.

Use semantic tokens whenever a color expresses one of these roles. Deliberate
legacy or feature-specific shades use `@hex_RRGGBB`; alpha variants use
`@rgba_RRGGBB_AAA`, where `AAA` is Qt alpha from 0 to 255. Their Dark and Bright
counterparts are explicit palette data in each `Theme`, not HSL calculations.

### Interface brightness

| Level | Name | Behavior |
|---:|---|---|
| 1 | Dark | Original darker palette |
| 2 | Standard | Canonical design values |
| 3 | Bright | Explicit light palette with dark text |

The selected level is stored as `APP/brightness_level`. A switch selects one
immutable `Theme` and reapplies the single compiled application stylesheet.
There is no Qt monkeypatch and no retained per-widget Designer stylesheet.

QPainter, delegates, and OpenGL code that cannot use QSS must read
`theme.color()`, `theme.qcolor()`, or `theme.gl_clear_color()`.

## 3. Typography

- Primary family: `"Segoe UI"` with the platform sans-serif fallback.
- Labels: `font: 600 10pt "Segoe UI";`
- Buttons: `font: 580 10pt "Segoe UI";`
- Group titles: `font: 700 11pt "Segoe UI";`
- Dock titles and tabs: `font: 9pt "Segoe UI";`
- Consoles and code: `"Consolas"`, `"Courier New"`, or another monospace face.

## 4. Component conventions

- Buttons use the shared border/radius rules and defined hover, pressed, focus,
  and disabled states.
- Group boxes use a top divider by default; avoid decorative side and bottom
  borders unless the component requires them.
- Tree and table selections use `@selection` with `@selection_text`.
- Inputs use `@surface_input`, a shared border, and `@accent` on focus.
- Feature variants opt in with a descriptive dynamic property such as
  `h5Component`, `h5State`, `selected`, `zebraRow`, or `paintThrough`.

When changing a dynamic property after a widget is visible, use
`gui.styles.common.set_style_property()` so Qt repolishes the widget.

## 5. Architecture and workflow

The styling system lives in `Hammer5ToolsGUI/gui/styles/`:

- `theme.py` owns the `Theme` dataclass, three explicit instances, metrics,
  brightness selection, and non-QSS color helpers.
- `qss_compiler.py` deterministically combines `qss/*.qss` and
  `qss/features/*.qss`, substitutes tokens, and rejects unknown tokens.
- `manager.py` is the only application stylesheet owner. Its `apply()` and
  `reapply()` functions are the only route to `QApplication.setStyleSheet()`.
- `qss/*.qss` contains shared component rules.
- `qss/features/*.qss` contains narrowly scoped feature rules.
- `property_icons.py` owns property-icon lookup.

For a new or changed widget:

1. Reuse an existing Qt type or `h5Component` selector where appropriate.
2. Otherwise set a descriptive dynamic property and add a rule to the narrowest
   suitable QSS fragment.
3. Prefer semantic tokens; use `@hex_` only for intentional one-off shades.
4. Keep a direct widget stylesheet only when a visual value is genuinely runtime
   data, such as a user-selected color swatch, and document the exception inline.
5. Compile all three themes and run the affected UI tests.

Qt Designer `.ui` files remain layout sources. `compile_ui.py` deliberately
strips generated `setStyleSheet()` statements, so Designer style properties do
not create private cascade roots. Put their visual rules in central QSS before
regenerating `ui_*.py`; never hand-edit generated modules.

Application startup applies the selected theme from
`Hammer5ToolsGUI/gui/main.py`.
