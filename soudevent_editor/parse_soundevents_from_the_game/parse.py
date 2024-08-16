import keyvalues3 as kv3
import os
soundevents_folder = 'soundevents'
soundevents = []
for root, _, files in os.walk(soundevents_folder):
    for file_name in files:
        if file_name.endswith('.vsndevts'):
            file_path = os.path.join(root, file_name)
            try:
                data = kv3.read(file_path)
                for key in data.keys():
                    print(key)
                    soundevents.append(key)
            except UnicodeDecodeError as e:
                print(f"Error decoding file: {file_path}. {e}")

with open('items.py', 'w') as file:
    file.write("soundevents = " + str(soundevents))