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
#=================================================================<  Label  >===============================================================

def add_label_list(label):
    global m_sLabel
    global m_sLabel_list
    if label in m_sLabel_list:
        pass
    else:
        m_sLabel_list.append(label)

def set_Label(label):
    global m_sLabel
    global m_sLabel_list
    m_sLabel = label
    return label
def get_label(_class)
    global m_sLabel
    global m_sLabel_list
    base_name = get_clean_class_name(_class)
    if base_name in m_sLabel_list:
        name = f"{base_name}_{}"
    pass

