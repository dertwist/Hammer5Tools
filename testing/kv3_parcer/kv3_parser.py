
import sys
import keyvalues3 as kv3
data = {'m_Variables': [{'_class': 'CSmartPropVariable_Float', 'm_VariableName': 'length', 'm_nElementID': 61}, {'_class': 'CSmartPropVariable_Int', 'm_VariableName': 'height', 'm_nElementID': 62}], 'generic_data_type': 'CSmartPropRoot', '_editor': {'m_nElementID':'1'}}

data_read = kv3.read('sample.vsmart')
data = data_read
# print(type(data['_editor']))
# print(data['generic_data_type'])
#
#
# print(data['m_Variables'])

def child(data, key_child):
    data_out = {}
    if isinstance(data[key_child], dict):
        print('dict', key_child)
        data_out.update({key_child: data[key_child]})
    if isinstance(data[key_child], str):
        print('str', key_child)
        data_out.update({key_child: data[key_child]})
    if isinstance(data[key_child], list):
        def list_child(data, key):
            # print(data)
            for item in data:
                print('item', item)
                for key_item in item.keys():
                    print('key_item', key_item)
                    if key_item == key:
                        print('Found child')
                        data_out.update({key_child: data})
                        list_child(item[key], key)


        if key_child == 'm_Children':
            list_child(data[key_child], key_child)
        else:
            print('list', key_child, data[key_child])
            data_out.update({key_child: data[key_child]})
    else:
        print('Do not match anyone')
    return data_out

data_kv3 = {}
for parent in data.keys():
    data_kv3.update(child(data, parent))


print(data_kv3)

# kv3.write(data_kv3, sys.stdout)
kv3.write(data_kv3, 'output.vsmart')
