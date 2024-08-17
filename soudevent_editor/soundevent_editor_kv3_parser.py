import sys
import keyvalues3 as kv3

def child_key(data, key_child):
    data_out = {}
    if key_child in data and isinstance(data[key_child], dict):
        for key in data[key_child]:
            data_out[key_child] = data_out.get(key_child, {})
            data_out[key_child].update({key: data[key_child][key]})
            print({key_child: {key: data[key_child][key]}})
            child_key(data[key_child], key)
    return data_out

def parse_kv3(path):
    data = kv3.read(path)
    data_kv3 = {}
    for parent in data.keys():
        data_out = child_key(data, parent)
        data_kv3.update(data_out)
    return data_kv3