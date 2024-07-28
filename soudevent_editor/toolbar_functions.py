# toolbar_functions.py

from PySide6.QtWidgets import QFileDialog, QMessageBox
import json
import keyvalues3 as kv3
import sys
from preferences import get_cs2_path

def quick_export_to_file(tree, square_brackets_group,update_debug_window):
    root = tree.invisibleRootItem()
    data = tree_item_to_dict(root)
    data = convert_children_to_list(data, square_brackets_group)
    print(data)

    try:
        for key in square_brackets_group:
            if key in data and not isinstance(data[key], list):
                data[key] = [data[key]]
    except:
        pass

    kvfg = data

    print(kv3.write(kvfg, sys.stdout))
    get_cs2_path()

    file_path = r"D:\CG\Projects\Other\Hammer5Tools\soudevent_editor\soundevents_addon_out.vsndevts"
    file_path = 'output.vsndevts'

    orig_stdout = sys.stdout
    f = open(file_path, 'w')
    sys.stdout = f

    for i in range(1):
        print(kv3.write(kvfg, sys.stdout))
    sys.stdout = orig_stdout
    f.close()


    with open(file_path, 'r') as file:
        content = file.read()

    new_content = content.replace('None', '')

    with open(file_path, 'w') as file:
        file.write(new_content)
    update_debug_window()
    return str(data)


def export_to_file(tree, square_brackets_group, update_debug_window):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(None, "Save JSON File", "", "JSON Files (*.json);;All Files (*)",
                                               options=options)
    if file_path:
        json_data = export_to_json(tree, square_brackets_group)
        with open(file_path, "w") as file:
            file.write(json_data)
        QMessageBox.information(None, "Export", "Data exported successfully!")
    update_debug_window()

# def quick_export_to_file(tree, square_brackets_group, update_debug_window):
#     json_data = export_to_json(tree, square_brackets_group)
#     with open("exported_data.json", "w") as file:
#         file.write(json_data)
#     QMessageBox.information(None, "Export", "Data exported to 'exported_data.json' successfully!")
#     update_debug_window()

def tree_item_to_dict(item):
    if item.childCount() == 0:
        return item.text(1)
    data = {}
    for i in range(item.childCount()):
        child = item.child(i)
        key = child.text(0)
        value = tree_item_to_dict(child)
        if key in data:
            if isinstance(data[key], list):
                data[key].append(value)
            else:
                data[key] = [data[key], value]
        else:
            data[key] = value
    return data

def convert_children_to_list(data, square_brackets_group):
    if isinstance(data, dict):
        if 'm_Children' in data and isinstance(data['m_Children'], dict):
            data['m_Children'] = [data['m_Children']]

        for key, value in data.items():
            data[key] = convert_children_to_list(value, square_brackets_group)

    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = convert_children_to_list(data[i], square_brackets_group)

    return data