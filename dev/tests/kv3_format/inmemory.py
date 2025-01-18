import keyvalues3 as kv3

# var = 'test'
var = {'fd': ['test']}
# var = 'a'
kv3_data = kv3.json_to_kv3(var)
print(kv3_data, type(kv3_data))

json_val = kv3.kv3_to_json(kv3_data)

print(json_val, type(json_val))