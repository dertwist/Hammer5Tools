import keyvalues3 as kv3
import os

import zipfile
import os
import subprocess
import time
import argparse

def print_elapsed_time(stage_name, start_time):
    elapsed_time = time.time() - start_time
    print(f"{stage_name} took {elapsed_time:.2f} seconds")

stage_start_time = time.time()
soundevents_folder = 'soundevents'
soundevents = set()
for root, _, files in os.walk(soundevents_folder):
    for file_name in files:
        if file_name.endswith('.vsndevts'):
            file_path = os.path.join(root, file_name)
            try:
                data = kv3.read(file_path)
                for key in data.keys():
                    # print(key)
                    soundevents.add(key)
            except UnicodeDecodeError as e:
                print(f"Error decoding file: {file_path}. {e}")

with open('items.py', 'w') as file:
    file.write("soundevents = " + str(soundevents))

print_elapsed_time("Kill process", stage_start_time)