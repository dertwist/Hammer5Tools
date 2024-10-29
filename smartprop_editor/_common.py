from smartprop_editor.objects import element_prefix
from smartprop_editor.element_id import get_ElementID_key
def get_clean_class_name(input):
    if element_prefix in input:
        return input.replace(element_prefix, '')
    else:
        return input
def get_label_id_from_value(value):
    suffix = get_ElementID_key(value)
    prefix = get_clean_class_name(value['_class'])
    return f"{prefix}_%02d" % (int(suffix))

