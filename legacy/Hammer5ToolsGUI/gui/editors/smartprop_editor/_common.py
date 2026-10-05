from gui.editors.smartprop_editor.objects import element_prefix
from gui.widgets.element_id import get_element_id_key

disable_line_value_length_limit_keys = [
    "m_vRandomPositionMax", "m_vRandomPositionMin", "m_flRandomScaleMax", "m_vRandomRotationMax",
    "m_flScale", "m_vRotation", "m_sModelName", "m_nScaleMode", "m_CoordinateSpace", "m_DirectionSpace",
    "m_GridPlacementMode", "m_GridOriginMode", "m_nNoHitResult", "m_SelectionMode", "m_PlacementMode",
    "m_DistributionMode", "m_HandleShape", "m_PointSpace", "m_PathSpace", "m_PlaceAtPositions", "m_Mode",
    "m_ApplyColorMode", "m_flBendPoint", "m_HandleSize", "m_ColorSelection", "m_HandleColor",
    "m_ColorChoices", "m_MaterialGroupName", "m_Expression", "m_StateName", "m_VariableName", "m_Comment",
    "m_VariableValue", "m_TargetName", "m_VariableComparison", "m_AllowedSurfaceProperties", 'm_nPickMode',
    "m_DisallowedSurfaceProperties", 'm_Components', 'm_flMinLength', 'm_flMaxLength', 'm_flRandomScaleMin',
    'm_flRandomScaleMax', 'm_flMaxLength', 'm_flMinLength', 'm_vRandomRotationMin', 'm_vRandomRotationMax',
    'm_flLength', 'm_vStart', 'm_vEnd', 'm_MaterialGroupName', 'm_bEnabled', 'm_flSpacing'
]
def read_variable_rows(layout, only_names=False):
    """The variable widgets in `layout`, as {index: [field, ...]}.

    The variables scroll-area layout is still the store for the variable list,
    so this is the one place that walks it. Reading it in a single function
    keeps the widget-attribute contract in one place for the day the document
    model owns the list instead.
    """
    rows = {}
    if layout is None:
        return rows
    for index in range(layout.count()):
        item = layout.itemAt(index)
        widget = item.widget() if item is not None else None
        if widget is None:
            continue
        if only_names:
            rows[index] = [widget.name, widget.var_class, widget.var_display_name]
        else:
            rows[index] = [
                widget.name,
                widget.var_class,
                widget.var_value,
                widget.var_visible_in_editor,
                widget.var_display_name,
            ]
    return rows


def get_clean_class_name(input):
    if element_prefix in input:
        return input.replace(element_prefix, '')
    else:
        return input
def get_clean_class_name_value(value):
    _class = value.get('_class', 'class')
    return get_clean_class_name(_class)
def get_label_id_from_value(value):
    suffix = get_element_id_key(value)
    prefix = get_clean_class_name(value.get('_class', 'None'))
    if prefix == 'None':
        prefix = 'element'
        print(f'Cant get value from _class key from value: \n {value}')
    return f"{prefix}_%02d" % (int(suffix))


def is_category_variable_name(name) -> bool:
    """Return True if the variable name matches a category marker pattern."""
    if not name or not isinstance(name, str):
        return False
    if name.startswith("hammer5tools_category_"):
        return True
    import re
    return bool(
        re.match(r"^hammer5tools_category_([a-z0-9]+)_(start|end)$", name)
        or re.match(r"^hammer5tools_category_(.*)_category_(.*)_(start|end)$", name)
    )


def is_category_widget(widget) -> bool:
    """Return True if the widget represents a variable category marker."""
    if widget is None:
        return False
    if hasattr(widget, "is_start") or hasattr(widget, "is_end"):
        return True
    widget_class = widget.__class__.__name__
    if "Category" in widget_class:
        return True
    name = getattr(widget, "name", None)
    if name and is_category_variable_name(name):
        return True
    return False


# Clipboard string patterns for SmartProp components (modifiers, selection criteria) and properties
CLIPBOARD_PREFIX = "hammer5tools:smartprop_editor_property"
CLIPBOARD_BATCH_PREFIX = "hammer5tools:smartprop_editor_property_batch"
CLIPBOARD_FIELD_PREFIX = "hammer5tools:smartprop_editor_field"


def classify_smartprop_class(class_name: str) -> str | None:
    """Return component kind ('modifier', 'selection_criteria', 'element', 'variable', 'choice') from a _class name."""
    if not isinstance(class_name, str):
        return None
    if class_name.startswith(("CSmartPropOperation_", "CSmartPropFilter_", "CSmartPropModifier_")):
        return "modifier"
    if class_name.startswith("CSmartPropSelectionCriteria_"):
        return "selection_criteria"
    if class_name.startswith("CSmartPropElement_"):
        return "element"
    if class_name.startswith("CSmartPropVariable_"):
        return "variable"
    if class_name.startswith("CSmartPropChoice"):
        return "choice"
    return None


def classify_smartprop_dict(data: dict) -> str | None:
    """Return component kind from a dict containing a _class key."""
    if isinstance(data, dict):
        cls_name = data.get("_class")
        if cls_name:
            return classify_smartprop_class(cls_name)
    return None


