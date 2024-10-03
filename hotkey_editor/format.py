import keyvalues3 as kv3

class HotkeysOpen():
    def __init__(self, filepath):
        self.data = kv3.read(filepath)
        print(self.data)
        for i in self.data.value.items():
            print(i, type(i))
            if isinstance(i, list):
                for o in i:
                    print(i)

        kv3_ouput = kv3.textwriter.encode(self.data)
        print(kv3_ouput)
        print(self.data.value)

