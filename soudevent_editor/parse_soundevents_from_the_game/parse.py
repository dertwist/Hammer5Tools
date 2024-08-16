import keyvalues3 as kv3
import os

# Path to the soundevents folder
soundevents_folder = 'soundevents'
soundevents = []
for root, _, files in os.walk(soundevents_folder):
    for file_name in files:
        if file_name.endswith('.vsndevts'):  # Check if the file is a vsndevts file
            file_path = os.path.join(root, file_name)

            # Apply the code snippet for each file
            data = kv3.read(file_path)

            for key in data.keys():
                print(key)
                soundevents.append(key)  # Append the key to the soundevents list

with open('sounds.txt', 'w') as file:
    for event in soundevents:
        file.write(event + '\n')