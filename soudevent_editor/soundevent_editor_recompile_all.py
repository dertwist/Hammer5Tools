from preferences import get_cs2_path
import os
import subprocess

def compile(input_file):
    resourcecompiler = os.path.join(get_cs2_path(), 'game', 'bin', 'win64', 'resourcecompiler.exe')
    process = subprocess.Popen([resourcecompiler, '-i', input_file, '-f'], shell=True)
    process.wait()


