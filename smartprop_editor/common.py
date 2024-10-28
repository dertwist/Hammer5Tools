from smartprop_editor.objects import element_prefix
def get_clean_class_name(input):
    if element_prefix in input:
        return input.replace(element_prefix, '')
    else:
        return input