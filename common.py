from preferences import get_cs2_path
import os
import subprocess
import threading
import keyvalues3 as kv3
import re, unicodedata, random, string

#===============================================================<  Variables  >=============================================================
editor_info = {
    'editor_info':
    [{'Info':
    'Hammer5Tools by Twist', 'GitHub':
    'https://github.com/dertwist/Hammer5Tools',
    'Steam': 'https://steamcommunity.com/id/der_twist',
    'Twitter': 'https://twitter.com/der_twist'}
    ]}

#===========================================================<  generic functions  >=========================================================
def compile(input_file):
    """Compiling a file through game resourcecompiler"""
    def compile(input_file):
        resourcecompiler = os.path.join(get_cs2_path(), 'game', 'bin', 'win64', 'resourcecompiler.exe')
        process = subprocess.Popen([resourcecompiler, '-i', input_file], shell=True)
        process.wait()

    # Create a new thread for the compile function
    thread = threading.Thread(target=compile, args=(input_file,))
    thread.start()

#===============================================================<  Format  >============================================================
def Kv3ToJson(input):
    if '<!-- kv3 encoding:' in input:
        pass
    else:
        input = '<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->\n{' + input + '\n}'
    output = kv3.textreader.KV3TextReader().parse(input).value
    return output
def JsonToKv3(input):
    if isinstance(input, dict):
        return kv3.textwriter.encode(input)
    else:
        raise ValueError('[JsonToKv3] Invalid input type: Input should be a dictionary')