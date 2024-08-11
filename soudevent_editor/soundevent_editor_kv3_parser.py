import sys
import keyvalues3 as kv3

def child_merge(block_1, block_2):
    merged_data = {}

    # Iterate through the keys of both dictionaries
    for key in set(block_1.keys()).union(block_2.keys()):
        if key in block_1 and key in block_2:
            # If both dictionaries have the same key, merge their values
            merged_data[key] = {**block_1[key], **block_2[key]}
        elif key in block_1:
            # If the key is only in block_1
            merged_data[key] = block_1[key]
        else:
            # If the key is only in block_2
            merged_data[key] = block_2[key]

    return merged_data



def child_key (data, key_child):
    data_out = {}
    if isinstance(data[key_child], dict):
        for key in data[key_child]:
            data_out = child_merge(data_out, {key_child: {key: data[key_child][key]}})
            if key == 'volume':
                try:
                    data_out = child_merge(data_out, {key_child: {key: data[key_child][key]}})
                except:
                    pass
                print(data_out)
            if key == 'position':
                try:
                    data_out = child_merge(data_out, {key_child: {key: data[key_child][key]}})
                except:
                    pass
            child_key(data[key_child], key)
    elif isinstance(data[key_child], list):
        try:
            if key_child == 'distance_volume_mapping_curve':
                for key in data[key_child]:
                    block_new = {key_child: key}
                    data_out = child_merge(data_out, block_new)
                    print(key,data[key_child])
                    print(data_out)
        except:
            pass
        for key in data[key_child]:
            try:
                if key_child == 'distance_volume_mapping_curve':
                    block_new = {key_child: {key: data[key_child][key]}}
                    data_out = child_merge(data_out, block_new)
                    print(block_new)
                else:
                    block_new = {key_child: {key: data[key_child][key]}}
                    data_out = child_merge(data_out, block_new)
                    print(block_new)
            except:
                pass
    elif isinstance(data[key_child], int):
        pass
        # print(key_child,'int ', data[key_child])
    elif isinstance(data[key_child], float):
        try:
            for key in data[key_child]:
                print(key_child, key, data[key_child][key])
        except:
            pass

    elif isinstance(data[key_child], str):
        try:
            for key in data[key_child]:
                print(key_child, key, data[key_child][key])
        except:
            pass
    else:
        print('Do not match')
    return data_out

def parse_kv3(path):
    data = kv3.read(path)
    data_kv3 = {}
    for parent in data.keys():
        data_out = child_key(data, parent)
        data_kv3 = child_merge(data_kv3, data_out)
    return data_kv3