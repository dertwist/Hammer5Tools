# UI/UX & Stylesheet Guidelines

This document outlines the UI/UX design rules, Qt styling principles, dark theme color tokens, custom widget guidelines, and visual design patterns for **Hammer 5 Tools**.

---

## 1. UI/UX Design Philosophy

- **Hammer / CS2 Tool Aesthetics**: Designed to match Valve's Source 2 Hammer environment and modern desktop tools with a dark, sleek appearance.
- **Unified Global QSS**: All windows, dialogs, property inspectors, and tree views MUST consume the central global stylesheet string from `src/styles/qt_global_stylesheet.py`.
- **High Contrast & Readability**: Maintain strong contrast between background containers (`#151515` / `#1C1C1C`) and text content (`#E3E3E3`).
- **Interactive Feedback**: Every interactive component (buttons, inputs, tree items, combo boxes) MUST define visual hover, pressed, and focus states.

---

## 2. Color Palette & Tokens

The application uses a dark theme palette defined in `src/styles/qt_global_stylesheet.py`:

| Token | Hex Code | Usage / Purpose |
|---|---|---|
| `background_neutral` | `#151515` | Main window background, outer containers |
| `background_primary` | `#1C1C1C` | Central widgets, card backdrops, dock headers |
| `background_secondary` | `#1D1D1F` | Input fields, sidebar backgrounds, tree row backdrops |
| `text_primary` | `#E3E3E3` | Primary text, label text, button captions |
| `text_neutral` | `#9D9D9D` | Subtitles, disabled items, placeholder text |
| `stroke` | `#363639` | Borders, splitters, dividers, groupbox rules |
| `selected_fill` | `#414956` | Selection background in tree views and lists |
| `pressed` | `#606C77` | Button active/pressed states |
| `accent` | `#3A78C4` | Primary action buttons, focused input borders |

---

## 3. Typography Standards

- **Primary Font Family**: `"Segoe UI"`, fallback to system sans-serif.
- **Label Styling**: `font: 600 10pt "Segoe UI"; color: #E3E3E3;`
- **Button Typography**: `font: 580 10pt "Segoe UI";`
- **Group Titles**: `font: 700 11pt "Segoe UI"; color: #FFFFFF;`
- **Console / Monospace**: Monospaced font (`"Consolas"`, `"Courier New"`).

---

## 4. Component & Widget Specifications

### Push Buttons (`QPushButton`)
- Default Border: `1px solid #363639`, Radius: `3px`.
- Hover State: Border highlight (`#414956` or `#3A78C4`).
- Pressed State: Background `#606C77`.

### Group Boxes (`QGroupBox`)
- Top Border: `1px solid #505050`. Bottom/Left/Right: none.
- Indicator Icons: `url(://icons/arrow_drop_down.png)` (checked) and `url(://icons/arrow_drop_right.png)` (unchecked).

### Tree & Table Views (`QTreeView`, `QTreeWidget`, `QTableView`)
- Background: `#151515` / `#1D1D1F`.
- Selected Row: Background `#414956`, Text `#E3E3E3`.

### Input Controls (`QLineEdit`, `QSpinBox`, `QComboBox`)
- Background: `#1D1D1F`, Border: `1px solid #363639`.
- Focus Ring: Border color shifts to `#3A78C4` on focus.

---

## 5. UI Architecture & Implementation Workflow

1. **Qt Designer (`.ui`) Files**: Build layout structure using Qt Designer, then compile to Python using `compile_ui.py`.
2. **Central QSS Application**: Apply `QT_Stylesheet_global` at app startup (`src/app_core.py`).
3. **Property Icons**: Use `src/styles/property_icons.py` to retrieve property type icons dynamically.
4. **No Inline Hardcoded Styles**: Avoid inline `setStyleSheet()` calls with hardcoded colors inside widgets; leverage `src/styles/` helper functions.
