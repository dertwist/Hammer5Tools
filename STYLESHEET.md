# UI/UX & Stylesheet Guidelines

This document outlines the UI/UX design rules, Qt styling principles, dark theme color tokens, custom widget guidelines, and visual design patterns for **Hammer 5 Tools**.

---

## 1. UI/UX Design Philosophy

- **Hammer / CS2 Tool Aesthetics**: Designed to match Valve's Source 2 Hammer environment and modern desktop tools with a dark, sleek appearance.
- **Unified Global QSS**: All windows, dialogs, property inspectors, and tree views MUST consume the central global stylesheet string from `src/styles/qt_global_stylesheet.py`.
- **High Contrast & Readability**: Maintain strong contrast between background containers (`#272727` / `#2E2E2E`) and text content (`#E5E5E5`).
- **Interactive Feedback**: Every interactive component (buttons, inputs, tree items, combo boxes) MUST define visual hover, pressed, and focus states.

---

## 2. Color Palette & Tokens

The application uses a dark theme palette defined in `src/styles/qt_global_stylesheet.py`:

| Token | Hex Code | Usage / Purpose |
|---|---|---|
| `background_neutral` | `#272727` | Main window background, outer containers |
| `background_primary` | `#2E2E2E` | Central widgets, card backdrops, dock headers |
| `background_secondary` | `#2F2F31` | Input fields, sidebar backgrounds, tree row backdrops |
| `text_primary` | `#E5E5E5` | Primary text, label text, button captions |
| `text_neutral` | `#A5A5A5` | Subtitles, disabled items, placeholder text |
| `stroke` | `#464649` | Borders, splitters, dividers, groupbox rules |
| `selected_fill` | `#515965` | Selection background in tree views and lists |
| `pressed` | `#6D7882` | Button active/pressed states |
| `accent` | `#4A83C9` | Primary action buttons, focused input borders |

---

## 3. Typography Standards

- **Primary Font Family**: `"Segoe UI"`, fallback to system sans-serif.
- **Label Styling**: `font: 600 10pt "Segoe UI"; color: #E5E5E5;`
- **Button Typography**: `font: 580 10pt "Segoe UI";`
- **Group Titles**: `font: 700 11pt "Segoe UI"; color: #FFFFFF;`
- **Console / Monospace**: Monospaced font (`"Consolas"`, `"Courier New"`).

---

## 4. Component & Widget Specifications

### Push Buttons (`QPushButton`)
- Default Border: `1px solid #464649`, Radius: `3px`.
- Hover State: Border highlight (`#515965` or `#4A83C9`).
- Pressed State: Background `#6D7882`.

### Group Boxes (`QGroupBox`)
- Top Border: `1px solid #5E5E5E`. Bottom/Left/Right: none.
- Indicator Icons: `url(://icons/arrow_drop_down.png)` (checked) and `url(://icons/arrow_drop_right.png)` (unchecked).

### Tree & Table Views (`QTreeView`, `QTreeWidget`, `QTableView`)
- Background: `#272727` / `#2F2F31`.
- Selected Row: Background `#515965`, Text `#E5E5E5`.

### Input Controls (`QLineEdit`, `QSpinBox`, `QComboBox`)
- Background: `#2F2F31`, Border: `1px solid #464649`.
- Focus Ring: Border color shifts to `#4A83C9` on focus.

---

## 5. UI Architecture & Implementation Workflow

1. **Qt Designer (`.ui`) Files**: Build layout structure using Qt Designer, then compile to Python using `compile_ui.py`.
2. **Central QSS Application**: Apply `QT_Stylesheet_global` at app startup (`src/app_core.py`).
3. **Property Icons**: Use `src/styles/property_icons.py` to retrieve property type icons dynamically.
4. **No Inline Hardcoded Styles**: Avoid inline `setStyleSheet()` calls with hardcoded colors inside widgets; leverage `src/styles/` helper functions.
