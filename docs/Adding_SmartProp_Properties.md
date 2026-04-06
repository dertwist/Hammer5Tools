# Adding or Updating SmartProp Properties

This guide explains the workflow for adding or updating new properties for SmartProp elements, operators, filters, and selection criteria within Hammer5Tools.

The SmartProp editor's dependency graph relies on a two-step synchronization process. To successfully expose a new native KeyValues3 property to the UI, you must update both the data schema and the UI mapping.

## Step 1: Update the Schema Definitions (`objects.py`)

The file `src/editors/smartprop_editor/objects.py` serves as the programmatic source of truth for the engine schema logic. 

1. **Locate the target list:**
   - `elements_list`: Modifies geometric nodes (e.g., `PlaceInSphere`, `Model`)
   - `operators_list`: Modifies math or modifier operations (e.g., `RandomOffset`, `Trace`)
   - `filters_list`: Modifies culling operations.
   - `selection_criteria_list`: Modifies conditional selection logic.

2. **Add the Key-Value Pair:**
   Find the dictionary representing your target node. Add the new attribute key using its exact engine prefix matching the schema dump (e.g., `m_vSnapIncrement`). Provide an appropriate default fallback value (`None` for uninitialized vectors, `0.0` for floats, `False` for booleans).

   ```python
   # Example: Adding a property to RandomOffset
   {'RandomOffset': {
       '_class': "CSmartPropOperation_RandomOffset",
       "m_vRandomPositionMin": None, 
       "m_vRandomPositionMax": None,
       "m_vSnapIncrement": None # <--- New property added here
   }},
   ```

## Step 2: Update the UI Mapping Cache (`property_frame.py`)

Simply adding the value to `objects.py` enables the background KV3 parser to serialize/deserialize the data, but the PySide6 UI will not render a widget for it until it is mapped.

1. **Locate `_prop_classes_map_cache`:**
   Open `src/editors/smartprop_editor/property_frame.py`. Near the top of the `PropertyFrame` class, locate the `_prop_classes_map_cache` dictionary.

2. **Register the UI Property:**
   Find the class key (e.g., `'RandomOffset'`) and append your new property key to the string array. The order of this array matters! It dictates the exact visual, top-to-bottom order the properties are rendered in the right-hand Hammer5Tools inspector dock.

   ```python
   'RandomOffset': [
       'm_nReferenceID', # UI internal logic
       'm_bEnabled',     # Evaluative master bool
       'm_vRandomPositionMin',
       'm_vRandomPositionMax',
       'm_vSnapIncrement' # <--- Register mapping here
   ],
   ```
   *Note: Standard elements (`CSmartPropElement_`) typically require both `'m_nReferenceID'` and `'m_bEnabled'` as the first two items in their list, whereas operators usually only require `'m_bEnabled'`.*

## Step 3: Resolving Complex UI Types (Optional)

Most primitives are automatically mapped via naming conventions in `property_frame.py`'s `_PREFIX_DISPATCH` method (e.g., `m_fl` yields a Float slider, `m_b` yields a Boolean checkbox, `m_v` yields a Vector3D grid). 

However, if your new property dictates specialized rendering (like a color dialog, combo box enum, or specific slider clamping bounds), you must declare it in the dispatch logic:

**Combo box Strings:** Add an entry tuple to `_COMBOBOX_SUBSTRING_RULES` identifying the allowed enum string states.
**Specific Overrides:** Add a mapping to `_EXACT_PROP_DISPATCH` mapping the `m_vMyKey` to a specific widget class (e.g., `PropertyColorMatch`, `PropertyFloat` with bound `extra_kwargs`).

Save both files and re-launch Hammer5Tools to see the new procedurally aware UI fields.
