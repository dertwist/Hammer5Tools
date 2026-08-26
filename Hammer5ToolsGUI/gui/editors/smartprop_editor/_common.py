from gui.editors.smartprop_editor.objects import element_prefix
from gui.widgets.element_id import get_ElementID_key

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
def get_clean_class_name(input):
    if element_prefix in input:
        return input.replace(element_prefix, '')
    else:
        return input
def get_clean_class_name_value(value):
    _class = value.get('_class', 'class')
    return get_clean_class_name(_class)
def get_label_id_from_value(value):
    suffix = get_ElementID_key(value)
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


# Clipboard string patterns for SmartProp components (modifiers, selection criteria)
CLIPBOARD_PREFIX = "hammer5tools:smartprop_editor_property"
CLIPBOARD_BATCH_PREFIX = "hammer5tools:smartprop_editor_property_batch"


def parse_component_clipboard(clip_text: str) -> tuple[str | None, list[dict]]:
    """Parse clipboard text containing single or batch SmartProp component data.

    Returns:
        (group_type, list_of_dicts) where group_type is 'modifier' or 'selection_criteria',
        or (None, []) if the clipboard format is invalid.
    """
    if not clip_text or not isinstance(clip_text, str):
        return None, []

    is_batch = clip_text.startswith(CLIPBOARD_BATCH_PREFIX + ";;")
    is_single = clip_text.startswith(CLIPBOARD_PREFIX + ";;")

    if not (is_batch or is_single):
        return None, []

    prefix = CLIPBOARD_BATCH_PREFIX if is_batch else CLIPBOARD_PREFIX
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

    if is_batch:
        if isinstance(evaluated, list):
            dicts = [d for d in evaluated if isinstance(d, dict)]
            if dicts:
                return group_type, dicts
    else:
        if isinstance(evaluated, dict):
            return group_type, [evaluated]

    return None, []