def parse_component_clipboard(clip_text: str) -> tuple[str | None, list[dict]]:
    """Parse clipboard text containing single or batch SmartProp component or element data.

    Accepts generic KV3 text as well as legacy semicolon-delimited strings for backward compatibility.

    Returns:
        (group_type, list_of_dicts) where group_type is 'modifier', 'selection_criteria',
        'element', or 'variable', or (None, []) if the clipboard format is invalid.
    """
    if not clip_text or not isinstance(clip_text, str):
        return None, []

    clip_text = clip_text.strip()
    if not clip_text:
        return None, []

    # 1. Check legacy prefix for backward compatibility
    is_legacy_batch = clip_text.startswith(CLIPBOARD_BATCH_PREFIX + ";;")
    is_legacy_single = clip_text.startswith(CLIPBOARD_PREFIX + ";;")
    if is_legacy_batch or is_legacy_single:
        prefix = CLIPBOARD_BATCH_PREFIX if is_legacy_batch else CLIPBOARD_PREFIX
        body = clip_text[len(prefix) + 2:]
        try:
            header, rest = body.split(";;", 1)
            payload_str, raw_group = rest.rsplit(";;", 1)
        except ValueError:
            return None, []

        raw_group = raw_group.strip()
        if raw_group in ("modifier", "modifiers", "operators"):
            group_type = "modifier"
        elif raw_group in ("selection_criteria", "criterion", "criteria"):
            group_type = "selection_criteria"
        else:
            group_type = raw_group

        try:
            import ast
            evaluated = ast.literal_eval(payload_str)
        except Exception:
            return None, []

        if is_legacy_batch:
            if isinstance(evaluated, list):
                dicts = [d for d in evaluated if isinstance(d, dict)]
                if dicts:
                    return group_type, dicts
        else:
            if isinstance(evaluated, dict):
                return group_type, [evaluated]
        return None, []

    # 2. Try parsing as KV3
    try:
        from gui.common import Kv3ToJson
        from gui.editors.smartprop_editor.document_model import normalize_kv3_text
        parsed = Kv3ToJson(normalize_kv3_text(clip_text))
    except Exception:
        return None, []

    if isinstance(parsed, dict):
        # Case A: Container dictionary
        for container_key, group_type in (
            ("m_Modifiers", "modifier"),
            ("m_SelectionCriteria", "selection_criteria"),
            ("m_Children", "element"),
            ("m_Variables", "variable"),
            ("m_Choices", "choice"),
        ):
            if container_key in parsed and isinstance(parsed[container_key], list):
                dicts = [d for d in parsed[container_key] if isinstance(d, dict)]
                if dicts:
                    first_kind = classify_smartprop_dict(dicts[0])
                    return (first_kind or group_type), dicts

        # Case B: Single component/element object
        if "_class" in parsed:
            kind = classify_smartprop_class(parsed["_class"])
            if kind:
                return kind, [parsed]
            return None, [parsed]

    elif isinstance(parsed, list):
        # Case C: List of component objects
        dicts = [d for d in parsed if isinstance(d, dict)]
        if dicts:
            first_kind = classify_smartprop_dict(dicts[0])
            return first_kind, dicts

    return None, []


def parse_property_clipboard(clip_text: str, target_value_class: str | None = None) -> tuple[bool, object]:
    """Parse clipboard text containing a single SmartProp property / field value.

    Accepts generic KV3 text (e.g. ``{ m_vEnd = { ... } }``) as well as legacy
    semicolon-delimited strings (``hammer5tools:smartprop_editor_field;;m_vEnd;;{...}``)
    or raw literal expressions.

    Returns:
        (success, payload) where success is True if a property value was found.
    """
    if not clip_text or not isinstance(clip_text, str):
        return False, None

    clip_text = clip_text.strip()
    if not clip_text:
        return False, None

    # 1. Check legacy prefix
    if clip_text.startswith(CLIPBOARD_FIELD_PREFIX + ";;"):
        parts = clip_text.split(";;")
        try:
            import ast
            if len(parts) >= 3:
                return True, ast.literal_eval(parts[2])
            elif len(parts) == 2:
                return True, ast.literal_eval(parts[1])
        except Exception:
            return False, None

    # 2. Try parsing as KV3
    try:
        from gui.common import Kv3ToJson
        from gui.editors.smartprop_editor.document_model import normalize_kv3_text
        parsed = Kv3ToJson(normalize_kv3_text(clip_text))
    except Exception:
        parsed = None

    if parsed is not None:
        if isinstance(parsed, dict):
            # If the user copied an entire element/component or container, don't treat as single property
            if any(k in parsed for k in ("m_Modifiers", "m_SelectionCriteria", "m_Children", "m_Variables", "m_Choices")):
                return False, None
            if "_class" in parsed and not target_value_class:
                return False, None
            if target_value_class and target_value_class in parsed:
                return True, parsed[target_value_class]
            if len(parsed) == 1:
                return True, next(iter(parsed.values()))
            if any(k in parsed for k in ("m_Components", "m_Expression", "m_SourceName", "m_VariableComparison", "m_AllowedSurfaceProperties")):
                return True, parsed
        elif isinstance(parsed, (list, int, float, str, bool)):
            return True, parsed

    # 3. Fallback to ast.literal_eval (Python literal dict / list / number)
    try:
        import ast
        evaluated = ast.literal_eval(clip_text)
        if isinstance(evaluated, dict):
            if any(k in evaluated for k in ("m_Modifiers", "m_SelectionCriteria", "m_Children", "m_Variables", "m_Choices")):
                return False, None
            if target_value_class and target_value_class in evaluated:
                return True, evaluated[target_value_class]
            if len(evaluated) == 1:
                return True, next(iter(evaluated.values()))
            if any(k in evaluated for k in ("m_Components", "m_Expression", "m_SourceName", "m_VariableComparison")):
                return True, evaluated
        elif isinstance(evaluated, (list, int, float, str, bool)):
            return True, evaluated
    except Exception:
        pass

    return False, None




