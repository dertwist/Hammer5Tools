from smartprop_editor.objects import element_prefix
from smartprop_editor.element_id import get_ElementID_key
def get_clean_class_name(input):
    if element_prefix in input:
        return input.replace(element_prefix, '')
    else:
        return input
def get_clean_class_name_value(value):
    _class = value['_class']
    return get_clean_class_name(_class)
def get_label_id_from_value(value):
    suffix = get_ElementID_key(value)
    prefix = get_clean_class_name(value.get('_class', 'None'))
    if prefix == 'None':
        prefix = 'element'
        print(f'Cant get value from _class key from value: \n {value}')
    return f"{prefix}_%02d" % (int(suffix))


def unique_counter_name(item, tree):
    parent = item.parent() or tree.invisibleRootItem()
    existing_names = [parent.child(i).text(0) for i in range(parent.childCount())]

    base_text = item.text(0)
    counter = 0
    new_text = base_text

    # Check if the element name has digits at the end
    if base_text[-1].isdigit():
        counter = int(base_text.split('_')[-1]) + 1
        new_text = f"{base_text.rsplit('_', 1)[0]}_{counter:02}"
    else:
        while new_text in existing_names:
            counter += 1
            new_text = f"{base_text}_{counter:02}"
    return  new_text