import keyvalues3 as kv3
data = (kv3.read('surfaceproperties.txt')).value
surfaces = []
for key, value in data.items():
    for item in value:
        for key, value in item.items():
            if key != 'surfacePropertyName':
                pass
            else:
                surfaces.append(value)
print(surfaces)