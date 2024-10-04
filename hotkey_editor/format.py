import keyvalues3 as kv3

class HotkeysOpen():
    def __init__(self, filepath):
        self.data = kv3.read(filepath)

