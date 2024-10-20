from preferences import get_cs2_path
import os
import subprocess
import threading

editor_info = {
    'editor_info':
    [{'Info':
    'Hammer5Tools by Twist', 'GitHub':
    'https://github.com/dertwist/Hammer5Tools',
    'Steam': 'https://steamcommunity.com/id/der_twist',
    'Twitter': 'https://twitter.com/der_twist'}
    ]}


def compile(input_file):
    # Define a function to run compile in a thread
    def compile(input_file):
        resourcecompiler = os.path.join(get_cs2_path(), 'game', 'bin', 'win64', 'resourcecompiler.exe')
        process = subprocess.Popen([resourcecompiler, '-i', input_file], shell=True)
        process.wait()

    # Create a new thread for the compile function
    thread = threading.Thread(target=compile, args=(input_file,))
    thread.start()
