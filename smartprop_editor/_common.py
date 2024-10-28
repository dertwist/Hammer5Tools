from smartprop_editor.objects import element_prefix
global m_sLabel
global m_sLabel_list
m_sLabel = ""
m_sLabel_list = [""]
def get_clean_class_name(input):
    if element_prefix in input:
        return input.replace(element_prefix, '')
    else:
        return input
