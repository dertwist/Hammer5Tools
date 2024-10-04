import os.path

import keyvalues3 as kv3

class HotkeysOpen():
    def __init__(self, filepath):
        self.data = kv3.read(filepath)

file = kv3.read(os.path.normpath("D:\\CG\\Projects\\Other\\Hammer5Tools\\hotkeys\\hammer\\test.txt"))
print(file.value)
